"""Keyword-powered research agent backed by Bright Data Search."""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from app.orchestration.brightdata import BrightDataCLI


@dataclass(frozen=True)
class ResearchItem:
    title: str
    url: str
    snippet: str
    price: str | None = None


def _result_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    for key in ("organic", "results", "shopping_results", "items"):
        if isinstance(payload, dict) and isinstance(payload.get(key), list):
            return [item for item in payload[key] if isinstance(item, dict)]
    return []


class KeywordResearchAgent:
    def __init__(self, cli: BrightDataCLI | None = None) -> None:
        self.cli = cli or BrightDataCLI()

    def research(
        self,
        keyword: str,
        output_path: Path,
        *,
        country: str | None = None,
        search_type: str = "shopping",
        limit: int = 10,
    ) -> dict[str, Any]:
        self.cli.search(keyword, output_path, country=country, search_type=search_type)
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        items = [
            ResearchItem(
                title=str(item.get("title") or item.get("name") or "Untitled result"),
                url=str(item.get("link") or item.get("url") or ""),
                snippet=str(item.get("snippet") or item.get("description") or ""),
                price=str(item.get("price")) if item.get("price") is not None else None,
            )
            for item in _result_list(payload)[:limit]
        ]
        return {
            "keyword": keyword,
            "country": country,
            "search_type": search_type,
            "summary": f"Bright Data returned {len(items)} results for {keyword!r}.",
            "results": [item.__dict__ for item in items],
            "raw_output": str(output_path),
        }

