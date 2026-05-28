# Point .env at native GPU + download GGUF from Hugging Face
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $EnvFile)) {
    Copy-Item (Join-Path $ProjectRoot ".env.example") $EnvFile
}

$lines = @(
    "LOCAL_LLM_BACKEND=native",
    "HF_GGUF_REPO=bartowski/Qwen2.5-7B-Instruct-GGUF",
    "HF_GGUF_FILENAME=Qwen2.5-7B-Instruct-Q4_K_M.gguf",
    "LOCAL_GGUF_PATH=models/Qwen2.5-7B-Instruct-Q4_K_M.gguf",
    "LOCAL_LLM_N_GPU_LAYERS=-1",
    "LOCAL_LLM_PRELOAD=true"
)
$content = Get-Content $EnvFile -Raw
foreach ($line in $lines) {
    $key = ($line -split "=", 2)[0]
    if ($content -match "(?m)^$key=") {
        $content = $content -replace "(?m)^$key=.*", $line
    } else {
        $content += "`n$line"
    }
}
Set-Content -Path $EnvFile -Value $content.TrimEnd()
Add-Content -Path $EnvFile -Value ""

& "$ProjectRoot\scripts\download_native_model.ps1"
