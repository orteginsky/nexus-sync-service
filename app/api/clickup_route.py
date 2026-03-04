#
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.clickup_service import ClickUpService

router = APIRouter(prefix="/clickup", tags=["ClickUp"])
service = ClickUpService()

# --- Schemas ---
class CommentSearchRequest(BaseModel):
    task_id: str
    keyword: str

class CommentResponse(BaseModel):
    found: bool
    user: Optional[str] = None
    text: Optional[str] = None
    date: Optional[str] = None

# --- Endpoint ---
@router.post("/search-comment", response_model=CommentResponse)
async def search_task_comment(payload: CommentSearchRequest):
    """
    Busca el último comentario en una tarea que coincida con una palabra clave.
    """
    result = await service.get_last_comment_with_keyword(
        payload.task_id, 
        payload.keyword
    )
    
    if not result:
        return CommentResponse(found=False)
    
    return CommentResponse(
        found=True,
        user=result["user"],
        text=result["text"],
        date=result["date"]
    )