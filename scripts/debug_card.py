import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np
from core.preprocessing import load_image


def main():
    path = sys.argv[1]
    stem = Path(path).stem
    image = load_image(path)
    h, w = image.shape[:2]
    total = h * w
    print(f"image size: {w}x{h}")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    cv2.imwrite(f"{stem}_1_edges_raw.jpg", edges)
    edges = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=2)
    cv2.imwrite(f"{stem}_2_edges_dilated.jpg", edges)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print("contours found:", len(contours))
    if not contours:
        print("REASON: no contours")
        return

    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    print(f"largest contour area ratio: {area / total:.1%}  (threshold 15%)")

    x, y, bw, bh = cv2.boundingRect(largest)
    touches = x <= 2 or y <= 2 or x + bw >= w - 2 or y + bh >= h - 2
    print(f"bounding box: {x},{y},{bw}x{bh}  touches image border: {touches}")

    peri = cv2.arcLength(largest, True)
    for eps in (0.01, 0.02, 0.03, 0.05):
        approx = cv2.approxPolyDP(largest, eps * peri, True)
        print(f"  epsilon={eps}: {len(approx)} points")

    overlay = image.copy()
    cv2.drawContours(overlay, [largest], -1, (0, 255, 0), 4)
    approx = cv2.approxPolyDP(largest, 0.02 * peri, True)
    cv2.polylines(overlay, [approx], True, (0, 0, 255), 4)
    cv2.imwrite(f"{stem}_3_overlay.jpg", overlay)

    if area < total * 0.15:
        print("REASON: contour too small (<15%)")
    elif len(approx) != 4:
        print(f"REASON: approx has {len(approx)} points instead of 4")
    else:
        print("OK: card should be cropped")


if __name__ == "__main__":
    main()