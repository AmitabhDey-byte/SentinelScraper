param(
  [switch]$Once,
  [int]$Heal,
  [switch]$Approve
)

$backendRoot = Join-Path $PSScriptRoot "..\backend"
Push-Location $backendRoot
try {
  if ($Heal -gt 0) {
    $args = @('-m', 'app.orchestration.scheduler', '--heal', "$Heal")
    if ($Approve) { $args += '--approve' }
    python @args
  } elseif ($Once) {
    python -m app.orchestration.scheduler --once
  } else {
    python -m app.orchestration.scheduler
  }
} finally {
  Pop-Location
}

