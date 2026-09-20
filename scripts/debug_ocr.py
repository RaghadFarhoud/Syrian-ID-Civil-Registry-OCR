
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.preprocessing import preprocess


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(1)

    image_path = args[0]
    use_paddle = "--engine" in args and "paddle" in args

    if use_paddle:
        from main import build_paddle_engine
        engine = build_paddle_engine()
    else:
        from core.ocr_engine import TesseractOCREngine
        engine = TesseractOCREngine()

    prep = preprocess(image_path)
    print(f"corrected rotation {prep['rotation_applied']} degrees\n")

    import cv2
    debug_out = Path(image_path).stem + "_preprocessed.jpg"
    cv2.imwrite(debug_out, prep["color"])
    print(f"preprossed image: {debug_out}\n")

    regions = engine.read_regions(prep)
    print(f"number of text regions detected: {len(regions)}\n")
    print(f"{'text':<40} {'x':>5} {'y':>5} {'width':>6} {'height':>7} {'confidence':>6}")
    print("-" * 80)
    for r in sorted(regions, key=lambda r: r.y):
        print(f"{r.text:<40} {r.x:>5} {r.y:>5} {r.width:>6} {r.height:>7} {r.confidence:>6.1f}")


if __name__ == "__main__":
    main()