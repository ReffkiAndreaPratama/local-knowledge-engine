"""Collections and saved-search endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.base import get_db
from app.schemas.collection import (
    CollectionCreate,
    CollectionListResponse,
    CollectionMembersRequest,
    CollectionResponse,
    SavedSearchCreate,
    SavedSearchListResponse,
    SavedSearchResponse,
)
from app.services.collection_service import CollectionService, SavedSearchService

router = APIRouter()


@router.get("", response_model=CollectionListResponse)
@router.get("/", response_model=CollectionListResponse, include_in_schema=False)
async def list_collections(db: Session = Depends(get_db)):
    items = CollectionService(db).list()
    return {"items": items, "total": len(items)}


@router.post("", response_model=CollectionResponse, status_code=201)
@router.post("/", response_model=CollectionResponse, status_code=201, include_in_schema=False)
async def create_collection(payload: CollectionCreate, db: Session = Depends(get_db)):
    try:
        return CollectionService(db).create(payload.name, payload.description)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(collection_id: str, db: Session = Depends(get_db)):
    collection = CollectionService(db).get(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.delete("/{collection_id}")
async def delete_collection(collection_id: str, db: Session = Depends(get_db)):
    if not CollectionService(db).delete(collection_id):
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"message": "Collection deleted"}


@router.get("/{collection_id}/document-ids")
async def get_collection_document_ids(collection_id: str, db: Session = Depends(get_db)):
    service = CollectionService(db)
    if service.get(collection_id) is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"document_ids": service.document_ids(collection_id)}


@router.post("/{collection_id}/documents")
async def add_collection_documents(
    collection_id: str, payload: CollectionMembersRequest, db: Session = Depends(get_db)
):
    try:
        added = CollectionService(db).add_documents(collection_id, payload.document_ids)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"added": added}


@router.delete("/{collection_id}/documents/{document_id}")
async def remove_collection_document(
    collection_id: str, document_id: str, db: Session = Depends(get_db)
):
    if not CollectionService(db).remove_document(collection_id, document_id):
        raise HTTPException(status_code=404, detail="Document is not in this collection")
    return {"message": "Document removed from collection"}


saved_search_router = APIRouter()


@saved_search_router.get("", response_model=SavedSearchListResponse)
@saved_search_router.get("/", response_model=SavedSearchListResponse, include_in_schema=False)
async def list_saved_searches(db: Session = Depends(get_db)):
    items = SavedSearchService(db).list()
    return {"items": items, "total": len(items)}


@saved_search_router.post("", response_model=SavedSearchResponse, status_code=201)
@saved_search_router.post("/", response_model=SavedSearchResponse, status_code=201, include_in_schema=False)
async def create_saved_search(payload: SavedSearchCreate, db: Session = Depends(get_db)):
    return SavedSearchService(db).create(payload.name, payload.query, payload.search_mode)


@saved_search_router.delete("/{saved_id}")
async def delete_saved_search(saved_id: str, db: Session = Depends(get_db)):
    if not SavedSearchService(db).delete(saved_id):
        raise HTTPException(status_code=404, detail="Saved search not found")
    return {"message": "Saved search deleted"}
