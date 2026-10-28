"""Assistant API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.base import get_db
from app.schemas.assistant import AssistantRequest, AssistantResponse
from app.services.assistant_service import AssistantService

router = APIRouter()


@router.post("/ask", response_model=AssistantResponse)
async def ask(request: AssistantRequest, db: Session = Depends(get_db)):
    """Answer a question grounded in indexed documents."""
    return await AssistantService(db).ask(request)
