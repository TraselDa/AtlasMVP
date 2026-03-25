from fastapi import APIRouter, UploadFile, File, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import List
import mimetypes
import logging
from minio.error import S3Error

from app.schemas.document import (
    PaginatedDocumentsResponse,
    DocumentFilterRequest,
    VectorSearchRequest,
    VectorSearchResponse,
    BatchProcessResponse,
    DocumentResponse,
    DocumentDeleteResponse,
    DocumentStatsResponse
)
from app.schemas.document_type import (
    DocumentTypeListResponse,
    DocumentTypeResponse,
    DocumentTypeStatsResponse
)
from app.services.document.document_services import DocumentService
from app.services.document.document_type_service import DocumentTypeService
from app.services.minio.minio_service import minio_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/document-types", response_model=DocumentTypeListResponse)
async def get_document_types(
    skip: int = Query(0, ge=0, description="Nombre d'éléments à sauter"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum d'éléments à retourner")
):
    """Récupère tous les types de documents actifs avec pagination"""
    return await DocumentTypeService.get_all_document_types(skip=skip, limit=limit)

@router.get("/document-types/{slug}", response_model=DocumentTypeResponse)
async def get_document_type(slug: str):
    """Récupère un type de document par son slug"""
    return await DocumentTypeService.get_document_type(slug)

@router.get("/document-types/{slug}/stats", response_model=DocumentTypeStatsResponse)
async def get_document_type_stats(slug: str):
    """Récupère les statistiques d'un type de document"""
    return await DocumentTypeService.get_document_type_stats(slug)

@router.post("/documents/upload", response_model=BatchProcessResponse)
async def upload_documents(
    document_type_slug: str = Query(..., description="Slug du type de document"),
    files: List[UploadFile] = File(...)
):
    """Upload et traite plusieurs documents simultanément"""
    if not files:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni")
    
    if len(files) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 fichiers autorisés par requête")
    
    return await DocumentService.process_document_batch(document_type_slug, files)

@router.get("/documents/{document_type_slug}", response_model=PaginatedDocumentsResponse)
async def get_documents(
    document_type_slug: str,
    skip: int = Query(0, ge=0, description="Nombre d'éléments à sauter"),
    limit: int = Query(20, ge=1, le=100, description="Nombre maximum d'éléments à retourner")
):
    """Récupère les documents d'un type spécifique avec pagination"""
    return await DocumentService.get_documents(document_type_slug, skip=skip, limit=limit)

@router.post("/documents/{document_type_slug}/filter", response_model=PaginatedDocumentsResponse)
async def filter_documents(
    document_type_slug: str,
    filter_request: DocumentFilterRequest
):
    """Filtre les documents avec pagination"""
    return await DocumentService.filter_documents(
        document_type_slug,
        filter_request.filters,
        filter_request.skip,
        filter_request.limit
    )

@router.get("/documents/{document_type_slug}/{document_slug}")
async def get_document_file(
    document_type_slug: str,
    document_slug: str
):
    """Sert le fichier d'un document depuis MinIO"""
    document = await DocumentService.get_document_by_slug(document_type_slug, document_slug)

    if not document.minio_path:
        raise HTTPException(status_code=404, detail="Fichier non trouvé pour ce document")

    try:
        response = minio_service.client.get_object(
            minio_service.bucket_name, document.minio_path
        )
        content_type = mimetypes.guess_type(document.minio_path)[0] or "application/octet-stream"
        filename = document.minio_path.split("/")[-1]

        return StreamingResponse(
            response,
            media_type=content_type,
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )
    except S3Error as e:
        logger.error(f"Erreur MinIO pour {document.minio_path}: {e}")
        raise HTTPException(status_code=404, detail="Fichier non trouvé dans le stockage")

@router.post("/documents/{document_type_slug}/search", response_model=VectorSearchResponse)
async def vector_search(
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



@router.delete("/documents/{document_type_slug}/{document_slug}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_type_slug: str,
    document_slug: str
):
    """Supprime un document (soft delete)"""
    return await DocumentService.delete_document(document_type_slug, document_slug)



@router.get("/documents/{document_type_slug}/stats", response_model=DocumentStatsResponse)
async def get_document_stats(document_type_slug: str):
    """Récupère les statistiques des documents d'un type"""
    return await DocumentService.get_document_stats(document_type_slug)
