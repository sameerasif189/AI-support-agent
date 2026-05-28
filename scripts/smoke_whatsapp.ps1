# Smoke-test WhatsApp integration (local or Vercel URL).
# Usage: powershell -File scripts/smoke_whatsapp.ps1
#        powershell -File scripts/smoke_whatsapp.ps1 -BaseUrl https://your-app.vercel.app

param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$VerifyToken = "erp-ai-verify"
)

$ErrorActionPreference = "Stop"

Write-Host "Status: $BaseUrl/integrations/whatsapp/status" -ForegroundColor Cyan
$status = Invoke-RestMethod -Uri "$BaseUrl/integrations/whatsapp/status" -Method GET
$status | ConvertTo-Json

Write-Host "`nWebhook verify (GET) ..." -ForegroundColor Cyan
$challenge = "smoke-test-challenge-123"
$verifyUri = "$BaseUrl/channels/whatsapp?hub.mode=subscribe&hub.verify_token=$VerifyToken&hub.challenge=$challenge"
$resp = Invoke-WebRequest -Uri $verifyUri -Method GET -UseBasicParsing
if ($resp.Content -ne $challenge) {
    throw "Verify failed: expected '$challenge', got '$($resp.Content)'"
}
Write-Host "Verify OK" -ForegroundColor Green

Write-Host "`nLegacy chat webhook (POST) ..." -ForegroundColor Cyan
$body = @{ from = "1"; message = "What are your support hours?" } | ConvertTo-Json
$result = Invoke-RestMethod -Uri "$BaseUrl/channels/whatsapp" -Method POST -ContentType "application/json" -Body $body
$result | ConvertTo-Json -Depth 5
Write-Host "Smoke complete." -ForegroundColor Green
