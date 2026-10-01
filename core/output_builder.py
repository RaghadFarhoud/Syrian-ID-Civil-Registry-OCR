import re

from core.config import ALL_FIELDS, MIN_OCR_CONFIDENCE, OPTIONAL_FIELDS, REQUIRED_FIELDS

_DATE_PATTERN = re.compile(
    r"^\D*[\d٠-٩]{1,4}\D+[\d٠-٩]{1,4}\D+[\d٠-٩]{2,4}\D*$"
)

_ARABIC_DIGIT_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

# فحص إذا أول رقمين هنن من رموز المحافظات يعني بين 01-14
def _looks_like_valid_national_number(value: str) -> bool:
    digits_only = value.strip().translate(_ARABIC_DIGIT_MAP)
    if not digits_only.isdigit() or len(digits_only) != 11:
        return False
    governorate_code = int(digits_only[:2])
    return 1 <= governorate_code <= 14


def _looks_like_valid_date(value: str) -> bool:
    return bool(_DATE_PATTERN.match(value.strip()))


def merge_by_confidence(*extracted_sides: dict) -> dict:
    merged: dict[str, dict] = {}
    for side in extracted_sides:
        for field_key, data in side.items():
            if field_key not in merged or data["confidence"] > merged[field_key]["confidence"]:
                merged[field_key] = data
    return merged


def build_output(
    merged_fields: dict,
    document_type: str,
    rotation_info: list[int] | None = None,
    all_fields: list[str] | None = None,
    required_fields: list[str] | None = None,
) -> dict:
  
    fields_to_check = all_fields if all_fields is not None else ALL_FIELDS
    required = required_fields if required_fields is not None else REQUIRED_FIELDS

    fields = {}
    low_confidence_fields = []

    for key in fields_to_check:
        entry = merged_fields.get(key)
        if entry is None:
            fields[key] = None
            continue
        fields[key] = entry["value"]

        needs_review = entry["confidence"] < MIN_OCR_CONFIDENCE
        if key == "birth_date" and not _looks_like_valid_date(entry["value"]):
            needs_review = True
        if key == "national_number" and not _looks_like_valid_national_number(entry["value"]):
            needs_review = True

        if needs_review:
            low_confidence_fields.append(key)

    missing_required = [f for f in required if fields[f] is None]

    return {
        "document_type": document_type,
        "fields": fields,
        "extraction_status": {
            "success": len(missing_required) == 0,
            "missing_required_fields": missing_required,
            "low_confidence_fields": low_confidence_fields,
        },
    }