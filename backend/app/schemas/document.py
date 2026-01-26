from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from bson import ObjectId
from fastapi import UploadFile

class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)

# ========== REQUESTS ==========
class DocumentUploadRequest(BaseModel):
    document_type_slug: str

class DocumentPaginatedRequest(BaseModel):
    skip: int = 0
    limit: int = 20

class DocumentFilterRequest(BaseModel):
    filters: Dict[str, Any]
    skip: int = 0
    limit: int = 20

class VectorSearchRequest(BaseModel):
    query: str
    document_type_slug: str
    top_k: int = 10
    use_llm: bool = False
    include_content: bool = True

class DocumentDeleteRequest(BaseModel):
    document_type_slug: str
    document_slug: str

# ========== DATABASE SCHEMAS ==========
class DocumentDBSchema(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[PyObjectId] = Field(None, alias="_id")
    slug: str
    document_type_slug: str
    document_name: str
    minio_path: str
    extracted_data: Dict[str, Any]
    processing_date: datetime = Field(default_factory=datetime.utcnow)
    vectorized: bool = False
    vector_ids: List[str] = []
    metadata: Dict[str, Any] = {}
    source_type: str
    is_active: bool = True
    is_marked_for_deletion: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# ========== RESPONSES ==========
class DocumentResponse(BaseModel):
    slug: str
    document_type_slug: str
    document_name: str
    minio_path: str
    extracted_data: Dict[str, Any]
    processing_date: str
    source_type: str
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    
    @classmethod
    def from_db(cls, db_doc: DocumentDBSchema) -> "DocumentResponse":
        return cls(
            slug=db_doc.slug,
            document_type_slug=db_doc.document_type_slug,
            document_name=db_doc.document_name,
            minio_path=db_doc.minio_path,
            extracted_data=db_doc.extracted_data,
            processing_date=db_doc.processing_date.isoformat(),
            source_type=db_doc.source_type,
            metadata=db_doc.metadata,
            created_at=db_doc.created_at.isoformat(),
            updated_at=db_doc.updated_at.isoformat()
        )

class PaginatedDocumentsResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
    skip: int
    limit: int
    fields: List[Dict[str, str]]

class VectorSearchResult(BaseModel):
    document: DocumentResponse
    score: float
    vector_content: Optional[str] = None

class VectorSearchResponse(BaseModel):
    results: List[VectorSearchResult]
    query: str
    document_type_slug: str
    total_matches: int

class ProcessResult(BaseModel):
    filename: str
    status: str
    document_slug: Optional[str] = None
    minio_path: Optional[str] = None
    error: Optional[str] = None

class BatchProcessResponse(BaseModel):
    total_files: int
    processed_files: int
    successful_files: int
    failed_files: int
    results: List[ProcessResult]

class DocumentDeleteResponse(BaseModel):
    status: str
    message: str
    deleted_slug: Optional[str] = None

# ========== METADATA SCHEMAS ==========
class DocumentMetadata(BaseModel):
    source_type: str
    size: int
    content_type: str
    original_filename: str
    pages: Optional[int] = None
    dimensions: Optional[Dict[str, int]] = None

class DocumentFieldSummary(BaseModel):
    field_name: str
    field_type: str
    sample_values: List[Any]
    count: int

class DocumentStatsResponse(BaseModel):
    total_documents: int
    processed_documents: int
    vectorized_documents: int
    by_source_type: Dict[str, int]
    by_month: Dict[str, int]
    field_summary: List[DocumentFieldSummary]