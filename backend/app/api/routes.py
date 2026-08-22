"""Dashboard API routes."""

from collections.abc import Sequence

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from datetime import datetime, timezone
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
    MarketInsightResponse,
    ProfileResponse,
    OperationEventResponse,
    OperationResponse,
)
from app.api.auth import current_user_id
from app.db.models import Collector, Favorite, Incident, Operation, PriceHistory, Product
from app.db.session import SessionLocal, get_db
from app.orchestration.brightdata import BrightDataCLI
from app.orchestration.scheduler import heal_incident, run_collector
from app.services.narration import GeminiNarrator
from app.services.search_agent import KeywordResearchAgent
from app.services.docs_rag import SitemapRag
from app.services.market_insight import MarketInsightNarrator


router = APIRouter()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _operation_response(operation: Operation) -> OperationResponse:
    events = [OperationEventResponse.model_validate(event) for event in operation.events]
    return OperationResponse(
        id=operation.id,
        kind=operation.kind,
        status=operation.status,
        incident_id=operation.incident_id_fk,
        started_at=operation.started_at,
        completed_at=operation.completed_at,
        events=events,
        error=operation.error,
    )


def _record_event(operation: Operation, message: str) -> None:
    operation.events = [*operation.events, {"at": _now().isoformat(), "message": message}]


def _finish_operation(operation_id: str, *, status_value: str, error: str | None = None) -> None:
    with SessionLocal() as db:
        operation = db.get(Operation, operation_id)
        if operation is None:
            return
        operation.status = status_value
        operation.error = error
        operation.completed_at = _now()
        _record_event(operation, "Operation completed." if status_value == "completed" else "Operation stopped with an error.")
        db.commit()


def _run_scan_operation(operation_id: str) -> None:
    cli = BrightDataCLI()
    failures: list[str] = []
    try:
        with SessionLocal() as db:
            operation = db.get(Operation, operation_id)
            if operation is None:
                return
            operation.status = "running"
            _record_event(operation, "Collector scan started through Bright Data Scraper Studio.")
            db.commit()
            collectors = db.scalars(select(Collector).order_by(Collector.site_name)).all()

        for collector_id in [collector.id for collector in collectors]:
            with SessionLocal() as db:
                operation = db.get(Operation, operation_id)
                collector = db.get(Collector, collector_id)
                if operation is None or collector is None:
                    continue
                _record_event(operation, f"Running {collector.site_name} collector.")
                db.commit()
                try:
                    run = run_collector(db, collector, cli)
                    _record_event(operation, f"{collector.site_name} returned {run.row_count} listing row(s); completeness checked.")
                    db.commit()
                except Exception as exc:
                    failures.append(f"{collector.site_name}: {exc}")
                    _record_event(operation, f"{collector.site_name} could not complete: {exc}")
                    db.commit()
        _finish_operation(operation_id, status_value="completed" if not failures else "completed_with_errors", error="; ".join(failures) or None)
    except Exception as exc:  # pragma: no cover - defensive task boundary
        _finish_operation(operation_id, status_value="failed", error=str(exc))


def _run_heal_operation(operation_id: str, incident_id: int, approve: bool) -> None:
    try:
        with SessionLocal() as db:
            operation = db.get(Operation, operation_id)
            if operation is None:
                return
            operation.status = "running"
            _record_event(operation, "Requesting Bright Data AI healing proposal." if not approve else "Approving Bright Data heal and verifying recovery.")
            db.commit()
            healed = heal_incident(db, incident_id, BrightDataCLI(), GeminiNarrator(), approve=approve)
            if approve:
                collector = db.get(Collector, healed.collector_id_fk)
                if collector is not None:
                    rerun = run_collector(db, collector, BrightDataCLI())
                    _record_event(operation, f"Verification re-run completed with {rerun.row_count} listing row(s).")
            _record_event(operation, "Heal proposal saved for review." if not approve else "Heal approved, recovered fields recorded, and Gemini narration attached.")
            db.commit()
        _finish_operation(operation_id, status_value="completed")
    except Exception as exc:
        _finish_operation(operation_id, status_value="failed", error=str(exc))


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


def _product_response(product: Product) -> ProductResponse:
    latest = _latest_history(product.price_history)
    return ProductResponse(
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
    response = [_product_response(product) for product in products]
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


def _queue_operation(
    *,
    db: Session,
    background_tasks: BackgroundTasks,
    kind: str,
    incident_id: int | None = None,
    task: str,
) -> OperationResponse:
    from uuid import uuid4

    operation = Operation(
        id=str(uuid4()),
        kind=kind,
        status="queued",
        incident_id_fk=incident_id,
        events=[{"at": _now().isoformat(), "message": "Operation queued."}],
    )
    db.add(operation)
    db.commit()
    db.refresh(operation)
    if task == "scan":
        background_tasks.add_task(_run_scan_operation, operation.id)
    elif task == "heal":
        assert incident_id is not None
        background_tasks.add_task(_run_heal_operation, operation.id, incident_id, False)
    else:
        assert incident_id is not None
        background_tasks.add_task(_run_heal_operation, operation.id, incident_id, True)
    return _operation_response(operation)


@router.post("/operations/scan", response_model=OperationResponse, status_code=status.HTTP_202_ACCEPTED)
def scan_network(
    background_tasks: BackgroundTasks,
    _: str = Depends(current_user_id),
    db: Session = Depends(get_db),
) -> OperationResponse:
    """Queue an authenticated Bright Data run for every registered collector."""

    return _queue_operation(db=db, background_tasks=background_tasks, kind="scan", task="scan")


@router.post("/operations/incidents/{incident_id}/heal", response_model=OperationResponse, status_code=status.HTTP_202_ACCEPTED)
def propose_heal(
    incident_id: int,
    background_tasks: BackgroundTasks,
    _: str = Depends(current_user_id),
    db: Session = Depends(get_db),
) -> OperationResponse:
    if db.get(Incident, incident_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return _queue_operation(
        db=db, background_tasks=background_tasks, kind="heal_proposal", incident_id=incident_id, task="heal"
    )


@router.post("/operations/incidents/{incident_id}/approve", response_model=OperationResponse, status_code=status.HTTP_202_ACCEPTED)
def approve_heal(
    incident_id: int,
    background_tasks: BackgroundTasks,
    _: str = Depends(current_user_id),
    db: Session = Depends(get_db),
) -> OperationResponse:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    if incident.healed_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Incident is already healed")
    return _queue_operation(
        db=db, background_tasks=background_tasks, kind="approve_and_verify", incident_id=incident_id, task="approve"
    )


@router.get("/operations/latest", response_model=OperationResponse | None)
def latest_operation(db: Session = Depends(get_db)) -> OperationResponse | None:
    operation = db.scalar(select(Operation).order_by(Operation.started_at.desc()).limit(1))
    return _operation_response(operation) if operation else None


@router.get("/operations/{operation_id}", response_model=OperationResponse)
def get_operation(
    operation_id: str,
    db: Session = Depends(get_db),
) -> OperationResponse:
    operation = db.get(Operation, operation_id)
    if operation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operation not found")
    return _operation_response(operation)


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


@router.get("/me/profile", response_model=ProfileResponse)
def profile(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    favorites_count = db.scalar(select(func.count(Favorite.id)).where(Favorite.user_id == user_id)) or 0
    return ProfileResponse(
        user_id=user_id,
        favorites_count=favorites_count,
        auth_mode="operator" if user_id == "operator" else "local-demo",
    )


@router.get("/me/favorites", response_model=list[ProductResponse])
def list_favorites(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
) -> list[ProductResponse]:
    products = db.scalars(
        select(Product)
        .join(Favorite, Favorite.product_id_fk == Product.id)
        .where(Favorite.user_id == user_id)
        .options(selectinload(Product.collector), selectinload(Product.price_history))
        .order_by(Favorite.created_at.desc())
    ).unique().all()
    return [_product_response(product) for product in products]


@router.put("/me/favorites/{product_id}", response_model=ProfileResponse)
def save_favorite(
    product_id: int,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    if db.get(Product, product_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    existing = db.scalar(
        select(Favorite).where(Favorite.user_id == user_id, Favorite.product_id_fk == product_id)
    )
    if existing is None:
        db.add(Favorite(user_id=user_id, product_id_fk=product_id))
        db.commit()
    return profile(user_id=user_id, db=db)


@router.delete("/me/favorites/{product_id}", response_model=ProfileResponse)
def remove_favorite(
    product_id: int,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    favorite = db.scalar(
        select(Favorite).where(Favorite.user_id == user_id, Favorite.product_id_fk == product_id)
    )
    if favorite is not None:
        db.delete(favorite)
        db.commit()
    return profile(user_id=user_id, db=db)


@router.get("/insights/market", response_model=MarketInsightResponse)
def market_insight(db: Session = Depends(get_db)) -> MarketInsightResponse:
    incidents = db.scalars(select(Incident)).all()
    open_incidents = sum(incident.healed_at is None for incident in incidents)
    products = db.scalars(select(Product).options(selectinload(Product.price_history))).unique().all()
    drops = 0
    restocks = 0
    for product in products:
        history = sorted(product.price_history, key=lambda item: item.observed_at)
        if len(history) < 2:
            continue
        previous, current = history[-2:]
        if previous.price is not None and current.price is not None and current.price < previous.price:
            drops += 1
        if not _is_in_stock(previous.stock_status) and _is_in_stock(current.stock_status):
            restocks += 1
    result = MarketInsightNarrator().create(
        drops=drops, restocks=restocks, open_incidents=open_incidents
    )
    return MarketInsightResponse(**result.insight.model_dump(), source=result.source)
