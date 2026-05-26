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
  & $FilePath @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "$FilePath failed with exit code $LASTEXITCODE"
  }
}

$Python = Find-Executable @(
  $env:MATADOR_DEV_PYTHON,
  "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe",
  "python"
)
$Node = Find-Executable @(
  $env:MATADOR_DEV_NODE,
  "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe",
  "node"
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
    "gofree_collector\dashboard.py",
    "gofree_collector\edge_ingest.py"
  )
}

if (-not $SkipJs) {
  if (-not $Node) { throw "Node.js not found. Set MATADOR_DEV_NODE or install Node.js." }
  Write-Step "Embedded browser JavaScript parse"
  $script = @'
const fs = require("fs");
const files = ["web/nextindex.html", "web/pi_edge_diagnostics.html", "web/admin.html", "web/diagnostics.html", "web/sql.html"];
for (const file of files) {
  const html = fs.readFileSync(file, "utf8");
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((match) => match[1]);
  for (const source of scripts) new Function(source);
  console.log(`${file}: ${scripts.length} script block(s) ok`);
}
'@
  $tempScript = Join-Path ([System.IO.Path]::GetTempPath()) "matador-dev-check-js-$PID.js"
  try {
    Set-Content -LiteralPath $tempScript -Value $script -Encoding UTF8
    Invoke-Native $Node @($tempScript)
  } finally {
    Remove-Item -LiteralPath $tempScript -ErrorAction SilentlyContinue
  }
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
      "diff",
      "--check",
      "--",
      "edge_agent/pi_edge_agent.py",
      "gofree_collector/dashboard.py",
      "gofree_collector/edge_ingest.py",
      "web/nextindex.html",
      "web/pi_edge_diagnostics.html",
      "web/admin.html",
      "web/diagnostics.html",
      "web/sql.html",
      "README.md",
      "CHANGELOG.md",
      "docs/edge_agent.md",
      "docs/pi_edge_agent.md",
      "docs/sql_admin.md",
      "scripts/update.sh",
      "scripts/install.sh",
      "scripts/status.sh",
      "scripts/dev-check.ps1",
      "scripts/dev-check.sh"
    )
  } else {
    Write-Host "git not found; skipping diff whitespace check." -ForegroundColor Yellow
  }
}

Write-Host ""
Write-Host "Development checks passed." -ForegroundColor Green
