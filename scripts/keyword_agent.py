"""Research products, prices, jobs, or listings from a plain-English keyword."""

from argparse import ArgumentParser
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.search_agent import KeywordResearchAgent  # noqa: E402


def main() -> None:
    parser = ArgumentParser(description="Run Bright Data Search as a keyword agent")
    parser.add_argument("keyword")
    parser.add_argument("--country")
    parser.add_argument("--type", default="shopping", choices=["web", "news", "images", "shopping"])
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    output_path = Path("backend/output/research") / f"{uuid4().hex}.json"
    print(KeywordResearchAgent().research(args.keyword, output_path, country=args.country, search_type=args.type, limit=args.limit))


if __name__ == "__main__":
    main()

