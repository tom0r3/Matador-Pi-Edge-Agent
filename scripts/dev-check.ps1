Param(
  [switch]$SkipPython,
  [switch]$SkipJs,
  [switch]$SkipShell,
  [switch]$SkipDiffCheck
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

function Write-Step {
  Param([string]$Message)
  Write-Host ""
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Find-Executable {
  Param([string[]]$Candidates)
  foreach ($candidate in $Candidates) {
    if (-not $candidate) { continue }
    if ($candidate -match "[\\/]" -and (Test-Path $candidate)) {
      return (Resolve-Path $candidate).Path
    }
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($command) {
      return $command.Source
    }
  }
  return $null
}

function Invoke-Native {
  Param(
    [string]$FilePath,
    [string[]]$Arguments
  )
  $previousErrorActionPreference = $ErrorActionPreference
  try {
    # Native tools can write warnings to stderr while still succeeding.
    $ErrorActionPreference = "Continue"
    & $FilePath @Arguments
    $exitCode = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousErrorActionPreference
  }
  if ($exitCode -ne 0) {
    throw "$FilePath failed with exit code $exitCode"
  }
}

$Python = Find-Executable @(
  $env:MATADOR_DEV_PYTHON,
  "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe",
  "python"
)
$Bash = Find-Executable @(
  $env:MATADOR_DEV_BASH,
  "C:\Program Files\Git\bin\bash.exe",
  "bash"
)

if (-not $SkipPython) {
  if (-not $Python) { throw "Python not found. Set MATADOR_DEV_PYTHON or install Python." }
  Write-Step "Python compile"
  Invoke-Native $Python @(
    "-m",
    "py_compile",
    "edge_agent\pi_edge_agent.py",
    "edge_agent\navico_advertiser.py",
    "edge_agent\remote_channel_protocol.py"
  )
  Write-Step "Python tests"
  Invoke-Native $Python @(
    "-m",
    "unittest",
    "discover",
    "-s",
    "tests"
  )
}

if (-not $SkipJs) {
  Write-Step "Browser JavaScript parse"
  Write-Host "No browser JavaScript in the standalone Pi Agent repository."
}

if (-not $SkipShell) {
  if (-not $Bash) { throw "bash not found. Install Git for Windows or set MATADOR_DEV_BASH." }
  Write-Step "Shell script syntax"
  foreach ($file in @("scripts/update.sh", "scripts/install.sh", "scripts/status.sh", "scripts/factory-reset.sh", "scripts/prepare-golden-image.sh", "scripts/set-hostname.sh", "scripts/dev-check.sh")) {
    if (Test-Path $file) {
      Invoke-Native $Bash @("-n", $file)
      Write-Host "$file ok"
    }
  }
}

if (-not $SkipDiffCheck) {
  $Git = Find-Executable @("git")
  if ($Git) {
    Write-Step "Git whitespace check"
    Invoke-Native $Git @(
      "-c",
      "safe.directory=$RepoRoot",
      "-C",
      $RepoRoot,
      "diff",
      "--check",
      "--",
      "edge_agent/pi_edge_agent.py",
      "edge_agent/navico_advertiser.py",
      "edge_agent/remote_channel_protocol.py",
      "tests/test_navico_advertiser.py",
      "tests/test_remote_channel_protocol.py",
      "README.md",
      "CHANGELOG.md",
      "VERSION",
      "scripts/update.sh",
      "scripts/install.sh",
      "scripts/status.sh",
      "deploy/matador-pi-edge-agent.service",
      "scripts/dev-check.ps1",
      "scripts/dev-check.sh"
    )
  } else {
    Write-Host "git not found; skipping diff whitespace check." -ForegroundColor Yellow
  }
}

Write-Host ""
Write-Host "Development checks passed." -ForegroundColor Green
