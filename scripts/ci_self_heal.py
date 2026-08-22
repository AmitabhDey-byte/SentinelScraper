"""Run the collector loop in CI or a hosted cron job."""

from datetime import datetime, timezone
from pathlib import Path
import os
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.db.models import Incident, Operation  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.orchestration.brightdata import BrightDataCLI  # noqa: E402
from app.orchestration.scheduler import heal_incident, run_once  # noqa: E402
from app.services.narration import GeminiNarrator  # noqa: E402


def open_incidents():
    with SessionLocal() as db:
        return db.scalars(
            select(Incident).where(Incident.healed_at.is_(None)).order_by(Incident.detected_at)
        ).all()


def write_summary(lines: list[str]) -> None:
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        Path(summary_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def operation_event(operation_id: str, message: str, *, status: str | None = None, error: str | None = None) -> None:
    with SessionLocal() as db:
        operation = db.get(Operation, operation_id)
        if operation is None:
            return
        operation.events = [*operation.events, {"at": datetime.now(timezone.utc).isoformat(), "message": message}]
        if status:
            operation.status = status
            operation.completed_at = datetime.now(timezone.utc)
        if error:
            operation.error = error
        db.commit()


def start_operation() -> str:
    operation_id = str(uuid4())
    with SessionLocal() as db:
        db.add(
            Operation(
                id=operation_id,
                kind="auto_heal",
                status="running",
                events=[{"at": datetime.now(timezone.utc).isoformat(), "message": "Scheduled self-heal cycle started."}],
            )
        )
        db.commit()
    return operation_id


def main() -> None:
    auto_approve = os.getenv("AUTO_APPROVE_HEALS", "false").casefold() == "true"
    cli = BrightDataCLI()
    narrator = GeminiNarrator()
    summary = ["## SentinelScrape self-heal run", "", f"- Automatic approval: `{auto_approve}`"]
    operation_id = start_operation()

    first_failures = run_once(cli)
    if first_failures:
        summary.extend(f"- Collector failure: `{failure}`" for failure in first_failures)
        write_summary(summary)
        error = "; ".join(first_failures)
        operation_event(operation_id, f"Collector run failed: {error}", status="failed", error=error)
        raise SystemExit(f"Collector run failed: {error}")
    incidents = open_incidents()
    summary.append(f"- Open incidents detected: `{len(incidents)}`")
    operation_event(operation_id, f"First scan complete: {len(incidents)} open incident(s) detected.")

    for incident in incidents:
        if not auto_approve:
            summary.append(f"- Incident `{incident.id}` remains open; approval is disabled.")
            operation_event(operation_id, f"Incident {incident.id} awaits human approval.")
            continue
        with SessionLocal() as db:
            heal_incident(db=db, incident_id=incident.id, cli=cli, narrator=narrator, approve=True)
        summary.append(f"- Incident `{incident.id}` healed, approved, and narrated.")
        operation_event(operation_id, f"Incident {incident.id} healed, approved, and narrated.")

    second_failures = run_once(cli)
    if second_failures:
        summary.extend(f"- Re-run failure: `{failure}`" for failure in second_failures)
        write_summary(summary)
        error = "; ".join(second_failures)
        operation_event(operation_id, f"Verification run failed: {error}", status="failed", error=error)
        raise SystemExit(f"Collector re-run failed: {error}")
    remaining = open_incidents()
    summary.append(f"- Open incidents after re-run: `{len(remaining)}`")
    write_summary(summary)
    if remaining:
        operation_event(operation_id, f"Verification complete: {len(remaining)} incident(s) still open.", status="failed", error="Verification left open incidents.")
        raise SystemExit(f"{len(remaining)} incident(s) remain open after the CI self-heal loop")
    operation_event(operation_id, "Verification complete: all collectors are healthy.", status="completed")


if __name__ == "__main__":
    main()
