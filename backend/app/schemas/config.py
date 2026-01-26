from pydantic import BaseModel
from typing import Dict, Any

class ConfigUpload(BaseModel):
    document_type_slug: str
    config_type: str  # pdf_native, pdf_scanned, image, docx
    config_data: Dict[str, Any]

class BuildConfigRequest(BaseModel):
    document_type_slug: str

class DocumentMetadata(BaseModel):
    name: str
    size: int
    content_type: str
    minio_path: str