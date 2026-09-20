
from core.field_parser import parse_regions_to_fields, reocr_missing_trailing_numbers
from core.ocr_engine import OCREngine, TesseractOCREngine
from core.output_builder import build_output
from core.preprocessing import preprocess

# بياخد صورة وحدة 
class CivilRegistryPipeline:
    DOCUMENT_TYPE = "civil_registry"
    EXPECTED_IMAGE_COUNT = 1

    def __init__(self, ocr_engine: OCREngine | None = None):
        self.ocr_engine = ocr_engine or TesseractOCREngine()

    def run(self, image_paths: list[str]) -> dict:
        if len(image_paths) != self.EXPECTED_IMAGE_COUNT:
            raise ValueError(
                f"civil registry requires {self.EXPECTED_IMAGE_COUNT} image "
                f"received {len(image_paths)}"
            )

        prep = preprocess(image_paths[0])
        regions = self.ocr_engine.read_regions(prep)
        extracted = parse_regions_to_fields(regions)
        extracted = reocr_missing_trailing_numbers(extracted, prep, self.ocr_engine)

        return build_output(
            extracted,
            document_type=self.DOCUMENT_TYPE,
            rotation_info=[prep["rotation_applied"]],
        )