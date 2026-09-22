# سكربت إعداد المشروع على لابتوب Windows: يعمل venv، يثبت المتطلبات، وينزّل موديلات paddle
# تشغيل: افتح PowerShell بمجلد المشروع واكتب: .\setup.ps1
# إذا طلع خطأ "running scripts is disabled" اول مرة، شغّل هالأمر مرة وحدة:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

$ErrorActionPreference = "Stop"

Write-Host "== 1. التحقق من Python ==" -ForegroundColor Cyan
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "python غير موجود. نزّله من https://python.org وتأكد تأشر (Add python.exe to PATH) أثناء التثبيت." -ForegroundColor Red
    exit 1
}

Write-Host "== 2. إنشاء بيئة افتراضية (venv) ==" -ForegroundColor Cyan
if (-not (Test-Path "venv")) {
    python -m venv venv
}

$venvPython = ".\venv\Scripts\python.exe"
$venvPip = ".\venv\Scripts\pip.exe"

Write-Host "== 3. تحديث pip ==" -ForegroundColor Cyan
& $venvPip install --upgrade pip

Write-Host "== 4. تثبيت متطلبات المشروع (Tesseract wrapper + PaddleOCR) ==" -ForegroundColor Cyan
& $venvPip install -r requirements.txt

Write-Host "== 5. تنزيل موديلات PaddleOCR (لمرة وحدة فقط لكل جهاز) ==" -ForegroundColor Cyan
if (-not (Test-Path "models")) {
    & $venvPython core\download_paddle_models.py
} else {
    Write-Host "مجلد models موجود مسبقاً - تم التخطي."
}

Write-Host "== 6. التحقق من Tesseract ==" -ForegroundColor Cyan
$tesseractPath = "C:\Program Files\Tesseract-OCR\tesseract.exe"
if (-not (Test-Path $tesseractPath)) {
    Write-Host "تحذير: Tesseract غير مثبت بالمسار الافتراضي ($tesseractPath)." -ForegroundColor Yellow
    Write-Host "نزّله من: https://github.com/UB-Mannheim/tesseract/wiki (تأكد تختار Arabic بوقت التثبيت)"
}

Write-Host ""
Write-Host "الإعداد اكتمل. لتشغيل الـ API:" -ForegroundColor Green
Write-Host "  .\venv\Scripts\Activate.ps1"
Write-Host "  uvicorn api:app --host 0.0.0.0 --port 8000"
