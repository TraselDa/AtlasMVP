# app/services/ocr_adapter/ocr_adapter.py

import json
from pathlib import Path
from app.core_engine.ocr_engine.tesseract_service import TesseractOCRService

# Pour gérer PDF/DOCX
from pdf2image import convert_from_bytes
import docx
from PIL import Image
import io
import fitz  # PyMuPDF


class OCRAdapter:
    def __init__(self, engine="tesseract", config_dir: str | Path = None):
        self.tesseract_engine = TesseractOCRService()
        if engine not in ["tesseract"]:
            raise ValueError(f"Engine inconnu : {engine}")
        self.engine_name = engine

        if config_dir is None:
            raise ValueError("config_dir doit être spécifié")
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # JSON unifié
        self.config_json = {}
        config_json_path = self.config_dir / "config.json"
        if config_json_path.exists():
            import json
            with open(config_json_path, "r", encoding="utf-8") as f:
                self.config_json = json.load(f)

    def process(self, file_content: bytes, engine=None, raw=False):
        eng = engine or self.engine_name
        if eng == "tesseract":
            ocr = self.tesseract_engine
        else:
            raise ValueError(f"Engine inconnu : {eng}")

        ext = self._detect_extension(file_content)
        if ext in [".png", ".jpg", ".jpeg"]:
            text = ocr.extract_text(file_content)
        elif ext == ".pdf":
            text = self._extract_from_pdf(file_content, ocr)
        elif ext == ".docx":
            text = self._extract_from_docx(file_content)
        else:
            raise ValueError(f"Format de fichier non supporté : {ext}")

        if raw:
            return {"text": text}

        # Mapping JSON si on a un config_json
        result_json = {}
        for key in self.config_json.keys():
            result_json[key] = self._extract_field(text, key)
        return result_json


    def extract_raw(self, file_content: bytes, engine: str = "tesseract") -> dict:
        """
        Extraction RAW OCR destinée au BUILD CONFIG
        """
        # Sélection moteur
        if engine == "tesseract":
            ocr = self.tesseract_engine
        else:
            raise ValueError(f"Engine inconnu : {engine}")

        # Détection type fichier
        ext = self._detect_extension(file_content)
        # Source type = image, pdf_native, pdf_scanned, docx
        source_type = None

        # OCR
        if ext in [".png", ".jpg", ".jpeg"]:
            source_type = "image"
            raw_text = ocr.extract_text(file_content)
        elif ext == ".pdf":
            if self._pdf_has_text(file_content):
                source_type = "pdf_native"
            else:
                source_type = "pdf_scanned"
            raw_text = self._extract_from_pdf(file_content, ocr)
        elif ext == ".docx":
            source_type = "docx"
            raw_text = self._extract_from_docx(file_content)
        else:
            raise ValueError(f"Format non supporté : {ext}")

        # Normalisation lignes
        lines = self._normalize_lines(raw_text)

        return {
            "engine": engine,
            "source_type": source_type,
            "raw_text": raw_text,
            "lines": lines
        }
    
    def save_raw_json(self, raw_data: dict, filename: str = "raw_ocr.json") -> Path:
        """
        Sauvegarde du RAW OCR en JSON (BUILD CONFIG)
        """
        output_path = self.config_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)

        return output_path
    # Helper methods
    def _normalize_lines(self, raw_text: str) -> list[str]:
        lines = []

        for line in raw_text.split("\n"):
            cleaned = line.strip()

            # Ignore lignes vides
            if not cleaned:
                continue

            # Ignore bruit OCR (1–2 caractères non numériques)
            if len(cleaned) <= 2 and not any(c.isdigit() for c in cleaned):
                continue

            lines.append(cleaned)

        return lines
    
    def _detect_extension(self, file_content: bytes):
        header = file_content[:4]
        if header.startswith(b"%PDF"):
            return ".pdf"
        elif header.startswith(b"PK"):
            return ".docx"
        else:
            return ".png"

    def _pdf_has_text(self, file_content: bytes) -> bool:
        doc = fitz.open(stream=file_content, filetype="pdf")
        for page in doc:
            if page.get_text().strip():
                return True
        return False

    def _extract_from_pdf(self, file_content: bytes, ocr):
        # 1️⃣ Si PDF natif → extraction directe
        if self._pdf_has_text(file_content):
            doc = fitz.open(stream=file_content, filetype="pdf")
            return "\n".join(page.get_text() for page in doc)

        # 2️⃣ Sinon → OCR (PDF scanné)
        pages = convert_from_bytes(file_content, dpi=200)  # DPI réduit = plus rapide
        text_pages = []

        for page in pages:
            buf = io.BytesIO()
            page.save(buf, format="PNG")
            text_pages.append(
                ocr.extract_text(buf.getvalue())
            )

        return "\n".join(text_pages)

    def _extract_from_docx(self, file_content: bytes):
        buf = io.BytesIO(file_content)
        doc = docx.Document(buf)
        return "\n".join([p.text for p in doc.paragraphs])

    def _extract_field(self, text: str, key: str):
        for line in text.split("\n"):
            if key.lower() in line.lower():
                return line.strip()
        return None