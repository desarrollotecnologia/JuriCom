"""Schemas para solicitudes del módulo Gestión de Solicitudes."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.domain.value_objects.estado_solicitud_gestion import EstadoSolicitudGestion
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion


class SolicitudGestionProductoResponse(BaseModel):
    id: int
    codigo_siimed: str
    unidad: str
    descripcion: str
    centro_costo: str
    cantidad: float = 1.0
    cantidad_entregada: float = 0.0
    cantidad_pendiente: float = 1.0
    estado_entrega: str = "pendiente"
    estado_aprobacion: str = "pendiente"
    estado_aprobacion_label: str = "Pendiente"
    numero_tramite_oc: str = ""


class SolicitudGestionArchivoResponse(BaseModel):
    id: int
    nombre_original: str
    mime_type: str
    tamano_bytes: int
    categoria: str = "solicitud"
    observacion_id: Optional[int] = None
    created_at: Optional[datetime] = None


class SolicitudGestionHistorialEstadoResponse(BaseModel):
    id: int
    etapa: EstadoSolicitudGestion
    etapa_label: str
    usuario_id: Optional[int] = None
    usuario_username: str = ""
    comentario: str = ""
    created_at: Optional[datetime] = None


class SolicitudGestionObservacionResponse(BaseModel):
    id: int
    autor_nombre: str
    autor_rol: str
    autor_etiqueta: str
    contenido: str
    contenido_texto: str = ""
    archivos: list[SolicitudGestionArchivoResponse] = []
    created_at: Optional[datetime] = None


class SolicitudGestionListItem(BaseModel):
    id: int
    codigo: str
    tipo: TipoSolicitudGestion
    titulo: str
    presupuestado: Optional[bool] = None
    centro_costo_area: str
    lider_area_label: str
    estado: EstadoSolicitudGestion
    cantidad_productos: int
    cantidad_productos_aprobados: int = 0
    aprobacion_parcial: bool = False
    tiene_tramite_oc_registrado: bool = False
    entrega_completa: bool = False
    tiene_entrega_pendiente: bool = False
    cantidad_archivos: int
    creado_por_username: str = ""
    gestor_id: Optional[int] = None
    gestor_username: str = ""
    created_at: Optional[datetime] = None


class AgregarObservacionSolicitudBody(BaseModel):
    contenido: str = ""
    contenido_texto: str = ""
    contexto_rol: str = "default"


class RechazarSolicitudGestionBody(BaseModel):
    motivo: str = ""


class SolicitudGestionResponse(BaseModel):
    id: int
    codigo: str
    tipo: TipoSolicitudGestion
    titulo: str
    presupuestado: Optional[bool] = None
    centro_costo_area: str
    lider_area_id: str
    lider_area_label: str
    observaciones: str
    observaciones_texto: str
    observaciones_gestion: str = ""
    justificacion_cotizaciones: str = ""
    numero_tramite_oc: str = ""
    lider_segunda_aprobacion_id: str = ""
    lider_segunda_aprobacion_label: str = ""
    gestor_id: Optional[int] = None
    gestor_username: str = ""
    estado: EstadoSolicitudGestion
    creado_por_id: int
    creado_por_username: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    productos: list[SolicitudGestionProductoResponse]
    archivos: list[SolicitudGestionArchivoResponse]
    observaciones_trazabilidad: list[SolicitudGestionObservacionResponse] = []
    historial_estados: list[SolicitudGestionHistorialEstadoResponse] = []
    aprobacion_parcial: bool = False
    cantidad_productos_aprobados: int = 0
    tiene_tramite_oc_registrado: bool = False
    entrega_completa: bool = False
    tiene_entrega_pendiente: bool = False


class MarcarEntregaSolicitudResponse(BaseModel):
    solicitud: SolicitudGestionResponse
    email_enviado: bool = False


class EntregaParcialSolicitudResponse(BaseModel):
    solicitud: SolicitudGestionResponse
    email_enviado: bool = False
    lineas_entrega: list[str] = []
