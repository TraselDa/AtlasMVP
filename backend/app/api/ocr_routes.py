import shutil
from fastapi import APIRouter, UploadFile, File
from pathlib import Path
from app.core_engine.ocr_engine.ocr_adapter import OCRAdapter
from app.core_engine.normalization.document_normalizer import DocumentNormalizer
from app.core_engine.execution.engine import ExecutionEngine
from app.core_engine.execution.engine import ExecutionEngine
import json, yaml

from app.core_engine.execution.config_resolver import ConfigResolver

router = APIRouter(prefix="/ocr", tags=["ocr"])

# Dossier config
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "data" / "facture_sample" / "config"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
EXTRACTED_DIR = CONFIG_DIR / "data_extracted"
EXTRACTED_DIR.mkdir(exist_ok=True)


# Charge ton mapping JSON depuis un fichier (ou tu peux le mettre en dur)
# Source type = image, pdf_native, pdf_scanned, docx
CONFIG_REGISTRY = {
    "pdf_native": Path("./data/facture_sample/config/config.json"),
    #"pdf_native": "configs/invoice_pdf_native.json",
    "pdf_scanned": "configs/invoice_pdf_scanned_ocr.json",
    "image": "configs/invoice_image_ocr.json",
    "docx": "configs/invoice_docx_ocr.json",
}

"""mapping_file = Path("./data/facture_sample/config/config.json")
with open(mapping_file, "r", encoding="utf-8") as f:
    mapping_config = json.load(f)"""

# OCRAdapter avec config_dir



@router.post("/build_config")
def build_config():
    """
    Parcours config/ et construit le RAW JSON pour la création de config unifiée
    """

    ocr_adapter = OCRAdapter(engine="tesseract", config_dir=CONFIG_DIR)
    normalizer = DocumentNormalizer()

    if EXTRACTED_DIR.exists():
        shutil.rmtree(EXTRACTED_DIR)
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for file_path in CONFIG_DIR.iterdir():
        if not file_path.is_file() or file_path.suffix.lower() not in [".pdf", ".png", ".jpg", ".jpeg", ".docx"]:
            continue

        with open(file_path, "rb") as f:
            content = f.read()

        raw = ocr_adapter.extract_raw(content, engine="tesseract")

        normalized_raw = normalizer.normalize(raw)

        output_path = EXTRACTED_DIR / f"{file_path.stem}_tesseract.normalized_raw.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(normalized_raw, f, ensure_ascii=False, indent=2)

        results.append({
            "file": file_path.name,
            "engine": "tesseract",
            "lines": len(normalized_raw["lines"]),
            "output": str(output_path)
        })

    return {
        "status": "ok",
        "files_processed": len(results),
        "results": results
    }


@router.post("/process")
async def process_file(file: UploadFile = File(...)):
    """
    Upload d’un document, extraction OCR, normalisation, exécution des règles.
    Retourne JSON final basé sur les règles configurées.
    """
    ocr_adapter = OCRAdapter(engine="tesseract", config_dir=CONFIG_DIR)
    normalizer = DocumentNormalizer()



    content = await file.read()
    raw = ocr_adapter.extract_raw(content, engine="tesseract")
        # --- NORMALISATION ---
    normalized = normalizer.normalize(raw)
    
    """CONFIG_REGISTRY = {
    "pdf_native": "configs/config.json",
    #"pdf_native": "configs/invoice_pdf_native.json",
    "pdf_scanned": "configs/invoice_pdf_scanned_ocr.json",
    "image": "configs/invoice_image_ocr.json",
    "docx": "configs/invoice_docx_ocr.json",
    }

    mapping_file = Path("./data/facture_sample/config/config.json")
    with open(mapping_file, "r", encoding="utf-8") as f:
        mapping_config = json.load(f)

    engine = ExecutionEngine(mapping_config=mapping_config)"""
    
    resolver = ConfigResolver(CONFIG_REGISTRY)
    mapping_config = resolver.resolve(normalized)
    engine = ExecutionEngine(mapping_config=mapping_config)
    # --- Exécution des règles sur le document normalisé ---
    final_json = engine.execute(normalized)
    # Exécution des règles sur le document normalisé
    #final_json = engine.execute(raw)

    # Export YAML + JSON (optionnel)
    yaml_data = yaml.safe_dump(final_json, sort_keys=False, allow_unicode=True)

    return {
        "filename": file.filename,
        "json": final_json,
        "yaml": yaml_data,
        "raw_lines": raw.get("lines", []),
        "normalized_lines": normalized.get("lines", []),
    }

