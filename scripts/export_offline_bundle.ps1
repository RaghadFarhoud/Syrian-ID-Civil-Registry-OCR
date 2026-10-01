# =============================================================
#  Builds the offline package to hand over to the client.
#  Run this on a machine WITH internet, once, before delivery:
#
#     powershell -ExecutionPolicy Bypass -File scripts\export_offline_bundle.ps1
#     powershell -ExecutionPolicy Bypass -File scripts\export_offline_bundle.ps1 -Zip
#
#  -Zip also produces  ID-Extraction-Offline.zip  next to the project.
#  Everything the client needs is already inside the project folder
#  (venv\ = all packages, models\ = the AI models).
# =============================================================
param(
    [switch]$Zip,
    [string]$OutputDir = ""
)
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $Root "venv"
$SitePackages = Join-Path $Venv "Lib\site-packages"
$Models = Join-Path $Root "models"
$Installers = Join-Path $Root "installers"

function Step([string]$m) { Write-Host ""; Write-Host $m -ForegroundColor Cyan }
function Ok([string]$m) { Write-Host "[ OK ] $m" -ForegroundColor Green }
function Warn([string]$m) { Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Die([string]$m) { Write-Host ""; Write-Host "[FAIL] $m" -ForegroundColor Red; exit 1 }
function SizeOf($p) {
    if (-not (Test-Path -LiteralPath $p)) { return 0 }
    return (Get-ChildItem -LiteralPath $p -Recurse -File -Force -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum
}
function Mb([double]$b) { return [math]::Round($b / 1MB, 1) }
function Gb([double]$b) { return [math]::Round($b / 1GB, 2) }
function Fmt([double]$b) {
    if ($b -ge 1GB) { return "$(Gb $b) GB" }
    if ($b -ge 1MB) { return "$(Mb $b) MB" }
    return "$([math]::Round($b / 1KB, 1)) KB"
}

Write-Host "-----------------------------------------------------" -ForegroundColor DarkCyan
Write-Host " Building the offline package" -ForegroundColor DarkCyan
Write-Host "-----------------------------------------------------" -ForegroundColor DarkCyan

# ------------------------------------------------------------- 1. packages
Step "1. Checking the bundled packages (venv)"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPy)) { Die "venv\Scripts\python.exe not found - run setup.ps1 first (needs internet)." }

$pkgs = & $VenvPy -m pip list --format=freeze 2>$null
if (-not $pkgs) { Die "pip could not list the packages of the venv." }
$paddleLine = ($pkgs | Select-String -Pattern "^paddlepaddle" | Select-Object -First 1)
if (-not $paddleLine) { Die "paddlepaddle is not installed in the venv - run setup.ps1 (or run.ps1) first." }
Ok "$($pkgs.Count) packages installed, including $($paddleLine.ToString())"

# ------------------------------------------------------------- 2. cleanup
Step "2. Removing leftovers so the package is smaller"
# "~addle" is a half-deleted copy of paddle left behind by an old
# paddlepaddle/paddlepaddle-gpu swap. It is dead weight (~320 MB).
Get-ChildItem -LiteralPath $SitePackages -Directory -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "~*" -and $_.Name -notin @("~ip") } |
    ForEach-Object {
        $mb = Mb (SizeOf $_.FullName)
        Remove-Item -Recurse -Force -LiteralPath $_.FullName -ErrorAction SilentlyContinue
        if (-not (Test-Path -LiteralPath $_.FullName)) { Ok "removed $($_.Name) ($mb MB)" }
    }
# __pycache__ / *.pyc are rebuilt on the client's machine
Get-ChildItem -LiteralPath $Venv -Recurse -Directory -Filter "__pycache__" -Force -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -LiteralPath $Root -Recurse -File -Filter "*.pyc" -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch "\\venv\\Lib\\site-packages\\[^\\]+\\" } |
    Remove-Item -Force -ErrorAction SilentlyContinue
# .cache\huggingface inside the model folders is only download bookkeeping
Get-ChildItem -LiteralPath $Models -Recurse -Directory -Filter ".cache" -Force -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
# noise
foreach ($f in @("server.log", "server_err.log", "result.json")) {
    $p = Join-Path $Root $f
    if (Test-Path -LiteralPath $p) { Remove-Item -Force -LiteralPath $p; Ok "removed $f" }
}
# the dev machine's own path must not stay inside the venv config
$cfg = Join-Path $Venv "pyvenv.cfg"
if (Test-Path -LiteralPath $cfg) {
    (Get-Content -LiteralPath $cfg) |
        Where-Object { $_ -notmatch "^command\s*=" } |
        Set-Content -LiteralPath $cfg
    Ok "cleaned venv\pyvenv.cfg (the client's installer rewrites the paths anyway)"
}

# ------------------------------------------------------------- 3. models
Step "3. Checking the AI models"
$expected = @("PP-OCRv5_mobile_det", "arabic_PP-OCRv5_mobile_rec", "PP-LCNet_x1_0_textline_ori")
$missing = @()
foreach ($m in $expected) {
    $d = Join-Path $Models $m
    $params = Join-Path $d "inference.pdiparams"
    if ((-not (Test-Path -LiteralPath $d)) -or -not (Test-Path -LiteralPath $params) -or (Get-Item $params).Length -lt 1MB) {
        $missing += $m
    }
}
if ($missing.Count -gt 0) {
    Warn "missing models: $($missing -join ', ')"
    Warn "downloading them now (this machine needs internet for this step only)..."
    & $VenvPy (Join-Path $Root "scripts\download_paddle_models.py")
    if ($LASTEXITCODE -ne 0) { Die "model download failed." }
}
foreach ($m in $expected) { Ok "$m  ($(Mb (SizeOf (Join-Path $Models $m))) MB)" }

# ------------------------------------------------------------- 4. tesseract
Step "4. Tesseract (needed for rotation + some digit fields)"
$source = "C:\Program Files\Tesseract-OCR"
if (Test-Path -LiteralPath (Join-Path $source "tesseract.exe")) {
    $dest = Join-Path $Root "tesseract"
    if (Test-Path -LiteralPath $dest) { Remove-Item -Recurse -Force -LiteralPath $dest }
    New-Item -ItemType Directory -Path $dest -Force | Out-Null
    # the exe + its DLLs + tessdata (ara/eng/osd) - so the client needs no installer
    Get-ChildItem -LiteralPath $source -File | Where-Object { $_.Extension -in @(".exe", ".dll") } |
        Copy-Item -Destination $dest -Force
    Copy-Item -LiteralPath (Join-Path $source "tessdata") -Destination $dest -Recurse -Force
    $kept = Get-ChildItem -LiteralPath (Join-Path $dest "tessdata") -Filter "*.traineddata" |
        Where-Object { $_.BaseName -in @("ara", "eng", "osd") }
    Get-ChildItem -LiteralPath (Join-Path $dest "tessdata") -Filter "*.traineddata" |
        Where-Object { $_.BaseName -notin @("ara", "eng", "osd") } |
        Remove-Item -Force
    Ok "portable Tesseract copied into tesseract\ ($((Mb (SizeOf $dest))) MB) - languages: $($kept.BaseName -join ', ')"
} else {
    Warn "Tesseract is not installed on this machine."
    Warn "Install it with the Arabic (ara) + English (eng) languages, then re-run this script,"
    Warn "or drop its installer into installers\ before delivering."
}

# ------------------------------------------------------------- 5. python installer
Step "5. Optional: bundling the Python installer for the client"
if (-not (Test-Path -LiteralPath $Installers)) { New-Item -ItemType Directory -Path $Installers -Force | Out-Null }
$pyExe = (Get-Content -LiteralPath $cfg | Select-String -Pattern "^executable\s*=").ToString().Split("=")[1].Trim()
if ($pyExe -and (Test-Path -LiteralPath $pyExe)) {
    $ver = & $pyExe -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
    $target = Join-Path $Installers "python-$ver-amd64.exe"
    if (Test-Path -LiteralPath $target) {
        Ok "already there: installers\python-$ver-amd64.exe"
    } else {
        Warn "put the official installer here first:  python-$ver-amd64.exe"
        Warn "download it once from https://www.python.org/downloads/release/python-$ver/"
        Warn "(only needed if the client has no Python at all - otherwise send the version number instead)"
    }
} else {
    Warn "could not read the base python from venv\pyvenv.cfg"
}

# ------------------------------------------------------------- 6. report
Step "6. What the client receives"
$files = @(
    "api.py", "main.py", "requirements.txt", "start.bat", "install-offline.bat",
    "install-offline.ps1", "run.ps1", "README.md", "core", "pipelines",
    "static", "extension", "models", "venv", "tesseract", "installers"
)
foreach ($f in $files) {
    $p = Join-Path $Root $f
    if (Test-Path -LiteralPath $p) {
        Write-Host ("      {0,-24} {1}" -f $f, (Fmt (SizeOf $p))) -ForegroundColor DarkGray
    } else {
        Write-Host ("      {0,-24} (not present)" -f $f) -ForegroundColor DarkYellow
    }
}
$total = Gb (SizeOf $Root)
Write-Host ""
Ok "total: $total GB (zipped it is noticeably smaller)"
$ver = (& $VenvPy -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null | Select-Object -Last 1)
if ($ver) { Ok "the client needs Python $ver (64-bit) - the installer script repairs the paths automatically" }

# ------------------------------------------------------------- 7. zip
if ($Zip) {
    Step "7. Creating the zip"
    if (-not $OutputDir) { $OutputDir = Split-Path -Parent $Root }
    $zipPath = Join-Path $OutputDir "ID-Extraction-Offline.zip"
    if (Test-Path -LiteralPath $zipPath) { Remove-Item -Force -LiteralPath $zipPath }
    Compress-Archive -Path (Join-Path $Root "*") -DestinationPath $zipPath -CompressionLevel Optimal -Force
    Ok "$zipPath  ($(Gb (Get-Item $zipPath).Length) GB)"
    Warn "send the zip with a USB drive or a local disk - do NOT use an email/gmail (it blocks large attachments)"
}

Write-Host ""
Write-Host "Done. Send the project folder (or the zip) to the client." -ForegroundColor Green
Write-Host ""
