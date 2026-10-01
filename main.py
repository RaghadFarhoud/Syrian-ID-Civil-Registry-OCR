
from pathlib import Path
from typing import Literal

from core.ocr_engine import OCREngine
from pipelines.civil_registry_pipeline import CivilRegistryPipeline
from pipelines.national_id_pipeline import NationalIdPipeline

DocumentType = Literal["national_id", "civil_registry"]

PROJECT_ROOT = Path(__file__).resolve().parent

_PIPELINES = {
    "national_id": NationalIdPipeline,
    "civil_registry": CivilRegistryPipeline,
}

MODEL_NAMES = {
    "det": "PP-OCRv5_mobile_det",
    "rec": "arabic_PP-OCRv5_mobile_rec",
    "ori": "PP-LCNet_x1_0_textline_ori",
}


def _resolve_model_dir(models_dir: str | Path, key: str) -> str:
    """مسار الموديل مطلوب. وإذا ناقص ما في روح للإنترنت - بيطلع خطأ واضح."""
    path = Path(models_dir)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    target = path / MODEL_NAMES[key]
    if not target.is_dir():
        raise FileNotFoundError(
            f"OCR model folder is missing: {target}\n"
            "The program runs fully offline and never downloads models. "
            "Keep the 'models' folder (and its 3 sub-folders) next to the project."
        )
    return str(target)


def build_paddle_engine(models_dir: str | Path = "models") -> OCREngine:
    from core.ocr_engine import PaddleOCREngine

    return PaddleOCREngine(
        lang="ar",
        text_detection_model_name=MODEL_NAMES["det"],
        text_detection_model_dir=_resolve_model_dir(models_dir, "det"),
        text_recognition_model_dir=_resolve_model_dir(models_dir, "rec"),
        textline_orientation_model_dir=_resolve_model_dir(models_dir, "ori"),
        use_textline_orientation=False,
    )


def extract_document(
    document_type: DocumentType,
    image_paths: list[str],
    ocr_engine: OCREngine | None = None,
) -> dict:
    """
       من الباك
        document_type: "national_id" أو "civil_registry"                       
        image_paths:مسارات الصور
                     - national_id: صورتين للهوية (أمامية + خلفية)
                     - civil_registry:للسجل صورة  
        
    رح يرجع 
        ValueError: إذا نوع الوثيقة مو مطابق أو عدد الصور ما بطابق 
    """
    pipeline_cls = _PIPELINES.get(document_type)
    if pipeline_cls is None:
        raise ValueError(
            f"document_type not supported: '{document_type}'. "
            f"accepted values: {list(_PIPELINES.keys())}"
        )

    pipeline = pipeline_cls(ocr_engine=ocr_engine) if ocr_engine else pipeline_cls()
    return pipeline.run(image_paths)


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path

  
    args = sys.argv[1:]
    if len(args) < 2:
        # لحتى تشغل
        print("usage: python main.py <national_id|civil_registry> [--engine paddle] [--out FILE] <صورة1> [صورة2]")
        sys.exit(1)

    doc_type = args[0]
    rest = args[1:]

    engine = None
    if rest and rest[0] == "--engine" and len(rest) > 1 and rest[1] == "paddle":
        print(" loading..", file=sys.stderr)
        engine = build_paddle_engine()
        rest = rest[2:]

    output_path = Path("result.json")
    if rest and rest[0] == "--out" and len(rest) > 1:
        output_path = Path(rest[1])
        rest = rest[2:]

    paths = rest
    result = extract_document(doc_type, paths, ocr_engine=engine)
    json_text = json.dumps(result, ensure_ascii=False, indent=2)

    print(json_text)

    output_path.write_text(json_text, encoding="utf-8")
    print(f"\n the result im: {output_path.resolve()}", file=sys.stderr)