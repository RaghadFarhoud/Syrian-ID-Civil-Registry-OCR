from core.field_parser import parse_regions_to_fields, reocr_missing_trailing_numbers
from core.id_date import finalize_birth_date, finalize_national_number
from core.ocr_engine import OCREngine, TesseractOCREngine
from core.output_builder import build_output, merge_by_confidence
from core.preprocessing import preprocess


class NationalIdPipeline:
    DOCUMENT_TYPE = "national_id"
    EXPECTED_IMAGE_COUNT = 2  # back + front

    def __init__(self, ocr_engine: OCREngine | None = None):
        self.ocr_engine = ocr_engine or TesseractOCREngine()

    def run(self, image_paths: list[str]) -> dict:
        if len(image_paths) != self.EXPECTED_IMAGE_COUNT:
            raise ValueError(
                f"ID requires {self.EXPECTED_IMAGE_COUNT} images (front + back) "
                f"received {len(image_paths)}"
            )

        side_extractions = []
        rotations = []

        for path in image_paths:
            prep = preprocess(path)
            rotations.append(prep["rotation_applied"])
            regions = self.ocr_engine.read_regions(prep)
            extracted = parse_regions_to_fields(regions)
            extracted = reocr_missing_trailing_numbers(extracted, prep, self.ocr_engine)
            extracted = finalize_birth_date(extracted, regions, prep, self.ocr_engine)
            extracted = finalize_national_number(extracted)
            side_extractions.append(extracted)

        merged = merge_by_confidence(*side_extractions)

        return build_output(
            merged,
            document_type=self.DOCUMENT_TYPE,
            rotation_info=rotations,
        )