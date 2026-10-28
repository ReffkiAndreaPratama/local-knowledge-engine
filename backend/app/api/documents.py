"""Documents API endpoints."""
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.database.base import get_db
from app.schemas.document import (
    ChunkListResponse,
    DocumentImportResponse,
    DocumentListResponse,
    DocumentResponse,
    FolderImportRequest,
    FolderImportResponse,
    ReindexRequest,
    ReindexResponse,
)
from app.services.document_service import DocumentService

router = APIRouter()


@router.post("/import", response_model=DocumentImportResponse)
async def import_documents(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Import one or more uploaded documents."""
    service = DocumentService(db)
    return await service.import_files(files)


@router.post("/import-folder", response_model=FolderImportResponse)
async def import_folder(request: FolderImportRequest, db: Session = Depends(get_db)):
    """Import every supported file inside an allowed directory."""
    service = DocumentService(db)
    try:
        return service.import_folder(request.directory, recursive=request.recursive)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=DocumentListResponse)
@router.get("/", response_model=DocumentListResponse, include_in_schema=False)
async def get_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    filename: Optional[str] = None,
    extension: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List documents with optional filters."""
    service = DocumentService(db)
    items, total = service.list_documents(
        skip=skip,
        limit=limit,
        filename=filename,
        extension=extension,
        status=status,
    )
    return {"items": items, "total": total}


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, db: Session = Depends(get_db)):
    service = DocumentService(db)
    document = service.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("/{document_id}/chunks", response_model=ChunkListResponse)
async def get_document_chunks(
    document_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    service = DocumentService(db)
    document = service.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    items, total = service.get_chunks(document_id, skip=skip, limit=limit)
    return {"items": items, "total": total}


@router.delete("/{document_id}")
async def delete_document(document_id: str, db: Session = Depends(get_db)):
    service = DocumentService(db)
    if not service.delete_document(document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted", "document_id": document_id}


@router.post("/{document_id}/reindex", response_model=ReindexResponse)
async def reindex_document(document_id: str, db: Session = Depends(get_db)):
    service = DocumentService(db)
    if service.get_document(document_id) is None:
        raise HTTPException(status_code=404, detail="Document not found")
    job_id = service.reindex_documents([document_id])
    if job_id is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"job_id": job_id}


@router.post("/reindex", response_model=ReindexResponse)
async def reindex_many(request: ReindexRequest, db: Session = Depends(get_db)):
    service = DocumentService(db)
    job_id = service.reindex_documents(request.document_ids)
    if job_id is None:
        raise HTTPException(status_code=404, detail="No matching documents")
    return {"job_id": job_id}


@router.post("/scan-changes")
async def scan_for_changes(db: Session = Depends(get_db)):
    """Detect changed or missing source files and queue re-indexing."""
    service = DocumentService(db)
    return service.scan_for_changes()
