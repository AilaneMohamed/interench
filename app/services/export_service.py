from __future__ import annotations

import csv
from io import BytesIO, StringIO
from sqlalchemy.orm import Session
from openpyxl import Workbook
from models import Sale, Lot

HEADERS = [
    "sale_id",
    "house_name",
    "sale_title",
    "sale_type",
    "sale_status",
    "sale_start_at",
    "city",
    "postal_code",
    "country",
    "sale_url",
    "results_available",
    "result_summary",
    "lot_number",
    "lot_title",
    "lot_url",
    "image_url",
    "lot_result_status",
    "lot_result_amount",
]


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
                    "sale_id": sale.id,
                    "house_name": sale.house_name,
                    "sale_title": sale.title,
                    "sale_type": sale.type,
                    "sale_status": sale.status,
                    "sale_start_at": sale.start_at.isoformat() if sale.start_at else None,
                    "city": sale.city,
                    "postal_code": sale.postal_code,
                    "country": sale.country,
                    "sale_url": sale.external_url,
                    "results_available": sale.results_available,
                    "result_summary": sale.result_summary,
                    "lot_number": lot.lot_number,
                    "lot_title": lot.title,
                    "lot_url": lot.public_url,
                    "image_url": lot.image_url,
                    "lot_result_status": lot.result_status,
                    "lot_result_amount": lot.result_amount,
                })
        else:
            rows.append({
                "sale_id": sale.id,
                "house_name": sale.house_name,
                "sale_title": sale.title,
                "sale_type": sale.type,
                "sale_status": sale.status,
                "sale_start_at": sale.start_at.isoformat() if sale.start_at else None,
                "city": sale.city,
                "postal_code": sale.postal_code,
                "country": sale.country,
                "sale_url": sale.external_url,
                "results_available": sale.results_available,
                "result_summary": sale.result_summary,
                "lot_number": None,
                "lot_title": None,
                "lot_url": None,
                "image_url": None,
                "lot_result_status": None,
                "lot_result_amount": None,
            })

    return rows


def build_csv_bytes(db: Session, house_name: str | None = None) -> bytes:
    rows = _rows_for_house(db, house_name)
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=HEADERS)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8-sig")


def build_xlsx_bytes(db: Session, house_name: str | None = None) -> bytes:
    rows = _rows_for_house(db, house_name)

    wb = Workbook()
    ws = wb.active
    ws.title = "ventes_lots"

    ws.append(HEADERS)
    for row in rows:
        ws.append([row.get(col) for col in HEADERS])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output.read()
