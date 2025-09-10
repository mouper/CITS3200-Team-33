Param(
  [string]$Port = "5050",
  [string]$Host = "127.0.0.1"
)

$ErrorActionPreference = "Stop"

Write-Host "Starting Flask server on http://$Host:$Port ..." -ForegroundColor Cyan

# Start Flask server in background job
$repoRoot = Split-Path -Parent $PSScriptRoot
$runPath = Join-Path $repoRoot "server\run.py"

if (-Not (Test-Path $runPath)) {
  Write-Error "Could not find server/run.py at $runPath"
  exit 1
}

$env:FLASK_RUN_PORT = $Port
$job = Start-Job -ScriptBlock {
  param($runFile)
  & python $runFile
} -ArgumentList $runPath

Start-Sleep -Seconds 1

# Poll health until up or timeout
$healthUrl = "http://$Host:$Port/health"
$deadline = (Get-Date).AddSeconds(10)
$up = $false
while ((Get-Date) -lt $deadline) {
  try {
    $resp = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
    if ($resp.StatusCode -eq 200) { $up = $true; break }
  } catch { Start-Sleep -Milliseconds 400 }
}

if ($up) {
  Write-Host "Flask is up at $healthUrl" -ForegroundColor Green
} else {
  Write-Warning "Flask did not respond in time; continuing anyway."
}

# Try to open Chrome with the unpacked extension
$extPath = Join-Path $repoRoot "packages\extension\src"
if (-Not (Test-Path $extPath)) {
  Write-Warning "Extension path not found at $extPath"
} else {
  Write-Host "Launching Chrome with extension from $extPath" -ForegroundColor Cyan
  $chrome = "$env:ProgramFiles\Google\Chrome\Application\chrome.exe"
  if (-Not (Test-Path $chrome)) { $chrome = "$env:ProgramFiles(x86)\Google\Chrome\Application\chrome.exe" }
  if (-Not (Test-Path $chrome)) { $chrome = "$env:LocalAppData\Google\Chrome\Application\chrome.exe" }

  if (Test-Path $chrome) {
    Start-Process -FilePath $chrome -ArgumentList "--load-extension=$extPath","http://$Host:$Port/version"
  } else {
    Write-Warning "Chrome not found. Please open Chrome manually and load the unpacked extension from $extPath"
  }
}

Write-Host "To stop the Flask server, run: Receive-Job $($job.Id); Stop-Job $($job.Id)" -ForegroundColor Yellow


