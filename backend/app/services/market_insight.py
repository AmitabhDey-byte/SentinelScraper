"""Grounded Gemini market brief with a deterministic, evidence-first fallback."""

from dataclasses import dataclass
import json
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.config import settings


class MarketInsight(BaseModel):
    headline: str = Field(min_length=1, max_length=140)
    recommendation: str = Field(min_length=1, max_length=280)
    rationale: str = Field(min_length=1, max_length=360)
    confidence: Literal["low", "medium", "high"]


@dataclass(frozen=True)
class InsightResult:
    insight: MarketInsight
    source: Literal["gemini", "fallback"]


def fallback_insight(*, drops: int, restocks: int, open_incidents: int) -> MarketInsight:
    if open_incidents:
        return MarketInsight(
            headline="Verify the feed before making a buying decision.",
            recommendation="Treat current prices as provisional until the open collector repair has completed.",
            rationale=f"{open_incidents} collector repair(s) remain open; {drops} price movement signal(s) and {restocks} restock signal(s) are visible.",
            confidence="low",
        )
    if drops:
        return MarketInsight(
            headline="A verified price window is open.",
            recommendation="Review the lowest tracked listings now and save any model you would buy at the observed price.",
            rationale=f"The latest scan found {drops} price drop signal(s) and {restocks} restock signal(s), with no open extraction incidents.",
            confidence="medium",
        )
    return MarketInsight(
        headline="The market is steady in the latest verified scan.",
        recommendation="Save target models and wait for a new drop or restock signal before acting.",
        rationale=f"The latest scan found {drops} price drop signal(s), {restocks} restock signal(s), and no open extraction incidents.",
        confidence="medium",
    )


class MarketInsightNarrator:
    def __init__(self, *, client: Any | None = None) -> None:
        self._client = client

    def create(self, *, drops: int, restocks: int, open_incidents: int) -> InsightResult:
        fallback = fallback_insight(drops=drops, restocks=restocks, open_incidents=open_incidents)
        if not settings.gemini_api_key and self._client is None:
            return InsightResult(insight=fallback, source="fallback")
        try:
            response = self._generate(drops=drops, restocks=restocks, open_incidents=open_incidents)
            payload = getattr(response, "parsed", None)
            if payload is None:
                payload = json.loads(getattr(response, "text", ""))
            insight = MarketInsight.model_validate(payload)
            return InsightResult(insight=insight, source="gemini")
        except (ValueError, TypeError, ValidationError, json.JSONDecodeError, ImportError, AttributeError):
            return InsightResult(insight=fallback, source="fallback")
        except Exception:
            return InsightResult(insight=fallback, source="fallback")

    def _generate(self, *, drops: int, restocks: int, open_incidents: int) -> Any:
        prompt = (
            "Create a concise market brief for a laptop price intelligence dashboard. "
            "Never invent listings, prices, sites, or future certainty. Base the recommendation only on these facts. "
            f"Price-drop signals: {drops}. Restock signals: {restocks}. Open collector incidents: {open_incidents}."
        )
        if self._client is not None:
            return self._client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config={"response_mime_type": "application/json", "response_schema": MarketInsight},
            )
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.gemini_api_key)
        return client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json", response_schema=MarketInsight
            ),
        )
