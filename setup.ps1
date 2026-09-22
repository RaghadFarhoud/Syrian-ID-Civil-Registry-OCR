$ErrorActionPreference = "Stop"

Write-Host "1. Python checking" -ForegroundColor Cyan
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "python does not exist, download it from https://python.org and make sure to point (Add python.exe to PATH) during installation" -ForegroundColor Red
    exit 1
}

Write-Host "2. creating virtual environment (venv)" -ForegroundColor Cyan
if (-not (Test-Path "venv")) {
    python -m venv venv
}

$venvPython = ".\venv\Scripts\python.exe"
$venvPip = ".\venv\Scripts\pip.exe"

Write-Host "3. updating pip" -ForegroundColor Cyan
& $venvPip install --upgrade pip

Write-Host "4. installing project dependencies (Tesseract wrapper + PaddleOCR)" -ForegroundColor Cyan
& $venvPip install -r requirements.txt

Write-Host "5. downloading PaddleOCR models (for each device only once)" -ForegroundColor Cyan
if (-not (Test-Path "models")) {
    & $venvPython scripts\download_paddle_models.py
} else {
    Write-Host "models folder already exists - skipping."
}

Write-Host "6. checking Tesseract" -ForegroundColor Cyan
$tesseractPath = "C:\Program Files\Tesseract-OCR\tesseract.exe"
if (-not (Test-Path $tesseractPath)) {
    Write-Host "Warning: Tesseract is not installed in the default path ($tesseractPath)." -ForegroundColor Yellow
    Write-Host "Download it from: https://github.com/UB-Mannheim/tesseract/wiki (Make sure to select Arabic during installation)"
}

Write-Host ""
Write-Host "7. to run API:" -ForegroundColor Green
Write-Host "  .\venv\Scripts\Activate.ps1"
Write-Host "  uvicorn api:app --host 0.0.0.0 --port 8000"