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
    with SessionLocal() as db:
        for slug, site in SITES.items():
            existing = db.scalar(select(Collector).where(Collector.site_name == site["name"]))
            if existing:
                print(f"{site['name']}: already registered as {existing.collector_id}")
                continue
            try:
                collector_id = cli.create(site["url"], FIELD_DESCRIPTION, f"sentinelscrape-{slug}-laptops")
                db.add(Collector(collector_id=collector_id, site_name=site["name"], category="laptops"))
                db.commit()
                print(f"{site['name']}: registered {collector_id}")
            except Exception as exc:
                db.rollback()
                failures.append(f"{site['name']}: {exc}")
                print(f"{site['name']}: failed — {exc}", file=sys.stderr)

    if failures:
        raise SystemExit("Collector bootstrap completed with failures:\n" + "\n".join(failures))


if __name__ == "__main__":
    main()
