# Full local prep for Vercel + WhatsApp demo: Neon schema, migrations, seed, optional smoke.
# Prereq: .env with DATABASE_URL (Neon pooled) and optionally LLM_API_KEY for smoke chat test.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example — set DATABASE_URL and re-run." -ForegroundColor Yellow
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
    Write-Host "ERROR: Install Python 3.11+ (py launcher)." -ForegroundColor Red
    exit 1
}

& $py -m pip install -q -r requirements.txt

Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        $name = $matches[1].Trim()
        $val = $matches[2].Trim().Trim('"').Trim("'")
        Set-Item -Path "env:$name" -Value $val
    }
}

if (-not $env:DATABASE_URL) {
    Write-Host "ERROR: Set DATABASE_URL in .env (Neon pooled URL)." -ForegroundColor Red
    exit 1
}

$migrations = @(
    "scripts/init_schema.sql",
    "scripts/migrate_auth_rag.sql",
    "scripts/migrate_kb_rag_fts.sql",
    "scripts/migrate_customer_memory.sql",
    "scripts/migrate_pgvector_rag.sql",
    "scripts/migrate_chat_history.sql",
    "scripts/migrate_rag_feeds.sql"
)

foreach ($sql in $migrations) {
    if (Test-Path $sql) {
        Write-Host "Applying $sql ..." -ForegroundColor Green
        & $py scripts/apply_sql.py $sql
    }
}

Write-Host "Seeding demo ERP + users (cust1 / Alex = customer 1) ..." -ForegroundColor Green
& $py scripts/seed_db.py

if ($env:EMBEDDING_API_KEY) {
    Write-Host "Reindexing vector RAG ..." -ForegroundColor Green
    & $py scripts/reindex_vector_rag.py
}

Write-Host "`n--- Next: deploy to Vercel ---" -ForegroundColor Cyan
Write-Host "1. git init && git push to GitHub"
Write-Host "2. Import repo on vercel.com"
Write-Host "3. Paste env vars from vercel.env.example (Production)"
Write-Host "4. Meta WhatsApp webhook: https://YOUR_APP.vercel.app/channels/whatsapp"
Write-Host "5. Check: https://YOUR_APP.vercel.app/integrations/whatsapp/status"
Write-Host "`nFull guide: docs/vercel_whatsapp_demo.md"
