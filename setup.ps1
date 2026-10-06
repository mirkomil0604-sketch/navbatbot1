# SHIELD.AI Quick Start Script for Windows
# Setup and run API + Telegram Bot

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  SHIELD.AI Quick Start Setup" -ForegroundColor Cyan
Write-Host "  Uzbek Misinformation Detection System" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/6] Checking requirements..." -ForegroundColor Yellow

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Python not found. Install Python 3.10+ from python.org" -ForegroundColor Red
    exit 1
}

$pythonVersion = python --version 2>&1
Write-Host "OK: $pythonVersion found" -ForegroundColor Green

Write-Host ""
Write-Host "[2/6] Setting up configuration..." -ForegroundColor Yellow

if (-not $env:TELEGRAM_BOT_TOKEN) {
    Write-Host "ERROR: TELEGRAM_BOT_TOKEN not set!" -ForegroundColor Red
    $env:TELEGRAM_BOT_TOKEN = Read-Host "Enter TELEGRAM_BOT_TOKEN"
}

if (-not $env:OLLAMA_URL) {
    $env:OLLAMA_URL = "http://localhost:11434/api/generate"
}

if (-not $env:OLLAMA_MODEL) {
    $env:OLLAMA_MODEL = "gemma2:9b"
}

Write-Host "OK: Configuration set" -ForegroundColor Green
Write-Host "   OLLAMA_URL: $env:OLLAMA_URL"
Write-Host "   OLLAMA_MODEL: $env:OLLAMA_MODEL"

Write-Host ""
Write-Host "[3/6] Setting up Python environment..." -ForegroundColor Yellow

if (-not (Test-Path -LiteralPath "venv")) {
    Write-Host "   Creating virtual environment..."
    python -m venv venv
    Write-Host "   OK: Virtual environment created" -ForegroundColor Green
}

$venvPython = Join-Path (Join-Path $PWD "venv") "Scripts\python.exe"
$venvPip = Join-Path (Join-Path $PWD "venv") "Scripts\pip.exe"

Write-Host "   Installing dependencies..."
if (Test-Path -LiteralPath "requirements.txt") {
    & $venvPip install -q -r requirements.txt
} else {
        & $venvPip install -q fastapi uvicorn httpx python-telegram-bot ollama
}
Write-Host "OK: Python environment ready" -ForegroundColor Green

Write-Host ""
Write-Host "[4/6] Verifying configuration..." -ForegroundColor Yellow

if (-not (Test-Path -LiteralPath "shield_ai_api_server.py")) {
    Write-Host "ERROR: shield_ai_api_server.py not found" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path -LiteralPath "shield_ai_telegram_bot.py")) {
    Write-Host "ERROR: shield_ai_telegram_bot.py not found" -ForegroundColor Red
    exit 1
}

Write-Host "OK: Configuration verified" -ForegroundColor Green

Write-Host ""
Write-Host "[5/6] Starting servers..." -ForegroundColor Yellow

$env:TELEGRAM_BOT_TOKEN = $env:TELEGRAM_BOT_TOKEN
$env:OLLAMA_URL = $env:OLLAMA_URL
$env:OLLAMA_MODEL = $env:OLLAMA_MODEL

$apiProcess = Start-Process -FilePath $venvPython -ArgumentList "shield_ai_api_server.py" -PassThru -WindowStyle Hidden -WorkingDirectory $PWD
Write-Host "   [API] FastAPI server starting (PID: $($apiProcess.Id))..."

$botProcess = Start-Process -FilePath $venvPython -ArgumentList "shield_ai_telegram_bot.py" -PassThru -WindowStyle Hidden -WorkingDirectory $PWD
Write-Host "   [BOT] Telegram bot starting (PID: $($botProcess.Id))..."

Start-Sleep -Seconds 4

try {
    $health = Invoke-RestMethod -Uri "http://localhost:8001/health" -Method GET -TimeoutSec 5
    if ($health.status -eq "ok") {
        Write-Host "   OK: FastAPI server running on http://localhost:8001" -ForegroundColor Green
    } else {
        throw "API health check returned non-ok status"
    }
} catch {
    Write-Host "ERROR: FastAPI server failed to start or health check failed" -ForegroundColor Red
    Stop-Process -Id $botProcess.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $apiProcess.Id -Force -ErrorAction SilentlyContinue
    exit 1
}

try {
    $null = $botProcess.Handle
    Write-Host "   OK: Telegram bot running" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Telegram bot failed to start" -ForegroundColor Red
    Stop-Process -Id $apiProcess.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $botProcess.Id -Force -ErrorAction SilentlyContinue
    exit 1
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  OK: SHIELD.AI Running!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "API Server" -ForegroundColor Cyan
Write-Host "   URL: http://localhost:8001"
Write-Host "   Docs: http://localhost:8001/docs"
Write-Host ""
Write-Host "Telegram Bot"
Write-Host "   Search your bot in Telegram"
Write-Host "   Commands: /start, /help, /example"
Write-Host ""
Write-Host "Status"
Write-Host "   API PID: $($apiProcess.Id)"
Write-Host "   Bot PID: $($botProcess.Id)"
Write-Host ""
Write-Host "Test with:"
Write-Host "   curl http://localhost:8001/health"
Write-Host ""
Write-Host "Press Ctrl+C to stop"
Write-Host ""

try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host ""
    Write-Host "Shutting down..." -ForegroundColor Yellow
    Stop-Process -Id $botProcess.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $apiProcess.Id -Force -ErrorAction SilentlyContinue
}
