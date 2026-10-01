
import cv2
import numpy as np
import pytesseract
from PIL import Image
import os as _os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Tesseract is used for rotation detection and for the digit re-crops, so it must
# exist locally. It is never downloaded: the client gets a portable copy inside the
# project (tesseract/), and this lookup finds it in any order. First match wins:
#   1) TESSERACT_CMD            - explicit override from the environment
#   2) tesseract/               - portable copy shipped with the offline bundle
#   3) the standard Windows install
#   4) whatever is already on PATH (pytesseract default)
_TESSERACT_CANDIDATES = [
    _os.environ.get("TESSERACT_CMD"),
    str(_PROJECT_ROOT / "tesseract" / "tesseract.exe"),
    str(_PROJECT_ROOT / "tesseract" / "bin" / "tesseract.exe"),
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]
for _candidate in _TESSERACT_CANDIDATES:
    if _candidate and _os.path.isfile(_candidate):
        pytesseract.pytesseract.tesseract_cmd = _candidate
        break

# أول شي منحول الصورة لمصفوفةcv
def load_image(path: str) -> np.ndarray:
    pil_img = Image.open(path).convert("RGB")
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

# منكشف دوران الصورة وبصححا ب terrseract
def correct_rotation(image: np.ndarray) -> tuple[np.ndarray, int]:
    try:
        osd = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
        rotate_angle = osd.get("rotate", 0)
    except Exception:
# إذا فشل (أو Tesseract مو موجود) خلص ما مندورا
        rotate_angle = 0

    if rotate_angle == 0:
        return image, 0

    rotation_map = {
        90: cv2.ROTATE_90_COUNTERCLOCKWISE,
        180: cv2.ROTATE_180,
        270: cv2.ROTATE_90_CLOCKWISE,
    }
    cv2_flag = rotation_map.get(rotate_angle)
    if cv2_flag is None:
        return image, 0

    return cv2.rotate(image, cv2_flag), rotate_angle


def enhance_for_ocr(image: np.ndarray) -> np.ndarray:
    """
   هون طبقت كذا تحسين
    - حولت لتدرج رمادي
    - شلت الضجيج 
    - رفعت التباين
وبالهوية بكون في خطوط وطبعات متل بقع الحبر كمان     """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    return enhanced


def preprocess(path: str) -> dict:
    # بطبق المعالجة وبرجع صوتين وحدة ملونة ووحدة بتدرج رمادي 
    # الملونة للبادل والرمادي ل tesseract 
    from core.card_detection import detect_and_crop_card

    image = load_image(path)
    image = detect_and_crop_card(image)
    rotated, angle = correct_rotation(image)
    enhanced = enhance_for_ocr(rotated)
    return {
        "color": rotated,
        "ocr_ready": enhanced,
        "rotation_applied": angle,
    }
