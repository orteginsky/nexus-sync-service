# app/models/__init__.py
"""Modelos de SQLAlchemy."""

from app.models.base import Base
from app.models.case_assignment import CaseAssignment

__all__ = ["Base", "CaseAssignment"]
