from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    article: Mapped[str | None] = mapped_column(String(255), index=True)
    supplier_article: Mapped[str | None] = mapped_column(String(255), index=True)
    barcode: Mapped[str | None] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str | None] = mapped_column(Text)
    brand: Mapped[str | None] = mapped_column(String(255), index=True)
    product_type: Mapped[str | None] = mapped_column(String(255), index=True)

    poles: Mapped[int | None] = mapped_column(Integer)
    nominal_current_a: Mapped[float | None] = mapped_column(Float)
    breaking_capacity_ka: Mapped[float | None] = mapped_column(Float)
    nominal_voltage_v: Mapped[float | None] = mapped_column(Float)
    installation_type: Mapped[str | None] = mapped_column(String(255))

    price_amount: Mapped[int | None] = mapped_column(BigInteger)
    quantity_total: Mapped[int | None] = mapped_column(Integer)
    stores: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    offers: Mapped[list[Any]] = mapped_column(JSON, default=list)
    image_url: Mapped[str | None] = mapped_column(Text)
    product_url: Mapped[str | None] = mapped_column(Text)

    properties_raw: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    has_conflicts: Mapped[bool] = mapped_column(Boolean, default=False)
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    search_text: Mapped[str] = mapped_column(Text, default="")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_seen_sync_id: Mapped[str | None] = mapped_column(String(36), index=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    detail_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
