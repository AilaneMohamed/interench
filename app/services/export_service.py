from io import BytesIO
import pandas as pd
from sqlalchemy.orm import Session
from ..models import Sale, Lot


def _rows_for_house(db: Session, house_name: str | None = None):
    query = db.query(Sale).order_by(Sale.start_at.desc().nullslast(), Sale.id.desc())
    if house_name:
        query = query.filter(Sale.house_name == house_name)

    rows = []
    for sale in query.all():
        lots = db.query(Lot).filter(Lot.sale_id == sale.id).order_by(Lot.id.asc()).all()
        if lots:
            for lot in lots:
                rows.append({
                    'sale_id': sale.id,
                    'house_name': sale.house_name,
                    'sale_title': sale.title,
                    'sale_type': sale.type,
                    'sale_status': sale.status,
                    'sale_start_at': sale.start_at.isoformat() if sale.start_at else None,
                    'city': sale.city,
                    'postal_code': sale.postal_code,
                    'country': sale.country,
                    'sale_url': sale.external_url,
                    'results_available': sale.results_available,
                    'result_summary': sale.result_summary,
                    'lot_number': lot.lot_number,
                    'lot_title': lot.title,
                    'lot_url': lot.public_url,
                    'image_url': lot.image_url,
                    'lot_result_status': lot.result_status,
                    'lot_result_amount': lot.result_amount,
                })
        else:
            rows.append({
                'sale_id': sale.id,
                'house_name': sale.house_name,
                'sale_title': sale.title,
                'sale_type': sale.type,
                'sale_status': sale.status,
                'sale_start_at': sale.start_at.isoformat() if sale.start_at else None,
                'city': sale.city,
                'postal_code': sale.postal_code,
                'country': sale.country,
                'sale_url': sale.external_url,
                'results_available': sale.results_available,
                'result_summary': sale.result_summary,
                'lot_number': None,
                'lot_title': None,
                'lot_url': None,
                'image_url': None,
                'lot_result_status': None,
                'lot_result_amount': None,
            })
    return rows


def build_csv_bytes(db: Session, house_name: str | None = None) -> bytes:
    df = pd.DataFrame(_rows_for_house(db, house_name))
    return df.to_csv(index=False).encode('utf-8')


def build_xlsx_bytes(db: Session, house_name: str | None = None) -> bytes:
    df = pd.DataFrame(_rows_for_house(db, house_name))
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='ventes_lots')
    output.seek(0)
    return output.read()
