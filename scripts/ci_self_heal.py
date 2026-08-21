"""Run the collector loop in CI and optionally close incidents automatically.

The normal scheduler preserves human approval. CI opts into automatic approval
only when AUTO_APPROVE_HEALS=true, making that policy explicit in the workflow.
"""

from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.db.models import Incident  # noqa: E402
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


def main() -> None:
    auto_approve = os.getenv("AUTO_APPROVE_HEALS", "false").casefold() == "true"
    cli = BrightDataCLI()
    narrator = GeminiNarrator()
    summary = ["## SentinelScrape self-heal run", "", f"- Automatic approval: `{auto_approve}`"]

    first_failures = run_once(cli)
    if first_failures:
        summary.extend(f"- Collector failure: `{failure}`" for failure in first_failures)
        write_summary(summary)
        raise SystemExit(f"Collector run failed: {'; '.join(first_failures)}")
    incidents = open_incidents()
    summary.append(f"- Open incidents detected: `{len(incidents)}`")

    for incident in incidents:
        if not auto_approve:
            summary.append(f"- Incident `{incident.id}` remains open; approval is disabled.")
            continue
        with SessionLocal() as db:
            heal_incident(db=db, incident_id=incident.id, cli=cli, narrator=narrator, approve=True)
        summary.append(f"- Incident `{incident.id}` healed, approved, and narrated.")

    second_failures = run_once(cli)
    if second_failures:
        summary.extend(f"- Re-run failure: `{failure}`" for failure in second_failures)
        write_summary(summary)
        raise SystemExit(f"Collector re-run failed: {'; '.join(second_failures)}")
    remaining = open_incidents()
    summary.append(f"- Open incidents after re-run: `{len(remaining)}`")
    write_summary(summary)
    if remaining:
        raise SystemExit(f"{len(remaining)} incident(s) remain open after the CI self-heal loop")


if __name__ == "__main__":
    main()
