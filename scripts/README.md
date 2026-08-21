# Operational scripts

- `bootstrap_collectors.py` creates and registers the five tracked Bright Data collectors.
- `run_scheduler.ps1` runs one polling cycle, starts the continuous loop, or proposes/approves a heal.
- `ci_self_heal.py` runs the CI loop: poll → detect → heal/approve → re-run → write a GitHub summary.
