"""Ask an indexed documentation corpus a cited question."""

from argparse import ArgumentParser
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.docs_rag import SitemapRag  # noqa: E402


def main() -> None:
    parser = ArgumentParser(description="Query a SentinelScrape documentation index")
    parser.add_argument("question")
    parser.add_argument("--index", default="backend/output/rag/index.json")
    args = parser.parse_args()
    answer = SitemapRag().answer(Path(args.index), args.question)
    print(answer.model_dump_json(indent=2))


if __name__ == "__main__":
    main()

