"""Solicitud del módulo Gestión de Solicitudes (compra, salidas de almacén, insumos)."""

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
    area_consumo: str = ""
    cantidad: Decimal = field(default_factory=lambda: Decimal("1"))
    cantidad_recibida: Decimal = field(default_factory=lambda: Decimal("0"))
    cantidad_entregada: Decimal = field(default_factory=lambda: Decimal("0"))
    numero_tramite_oc: str = ""
    valor_tramite_oc: Optional[Decimal] = None
    id: Optional[int] = None
    solicitud_id: Optional[int] = None
    estado_aprobacion: EstadoAprobacionProducto = EstadoAprobacionProducto.PENDIENTE

    @property
    def cantidad_pendiente(self) -> Decimal:
        pendiente = self.cantidad - self.cantidad_entregada
        return pendiente if pendiente > 0 else Decimal("0")

    @property
    def cantidad_pendiente_recepcion(self) -> Decimal:
        pendiente = self.cantidad - self.cantidad_recibida
        return pendiente if pendiente > 0 else Decimal("0")

    @property
    def cantidad_disponible_entrega(self) -> Decimal:
        disponible = self.cantidad_recibida - self.cantidad_entregada
        return disponible if disponible > 0 else Decimal("0")

    @property
    def estado_recepcion(self) -> str:
        if self.cantidad_recibida <= 0:
            return "pendiente"
        if self.cantidad_recibida >= self.cantidad:
            return "recibido"
        return "parcial"

    @property
    def estado_entrega(self) -> str:
        if self.cantidad_entregada <= 0:
            return "pendiente"
        if self.cantidad_entregada >= self.cantidad:
            return "entregado"
        return "parcial"

    @staticmethod
    def _formatear_cantidad(cantidad: Decimal) -> str:
        if cantidad == cantidad.to_integral_value():
            return str(int(cantidad))
        texto = format(cantidad.normalize(), "f")
        return texto.rstrip("0").rstrip(".") or "0"

    @property
    def unidad_etiqueta(self) -> str:
        return (self.unidad or "").strip() or "UND"

    def etiqueta_cantidad(self, cantidad: Decimal) -> str:
        return f"{self._formatear_cantidad(cantidad)} {self.unidad_etiqueta}"

    def linea_historial_recepcion(
        self, cantidad_delta: Decimal, total_recibido: Decimal
    ) -> str:
        return (
            f"{self.descripcion}: +{self._formatear_cantidad(cantidad_delta)} "
            f"(recibido {self.etiqueta_cantidad(total_recibido)} "
            f"de {self.etiqueta_cantidad(self.cantidad)})"
        )

    def linea_historial_entrega(
        self, cantidad_delta: Decimal, total_entregado: Decimal
    ) -> str:
        return (
            f"{self.descripcion}: +{self._formatear_cantidad(cantidad_delta)} "
            f"(entregado {self.etiqueta_cantidad(total_entregado)} "
            f"de {self.etiqueta_cantidad(self.cantidad)})"
        )


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
    valor_tramite_oc: Optional[Decimal] = None
    gestor_id: Optional[int] = None
    gestor_username: str = ""
    lider_segunda_aprobacion_id: str = ""
    lider_segunda_aprobacion_label: str = ""
    requiere_anticipo: bool = False
    porcentaje_anticipo: Optional[Decimal] = None
    lider_anticipo_id: str = ""
    lider_anticipo_label: str = ""
    monto_anticipo: Optional[Decimal] = None
    observaciones_anticipo: str = ""
    gestor_anticipo_id: Optional[int] = None
    gestor_anticipo_username: str = ""
    factura_registrada_at: Optional[datetime] = None
    factura_registrada_por_id: Optional[int] = None
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
        if self.es_salidas_almacen:
            return True
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
    def tiene_recepcion_pendiente(self) -> bool:
        return any(p.cantidad_pendiente_recepcion > 0 for p in self.productos_para_entrega)

    @property
    def recepcion_completa(self) -> bool:
        productos = self.productos_para_entrega
        if not productos:
            return False
        return all(p.cantidad_recibida >= p.cantidad for p in productos)

    @property
    def observaciones_factura(self) -> list["SolicitudGestionObservacion"]:
        items = []
        for observacion in self.observaciones_trazabilidad or []:
            archivos = observacion.archivos or []
            if any((a.categoria or "") == "factura" for a in archivos):
                items.append(observacion)
                continue
            texto = f"{observacion.contenido_texto or ''} {observacion.contenido or ''}".lower()
            if "factura registrada" in texto and archivos:
                items.append(observacion)
        return sorted(items, key=lambda o: o.created_at or datetime.min)

    @property
    def cantidad_facturas(self) -> int:
        return len(self.observaciones_factura)

    @property
    def factura_registrada(self) -> bool:
        from app.domain.value_objects.estado_solicitud_gestion import (
            EstadoSolicitudGestion,
            normalizar_estado,
        )

        return (
            self.factura_registrada_at is not None
            or normalizar_estado(self.estado) == EstadoSolicitudGestion.FACTURADA
        )

    @property
    def tiene_entrega_pendiente(self) -> bool:
        return any(p.cantidad_entregada < p.cantidad for p in self.productos_para_entrega)

    def actor_puede_gestionar(self, actor_id: int, *, is_admin: bool = False) -> bool:
        """True si el usuario puede operar la solicitud en panel o entrega."""
        if is_admin:
            return True
        if not self.gestor_id and not self.gestor_anticipo_id:
            return True
        return actor_id in (self.gestor_id, self.gestor_anticipo_id)

    @property
    def es_salidas_almacen(self) -> bool:
        from app.domain.value_objects.tipo_solicitud_gestion import es_flujo_salidas_almacen

        return es_flujo_salidas_almacen(self.tipo)
