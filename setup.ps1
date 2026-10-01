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
& $venvPython -m pip install --upgrade pip

Write-Host "4. installing project dependencies (Paddle is installed in the next step: GPU or CPU)" -ForegroundColor Cyan
& $venvPip install -r requirements.txt

# Detect NVIDIA GPU (nvidia-smi present and responding)
$gpuDetected = $false
$smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($smi) {
    $null = & $smi.Source --query-gpu=name --format=csv,noheader 2>&1
    $gpuDetected = ($LASTEXITCODE -eq 0)
}

# Paddle runtime: GPU build when an NVIDIA GPU exists (CUDA 12.6, bundles its own CUDA),
# otherwise the CPU build. Exactly one of the two is installed.
# If you already downloaded the big GPU wheel, it is used as-is (no re-download):
# the "wheels" folder of this project first, then the Downloads folder.
$stagedWheel = @(
    (Get-ChildItem -Path (Join-Path $PSScriptRoot "wheels") -Filter "paddlepaddle_gpu*.whl" -ErrorAction SilentlyContinue),
    (Get-ChildItem -Path (Join-Path $env:USERPROFILE "Downloads") -Filter "paddlepaddle_gpu*.whl" -ErrorAction SilentlyContinue)
) | Sort-Object Length -Descending | Select-Object -First 1
$sitePackages = (& $venvPython -c "import sysconfig; print(sysconfig.get_paths()['purelib'])" 2>$null)

# paddlepaddle and paddlepaddle-gpu write into the SAME "paddle" folder, so a leftover copy
# of the other build silently breaks the install (the server then dies with
# "No module named 'paddle.inference'"). So both are always removed together, folder
# included, before installing one - and a build only counts as installed if it imports.
function Test-Paddle([string]$dist) {
    # Paddle prints warnings on stderr, so the preference is relaxed around the probe,
    # otherwise "Stop" would turn a normal warning into a terminating error.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    $null = & $venvPython -c "import importlib.metadata as m, paddle, paddle.inference; assert m.version('$dist')" 2>&1
    $ok = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prev
    return $ok
}

function Clear-Paddle {
    & $venvPython -m pip uninstall -y paddlepaddle paddlepaddle-gpu 2>&1 | Out-Null
    if ($sitePackages) {
        if (Test-Path -LiteralPath (Join-Path $sitePackages "paddle")) {
            Remove-Item -Recurse -Force -LiteralPath (Join-Path $sitePackages "paddle") -ErrorAction SilentlyContinue
        }
        Get-ChildItem -LiteralPath $sitePackages -Filter "paddlepaddle*.dist-info" -Directory -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Install-PaddleCpu {
    Clear-Paddle
    & $venvPip install paddlepaddle==3.3.1 2>&1 | Out-Null
    if (-not (Test-Paddle "paddlepaddle")) {
        Write-Host "Failed to install CPU PaddlePaddle. Check your internet connection and try again." -ForegroundColor Red
        exit 1
    }
    return $true
}

function Install-PaddleGpu {
    Clear-Paddle
    if ($stagedWheel) {
        & $venvPip install $stagedWheel.FullName 2>&1 | Out-Null
    } else {
        & $venvPip install --timeout 180 --retries 5 "paddlepaddle-gpu==3.3.1" -i "https://www.paddlepaddle.org.cn/packages/stable/cu126/" 2>&1 | Out-Null
    }
    return (Test-Paddle "paddlepaddle-gpu")
}

if ($gpuDetected) {
    if (Test-Paddle "paddlepaddle-gpu") {
        Write-Host "     PaddlePaddle runtime: GPU (CUDA 12.6)" -ForegroundColor Green
    } else {
        if ($stagedWheel) {
            Write-Host "5. NVIDIA GPU detected + local wheel found - installing GPU PaddlePaddle from wheel (no download)" -ForegroundColor Cyan
        } else {
            Write-Host "5. NVIDIA GPU detected - installing GPU-accelerated PaddlePaddle (CUDA 12.6, large download, one-time only)" -ForegroundColor Cyan
        }
        if (Install-PaddleGpu) {
            Write-Host "     PaddlePaddle runtime: GPU (CUDA 12.6)" -ForegroundColor Green
        } else {
            Write-Host "     GPU install failed (network?) - falling back to CPU." -ForegroundColor Yellow
            Install-PaddleCpu
            Write-Host "     PaddlePaddle runtime: CPU" -ForegroundColor Yellow
        }
    }
} else {
    if (-not (Test-Paddle "paddlepaddle")) {
        Write-Host "5. no NVIDIA GPU detected - installing CPU PaddlePaddle" -ForegroundColor Cyan
        Install-PaddleCpu
    }
    Write-Host "     PaddlePaddle runtime: CPU" -ForegroundColor Green
}

Write-Host "6. downloading PaddleOCR models (for each device only once)" -ForegroundColor Cyan
$expectedModels = @("PP-OCRv5_mobile_det", "arabic_PP-OCRv5_mobile_rec", "PP-LCNet_x1_0_textline_ori")
$allModelsPresent = $true
foreach ($m in $expectedModels) {
    if (-not (Test-Path (Join-Path "models" $m))) { $allModelsPresent = $false }
}
if (-not $allModelsPresent) {
    & $venvPython scripts\download_paddle_models.py
} else {
    Write-Host "models already exist - skipping."
}

Write-Host "7. checking Tesseract" -ForegroundColor Cyan
$tesseractPath = "C:\Program Files\Tesseract-OCR\tesseract.exe"
if (-not (Test-Path $tesseractPath)) {
    Write-Host "Warning: Tesseract is not installed in the default path ($tesseractPath)." -ForegroundColor Yellow
    Write-Host "Download it from: https://github.com/UB-Mannheim/tesseract/wiki (Make sure to select Arabic during installation)"
}

Write-Host ""
Write-Host "8. to run API:" -ForegroundColor Green
Write-Host "  .\venv\Scripts\Activate.ps1"
Write-Host "  uvicorn api:app --host 0.0.0.0 --port 8000"