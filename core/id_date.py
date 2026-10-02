# تصحيحات للهوية
import re
from datetime import date

import cv2
from collections import Counter
from core.config import MIN_OCR_CONFIDENCE

_MIN_YEAR = 1900
# منرجع الأرقام العربية لانكليزي
_TO_ASCII_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "0123456789" * 2)
_TO_EASTERN_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
_BIDI_MARKS = re.compile("[\u200e\u200f\u202a-\u202e\u2066-\u2069\u061c]")


def _ascii_digits(text: str) -> str:
    return _BIDI_MARKS.sub("", text).translate(_TO_ASCII_DIGITS)


def _digits_only(text: str) -> str:
    return "".join(ch for ch in _ascii_digits(text) if ch.isdigit())


def _valid(year: int, month: int, day: int) -> str | None:
    if not (_MIN_YEAR <= year <= date.today().year):
        return None
    try:
        date(year, month, day)
    except ValueError:
        return None
    return f"{day:02d}-{month:02d}-{year:04d}"


def _from_separated(a: str, b: str, c: str) -> str | None:
# تزبيط اتجاهات الأرقام
    if len(b) > 2:
        return None
    if len(a) == 4 and len(c) <= 2:
        return _valid(int(a), int(b), int(c))  
    if len(c) == 4 and len(a) <= 2:
        return _valid(int(c), int(b), int(a))  
    return None


def _from_compact(digits: str) -> str | None:
    if not 6 <= len(digits) <= 8:
        return None
    results = set()
    for year_first in (True, False):
        year = digits[:4] if year_first else digits[-4:]
        rest = digits[4:] if year_first else digits[:-4]
        for k in range(1, len(rest)):
            first, second = rest[:k], rest[k:]
            if len(first) > 2 or len(second) > 2:
                continue
            month, day = (first, second) if year_first else (second, first)
            results.add(_valid(int(year), int(month), int(day)))
    results.discard(None)
    return results.pop() if len(results) == 1 else None


def _from_year_and_rest(year: str, rest: str) -> str | None:
    results = set()
    for k in range(1, len(rest)):
        first, second = rest[:k], rest[k:]
        if len(first) > 2 or len(second) > 2:
            continue
        for day, month in ((first, second), (second, first)):
            results.add(_valid(int(year), int(month), int(day)))
    results.discard(None)
    return results.pop() if len(results) == 1 else None


def normalize_id_date(text: str) -> tuple[str | None, bool]:
    if not text:
        return None, False
    groups = re.findall(r"\d+", _ascii_digits(text))

    found = set()
    for i in range(len(groups) - 2):
        result = _from_separated(*groups[i:i + 3])
        if result:
            found.add(result)
    if len(found) == 1:
        return found.pop(), True

    if len(groups) == 1:
        return _from_compact(groups[0]), False
    if len(groups) == 2:
        a, b = groups
        if len(a) == 4 and len(b) != 4:
            return _from_year_and_rest(a, b), False
        if len(b) == 4 and len(a) != 4:
            return _from_year_and_rest(b, a), False
    return None, False


from collections import Counter

def _agrees_with_original(candidate: str, original_value: str) -> bool:
    day, month, year = candidate.split("-")
    cand = Counter(f"{int(day)}{int(month)}{year}")
    orig = Counter(_digits_only(original_value))
    extra_in_original = sum((orig - cand).values())   # رقم في الأولى غير موجود في الثانية
    missing_in_original = sum((cand - orig).values()) # رقم في الثانية ناقص من الأولى
    return extra_in_original == 0 and missing_in_original <= 1


_REREAD_WINDOWS = (0.30, 0.33, 0.36, 0.39, 0.42, 0.45, 0.50, 0.60, 0.75, 1.0)
_REREAD_TARGET_HEIGHT = 120  


def _date_hit_box(original_value: str, regions: list):
    target = _digits_only(original_value)
    hits = [r for r in regions if _digits_only(r.text) and _digits_only(r.text) in target]
    if not hits:
        return None
    primary = max(hits, key=lambda r: len(_digits_only(r.text)))
    hits = [r for r in hits if abs(r.y_center - primary.y_center) <= max(primary.height, 10)]
    x0 = min(r.x for r in hits)
    y0 = min(r.y for r in hits)
    x1 = max(r.x + r.width for r in hits)
    y1 = max(r.y + r.height for r in hits)
    return x0, y0, x1, y1


def reread_date(original_value: str, regions: list, prep: dict, engine, trace: list | None = None) -> str | None:

    color = prep.get("color")
    if color is None or engine is None:
        return None
    box = _date_hit_box(original_value, regions)
    if box is None:
        return None

    x0, y0, x1, y1 = box
    w, h = max(x1 - x0, 10), max(y1 - y0, 10)
    pad_x, pad_y = int(h * 1.5), int(h * 0.3)
    img_h, img_w = color.shape[:2]
    top, bottom = max(0, y0 - pad_y), min(img_h, y1 + pad_y)
    left = max(0, x0 - pad_x)

    scale = min(6.0, max(2.0, _REREAD_TARGET_HEIGHT / h))
    votes = Counter()
    for frac in _REREAD_WINDOWS:
        right = min(img_w, x1 + pad_x) if frac >= 1.0 else min(img_w, x0 + int(w * frac) + int(h * 0.5))
        crop = color[top:bottom, left:right]
        if crop.size == 0:
            continue
        big = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        big = cv2.copyMakeBorder(big, 20, 20, 20, 20, cv2.BORDER_REPLICATE)
        gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
        try:
            sub_regions = engine.read_regions({"color": big, "ocr_ready": gray})
        except Exception:
            continue
        text = " ".join(r.text for r in sorted(sub_regions, key=lambda r: r.x))
        result, exact = normalize_id_date(text)
        verified = bool(result and exact and _agrees_with_original(result, original_value))
        if trace is not None:
            trace.append({"window": frac, "text": text, "result": result, "exact": exact,
                          "verified": verified, "image": big})
        if verified:
            return result
        if result and exact:
            votes[result] += 1

    if votes:
        best, n = votes.most_common(1)[0]
        if n >= 2:
            return best
    return None


def finalize_birth_date(extracted: dict, regions: list, prep: dict, engine=None) -> dict:
    entry = extracted.get("birth_date")
    if entry is None:
        return extracted
    try:
        original_value = entry["value"]
        result, exact = normalize_id_date(original_value)
        if not exact:
            reread = reread_date(original_value, regions, prep, engine)
            if reread:
                result = reread
                day, month, year = reread.split("-")
                unpadded = f"{int(day)}{int(month)}{year}"
                exact = len(unpadded) == len(_digits_only(original_value))
        if result is None:
            return extracted

        entry["value"] = result
        if not exact:
            entry["confidence"] = min(entry["confidence"], MIN_OCR_CONFIDENCE - 1)
    except Exception:
        pass
    return extracted

def finalize_national_number(extracted: dict) -> dict:
#  إذا كان عشر أرقام ومافي صفر بالأول منحط الصفر وبخفض الثقة
    entry = extracted.get("national_number")
    if entry is None:
        return extracted
    try:
        value = entry["value"]
        digits = _digits_only(value)
        if len(digits) == 10 and not digits.startswith("0"):
            fixed = "0" + digits
            if any("\u0660" <= ch <= "\u0669" for ch in value):
                fixed = fixed.translate(_TO_EASTERN_DIGITS) 
            entry["value"] = fixed
            entry["confidence"] = min(entry["confidence"], MIN_OCR_CONFIDENCE - 1)
    except Exception:
        pass
    return extracted