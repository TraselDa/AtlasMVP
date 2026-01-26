import json
from pathlib import Path
from typing import Optional, Dict, Any
import io
import fitz  # PyMuPDF
from pdf2image import convert_from_bytes
import docx
from PIL import Image

from app.core_engine.ocr_engine.tesseract_service import TesseractOCRService
from app.services.minio.minio_service import minio_service
import logging
logger = logging.getLogger(__name__)
class OCRAdapter:
    def __init__(self, engine: str = "tesseract", config_data: Optional[Dict[str, Any]] = None):
        self.tesseract_engine = TesseractOCRService()
        if engine not in ["tesseract"]:
            raise ValueError(f"Engine inconnu : {engine}")
        self.engine_name = engine
        
        # Configuration JSON (peut être chargée depuis MinIO)
        self.config_json = config_data or {}
    
    def set_config(self, config_data: Dict[str, Any]):
        """Définit la configuration pour le traitement"""
        self.config_json = config_data or {}

    def process(self, file_content: bytes, engine: Optional[str] = None, raw: bool = False) -> dict:
        """Traite un fichier et retourne les données extraites"""
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
        Retourne un dictionnaire avec:
        - engine: le moteur utilisé
        - source_type: image, pdf_native, pdf_scanned, docx
        - raw_text: le texte brut extrait
        - lines: les lignes normalisées
        """
        # Sélection moteur
        if engine == "tesseract":
            ocr = self.tesseract_engine
        else:
            raise ValueError(f"Engine inconnu : {engine}")

        # Détection type fichier
        ext = self._detect_extension(file_content)
        source_type = None
        raw_text = ""

        # Détection selon le type exact
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

    async def save_raw_json(self, raw_data: dict, minio_path: str = None) -> Optional[str]:
        """
        Sauvegarde du RAW OCR en JSON dans MinIO
        Retourne le chemin MinIO si sauvegarde réussie
        """
        try:
            if minio_path is None:
                logger.warning("Aucun chemin MinIO spécifié pour sauvegarde")
                return None
            
            json_data = json.dumps(raw_data, ensure_ascii=False, indent=2).encode('utf-8')
            
            # Sauvegarder dans MinIO
            await minio_service.upload_file(
                minio_path,
                json_data,
                content_type="application/json"
            )
            
            logger.info(f"RAW OCR sauvegardé dans MinIO: {minio_path}")
            return minio_path
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde RAW OCR: {e}")
            return None
    
    async def load_config_from_minio(self, minio_path: str) -> Dict[str, Any]:
        """Charge une configuration depuis MinIO"""
        try:
            config_content = await minio_service.read_file(minio_path)
            config_data = json.loads(config_content.decode('utf-8'))
            self.config_json = config_data
            logger.info(f"Configuration chargée depuis MinIO: {minio_path}")
            return config_data
        except Exception as e:
            logger.error(f"Erreur chargement config depuis MinIO {minio_path}: {e}")
            return {}
    
    def _normalize_lines(self, raw_text: str) -> list[str]:
        """Normalise les lignes de texte"""
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
    
    def _detect_extension(self, file_content: bytes) -> str:
        """Détecte l'extension du fichier à partir de son contenu"""
        header = file_content[:4]
        if header.startswith(b"%PDF"):
            return ".pdf"
        elif header.startswith(b"PK"):
            # ZIP signature (DOCX est un ZIP)
            return ".docx"
        else:
            # Par défaut, considérer comme image
            return ".png"

    def _pdf_has_text(self, file_content: bytes) -> bool:
        """Vérifie si un PDF contient du texte natif"""
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            for page in doc:
                if page.get_text().strip():
                    return True
            return False
        except Exception as e:
            # En cas d'erreur, on considère que c'est un PDF scanné
            return False

    def _extract_from_pdf(self, file_content: bytes, ocr) -> str:
        """Extrait le texte d'un PDF (natif ou scanné)"""
        # 1️⃣ Si PDF natif → extraction directe
        if self._pdf_has_text(file_content):
            doc = fitz.open(stream=file_content, filetype="pdf")
            return "\n".join(page.get_text() for page in doc)

        # 2️⃣ Sinon → OCR (PDF scanné)
        try:
            pages = convert_from_bytes(file_content, dpi=200)  # DPI réduit = plus rapide
            text_pages = []

            for page in pages:
                buf = io.BytesIO()
                page.save(buf, format="PNG")
                text_pages.append(ocr.extract_text(buf.getvalue()))

            return "\n".join(text_pages)
        except Exception as e:
            # Fallback: essayer d'extraire avec PyMuPDF même si pas de texte
            try:
                doc = fitz.open(stream=file_content, filetype="pdf")
                return "\n".join(page.get_text() for page in doc)
            except:
                return ""

    def _extract_from_docx(self, file_content: bytes) -> str:
        """Extrait le texte d'un fichier DOCX"""
        try:
            buf = io.BytesIO(file_content)
            doc = docx.Document(buf)
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            return ""

    def _extract_field(self, text: str, key: str) -> Optional[str]:
        """Extrait un champ spécifique du texte"""
        for line in text.split("\n"):
            if key.lower() in line.lower():
                return line.strip()
        return None