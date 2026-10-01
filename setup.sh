set -e

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="venv"

echo "1. check python"
command -v "$PYTHON_BIN" >/dev/null || { echo "python3 does not exist"; exit 1; }

echo "2.creating venv"
if [ ! -d "$VENV_DIR" ]; then
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "3.upgrade pip"
pip install --upgrade pip

echo "4. installing project dependencies (Paddle is installed in the next step: GPU or CPU)"
pip install -r requirements.txt

# Detect an NVIDIA GPU via nvidia-smi
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi --query-gpu=name --format=csv,noheader >/dev/null 2>&1; then
    # Find a locally staged GPU wheel if present (drop it in "wheels/" to skip the download)
    STAGED=""
    for w in wheels/paddlepaddle_gpu-*.whl; do
        if [ -f "$w" ]; then STAGED="$w"; break; fi
    done

    pip uninstall -y paddlepaddle >/dev/null 2>&1 || true
    if pip show paddlepaddle-gpu >/dev/null 2>&1; then
        echo "     PaddlePaddle runtime: GPU (CUDA 12.6)"
    elif [ -n "$STAGED" ]; then
        echo "5. NVIDIA GPU detected + local wheel - installing GPU PaddlePaddle from wheel..."
        if pip install "$STAGED"; then
            echo "     PaddlePaddle runtime: GPU (CUDA 12.6)"
        else
            echo "     GPU install failed - falling back to CPU."
            pip install paddlepaddle==3.3.1
            echo "     PaddlePaddle runtime: CPU"
        fi
    else
        echo "5. NVIDIA GPU detected - installing GPU-accelerated PaddlePaddle (CUDA 12.6, large download, one-time only)"
        if pip install --timeout 120 --retries 5 paddlepaddle-gpu==3.3.1 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/; then
            echo "     PaddlePaddle runtime: GPU (CUDA 12.6)"
        else
            echo "     GPU install failed (network?) - falling back to CPU."
            pip install paddlepaddle==3.3.1
            echo "     PaddlePaddle runtime: CPU"
        fi
    fi
else
    pip uninstall -y paddlepaddle-gpu >/dev/null 2>&1 || true
    if ! pip show paddlepaddle >/dev/null 2>&1; then
        echo "5. no NVIDIA GPU detected - installing CPU PaddlePaddle"
        pip install paddlepaddle==3.3.1
    fi
    echo "     PaddlePaddle runtime: CPU"
fi

echo "6. downloading paddleocr models"
if [ ! -d "models/PP-OCRv5_mobile_det" ] || [ ! -d "models/arabic_PP-OCRv5_mobile_rec" ] || [ ! -d "models/PP-LCNet_x1_0_textline_ori" ]; then
    python scripts/download_paddle_models.py
else
    echo "already downloaded, skipping.."
fi

echo "7. checking Tesseract (must be installed at the system level, not via pip)"
if ! command -v tesseract >/dev/null; then
    echo "warning: tesseract is not installed on this machine, please install it manually"
    echo "  Ubuntu/Debian: sudo apt install tesseract-ocr tesseract-ocr-ara"
    echo "  macOS:         brew install tesseract tesseract-lang"
fi

echo "8. checking libgl1 library (required by PaddleOCR on Linux)"
if command -v apt >/dev/null && ! ldconfig -p 2>/dev/null | grep -q libGL.so; then
    echo "warning: libgl1 is not installed. Install it with: sudo apt install libgl1"
fi

echo ""
echo "to run the API, execute the following commands:"
echo "  source venv/bin/activate"
echo "  uvicorn api:app --host 0.0.0.0 --port 8000"