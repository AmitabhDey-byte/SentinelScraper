"""Create a deterministic broken snapshot to demo detection and recovery locally.

This is a no-network proof of the 80%/20% trust rule. The live demo uses the
same incident shape, then ``scheduler --heal INCIDENT_ID --approve`` calls the
Bright Data healing flow.
"""

from argparse import ArgumentParser
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.diff_detector import compare_snapshots  # noqa: E402


def main() -> None:
    parser = ArgumentParser(description="Demonstrate a field break and recovery")
    parser.add_argument("--field", default="rating")
    parser.add_argument("--output", default="backend/output/demo-self-heal")
    args = parser.parse_args()
    fixture_path = ROOT / "backend/tests/fixtures/previous_snapshot.json"
    previous = json.loads(fixture_path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(previous)
    for row in broken:
        row[args.field] = ""
    output_dir = ROOT / args.output
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "before.json").write_text(json.dumps(previous, indent=2), encoding="utf-8")
    (output_dir / "broken.json").write_text(json.dumps(broken, indent=2), encoding="utf-8")
    detected = compare_snapshots(previous, broken)
    recovered = compare_snapshots(broken, previous)
    print(json.dumps({"detected": detected.dropped_fields, "recovered": recovered.recovered_fields}, indent=2))


if __name__ == "__main__":
    main()

