# Sincronizador Nexus

Microservicio FastAPI que lee la tabla `case_assignments` en PostgreSQL, limpia y normaliza los datos y actualiza la hoja Master del despacho.

## Requisitos
- Python 3.11 (verificado en `.venv/pyvenv.cfg`)
- PostgreSQL accesible con las tablas `case_assignments` y `leads_cache`
- Credenciales de Service Account con acceso a Drive/Sheets (`drive-sheets@ortega-473114.iam.gserviceaccount.com`)
- Opcional: Entorno virtual creado (`python -m venv .venv`)

## Instalación
```bash
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Configuración (.env)
Variables principales usadas por `app/config.py`:

| Variable | Descripción | Ejemplo |
| --- | --- | --- |
| `DATABASE_URL` | DSN completo; si no se define se arma con host/port/etc. | `postgresql://user:pass@host:5432/nexus_legal_db?sslmode=require` |
| `DATABASE_HOST` / `DATABASE_PORT` / `DATABASE_NAME` / `DATABASE_USER` / `DATABASE_PASSWORD` / `DATABASE_SSL_MODE` | Componentes para construir el DSN | |
| `GOOGLE_SHEETS_ENABLED` | `true` para habilitar escritura en Sheets | `true` |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | ID de la hoja Master (opcional, usa default en código) | |
| `GOOGLE_SHEETS_CREDENTIALS_JSON` | Credenciales en JSON (string). Prioridad sobre ruta de archivo. | `{"type": "...", ...}` |
| `GOOGLE_SHEETS_CREDENTIALS_PATH` | Ruta al archivo JSON si no se usa el campo anterior | `./service-account.json` |
| `CORS_ORIGINS` | Lista separada por comas o `*` | `*` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |

> Nota: Si defines ambos `GOOGLE_SHEETS_CREDENTIALS_JSON` y `GOOGLE_SHEETS_CREDENTIALS_PATH`, prevalece el JSON embebido (útil para Cloud Run/Secrets).

## Ejecutar en local
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Healthcheck: http://localhost:8000/health
```

## Endpoints principales
- `POST /sync/master`  
  Lanza la sincronización DB → Google Sheets. Devuelve estadísticas (`rows_updated`, `rows_inserted`, duración, errores).
- `POST /sync/master/background`  
  Encola la sincronización en segundo plano (útil para botones de Apps Script).
- `GET /sync/status`  
  Estado simple del servicio.
- `GET /` y `GET /health`  
  Comprobaciones de disponibilidad.

## Flujo de sincronización
1) Lee todos los registros de `case_assignments` usando SQLAlchemy (`app/database.py`).  
2) Mapea columnas DB → Sheets y limpia datos (`app/core/processor.py`):
   - Normaliza assignee (incluye reglas específicas: cualquier “barbara” → “Barbara Becerra”).
   - Formatea fechas a `DD/MM/YYYY`.
   - Limpia `ID Cliente` dejando solo dígitos.
3) Escribe en la hoja Master (`app/services/sheet_service.py`):
   - Upsert por columna **ID** (task_id).  
   - Actualizaciones en batch para respetar cuotas.  
   - Inserta filas nuevas cuando el ID no existe.

## Estructura del proyecto
```
nexus-sync-service/
├── app/
│   ├── api/            # Rutas FastAPI (trigger de sincronización)
│   ├── core/           # Limpieza
│   ├── models/         # Modelos SQLAlchemy (case_assignments)
│   ├── services/       # Orquestador de Sheets
│   ├── database.py     # Session factory
│   ├── config.py       # Settings via Pydantic
│   └── main.py         # App FastAPI
├── documentacion_tecnica.md  # Detalle funcional
└── requirements.txt
```

## Despliegue sugerido
- Contenedor + Cloud Run (o servicio equivalente) con variables de entorno seguras.
- Otorga a la service account el rol **Cloud SQL Client** y permisos de edición en las hojas externas.
- Configura un Apps Script en la hoja Master para invocar `POST /sync/master` mediante un botón.

## Troubleshooting rápido
- **Sin credenciales válidas**: se lanzará `ValueError` al intentar autorizar gspread. Verifica `GOOGLE_SHEETS_CREDENTIALS_JSON` o la ruta de archivo.  
- **Fechas mal formateadas**: se registran en logs como “No se pudo parsear la fecha”; revisa `DATE_COLUMNS` en `app/core/processor.py`.  
- **Cuotas de Google**: el servicio usa lotes (200 filas, espera 0.8s). Ajusta `wait_seconds` en `_batch_update` si ves throttling.

## Próximos pasos (ideas)
- Agregar pruebas unitarias para `DataProcessor`.
- Hacer configurable el `COLUMN_MAPPING` vía variable JSON (`GOOGLE_SHEETS_FIELD_MAPPING` ya previsto).
