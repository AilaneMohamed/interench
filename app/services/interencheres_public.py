from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from models import Sale, Lot

BASE_URL = "https://www.interencheres.com"
CALENDAR_URL = f"{BASE_URL}/calendrier/"
RESULTS_URL = f"{BASE_URL}/resultats-ventes.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; InterencheresPublicTracker/1.0; +https://localhost)",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

MONTHS = {
    "janvier": 1,
    "février": 2,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12,
    "decembre": 12,
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


def normalize_text(value: str | None) -> str:
    value = value or ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = value.lower().strip()
    value = re.sub(r"\s+", " ", value)
    return value


def looks_like_interencheres_url(value: str) -> bool:
    value = (value or "").strip().lower()
    return value.startswith("http://") or value.startswith("https://")


def is_profile_url(value: str) -> bool:
    value = (value or "").strip().lower()
    return "interencheres.com/commissaire-priseur/" in value


class InterencheresPublicCrawler:
    def __init__(self, timeout: int = 25):
        self.client = httpx.Client(
            headers=HEADERS,
            timeout=timeout,
            follow_redirects=True,
        )

    def close(self):
        self.client.close()

    def fetch_text(self, url: str) -> str:
        response = self.client.get(url)
        response.raise_for_status()
        return response.text

    def extract_house_name_from_profile(self, html: str) -> str | None:
        soup = BeautifulSoup(html, "lxml")

        h1 = soup.find("h1")
        if h1:
            text = re.sub(r"\s+", " ", h1.get_text(" ", strip=True)).strip()
            if text:
                return text

        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        if title:
            text = re.sub(r"\s+", " ", title).strip()
            if text:
                return text

        return None

    def _extract_datetime(self, text: str) -> datetime | None:
        match = re.search(
            r"(\d{1,2})\s+([A-Za-zÀ-ÿ]+)\s+(\d{4})\s+à\s+(\d{1,2})h(\d{2})",
            text,
            flags=re.I,
        )
        if not match:
            return None

        day = int(match.group(1))
        month_name = match.group(2).lower()
        year = int(match.group(3))
        hour = int(match.group(4))
        minute = int(match.group(5))

        month = MONTHS.get(month_name)
        if not month:
            return None

        try:
            return datetime(year, month, day, hour, minute)
        except ValueError:
            return None

    def _sale_from_block(
        self,
        block_text: str,
        source_page: str,
        href: str | None,
        results_mode: bool = False,
    ) -> ParsedSale | None:
        block_text = re.sub(r"\s+", " ", block_text).strip()
        if len(block_text) < 30:
            return None

        type_match = re.search(r"\b(Live|Chrono|Catalogue)\b", block_text, flags=re.I)
        sale_type = type_match.group(1).capitalize() if type_match else None

        location_match = re.search(
            r"(\d{4,5})\s+([A-Za-zÀ-ÿ\-\s'’]+)\s*-\s*([A-Za-zÀ-ÿ\-\s'’]+)",
            block_text,
            flags=re.I,
        )
        postal_code = city = country = None
        if location_match:
            postal_code = location_match.group(1).strip()
            city = re.sub(r"\s+", " ", location_match.group(2)).strip()
            country = re.sub(r"\s+", " ", location_match.group(3)).strip()

        title = None
        house_name = None

        if type_match:
            after_type = block_text.split(type_match.group(0), 1)[1].strip()
            if location_match:
                prefix = block_text[:location_match.start()].strip()
                parts = [p.strip() for p in re.split(r"\s{2,}", prefix) if p.strip()]
                if len(parts) >= 2:
                    title = parts[-2]
                    house_name = parts[-1]

            if not title:
                title = re.split(
                    r"S'inscrire à la vente|Accéder au direct|Voir les lots|Voir les résultats|\d{4,5}\s",
                    after_type,
                    maxsplit=1,
                )[0].strip()

        if not title or len(title) < 4:
            return None

        if not house_name:
            house_name = "Maison de ventes inconnue"

        if results_mode or "Voir les résultats" in block_text:
            status = "Terminée"
        elif "En cours" in block_text:
            status = "En cours"
        else:
            status = "À venir"

        results_available = results_mode or ("Voir les résultats" in block_text)
        result_summary = (
            "Résultats disponibles publiquement"
            if results_available
            else "Résultats non publiés ou non détectés"
        )

        external_url = urljoin(BASE_URL, href) if href else source_page

        return ParsedSale(
            external_url=external_url,
            title=title,
            house_name=house_name,
            type=sale_type,
            status=status,
            start_at=self._extract_datetime(block_text),
            city=city,
            postal_code=postal_code,
            country=country,
            source_page=source_page,
            results_available=results_available,
            result_summary=result_summary,
        )

    def parse_contextual_sales(
        self,
        html: str,
        source_page: str,
        results_mode: bool = False,
    ) -> list[ParsedSale]:
        soup = BeautifulSoup(html, "lxml")
        sales: list[ParsedSale] = []

        anchors = soup.find_all("a", href=True)
        seen_blocks = set()

        for a in anchors:
            label = " ".join(a.stripped_strings)
            href = a.get("href", "")

            if not label:
                continue

            if (
                "Voir les lots" in label
                or "Accéder au direct" in label
                or "Voir les résultats" in label
                or "S'inscrire à la vente" in label
            ):
                parent = a
                for _ in range(4):
                    if parent.parent:
                        parent = parent.parent

                block_text = parent.get_text(" ", strip=True)
                block_text = re.sub(r"\s+", " ", block_text).strip()

                if block_text in seen_blocks:
                    continue
                seen_blocks.add(block_text)

                sale = self._sale_from_block(
                    block_text=block_text,
                    source_page=source_page,
                    href=href,
                    results_mode=results_mode,
                )
                if sale:
                    sales.append(sale)

        if not sales:
            text = soup.get_text("\n", strip=True)
            chunks = re.split(r"(?=\b(?:Live|Chrono|Catalogue)\b)", text)
            for chunk in chunks:
                sale = self._sale_from_block(
                    block_text=chunk,
                    source_page=source_page,
                    href=None,
                    results_mode=results_mode,
                )
                if sale:
                    sales.append(sale)

        dedup = {}
        for sale in sales:
            key = (sale.external_url, sale.title, sale.house_name)
            dedup[key] = sale

        return list(dedup.values())

    def fetch_and_parse_sale_lots(
        self,
        sale_url: str,
        results_available: bool = False,
    ) -> list[ParsedLot]:
        html = self.fetch_text(sale_url)
        soup = BeautifulSoup(html, "lxml")
        lots: list[ParsedLot] = []
        seen = set()

        for node in soup.find_all(["a", "article", "div", "li"]):
            text = node.get_text(" ", strip=True)
            if len(text) < 8:
                continue

            has_marker = any(
                marker in text
                for marker in ["Estimation", "Mise à prix", "Enchère en cours", "Lot "]
            )
            if not has_marker:
                continue

            lot_match = re.search(
                r"\bLot\s*(?:n[o°.]?\s*)?(\d+[A-Za-z\-]*)\b",
                text,
                flags=re.I,
            )
            lot_number = lot_match.group(1) if lot_match else None

            title = re.split(
                r"Estimation|Mise à prix|Enchère en cours|Proposé par|Live|Chrono|Catalogue",
                text,
            )[0].strip()

            if lot_number:
                title = re.sub(
                    r"^Lot\s*(?:n[o°.]?\s*)?" + re.escape(lot_number) + r"\s*",
                    "",
                    title,
                    flags=re.I,
                ).strip()

            if len(title) < 3:
                continue

            href = node.get("href") if hasattr(node, "get") else None
            img = node.find("img") if hasattr(node, "find") else None

            public_url = urljoin(BASE_URL, href) if href else None
            image_url = urljoin(BASE_URL, img.get("src")) if img and img.get("src") else None

            key = (lot_number, title[:120], public_url)
            if key in seen:
                continue
            seen.add(key)

            result_status = None
            result_amount = None

            if results_available:
                if "Adjugé" in text:
                    result_status = "Adjugé"
                elif "Invendu" in text:
                    result_status = "Invendu"

                amount_match = re.search(r"(\d[\d\s\u202f]*\s?€)", text)
                if amount_match:
                    result_amount = amount_match.group(1).strip()

            lots.append(
                ParsedLot(
                    lot_number=lot_number,
                    title=title,
                    public_url=public_url,
                    image_url=image_url,
                    result_status=result_status,
                    result_amount=result_amount,
                )
            )

        return lots

    def refresh_house(self, db: Session, house_name_or_url: str):
        raw_value = (house_name_or_url or "").strip()
        if not raw_value:
            raise ValueError("Merci de saisir un nom de maison de vente ou une URL Interencheres.")

        target_house = raw_value

        if looks_like_interencheres_url(raw_value):
            if "interencheres.com" not in raw_value.lower():
                raise ValueError("URL non supportée. Merci d'utiliser une URL Interencheres.")
            html = self.fetch_text(raw_value)

            if is_profile_url(raw_value):
                extracted = self.extract_house_name_from_profile(html)
                if not extracted:
                    raise ValueError("Impossible d'extraire le nom de la maison depuis l'URL fournie.")
                target_house = extracted
            else:
                raise ValueError("Pour l'instant, colle une URL de profil commissaire-priseur Interencheres.")

        norm_target = normalize_text(target_house)

        candidate_sales: list[ParsedSale] = []

        html_calendar = self.fetch_text(CALENDAR_URL)
        html_results = self.fetch_text(RESULTS_URL)

        for sale in self.parse_contextual_sales(html_calendar, CALENDAR_URL, results_mode=False):
            sale_norm = normalize_text(sale.house_name)
            if norm_target in sale_norm or sale_norm in norm_target:
                candidate_sales.append(sale)

        for sale in self.parse_contextual_sales(html_results, RESULTS_URL, results_mode=True):
            sale_norm = normalize_text(sale.house_name)
            if norm_target in sale_norm or sale_norm in norm_target:
                candidate_sales.append(sale)

        if not candidate_sales:
            raise ValueError(
                f"Aucune vente publique trouvée pour « {target_house} ». "
                "Essaie une URL de profil Interencheres ou une autre écriture du nom."
            )

        created_sales = updated_sales = created_lots = updated_lots = 0

        for parsed_sale in candidate_sales:
            db_sale = (
                db.query(Sale)
                .filter(
                    Sale.external_url == parsed_sale.external_url,
                    Sale.title == parsed_sale.title,
                    Sale.house_name == parsed_sale.house_name,
                )
                .first()
            )

            if not db_sale:
                db_sale = Sale(
                    external_url=parsed_sale.external_url,
                    title=parsed_sale.title,
                    house_name=parsed_sale.house_name,
                    type=parsed_sale.type,
                    status=parsed_sale.status,
                    start_at=parsed_sale.start_at,
                    city=parsed_sale.city,
                    postal_code=parsed_sale.postal_code,
                    country=parsed_sale.country,
                    source_page=parsed_sale.source_page,
                    results_available=parsed_sale.results_available,
                    result_summary=parsed_sale.result_summary,
                )
                db.add(db_sale)
                db.flush()
                created_sales += 1
            else:
                db_sale.type = parsed_sale.type
                db_sale.status = parsed_sale.status
                db_sale.start_at = parsed_sale.start_at
                db_sale.city = parsed_sale.city
                db_sale.postal_code = parsed_sale.postal_code
                db_sale.country = parsed_sale.country
                db_sale.results_available = parsed_sale.results_available
                db_sale.result_summary = parsed_sale.result_summary
                db.flush()
                updated_sales += 1

            lot_candidates: list[ParsedLot] = []
            try:
                if db_sale.external_url and db_sale.external_url != db_sale.source_page:
                    lot_candidates = self.fetch_and_parse_sale_lots(
                        db_sale.external_url,
                        results_available=db_sale.results_available,
                    )
            except Exception:
                lot_candidates = []

            for parsed_lot in lot_candidates:
                q = db.query(Lot).filter(Lot.sale_id == db_sale.id)
                if parsed_lot.lot_number:
                    q = q.filter(Lot.lot_number == parsed_lot.lot_number)
                else:
                    q = q.filter(Lot.title == parsed_lot.title)

                db_lot = q.first()

                if not db_lot:
                    db_lot = Lot(
                        sale_id=db_sale.id,
                        lot_number=parsed_lot.lot_number,
                        title=parsed_lot.title,
                        public_url=parsed_lot.public_url,
                        image_url=parsed_lot.image_url,
                        result_status=parsed_lot.result_status,
                        result_amount=parsed_lot.result_amount,
                    )
                    db.add(db_lot)
                    created_lots += 1
                else:
                    db_lot.title = parsed_lot.title
                    db_lot.public_url = parsed_lot.public_url
                    db_lot.image_url = parsed_lot.image_url
