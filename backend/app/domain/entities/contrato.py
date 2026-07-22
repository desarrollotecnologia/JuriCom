"""Entidad Contrato y archivos adjuntos.

Representa una "Solicitud Radicar" creada por un usuario de Compras.
La empresa siempre es Colbeef (constante de negocio).

Cada contrato tiene un código único legible (ej. C-0001 u OS-0001) que se usa en
correos electrónicos y para búsquedas dentro del sistema.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Optional

from app.domain.entities.otrosi import Otrosi
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
from app.domain.value_objects.estado_contrato import EstadoContrato
from app.domain.value_objects.moneda import Moneda
from app.domain.value_objects.unidad_plazo import UnidadPlazo


COMPANIA_DEFAULT = "Colbeef"
CODIGO_PREFIX = "JC"
TIPO_CODIGO_CONTRATO = "C"
TIPO_CODIGO_ORDEN_TRABAJO = "OS"
TIPOS_CODIGO_VALIDOS = {TIPO_CODIGO_CONTRATO, TIPO_CODIGO_ORDEN_TRABAJO}

# La columna `valor` es DECIMAL(18,2): admite hasta 16 dígitos enteros.
VALOR_MAXIMO = Decimal("9999999999999999.99")
# `plazo_cantidad` es INT con signo en MySQL.
PLAZO_MAXIMO = 2_147_483_647


def normalizar_tipo_codigo(tipo_codigo: str) -> str:
    tipo = (tipo_codigo or TIPO_CODIGO_CONTRATO).strip().upper()
    if tipo not in TIPOS_CODIGO_VALIDOS:
        raise ValueError("El tipo de código debe ser C u OS.")
    return tipo


def construir_codigo(numero_id: int, tipo_codigo: str = TIPO_CODIGO_CONTRATO) -> str:
    """Construye el código legible de un contrato a partir de su id.

    Formato histórico: JC-0001.
    Formato nuevo: C-0001 u OS-0001.
    """
    return f"{normalizar_tipo_codigo(tipo_codigo)}-{numero_id:04d}"


class TipoArchivo(str, Enum):
    # --- subidos por Compras al radicar (3 obligatorios + 1 opcional) ---
    CAMARA_COMERCIO = "camara_comercio"
    COTIZACION = "cotizacion"
    CEDULA_REP_LEGAL = "cedula_rep_legal"
    # Históricos: antes se subían pantallazos; ahora se aprueba por correo.
    CORREO_APROBACION_GERENCIA = "correo_aprobacion_gerencia"
    CORREO_APROBACION_LIDER = "correo_aprobacion_lider"
    OPCIONAL = "opcional"

    # --- subidos por Jurídica posteriormente ---
    POLIZA = "poliza"
    BORRADOR_FIRMADO = "borrador_firmado"
    OTROSI = "otrosi"

    @classmethod
    def obligatorios_radicacion(cls) -> list["TipoArchivo"]:
        """Archivos obligatorios para radicar la solicitud (los sube Compras)."""
        return [
            cls.CAMARA_COMERCIO,
            cls.COTIZACION,
            cls.CEDULA_REP_LEGAL,
        ]

    @classmethod
    def archivos_juridica(cls) -> list["TipoArchivo"]:
        """Archivos que sólo Jurídica/Admin puede subir."""
        return [cls.POLIZA, cls.BORRADOR_FIRMADO]


@dataclass
class ArchivoAdjunto:
    tipo: TipoArchivo
    nombre_original: str
    ruta_almacenamiento: str
    mime_type: str
    tamano_bytes: int
    id: Optional[int] = None
    contrato_id: Optional[int] = None
    subido_por_id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class Contrato:
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
    creado_por_id: int
    correo_lider_proceso: str
    correo_gerencia: str

    compania: str = COMPANIA_DEFAULT
    id: Optional[int] = None
    codigo: Optional[str] = None
    tipo_codigo: str = TIPO_CODIGO_CONTRATO
    solicitud_gestion_id: Optional[int] = None
    solicitud_gestion_codigo: str = ""
    estado_aprobacion: EstadoAprobacion = EstadoAprobacion.PENDIENTE_LIDER
    estado: EstadoContrato = EstadoContrato.EN_PROCESO
    fecha_inicio: Optional[date] = None
    fecha_inicio_original: Optional[date] = None
    fecha_fin: Optional[date] = None
    fecha_proxima_notificacion: Optional[date] = None
    hora_proxima_notificacion: Optional[time] = time(0, 10)
    fecha_ultima_notificacion_vencimiento: Optional[datetime] = None
    aprobado_lider_at: Optional[datetime] = None
    aprobado_gerencia_at: Optional[datetime] = None
    eliminado_at: Optional[datetime] = None
    eliminado_por_id: Optional[int] = None
    eliminado_observacion: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    archivos: list[ArchivoAdjunto] = field(default_factory=list)
    otrosies: list[Otrosi] = field(default_factory=list)

    @property
    def codigo_o_pendiente(self) -> str:
        """Útil cuando el código aún no se ha asignado (p. ej. en pruebas)."""
        return self.codigo or "(sin código)"

    def archivos_obligatorios_presentes(self) -> bool:
        tipos = {a.tipo for a in self.archivos}
        return all(t in tipos for t in TipoArchivo.obligatorios_radicacion())

    def archivos_obligatorios_faltantes(self) -> list[TipoArchivo]:
        tipos = {a.tipo for a in self.archivos}
        return [t for t in TipoArchivo.obligatorios_radicacion() if t not in tipos]

    def tiene_poliza(self) -> bool:
        return any(a.tipo == TipoArchivo.POLIZA for a in self.archivos)

    def tiene_borrador(self) -> bool:
        return any(a.tipo == TipoArchivo.BORRADOR_FIRMADO for a in self.archivos)

    def requiere_poliza_y_no_la_tiene(self) -> bool:
        return self.requiere_poliza and not self.tiene_poliza()

    def cantidad_otrosies(self) -> int:
        return len(self.otrosies)

    def proximo_numero_otrosi(self) -> int:
        if not self.otrosies:
            return 1
        return max((o.numero or 0) for o in self.otrosies) + 1
