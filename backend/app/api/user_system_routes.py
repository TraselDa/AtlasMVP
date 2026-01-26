from fastapi import APIRouter, UploadFile, File, Query, Body
from typing import List, Dict, Any

from app.schemas.document_type import DocumentTypeCreateRequest, DocumentTypeResponse
from app.schemas.config import ConfigUpload, BuildConfigRequest, DocumentMetadata
from app.schemas.document import (
    VectorSearchRequest, VectorSearchResponse, PaginatedDocumentsResponse
)
from app.services.document.document_type_service import DocumentTypeService
from app.services.config.config_service import ConfigService
from app.services.document.document_services import DocumentService

router = APIRouter(prefix="/user-systems", tags=["user-systems"])

# Gestion des types de documents
@router.post("/document-types")
async def create_document_type(
    doc_type: DocumentTypeCreateRequest,
    #created_by: str = Query(..., description="Utilisateur créant le type")
):
    """Crée un nouveau type de document"""
    return await DocumentTypeService.create_document_type(
        doc_type
    )

@router.get("/document-types")
async def get_all_document_types():
    """Récupère tous les types de documents"""
    return await DocumentTypeService.get_all_document_types()

@router.get("/document-types/{slug}")
async def get_document_type(slug: str):
    """Récupère un type de document par son slug"""
    return await DocumentTypeService.get_document_type(slug)

@router.put("/document-types/{slug}")
async def update_document_type(
    slug: str,
    update_data: Dict[str, Any] = Body(...)
):
    """Met à jour un type de document"""
    return await DocumentTypeService.update_document_type(slug, update_data)

@router.delete("/document-types/{slug}/soft")
async def soft_delete_document_type(slug: str):
    """Marque un type de document pour suppression"""
    return await DocumentTypeService.soft_delete_document_type(slug)

@router.post("/document-types/{slug}/restore")
async def restore_document_type(slug: str):
    """Restaure un type de document"""
    return await DocumentTypeService.restore_document_type(slug)

@router.delete("/document-types/{slug}/hard")
async def hard_delete_document_type(slug: str):
    """Supprime définitivement un type de document"""
    return await DocumentTypeService.hard_delete_document_type(slug)

# Gestion des documents initiaux
@router.post("/document-types/{document_type_slug}/init-documents")
async def upload_initial_document(
    document_type_slug: str,
    file: UploadFile = File(...)
):
    """Upload un document initial pour configuration"""
    return await ConfigService.upload_initial_document(document_type_slug, file)

@router.get("/document-types/{document_type_slug}/init-documents")
async def get_initial_documents(document_type_slug: str):
    """Récupère les documents initiaux"""
    return await ConfigService.get_initial_documents(document_type_slug)

# Configuration initiale et gestion des configs
@router.post("/document-types/{document_type_slug}/build-config")
async def build_initial_config(document_type_slug: str):
    """Construit la configuration initiale"""
    return await ConfigService.build_initial_config(document_type_slug)

@router.get("/document-types/{document_type_slug}/normalized-init")
async def get_normalized_init(document_type_slug: str):
    """Récupère les documents normalisés initiaux"""
    return await ConfigService.get_normalized_init(document_type_slug)

@router.post("/document-types/{document_type_slug}/configs")
async def upload_config(
    document_type_slug: str,
    config_upload: ConfigUpload
):
    """Upload une configuration"""
    return await ConfigService.upload_config(
        document_type_slug,
        config_upload.config_type,
        config_upload.config_data
    )

@router.get("/document-types/{document_type_slug}/configs/{config_type}")
async def get_config(document_type_slug: str, config_type: str):
    """Récupère une configuration"""
    return await ConfigService.get_config_by_type(document_type_slug, config_type)

@router.delete("/document-types/{document_type_slug}/configs/{config_type}")
async def delete_config(document_type_slug: str, config_type: str):
    """Supprime une configuration"""
    return await ConfigService.delete_config(document_type_slug, config_type)

# Routes de test (héritées du service user)
@router.post("/test/{document_type_slug}/upload")
async def test_upload_documents(
    document_type_slug: str,
    files: List[UploadFile] = File(...)
):
    """Test d'upload de documents"""
    return await DocumentService.process_document_batch(document_type_slug, files)

@router.get("/test/{document_type_slug}/documents")
async def test_get_documents(
    document_type_slug: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Test de récupération de documents"""
    return await DocumentService.get_documents(document_type_slug, skip, limit)

@router.post("/test/{document_type_slug}/search")
async def test_vector_search(
    document_type_slug: str,
    search_request: VectorSearchRequest
):
    """Test de recherche vectorielle"""
    """return await DocumentService.vector_search(
        search_request.query,
        document_type_slug,
        search_request.top_k,
        search_request.include_content
    )"""

    return await DocumentService.ask_documents(
        search_request.query,
        document_type_slug,
        use_llm=search_request.use_llm
        #search_request.top_k,
        #search_request.include_content
    )