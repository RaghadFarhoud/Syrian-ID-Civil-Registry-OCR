
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_MODELS_DIR = PROJECT_ROOT / "models"

MODELS_TO_DOWNLOAD = {
    "text_detection": "PP-OCRv5_mobile_det",
    "text_recognition": "arabic_PP-OCRv5_mobile_rec",  
    "textline_orientation": "PP-LCNet_x1_0_textline_ori",
}


def main():
    from paddlex.inference.utils.official_models import official_models

    LOCAL_MODELS_DIR.mkdir(exist_ok=True)

    for module, model_name in MODELS_TO_DOWNLOAD.items():
        print(f"[{module}] تحميل {model_name} ...")
        cached_path = official_models.get_model_path(model_name)
        cached_path = Path(cached_path)

        dest = LOCAL_MODELS_DIR / model_name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(cached_path, dest)
        print(f" copy to: {dest}")



if __name__ == "__main__":
    main()
