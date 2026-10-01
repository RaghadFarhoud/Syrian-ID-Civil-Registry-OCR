#!/usr/bin/env python3
"""
ID Relay - build_config.py
قراءة .env (أو متغيرات البيئة) وإنتاج extension/config.js
الاستخدام:
    python build_config.py
"""
import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

EXT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
ENV_FILE = EXT_DIR / ".env"
EXAMPLE_FILE = EXT_DIR / ".env.example"

FIELD_KEYS = [
    "first_name",
    "father_name",
    "family_name",
    "mother_name",
    "mother_family_name",
    "birth_date",
    "amanah",
    "registry_number",
    "national_number",
]

DEFAULT_LABELS = {
    "first_name": ["الاسم", "الا سم", "الإسم", "الاسم الأول", "الاسم الثلاثي"],
    "father_name": ["اسم الاب", "إسم الأب", "اسم الأب"],
    "family_name": ["النسبة", "الشهرة", "الكنية"],
    "mother_name": [
        "اسم الام ونسبتها", "إسم الام", "اسم الام", "اسم ونسبة الأم",
        "اسم ونسبة الام", "اسم و نسبة الأم",
    ],
    "mother_family_name": ["نسبة الام", "نسبة الأم"],
    "birth_date": [
        "تاريخ الولادة", "محل وتاريخ الولادة", "محل و تاريخ الولادة",
        "تاريخ الميلاد", "بتاريخ الولادة",
    ],
    "amanah": ["الامانة", "الأمانة"],
    "registry_number": ["محل ورقم القيد", "رقم القيد", "محل القيد", "القيد"],
    "national_number": ["الرقم الوطني", "رقم وطني"],
}

# زر "إضافة بطاقة جديدة" — يجب الضغط عليه قبل ظهور حقول البطاقة (الرقم الوطني)
ADD_CARD_SELECTOR = 'button[mattooltip="إضافة بطاقة جديدة"]'

# حقول ثابتة (ليست من الاستخراج) تُملأ تلقائياً لتجهيز بطاقة الهوية.
# value = القيمة التي نختارها، و ensure = أزرار تحضيرية.
# valueByDocumentType = قيم مختلفة حسب نوع المستند المستخرج.
FIXED_FIELDS = [
    {
        "key": "card_name",
        "value": "هوية",
        "valueByDocumentType": {
            "national_id": "هوية",
            "civil_registry": "قيد مدني",
        },
        "selectors": ['mat-select[formcontrolname="cardName"]', 'mat-select[id^="identityCards.0.cardName"]'],
        "labels": ["نوع البطاقة", "هوية", "قيد مدني", "سجل مدني"],
        "ensure": [ADD_CARD_SELECTOR],
    },
    {
        "key": "card_issuer",
        "value": "نفوس",
        "selectors": ['mat-select[formcontrolname="cardIssuer"]', 'mat-select[id^="identityCards.0.cardIssuer"]'],
        "labels": ["جهة الإصدار", "نفوس"],
        "ensure": [ADD_CARD_SELECTOR],
    },
]



def parse_env_file(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            env[key] = value
    return env


def to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")


def split_csv(value: str) -> list[str]:
    return [p.strip() for p in value.split(",") if p.strip()]


def parse_value_by_doctype(value: str) -> dict:
    """FIXED_VALUE_BY_DOCTYPE_<key>=national_id=هوية,civil_registry=قيد مدني"""
    out = {}
    for part in value.split(","):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, _, val = part.partition("=")
        name = name.strip()
        val = val.strip()
        if name and val:
            out[name] = val
    return out


def build_config() -> dict:
    env = parse_env_file(EXAMPLE_FILE)  # القيم الافتراضية من المثال
    env.update(parse_env_file(ENV_FILE))  # قيم المستخدم
    for key, value in os.environ.items():  # متغيرات البيئة تفوز دائماً
        if key.startswith("RELAY_") or key.startswith("FIELD_") or key.startswith("FIXED_"):
            env[key] = value

    selectors = {key: split_csv(env.get(f"FIELD_SELECTOR_{key}", "")) for key in FIELD_KEYS}
    extra_labels = {
        key: split_csv(env.get(f"FIELD_LABEL_{key}", "")) for key in FIELD_KEYS
    }
    ensure = {key: split_csv(env.get(f"FIELD_ENSURE_{key}", "")) for key in FIELD_KEYS}

    # حقل الرقم الوطني يحتاج زر "إضافة بطاقة جديدة" حتى تظهر بطاقة الهوية
    if not ensure["national_number"]:
        ensure["national_number"] = [ADD_CARD_SELECTOR]

    fields = []
    for key in FIELD_KEYS:
        fields.append({
            "key": key,
            "selectors": selectors[key],
            "labels": [l for l in (DEFAULT_LABELS[key] + extra_labels[key]) if l],
            "ensure": ensure[key],
        })

    # الحقول الثابتة (تجهيز بطاقة الهوية)
    for fixed in FIXED_FIELDS:
        key = fixed["key"]
        sels = split_csv(env.get(f"FIXED_SELECTOR_{key}", "")) or list(fixed["selectors"])
        labs = split_csv(env.get(f"FIXED_LABEL_{key}", "")) or list(fixed["labels"])
        ens = split_csv(env.get(f"FIXED_ENSURE_{key}", "")) or list(fixed["ensure"])
        val = env.get(f"FIXED_VALUE_{key}", fixed["value"])
        entry = {
            "key": key,
            "value": val,
            "selectors": sels,
            "labels": labs,
            "ensure": ens,
        }
        # قيم مختلفة حسب نوع المستند المستخرج (مثلاً نوع البطاقة)
        by_doc = parse_value_by_doctype(env.get(f"FIXED_VALUE_BY_DOCTYPE_{key}", ""))
        if not by_doc:
            by_doc = dict(fixed.get("valueByDocumentType") or {})
        if by_doc:
            entry["valueByDocumentType"] = by_doc
        fields.append(entry)

    return {
        "baseUrl": env.get("RELAY_BASE_URL", "http://localhost:8000").rstrip("/"),
        "targetTabPrefix": env.get("RELAY_TARGET_TAB_PREFIX", "http://localhost:8000/demo-target"),
        "openTabIfMissing": to_bool(env.get("RELAY_OPEN_TAB_IF_MISSING", "1")),
        "openUrlIfMissing": env.get("RELAY_OPEN_URL_IF_MISSING", "http://localhost:8000/demo-target"),
        "fillOnly": to_bool(env.get("RELAY_FILL_ONLY", "1")),
        "autodetectLabels": to_bool(env.get("RELAY_AUTODETECT_LABELS", "1")),
        "fillWhenVisible": to_bool(env.get("RELAY_FILL_WHEN_VISIBLE", "1")),
        "scanFrames": to_bool(env.get("RELAY_SCAN_FRAMES", "1")),
        "skipEmptyValues": to_bool(env.get("RELAY_SKIP_EMPTY_VALUES", "1")),
        "sweepHidden": to_bool(env.get("RELAY_SWEEP_HIDDEN", "1")),
        "fields": fields,
    }


def main() -> None:
    try:
        from core.config import FIELD_LABELS  # استخدم تسميات الاستخراج الفعلية
    except Exception:
        FIELD_LABELS = {}

    merged = dict(DEFAULT_LABELS)
    for key, labels in FIELD_LABELS.items():
        if key.startswith("_") or key not in FIELD_KEYS:
            continue
        merged[key] = list(dict.fromkeys((merged.get(key, []) + labels)))

    payload = build_config()
    for field in payload["fields"]:
        if field["key"] in merged:
            field["labels"] = list(dict.fromkeys(merged.get(field["key"], []) + field["labels"]))
        field["labels"] = list(dict.fromkeys(field["labels"]))

    text = (
        "(function (root) {\n"
        + "  root.RELAY_CONFIG = "
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + ";\n"
        + "})(typeof self !== 'undefined' ? self : this);\n"
    )
    (EXT_DIR / "config.js").write_text(text, encoding="utf-8")

    src = "متغيرات البيئة" if any(
        k.startswith(("RELAY_", "FIELD_", "FIXED_")) for k in os.environ
    ) else ".env"
    missing = [f["key"] for f in payload["fields"] if not f["selectors"]]
    print("تم توليد extension/config.js من", src)
    print("  قاعدة الخادم   :", payload["baseUrl"])
    print("  تابات الموقع   :", payload["targetTabPrefix"])
    print("  تسمية الموقع   :", "مفتوح من قبل المُعِدّ" if missing else "-")
    print("  حقول بسيليكتور :", len(payload["fields"]) - len(missing), "من", len(payload["fields"]))
    print("  مسح الخطوات المخفية:", "مفعّل" if payload["sweepHidden"] else "معطّل")
    if missing:
        print("  حقول بدون سيليكتور (ستعتمد على الكشف التلقائي):")
        for k in missing:
            print("    -", k)


if __name__ == "__main__":
    main()