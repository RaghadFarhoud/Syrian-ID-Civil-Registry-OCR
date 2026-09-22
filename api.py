"""
REST API لخدمة استخراج بيانات الهوية والسجل المدني.
تشغيل محلي: uvicorn api:app --host 0.0.0.0 --port 8000 --reload
"""
import shutil
import tempfile
import traceback
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from main import extract_document

app = FastAPI(
    title="ID / Civil Registry Extraction API",
    version="1.0.0",
    description="واجهة REST لاستخراج بيانات الهوية والسجل المدني من الصور",
)

# يسمح لموقعك (دومين مختلف) يتصل بالـ API. بالإنتاج بدّل "*" بدومين الموقع الفعلي.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_PADDLE_ENGINE = None  # نحمّل موديل paddle مرة وحدة بس، عند أول طلب يطلبه


def _get_engine(engine_name: str):
    global _PADDLE_ENGINE
    if engine_name == "tesseract":
        return None  # None => الـ pipeline بترجع لـ TesseractOCREngine الافتراضي
    if _PADDLE_ENGINE is None:
        from main import build_paddle_engine
        _PADDLE_ENGINE = build_paddle_engine()
    return _PADDLE_ENGINE


@app.on_event("startup")
def _preload_default_engine():
    # نحمّل موديل paddle مرة وحدة عند إقلاع السيرفر، مش عند أول طلب،
    # لأنو التحميل بياخد وقت وما لازم أول مستخدم يستناه.
    _get_engine("paddle")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/extract")
async def extract(
    document_type: str = Form(..., description="national_id أو civil_registry"),
    engine: str = Form("paddle", description="paddle أو tesseract"),
    files: list[UploadFile] = File(..., description="صورة واحدة للسجل المدني، صورتين (أمامية+خلفية) للهوية"),
):
    if document_type not in ("national_id", "civil_registry"):
        raise HTTPException(400, "document_type يجب أن يكون national_id أو civil_registry")

    expected = 2 if document_type == "national_id" else 1
    if len(files) != expected:
        raise HTTPException(400, f"{document_type} يحتاج {expected} صورة بالضبط، وصل {len(files)}")

    tmp_dir = Path(tempfile.mkdtemp(prefix="idextract_"))
    try:
        saved_paths = []
        for f in files:
            dest = tmp_dir / f.filename
            with dest.open("wb") as out:
                shutil.copyfileobj(f.file, out)
            saved_paths.append(str(dest))

        ocr_engine = _get_engine(engine)
        result = extract_document(document_type, saved_paths, ocr_engine=ocr_engine)
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(500, f"extraction failed: {exc}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
