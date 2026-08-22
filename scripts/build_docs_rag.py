"""Build a sitemap-backed documentation index."""

from argparse import ArgumentParser
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.docs_rag import SitemapRag  # noqa: E402


def main() -> None:
    parser = ArgumentParser(description="Build a Bright Data sitemap-to-RAG index")
    parser.add_argument("sitemap_url")
    parser.add_argument("--output", default="backend/output/rag/index.json")
    parser.add_argument("--max-pages", type=int, default=20)
    args = parser.parse_args()
    result = SitemapRag().ingest(args.sitemap_url, Path(args.output), max_pages=args.max_pages)
    print(result)


if __name__ == "__main__":
    main()

