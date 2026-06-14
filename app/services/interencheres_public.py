from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from ..models import Sale, Lot

BASE_URL = 'https://www.interencheres.com'
CALENDAR_URL = f'{BASE_URL}/calendrier/'
RESULTS_URL = f'{BASE_URL}/resultats-ventes.html'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; PublicAuctionTracker/1.0; +https://localhost)',
    'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
}
MONTHS = {
    'janvier': 1, 'février': 2, 'fevrier': 2, 'mars': 3, 'avril': 4, 'mai': 5,
    'juin': 6, 'juillet': 7, 'août': 8, 'aout': 8, 'septembre': 9, 'octobre': 10,
    'novembre': 11, 'décembre': 12, 'decembre': 12,
}


@dataclass
class ParsedSale:
    external_url: str
    title: str
    house_name: str
    type: str | None
    status: str | None
    start_at: datetime | None
    city: str | None
    postal_code: str | None
    country: str | None
    source_page: str
    results_available: bool
    result_summary: str | None


@dataclass
class ParsedLot:
    lot_number: str | None
    title: str
    public_url: str | None = None
    image_url: str | None = None
    result_status: str | None = None
    result_amount: str | None = None


class InterencheresPublicCrawler:
    def __init__(self):
        self.client = httpx.Client(headers=HEADERS, timeout=25, follow_redirects=True)

    def close(self):
        self.client.close()

    def fetch_text(self, url: str) -> str:
        r = self.client.get(url)
        r.raise_for_status()
        return r.text

    def _extract_datetime(self, text: str):
        m = re.search(r'(\d{1,2})\s+([A-Za-zÀ-ÿ]+)\s+(\d{4})\s+à\s+(\d{1,2})h(\d{2})', text, re.I)
        if not m:
            return None
        day = int(m.group(1))
        month_name = m.group(2).lower()
        year = int(m.group(3))
        hour = int(m.group(4))
        minute = int(m.group(5))
        month = MONTHS.get(month_name)
        if not month:
            return None
        try:
            return datetime(year, month, day, hour, minute)
        except ValueError:
            return None

    def parse_sales(self, html: str, source_page: str, results_mode: bool = False):
        soup = BeautifulSoup(html, 'lxml')
        text = soup.get_text("\n", strip=True)
        chunks = re.split(r'(?=\b(?:Live|Chrono|Catalogue)\b)', text)
        sales = []
        for chunk in chunks:
            chunk = re.sub(r'\s+', ' ', chunk).strip()
            if len(chunk) < 40:
                continue

            m_type = re.search(r'\b(Live|Chrono|Catalogue)\b', chunk, re.I)
            sale_type = m_type.group(1).capitalize() if m_type else None
            loc = re.search(r"(\d{4,5})\s+([A-Za-zÀ-ÿ\-\s'’]+)\s*-\s*([A-Za-zÀ-ÿ\-\s'’]+)", chunk)
            postal = city = country = None
            if loc:
                postal = loc.group(1).strip()
                city = re.sub(r'\s+', ' ', loc.group(2)).strip()
                country = re.sub(r'\s+', ' ', loc.group(3)).strip()

            title = None
            house = None
            if m_type:
                after = chunk.split(m_type.group(0), 1)[1].strip()
                if loc:
                    prefix = chunk[:loc.start()].strip()
                    parts = [p.strip() for p in re.split(r'\s{2,}', prefix) if p.strip()]
                    if len(parts) >= 2:
                        title = parts[-2]
                        house = parts[-1]
                if not title:
                    title = re.split(r"S'inscrire à la vente|Accéder au direct|Voir les lots|Voir les résultats|\d{4,5}\s", after)[0].strip()

            if not title or len(title) < 4:
                continue
            if not house:
                house = 'Maison de ventes inconnue'

            if results_mode or 'Voir les résultats' in chunk:
                status = 'Terminée'
            elif 'En cours' in chunk:
                status = 'En cours'
            else:
                status = 'À venir'

            results_available = results_mode or ('Voir les résultats' in chunk)
            sales.append(
                ParsedSale(
                    external_url=source_page,
                    title=title,
                    house_name=house,
                    type=sale_type,
                    status=status,
                    start_at=self._extract_datetime(chunk),
                    city=city,
                    postal_code=postal,
                    country=country,
                    source_page=source_page,
                    results_available=results_available,
                    result_summary='Résultats disponibles publiquement' if results_available else 'Résultats non publiés ou non détectés',
                )
            )

        out = []
        seen = set()
        for s in sales:
            key = (s.title, s.house_name, s.source_page)
            if key not in seen:
                seen.add(key)
                out.append(s)
        return out

    def fetch_and_parse_sale_lots(self, sale_url: str, results_available: bool = False):
        html = self.fetch_text(sale_url)
        soup = BeautifulSoup(html, 'lxml')
        lots = []
        seen = set()
        for node in soup.find_all(['a', 'article', 'div', 'li']):
            txt = node.get_text(' ', strip=True)
            if len(txt) < 8:
                continue
            has_marker = any(k in txt for k in ['Estimation', 'Mise à prix', 'Enchère en cours', 'Lot '])
            if not has_marker:
                continue
            m_lot = re.search(r'\bLot\s*(?:n[o°.]?\s*)?(\d+[A-Za-z\-]*)\b', txt, re.I)
            lot_number = m_lot.group(1) if m_lot else None
            title = re.split(r'Estimation|Mise à prix|Enchère en cours|Proposé par|Live|Chrono|Catalogue', txt)[0].strip()
            if lot_number:
                title = re.sub(r'^Lot\s*(?:n[o°.]?\s*)?' + re.escape(lot_number) + r'\s*', '', title, flags=re.I).strip()
            if len(title) < 3:
                continue
            href = node.get('href') if hasattr(node, 'get') else None
            img = node.find('img') if hasattr(node, 'find') else None
            image_url = urljoin(BASE_URL, img.get('src')) if img and img.get('src') else None
            public_url = urljoin(BASE_URL, href) if href else None
            key = (lot_number, title[:120], public_url)
            if key in seen:
                continue
            seen.add(key)
            result_status = 'Adjugé' if ('Adjugé' in txt and results_available) else ('Invendu' if ('Invendu' in txt and results_available) else None)
            m_amount = re.search(r'(\d[\d\s\u202f]*\s?€)', txt)
            result_amount = m_amount.group(1).strip() if (m_amount and results_available) else None
            lots.append(ParsedLot(lot_number, title, public_url, image_url, result_status, result_amount))
        return lots

    def refresh_house(self, db: Session, house_name: str):
        norm = house_name.strip().lower()
        candidate_sales = []
        html_calendar = self.fetch_text(CALENDAR_URL)
        html_results = self.fetch_text(RESULTS_URL)
        for sale in self.parse_sales(html_calendar, CALENDAR_URL, False):
            if sale.house_name.strip().lower() == norm:
                candidate_sales.append(sale)
        for sale in self.parse_sales(html_results, RESULTS_URL, True):
            if sale.house_name.strip().lower() == norm:
                candidate_sales.append(sale)

        created_sales = updated_sales = created_lots = updated_lots = 0
        for ps in candidate_sales:
            db_sale = db.query(Sale).filter(Sale.external_url == ps.external_url, Sale.title == ps.title, Sale.house_name == ps.house_name).first()
            if not db_sale:
                db_sale = Sale(
                    external_url=ps.external_url,
                    title=ps.title,
                    house_name=ps.house_name,
                    type=ps.type,
                    status=ps.status,
                    start_at=ps.start_at,
                    city=ps.city,
                    postal_code=ps.postal_code,
                    country=ps.country,
                    source_page=ps.source_page,
                    results_available=ps.results_available,
                    result_summary=ps.result_summary,
                )
                db.add(db_sale)
                db.flush()
                created_sales += 1
            else:
                db_sale.type = ps.type
                db_sale.status = ps.status
                db_sale.start_at = ps.start_at
                db_sale.city = ps.city
                db_sale.postal_code = ps.postal_code
                db_sale.country = ps.country
                db_sale.results_available = ps.results_available
                db_sale.result_summary = ps.result_summary
                updated_sales += 1

            lot_candidates = []
            try:
                if db_sale.external_url and db_sale.external_url != db_sale.source_page:
                    lot_candidates = self.fetch_and_parse_sale_lots(db_sale.external_url, db_sale.results_available)
            except Exception:
                lot_candidates = []

            for pl in lot_candidates:
                q = db.query(Lot).filter(Lot.sale_id == db_sale.id)
                q = q.filter(Lot.lot_number == pl.lot_number) if pl.lot_number else q.filter(Lot.title == pl.title)
                db_lot = q.first()
                if not db_lot:
                    db.add(Lot(sale_id=db_sale.id, lot_number=pl.lot_number, title=pl.title, public_url=pl.public_url, image_url=pl.image_url, result_status=pl.result_status, result_amount=pl.result_amount))
                    created_lots += 1
                else:
                    db_lot.title = pl.title
                    db_lot.public_url = pl.public_url
                    db_lot.image_url = pl.image_url
                    db_lot.result_status = pl.result_status
                    db_lot.result_amount = pl.result_amount
                    updated_lots += 1
        db.commit()
        return {
            'created_sales': created_sales,
            'updated_sales': updated_sales,
            'created_lots': created_lots,
            'updated_lots': updated_lots,
            'matched_house': house_name,
        }
