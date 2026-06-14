from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class LotOut(BaseModel):
    id: int
    lot_number: Optional[str] = None
    title: str
    public_url: Optional[str] = None
    image_url: Optional[str] = None
    result_status: Optional[str] = None
    result_amount: Optional[str] = None
    last_seen_at: datetime

    class Config:
        from_attributes = True


class SaleOut(BaseModel):
    id: int
    external_url: str
    title: str
    house_name: str
    type: Optional[str] = None
    status: Optional[str] = None
    start_at: Optional[datetime] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    source_page: Optional[str] = None
    results_available: bool = False
    result_summary: Optional[str] = None
    last_seen_at: datetime

    class Config:
        from_attributes = True


class SaleWithLotsOut(SaleOut):
    lots: List[LotOut] = []


class RefreshResponse(BaseModel):
    created_sales: int
    updated_sales: int
    created_lots: int
    updated_lots: int
    matched_house: str
