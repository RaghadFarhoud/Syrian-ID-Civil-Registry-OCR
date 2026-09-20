
import re

from rapidfuzz import fuzz, process
from core.arabic_date_parser import parse_arabic_worded_date
from core.config import (
    FIELD_LABELS,
    LABEL_MATCH_THRESHOLD,
    MIN_LABEL_LENGTH_RATIO,
    NOISE_CONFIDENCE_FLOOR,
)
from core.ocr_engine import TextRegion


def _clean_value(text: str) -> str:
    text = re.sub(r"^[\s:：\-–—]+", "", text)
    text = re.sub(r"[\s:：\-–—]+$", "", text)
    return text.strip()


def _strip_place_prefix(value: str) -> str:

    digits = set("0123456789٠١٢٣٤٥٦٧٨٩")
    tokens = value.split()
    for i, token in enumerate(tokens):
        if any(ch in digits for ch in token):
            return " ".join(tokens[i:])
    return value
def _finalize_birth_date(value_text: str) -> str:    
    cleaned = _strip_place_prefix(value_text)
    parsed = parse_arabic_worded_date(value_text)
    return parsed if parsed else cleaned

def _best_label_match(text: str) -> tuple[str, str, float] | None:
    best = None
    for field_key, labels in FIELD_LABELS.items():
        match = process.extractOne(text, labels, scorer=fuzz.partial_ratio)
        if match is None:
            continue
        label_text, score, _ = match
        if best is None or score > best[2]:
            best = (field_key, label_text, score)

    if best is None or best[2] < LABEL_MATCH_THRESHOLD:
        return None

    field_key, label_text, score = best
    length_ratio = len(label_text) / max(len(text), 1)
    if length_ratio < MIN_LABEL_LENGTH_RATIO:
        return None

    return best


def _strip_label_fuzzy(text: str, label: str) -> str:
    label_len = len(label)
    best_cut = None
    best_score = -1

    for cut in range(max(0, label_len - 2), min(len(text), label_len + 3) + 1):
        prefix = text[:cut]
        score = fuzz.ratio(prefix, label)
        if score > best_score:
            best_score = score
            best_cut = cut

    if best_cut is None or best_score < LABEL_MATCH_THRESHOLD:
        return text

    return text[best_cut:]

# إذاكان في مساحة كبيرة افقياً بيقسم المنطقة لعمودين
def split_into_columns(regions: list[TextRegion], min_gap_ratio: float = 0.15) -> list[list[TextRegion]]:  
    if len(regions) < 4:
        return [regions]

    xs = sorted(r.x + r.width for r in regions)  # الحافة اليمين (RTL)
    gaps = [(xs[i + 1] - xs[i], xs[i], xs[i + 1]) for i in range(len(xs) - 1)]
    biggest_gap, left_edge, right_edge = max(gaps, key=lambda g: g[0])

    total_span = xs[-1] - xs[0]
    if total_span == 0 or biggest_gap / total_span < min_gap_ratio:
        return [regions]

    split_point = (left_edge + right_edge) / 2
    left_col = [r for r in regions if (r.x + r.width) <= split_point]
    right_col = [r for r in regions if (r.x + r.width) > split_point]
    return [left_col, right_col]

# هون بمع المناظق النصية بصفوف حسب تقارب مركز الصف عمودياً 
def group_into_rows(regions: list[TextRegion], overlap_ratio: float = 0.5) -> list[list[TextRegion]]:
    if not regions:
        return []

    heights = sorted(r.height for r in regions)
    median_height = heights[len(heights) // 2] or 20
    threshold = median_height * overlap_ratio

    sorted_regions = sorted(regions, key=lambda r: r.y_center)
    rows: list[list[TextRegion]] = []

    for region in sorted_regions:
        placed = False
        for row in rows:
            row_center = sum(r.y_center for r in row) / len(row)
            if abs(region.y_center - row_center) <= threshold:
                row.append(region)
                placed = True
                break
        if not placed:
            rows.append([region])

    return rows


def _filter_noise_regions(regions: list[TextRegion]) -> list[TextRegion]:
    cleaned = []
    for r in regions:
        text = r.text.strip()
        if not text:
            continue
        if len(text) <= 1 and not text.isalnum():
            continue 
        if len(text) <= 2 and r.confidence < NOISE_CONFIDENCE_FLOOR:
            continue
        cleaned.append(r)
    return cleaned


_DIGIT_CHARS = set("0123456789٠١٢٣٤٥٦٧٨٩")
def _is_digits_only(text: str) -> bool:
    text = text.strip()
    return bool(text) and all(ch in _DIGIT_CHARS for ch in text)

def _recover_split_trailing_number(
    value_text: str, row_regions: list[TextRegion], all_regions: list[TextRegion]
) -> str:
 
    stripped = value_text.strip()
    if not stripped or stripped[-1] in _DIGIT_CHARS or not row_regions:
        return value_text  

    row_y = sum(r.y_center for r in row_regions) / len(row_regions)
    avg_height = sum(r.height for r in row_regions) / len(row_regions) or 20
    row_left_x = min(r.x for r in row_regions)
    row_right_x = max(r.x + r.width for r in row_regions)
    row_width = max(row_right_x - row_left_x, avg_height)

    used_ids = {id(r) for r in row_regions}
    best_distance, best_region = None, None
    for r in all_regions:
        if id(r) in used_ids or not _is_digits_only(r.text):
            continue
        if abs(r.y_center - row_y) > avg_height * 1.5:
            continue 
        distance = max(row_left_x - (r.x + r.width), r.x - row_right_x, 0)
        if distance > row_width * 1.5:
            continue 
        if best_distance is None or distance < best_distance:
            best_distance, best_region = distance, r

    if best_region is None:
        return value_text

    return f"{stripped} {best_region.text.strip()}"

# هاد ليحفظ حدود الصف مشان يعرف وين يقص إذا الرقم ضاع بعد خ
def _attach_recovery_bbox(entry: dict, row_regions: list[TextRegion]) -> None:
  
    if not row_regions:
        return
    entry["_recovery_bbox"] = (
        min(r.x for r in row_regions),
        min(r.y for r in row_regions),
        max(r.y + r.height for r in row_regions),
    )


def _needs_trailing_number_recovery(value_text: str) -> bool:
    stripped = value_text.strip()
    return not stripped or stripped[-1] not in _DIGIT_CHARS

# هون لعالج حالة انو ممكن حرف أخير يروح لحقل تاني أو حرف أول يضل بغير حقل
def _strip_leaked_label_suffix(value_text: str, matched_label: str, label_region_text: str) -> str:
    best_len, best_score = 0, -1
    for k in range(1, len(matched_label) + 1):
        score = fuzz.ratio(label_region_text, matched_label[:k])
        if score > best_score:
            best_score, best_len = score, k

    residual = matched_label[best_len:]
    if not residual or len(residual) > 3:
        return value_text

    prefix_of_value = value_text[:len(residual)]
    if fuzz.ratio(prefix_of_value, residual) >= LABEL_MATCH_THRESHOLD:
        return _clean_value(value_text[len(residual):])
    return value_text


def parse_regions_to_fields(regions: list[TextRegion]) -> dict:
    extracted: dict[str, dict] = {}
    regions = _filter_noise_regions(regions)
    all_regions = regions  
    columns = split_into_columns(regions)

    for column in columns:
        rows = group_into_rows(column)
        _process_rows(rows, extracted, all_regions)

    return extracted

_TRAILING_NUMBER_RECOVERY_FIELDS = {"registry_number"}
def _process_rows(rows: list[list[TextRegion]], extracted: dict, all_regions: list[TextRegion]) -> None:
    for row in rows:
        row_sorted = sorted(row, key=lambda r: -r.x)  

        colon_result = _try_colon_split(row_sorted)
        if colon_result:
            field_key, value_text, conf = colon_result
            if field_key == "birth_date":
                    value_text = _finalize_birth_date(value_text)
            if field_key in _TRAILING_NUMBER_RECOVERY_FIELDS:
                value_text = _recover_split_trailing_number(value_text, row_sorted, all_regions)
            entry = {"value": value_text, "confidence": round(conf, 1)}
            if field_key in _TRAILING_NUMBER_RECOVERY_FIELDS and _needs_trailing_number_recovery(value_text):
                _attach_recovery_bbox(entry, row_sorted)
            if field_key not in extracted or extracted[field_key]["confidence"] < entry["confidence"]:
                extracted[field_key] = entry
            continue

        label_region = None
        label_match = None
        for region in row_sorted:
            match = _best_label_match(region.text)
            if match and (label_match is None or match[2] > label_match[2]):
                label_region = region
                label_match = match

        if label_region is None:
            continue

        field_key, matched_label, _ = label_match
        other_regions = [r for r in row_sorted if r is not label_region]

        if other_regions:
            value_text = " ".join(r.text for r in other_regions)
            value_text = _strip_leaked_label_suffix(value_text, matched_label, label_region.text)
            confidences = [r.confidence for r in other_regions] + [label_region.confidence]
            avg_conf = sum(confidences) / len(confidences)
        else:
            value_text = _strip_label_fuzzy(label_region.text, matched_label)
            avg_conf = label_region.confidence * 0.85

        value_text = _clean_value(value_text)
        if not value_text:
            continue

        if field_key == "birth_date":
                value_text = _finalize_birth_date(value_text)
        if field_key in _TRAILING_NUMBER_RECOVERY_FIELDS:
            value_text = _recover_split_trailing_number(value_text, row_sorted, all_regions)
        if field_key in extracted and extracted[field_key]["confidence"] >= avg_conf:
            continue

        entry = {"value": value_text, "confidence": round(avg_conf, 1)}
        if field_key in _TRAILING_NUMBER_RECOVERY_FIELDS and _needs_trailing_number_recovery(value_text):
            _attach_recovery_bbox(entry, row_sorted)
        extracted[field_key] = entry
# بدور على : وبطابق الحقل اللي قبلا مع التسميات بالكونفيغ
def _try_colon_split(row_regions: list[TextRegion]) -> tuple[str, str, float] | None:
    for i, region in enumerate(row_regions):
        if ":" not in region.text and "：" not in region.text:
            continue

        label_part, _, value_part = _split_on_colon(region.text)
        match = _best_label_match(label_part)
        if not match:
            continue
        field_key, _, score = match
        if score < LABEL_MATCH_THRESHOLD:
            continue

        value_part = _clean_value(value_part)
        remaining = [r.text for r in row_regions[i + 1:]]
        if remaining:
            value_part = _clean_value(value_part + " " + " ".join(remaining))

        if not value_part:
            continue

        confs = [r.confidence for r in row_regions]
        return field_key, value_part, sum(confs) / len(confs)

    return None

def _split_on_colon(text: str) -> tuple[str, str, str]:
    for sep in (":", "："):
        if sep in text:
            left, right = text.split(sep, 1)
            return left, sep, right
    return text, "", ""

_RECROP_MARGIN_LEFT = 170
_RECROP_MARGIN_RIGHT = 40
_RECROP_MARGIN_V = 4
_RECROP_UPSCALE = 4


def _read_digits_near(color_image, left_x: int, top_y: int, bottom_y: int) -> str:
    import cv2
    import numpy as np
    import pytesseract

    img_h, img_w = color_image.shape[:2]
    x0 = max(0, left_x - _RECROP_MARGIN_LEFT)
    x1 = min(img_w, left_x + _RECROP_MARGIN_RIGHT)
    y0 = max(0, top_y - _RECROP_MARGIN_V)
    y1 = min(img_h, bottom_y + _RECROP_MARGIN_V)
    if x1 <= x0 or y1 <= y0:
        return ""

    crop = color_image[y0:y1, x0:x1]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    scaled = cv2.resize(gray, None, fx=_RECROP_UPSCALE, fy=_RECROP_UPSCALE, interpolation=cv2.INTER_CUBIC)
    _, binarized = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
# هون تنضيف خطوط نقط إلخ
    h, w = binarized.shape
    cleaned = binarized.copy()
    for row in range(h):
        dark_ratio = (binarized[row] < 128).sum() / w
        if dark_ratio > 0.5:
            cleaned[row] = 255

    inv = cv2.bitwise_not(cleaned)
    inv = cv2.dilate(inv, np.ones((3, 15), np.uint8), iterations=1)
    contours, _ = cv2.findContours(inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [cv2.boundingRect(c) for c in contours]
    boxes = [b for b in boxes if b[2] > 15 and b[3] > 15]  
    if not boxes:
        return ""

    bx, by, bw, bh = max(boxes, key=lambda b: b[2] * b[3])
    pad = 10
    sub = cleaned[max(0, by - pad):by + bh + pad, max(0, bx - pad):bx + bw + pad]

    config = "--psm 7 -c tessedit_char_whitelist=0123456789"
    text = pytesseract.image_to_string(sub, config=config)
    return "".join(ch for ch in text if ch.isdigit())


def reocr_missing_trailing_numbers(extracted: dict, prep: dict, engine=None) -> dict:
    color_image = prep.get("color")
    if color_image is None:
        return extracted

    for entry in extracted.values():
        bbox = entry.pop("_recovery_bbox", None)
        if bbox is None:
            continue

        left_x, top_y, bottom_y = bbox
        try:
            recovered = _read_digits_near(color_image, left_x, top_y, bottom_y)
        except Exception:
            continue  

        if recovered:
            entry["value"] = f"{entry['value'].strip()} {recovered}".strip()

    return extracted