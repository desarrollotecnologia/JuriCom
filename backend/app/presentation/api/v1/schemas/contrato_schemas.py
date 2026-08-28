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
from app.domain.value_objects.tipo_precio import TipoPrecio
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
    proveedor_email: str = ""
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
    tipo_precio: TipoPrecio = TipoPrecio.MAS_IVA
    forma_pago: str = ""
    centro_costos: str = ""
    supervisor_id: Optional[int] = None
    supervisor_username: str = ""
    requiere_anticipo: bool = False
    porcentaje_anticipo: Optional[Decimal] = None
    monto_anticipo: Optional[Decimal] = None
    observaciones_anticipo: str = ""
    anticipo_pagado: bool = False
    correo_lider_proceso: str
    correo_gerencia: str
    estado_aprobacion: EstadoAprobacion
    fecha_inicio: Optional[date] = None
    fecha_inicio_original: Optional[date] = None
    fecha_fin: Optional[date] = None
    fecha_limite_elaboracion: Optional[date] = None
    dias_para_elaborar: Optional[int] = None
    alerta_elaboracion: bool = False
    fecha_proxima_notificacion: Optional[date] = None
    hora_proxima_notificacion: Optional[time] = time(7, 30)
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
    creado_por_username: str = ""
    proveedor_contratista: str
    nit_proveedor: str
    proveedor_email: str = ""
    descripcion_servicio: str
    valor: Decimal
    moneda: Moneda
    plazo_cantidad: int
    plazo_unidad: UnidadPlazo
    renovacion_automatica: bool
    requiere_poliza: bool
    tipo_precio: TipoPrecio = TipoPrecio.MAS_IVA
    forma_pago: str = ""
    centro_costos: str = ""
    supervisor_id: Optional[int] = None
    supervisor_username: str = ""
    requiere_anticipo: bool = False
    anticipo_pagado: bool = False
    tiene_poliza: bool
    tiene_borrador: bool
    requiere_acta_liquidacion: bool = False
    tiene_informe_final: bool = False
    tiene_acta_liquidacion: bool = False
    pendiente_acta_liquidacion: bool = False
    cantidad_otrosies: int = 0
    estado_aprobacion: EstadoAprobacion
    estado: EstadoContrato
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    fecha_limite_elaboracion: Optional[date] = None
    dias_para_elaborar: Optional[int] = None
    alerta_elaboracion: bool = False
    fecha_proxima_notificacion: Optional[date] = None
    hora_proxima_notificacion: Optional[time] = time(7, 30)
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
    requiere_acta_liquidacion: bool = False
    tiene_informe_final: bool = False
    tiene_acta_liquidacion: bool = False
    pendiente_acta_liquidacion: bool = False
    eliminado_at: Optional[datetime] = None
    eliminado_por_id: Optional[int] = None
    eliminado_observacion: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    archivos: list[ArchivoResponse] = Field(default_factory=list)
    otrosies: list[OtrosiResponse] = Field(default_factory=list)


class CambiarEstadoRequest(BaseModel):
    estado: EstadoContrato
    observacion: str = ""


class EditarContratoRequest(BaseModel):
    proveedor_contratista: str
    nit_proveedor: str
    proveedor_email: str = ""
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
    tipo_precio: TipoPrecio = TipoPrecio.MAS_IVA
    forma_pago: str = ""
    centro_costos: str = ""
    supervisor_id: Optional[int] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    fecha_limite_elaboracion: Optional[date] = None
    fecha_proxima_notificacion: Optional[date] = None
    hora_proxima_notificacion: Optional[time] = time(7, 30)


class NotificacionResponse(BaseModel):
    enviado: bool
    cantidad_contratos: int
    destinatarios: list[str]
    mensaje: Optional[str] = None


class SolicitarInformacionRequest(BaseModel):
    mensaje: str = Field(..., min_length=1, description="Qué información falta.")


class SolicitudInformacionResponse(BaseModel):
    id: int
    contrato_id: int
    contrato_codigo: Optional[str] = None
    proveedor_contratista: Optional[str] = None
    solicitado_por_id: int
    solicitado_por_username: str = ""
    mensaje: str
    fecha_limite_respuesta: Optional[date] = None
    dias_para_responder: Optional[int] = None
    vencida: bool = False
    estado: str
    respuesta: str = ""
    respondido_por_id: Optional[int] = None
    respondido_por_username: str = ""
    respondido_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    archivos: list[ArchivoResponse] = Field(default_factory=list)
