"""
Configuración optimizada para el Sincronizador Nexus.
Se centra en la conexión a DB y autenticación con Google.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Dict
import json


class Settings(BaseSettings):
    """Configuración del microservicio de sincronización"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # --- DATABASE ---
    # DATABASE_URL tiene prioridad (especialmente el formato de socket para Cloud Run)
    database_url: Optional[str] = None
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "nexus_legal_db"
    database_user: str = "nexus_user"
    database_password: str = ""
    database_ssl_mode: str = "disable"

    api_token:str 
    # --- GOOGLE SHEETS ---
    # El Master URL se define en el servicio, pero aquí manejamos el acceso
    google_sheets_credentials_path: Optional[str] = None
    google_sheets_credentials_json: Optional[str] = None
    google_sheets_enabled: bool = True
    
    # La URL de las google sheets
    GOOGLE_SHEETS_SPREADSHEET_ID: str = "1U21BvVZtiJBnGyy9RJ1oRZQR-x4q6xQNCfqqKjqlKxA"
    COLUMN_MAPPING: Dict = {
        "task_id": "ID",
        "task_name": "Task Name",
        "status": "Status",
        "assignee": "Assignee",
        "due_date": "Due Date",
        "abogado_asignado": "🧑‍⚖️ Abogado Asignado",
        "proyecto": "🗂️ Proyecto",
        "id_cliente": "ID Cliente",
        "priority": "Priority",
        "date_created": "Date Created",
        "date_updated": "Date Updated",
        "date_closed": "Date Closed",
        "date_done": "Date Done",
        "case_review_status": "Case Review Status",
        "open_case_type": "Open Case type",
        "rapsheet_status": "Rapsheet",
        "label_type": "🔖 Label Type",
        "cr_done_date": "CR Done Date",
        "date_status_signed": "Date Status SIGNED",
        "packet_ready_cr": "Packet ready for CR",
        "caso_resometer": "Caso para Resometer",
    }
    master_url: str = "https://docs.google.com/spreadsheets/d/1U21BvVZtiJBnGyy9RJ1oRZQR-x4q6xQNCfqqKjqlKxA/edit"
    unificado_url: str = "https://docs.google.com/spreadsheets/d/10ygkwwapPEnK4_AWMsbVNxmgbnb-pxr-Okoy-5xbbG4/edit"
    visas_url: str = "https://docs.google.com/spreadsheets/d/1GnOoXNRfRi4AR39m2FSKtfUc-r0bppYNpG4eWwBOm8E/edit"
    import_url: str = "https://docs.google.com/spreadsheets/d/1b9H54Z3mSbtrjJmz5Gc4lm76G5HRNmeJMyK9QLWIPmA/edit"
    descarga_mc_url: str = "https://docs.google.com/spreadsheets/d/1JTeMfMik_5slthEv1AY1b5jxWen4pAAPZbmR_2TTLFg"

    # --- APPLICATION ---
    app_env: str = "production"
    debug: bool = False
    log_level: str = "INFO"
    cors_origins: str = "*"

    @property
    def database_dsn(self) -> str:
        """Retorna la URL de conexión. Prioriza DATABASE_URL de las variables de entorno."""
        if self.database_url:
            return self.database_url

        return (
            f"postgresql://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
            f"?sslmode={self.database_ssl_mode}"
        )

    @property
    def cors_origins_list(self) -> list[str]:
        """Convierte string de CORS a lista para FastAPI"""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def google_credentials_dict(self) -> Optional[dict]:
        """Parsea el JSON de credenciales si existe y no está vacío."""
        # 1. Limpiamos espacios y validamos que no sea None o vacío
        value = (self.google_sheets_credentials_json or "").strip()
        
        if not value:
            return None

        try:
            # 2. Intentamos parsear solo si hay contenido real
            return json.loads(value)
        except json.JSONDecodeError as e:
            # Devolver None para que intente ADC como fallback
            print(f"⚠️ Error parseando JSON de credenciales: {e}. Reintentando con ADC...")
            return None

# Singleton para importar en el resto de la app
settings = Settings()