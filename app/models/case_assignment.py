# app/models/case_assignment.py
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, Index, JSON
from sqlalchemy.sql import func
from app.models.base import Base

class CaseAssignment(Base):
    """
    Modelo para la lista 'Case Assignment'.
    Almacena el seguimiento de casos asignados, firmas y documentos.
    """
    __tablename__ = "case_assignments"

    # Identificadores Únicos
    task_id = Column(String(50), primary_key=True, index=True)
    id_cliente = Column(String(255), nullable=True, index=True)
    mycase_link = Column(Text, nullable=True)
    
    # Metadatos de Sistema
    task_name = Column(Text, nullable=True)
    status = Column(String(255), nullable=True)
    priority = Column(String(255), nullable=True)
    assignee = Column(Text, nullable=True)
    list_name = Column(String(255), nullable=True, default="Case Assignment")
    created_by = Column(String(255), nullable=True)
    folder_name = Column(String(255), nullable=True)
    space_name = Column(String(255), nullable=True)
    
    # Fechas (Basado en el análisis de TIMESTAMP)
    date_created = Column(DateTime(timezone=True), nullable=True)
    date_updated = Column(DateTime(timezone=True), nullable=True)
    date_closed = Column(DateTime(timezone=True), nullable=True)
    date_done = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    
    # Campos Específicos de Negocio (Mapeados de C y análisis CSV)
    abogado_asignado = Column(String(255), nullable=True)
    proyecto = Column(String(255), nullable=True)
    label_type = Column(String(255), nullable=True)
    case_review_status = Column(String(255), nullable=True)
    open_case_type = Column(String(255), nullable=True)
    rapsheet_status = Column(String(255), nullable=True)
    antiguos_attorney = Column(String(255), nullable=True)
    
    # Documentación y Links
    link_audio_cr = Column(Text, nullable=True)
    link_google_meet = Column(Text, nullable=True)
    link_decl_spanish = Column(Text, nullable=True)
    cover_letter_link = Column(Text, nullable=True)
    p_plus_filed_copy = Column(Text, nullable=True)
    
    # Fechas de Proceso
    cr_done_date = Column(DateTime(timezone=True), nullable=True)
    date_status_signed = Column(DateTime(timezone=True), nullable=True)
    fecha_asignacion = Column(DateTime(timezone=True), nullable=True)
    open_case_date = Column(DateTime(timezone=True), nullable=True)
    deadline_statute = Column(DateTime(timezone=True), nullable=True)
    
    # Checkboxes y Fórmulas (Basado en BOOLEAN del análisis)
    packet_ready_cr = Column(Boolean, nullable=True, default=False)
    caso_resometer = Column(Boolean, nullable=True, default=False)
    cr_done_equals_signed = Column(Boolean, nullable=True) # Fórmula
    signed_in_7_days = Column(Boolean, nullable=True)      # Fórmula

    # Contenido Pesado
    task_content = Column(Text, nullable=True)
    latest_comment = Column(Text, nullable=True)

    # Asegúrate de que list_name también esté si lo usas en el servicio

    # ========================================================================
    # RESPALDO TOTAL (JSONB para Postgres)
    # ========================================================================
    raw_data = Column(JSON, nullable=True, comment="Copia íntegra del webhook")
    
    synced_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CaseAssignment(task_id={self.task_id}, client={self.id_cliente})>"