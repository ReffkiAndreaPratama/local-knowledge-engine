"""Collection and saved-search service."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.collection import Collection, CollectionDocument
from app.models.document import Document
from app.models.search import SavedSearch


class CollectionService:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> List[dict]:
        collections = self.db.query(Collection).order_by(Collection.name).all()
        return [self._to_dict(collection) for collection in collections]

    def get(self, collection_id: str) -> Optional[dict]:
        collection = self.db.query(Collection).filter(Collection.id == collection_id).first()
        return self._to_dict(collection) if collection else None

    def create(self, name: str, description: str | None) -> dict:
        exists = self.db.query(Collection).filter(Collection.name == name).first()
        if exists:
            raise ValueError("A collection with this name already exists")
        collection = Collection(name=name, description=description)
        self.db.add(collection)
        self.db.commit()
        self.db.refresh(collection)
        return self._to_dict(collection)

    def delete(self, collection_id: str) -> bool:
        collection = self.db.query(Collection).filter(Collection.id == collection_id).first()
        if not collection:
            return False
        self.db.delete(collection)
        self.db.commit()
        return True

    def add_documents(self, collection_id: str, document_ids: List[str]) -> int:
        collection = self.db.query(Collection).filter(Collection.id == collection_id).first()
        if not collection:
            raise ValueError("Collection not found")

        valid_ids = {
            row[0]
            for row in self.db.query(Document.id).filter(Document.id.in_(document_ids)).all()
        }
        added = 0
        for document_id in valid_ids:
            existing = (
                self.db.query(CollectionDocument)
                .filter(
                    CollectionDocument.collection_id == collection_id,
                    CollectionDocument.document_id == document_id,
                )
                .first()
            )
            if existing:
                continue
            self.db.add(
                CollectionDocument(collection_id=collection_id, document_id=document_id)
            )
            added += 1
        self.db.commit()
        return added

    def remove_document(self, collection_id: str, document_id: str) -> bool:
        row = (
            self.db.query(CollectionDocument)
            .filter(
                CollectionDocument.collection_id == collection_id,
                CollectionDocument.document_id == document_id,
            )
            .first()
        )
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def document_ids(self, collection_id: str) -> List[str]:
        rows = (
            self.db.query(CollectionDocument.document_id)
            .filter(CollectionDocument.collection_id == collection_id)
            .all()
        )
        return [row[0] for row in rows]

    def _to_dict(self, collection: Collection) -> dict:
        count = (
            self.db.query(CollectionDocument)
            .filter(CollectionDocument.collection_id == collection.id)
            .count()
        )
        return {
            "id": collection.id,
            "name": collection.name,
            "description": collection.description,
            "document_count": count,
            "created_at": collection.created_at,
        }


class SavedSearchService:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> List[SavedSearch]:
        return self.db.query(SavedSearch).order_by(SavedSearch.created_at.desc()).all()

    def create(self, name: str, query: str, search_mode: str) -> SavedSearch:
        saved = SavedSearch(name=name, query=query, search_mode=search_mode)
        self.db.add(saved)
        self.db.commit()
        self.db.refresh(saved)
        return saved

    def delete(self, saved_id: str) -> bool:
        saved = self.db.query(SavedSearch).filter(SavedSearch.id == saved_id).first()
        if not saved:
            return False
        self.db.delete(saved)
        self.db.commit()
        return True
