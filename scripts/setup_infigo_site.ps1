# Prepare API + KB for https://infigosolutions.com/ embed
# Usage: set DATABASE_URL and LLM_* in .env, then:
#   powershell -ExecutionPolicy Bypass -File scripts/setup_infigo_site.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $env:DATABASE_URL) {
    if (Test-Path ".env") {
        Get-Content ".env" | ForEach-Object {
            if ($_ -match '^\s*DATABASE_URL=(.+)$') { $env:DATABASE_URL = $matches[1].Trim().Trim('"') }
        }
    }
}
if (-not $env:DATABASE_URL) {
    Write-Host "Set DATABASE_URL in .env" -ForegroundColor Red
    exit 1
}

Write-Host "== Schema (if needed) ==" -ForegroundColor Cyan
& "$PSScriptRoot\setup_neon_db.ps1" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "Run setup_neon_db.ps1 manually if this failed." -ForegroundColor Yellow }

Write-Host "== Seed Infigo KB ==" -ForegroundColor Cyan
python "$PSScriptRoot\seed_infigo_kb.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "  1. Add FAQ PDFs via POST /knowledge/file (admin login) or update config/infigo_kb_seed.md and re-run seed."
Write-Host "  2. Set in .env / Vercel: SITE_CONTACT_EMAIL, SITE_BOOKING_URL, PUBLIC_CHAT_API_KEY"
Write-Host "  3. Deploy API; embed on site — see docs/infigo_website_integration.md"
Write-Host "  4. Check GET /integrations/site/status on your API host"
