import json
from pathlib import Path

import pytest

from app.services.diff_detector import (
    completeness_baseline,
    compare_snapshots,
    field_completeness,
    is_non_empty,
    normalize_snapshot,
)


FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_fixture_snapshots_detect_rating_drop_and_price_recovery():
    previous = load_fixture("previous_snapshot.json")
    current = load_fixture("current_snapshot.json")

    # Make the fixture demonstrate both directions of the detector.
    for row in previous:
        row["price"] = ""

    result = compare_snapshots(previous, current)

    assert result.rows_prev == 5
    assert result.rows_curr == 5
    assert result.dropped_fields == ["rating"]
    assert result.recovered_fields == ["price"]
    assert result.previous_completeness["rating"] == 1.0
    assert result.current_completeness["rating"] == 0.0
    assert result.previous_completeness["price"] == 0.0
    assert result.current_completeness["price"] == 1.0
    assert result.has_incident is True
    assert result.has_recovery is True


def test_thresholds_are_strictly_greater_than_and_less_than():
    previous = [{"rating": "4.5"} for _ in range(5)]
    current = [{"rating": ""} for _ in range(5)]

    # Exactly 80% and 20% do not qualify as transitions.
    previous[4]["rating"] = ""
    current[0]["rating"] = "4.0"

    result = compare_snapshots(previous, current)

    assert result.previous_completeness["rating"] == pytest.approx(0.8)
    assert result.current_completeness["rating"] == pytest.approx(0.2)
    assert result.dropped_fields == []
    assert result.recovered_fields == []


def test_empty_current_field_is_detected_when_previous_was_complete():
    previous = [{"image_url": "https://example.com/image.jpg"} for _ in range(3)]
    current = [{"name": "Laptop"} for _ in range(3)]

    result = compare_snapshots(previous, current)

    assert result.dropped_fields == ["image_url"]
    assert result.current_completeness["image_url"] == 0.0


def test_empty_values_include_blank_strings_none_and_empty_collections():
    snapshot = [{"a": " ", "b": None, "c": [], "d": {}, "e": 0, "f": False, "g": "ok"}]

    result = field_completeness(snapshot)

    assert result == {"a": 0.0, "b": 0.0, "c": 0.0, "d": 0.0, "e": 1.0, "f": 1.0, "g": 1.0}
    assert is_non_empty(0) is True
    assert is_non_empty(False) is True


def test_normalize_snapshot_accepts_listings_wrapper_and_rejects_unknown_shape():
    rows = [{"title": "Laptop"}]

    assert normalize_snapshot({"listings": rows}) == rows
    with pytest.raises(ValueError, match="row list"):
        normalize_snapshot({"unexpected": rows})


def test_compact_baseline_preserves_the_exact_diff_thresholds():
    previous = [{"title": "Laptop", "rating": "4.5"} for _ in range(5)]
    current = [{"title": "Laptop", "rating": ""} for _ in range(5)]

    result = compare_snapshots(completeness_baseline(previous), current)

    assert result.rows_prev == 5
    assert result.dropped_fields == ["rating"]
