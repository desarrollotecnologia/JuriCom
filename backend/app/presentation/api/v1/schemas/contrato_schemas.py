"""Schemas Pydantic para contratos."""

from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.domain.entities.contrato import TipoArchivo
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
from app.domain.value_objects.estado_contrato import EstadoContrato
from app.domain.value_objects.moneda import Moneda
from app.domain.value_objects.tipo_otrosi import TipoOtrosi
from app.domain.value_objects.unidad_plazo import UnidadPlazo


class ArchivoResponse(BaseModel):
    id: int
    tipo: TipoArchivo
    nombre_original: str
    mime_type: str
    tamano_bytes: int
    subido_por_id: Optional[int] = None
    created_at: Optional[datetime] = None


class ContratoBase(BaseModel):
    codigo: Optional[str] = None
    tipo_codigo: str = "C"
    solicitud_gestion_id: Optional[int] = None
    solicitud_gestion_codigo: str = ""
    compania: str
    proveedor_contratista: str
    nit_proveedor: str
    descripcion_servicio: str
    obligaciones_colbeef: str
    obligaciones_proveedor: str
    valor: Decimal
    moneda: Moneda
    plazo_cantidad: int
    plazo_unidad: UnidadPlazo
    renovacion_automatica: bool
    condiciones_recibido_satisfactorio: str
    requiere_poliza: bool
    correo_lider_proceso: str
    correo_gerencia: str
    estado_aprobacion: EstadoAprobacion
    fecha_inicio: Optional[date] = None
    fecha_inicio_original: Optional[date] = None
    fecha_fin: Optional[date] = None
    fecha_proxima_notificacion: Optional[date] = None
    hora_proxima_notificacion: Optional[time] = time(0, 10)
    estado: EstadoContrato
    creado_por_id: int


class OtrosiResponse(BaseModel):
    id: int
    numero: int
    tipo: TipoOtrosi
    descripcion: str
    plazo_adicional_cantidad: Optional[int] = None
    plazo_adicional_unidad: Optional[UnidadPlazo] = None
    valor_adicional: Optional[Decimal] = None
    nueva_descripcion_servicio: Optional[str] = None
    archivo_id: Optional[int] = None
    estado_aprobacion: EstadoAprobacion = EstadoAprobacion.APROBADO
    aprobado_lider_at: Optional[datetime] = None
    aprobado_gerencia_at: Optional[datetime] = None
    creado_por_id: int
    created_at: Optional[datetime] = None


class OtrosiPendienteResponse(BaseModel):
    contrato: ContratoBase
    contrato_id: int
    otrosi: OtrosiResponse


class ContratoListItem(BaseModel):
    id: int
    codigo: Optional[str] = None
    tipo_codigo: str = "C"
    solicitud_gestion_id: Optional[int] = None
    solicitud_gestion_codigo: str = ""
    proveedor_contratista: str
    nit_proveedor: str
    valor: Decimal
    moneda: Moneda
    plazo_cantidad: int
    plazo_unidad: UnidadPlazo
    renovacion_automatica: bool
    requiere_poliza: bool
    tiene_poliza: bool
    tiene_borrador: bool
    cantidad_otrosies: int = 0
    estado_aprobacion: EstadoAprobacion
    estado: EstadoContrato
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    fecha_proxima_notificacion: Optional[date] = None
    hora_proxima_notificacion: Optional[time] = time(0, 10)
    eliminado_at: Optional[datetime] = None
    eliminado_por_id: Optional[int] = None
    eliminado_observacion: str = ""
    dias_para_vencer: Optional[int] = None
    alerta_vencimiento: bool = False
    created_at: Optional[datetime] = None


class SeguimientoContratoResponse(BaseModel):
    codigo: str
    tipo_codigo: str = "C"
    solicitud_gestion_id: Optional[int] = None
    solicitud_gestion_codigo: str = ""
    proveedor_contratista: str
    estado_aprobacion: EstadoAprobacion
    estado: EstadoContrato
    creado_en: Optional[datetime] = None
    aprobado_lider_at: Optional[datetime] = None
    aprobado_gerencia_at: Optional[datetime] = None
    tiene_poliza: bool = False
    tiene_borrador: bool = False
    requiere_poliza: bool = False


class ContratoResponse(ContratoBase):
    id: int
    tiene_poliza: bool = False
    tiene_borrador: bool = False
    eliminado_at: Optional[datetime] = None
    eliminado_por_id: Optional[int] = None
    eliminado_observacion: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    archivos: list[ArchivoResponse] = Field(default_factory=list)
    otrosies: list[OtrosiResponse] = Field(default_factory=list)


class CambiarEstadoRequest(BaseModel):
    estado: EstadoContrato


class EditarContratoRequest(BaseModel):
    proveedor_contratista: str
    nit_proveedor: str
    descripcion_servicio: str
    obligaciones_colbeef: str
    obligaciones_proveedor: str
    valor: Decimal
    moneda: Moneda
    plazo_cantidad: int
    plazo_unidad: UnidadPlazo
    renovacion_automatica: bool
    condiciones_recibido_satisfactorio: str
    requiere_poliza: bool
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    fecha_proxima_notificacion: Optional[date] = None
    hora_proxima_notificacion: Optional[time] = time(0, 10)


class NotificacionResponse(BaseModel):
    enviado: bool
    cantidad_contratos: int
    destinatarios: list[str]
    mensaje: Optional[str] = None
