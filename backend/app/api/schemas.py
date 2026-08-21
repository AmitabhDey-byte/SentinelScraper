"""Public API response models."""

from datetime import datetime

from pydantic import BaseModel


class PricePoint(BaseModel):
    observed_at: datetime
    price: float | None


class ProductResponse(BaseModel):
    id: int
    collector_id: str
    site_name: str
    name: str
    image_url: str | None
    listing_url: str
    price: float | None
    stock_status: str | None
    price_history: list[PricePoint]


class IncidentResponse(BaseModel):
    id: int
    collector_id: str
    site_name: str
    detected_at: datetime
    dropped_fields: list[str]
    recovered_fields: list[str]
    rows_prev: int
    rows_curr: int
    healed_at: datetime | None
    narration_text: str | None
    narration_source: str | None
    status: str


class AlertResponse(BaseModel):
    type: str
    product_id: int
    collector_id: str
    site_name: str
    product_name: str
    image_url: str | None
    previous_value: float | None
    current_value: float | None
    delta: float | None
    observed_at: datetime
    stock_status: str | None


class CollectorStatusResponse(BaseModel):
    collector_id: str
    site_name: str
    category: str
    status: str
    last_run_at: datetime | None
    last_run_status: str | None
    row_count: int | None
    open_incidents: int
