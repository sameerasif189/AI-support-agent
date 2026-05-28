# Native GPU setup: CUDA llama-cpp-python + GGUF from Hugging Face (no Ollama)
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$py = "C:\Users\PC\miniconda3\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

Write-Host "Installing Python deps (llama-cpp CUDA + HF download) ..." -ForegroundColor Cyan
& $py -m pip install -q -r requirements-local.txt --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124
if ($LASTEXITCODE -ne 0) {
    & $py -m pip install -q huggingface_hub nvidia-cublas-cu12 nvidia-cuda-runtime-cu12
    & $py -m pip install llama-cpp-python --force-reinstall --no-cache-dir --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124
}

Write-Host "Verifying Hugging Face model link ..." -ForegroundColor Cyan
& $py scripts\download_gguf.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`nRestart the API server. .env should include:" -ForegroundColor Green
Write-Host "  LOCAL_LLM_BACKEND=native"
Write-Host "  LOCAL_GGUF_PATH=models/Qwen2.5-7B-Instruct-Q4_K_M.gguf"
