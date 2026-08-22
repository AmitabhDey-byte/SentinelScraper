"""Weekly competitor-page diffing and webhook delivery."""

from dataclasses import dataclass
from datetime import datetime, timezone
import difflib
import json
from pathlib import Path
import re
from typing import Any
from urllib.request import Request, urlopen

from app.orchestration.brightdata import BrightDataCLI


@dataclass(frozen=True)
class CompetitorSource:
    name: str
    url: str


def parse_sources(raw: str) -> list[CompetitorSource]:
    values = json.loads(raw or "[]")
    return [CompetitorSource(name=item["name"], url=item["url"]) for item in values]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _normalize(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


class CompetitiveIntelMonitor:
    def __init__(self, cli: BrightDataCLI | None = None) -> None:
        self.cli = cli or BrightDataCLI()

    def run(self, sources: list[CompetitorSource], output_dir: Path) -> dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        reports: list[dict[str, Any]] = []
        for source in sources:
            source_dir = output_dir / _slug(source.name)
            source_dir.mkdir(parents=True, exist_ok=True)
            current_path = source_dir / "current.md"
            previous_path = source_dir / "previous.md"
            self.cli.scrape(source.url, current_path, format="markdown")
            current = _normalize(current_path.read_text(encoding="utf-8"))
            previous = _normalize(previous_path.read_text(encoding="utf-8")) if previous_path.exists() else ""
            # The first run establishes a baseline; it is not a change alert.
            diff = (
                list(difflib.unified_diff(previous.splitlines(), current.splitlines(), lineterm=""))
                if previous
                else []
            )
            current_path.replace(previous_path)
            reports.append({
                "name": source.name,
                "url": source.url,
                "changed": bool(diff),
                "diff": diff[:200],
            })

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sources": reports,
            "changed_sources": [item["name"] for item in reports if item["changed"]],
        }
        report_path = output_dir / f"report-{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report


def notify_webhook(webhook_url: str, report: dict[str, Any], *, provider: str) -> None:
    changed = report["changed_sources"]
    text = "Competitive intel update: " + (", ".join(changed) if changed else "no changes detected")
    payload = {"content": text} if provider == "discord" else {"text": text}
    request = Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=15):
        pass
