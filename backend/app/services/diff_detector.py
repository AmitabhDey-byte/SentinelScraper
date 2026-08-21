"""Field-level completeness diffing for collector snapshots.

An incident is detected only when a field moves from strictly more than 80%
complete to strictly less than 20% complete. Recovery uses the exact inverse.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


SnapshotRow = Mapping[str, Any]
SnapshotInput = Sequence[SnapshotRow] | Mapping[str, Any]


@dataclass(frozen=True)
class SnapshotDiff:
    """The completeness change between two successful/current snapshots."""

    rows_prev: int
    rows_curr: int
    dropped_fields: list[str]
    recovered_fields: list[str]
    previous_completeness: dict[str, float]
    current_completeness: dict[str, float]

    @property
    def has_incident(self) -> bool:
        return bool(self.dropped_fields)

    @property
    def has_recovery(self) -> bool:
        return bool(self.recovered_fields)


def normalize_snapshot(snapshot: SnapshotInput) -> list[SnapshotRow]:
    """Return listing rows from a raw list or a common wrapper object.

    Scraper output is commonly a top-level list, but wrappers such as
    ``{"data": [...]}``, ``{"results": [...]}``, and ``{"items": [...]}``
    are accepted so the detector can consume saved collector output directly.
    """

    if isinstance(snapshot, list) or isinstance(snapshot, tuple):
        return [row for row in snapshot if isinstance(row, Mapping)]

    for key in ("data", "results", "items", "listings"):
        candidate = snapshot.get(key)
        if isinstance(candidate, (list, tuple)):
            return [row for row in candidate if isinstance(row, Mapping)]

    raise ValueError("Snapshot must be a row list or an object containing data/results/items/listings")


def is_non_empty(value: Any) -> bool:
    """Whether an extracted field value counts as populated."""

    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def field_completeness(snapshot: SnapshotInput) -> dict[str, float]:
    """Calculate fill rate for every field present in a snapshot."""

    rows = normalize_snapshot(snapshot)
    fields = sorted({field for row in rows for field in row})
    if not rows:
        return {field: 0.0 for field in fields}

    return {
        field: sum(is_non_empty(row.get(field)) for row in rows) / len(rows)
        for field in fields
    }


def compare_snapshots(previous: SnapshotInput, current: SnapshotInput) -> SnapshotDiff:
    """Compare per-field completeness and return dropped/recovered fields."""

    previous_rows = normalize_snapshot(previous)
    current_rows = normalize_snapshot(current)
    previous_completeness = field_completeness(previous_rows)
    current_completeness = field_completeness(current_rows)
    fields = sorted(set(previous_completeness) | set(current_completeness))

    dropped_fields = [
        field
        for field in fields
        if previous_completeness.get(field, 0.0) > 0.80
        and current_completeness.get(field, 0.0) < 0.20
    ]
    recovered_fields = [
        field
        for field in fields
        if previous_completeness.get(field, 0.0) < 0.20
        and current_completeness.get(field, 0.0) > 0.80
    ]

    return SnapshotDiff(
        rows_prev=len(previous_rows),
        rows_curr=len(current_rows),
        dropped_fields=dropped_fields,
        recovered_fields=recovered_fields,
        previous_completeness={field: previous_completeness.get(field, 0.0) for field in fields},
        current_completeness={field: current_completeness.get(field, 0.0) for field in fields},
    )

