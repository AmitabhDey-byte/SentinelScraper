import json

from app.services.competitive_intel import CompetitorSource, CompetitiveIntelMonitor
from app.services.docs_rag import chunks, sitemap_locations
from app.services.parallel_battle import ParallelScraperBattle
from app.services.search_agent import KeywordResearchAgent


class FakeCLI:
    def __init__(self, content: str = ""):
        self.content = content

    def scrape(self, url, output_path, *, format="markdown"):
        output_path.write_text(self.content or f"# {url}\n- extracted row", encoding="utf-8")

    def search(self, query, output_path, *, country=None, search_type="shopping"):
        output_path.write_text(
            json.dumps({"shopping_results": [{"title": query, "link": "https://example.com/item", "price": "$10"}]}),
            encoding="utf-8",
        )


def test_sitemap_parser_and_chunker_are_offline():
    xml = "<urlset><url><loc>https://example.com/docs</loc></url></urlset>"

    assert sitemap_locations(xml) == ["https://example.com/docs"]
    assert chunks("one two three", size=5, overlap=0) == ["one", "two", "three"]


def test_competitive_intel_establishes_a_baseline_then_detects_change(tmp_path):
    monitor = CompetitiveIntelMonitor(FakeCLI("same"))
    source = [CompetitorSource("Example", "https://example.com/changelog")]

    first = monitor.run(source, tmp_path)
    assert first["changed_sources"] == []

    monitor.cli.content = "changed"
    second = monitor.run(source, tmp_path)
    assert second["changed_sources"] == ["Example"]


def test_keyword_agent_normalizes_bright_data_search_results(tmp_path):
    result = KeywordResearchAgent(FakeCLI()).research("laptop", tmp_path / "search.json")

    assert result["results"][0]["title"] == "laptop"
    assert result["results"][0]["price"] == "$10"


def test_parallel_battle_returns_the_highest_coverage_agent(tmp_path):
    result = ParallelScraperBattle(FakeCLI(), workers=2).run(
        {
            "one": {"url": "https://example.com/one"},
            "two": {"url": "https://example.com/two"},
        },
        tmp_path,
    )

    assert result["winner"] in {"one", "two"}
    assert (tmp_path / "battle.json").exists()
