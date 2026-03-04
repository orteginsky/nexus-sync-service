# app/api/lookup_route.py
"""
Endpoints para cruzar campos de la BD con task_ids.

Por id_cliente:
- POST /lookup/task-ids              → cruce masivo (Set de ids_cliente → task_ids)
- GET  /lookup/task-id/{id_cliente}  → cruce individual con warning si hay duplicados

Por task_name:
- POST /lookup/task-ids-by-name      → cruce masivo (Set de task_names → task_ids)
- GET  /lookup/task-id-by-name       → cruce individual (?task_name=...) con warning si hay duplicados
"""

import logging

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.schemas import (
    ClienteLookupRequest,
    ClienteLookupResponse,
    ClienteLookupItem,
    SingleClienteLookupResponse,
    TaskNameLookupRequest,
    TaskNameLookupResponse,
    TaskNameLookupItem,
    SingleTaskNameLookupResponse,
)
from app.database import get_db
from app.models.case_assignment import CaseAssignment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lookup", tags=["Lookup → task_id"])


# ---------------------------------------------------------------------------
# POST /lookup/task-ids  — cruce masivo
# ---------------------------------------------------------------------------

@router.post("/task-ids", response_model=ClienteLookupResponse)
def lookup_task_ids(
    request: ClienteLookupRequest,
    db: Session = Depends(get_db),
) -> ClienteLookupResponse:
    """
    Recibe un conjunto de **id_cliente** (strings de 8 dígitos) y devuelve
    el **task_id** correspondiente para cada uno.

    - Si un id_cliente tiene múltiples registros en la BD se toma el primero
      (ordenado por `synced_at` descendente para priorizar el más reciente).
    - Los ids que no se encuentren en la BD aparecen en la lista `not_found`.

    **Input**
    ```json
    { "ids_cliente": ["12345678", "87654321"] }
    ```

    **Output**
    ```json
    {
      "found": [
        { "id_cliente": "12345678", "task_id": "abc123" }
      ],
      "not_found": ["87654321"]
    }
    ```
    """
    ids = list(request.ids_cliente)
    logger.info("Lookup masivo para %d id_cliente(s)", len(ids))

    # Consulta optimizada: un solo IN sobre el índice de id_cliente
    rows = (
        db.query(CaseAssignment.id_cliente, CaseAssignment.task_id)
        .filter(CaseAssignment.id_cliente.in_(ids))
        .order_by(CaseAssignment.id_cliente, CaseAssignment.synced_at.desc())
        .all()
    )

    # Tomar el primer task_id por id_cliente (el más reciente dado el ORDER BY)
    seen: dict[str, str] = {}
    for id_cliente, task_id in rows:
        if id_cliente not in seen:
            seen[id_cliente] = task_id

    found = [ClienteLookupItem(id_cliente=k, task_id=v) for k, v in seen.items()]
    not_found = [id_ for id_ in ids if id_ not in seen]

    logger.info("Encontrados: %d | No encontrados: %d", len(found), len(not_found))
    return ClienteLookupResponse(found=found, not_found=not_found)


# ---------------------------------------------------------------------------
# GET /lookup/task-id/{id_cliente}  — cruce individual
# ---------------------------------------------------------------------------

@router.get("/task-id/{id_cliente}", response_model=SingleClienteLookupResponse)
def lookup_single_task_id(
    id_cliente: str = Path(
        ...,
        description="ID de cliente: string de exactamente 8 dígitos.",
        pattern=r"^\d{8}$",
        min_length=8,
        max_length=8,
    ),
    db: Session = Depends(get_db),
) -> SingleClienteLookupResponse:
    """
    Recibe un único **id_cliente** (string de 8 dígitos) y devuelve su
    **task_id**.

    - Si existen **más de un registro** con ese id_cliente se retorna el
      primer `task_id` (el más reciente) y se incluye un campo `warning`
      indicando la cantidad de registros encontrados.
    - Si no se encuentra ningún registro, `task_id` es `null`.

    **Output (caso único)**
    ```json
    { "id_cliente": "12345678", "task_id": "abc123", "warning": null }
    ```

    **Output (caso duplicados)**
    ```json
    {
      "id_cliente": "12345678",
      "task_id": "abc123",
      "warning": "Se encontraron 3 registros para este id_cliente. Se retorna el task_id más reciente."
    }
    ```
    """
    logger.info("Lookup individual para id_cliente=%s", id_cliente)

    rows = (
        db.query(CaseAssignment.task_id)
        .filter(CaseAssignment.id_cliente == id_cliente)
        .order_by(CaseAssignment.synced_at.desc())
        .all()
    )

    if not rows:
        logger.info("id_cliente=%s no encontrado", id_cliente)
        return SingleClienteLookupResponse(id_cliente=id_cliente, task_id=None)

    task_ids = [r.task_id for r in rows]
    warning = None

    if len(task_ids) > 1:
        warning = (
            f"Se encontraron {len(task_ids)} registros para este id_cliente. "
            "Se retorna el task_id más reciente."
        )
        logger.warning("id_cliente=%s tiene %d registros duplicados", id_cliente, len(task_ids))

    return SingleClienteLookupResponse(
        id_cliente=id_cliente,
        task_id=task_ids[0],
        warning=warning,
    )


# ---------------------------------------------------------------------------
# POST /lookup/task-ids-by-name  — cruce masivo por task_name
# ---------------------------------------------------------------------------

@router.post("/task-ids-by-name", response_model=TaskNameLookupResponse)
def lookup_task_ids_by_name(
    request: TaskNameLookupRequest,
    db: Session = Depends(get_db),
) -> TaskNameLookupResponse:
    """
    Recibe un conjunto de **task_name** y devuelve el **task_id** correspondiente
    para cada uno.

    - Si un task_name tiene múltiples registros en la BD se toma el más reciente
      (ordenado por `synced_at` descendente).
    - Los task_names que no se encuentren aparecen en la lista `not_found`.

    **Input**
    ```json
    { "task_names": ["Juan Perez - Case Review", "Maria Lopez - Open Case"] }
    ```

    **Output**
    ```json
    {
      "found": [
        { "task_name": "Juan Perez - Case Review", "task_id": "abc123" }
      ],
      "not_found": ["Maria Lopez - Open Case"]
    }
    ```
    """
    names = list(request.task_names)
    logger.info("Lookup masivo por task_name para %d nombre(s)", len(names))

    rows = (
        db.query(CaseAssignment.task_name, CaseAssignment.task_id)
        .filter(CaseAssignment.task_name.in_(names))
        .order_by(CaseAssignment.task_name, CaseAssignment.synced_at.desc())
        .all()
    )

    seen: dict[str, str] = {}
    for task_name, task_id in rows:
        if task_name not in seen:
            seen[task_name] = task_id

    found = [TaskNameLookupItem(task_name=k, task_id=v) for k, v in seen.items()]
    not_found = [name for name in names if name not in seen]

    logger.info("Encontrados: %d | No encontrados: %d", len(found), len(not_found))
    return TaskNameLookupResponse(found=found, not_found=not_found)


# ---------------------------------------------------------------------------
# GET /lookup/task-id-by-name  — cruce individual por task_name
# ---------------------------------------------------------------------------

@router.get("/task-id-by-name", response_model=SingleTaskNameLookupResponse)
def lookup_single_task_id_by_name(
    task_name: str = Query(
        ...,
        description="Nombre exacto del task a buscar.",
        min_length=1,
    ),
    db: Session = Depends(get_db),
) -> SingleTaskNameLookupResponse:
    """
    Recibe un único **task_name** y devuelve su **task_id**.

    Se usa query parameter (`?task_name=...`) para soportar nombres con
    espacios y caracteres especiales sin problemas de URL encoding en el path.

    - Si existen **más de un registro** con ese task_name se retorna el
      más reciente y se incluye un campo `warning`.
    - Si no se encuentra ningún registro, `task_id` es `null`.

    **Output (caso único)**
    ```json
    { "task_name": "Juan Perez - Case Review", "task_id": "abc123", "warning": null }
    ```

    **Output (con duplicados)**
    ```json
    {
      "task_name": "Juan Perez - Case Review",
      "task_id": "abc123",
      "warning": "Se encontraron 2 registros para este task_name. Se retorna el task_id más reciente."
    }
    ```
    """
    logger.info("Lookup individual por task_name='%s'", task_name)

    rows = (
        db.query(CaseAssignment.task_id)
        .filter(CaseAssignment.task_name == task_name)
        .order_by(CaseAssignment.synced_at.desc())
        .all()
    )

    if not rows:
        logger.info("task_name='%s' no encontrado", task_name)
        return SingleTaskNameLookupResponse(task_name=task_name, task_id=None)

    task_ids = [r.task_id for r in rows]
    warning = None

    if len(task_ids) > 1:
        warning = (
            f"Se encontraron {len(task_ids)} registros para este task_name. "
            "Se retorna el task_id más reciente."
        )
        logger.warning("task_name='%s' tiene %d registros duplicados", task_name, len(task_ids))

    return SingleTaskNameLookupResponse(
        task_name=task_name,
        task_id=task_ids[0],
        warning=warning,
    )
