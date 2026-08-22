"""Run independent site collectors in parallel and select the strongest output."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from app.orchestration.brightdata import BrightDataCLI


@dataclass
class AgentResult:
    agent: str
    url: str
    output: str
    rows: int
    non_empty_lines: int
    score: int
    error: str | None = None


class ParallelScraperBattle:
    def __init__(self, cli: BrightDataCLI | None = None, workers: int = 3) -> None:
        self.cli = cli or BrightDataCLI()
        self.workers = workers

    def _run_agent(self, agent: str, url: str, output_dir: Path) -> AgentResult:
        output_path = output_dir / f"{agent}.md"
        try:
            self.cli.scrape(url, output_path, format="markdown")
            lines = [line.strip() for line in output_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            rows = sum(line.startswith(("- ", "* ", "|")) for line in lines)
            non_empty_lines = len(lines)
            score = rows * 3 + min(non_empty_lines, 100)
            return AgentResult(agent, url, str(output_path), rows, non_empty_lines, score)
        except Exception as exc:
            return AgentResult(agent, url, str(output_path), 0, 0, 0, str(exc))

    def run(self, sites: dict[str, dict[str, str]], output_dir: Path) -> dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        results: list[AgentResult] = []
        with ThreadPoolExecutor(max_workers=min(self.workers, len(sites) or 1)) as executor:
            futures = [executor.submit(self._run_agent, name, site["url"], output_dir) for name, site in sites.items()]
            for future in as_completed(futures):
                results.append(future.result())
        results.sort(key=lambda result: result.score, reverse=True)
        winner = results[0] if results else None
        payload = {
            "winner": winner.agent if winner else None,
            "reason": f"Highest extraction coverage score: {winner.score}." if winner else "No agent completed.",
            "agents": [asdict(result) for result in results],
        }
        (output_dir / "battle.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

