from pydantic import BaseModel, field_validator
from typing import Optional, List, Set


class SyncRequest(BaseModel):
    """Parámetros opcionales para personalizar la sincronización desde el request."""
    master_url: Optional[str] = None
    master_tab: Optional[str] = None

class SyncResponse(BaseModel):
    success: bool
    message: str
    stats: Optional[dict] = None
    timestamp: str

class SyncBackgroundResponse(BaseModel):
    success: bool
    message: str
    timestamp: str


# ---------------------------------------------------------------------------
# Lookup: id_cliente → task_id
# ---------------------------------------------------------------------------

class ClienteLookupRequest(BaseModel):
    """
    Conjunto de IDs de cliente (strings de exactamente 8 dígitos) para
    realizar un cruce masivo contra la base de datos y obtener sus task_ids.
    """
    ids_cliente: Set[str]

    @field_validator("ids_cliente")
    @classmethod
    def validar_ids(cls, v: Set[str]) -> Set[str]:
        if not v:
            raise ValueError("ids_cliente no puede estar vacío.")
        for id_ in v:
            if not id_.isdigit() or len(id_) != 8:
                raise ValueError(
                    f"'{id_}' no es válido. Cada id_cliente debe ser un string de exactamente 8 dígitos."
                )
        return v


class ClienteLookupItem(BaseModel):
    """Resultado individual del cruce para un id_cliente."""
    id_cliente: str
    task_id: Optional[str]


class ClienteLookupResponse(BaseModel):
    """Respuesta del endpoint de lookup masivo."""
    found: List[ClienteLookupItem]
    not_found: List[str]


class SingleClienteLookupResponse(BaseModel):
    """
    Respuesta del endpoint de lookup individual.
    Si existe más de un registro con el mismo id_cliente, se retorna el
    primer task_id encontrado y se activa el campo 'warning'.
    """
    id_cliente: str
    task_id: Optional[str]
    warning: Optional[str] = None


# ---------------------------------------------------------------------------
# Lookup: task_name → task_id
# ---------------------------------------------------------------------------

class TaskNameLookupRequest(BaseModel):
    """
    Conjunto de task_names para realizar un cruce masivo contra la base de
    datos y obtener sus task_ids.
    """
    task_names: Set[str]

    @field_validator("task_names")
    @classmethod
    def validar_task_names(cls, v: Set[str]) -> Set[str]:
        if not v:
            raise ValueError("task_names no puede estar vacío.")
        for name in v:
            if not name.strip():
                raise ValueError("Los task_names no pueden ser cadenas vacías o sólo espacios.")
        return v


class TaskNameLookupItem(BaseModel):
    """Resultado individual del cruce para un task_name."""
    task_name: str
    task_id: Optional[str]


class TaskNameLookupResponse(BaseModel):
    """Respuesta del endpoint de lookup masivo por task_name."""
    found: List[TaskNameLookupItem]
    not_found: List[str]


class SingleTaskNameLookupResponse(BaseModel):
    """
    Respuesta del endpoint de lookup individual por task_name.
    Si existe más de un registro con el mismo task_name, se retorna el
    primer task_id encontrado y se activa el campo 'warning'.
    """
    task_name: str
    task_id: Optional[str]
    warning: Optional[str] = None