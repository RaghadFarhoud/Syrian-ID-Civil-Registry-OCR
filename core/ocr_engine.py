
from dataclasses import dataclass
from typing import Protocol

import numpy as np
import pytesseract


@dataclass
class TextRegion:
    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float  

    @property
    def x_center(self) -> float:
        return self.x + self.width / 2

    @property
    def y_center(self) -> float:
        return self.y + self.height / 2


class OCREngine(Protocol):
    def read_regions(self, prep: dict) -> list[TextRegion]:
        
        ...


class TesseractOCREngine:

    def __init__(self, lang: str = "ara", psm: int = 6):
        self.lang = lang
        self.config = f"--psm {psm} -c preserve_interword_spaces=1"

    def read_regions(self, prep: dict) -> list[TextRegion]:
        image = prep["ocr_ready"]
        data = pytesseract.image_to_data(
            image, lang=self.lang, config=self.config,
            output_type=pytesseract.Output.DICT,
        )

        regions = []
        n = len(data["text"])
        for i in range(n):
            text = data["text"][i].strip()
            conf = float(data["conf"][i])
            if not text or conf < 0:
                continue
            regions.append(TextRegion(
                text=text,
                x=data["left"][i], y=data["top"][i],
                width=data["width"][i], height=data["height"][i],
                confidence=conf,
            ))
        return regions


class PaddleOCREngine:
   
    def __init__(
        self,
        lang: str = "ar",
        text_detection_model_name: str = "PP-OCRv5_mobile_det",
        text_detection_model_dir: str | None = None,
        text_recognition_model_name: str = "arabic_PP-OCRv5_mobile_rec",
        text_recognition_model_dir: str | None = None,
        textline_orientation_model_name: str = "PP-LCNet_x1_0_textline_ori",
        textline_orientation_model_dir: str | None = None,
        use_doc_orientation_classify: bool = False,
        use_doc_unwarping: bool = False,
          use_textline_orientation: bool = False,
    ):
  
        import os
        os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "False")

        from paddleocr import PaddleOCR

        self._ocr = PaddleOCR(
            lang=lang,
            text_detection_model_name=text_detection_model_name,
            text_detection_model_dir=text_detection_model_dir,
            text_recognition_model_name=text_recognition_model_name,
            text_recognition_model_dir=text_recognition_model_dir,
            textline_orientation_model_name=textline_orientation_model_name,
            textline_orientation_model_dir=textline_orientation_model_dir,
            use_doc_orientation_classify=use_doc_orientation_classify,
            use_doc_unwarping=use_doc_unwarping,
            use_textline_orientation=use_textline_orientation,
        )

    def read_regions(self, prep: dict) -> list[TextRegion]:
        image = prep["color"]  
        results = self._ocr.predict(image)

        regions: list[TextRegion] = []
        for res in results:
            texts = res.get("rec_texts", [])
            scores = res.get("rec_scores", [])
            polys = res.get("rec_polys") or res.get("dt_polys", [])

            for text, score, poly in zip(texts, scores, polys):
                text = text.strip()
                if not text:
                    continue
                xs = [p[0] for p in poly]
                ys = [p[1] for p in poly]
                x, y = int(min(xs)), int(min(ys))
                w, h = int(max(xs) - x), int(max(ys) - y)
                regions.append(TextRegion(
                    text=text, x=x, y=y, width=w, height=h,
                    confidence=round(float(score) * 100, 1),
                ))
        return regions