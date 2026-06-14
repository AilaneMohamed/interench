from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base


class Sale(Base):
    __tablename__ = 'sales'

    id = Column(Integer, primary_key=True, index=True)
    external_url = Column(String, nullable=False, unique=False, index=True)
    title = Column(String, nullable=False, index=True)
    house_name = Column(String, nullable=False, index=True)
    type = Column(String, nullable=True, index=True)
    status = Column(String, nullable=True, index=True)
    start_at = Column(DateTime, nullable=True, index=True)
    city = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    country = Column(String, nullable=True)
    source_page = Column(String, nullable=True)
    results_available = Column(Boolean, default=False)
    result_summary = Column(String, nullable=True)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    lots = relationship('Lot', back_populates='sale', cascade='all, delete-orphan')


class Lot(Base):
    __tablename__ = 'lots'
    __table_args__ = (UniqueConstraint('sale_id', 'lot_number', 'title', name='uq_sale_lot'),)

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey('sales.id'), nullable=False, index=True)
    lot_number = Column(String, nullable=True, index=True)
    title = Column(Text, nullable=False)
    public_url = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    result_status = Column(String, nullable=True)
    result_amount = Column(String, nullable=True)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    sale = relationship('Sale', back_populates='lots')
