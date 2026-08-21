import json
from types import SimpleNamespace

from app.services.diff_detector import SnapshotDiff
from app.services.narration import GeminiNarrator


def incident_diff() -> SnapshotDiff:
    return SnapshotDiff(
        rows_prev=20,
        rows_curr=6,
        dropped_fields=["rating"],
        recovered_fields=["rating"],
        previous_completeness={"rating": 1.0},
        current_completeness={"rating": 1.0},
    )


class FakeModels:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, response=None, error=None):
        self.models = FakeModels(response=response, error=error)


def response(payload):
    return SimpleNamespace(text=json.dumps(payload))


def test_valid_structured_response_is_trusted_and_configured_for_json():
    client = FakeClient(
        response=response(
            {
                "report": "The rating extractor changed and was healed on eBay.",
                "site_mentioned": "eBay",
                "field_mentioned": ["rating"],
                "rows_mentioned": 6,
            }
        )
    )

    result = GeminiNarrator(client=client, model="gemini-2.5-flash-lite").narrate(
        site_name="eBay", diff=incident_diff()
    )

    assert result.narration_source == "gemini"
    assert result.report.startswith("The rating extractor")
    call = client.models.calls[0]
    assert call["model"] == "gemini-2.5-flash-lite"
    assert call["config"]["response_mime_type"] == "application/json"
    assert "rating" in call["contents"]


def test_mismatched_site_field_or_rows_uses_fallback():
    mismatches = [
        {"site_mentioned": "Target", "field_mentioned": ["rating"], "rows_mentioned": 6},
        {"site_mentioned": "eBay", "field_mentioned": ["price"], "rows_mentioned": 6},
        {"site_mentioned": "eBay", "field_mentioned": ["rating"], "rows_mentioned": 20},
    ]

    for payload in mismatches:
        client = FakeClient(
            response=response({"report": "untrusted", **payload})
        )
        result = GeminiNarrator(client=client).narrate(site_name="eBay", diff=incident_diff())
        assert result.narration_source == "fallback"
        assert "eBay" in result.report
        assert "rating" in result.report


def test_malformed_response_and_api_error_use_fallback():
    malformed = FakeClient(response=SimpleNamespace(text="not-json"))
    errored = FakeClient(error=TimeoutError("simulated timeout"))

    malformed_result = GeminiNarrator(client=malformed).narrate(site_name="eBay", diff=incident_diff())
    errored_result = GeminiNarrator(client=errored).narrate(site_name="eBay", diff=incident_diff())

    assert malformed_result.narration_source == "fallback"
    assert errored_result.narration_source == "fallback"


def test_no_changed_fields_does_not_call_gemini():
    client = FakeClient(response=response({}))
    diff = SnapshotDiff(
        rows_prev=5,
        rows_curr=5,
        dropped_fields=[],
        recovered_fields=[],
        previous_completeness={},
        current_completeness={},
    )

    result = GeminiNarrator(client=client).narrate(site_name="eBay", diff=diff)

    assert result.narration_source == "fallback"
    assert client.models.calls == []

