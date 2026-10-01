"""
locally running: uvicorn api:app --host 0.0.0.0 --port 8000 --reload
"""
import logging
import shutil
import tempfile
import time
import traceback
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("api")

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_INDEX = STATIC_DIR / "index.html"

from main import extract_document

app = FastAPI(
    title="ID / Civil Registry Extraction API",
    version="1.0.0",
    description="واجهة REST لاستخراج بيانات الهوية والسجل المدني من الصور",
)


@app.get("/", response_class=FileResponse)
def index():
    return STATIC_INDEX


@app.get("/demo-target", response_class=FileResponse)
def demo_target():
    return STATIC_DIR / "demo-target.html"


@app.get("/client-test", response_class=FileResponse)
def client_test():
    return STATIC_DIR / "client-test.html"


@app.get("/logo", response_class=FileResponse)
def logo():
    return FileResponse(
        STATIC_DIR / "logo.jpg",
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(
        STATIC_DIR / "logo.jpg",
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=3600"},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_PADDLE_ENGINE = None  


def _get_engine(engine_name: str):
    global _PADDLE_ENGINE
    if engine_name == "tesseract":
        return None  
    if _PADDLE_ENGINE is None:
        from main import build_paddle_engine
        _PADDLE_ENGINE = build_paddle_engine()
    return _PADDLE_ENGINE


@app.on_event("startup")
def _preload_default_engine():
    t0 = time.perf_counter()
    _get_engine("paddle")
    device = getattr(_PADDLE_ENGINE, "_device", "unknown")
    logger.info("OCR engine loaded in %.2fs (device=%s)", time.perf_counter() - t0, device)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/extract")
async def extract(
    document_type: str = Form(..., description="national_id أو civil_registry"),
    engine: str = Form("paddle", description="paddle أو tesseract"),
    files: list[UploadFile] = File(..., description="صورة واحدة للسجل المدني، صورتين (أمامية + خلفية) للهوية"),
):
    file_names = [f.filename for f in files]
    logger.info(
        "REQUEST start: document_type=%s engine=%s files=%s",
        document_type, engine, file_names,
    )
    t0 = time.perf_counter()

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
        device = getattr(ocr_engine, "_device", "cpu") if ocr_engine is not None else "tesseract"
        result = extract_document(document_type, saved_paths, ocr_engine=ocr_engine)
        elapsed = time.perf_counter() - t0
        if isinstance(result, dict):
            result["elapsed_seconds"] = round(elapsed, 3)
            result["engine_device"] = device
        logger.info(
            "REQUEST done: document_type=%s engine=%s device=%s elapsed=%.2fs",
            document_type, engine, device, elapsed,
        )
        return result
    except ValueError as exc:
        logger.error(
            "REQUEST failed: document_type=%s engine=%s elapsed=%.2fs error=%s",
            document_type, engine, time.perf_counter() - t0, exc,
        )
        raise HTTPException(400, str(exc))
    except Exception as exc:
        traceback.print_exc()
        logger.error(
            "REQUEST failed: document_type=%s engine=%s elapsed=%.2fs error=%s",
            document_type, engine, time.perf_counter() - t0, exc,
        )
        raise HTTPException(500, f"extraction failed: {exc}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------- ناقل البيانات إلى موقع الإدخال (relay) ----------
_LAST_RESULT: dict | None = None


class RelayPayload(BaseModel):
    document_type: str = ""
    fields: dict = Field(default_factory=dict)
    extraction_status: dict = Field(default_factory=dict)


@app.post("/relay/last")
def relay_store(payload: RelayPayload):
    global _LAST_RESULT
    _LAST_RESULT = {
        "document_type": payload.document_type,
        "fields": payload.fields,
        "extraction_status": payload.extraction_status,
    }
    return {"ok": True}


@app.get("/relay/last")
def relay_last():
    if _LAST_RESULT is None:
        return {"document_type": "", "fields": {}, "extraction_status": {"success": False}}
    return _LAST_RESULT
