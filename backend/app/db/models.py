"""Persistent entities for collector runs, products, prices, and incidents."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Collector(Base):
    __tablename__ = "collectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    collector_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    site_name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    runs: Mapped[list["Run"]] = relationship(back_populates="collector", cascade="all, delete-orphan")
    products: Mapped[list["Product"]] = relationship(back_populates="collector", cascade="all, delete-orphan")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="collector", cascade="all, delete-orphan")


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (Index("ix_runs_collector_run_at", "collector_id_fk", "run_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    collector_id_fk: Mapped[int] = mapped_column(ForeignKey("collectors.id", ondelete="CASCADE"), nullable=False)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_json_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    collector: Mapped[Collector] = relationship(back_populates="runs")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (Index("ix_products_collector_external_key", "collector_id_fk", "external_key", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    collector_id_fk: Mapped[int] = mapped_column(ForeignKey("collectors.id", ondelete="CASCADE"), nullable=False)
    external_key: Mapped[str] = mapped_column(String(512), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    collector: Mapped[Collector] = relationship(back_populates="products")
    price_history: Mapped[list["PriceHistory"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    favorites: Mapped[list["Favorite"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (Index("ix_price_history_product_observed_at", "product_id_fk", "observed_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id_fk: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    price: Mapped[float | None] = mapped_column(nullable=True)
    stock_status: Mapped[str | None] = mapped_column(String(128), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    product: Mapped[Product] = relationship(back_populates="price_history")


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (Index("ix_incidents_collector_detected_at", "collector_id_fk", "detected_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    collector_id_fk: Mapped[int] = mapped_column(ForeignKey("collectors.id", ondelete="CASCADE"), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    dropped_fields: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    recovered_fields: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    rows_prev: Mapped[int] = mapped_column(Integer, nullable=False)
    rows_curr: Mapped[int] = mapped_column(Integer, nullable=False)
    healed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    narration_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    narration_source: Mapped[str | None] = mapped_column(String(32), nullable=True)

    collector: Mapped[Collector] = relationship(back_populates="incidents")


class Favorite(Base):
    """A saved product for a local observer or protected operator."""

    __tablename__ = "favorites"
    __table_args__ = (Index("ix_favorites_user_product", "user_id", "product_id_fk", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    product_id_fk: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    product: Mapped[Product] = relationship(back_populates="favorites")


class Operation(Base):
    """Persisted evidence for a user-triggered Bright Data operation."""

    __tablename__ = "operations"
    __table_args__ = (Index("ix_operations_started_at", "started_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kind: Mapped[str] = mapped_column(String(48), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    incident_id_fk: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    events: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=False, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
