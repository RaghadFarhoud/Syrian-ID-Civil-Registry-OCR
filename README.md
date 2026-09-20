# Syrian ID OCR

**English** | [العربية](README.ar.md)

An offline Arabic OCR pipeline that extracts structured JSON from **Syrian national ID cards** and **civil registry statements** (بيان قيد مدني). Built on PaddleOCR, with Tesseract and OpenCV for preprocessing and recovery steps.

> This is a Python library with a CLI, **not** a REST service. It is designed to be called from a backend (see [Integration](#integration)).

## Features

- **Fully offline at runtime**: PaddleOCR weights are stored locally; no network calls.
- **Two document pipelines** with a shared core: national ID (front + back images, merged) and civil registry (single image).
- **Robust preprocessing**: card detection on any background, perspective correction, rotation correction, contrast enhancement.
- **Layout-agnostic parsing**: OCR output is grouped into rows and columns, and fields are matched to their Arabic labels with fuzzy matching, so small OCR errors in labels do not break extraction.
- **Recovery steps** for common OCR failures: split or missing registry numbers, worded Arabic dates, unreadable birth-date separators, dropped leading zeros.
- **Review-oriented output**: uncertain values are flagged instead of silently guessed.

## Supported documents

| Document | Type key | Images | Notes |
|---|---|---|---|
| National ID card | `national_id` | 2 (front + back, any order) | Fields are merged by highest confidence |
| Civil registry statement | `civil_registry` | 1 | Two-column table; worded dates supported |

Extracted fields: `first_name`, `father_name`, `family_name`, `mother_name`, `birth_date`, `amanah`, `registry_number`, `national_number` (required) and `mother_family_name` (optional).

## How it works

```
image(s) on disk
   │
   ▼
main.extract_document()      picks the pipeline by document type
   │
   ▼
1. Preprocessing             card crop → rotation fix → contrast enhancement
2. OCR engine                image → text regions (text, box, confidence)
3. Field parser              regions → rows/columns → label matching → values
4. Recovery steps            registry number, worded date, ID birth date, national number
5. Merge (ID only)           best-confidence value per field across both sides
6. Output builder            final JSON + review flags
```

Each stage is independent: the OCR engine can be swapped without touching field logic, and each document type has its own pipeline.

## Project structure

```
main.py                      Entry point: extract_document()
core/
  preprocessing.py           Card crop, rotation correction, enhancement
  card_detection.py          Card boundary detection + perspective warp
  ocr_engine.py              PaddleOCR (primary) and Tesseract (fallback)
  field_parser.py            Regions → rows → fields
  arabic_date_parser.py      Worded Arabic date → YYYY-MM-DD (civil registry)
  id_date.py                 ID-only fixes: birth date + national number
  output_builder.py          Final JSON and review flags
  config.py                  Fields, Arabic labels, thresholds
pipelines/
  national_id_pipeline.py
  civil_registry_pipeline.py
scripts/
  download_paddle_models.py  One-time model download (online machine)
  debug_ocr.py               Print everything the OCR sees
  debug_id_date.py           Diagnose ID birth-date reading
models/                      Local PaddleOCR weights
```

## Installation

Requirements: Python 3.10+.

```bash
pip install -r requirements.txt
```

**Tesseract** must also be installed, with the `ara` and `osd` language data. It is required even when using PaddleOCR (rotation detection and digit recovery rely on it). On Windows it is auto-detected at `C:\Program Files\Tesseract-OCR\`.

### Models (offline setup)

PaddleOCR weights live in `models/`. To download them once on a connected machine:

```bash
python scripts/download_paddle_models.py
```

Then copy `models/` to the offline environment. `main.build_paddle_engine()` loads them from there.

> **Note:** the download script currently fetches `PP-OCRv5_server_det`, while `build_paddle_engine()` loads `models/PP-OCRv5_mobile_det`. Make sure both refer to the same detection model.

## Usage

### Python

```python
from main import extract_document, build_paddle_engine

engine = build_paddle_engine()  # create once, reuse across calls

result = extract_document(
    "national_id",
    ["front.jpg", "back.jpg"],
    ocr_engine=engine,
)
```

Inputs are **file paths on disk** (not bytes). A `ValueError` is raised for an unsupported document type or wrong number of images.

### Command line

```bash
python main.py national_id --engine paddle --out result.json front.jpg back.jpg
python main.py civil_registry --engine paddle civil.jpg
```

Options are positional-order sensitive: `--engine` first, then `--out`, then image paths. Without `--engine paddle`, the Tesseract fallback is used, which is significantly less accurate on these documents.

## Output format

```json
{
  "document_type": "national_id",
  "fields": {
    "first_name": "...",
    "father_name": "...",
    "family_name": "...",
    "mother_name": "...",
    "birth_date": "DD-MM-YYYY",
    "amanah": "...",
    "registry_number": "...",
    "national_number": "...",
    "mother_family_name": null
  },
  "extraction_status": {
    "success": true,
    "missing_required_fields": [],
    "low_confidence_fields": []
  }
}
```

- Fields that could not be extracted are `null`.
- **`success` means every required field was found, not that every value is correct.** Correctness is signaled by `low_confidence_fields`.
- A field is listed in `low_confidence_fields` when its OCR confidence is below 40, a date does not look like a date, or the national number is not 11 digits with a governorate code between 01 and 14.
- **Route any result with a non-empty `low_confidence_fields` (or `success: false`) to human review.**

### Format differences between documents

| | National ID | Civil registry |
|---|---|---|
| `birth_date` | `DD-MM-YYYY` | `YYYY-MM-DD` |
| Digits | Mostly Arabic-Indic (٠-٩) | Latin (0-9) |

Normalize these in your backend if you need a single format.

## Integration

The library is intentionally transport-agnostic. To expose it over HTTP, wrap `extract_document` in a thin service (for example FastAPI):

- Run the endpoint as a **sync** function; OCR is CPU-bound.
- Create the OCR engine **once per process** and reuse it. Thread-safety of the engine has not been verified, so prefer multiple worker processes over sharing it across threads.
- Save uploads to a temporary directory and delete them right after processing.
- Map `ValueError` to HTTP 400.
- Do not log extracted values.

## Debugging

```bash
python scripts/debug_ocr.py <image> --engine paddle
python scripts/debug_id_date.py <id_front_image> --engine paddle
```

`debug_ocr.py` prints every detected region with position and confidence and saves the preprocessed image. `debug_id_date.py` shows each birth-date re-read attempt and saves the crops it tried.

## Configuration

Field names, Arabic label variants and thresholds are centralized in `core/config.py`. New label spellings can be added there without changing parsing logic.

## Known limitations

- Thresholds and crop margins were calibrated on a small set of samples; build a regression suite on more samples before production use.
- Ambiguous values (for example a birth date whose day/month order cannot be determined) are left for review rather than guessed.
- `build_output` accepts `rotation_info` but does not currently include it in the output.
- Accuracy depends heavily on image quality; low-resolution or glare-affected photos will produce more flagged fields.

## Privacy and security

These documents contain personal data. **Never commit real ID images or extraction results** (the `.gitignore` excludes images and `result*.json`). Use masked or synthetic samples for testing, delete uploaded images after processing, and avoid logging extracted values.

## License

Not specified yet. Add a `LICENSE` file before sharing the repository beyond your team. Note that PaddleOCR and its models have their own licenses.
