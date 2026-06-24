"""Solicitud del módulo Gestión de Solicitudes (compra, traslado, insumos)."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.domain.value_objects.estado_aprobacion_producto import EstadoAprobacionProducto
from app.domain.value_objects.estado_solicitud_gestion import EstadoSolicitudGestion
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion

CODIGO_PREFIX = "SG"


def construir_codigo_solicitud(numero_id: int) -> str:
    return f"{CODIGO_PREFIX}-{numero_id:04d}"


@dataclass
class SolicitudGestionObservacion:
    autor_nombre: str
    autor_rol: str
    contenido: str
    contenido_texto: str = ""
    id: Optional[int] = None
    solicitud_id: Optional[int] = None
    usuario_id: Optional[int] = None
    created_at: Optional[datetime] = None
    archivos: list["SolicitudGestionArchivo"] = field(default_factory=list)

    @property
    def autor_etiqueta(self) -> str:
        return f"{self.autor_nombre} ({self.autor_rol})"


@dataclass
class SolicitudGestionHistorialEstado:
    etapa: EstadoSolicitudGestion
    id: Optional[int] = None
    solicitud_id: Optional[int] = None
    usuario_id: Optional[int] = None
    usuario_username: str = ""
    comentario: str = ""
    created_at: Optional[datetime] = None


@dataclass
class SolicitudGestionProducto:
    codigo_siimed: str
    unidad: str
    descripcion: str
    centro_costo: str
    cantidad: Decimal = field(default_factory=lambda: Decimal("1"))
    cantidad_entregada: Decimal = field(default_factory=lambda: Decimal("0"))
    numero_tramite_oc: str = ""
    id: Optional[int] = None
    solicitud_id: Optional[int] = None
    estado_aprobacion: EstadoAprobacionProducto = EstadoAprobacionProducto.PENDIENTE

    @property
    def cantidad_pendiente(self) -> Decimal:
        pendiente = self.cantidad - self.cantidad_entregada
        return pendiente if pendiente > 0 else Decimal("0")

    @property
    def estado_entrega(self) -> str:
        if self.cantidad_entregada <= 0:
            return "pendiente"
        if self.cantidad_entregada >= self.cantidad:
            return "entregado"
        return "parcial"


@dataclass
class SolicitudGestionArchivo:
    nombre_original: str
    ruta_almacenamiento: str
    mime_type: str
    tamano_bytes: int
    categoria: str = "solicitud"
    id: Optional[int] = None
    solicitud_id: Optional[int] = None
    observacion_id: Optional[int] = None
    subido_por_id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class SolicitudGestion:
    tipo: TipoSolicitudGestion
    titulo: str
    creado_por_id: int
    creado_por_username: str = ""
    creado_por_email: str = ""
    centro_costo_area: str = ""
    lider_area_id: str = ""
    lider_area_label: str = ""
    presupuestado: Optional[bool] = None
    observaciones: str = ""
    observaciones_texto: str = ""
    observaciones_gestion: str = ""
    justificacion_cotizaciones: str = ""
    numero_tramite_oc: str = ""
    gestor_id: Optional[int] = None
    gestor_username: str = ""
    lider_segunda_aprobacion_id: str = ""
    lider_segunda_aprobacion_label: str = ""
    id: Optional[int] = None
    codigo: Optional[str] = None
    estado: EstadoSolicitudGestion = EstadoSolicitudGestion.SOLICITUD
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    productos: list[SolicitudGestionProducto] = field(default_factory=list)
    archivos: list[SolicitudGestionArchivo] = field(default_factory=list)
    observaciones_trazabilidad: list[SolicitudGestionObservacion] = field(default_factory=list)

    @property
    def cantidad_productos(self) -> int:
        return len(self.productos)

    @property
    def cantidad_productos_aprobados(self) -> int:
        return sum(
            1
            for p in self.productos
            if p.estado_aprobacion == EstadoAprobacionProducto.APROBADO
        )

    @property
    def aprobacion_parcial(self) -> bool:
        return any(
            p.estado_aprobacion == EstadoAprobacionProducto.NO_APROBADO for p in self.productos
        )

    @property
    def tiene_tramite_oc_registrado(self) -> bool:
        if (self.numero_tramite_oc or "").strip():
            return True
        return any((p.numero_tramite_oc or "").strip() for p in self.productos)

    @property
    def productos_para_entrega(self) -> list[SolicitudGestionProducto]:
        return [
            p
            for p in self.productos
            if p.estado_aprobacion != EstadoAprobacionProducto.NO_APROBADO
        ]

    @property
    def entrega_completa(self) -> bool:
        productos = self.productos_para_entrega
        if not productos:
            return False
        return all(p.cantidad_entregada >= p.cantidad for p in productos)

    @property
    def tiene_entrega_pendiente(self) -> bool:
        return any(p.cantidad_pendiente > 0 for p in self.productos_para_entrega)
