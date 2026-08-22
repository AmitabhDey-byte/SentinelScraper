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


class ProductPageResponse(BaseModel):
    items: list[ProductResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


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


class IncidentPageResponse(BaseModel):
    items: list[IncidentResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


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


class AlertPageResponse(BaseModel):
    items: list[AlertResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


class CollectorStatusResponse(BaseModel):
    collector_id: str
    site_name: str
    category: str
    status: str
    last_run_at: datetime | None
    last_run_status: str | None
    row_count: int | None
    open_incidents: int


class ResearchRequest(BaseModel):
    keyword: str
    country: str | None = None
    search_type: str = "shopping"
    limit: int = 10


class ResearchItemResponse(BaseModel):
    title: str
    url: str
    snippet: str
    price: str | None


class ResearchResponse(BaseModel):
    keyword: str
    country: str | None
    search_type: str
    summary: str
    results: list[ResearchItemResponse]
    raw_output: str


class Citation(BaseModel):
    url: str
    title: str


class RagQueryRequest(BaseModel):
    question: str
    index_path: str = "backend/output/rag/index.json"
    top_k: int = 5


class RagQueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
