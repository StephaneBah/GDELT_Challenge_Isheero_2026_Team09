$root = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Test-Path "$root\.env")) {
    Write-Host "Fichier .env introuvable. Copier .env.example en .env et renseigner ANTHROPIC_API_KEY." -ForegroundColor Red
    exit 1
}

Write-Host "Installation des dependances..." -ForegroundColor Cyan
pip install -r "$root\requirements.txt" -q

Write-Host "Echo Media demarre sur http://localhost:8000" -ForegroundColor Green

Set-Location "$root\api"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
