# Install/pull Ollama model for RTX 5060 Ti 16GB (local GPU inference)
# Prereq: install Ollama from https://ollama.com/download/windows (uses NVIDIA GPU automatically)

$ErrorActionPreference = "Stop"
$Model = if ($env:LOCAL_LLM_MODEL) { $env:LOCAL_LLM_MODEL } else { "llama3.1:8b" }

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "Ollama not found on PATH." -ForegroundColor Yellow
    Write-Host "  1. Download: https://ollama.com/download/windows"
    Write-Host "  2. Install and open Ollama once (tray icon = server running)"
    Write-Host "  3. Re-run: powershell -ExecutionPolicy Bypass -File scripts/setup_local_llm.ps1"
    exit 1
}

Write-Host "Ollama: $(ollama --version)" -ForegroundColor Cyan
Write-Host "Pulling model '$Model' (good fit for 16GB VRAM)..." -ForegroundColor Green
ollama pull $Model

Write-Host "`nWarming up GPU (first run may take a minute)..." -ForegroundColor Green
ollama run $Model "Say OK in one word." --verbose 2>$null | Out-Null

Write-Host "`nInstalled models:" -ForegroundColor Cyan
ollama list

$base = "http://127.0.0.1:11434"
try {
    $tags = Invoke-RestMethod -Uri "$base/api/tags" -TimeoutSec 10
    Write-Host "`nOllama API is reachable at $base" -ForegroundColor Green
} catch {
    Write-Host "`nOllama API not reachable. Open the Ollama app from the Start menu." -ForegroundColor Red
    exit 1
}

Write-Host @"

Local LLM ready.
  .env should have:
    LOCAL_LLM_API_BASE=http://127.0.0.1:11434/v1
    LOCAL_LLM_MODEL=$Model
    LLM_ORDER=local,api

In the chat UI use LLM mode: auto (GPU first) or local (GPU only).

"@ -ForegroundColor Cyan
