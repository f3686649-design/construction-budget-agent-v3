$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if (-not (Test-Path ".\.venv\Scripts\streamlit.exe")) {
    Write-Host "Виртуальное окружение не найдено. Создайте .venv и установите зависимости из requirements.txt." -ForegroundColor Yellow
    exit 1
}

Write-Host "Запускаю Construction Budget Agent v3..." -ForegroundColor Green
Write-Host "Откройте в браузере: http://localhost:8501" -ForegroundColor Cyan

.\.venv\Scripts\streamlit.exe run app.py --server.address 0.0.0.0 --server.port 8501
