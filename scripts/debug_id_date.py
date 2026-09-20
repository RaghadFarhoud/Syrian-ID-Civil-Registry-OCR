
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2

from core.field_parser import parse_regions_to_fields
from core.id_date import normalize_id_date, reread_date
from core.preprocessing import preprocess


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(1)

    if "--engine" in args and "paddle" in args:
        from main import build_paddle_engine
        engine = build_paddle_engine()
    else:
        from core.ocr_engine import TesseractOCREngine
        engine = TesseractOCREngine()

    prep = preprocess(args[0])
    regions = engine.read_regions(prep)

    print("fields contains digits")
    for r in sorted(regions, key=lambda r: r.y):
        if any(ch.isdigit() for ch in r.text):
            print(f"  [{r.x},{r.y},{r.width}x{r.height}] conf={r.confidence:>5.1f}  {r.text!r}")

    entry = parse_regions_to_fields(regions).get("birth_date")
    print("\n birth_date before correction ")
    print(" ", entry)
    if not entry:
        return
    print("  normalize ->", normalize_id_date(entry["value"]))

    trace = []
    final = reread_date(entry["value"], regions, prep, engine, trace)
    print("\n re-reading attempts from narrowest to widest")
    for t in trace:
        name = f"date_win_{t['window']:.2f}.jpg"
        cv2.imwrite(name, t["image"])
        print(f"  window={t['window']:.2f} verified={t['verified']!s:<5} exact={t['exact']!s:<5} "
              f"result={t['result']}  text={t['text']!r}   [{name}]")
    print("\n the final result of re-reading", final)


if __name__ == "__main__":
    main()