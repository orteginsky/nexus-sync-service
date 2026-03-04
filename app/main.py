# app/main.py
"""
Sincronizador Nexus - Microservicio FastAPI
Sincroniza datos de PostgreSQL hacia Google Sheets Master.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.sync_route import router as sync_router
from app.api.clickup_route import router as clickup_router
from app.api.lookup_route import router as lookup_router

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events de la aplicación."""
    logger.info("🚀 Sincronizador Nexus iniciando...")
    logger.info(f"Entorno: {settings.app_env}")
    logger.info(f"Google Sheets habilitado: {settings.google_sheets_enabled}")
    yield
    logger.info("👋 Sincronizador Nexus cerrando...")


app = FastAPI(
    title="Sincronizador Nexus",
    description="Microservicio para sincronizar case_assignments de PostgreSQL hacia Google Sheets Master",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(sync_router)
app.include_router(clickup_router)
app.include_router(lookup_router)


@app.get("/")
async def root():
    """Health check del servicio."""
    return {
        "service": "Sincronizador Nexus",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    """Endpoint de health check para Cloud Run."""
    return {"status": "healthy"}
