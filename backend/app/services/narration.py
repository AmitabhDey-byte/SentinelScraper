"""Gemini-backed, guardrailed incident narration.

Gemini is allowed to provide the wording, but never the incident facts. The
site, changed fields, and current row count are validated against the actual
``SnapshotDiff`` before a response is trusted.
"""

from dataclasses import dataclass
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.services.diff_detector import SnapshotDiff


class GeminiNarration(BaseModel):
    """The only response shape accepted from Gemini."""

    report: str = Field(min_length=1)
    site_mentioned: str = Field(min_length=1)
    field_mentioned: list[str] = Field(min_length=1)
    rows_mentioned: int = Field(ge=0)


@dataclass(frozen=True)
class NarrationResult:
    report: str
    narration_source: Literal["gemini", "fallback"]
    structured: GeminiNarration | None = None


def _canonical(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().casefold()).strip("_")


def _field_names(fields: list[str]) -> str:
    if len(fields) == 1:
        return fields[0]
    if len(fields) == 2:
        return f"{fields[0]} and {fields[1]}"
    return f"{', '.join(fields[:-1])}, and {fields[-1]}"


def _fallback_report(site_name: str, diff: SnapshotDiff) -> str:
    changed_fields = sorted(set(diff.dropped_fields) | set(diff.recovered_fields))
    fields = _field_names(changed_fields) if changed_fields else "the tracked extraction fields"

    if diff.recovered_fields:
        return (
            f"{site_name} had a collector extraction change affecting {fields}; "
            f"Bright Data healing recovered the fields and the latest snapshot has "
            f"{diff.rows_curr} rows, versus {diff.rows_prev} previously."
        )
    return (
        f"{site_name} had a collector extraction change affecting {fields}; "
        f"the latest snapshot has {diff.rows_curr} rows, versus {diff.rows_prev} previously, "
        "so Bright Data healing is required."
    )


class GeminiNarrator:
    """Generate incident prose while enforcing facts from the detector."""

    def __init__(
        self,
        *,
        client: Any | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._client = client
        self._api_key = api_key if api_key is not None else settings.gemini_api_key
        self._model = model or settings.gemini_model

    def narrate(self, *, site_name: str, diff: SnapshotDiff) -> NarrationResult:
        """Return Gemini prose only when all factual guardrails pass."""

        fallback = NarrationResult(
            report=_fallback_report(site_name, diff),
            narration_source="fallback",
        )
        expected_fields = sorted(set(diff.dropped_fields) | set(diff.recovered_fields))
        if not expected_fields:
            return fallback

        try:
            response = self._generate(site_name=site_name, diff=diff, expected_fields=expected_fields)
            structured = self._parse_response(response)
            if not self._matches_diff(structured, site_name=site_name, diff=diff, expected_fields=expected_fields):
                return fallback
            return NarrationResult(
                report=structured.report.strip(),
                narration_source="gemini",
                structured=structured,
            )
        except (ValidationError, ValueError, TypeError, RuntimeError, ImportError, AttributeError, json.JSONDecodeError):
            return fallback
        except Exception:
            # The narration layer must never make a collector run fail because
            # an external model call timed out or returned an SDK-specific error.
            return fallback

    def _generate(self, *, site_name: str, diff: SnapshotDiff, expected_fields: list[str]) -> Any:
        prompt = (
            "Write one concise plain-English incident report for a web-scraper trust feed. "
            "Use only the supplied facts. Explain what extraction changed and what recovered. "
            "Return JSON matching the response schema. "
            f"Site: {site_name}. "
            f"Dropped fields: {diff.dropped_fields}. "
            f"Recovered fields: {diff.recovered_fields}. "
            f"Previous rows: {diff.rows_prev}. Current rows: {diff.rows_curr}. "
            f"The field_mentioned array must contain exactly: {expected_fields}. "
            f"The rows_mentioned value must be exactly: {diff.rows_curr}."
        )

        if self._client is None:
            if not self._api_key:
                raise RuntimeError("GEMINI_API_KEY is not configured")
            try:
                from google import genai
                from google.genai import types
            except ImportError as exc:
                raise RuntimeError("google-genai is not installed") from exc

            client = genai.Client(api_key=self._api_key)
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GeminiNarration,
            )
        else:
            # Test doubles and local adapters can inspect this stable config
            # without importing the external SDK.
            client = self._client
            config = {
                "response_mime_type": "application/json",
                "response_schema": GeminiNarration,
            }

        return client.models.generate_content(model=self._model, contents=prompt, config=config)

    @staticmethod
    def _parse_response(response: Any) -> GeminiNarration:
        parsed = getattr(response, "parsed", None)
        if parsed is not None:
            if isinstance(parsed, GeminiNarration):
                return parsed
            return GeminiNarration.model_validate(parsed)

        text = getattr(response, "text", None)
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Gemini response has no structured payload")
        return GeminiNarration.model_validate(json.loads(text))

    @staticmethod
    def _matches_diff(
        response: GeminiNarration,
        *,
        site_name: str,
        diff: SnapshotDiff,
        expected_fields: list[str],
    ) -> bool:
        response_fields = sorted({_canonical(field) for field in response.field_mentioned})
        actual_fields = sorted({_canonical(field) for field in expected_fields})
        return (
            _canonical(response.site_mentioned) == _canonical(site_name)
            and response_fields == actual_fields
            and response.rows_mentioned == diff.rows_curr
            and bool(response.report.strip())
        )

