"""Schemas para solicitudes del módulo Gestión de Solicitudes."""

from datetime import date, datetime, time
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
    area_consumo: str = ""
    cantidad: float = 1.0
    cantidad_recibida: float = 0.0
    cantidad_entregada: float = 0.0
    cantidad_pendiente: float = 1.0
    cantidad_pendiente_recepcion: float = 1.0
    cantidad_disponible_entrega: float = 0.0
    estado_recepcion: str = "pendiente"
    estado_entrega: str = "pendiente"
    estado_aprobacion: str = "pendiente"
    estado_aprobacion_label: str = "Pendiente"
    numero_tramite_oc: str = ""
    valor_tramite_oc: Optional[float] = None


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


class SolicitudGestionVisitaProgramadaResponse(BaseModel):
    id: int
    programador_visita: str
    proveedor_visita: str
    fecha_visita: Optional[date] = None
    hora_visita: Optional[time] = None


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
    numero_consecutivo: Optional[int] = None
    tipo: TipoSolicitudGestion
    titulo: str
    presupuestado: Optional[bool] = None
    centro_costo_area: str
    lider_area_label: str
    estado: EstadoSolicitudGestion
    estado_label: str = ""
    cantidad_productos: int
    cantidad_productos_aprobados: int = 0
    aprobacion_parcial: bool = False
    tiene_tramite_oc_registrado: bool = False
    entrega_completa: bool = False
    tiene_entrega_pendiente: bool = False
    tiene_recepcion_pendiente: bool = False
    recepcion_completa: bool = False
    cantidad_archivos: int
    creado_por_username: str = ""
    gestor_id: Optional[int] = None
    gestor_username: str = ""
    requiere_anticipo: bool = False
    porcentaje_anticipo: Optional[float] = None
    lider_anticipo_label: str = ""
    monto_anticipo: Optional[float] = None
    gestor_anticipo_id: Optional[int] = None
    gestor_anticipo_username: str = ""
    anticipo_gestionado: bool = False
    clasificacion_documento_servicio: str = ""
    clasificacion_documento_servicio_label: str = ""
    gestion_valor_registrada: bool = False
    contrato_id: Optional[int] = None
    contrato_codigo: str = ""
    factura_registrada: bool = False
    factura_registrada_at: Optional[datetime] = None
    cantidad_facturas: int = 0
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
    numero_consecutivo: Optional[int] = None
    tipo: TipoSolicitudGestion
    titulo: str
    presupuestado: Optional[bool] = None
    centro_costo_area: str
    lider_area_id: str
    lider_area_label: str
    observaciones: str
    observaciones_texto: str
    requiere_visita: Optional[bool] = None
    servicio_programado: Optional[bool] = None
    fecha_servicio_programado: Optional[date] = None
    descripcion_servicio: str = ""
    descripcion_servicio_texto: str = ""
    proveedor_sugerido: str = ""
    observaciones_gestion: str = ""
    justificacion_cotizaciones: str = ""
    numero_tramite_oc: str = ""
    valor_tramite_oc: Optional[float] = None
    lider_segunda_aprobacion_id: str = ""
    lider_segunda_aprobacion_label: str = ""
    gestor_id: Optional[int] = None
    gestor_username: str = ""
    requiere_anticipo: bool = False
    porcentaje_anticipo: Optional[float] = None
    lider_anticipo_id: str = ""
    lider_anticipo_label: str = ""
    monto_anticipo: Optional[float] = None
    observaciones_anticipo: str = ""
    gestor_anticipo_id: Optional[int] = None
    gestor_anticipo_username: str = ""
    anticipo_gestionado: bool = False
    clasificacion_documento_servicio: str = ""
    clasificacion_documento_servicio_label: str = ""
    gestion_valor_registrada: bool = False
    contrato_id: Optional[int] = None
    contrato_codigo: str = ""
    factura_registrada: bool = False
    factura_registrada_at: Optional[datetime] = None
    estado: EstadoSolicitudGestion
    creado_por_id: int
    creado_por_username: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    productos: list[SolicitudGestionProductoResponse]
    archivos: list[SolicitudGestionArchivoResponse]
    visitas_programadas: list[SolicitudGestionVisitaProgramadaResponse] = []
    observaciones_trazabilidad: list[SolicitudGestionObservacionResponse] = []
    historial_estados: list[SolicitudGestionHistorialEstadoResponse] = []
    aprobacion_parcial: bool = False
    cantidad_productos_aprobados: int = 0
    tiene_tramite_oc_registrado: bool = False
    entrega_completa: bool = False
    tiene_entrega_pendiente: bool = False
    tiene_recepcion_pendiente: bool = False
    recepcion_completa: bool = False


class RechazarAnticipoBody(BaseModel):
    motivo: str = ""


class MarcarEntregaSolicitudResponse(BaseModel):
    solicitud: SolicitudGestionResponse
    email_enviado: bool = False


class EntregaParcialSolicitudResponse(BaseModel):
    solicitud: SolicitudGestionResponse
    email_enviado: bool = False
    lineas_entrega: list[str] = []


class RecepcionInsumosSolicitudResponse(BaseModel):
    solicitud: SolicitudGestionResponse
    email_enviado: bool = False
    lineas_recepcion: list[str] = []
