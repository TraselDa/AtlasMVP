from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from bson import ObjectId

class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)

class DocumentTypeStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CONFIGURING = "configuring"

# ========== REQUESTS ==========
class DocumentTypeCreateRequest(BaseModel):
    name: str
    description: str
    created_by: str

class DocumentTypeUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[DocumentTypeStatus] = None
    config_paths: Optional[Dict[str, str]] = None
    fields_schema: Optional[Dict[str, Any]] = None

class DocumentTypePaginatedRequest(BaseModel):
    skip: int = 0
    limit: int = 100

# ========== DATABASE SCHEMAS ==========
class DocumentTypeDBSchema(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[PyObjectId] = Field(None, alias="_id")
    slug: str
    name: str
    description: str
    status: DocumentTypeStatus = DocumentTypeStatus.CONFIGURING
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    config_paths: Dict[str, str] = {}
    fields_schema: Optional[Dict[str, Any]] = None
    is_active: bool = True
    is_marked_for_deletion: bool = False
    deletion_date: Optional[datetime] = None
    scheduled_deletion_date: Optional[datetime] = None

# ========== RESPONSES ==========
class DocumentTypeResponse(BaseModel):
    slug: str
    name: str
    description: str
    status: str
    created_by: str
    created_at: str
    updated_at: str
    config_paths: Dict[str, str] = {}
    
    @classmethod
    def from_db(cls, db_doc: DocumentTypeDBSchema) -> "DocumentTypeResponse":
        return cls(
            slug=db_doc.slug,
            name=db_doc.name,
            description=db_doc.description,
            status=db_doc.status.value,
            created_by=db_doc.created_by,
            created_at=db_doc.created_at.isoformat(),
            updated_at=db_doc.updated_at.isoformat(),
            config_paths=db_doc.config_paths
        )

class DocumentTypeListResponse(BaseModel):
    items: List[DocumentTypeResponse]
    total: int
    skip: int
    limit: int

class DocumentTypeDeleteResponse(BaseModel):
    status: str
    message: str
    deleted_slug: Optional[str] = None

class DocumentTypeConfigPathsResponse(BaseModel):
    pdf_native: Optional[str] = None
    pdf_scanned: Optional[str] = None
    image: Optional[str] = None
    docx: Optional[str] = None

# ========== UTILITY SCHEMAS ==========
class DocumentTypeStatsResponse(BaseModel):
    total_documents: int = 0
    active_documents: int = 0
    last_updated: Optional[str] = None
    config_status: Dict[str, bool] = {}  # pdf_native: true, pdf_scanned: false, etc.

class DocumentTypeFieldSchema(BaseModel):
    field_name: str
    field_type: str
    required: bool = False
    description: Optional[str] = None
    validation_rules: Optional[Dict[str, Any]] = None