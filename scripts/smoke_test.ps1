$base = "http://127.0.0.1:8000"
Invoke-RestMethod -Uri "$base/health" -Method GET
Invoke-RestMethod -Uri "$base/chat" -Method POST -ContentType "application/json" -Body (@{
  user_id = "1"
  channel = "web"
  message = "where can I download my invoice copy?"
} | ConvertTo-Json)
