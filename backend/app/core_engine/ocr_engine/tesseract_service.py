import os
import platform

# Ajouter le binaire Tesseract au PATH
os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin"

# Définir TESSDATA_PREFIX AVANT pytesseract
if platform.system() == "Darwin":  # macOS
    os.environ["TESSDATA_PREFIX"] = "/opt/homebrew/share/tessdata/"
elif platform.system() == "Linux":
    os.environ["TESSDATA_PREFIX"] = "/usr/share/tesseract-ocr/4.00/"

# Vérification
assert os.path.exists(os.path.join(os.environ["TESSDATA_PREFIX"], "fra.traineddata")), \
       f"fra.traineddata introuvable! Vérifie TESSDATA_PREFIX={os.environ['TESSDATA_PREFIX']}"

import pytesseract
from PIL import Image
import io

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
        text = pytesseract.image_to_string(image, lang=self.lang,  config="--oem 1 --psm 6")
        return text