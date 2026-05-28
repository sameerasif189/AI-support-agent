$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

& "C:\Users\PC\miniconda3\python.exe" -m pip install -r "$ProjectRoot\requirements.txt"
# --reload on Windows breaks psycopg async pool (login hangs); restart manually after code changes
& "C:\Users\PC\miniconda3\python.exe" "$ProjectRoot\scripts\run_uvicorn.py" app.main:app --host 0.0.0.0 --port 8000
