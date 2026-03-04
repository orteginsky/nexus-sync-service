# app/services/clickup_service.py
"""
Servicio para interactuar con la API de ClickUp.
Obtiene tareas, comentarios, etc.
"""

import httpx
from typing import Dict, List, Optional
from app.config import settings

class ClickUpService:
    BASE_URL = "https://api.clickup.com/api/v2"

    def __init__(self):
        # Asegúrate de que 'api_token' esté definido en tu settings
        self.headers = {
            "Authorization": settings.api_token,
            "Content-Type": "application/json"
        }

    async def get_task_comments(self, task_id: str) -> List[Dict]:
        url = f"{self.BASE_URL}/task/{task_id}/comment"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return data.get("comments", [])
            except httpx.HTTPError as e:
                print(f"❌ Error al obtener comentarios de {task_id}: {e}")
                return []

    async def get_last_comment_with_keyword(self, task_id: str, keyword: str) -> Optional[Dict]:
        """
        Busca el comentario más reciente que contenga el string buscado.
        """
        comments = await self.get_task_comments(task_id)
        if not comments:
            return None
        for comment in reversed(comments):
            text = comment.get("comment_text", "")
            if text and keyword.lower() in text.lower():
                return {
                    "user": comment.get("user", {}).get("username"),
                    "text": text,
                    "date": comment.get("date")
                }
        return None