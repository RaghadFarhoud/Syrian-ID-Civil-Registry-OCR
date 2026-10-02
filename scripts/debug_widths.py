r"""شغّله: python scripts\debug_widths.py data\front1.jpg
يقارن جودة الاستخراج عند أحجام مختلفة للبطاقة بعد القص (None = الحجم الأصلي بلا تكبير)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2

from core.card_detection import detect_and_crop_card
from core.field_parser import parse_regions_to_fields
from core.preprocessing import load_image
from main import build_paddle_engine

WIDTHS = (None, 800, 1000, 1300, 1600)
KEYS = ("first_name", "family_name", "father_name", "mother_name", "birth_date", "national_number")


def resize_to_width(img, width):
    h, w = img.shape[:2]
    if h > w:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        h, w = w, h
    if width is None or width == w:
        return img
    interp = cv2.INTER_AREA if width < w else cv2.INTER_CUBIC
    return cv2.resize(img, (width, int(h * width / w)), interpolation=interp)


def main():
    path = sys.argv[1]
    engine = build_paddle_engine()
    card = detect_and_crop_card(load_image(path))
    print("cropped card size:", card.shape[1], "x", card.shape[0])
    for width in WIDTHS:
        img = resize_to_width(card, width)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        regions = engine.read_regions({"color": img, "ocr_ready": gray})
        fields = parse_regions_to_fields(regions, id_mode=True)
        print(f"\n=== width {width or 'native'} ({img.shape[1]}x{img.shape[0]}): {len(regions)} regions ===")
        for key in KEYS:
            e = fields.get(key)
            print(f"  {key:<16} {e['value']!r}  (conf {e['confidence']})" if e else f"  {key:<16} -")


if __name__ == "__main__":
    main()