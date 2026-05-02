import time
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import gspread
import google.auth
from google.oauth2 import service_account
from sqlalchemy.orm import Session

from app.core.processor import processor
from app.config import settings # Importante para evitar Hardcoding

logger = logging.getLogger(__name__)

@dataclass
class SyncStats:
    total_db_records: int = 0
    rows_updated: int = 0
    rows_inserted: int = 0
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

class SheetService:
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    def __init__(
        self,
        credentials_dict: Optional[dict] = None,
        credentials_path: Optional[str] = None,
        master_url: Optional[str] = None,
        master_tab: Optional[str] = None,
    ):
        # Si no se pasan por parámetros (ej. en tests), usamos los de config.py
        self.credentials_dict = credentials_dict or settings.google_credentials_dict
        self.credentials_path = credentials_path or settings.google_sheets_credentials_path
        self.master_url = master_url or settings.master_url
        self.master_tab = master_tab or "Master"
        self.client: Optional[gspread.Client] = None


    def _get_credentials(self):
        """Jerarquía de credenciales: JSON String > Archivo > ADC."""
        if self.credentials_dict:
            return service_account.Credentials.from_service_account_info(
                self.credentials_dict, scopes=self.SCOPES
            )
        if self.credentials_path:
            return service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=self.SCOPES
            )
        creds, _ = google.auth.default(scopes=self.SCOPES)
        return creds

    def _get_client(self) -> gspread.Client:
        if self.client is None:
            self.client = gspread.authorize(self._get_credentials())
        return self.client

    def sincronizar(self, db: Session) -> SyncStats:
        from app.models.case_assignment import CaseAssignment
        stats = SyncStats()
        start_time = time.time()

        try:
            # 1. Obtener datos de DB
            db_records = db.query(CaseAssignment).all()
            stats.total_db_records = len(db_records)
            if not db_records: return stats

            # 2. Conectar a Sheets
            ws = self._get_client().open_by_url(self.master_url).worksheet(self.master_tab)
            
            # 3. Mapear la hoja actual
            all_values = ws.get_all_values()
            header = all_values[0] if all_values else []
            
            # Crear mapa de ID -> Número de fila (fila 1 es header, datos empiezan en 2)
            id_col_idx = header.index("ID") if "ID" in header else 0
            existing_ids_map = {
                str(row[id_col_idx]).strip(): i + 2 
                for i, row in enumerate(all_values[1:]) 
                if len(row) > id_col_idx and row[id_col_idx]
            }

            updates = []
            new_rows = []

            # 4. Procesar registros (excluir los que tengan "duplicado" en task_name)
            for record in db_records:
                task_name = getattr(record, 'task_name', '') or ''
                if 'duplicado' in task_name.lower():
                    logger.debug(f"Registro {record.task_id} omitido por task_name duplicado: {task_name!r}")
                    stats.total_db_records -= 1
                    continue
                # Convertimos objeto DB a dict usando tu COLUMN_MAPPING
                raw_data = {col: getattr(record, attr, "") for attr, col in settings.COLUMN_MAPPING.items()}
                clean_data = processor.procesar_fila(raw_data)
                
                # Crear la fila siguiendo el orden exacto del header de la hoja
                ordered_row = [clean_data.get(col_name, "") for col_name in header]
                task_id = str(record.task_id).strip()

                if task_id in existing_ids_map:
                    row_num = existing_ids_map[task_id]
                    updates.append({
                        'range': f'A{row_num}', # gspread batch_update acepta la celda de inicio
                        'values': [ordered_row]
                    })
                    stats.rows_updated += 1
                else:
                    new_rows.append(ordered_row)
                    stats.rows_inserted += 1

            # 5. Ejecutar cambios
            if updates:
                self._batch_update(ws, updates)
            
            if new_rows:
                ws.append_rows(new_rows, value_input_option="USER_ENTERED")

            stats.duration_seconds = time.time() - start_time
            return stats

        except Exception as e:
            logger.error(f"❌ Error en sincronización: {str(e)}")
            stats.errors.append(str(e))
            return stats

    def _with_retry(self, func, *args, max_retries=3, **kwargs):
        """Reintenta una llamada a la API de Google con backoff exponencial ante errores 503."""
        import gspread.exceptions
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except gspread.exceptions.APIError as e:
                status = getattr(e.response, 'status_code', None)
                if status == 503 and attempt < max_retries - 1:
                    wait = 5 * (2 ** attempt)  # 5s, 10s, 20s
                    logger.warning(f"Google API 503 - reintentando en {wait}s (intento {attempt + 1}/{max_retries})")
                    time.sleep(wait)
                else:
                    raise

    def _batch_update(self, ws, updates, chunk_size=100):
        """Actualiza en bloques para no agotar la cuota de la API de Google."""
        for i in range(0, len(updates), chunk_size):
            chunk = updates[i:i + chunk_size]
            self._with_retry(ws.batch_update, chunk, value_input_option="USER_ENTERED")

def get_sheet_service() -> SheetService:
        """
        Factory function para crear una instancia de SheetService 
        utilizando la configuración centralizada de settings.
        """
        from app.config import settings # Importación local para evitar ciclos

        return SheetService(
            credentials_dict=settings.google_credentials_dict,
            credentials_path=settings.google_sheets_credentials_path,
            master_url=settings.master_url,
            master_tab="Master"
        )