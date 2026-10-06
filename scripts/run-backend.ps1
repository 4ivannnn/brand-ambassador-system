$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Backend environment not found. Create it with: uv venv --python 3.14 .venv; then install dependencies with: uv pip install --python .venv\Scripts\python.exe -r requirements.txt"
}

if (-not (Test-NetConnection -ComputerName localhost -Port 5432 -InformationLevel Quiet -WarningAction SilentlyContinue)) {
    throw "PostgreSQL is not listening on localhost:5432. Start PostgreSQL, or start Docker Desktop and run 'docker compose up -d db', then try again."
}

& $python -m scripts.bootstrap
if ($LASTEXITCODE -ne 0) { throw "Backend bootstrap failed. Check DATABASE_URL in .env and confirm database/schema.sql was applied to an empty PostgreSQL database." }

& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
