"""Create Bright Data collectors for the tracked SentinelScrape sites."""

from pathlib import Path
import sys

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db.models import Collector  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.orchestration.brightdata import BrightDataCLI  # noqa: E402
from app.sites import FIELD_DESCRIPTION, SITES  # noqa: E402


def main() -> None:
    cli = BrightDataCLI()
    failures: list[str] = []
    registered = 0
    for slug, site in SITES.items():
        with SessionLocal() as db:
            existing = db.scalar(select(Collector).where(Collector.site_name == site["name"]))
        if existing:
            print(f"{site['name']}: already registered as {existing.collector_id}")
            registered += 1
            continue
        try:
            collector_id = cli.create(site["url"], FIELD_DESCRIPTION, f"sentinelscrape-{slug}-laptops")
        except Exception as exc:
            failures.append(f"{site['name']}: {exc}")
            print(f"{site['name']}: failed — {exc}", file=sys.stderr)
            continue
        try:
            with SessionLocal() as db:
                db.add(Collector(collector_id=collector_id, site_name=site["name"], category="laptops"))
                db.commit()
            registered += 1
            print(f"{site['name']}: registered {collector_id}")
        except Exception as exc:
            failures.append(f"{site['name']}: database save failed: {exc}")
            print(f"{site['name']}: database save failed — {exc}", file=sys.stderr)

    if failures:
        print("Collector bootstrap warnings:\n" + "\n".join(failures), file=sys.stderr)
    if not registered:
        raise SystemExit("No Bright Data collectors could be registered.")


if __name__ == "__main__":
    main()
