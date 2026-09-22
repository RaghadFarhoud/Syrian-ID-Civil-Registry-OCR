#!/usr/bin/env bash
# سكربت إعداد المشروع على أي جهاز: يعمل venv، يثبت المتطلبات (بما فيها paddle)، وينزّل موديلات paddle
set -e

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="venv"

echo "== 1. التحقق من Python =="
command -v "$PYTHON_BIN" >/dev/null || { echo "python3 غير موجود على الجهاز"; exit 1; }

echo "== 2. إنشاء بيئة افتراضية (venv) =="
if [ ! -d "$VENV_DIR" ]; then
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "== 3. تحديث pip =="
pip install --upgrade pip

echo "== 4. تثبيت متطلبات المشروع (Tesseract wrapper + PaddleOCR) =="
pip install -r requirements.txt

echo "== 5. تنزيل موديلات PaddleOCR (لمرة وحدة فقط لكل جهاز) =="
if [ ! -d "models" ]; then
    python core/download_paddle_models.py
else
    echo "مجلد models موجود مسبقاً - تم التخطي."
fi

echo "== 6. التحقق من Tesseract (لازم مثبت على مستوى النظام، مو عبر pip) =="
if ! command -v tesseract >/dev/null; then
    echo "تحذير: tesseract غير مثبت على هذا الجهاز."
    echo "  Ubuntu/Debian: sudo apt install tesseract-ocr tesseract-ocr-ara"
    echo "  macOS:         brew install tesseract tesseract-lang"
fi

echo "== 7. التحقق من مكتبة libgl1 (تحتاجها paddle أحياناً على Linux) =="
if command -v apt >/dev/null && ! ldconfig -p 2>/dev/null | grep -q libGL.so; then
    echo "تحذير: libgl1 غير مثبتة. ثبّتها بـ: sudo apt install libgl1"
fi

echo ""
echo "الإعداد اكتمل. لتشغيل الـ API:"
echo "  source venv/bin/activate"
echo "  uvicorn api:app --host 0.0.0.0 --port 8000"
