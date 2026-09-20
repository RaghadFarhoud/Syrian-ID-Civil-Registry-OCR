

import re

from rapidfuzz import fuzz, process


def _normalize(text: str) -> str:
    text = re.sub(r"[أإآ]", "ا", text)
    text = text.replace("ة", "ه")
    return text.strip()

_ORDINAL_DAYS = {
    "الاول": 1, "الثاني": 2, "الثالث": 3, "الرابع": 4, "الخامس": 5,
    "السادس": 6, "السابع": 7, "الثامن": 8, "التاسع": 9, "العاشر": 10,
    "الحادي عشر": 11, "الثاني عشر": 12, "الثالث عشر": 13, "الرابع عشر": 14,
    "الخامس عشر": 15, "السادس عشر": 16, "السابع عشر": 17, "الثامن عشر": 18,
    "التاسع عشر": 19, "العشرون": 20, "العشرين": 20,
    "الحادي والعشرون": 21, "الحادي والعشرين": 21,
    "الثاني والعشرون": 22, "الثاني والعشرين": 22,
    "الثالث والعشرون": 23, "الثالث والعشرين": 23,
    "الرابع والعشرون": 24, "الرابع والعشرين": 24,
    "الخامس والعشرون": 25, "الخامس والعشرين": 25,
    "السادس والعشرون": 26, "السادس والعشرين": 26,
    "السابع والعشرون": 27, "السابع والعشرين": 27,
    "الثامن والعشرون": 28, "الثامن والعشرين": 28,
    "التاسع والعشرون": 29, "التاسع والعشرين": 29,
    "الثلاثون": 30, "الثلاثين": 30,
    "الحادي والثلاثون": 31, "الحادي والثلاثين": 31,
}

_MONTHS = {
    "كانون الثاني": 1, "شباط": 2, "اذار": 3, "نيسان": 4, "ايار": 5,
    "حزيران": 6, "تموز": 7, "اب": 8, "ايلول": 9,
    "تشرين الاول": 10, "تشرين الثاني": 11, "كانون الاول": 12,
}

_UNITS = {
    "صفر": 0, "واحد": 1, "اثنان": 2, "اثنين": 2, "ثلاثه": 3, "اربعه": 4,
    "خمسه": 5, "سته": 6, "سبعه": 7, "ثمانيه": 8, "تسعه": 9,
}
_TEENS = {
    "عشره": 10, "احد عشر": 11, "اثنا عشر": 12, "اثني عشر": 12,
    "ثلاثه عشر": 13, "اربعه عشر": 14, "خمسه عشر": 15, "سته عشر": 16,
    "سبعه عشر": 17, "ثمانيه عشر": 18, "تسعه عشر": 19,
}
_TENS = {
    "عشرون": 20, "عشرين": 20, "ثلاثون": 30, "ثلاثين": 30,
    "اربعون": 40, "اربعين": 40, "خمسون": 50, "خمسين": 50,
    "ستون": 60, "ستين": 60, "سبعون": 70, "سبعين": 70,
    "ثمانون": 80, "ثمانين": 80, "تسعون": 90, "تسعين": 90,
}
_HUNDREDS = {
    "مئه": 100, "مائه": 100, "مئتان": 200, "مئتين": 200,
    "ثلاثمئه": 300, "ثلاثمائه": 300, "اربعمئه": 400, "اربعمائه": 400,
    "خمسمئه": 500, "خمسمائه": 500, "ستمئه": 600, "ستمائه": 600,
    "سبعمئه": 700, "سبعمائه": 700, "ثمانمئه": 800, "ثمانمائه": 800,
    "تسعمئه": 900, "تسعمائه": 900,
}
_THOUSAND = {"الف": 1000, "الفين": 2000, "الفان": 2000}

# هون مطابقة ضبابية لانو المطابقة تماماً بتفشل إذا بيختلف بحرف واحد 
_ALL_NUMBER_WORDS: dict[str, int] = {
    **_THOUSAND, **_HUNDREDS, **_TEENS, **_TENS, **_UNITS,
}
# هون كل وحدة الا عتبة لانو الطول بيفرق
_ANCHOR_THRESHOLD = 70
_NUMBER_WORD_THRESHOLD = 75
_ORDINAL_THRESHOLD = 75
_MONTH_THRESHOLD = 75
_MIN_FUZZY_WORD_LEN = 3 

_DAY_ANCHOR = "اليوم"
_FROM_ANCHOR = "من"
_MONTH_ANCHOR = "شهر"
_YEAR_ANCHOR = "لعام"
_AD_ANCHOR = "ميلادي"

# هون منطابق حرفي أول شي وإذا مازبط ضبابي
def _lookup(text: str, table: dict, threshold: int) -> int | None:
    if not text:
        return None
    if text in table:
        return table[text]
    match = process.extractOne(text, table.keys(), scorer=fuzz.ratio)
    if match is not None and match[1] >= threshold:
        return table[match[0]]
    return None

# برجع فهرس أقرب كلمة
def _find_anchor(words: list[str], anchor: str, start: int, threshold: int = _ANCHOR_THRESHOLD) -> int | None:
    best_idx, best_score = None, -1
    for i in range(start, len(words)):
        score = fuzz.ratio(words[i], anchor)
        if score > best_score:
            best_score, best_idx = score, i
    if best_idx is not None and best_score >= threshold:
        return best_idx
    return None

# لنحول السنة المكتوبة لرقم
def _parse_year_words(text: str) -> int | None:
    words = text.split()
    total = 0
    matched_any = False

    for word in words:
        candidates = [word]
        if word.startswith("و") and len(word) > 1:
            candidates.append(word[1:])

        value = None
        for candidate in candidates:
            if candidate in _ALL_NUMBER_WORDS:
                value = _ALL_NUMBER_WORDS[candidate]
                break

        if value is None:
            # إذا ماتطابقت منشتغل عالضبابية 
            for candidate in candidates:
                if len(candidate) < _MIN_FUZZY_WORD_LEN:
                    continue
                value = _lookup(candidate, _ALL_NUMBER_WORDS, _NUMBER_WORD_THRESHOLD)
                if value is not None:
                    break

        if value is not None:
            total += value
            matched_any = True

    return total if matched_any and total > 0 else None

# هون منحلل التاريخ المكتوب بالكلمات العربية ونرجع التاريخ بصيغة يوم وشهر وسنة عن طريق لما أفصل مواقعن
def parse_arabic_worded_date(text: str) -> str | None:
    
    norm = _normalize(text)
    words = norm.split()
    if not words:
        return None

    day_idx = _find_anchor(words, _DAY_ANCHOR, 0)
    if day_idx is None:
        return None

    month_kw_idx = _find_anchor(words, _MONTH_ANCHOR, day_idx + 1)
    if month_kw_idx is None:
        return None

    year_kw_idx = _find_anchor(words, _YEAR_ANCHOR, month_kw_idx + 1)
    if year_kw_idx is None:
        return None

    ad_idx = _find_anchor(words, _AD_ANCHOR, year_kw_idx + 1)

    day_words = words[day_idx + 1: month_kw_idx]
    if day_words and fuzz.ratio(day_words[-1], _FROM_ANCHOR) >= _ANCHOR_THRESHOLD:
        day_words = day_words[:-1]
    day_text = " ".join(day_words).strip()

    month_text = " ".join(words[month_kw_idx + 1: year_kw_idx]).strip()

    year_end = ad_idx if ad_idx is not None else len(words)
    year_text = " ".join(words[year_kw_idx + 1: year_end]).strip()

    if not (day_text and month_text and year_text):
        return None

    day = _lookup(day_text, _ORDINAL_DAYS, _ORDINAL_THRESHOLD)
    if day is None:
        return None

    month = _lookup(month_text, _MONTHS, _MONTH_THRESHOLD)
    if month is None:
        return None

    year = _parse_year_words(year_text)
    if year is None or not (1900 <= year <= 2100):
        return None

    return f"{year:04d}-{month:02d}-{day:02d}"