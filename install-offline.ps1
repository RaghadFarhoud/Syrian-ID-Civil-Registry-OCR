# =============================================================
#  Offline installer - runs once on the client machine, NO internet needed
#  (English console so it is readable on any Windows locale)
# =============================================================
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$VenvDir = Join-Path $Root "venv"
$VenvPy = Join-Path $VenvDir "Scripts\python.exe"
$VenvCfg = Join-Path $VenvDir "pyvenv.cfg"
$InstallerDir = Join-Path $Root "installers"

function Say([string]$msg, [string]$color = "Gray") {
    Write-Host $msg -ForegroundColor $color
}
function Ok([string]$msg) { Say "[ OK ] $msg" "Green" }
function Warn([string]$msg) { Say "[WARN] $msg" "Yellow" }
function Die([string]$msg) {
    Say ""
    Say "[FAIL] $msg" "Red"
    Say ""
    Read-Host "Press Enter to close"
    exit 1
}

Say "-----------------------------------------------------" "DarkCyan"
Say " Offline setup - ID / Civil Registry Extraction" "DarkCyan"
Say "-----------------------------------------------------" "DarkCyan"
Say ""

# ---------------------------------------------------------------- 1. python
Say "1/5  Checking the bundled Python environment" "Cyan"
if (-not (Test-Path -LiteralPath $VenvPy)) {
    Die "venv\Scripts\python.exe is missing. The 'venv' folder was not sent with this package - ask for the full offline package."
}

# A venv remembers the absolute path of the Python it was built from
# (venv\pyvenv.cfg -> home = ...). Since this project is unpacked on someone
# else's machine, that line is rewritten to the Python installed here.
# Only Python 3.13 64-bit is accepted: the compiled packages inside venv\
# (paddle, opencv, numpy) are built for that exact interpreter.
function Find-BasePython {
    $candidates = @(
        (Get-Command python -ErrorAction SilentlyContinue).Source
    )
    $candidates += (Get-ChildItem -Path (Join-Path $env:LOCALAPPDATA "Programs\Python") -Filter "python.exe" -Recurse -Depth 1 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $candidates += (Get-ChildItem -Path "C:\" -Filter "python.exe" -Recurse -Depth 1 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $candidates += (Join-Path $env:ProgramFiles "Python313\python.exe")

    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    foreach ($c in $candidates) {
        if (-not $c -or -not (Test-Path -LiteralPath $c)) { continue }
        $stamp = (& $c -c "import sys,struct; print('%d.%d %d' % (sys.version_info[0], sys.version_info[1], struct.calcsize('P') * 8))" 2>$null | Select-Object -Last 1)
        if ("$stamp".Trim() -eq "3.13 64") {
            $ErrorActionPreference = $prevEap
            return (Resolve-Path -LiteralPath $c).Path
        }
    }
    $ErrorActionPreference = $prevEap
    return $null
}

$cfg = Get-Content -LiteralPath $VenvCfg -Raw
$expected = ([regex]::Match($cfg, "(?m)^version\s*=\s*(\S+)")).Groups[1].Value
# $HOME is a read-only PowerShell variable, so this one is named differently
$venvHome = ([regex]::Match($cfg, "(?m)^home\s*=\s*(.+)$")).Groups[1].Value.Trim()
$venvExe = ([regex]::Match($cfg, "(?m)^executable\s*=\s*(.+)$")).Groups[1].Value.Trim()

$base = Find-BasePython
if ($base) {
    $baseDir = Split-Path -Parent $base
    if ($baseDir -ne $venvHome) {
        Say "      Repointing the environment to: $baseDir" "DarkGray"
        $cfg = $cfg -replace "(?m)^home\s*=\s*.+$", "home = $baseDir"
        $cfg = $cfg -replace "(?m)^executable\s*=\s*.+$", "executable = $base"
        $cfg = $cfg -replace "(?m)^command\s*=\s*.+$", "command = $base -m venv"
        Set-Content -LiteralPath $VenvCfg -Value $cfg -NoNewline
    }
    Ok "Python 3.13 found at $base"
} elseif (Test-Path -LiteralPath $venvExe) {
    Ok "Python found at $venvExe (kept from pyvenv.cfg)"
} else {
    if (Test-Path -LiteralPath (Join-Path $InstallerDir "python-3.13.2-amd64.exe")) {
        Warn "Python 3.13 is not installed on this machine."
        Warn "Installing the bundled installer silently (a few minutes)..."
        $setup = Join-Path $InstallerDir "python-3.13.2-amd64.exe"
        $proc = Start-Process -FilePath $setup -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_pip=1", "Include_tcltk=0", "Include_test=0" -Wait -PassThru
        if ($proc.ExitCode -ne 0) { Die "The bundled Python installer failed (exit code $($proc.ExitCode))." }
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        $base = Find-BasePython
        if (-not $base) { Die "Python was installed but could not be located. Restart Windows and run install-offline.bat again." }
        $baseDir = Split-Path -Parent $base
        $cfg = $cfg -replace "(?m)^home\s*=\s*.+$", "home = $baseDir"
        $cfg = $cfg -replace "(?m)^executable\s*=\s*.+$", "executable = $base"
        $cfg = $cfg -replace "(?m)^command\s*=\s*.+$", "command = $base -m venv"
        Set-Content -LiteralPath $VenvCfg -Value $cfg -NoNewline
        Ok "Python installed at $baseDir"
    } else {
        Die @"
Python 3.13 ($expected) is not installed on this machine and no installer was included.

Install Python 3.13.2 (64-bit) from python.org, tick 'Add python.exe to PATH',
then run install-offline.bat again.
"@
    }
}

# ---------------------------------------------------------------- 2. packages
Say "2/5  Verifying the bundled packages (no download)" "Cyan"
$probe = @'
import sys
mods = ["paddle", "paddle.inference", "paddleocr", "paddlex", "fastapi",
        "uvicorn", "pytesseract", "cv2", "PIL", "numpy", "rapidfuzz", "multipart"]
missing = []
for m in mods:
    try:
        __import__(m)
    except Exception as exc:
        missing.append(f"{m} ({type(exc).__name__}: {exc})")
if missing:
    print("MISSING:" + "|".join(missing))
    sys.exit(1)
import paddle
print("OK " + paddle.__version__ + " cuda=" + str(paddle.device.is_compiled_with_cuda()))
'@
$probeFile = Join-Path $env:TEMP "idextract_probe.py"
Set-Content -LiteralPath $probeFile -Value $probe -Encoding UTF8
# Paddle writes notes/warnings to stderr; under ErrorActionPreference=Stop Windows
# PowerShell would turn those into a fatal error, so the preference is relaxed here.
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
$out = & $VenvPy $probeFile 2>&1
$probeExit = $LASTEXITCODE
$ErrorActionPreference = $prevEap
if ($probeExit -ne 0) {
    Say (($out | ForEach-Object { "$_" }) -join "`n")
    Remove-Item -LiteralPath $probeFile -Force -ErrorAction SilentlyContinue
    Die "Some packages are missing or broken. The 'venv' folder was not sent complete - ask for the full offline package."
}
$line = ($out | ForEach-Object { "$_" } | Where-Object { $_ -match "^OK " } | Select-Object -Last 1)
if (-not $line) {
    Remove-Item -LiteralPath $probeFile -Force -ErrorAction SilentlyContinue
    Die "The package check did not report back. Re-send the 'venv' folder - ask for the full offline package."
}
$parts = $line.Trim() -split "\s+"
Say "      PaddlePaddle $($parts[1]), CUDA available: $($parts[2])" "DarkGray"
if ($parts[2] -eq "cuda=False") {
    Warn "No GPU in this build / no NVIDIA card detected - the program still works on the CPU (slower)."
} else {
    Ok "GPU build active (paddlepaddle-gpu, CUDA 12.6 bundled - no CUDA install needed)"
}
Remove-Item -LiteralPath $probeFile -Force -ErrorAction SilentlyContinue

# ---------------------------------------------------------------- 3. models
Say "3/5  Checking the AI models" "Cyan"
$models = @("PP-OCRv5_mobile_det", "arabic_PP-OCRv5_mobile_rec", "PP-LCNet_x1_0_textline_ori")
$missingModels = @()
foreach ($m in $models) {
    $dir = Join-Path $Root "models\$m"
    if (-not (Test-Path -LiteralPath $dir)) { $missingModels += $m; continue }
    $params = Get-ChildItem -LiteralPath $dir -Filter "inference.pdiparams" -ErrorAction SilentlyContinue
    if (-not $params -or $params[0].Length -lt 1MB) { $missingModels += "$m (inference.pdiparams missing/empty)" }
}
if ($missingModels.Count -gt 0) {
    Die "Incomplete models: $($missingModels -join ', ')`nThe 'models' folder was not sent complete - ask for the full offline package."
}
Ok "All 3 models present"

# ---------------------------------------------------------------- 4. tesseract
Say "4/5  Checking Tesseract (rotation + digits)" "Cyan"
$localTess = @(
    (Join-Path $Root "tesseract\tesseract.exe"),
    (Join-Path $Root "tesseract\bin\tesseract.exe")
) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if ($localTess) {
    Ok "Portable copy found: $localTess"
} elseif (Test-Path "C:\Program Files\Tesseract-OCR\tesseract.exe") {
    Ok "Installed at C:\Program Files\Tesseract-OCR"
} else {
    $installer = Get-ChildItem -LiteralPath $InstallerDir -Filter "tesseract*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($installer) {
        Warn "Tesseract is not installed - running the bundled installer silently."
        $null = Start-Process -FilePath $installer.FullName -ArgumentList "/S" -Wait -PassThru
        if (Test-Path "C:\Program Files\Tesseract-OCR\tesseract.exe") {
            Ok "Tesseract installed"
        } else {
            Warn "Tesseract installer did not put tesseract.exe in the default folder. Open the program and pick Arabic (ara) + English (eng) + OSD during install, then re-run install-offline.bat."
        }
    } else {
        Warn "Tesseract not found. Extraction still runs, but rotation correction and a few digit fields get weaker. Install Tesseract with the Arabic (ara) and English (eng) languages."
    }
}

# ---------------------------------------------------------------- 5. done
Say "5/5  Offline environment variables" "Cyan"
$offline = @(
    "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=1",
    "HF_HUB_OFFLINE=1",
    "TRANSFORMERS_OFFLINE=1"
)
foreach ($pair in $offline) {
    $name = $pair.Split("=")[0]
    [System.Environment]::SetEnvironmentVariable($name, $pair.Split("=")[1], "User")
}
Ok "Paddle/HuggingFace forced offline for this Windows account"

Say ""
Say "-----------------------------------------------------" "DarkCyan"
Say " Setup finished. This program never uses the internet." "Green"
Say "-----------------------------------------------------" "Green"
Say "  1. You can now disconnect the network / block the internet."
Say "  2. Start the app by double-clicking:  start.bat"
Say "  3. The page opens automatically at:     http://localhost:8000/"
Say ""
Read-Host "Press Enter to close"
exit 0
