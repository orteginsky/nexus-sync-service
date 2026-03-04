# app/database.py
"""
Configuración de conexión a la base de datos.
Session factory y dependency injection para FastAPI.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.config import settings

# Motor de SQLAlchemy
engine = create_engine(
    settings.database_dsn,
    pool_pre_ping=True,  # Verifica conexión antes de usar
    pool_size=5,
    max_overflow=10,
    echo=settings.debug  # Log SQL queries en debug mode
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency para FastAPI.
    Crea una sesión de DB por request y la cierra al terminar.

    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
