import os
import platform
from PIL import Image
import pytesseract
import io

# ----------------------------
# CONFIG TESSERACT
# ----------------------------
def configure_tesseract():
    system = platform.system()

    # Local macOS Homebrew
    if system == "Darwin":
        tesseract_bin = "/opt/homebrew/bin/tesseract"
        tessdata_prefix = "/opt/homebrew/share/tessdata"
    else:  # Linux / Docker
        tesseract_bin = "/usr/bin/tesseract"
        tessdata_prefix = "/usr/share/tesseract-ocr/5/tessdata"  # <- CORRECT PATH Docker

    # Ajouter au PATH
    os.environ["PATH"] += os.pathsep + os.path.dirname(tesseract_bin)
    # Définir TESSDATA_PREFIX
    os.environ["TESSDATA_PREFIX"] = tessdata_prefix

    # Vérification simple mais non bloquante
    fra_path = os.path.join(tessdata_prefix, "fra.traineddata")
    if not os.path.exists(fra_path):
        print(f"[WARNING] fra.traineddata introuvable dans {tessdata_prefix}")
    else:
        print(f"[INFO] fra.traineddata trouvé : {fra_path}")


configure_tesseract()

# ----------------------------
# SERVICE
# ----------------------------
class TesseractOCRService:
    def __init__(self, lang="fra"):
        self.lang = lang

    def extract_text(self, file_bytes: bytes) -> str:
        """
        Retourne le texte brut extrait d'une image
        """
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        text = pytesseract.image_to_string(image, lang=self.lang, config="--oem 1 --psm 6")
        return text