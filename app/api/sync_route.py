# app/api/sync_route.py
"""
Endpoint para disparar la sincronización DB -> Google Sheets.
Diseñado para ser llamado desde un botón de Apps Script en Google Sheets.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.schemas import SyncRequest, SyncResponse, SyncBackgroundResponse
from app.database import get_db
from app.services.sheet_service import get_sheet_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["Sincronización"])

def _background_sync_task(db_url: str):
    """
    Tarea de sincronización para ejecución en background.
    Crea su propia sesión de DB.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    try:
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        try:
            service = get_sheet_service()
            stats = service.sincronizar(db)
            logger.info(
                f"Background sync completado - "
                f"Actualizados: {stats.rows_updated}, Insertados: {stats.rows_inserted}"
            )
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error en background sync: {e}")
        raise


@router.post("/master", response_model=SyncResponse)
async def sync_master(request: SyncRequest, db: Session = Depends(get_db)) -> SyncResponse:
    """
    Sincroniza los datos de case_assignments hacia la hoja Master.

    Este endpoint:
    1. Lee todos los registros de la tabla case_assignments
    2. Limpia y normaliza los datos (assignees, fechas)
    3. Actualiza o inserta filas en la hoja Master

    Returns:
        SyncResponse con estadísticas del proceso

    Raises:
        HTTPException: Si ocurre un error durante la sincronización
    """
    logger.info("📌 Recibida solicitud de sincronización")

    try:
        # 1. Obtener el servicio base
        service = get_sheet_service()
        
        # 2. Aplicar prioridad: Si viene en el JSON, sobreescribimos los valores del servicio
        if request.master_url:
            service.master_url = request.master_url
        if request.master_tab:
            service.master_tab = request.master_tab

        stats = service.sincronizar(db)

        return SyncResponse(
            success=True,
            message=f"Sincronización completada. Actualizados: {stats.rows_updated}, Insertados: {stats.rows_inserted}",
            stats={
                "total_db_records": stats.total_db_records,
                "rows_updated": stats.rows_updated,
                "rows_inserted": stats.rows_inserted,
                "duration_seconds": round(stats.duration_seconds, 2),
                "errors": stats.errors,
            },
            timestamp=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.error(f"Error en sincronización: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error durante la sincronización: {str(e)}",
        )


@router.post("/master/background", response_model=SyncBackgroundResponse)
async def sync_master_background(
    background_tasks: BackgroundTasks,
) -> SyncBackgroundResponse:
    """
    Inicia la sincronización en segundo plano.

    Útil cuando la sincronización toma mucho tiempo y no se quiere
    esperar la respuesta HTTP.

    Returns:
        SyncBackgroundResponse confirmando que la tarea fue encolada
    """
    from app.config import settings

    logger.info("📌 Iniciando sincronización en background")

    background_tasks.add_task(_background_sync_task, settings.database_dsn)

    return SyncBackgroundResponse(
        success=True,
        message="Sincronización iniciada en segundo plano",
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get("/status")
async def sync_status():
    """
    Verifica el estado del servicio de sincronización.

    Returns:
        Diccionario con estado del servicio
    """
    return {
        "status": "healthy",
        "service": "Sincronizador Nexus",
        "timestamp": datetime.utcnow().isoformat(),
    }
