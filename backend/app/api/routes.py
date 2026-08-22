"""Dashboard API routes."""

from collections.abc import Sequence

from fastapi import APIRouter, Depends, Query
from pathlib import Path
from uuid import uuid4
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.schemas import (
    AlertResponse,
    AlertPageResponse,
    CollectorStatusResponse,
    IncidentResponse,
    IncidentPageResponse,
    PricePoint,
    ProductResponse,
    ProductPageResponse,
    RagQueryRequest,
    RagQueryResponse,
    ResearchRequest,
    ResearchResponse,
)
from app.db.models import Collector, Incident, PriceHistory, Product
from app.db.session import get_db
from app.services.search_agent import KeywordResearchAgent
from app.services.docs_rag import SitemapRag


router = APIRouter()


@router.post("/research", response_model=ResearchResponse)
def research(request: ResearchRequest) -> ResearchResponse:
    output_path = Path(__file__).resolve().parents[2] / "output" / "research" / f"{uuid4().hex}.json"
    result = KeywordResearchAgent().research(
        request.keyword,
        output_path,
        country=request.country,
        search_type=request.search_type,
        limit=request.limit,
    )
    return ResearchResponse.model_validate(result)


@router.post("/rag/query", response_model=RagQueryResponse)
def rag_query(request: RagQueryRequest) -> RagQueryResponse:
    rag_root = Path(__file__).resolve().parents[2] / "output" / "rag"
    index_path = rag_root / Path(request.index_path).name
    answer = SitemapRag().answer(index_path, request.question, top_k=request.top_k)
    return RagQueryResponse.model_validate(answer.model_dump())


@router.get("/collectors", response_model=list[CollectorStatusResponse])
def list_collectors(db: Session = Depends(get_db)) -> list[CollectorStatusResponse]:
    collectors = db.scalars(
        select(Collector)
        .options(selectinload(Collector.runs), selectinload(Collector.incidents))
        .order_by(Collector.site_name)
    ).unique().all()
    response: list[CollectorStatusResponse] = []
    for collector in collectors:
        latest_run = max(collector.runs, key=lambda item: item.run_at, default=None)
        open_incidents = sum(incident.healed_at is None for incident in collector.incidents)
        if open_incidents:
            status = "attention"
        elif latest_run is None:
            status = "not_run"
        elif latest_run.status == "success":
            status = "healthy"
        else:
            status = "failed"
        response.append(
            CollectorStatusResponse(
                collector_id=collector.collector_id,
                site_name=collector.site_name,
                category=collector.category,
                status=status,
                last_run_at=latest_run.run_at if latest_run else None,
                last_run_status=latest_run.status if latest_run else None,
                row_count=latest_run.row_count if latest_run else None,
                open_incidents=open_incidents,
            )
        )
    return response


def _latest_history(history: Sequence[PriceHistory]) -> PriceHistory | None:
    return max(history, key=lambda item: item.observed_at, default=None)


def _history_points(history: Sequence[PriceHistory]) -> list[PricePoint]:
    return [
        PricePoint(observed_at=item.observed_at, price=item.price)
        for item in sorted(history, key=lambda item: item.observed_at)
    ]


@router.get("/products", response_model=ProductPageResponse)
def list_products(
    site: str | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=8, ge=1, le=50),
    db: Session = Depends(get_db),
) -> ProductPageResponse:
    count_statement = select(func.count(Product.id)).join(Product.collector)
    if site:
        count_statement = count_statement.where(Collector.site_name.ilike(site))
    if q:
        count_statement = count_statement.where(Product.name.ilike(f"%{q}%"))

    total = db.scalar(count_statement) or 0
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, total_pages)
    statement = (
        select(Product)
        .join(Product.collector)
        .options(selectinload(Product.collector), selectinload(Product.price_history))
        .order_by(Product.last_seen_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if site:
        statement = statement.where(Collector.site_name.ilike(site))
    if q:
        statement = statement.where(Product.name.ilike(f"%{q}%"))

    products = db.scalars(statement).unique().all()
    response: list[ProductResponse] = []
    for product in products:
        latest = _latest_history(product.price_history)
        response.append(
            ProductResponse(
                id=product.id,
                collector_id=product.collector.collector_id,
                site_name=product.collector.site_name,
                name=product.name,
                image_url=product.image_url,
                listing_url=product.external_key,
                price=latest.price if latest else None,
                stock_status=latest.stock_status if latest else None,
                price_history=_history_points(product.price_history),
            )
        )
    return ProductPageResponse(
        items=response,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get("/incidents", response_model=IncidentPageResponse)
def list_incidents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=8, ge=1, le=50),
    db: Session = Depends(get_db),
) -> IncidentPageResponse:
    total = db.scalar(select(func.count(Incident.id))) or 0
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, total_pages)
    statement = (
        select(Incident)
        .options(selectinload(Incident.collector))
        .order_by(Incident.detected_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    incidents = db.scalars(statement).unique().all()
    response = [
        IncidentResponse(
            id=incident.id,
            collector_id=incident.collector.collector_id,
            site_name=incident.collector.site_name,
            detected_at=incident.detected_at,
            dropped_fields=incident.dropped_fields,
            recovered_fields=incident.recovered_fields,
            rows_prev=incident.rows_prev,
            rows_curr=incident.rows_curr,
            healed_at=incident.healed_at,
            narration_text=incident.narration_text,
            narration_source=incident.narration_source,
            status="healed" if incident.healed_at else "open",
        )
        for incident in incidents
    ]
    return IncidentPageResponse(
        items=response,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


def _is_in_stock(status: str | None) -> bool:
    if not status:
        return False
    normalized = status.casefold().replace("-", " ").replace("_", " ")
    unavailable = ("out of stock", "unavailable", "sold out", "not available")
    return not any(term in normalized for term in unavailable)


@router.get("/alerts", response_model=AlertPageResponse)
def list_alerts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=8, ge=1, le=50),
    db: Session = Depends(get_db),
) -> AlertPageResponse:
    products = db.scalars(
        select(Product)
        .options(selectinload(Product.collector), selectinload(Product.price_history))
        .order_by(Product.last_seen_at.desc())
    ).unique().all()

    alerts: list[AlertResponse] = []
    for product in products:
        history = sorted(product.price_history, key=lambda item: item.observed_at)
        if len(history) < 2:
            continue
        previous, current = history[-2:]

        if previous.price is not None and current.price is not None and current.price < previous.price:
            alerts.append(
                AlertResponse(
                    type="price_drop",
                    product_id=product.id,
                    collector_id=product.collector.collector_id,
                    site_name=product.collector.site_name,
                    product_name=product.name,
                    image_url=product.image_url,
                    previous_value=previous.price,
                    current_value=current.price,
                    delta=current.price - previous.price,
                    observed_at=current.observed_at,
                    stock_status=current.stock_status,
                )
            )

        if not _is_in_stock(previous.stock_status) and _is_in_stock(current.stock_status):
            alerts.append(
                AlertResponse(
                    type="restock",
                    product_id=product.id,
                    collector_id=product.collector.collector_id,
                    site_name=product.collector.site_name,
                    product_name=product.name,
                    image_url=product.image_url,
                    previous_value=None,
                    current_value=current.price,
                    delta=None,
                    observed_at=current.observed_at,
                    stock_status=current.stock_status,
                )
            )

    alerts.sort(key=lambda alert: alert.observed_at, reverse=True)
    total = len(alerts)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, total_pages)
    start = (page - 1) * page_size
    return AlertPageResponse(
        items=alerts[start : start + page_size],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
