## 📘 Documentación Técnica: Sincronizador Nexus

### 1. Resumen del Proyecto

El **Sincronizador Nexus** es un microservicio independiente encargado de leer la tabla `case_assignments` de PostgreSQL, aplicar reglas de limpieza y normalización (heredadas del script de Jupyter), realizar cruces de información (Lookups) con otras hojas de cálculo y actualizar el "Master" de Google Sheets.

### 2. Arquitectura de Datos

El servicio se conectará a la base de datos existente. **Sí, es recomendable reciclar los módulos de conexión** (`database.py`, `config.py` y los `models`) para garantizar que ambos proyectos hablen el mismo idioma y utilicen el mismo pool de conexiones de Cloud SQL.

### 3. Mapeo de Columnas (DB → Sheets)

El microservicio debe realizar la traducción de los nombres técnicos de la base de datos a los nombres legibles del script original:

| Columna en DB (`case_assignments`) | Cabecera en Google Sheets |
| --- | --- |
| `task_id` | **ID** (Usado para el Upsert) |
| `task_name` | **Task Name** |
| `status` | **Status** |
| `assignee` | **Assignee** (Normalizado con lógica de script) |
| `due_date` | **Due Date** (Formato DD/MM/YYYY) |
| `abogado_asignado` | **🧑‍⚖️ Abogado Asignado** |
| `proyecto` | **🗂️ Proyecto** |
| `id_cliente` | **ID Cliente (short text)** |

### 4. Lógica de Procesamiento y Lookups

El servicio replicará las funciones críticas del script de Jupyter antes de subir los datos:

1. **Normalización de Assignee**: Implementará la función `limpiar_assignee_value` para convertir nombres parciales o correos en nombres completos (ej: "barbara" → "Barbara Becerra").
2. **Formateo de Fechas**: Todas las fechas de la DB se convertirán al formato `DD/MM/YYYY` usando una versión optimizada de `convertir_fecha_ddmmaaaa`.
3. **Lookups Externos (Vivos)**:
* El microservicio abrirá las hojas de **Visas**, **Unificado** y **Open Date** en cada ciclo de sincronización.
* Realizará la búsqueda por `ID` o `Task Name` para llenar las columnas AC a AK de la hoja Master.



### 5. Configuración y Seguridad

* **Cuenta de Servicio**: Se utilizará `drive-sheets@ortega-473114.iam.gserviceaccount.com`.
* **Permisos**: Debes asegurarte de que esta cuenta tenga el rol de **Usuario de Cliente de Cloud SQL** en Google Cloud para que pueda realizar consultas a la base de datos.


* **Disparador**: Se expondrá un endpoint `/sync/master`. Un botón en Google Sheets (mediante Apps Script) enviará una solicitud POST a esta URL para iniciar el proceso.

---

### 6. Estructura del Proyecto Recomendada

Para mantenerlo limpio y separado de la lógica de ClickUp:

```text
nexus-sync-service/
├── app/
│   ├── api/            # Endpoint para el botón de Sheets
│   ├── core/           # Lógica de Lookups y Limpieza (heredada de Jupyter)
│   ├── db/             # Reciclado: database.py y models.py
│   └── main.py
├── scripts/            # Script de Apps Script para el botón
├── Dockerfile
└── cloudbuild.yaml

```

### 7. ¿Por qué este diseño?

Al no integrar los Lookups en la base de datos y mantenerlos como consultas a otras Sheets, respetamos la flexibilidad que tu equipo necesita en esas hojas externas, pero centralizamos la "fuerza bruta" del procesamiento en un servidor estable.
