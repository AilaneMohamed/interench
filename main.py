from pathlib import Path
from typing import Optional
import sys

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Sale, Lot
from schemas import SaleOut, SaleWithLotsOut, LotOut, RefreshResponse
from services.export_service import build_csv_bytes, build_xlsx_bytes
from services.interencheres_public import InterencheresPublicCrawler

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Interencheres Public Sales Tracker", version="1.0.0")


def _static_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        return base / "app" / "static"
    return Path(__file__).resolve().parent / "app" / "static"


static_dir = _static_dir()
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
def root():
    return (static_dir / "index.html").read_text(encoding="utf-8")


@app.post("/api/refresh", response_model=RefreshResponse)
def refresh_public_sales(
    house_name: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
):
    crawler = InterencheresPublicCrawler()
    try:
        return crawler.refresh_house(db, house_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        crawler.close()


@app.get("/api/sales", response_model=list[SaleOut])
def list_sales(house_name: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Sale).order_by(Sale.start_at.desc().nullslast(), Sale.id.desc())
    if house_name:
        q = q.filter(Sale.house_name == house_name)
    return q.all()


@app.get("/api/sales/{sale_id}", response_model=SaleWithLotsOut)
def get_sale(sale_id: int, db: Session = Depends(get_db)):
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Vente introuvable")
    return sale


@app.get("/api/sales/{sale_id}/lots", response_model=list[LotOut])
def get_sale_lots(sale_id: int, db: Session = Depends(get_db)):
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Vente introuvable")
    return db.query(Lot).filter(Lot.sale_id == sale_id).order_by(Lot.id.asc()).all()


@app.get("/api/export/csv")
def export_csv(house_name: Optional[str] = None, db: Session = Depends(get_db)):
    payload = build_csv_bytes(db, house_name)
    return StreamingResponse(
        iter([payload]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="ventes_lots.csv"'},
    )


@app.get("/api/export/xlsx")
def export_xlsx(house_name: Optional[str] = None, db: Session = Depends(get_db)):
    payload = build_xlsx_bytes(db, house_name)
    return StreamingResponse(
        iter([payload]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="ventes_lots.xlsx"'},
    )
``
