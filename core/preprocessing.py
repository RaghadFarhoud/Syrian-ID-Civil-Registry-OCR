
import cv2
import numpy as np
import pytesseract
from PIL import Image
import os as _os
import platform as _platform

_DEFAULT_WINDOWS_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if _platform.system() == "Windows" and _os.path.exists(_DEFAULT_WINDOWS_TESSERACT):
    pytesseract.pytesseract.tesseract_cmd = _DEFAULT_WINDOWS_TESSERACT

# أول شي منحول الصورة لمصفوفةcv
def load_image(path: str) -> np.ndarray:
    pil_img = Image.open(path).convert("RGB")
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

# منكشف دوران الصورة وبصححا ب terrseract
def correct_rotation(image: np.ndarray) -> tuple[np.ndarray, int]:
    try:
        osd = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
        rotate_angle = osd.get("rotate", 0)
    except pytesseract.TesseractError:
# إذا فشل خلص ما مندورا
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
