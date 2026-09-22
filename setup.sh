
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

echo "4. installing (Tesseract wrapper + PaddleOCR)..+requirements"
pip install -r requirements.txt

echo "5. downloading paddleocr models (1.5 GB)"
if [ ! -d "models" ]; then
    python core/download_paddle_models.py
else
    echo "already downloaded, skipping.."
fi

echo "6. checking Tesseract (must be installed at the system level, not via pip)"
if ! command -v tesseract >/dev/null; then
    echo "warning: tesseract is not installed on this machine, please install it manually"
    echo "  Ubuntu/Debian: sudo apt install tesseract-ocr tesseract-ocr-ara"
    echo "  macOS:         brew install tesseract tesseract-lang"
fi

echo "7. checking libgl1 library (required by PaddleOCR on Linux)"
if command -v apt >/dev/null && ! ldconfig -p 2>/dev/null | grep -q libGL.so; then
    echo "warning: libgl1 is not installed. Install it with: sudo apt install libgl1"
fi

echo ""
echo "to run the API, execute the following commands:"
echo "  source venv/bin/activate"
echo "  uvicorn api:app --host 0.0.0.0 --port 8000"
