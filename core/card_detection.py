
import cv2
import numpy as np

# منقص على اكبر مستطيل موجودواذا ما التقا تباين واضح منخلي الصورة كاملة
def detect_and_crop_card(image: np.ndarray, min_area_ratio: float = 0.15) -> np.ndarray:
  
    h, w = image.shape[:2]
    total_area = h * w

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    edges = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=2)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image

    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)

    if area < total_area * min_area_ratio:
        # هون منرجع الصورة ذا ما لقينا مستطيل واضح
        return image

    peri = cv2.arcLength(largest, True)
    approx = cv2.approxPolyDP(largest, 0.02 * peri, True)

    if len(approx) != 4:
        # وهي ذا ما اكتشف حدود 4 واضحة كمان برجع الصورة كاملة
        return image

    pts = approx.reshape(4, 2).astype("float32")
    ordered = _order_points(pts)
    return _warp_perspective(image, ordered)

# هون منرتب 4 نقاط فوق - يمين، فوق - يسار، تحت - يمين، تحت - يسار
def _order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _warp_perspective(image: np.ndarray, rect: np.ndarray) -> np.ndarray:
    (tl, tr, br, bl) = rect
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = max(int(width_a), int(width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = max(int(height_a), int(height_b))

    if max_width < 50 or max_height < 50:
        return image  

    dst = np.array([
        [0, 0], [max_width - 1, 0],
        [max_width - 1, max_height - 1], [0, max_height - 1],
    ], dtype="float32")

    matrix = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, matrix, (max_width, max_height))