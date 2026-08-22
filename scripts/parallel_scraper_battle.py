"""Fan out site agents, score their extraction output, and publish a winner."""

from argparse import ArgumentParser
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.parallel_battle import ParallelScraperBattle  # noqa: E402
from app.sites import SITES  # noqa: E402


def main() -> None:
    parser = ArgumentParser(description="Run three or more independent Bright Data site agents in parallel")
    parser.add_argument("--sites", default="ebay,newegg,target")
    parser.add_argument("--output", default="backend/output/parallel-battle")
    args = parser.parse_args()
    selected = {name: SITES[name] for name in args.sites.split(",") if name in SITES}
    if len(selected) < 3:
        raise SystemExit("Choose at least three tracked site keys")
    print(ParallelScraperBattle(workers=len(selected)).run(selected, Path(args.output)))


if __name__ == "__main__":
    main()

