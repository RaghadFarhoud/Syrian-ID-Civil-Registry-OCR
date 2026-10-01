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


# التاريخ يطلع للعميل بصيغة يوم/شهر/سنة
_DATE_DISPLAY_PATTERN = re.compile(r"^(\d{1,4})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{1,4})$")
_EASTERN_DIGIT_CHARS = set("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹")


def _format_date_for_display(value: str) -> str:
    """dd/mm/yyyy, orders 1990-05-12 and 12-05-1990 alike, and if the original
    digits were Arabic it returns Arabic digits. Anything unparsable is returned
    as-is so the reviewer can see what was actually read."""
    text = value.strip()
    match = _DATE_DISPLAY_PATTERN.match(text)
    if not match:
        return text

    first, second, third = match.groups()
    if len(first) == 4 and len(third) <= 2:
        year, month, day = first, second, third
    elif len(third) == 4 and len(first) <= 2:
        day, month, year = first, second, third
    else:
        return text

    year, month, day = int(year), int(month), int(day)
    if not (1000 <= year <= 9999 and 1 <= month <= 12 and 1 <= day <= 31):
        return text

    formatted = f"{day:02d}/{month:02d}/{year:04d}"
    if any(ch in _EASTERN_DIGIT_CHARS for ch in text):
        formatted = formatted.translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))
    return formatted


# الأرقام العربية والفارسية تتحول لأرقام إنجليزية قبل الإرسال
_ASCII_DIGITS_TABLE = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "0123456789" * 2)


def _format_number_for_display(value: str) -> str:
    """الرقم الوطني يطلع بأرقام إنجليزية 0-9 كما يطلبها نموذج الموقع."""
    return value.translate(_ASCII_DIGITS_TABLE)


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
    field_status = {}

    for key in fields_to_check:
        entry = merged_fields.get(key)
        if entry is None:
            fields[key] = None
            field_status[key] = "missing"
            continue

        value = entry["value"]
        if key == "birth_date":
            value = _format_date_for_display(value)
        elif key == "national_number":
            value = _format_number_for_display(value)
        fields[key] = value

        needs_review = entry["confidence"] < MIN_OCR_CONFIDENCE
        if key == "birth_date" and not _looks_like_valid_date(value):
            needs_review = True
        if key == "national_number" and not _looks_like_valid_national_number(value):
            needs_review = True

        if needs_review:
            low_confidence_fields.append(key)
            field_status[key] = "low"
        else:
            field_status[key] = "ok"

    missing_required = [f for f in required if fields[f] is None]

    return {
        "document_type": document_type,
        "fields": fields,
        "extraction_status": {
            "success": len(missing_required) == 0,
            "missing_required_fields": missing_required,
            "low_confidence_fields": low_confidence_fields,
            "field_status": field_status,
        },
    }