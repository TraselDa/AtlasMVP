from pydantic import BaseModel
from typing import Dict, Any, List, Optional

class ConfigUpload(BaseModel):
    document_type_slug: str
    config_type: str  # pdf_native, pdf_scanned, image, docx
    config_data: Dict[str, Any]

class BuildConfigRequest(BaseModel):
    document_type_slug: str

class FieldToExtract(BaseModel):
    name: str
    type: str = "string"
    description: Optional[str] = None


class AutoGenerateConfigRequest(BaseModel):
    fields_to_extract: List[FieldToExtract]
    config_type: str = "pdf_scanned"  # pdf_native, pdf_scanned, image, docx
    auto_save: bool = False  # Si True, sauvegarde automatiquement la config générée


class DocumentMetadata(BaseModel):
    name: str
    size: int
    content_type: str
    minio_path: str