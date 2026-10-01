# =============================================================
#  One-click launcher - OFFLINE ONLY.
#  Never downloads anything: the packages (venv) and the models are
#  part of the project folder. Only Python 3.13 (64-bit) must be
#  installed on the machine; install-offline.bat is optional and only
#  adds the checks (models, Tesseract, offline flags).
# =============================================================
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "ID / Civil Registry Data Extraction Service"

function Step([string]$msg) {
    Write-Host ""
    Write-Host $msg -ForegroundColor Cyan
}

function Fail([string]$msg) {
    Write-Host ""
    Write-Host $msg -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

# بلا إنترنت: نمنع أي مكتبة من محاولة التحميل أو فحص الاتصال
$env:PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK = "1"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"

Write-Host "-----------------------------------------------------" -ForegroundColor DarkCyan
Write-Host " ID / Civil Registry Data Extraction Service" -ForegroundColor DarkCyan
Write-Host " Offline mode - no internet connection is used" -ForegroundColor DarkCyan
Write-Host "-----------------------------------------------------" -ForegroundColor DarkCyan

# -------------------------------------------------- 1. bundled environment
Step "Step 1/3: Checking the bundled Python environment"
$venvPy = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
$venvCfg = Join-Path $PSScriptRoot "venv\pyvenv.cfg"
if (-not (Test-Path -LiteralPath $venvPy)) {
    Fail @"
The 'venv' folder (with all packages) is missing from this project.

It must be delivered together with the project folder.
Ask the developer for the complete offline package, or run install-offline.bat
after unpacking everything.
"@
}

# venv\pyvenv.cfg stores the absolute path of the Python the environment was
# built from. On any other machine that path is wrong, and the bundled
# python.exe refuses to start - so it is repointed automatically at the
# Python 3.13 (64-bit) installed here. This is what makes the project
# movable: no need to run install-offline.bat before the first start.
# Only 3.13 + 64-bit is accepted, because the compiled packages inside
# venv\ (paddle, opencv, numpy) are built for that exact interpreter.
function Find-Python313 {
    $candidates = @((Get-Command python -ErrorAction SilentlyContinue).Source)
    $candidates += (Get-ChildItem -Path (Join-Path $env:LOCALAPPDATA "Programs\Python") -Filter "python.exe" -Recurse -Depth 1 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $candidates += (Get-ChildItem -Path "C:\" -Filter "python.exe" -Recurse -Depth 1 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $candidates += (Join-Path $env:ProgramFiles "Python313\python.exe")
    foreach ($c in $candidates) {
        if (-not $c -or -not (Test-Path -LiteralPath $c)) { continue }
        $stamp = (& $c -c "import sys,struct; print('%d.%d %d' % (sys.version_info[0], sys.version_info[1], struct.calcsize('P') * 8))" 2>$null | Select-Object -Last 1)
        if ("$stamp".Trim() -eq "3.13 64") { return (Resolve-Path -LiteralPath $c).Path }
    }
    return $null
}

$null = & $venvPy -c "import sys" 2>$null
if ($LASTEXITCODE -ne 0) {
    $base = Find-Python313
    if ($base -and (Test-Path -LiteralPath $venvCfg)) {
        $baseDir = Split-Path -Parent $base
        $cfg = Get-Content -LiteralPath $venvCfg -Raw
        $cfg = $cfg -replace "(?m)^home\s*=\s*.+$", "home = $baseDir"
        $cfg = $cfg -replace "(?m)^executable\s*=\s*.+$", "executable = $base"
        $cfg = $cfg -replace "(?m)^command\s*=\s*.+$", "command = $base -m venv"
        Set-Content -LiteralPath $venvCfg -Value $cfg -NoNewline
        $null = & $venvPy -c "import sys" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "      Environment linked to the Python installed here: $baseDir" -ForegroundColor DarkGray
        }
    }
}
if ($LASTEXITCODE -ne 0) {
    Fail @"
The bundled Python environment cannot start on this machine.

Python 3.13 (64-bit) is required and was not found.
  1) Install it from https://www.python.org/downloads/release/python-3132/
     (tick 'Add python.exe to PATH')
  2) Or put python-3.13.2-amd64.exe in the 'installers' folder and run install-offline.bat
  3) Then start the program again with start.bat
"@
}

# -------------------------------------------------- 2. packages
Step "Step 2/3: Checking the packages"
$probe = "import paddle.inference, paddleocr, fastapi, uvicorn, cv2, pytesseract, multipart, rapidfuzz"
Write-Host "      (the first time on a new machine this can take 1-3 minutes - Windows is preparing the files)" -ForegroundColor DarkGray
$null = & $venvPy -c $probe 2>&1
if ($LASTEXITCODE -ne 0) {
    Fail @"
The bundled packages are missing or damaged.

Usually the cause: the project folder was copied without the 'venv' folder,
or Python 3.13 is not installed on this machine.
Run:  install-offline.bat     (it repairs the paths and re-checks everything)
"@
}
$device = (& $venvPy -c "import paddle; print('GPU (CUDA 12.6)' if paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0 else 'CPU')" 2>&1 | Select-Object -Last 1)
Write-Host "      All packages present - PaddlePaddle runtime: $device" -ForegroundColor DarkGray

# -------------------------------------------------- 3. models
Step "Step 3/3: Checking the AI models"
$modelsDir = Join-Path $PSScriptRoot "models"
$expectedModels = @("PP-OCRv5_mobile_det", "arabic_PP-OCRv5_mobile_rec", "PP-LCNet_x1_0_textline_ori")
$missingModels = @()
foreach ($m in $expectedModels) {
    $dir = Join-Path $modelsDir $m
    if (-not (Test-Path -LiteralPath $dir)) { $missingModels += $m; continue }
    $params = Get-ChildItem -LiteralPath $dir -Filter "inference.pdiparams" -ErrorAction SilentlyContinue
    if (-not $params -or $params[0].Length -lt 1MB) { $missingModels += $m }
}
if ($missingModels.Count -gt 0) {
    Fail @"
Incomplete AI models: $($missingModels -join ', ')

The 'models' folder must be delivered complete with the project.
This program is offline-only and never downloads models.
"@
}
Write-Host "      All 3 models present - no download needed" -ForegroundColor DarkGray

# -------------------------------------------------- 4. serve
$baseUrl = "http://localhost:8000/"

try {
    $existing = Invoke-WebRequest -Uri $baseUrl -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    if ($existing.StatusCode -eq 200) {
        Write-Host "The server is already running. Opening the app now." -ForegroundColor Green
        Start-Process $baseUrl
        Read-Host "`nPress Enter to close"
        exit 0
    }
} catch { }

Write-Host ""
Write-Host "Starting the server at: $baseUrl"
Write-Host "The app will open automatically once the server is ready (model loading may take 30-60 seconds)."
Write-Host "To stop the server later: press Ctrl+C in this window or close it."

$poll = Start-Job -ScriptBlock {
    param($url)
    for ($i = 0; $i -lt 180; $i++) {
        try {
            $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
            if ($r.StatusCode -eq 200) {
                Start-Process $url
                break
            }
        } catch { }
        Start-Sleep -Seconds 2
    }
} -ArgumentList $baseUrl

# python -m uvicorn (not uvicorn.exe): the module launcher keeps working when the
# project folder is moved to another machine, the .exe wrappers do not.
& $venvPy -m uvicorn api:app --host 0.0.0.0 --port 8000

Remove-Job $poll -Force -ErrorAction SilentlyContinue
Write-Host "Server stopped."
Read-Host "Press Enter to close"
