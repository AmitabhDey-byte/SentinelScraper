"""Collector polling, diffing, persistence, and approved healing workflow."""

from argparse import ArgumentParser
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Collector, Incident, PriceHistory, Product, Run
from app.db.session import SessionLocal
from app.orchestration.brightdata import BrightDataCLI
from app.services.diff_detector import SnapshotDiff, compare_snapshots, normalize_snapshot
from app.services.narration import GeminiNarrator


OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output"
INLINE_SNAPSHOT_PREFIX = "snapshot:"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _value(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None and (not isinstance(value, str) or value.strip()):
            return value
    return None


def _price(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"[-+]?\d[\d,]*(?:\.\d+)?", str(value))
    return float(match.group(0).replace(",", "")) if match else None


def _rows(snapshot: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in normalize_snapshot(snapshot)]


def _load_json(path: str | None) -> Any:
    if not path:
        return None
    if path.startswith(INLINE_SNAPSHOT_PREFIX):
        return json.loads(path.removeprefix(INLINE_SNAPSHOT_PREFIX))
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = Path(__file__).resolve().parents[2] / candidate
    return json.loads(candidate.read_text(encoding="utf-8"))


def _latest_successful_run(db: Session, collector: Collector) -> Run | None:
    return db.scalar(
        select(Run)
        .where(Run.collector_id_fk == collector.id, Run.status == "success")
        .order_by(Run.run_at.desc())
        .limit(1)
    )


def _upsert_products(db: Session, collector: Collector, snapshot: Any, observed_at: datetime) -> None:
    for row in _rows(snapshot):
        name = _value(row, "title", "product_title", "name")
        listing_url = _value(row, "listing_url", "product_url", "url", "link")
        if not name and not listing_url:
            continue
        name = str(name or listing_url)
        external_key = str(listing_url or f"{collector.collector_id}:{name}")
        product = db.scalar(
            select(Product).where(
                Product.collector_id_fk == collector.id,
                Product.external_key == external_key,
            )
        )
        if product is None:
            product = Product(
                collector_id_fk=collector.id,
                external_key=external_key,
                name=name,
                image_url=_value(row, "image_url", "product_image_url", "image"),
                last_seen_at=observed_at,
            )
            db.add(product)
            db.flush()
        else:
            product.name = name
            product.image_url = _value(row, "image_url", "product_image_url", "image") or product.image_url
            product.last_seen_at = observed_at

        db.add(
            PriceHistory(
                product_id_fk=product.id,
                price=_price(_value(row, "price", "current_price")),
                stock_status=_value(row, "stock_status", "availability", "stock", "availability_status"),
                observed_at=observed_at,
            )
        )


def _create_incident_if_new(db: Session, collector: Collector, diff: SnapshotDiff, detected_at: datetime) -> Incident | None:
    if not diff.dropped_fields:
        return None
    open_incident = db.scalar(
        select(Incident)
        .where(Incident.collector_id_fk == collector.id, Incident.healed_at.is_(None))
        .order_by(Incident.detected_at.desc())
        .limit(1)
    )
    if open_incident:
        return open_incident
    incident = Incident(
        collector_id_fk=collector.id,
        detected_at=detected_at,
        dropped_fields=diff.dropped_fields,
        recovered_fields=diff.recovered_fields,
        rows_prev=diff.rows_prev,
        rows_curr=diff.rows_curr,
        narration_source=None,
    )
    db.add(incident)
    return incident


def run_collector(db: Session, collector: Collector, cli: BrightDataCLI, output_dir: Path = OUTPUT_DIR) -> Run:
    """Run one collector, persist its snapshot, and open an incident if needed."""

    started_at = _now()
    output_path = output_dir / f"{collector.collector_id}_{started_at.strftime('%Y%m%dT%H%M%SZ')}.json"
    previous_run = _latest_successful_run(db, collector)
    try:
        cli.run(collector.collector_id, _collector_url(collector), output_path)
        snapshot = json.loads(output_path.read_text(encoding="utf-8"))
        rows = _rows(snapshot)
        run = Run(
            collector_id_fk=collector.id,
            run_at=started_at,
            row_count=len(rows),
            # Keep the baseline in Neon as well as on ephemeral worker disk so
            # the next Render or GitHub Actions run can still perform its diff.
            raw_json_ref=f"{INLINE_SNAPSHOT_PREFIX}{json.dumps(snapshot, separators=(',', ':'))}",
            status="success",
        )
        db.add(run)
        db.flush()

        if previous_run and previous_run.raw_json_ref:
            previous_snapshot = _load_json(previous_run.raw_json_ref)
            diff = compare_snapshots(previous_snapshot, snapshot)
            _create_incident_if_new(db, collector, diff, started_at)

        _upsert_products(db, collector, snapshot, started_at)
        db.commit()
        return run
    except Exception:
        db.rollback()
        failed_run = Run(
            collector_id_fk=collector.id,
            run_at=started_at,
            row_count=0,
            raw_json_ref=str(output_path) if output_path.exists() else None,
            status="failed",
        )
        db.add(failed_run)
        db.commit()
        raise


def _collector_url(collector: Collector) -> str:
    """Resolve the configured URL from the tracked site registry."""

    from app.sites import SITES

    for site in SITES.values():
        if site["name"].casefold() == collector.site_name.casefold():
            return site["url"]
    raise ValueError(f"No tracked URL configured for site {collector.site_name}")


def heal_incident(
    db: Session,
    incident_id: int,
    cli: BrightDataCLI,
    narrator: GeminiNarrator,
    *,
    approve: bool = False,
    output_dir: Path = OUTPUT_DIR,
) -> Incident:
    """Propose a Bright Data heal and optionally approve/commit it.

    Approval is opt-in. Without ``approve=True`` the healed output is written
    for inspection, but the incident remains open and is not narrated as healed.
    """

    incident = db.get(Incident, incident_id)
    if incident is None:
        raise ValueError(f"Incident {incident_id} does not exist")
    collector = db.get(Collector, incident.collector_id_fk)
    if collector is None:
        raise ValueError(f"Collector for incident {incident_id} does not exist")

    healed_at = _now()
    output_path = output_dir / f"{collector.collector_id}_heal_{incident.id}_{healed_at.strftime('%Y%m%dT%H%M%SZ')}.json"
    hint = (
        f"The extraction fields {', '.join(incident.dropped_fields)} dropped below 20% completeness. "
        "Restore the requested listing fields and preserve product title, price, stock status, "
        "seller or brand, rating, product image URL, and listing URL."
    )
    cli.heal(collector.collector_id, _collector_url(collector), hint, output_path)
    healed_snapshot = json.loads(output_path.read_text(encoding="utf-8"))
    previous_run = _latest_successful_run(db, collector)
    previous_snapshot = _load_json(previous_run.raw_json_ref) if previous_run and previous_run.raw_json_ref else []
    recovery_diff = compare_snapshots(previous_snapshot, healed_snapshot)

    if not approve:
        return incident

    recovery_fields = sorted(set(incident.dropped_fields) & set(recovery_diff.recovered_fields))
    if not recovery_fields:
        raise ValueError("Bright Data heal did not recover any dropped field; approval was not recorded")

    cli.approve(collector.collector_id)

    combined_diff = SnapshotDiff(
        rows_prev=incident.rows_prev,
        rows_curr=len(_rows(healed_snapshot)),
        dropped_fields=incident.dropped_fields,
        recovered_fields=recovery_fields,
        previous_completeness={},
        current_completeness={},
    )
    narration = narrator.narrate(site_name=collector.site_name, diff=combined_diff)
    incident.recovered_fields = recovery_fields
    incident.rows_curr = combined_diff.rows_curr
    incident.healed_at = healed_at
    incident.narration_text = narration.report
    incident.narration_source = narration.narration_source
    _upsert_products(db, collector, healed_snapshot, healed_at)
    db.commit()
    return incident


def run_once(cli: BrightDataCLI | None = None) -> list[str]:
    cli = cli or BrightDataCLI()
    failures: list[str] = []
    with SessionLocal() as db:
        collectors = db.scalars(select(Collector).order_by(Collector.site_name)).all()
        if not collectors:
            return ["No collectors are registered. Run scripts/bootstrap_collectors.py first."]
        for collector in collectors:
            try:
                run_collector(db, collector, cli)
            except Exception as exc:
                print(f"[scheduler] {collector.site_name}: failed: {exc}")
                failures.append(f"{collector.site_name}: {exc}")
    return failures


def main() -> None:
    parser = ArgumentParser(description="Run SentinelScrape collectors and healing operations")
    parser.add_argument("--once", action="store_true", help="Run one polling cycle and exit")
    parser.add_argument("--heal", type=int, metavar="INCIDENT_ID", help="Run Bright Data healing for an incident")
    parser.add_argument("--approve", action="store_true", help="Approve the proposed Bright Data heal")
    args = parser.parse_args()

    if args.heal is not None:
        with SessionLocal() as db:
            heal_incident(db, args.heal, BrightDataCLI(), GeminiNarrator(), approve=args.approve)
        print(f"[scheduler] heal proposal completed for incident {args.heal}; approved={args.approve}")
        return

    if args.once:
        run_once()
        return

    interval_seconds = settings.scheduler_interval_minutes * 60
    while True:
        run_once()
        time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
