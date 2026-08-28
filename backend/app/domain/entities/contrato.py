"""Entidad Contrato y archivos adjuntos.

Representa una "Solicitud Radicar" creada por un usuario de Compras.
La empresa siempre es Colbeef (constante de negocio).

Cada contrato tiene un código único legible (ej. C-0001 u OS-0001) que se usa en
correos electrónicos y para búsquedas dentro del sistema.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional

from app.domain.entities.otrosi import Otrosi
from app.domain.value_objects.calendario_colombia import es_dia_habil
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
from app.domain.value_objects.estado_contrato import EstadoContrato
from app.domain.value_objects.moneda import Moneda
from app.domain.value_objects.tipo_precio import TipoPrecio
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

# Días hábiles que tiene Jurídica para elaborar el contrato tras la aprobación
# de gerencia. Es solo el valor por defecto: Jurídica puede fijar otra fecha.
DIAS_ELABORACION_DEFAULT = 2

# Hora por defecto de las notificaciones (antes 00:10).
HORA_NOTIFICACION_DEFAULT = time(7, 30)


def sumar_dias_habiles(inicio: date, dias: int) -> date:
    """Suma `dias` días hábiles (lun-vie, sin festivos Colombia) desde el día
    siguiente a `inicio`.
    """
    d = inicio
    restantes = dias
    while restantes > 0:
        d += timedelta(days=1)
        if es_dia_habil(d):
            restantes -= 1
    return d


def contar_dias_habiles(desde: date, hasta: date) -> int:
    """Días hábiles (lun-vie, sin festivos) entre `desde` y `hasta`, sin contar `desde`.

    Positivo si `hasta` es futuro, negativo si ya pasó, 0 si es el mismo día.
    """
    if hasta == desde:
        return 0
    paso = 1 if hasta > desde else -1
    d = desde
    total = 0
    while d != hasta:
        d += timedelta(days=paso)
        if es_dia_habil(d):
            total += paso
    return total


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

    # --- subidos por Compras al finalizar el contrato ---
    INFORME_FINAL = "informe_final"
    ACTA_LIQUIDACION = "acta_liquidacion"

    # --- adjuntos del hilo Jurídica ↔ supervisor ---
    SOLICITUD_INFORMACION = "solicitud_informacion"
    RESPUESTA_INFORMACION = "respuesta_informacion"

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

    @classmethod
    def archivos_finalizacion(cls) -> list["TipoArchivo"]:
        """Archivos que Compras adjunta al finalizar el contrato."""
        return [cls.INFORME_FINAL, cls.ACTA_LIQUIDACION]


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
    solicitud_informacion_id: Optional[int] = None
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
    tipo_precio: TipoPrecio = TipoPrecio.MAS_IVA
    forma_pago: str = ""
    centro_costos: str = ""
    proveedor_email: str = ""
    supervisor_id: Optional[int] = None
    supervisor_username: str = ""
    # Snapshot del anticipo copiado de la SRV al radicar (fijo en el contrato).
    requiere_anticipo: bool = False
    porcentaje_anticipo: Optional[Decimal] = None
    monto_anticipo: Optional[Decimal] = None
    observaciones_anticipo: str = ""
    # True cuando Tesorería confirmó el pago del anticipo (habilita activar el contrato).
    anticipo_pagado: bool = False

    compania: str = COMPANIA_DEFAULT
    id: Optional[int] = None
    codigo: Optional[str] = None
    tipo_codigo: str = TIPO_CODIGO_CONTRATO
    solicitud_gestion_id: Optional[int] = None
    solicitud_gestion_codigo: str = ""
    creado_por_username: str = ""
    estado_aprobacion: EstadoAprobacion = EstadoAprobacion.PENDIENTE_LIDER
    estado: EstadoContrato = EstadoContrato.EN_PROCESO
    fecha_inicio: Optional[date] = None
    fecha_inicio_original: Optional[date] = None
    fecha_fin: Optional[date] = None
    fecha_limite_elaboracion: Optional[date] = None
    fecha_proxima_notificacion: Optional[date] = None
    hora_proxima_notificacion: Optional[time] = HORA_NOTIFICACION_DEFAULT
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

    def tiene_informe_final(self) -> bool:
        return any(a.tipo == TipoArchivo.INFORME_FINAL for a in self.archivos)

    def tiene_acta_liquidacion(self) -> bool:
        return any(a.tipo == TipoArchivo.ACTA_LIQUIDACION for a in self.archivos)

    def requiere_acta_liquidacion(self, umbral: Decimal) -> bool:
        """El acta (elaborada por Jurídica) solo aplica a contratos > umbral."""
        return self.valor is not None and Decimal(self.valor) > Decimal(umbral)

    def esperando_acta_liquidacion(self, umbral: Decimal) -> bool:
        """Contrato activo, con informe final entregado, esperando el acta de Jurídica."""
        return (
            self.estado == EstadoContrato.ACTIVO
            and self.requiere_acta_liquidacion(umbral)
            and self.tiene_informe_final()
            and not self.tiene_acta_liquidacion()
        )

    def requiere_poliza_y_no_la_tiene(self) -> bool:
        return self.requiere_poliza and not self.tiene_poliza()

    def cantidad_otrosies(self) -> int:
        return len(self.otrosies)

    def proximo_numero_otrosi(self) -> int:
        if not self.otrosies:
            return 1
        return max((o.numero or 0) for o in self.otrosies) + 1

    def en_elaboracion(self) -> bool:
        """Aprobado por gerencia y en estado 'Elaborando contrato': Jurídica lo elabora."""
        return (
            self.estado == EstadoContrato.ELABORANDO
            and self.estado_aprobacion == EstadoAprobacion.APROBADO
        )

    def fecha_limite_elaboracion_efectiva(self) -> Optional[date]:
        """Fecha tope para elaborar: la fijada por Jurídica o la calculada
        (aprobación de gerencia + N días hábiles)."""
        if self.fecha_limite_elaboracion:
            return self.fecha_limite_elaboracion
        if self.aprobado_gerencia_at:
            return sumar_dias_habiles(
                self.aprobado_gerencia_at.date(), DIAS_ELABORACION_DEFAULT
            )
        return None

    def dias_para_elaborar(self) -> Optional[int]:
        """Días hábiles que faltan para la fecha límite de elaboración.
        Negativo si ya está vencida. None si el contrato no está en elaboración."""
        if not self.en_elaboracion():
            return None
        limite = self.fecha_limite_elaboracion_efectiva()
        if not limite:
            return None
        return contar_dias_habiles(date.today(), limite)
