"""Small subprocess adapter for the Bright Data ``bdata`` CLI."""

from pathlib import Path
import subprocess


class BrightDataCLI:
    def __init__(self, executable: str = "bdata") -> None:
        self.executable = executable

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [self.executable, *args],
            check=True,
            capture_output=True,
            text=True,
        )

    def create(self, url: str, field_description: str, name: str) -> str:
        result = self._run(["scraper", "create", url, field_description, "--name", name])
        output = f"{result.stdout}\n{result.stderr}"
        for token in output.replace("'", " ").replace('"', " ").split():
            if token.startswith("c_"):
                return token.rstrip(",.;")
        raise RuntimeError(f"Bright Data did not return a collector_id for {name}: {output.strip()}")

    def run(self, collector_id: str, url: str, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._run(["scraper", "run", collector_id, "--url", url, "-o", str(output_path)])

    def heal(self, collector_id: str, url: str, hint: str, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._run(["scraper", "heal", collector_id, hint, "--url", url, "-o", str(output_path)])

    def approve(self, collector_id: str) -> None:
        self._run(["scraper", "approve", collector_id])

    def scrape(self, url: str, output_path: Path, *, format: str = "markdown") -> None:
        """Fetch arbitrary web content through Bright Data's unlocker."""

        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._run(["scrape", url, "-f", format, "-o", str(output_path)])

    def search(
        self,
        query: str,
        output_path: Path,
        *,
        country: str | None = None,
        search_type: str = "shopping",
    ) -> None:
        """Run Bright Data Search with machine-readable JSON output."""

        output_path.parent.mkdir(parents=True, exist_ok=True)
        args = ["search", query, "--type", search_type, "--json", "-o", str(output_path)]
        if country:
            args.extend(["--country", country])
        self._run(args)
