"""Run the weekly competitive intelligence diff."""

from argparse import ArgumentParser
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings  # noqa: E402
from app.services.competitive_intel import CompetitiveIntelMonitor, notify_webhook, parse_sources  # noqa: E402


def main() -> None:
    parser = ArgumentParser(description="Diff competitor changelog pages through Bright Data")
    parser.add_argument("--output", default="backend/output/competitive-intel")
    args = parser.parse_args()
    sources = parse_sources(settings.competitor_sources_json)
    if not sources:
        raise SystemExit("Set COMPETITOR_SOURCES_JSON to a JSON array of {name,url} sources")
    report = CompetitiveIntelMonitor().run(sources, Path(args.output))
    if settings.slack_webhook_url:
        notify_webhook(settings.slack_webhook_url, report, provider="slack")
    if settings.discord_webhook_url:
        notify_webhook(settings.discord_webhook_url, report, provider="discord")
    print(report)


if __name__ == "__main__":
    main()
