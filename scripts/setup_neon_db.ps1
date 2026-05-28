# One-shot Neon setup: schema + migrations + seed (no psql required)
# Prereq: copy .env.example to .env and set DATABASE_URL to your Neon pooled URL

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not (Test-Path ".env")) {
    Write-Host "ERROR: No .env file." -ForegroundColor Red
    Write-Host "  copy .env.example .env"
    Write-Host "  Then set DATABASE_URL to your Neon pooled connection string (ends with neon.tech)."
    exit 1
}

$py = $null
foreach ($cmd in @("py", "python3", "python")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        $py = $cmd
        break
    }
}
if (-not $py) {
    Write-Host "ERROR: Python not found. Install Python 3.11+ and ensure 'py' or 'python' is on PATH." -ForegroundColor Red
    exit 1
}

Write-Host "Using Python: $py" -ForegroundColor Cyan
& $py -m pip install -q -r requirements.txt

# Load .env into this session for seed/apply scripts (dotenv also loads in Python)
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        $name = $matches[1].Trim()
        $val = $matches[2].Trim().Trim('"').Trim("'")
        Set-Item -Path "env:$name" -Value $val
    }
}

if (-not $env:DATABASE_URL -or $env:DATABASE_URL -like "*...*") {
    Write-Host "ERROR: DATABASE_URL in .env is empty or still a placeholder." -ForegroundColor Red
    exit 1
}

if ($env:DATABASE_URL -notmatch "neon\.tech") {
    Write-Host "WARNING: DATABASE_URL does not contain neon.tech — confirm this is your Neon URL." -ForegroundColor Yellow
}

Write-Host "`n[1/4] init_schema.sql (drops and recreates tables)" -ForegroundColor Green
& $py scripts/apply_sql.py scripts/init_schema.sql

foreach ($sql in @(
    "scripts/migrate_auth_rag.sql",
    "scripts/migrate_kb_rag_fts.sql",
    "scripts/migrate_customer_memory.sql",
    "scripts/migrate_pgvector_rag.sql",
    "scripts/migrate_chat_history.sql",
    "scripts/migrate_rag_feeds.sql"
)) {
    if (Test-Path $sql) {
        Write-Host "`nApplying $sql" -ForegroundColor Green
        & $py scripts/apply_sql.py $sql
    }
}

Write-Host "`nSeeding (~500 rows + demo users)" -ForegroundColor Green
& $py scripts/seed_db.py

Write-Host "`nSetup complete. Log in: cust1 / Alex (customer 1) or admin / Admin" -ForegroundColor Cyan
Write-Host "Vercel demo: powershell -File scripts/setup_vercel_whatsapp_demo.ps1"
Write-Host "Start app: powershell -ExecutionPolicy Bypass -File scripts/run_dev.ps1"
