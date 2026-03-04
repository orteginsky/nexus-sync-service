import re
from datetime import datetime
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)

# [Mantenemos NOMBRES_VALIDOS y DATE_COLUMNS igual...]
NOMBRES_VALIDOS = [
    "Pedro Nieves", "Eugenia Ibarra", "Paola Linares", "Jesús Rosario",
    "Jesus Rosario", "Jesús Daniel Martínez Irizarry", "Jeyka Perez",
    "Laura Rivera", "Saquía Rivera Azize", "Cristian Soto", "Janice Zayas",
    "Barbara Becerra", "Felmarie Figuera", "Felmarie Figueroa",
    "Vanelisse Encarnación", "Edwin Rivera", "Eric Dessus",
    "Eric Ian Dessus Matos", "Maria Colon", "Jesús Martinez", "Jose Ballesteros",
]

DATE_COLUMNS = [
    # Nombres de columna en Google Sheets (los que llegan al processor desde sheet_service)
    "Start Date", "Date Created", "Date Updated", "Date Closed", "Date Done",
    "Due Date", "CR Done Date", "Date Status SIGNED",
    "CR Done Date (date)", "Date Status SIGNED (date)",
    # Nombres de atributo en DB (por compatibilidad con otros flujos)
    "due_date", "date_created", "date_updated", "date_closed", "date_done",
    "cr_done_date", "date_status_signed", "fecha_asignacion",
    "open_case_date", "deadline_statute",
]

class DataProcessor:
    """Procesador de datos para limpieza, normalización y cálculo de lógica de negocio."""

    # El SWITCH de Google Sheets mapeado a categorías de Backlog
    OUTCOME_MAP = {
        "lea - missing": "Packets Backlog",
        "additional docs done": "Packets Backlog",
        "compliance done": "Attorney backlog",
        "case review done": "Attorney backlog",
        "corrections done/pend sign": "Attorney backlog",
        "pending atty review": "Attorney backlog",
        "pending decl sign atty": "Attorney backlog",
        "compliance cdmx review": "CAD Backlog",
        "docs pending translations": "Writters Backlog",
        "pend final review assembly": "Packets Backlog",
        "pending decl corrections": "Packets Backlog",
        "pending forms corrections": "Packets Backlog",
        "translations done": "Packets Backlog",
        "pending additional docs": "FU Backlog",
        "cr-assigned pending": "Pending to CR Backlog",
        "cr-case cancelled": "Pending to CR Backlog",
        "cr-on progress": "Pending to CR Backlog",
        "cr-unresponsive": "Pending to CR Backlog",
        "pending": "Pending to CR Backlog",
        "pending case review": "Pending to CR Backlog",
        "pending to cr": "Pending to CR Backlog",
        "cancellation request": "Cancun",
        "signed": "Signed"
    }

    def __init__(self):
        self.nombres_validos = NOMBRES_VALIDOS
        self.date_columns = DATE_COLUMNS

    def calcular_outcome(self, status_value: Any) -> str:
        """
        Replica la lógica de ARRAYFORMULA(SI(C2:C="", "", SWITCH...))
        donde 'C' es la columna de Status.
        """
        if status_value is None:
            return ""
        
        # Normalizamos el valor para el match (minúsculas y sin espacios)
        s = str(status_value).strip().lower()
        
        if not s:
            return ""
            
        # Retorna el mapeo o vacío si no coincide con ninguna regla
        return self.OUTCOME_MAP.get(s, "")

    def limpiar_id(self, value) -> Optional[int]:
        if value is None or str(value).strip().lower() in ("none", "null", ""):
            return None
        solo_numeros = re.sub(r'\D', '', str(value))
        try:
            return int(solo_numeros) if solo_numeros else None
        except ValueError:
            return None

    def convertir_fecha_ddmmaaaa(self, val) -> str:
        if val is None:
            return ""
        if isinstance(val, datetime):
            return val.strftime("%d/%m/%Y")
        s = str(val).strip()
        if not s or s.lower() in ("none", "null", "nat"):
            return ""
        try:
            return datetime.fromisoformat(s).strftime("%d/%m/%Y")
        except ValueError: 
            pass
        s = s.replace(".", "/").replace("-", "/")
        match = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", s)
        if match: s = match.group(1)
        formatos = ["%m/%d/%Y", "%d/%m/%Y", "%m/%d/%y", "%d/%m/%y", "%Y/%m/%d", "%B %d %Y", "%Y-%m-%d"]
        for fmt in formatos:
            try: return datetime.strptime(s, fmt).strftime("%d/%m/%Y")
            except ValueError: continue
        return str(val)

    def limpiar_assignee_value(self, assignee: Optional[str]) -> str:
        a = (assignee or "").strip()
        if not a: return a
        if "barbara" in a.lower(): return "Barbara Becerra"
        for name in self.nombres_validos:
            if name.lower() in a.lower(): return name
        return a

    def procesar_fila(self, row_data: dict) -> dict:
        """Procesa una fila completa y genera la columna calculada OUTCOME."""
        processed = {}

        # 1. Limpieza y normalización estándar
        for key, value in row_data.items():
            if key is None: continue
            
            key_str = str(key)
            key_lower = key_str.lower()
            
            if key_lower == "assignee":
                processed[key_str] = self.limpiar_assignee_value(value)
            elif key_str in self.date_columns or key_lower in [c.lower() for c in self.date_columns]:
                processed[key_str] = self.convertir_fecha_ddmmaaaa(value)
            elif key_lower in ("id_cliente", "id cliente"):
                processed[key_str] = self.limpiar_id(value)
            else:
                if value is None:
                    processed[key_str] = ""
                elif isinstance(value, (int, float)):
                    processed[key_str] = value
                else:
                    processed[key_str] = str(value).strip()

        # 2. CÁLCULO DE OUTCOME (Basado en el Status ya normalizado)
        # Buscamos 'Status' (que es el nombre en el mapping de Sheets)
        status_actual = processed.get("Status")
        processed["OUTCOME"] = self.calcular_outcome(status_actual)

        return processed

processor = DataProcessor()