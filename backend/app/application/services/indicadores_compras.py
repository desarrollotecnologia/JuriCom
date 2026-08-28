"""Indicadores del módulo Compras (solicitudes de gestión).

Función pura sobre una lista de ``SolicitudGestion`` para poder testear sin BD.
Devuelve KPIs del mes + series/distribuciones para alimentar el dashboard.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Optional

from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    aprobada_por_gerencia,
    normalizar_estado,
)
from app.domain.value_objects.tipo_solicitud_gestion import (
    TipoSolicitudGestion,
    es_flujo_salidas_almacen,
    es_flujo_servicios,
)

# "Gestionada" = la operación llegó a un estado realizado (completada).
ESTADOS_REALIZADAS = {
    EstadoSolicitudGestion.CONTRATO_FINALIZADO,
    EstadoSolicitudGestion.ENTREGADO,
    EstadoSolicitudGestion.FACTURADA,
}

MESES_SERIE = 6


@dataclass
class PuntoSerie:
    mes: str  # "AAAA-MM"
    recibidas: int
    gestionadas: int


@dataclass
class IndicadoresCompras:
    mes: str  # "AAAA-MM"
    recibidas_mes: int
    gestionadas_mes: int
    # Promedio de días entre creación y cierre de las gestionadas del mes (None si no hay).
    tiempo_resolucion_dias: Optional[float]
    # Valor total (COP) de las solicitudes de servicios creadas en el mes.
    valor_servicios: Decimal
    serie: list[PuntoSerie] = field(default_factory=list)
    por_estado: dict[str, int] = field(default_factory=dict)
    por_tipo: dict[str, int] = field(default_factory=dict)
    # Rankings (histórico, todas las solicitudes): top 5.
    areas_gasto: list["ItemRanking"] = field(default_factory=list)
    proveedores_frecuentes: list["ItemRanking"] = field(default_factory=list)


@dataclass
class ItemRanking:
    etiqueta: str
    valor: float  # dinero (áreas) o cantidad (proveedores)
    detalles: list[str] = field(default_factory=list)  # ej: códigos de solicitudes


def _fecha_cierre(s: SolicitudGestion) -> Optional[datetime]:
    # ponytail: aproximamos el cierre con factura_registrada_at o updated_at.
    # (No leemos el historial para no cargar relaciones extra; suficiente para el KPI.)
    return s.factura_registrada_at or s.updated_at or s.created_at


def _clave_mes(dt: datetime) -> str:
    return f"{dt.year:04d}-{dt.month:02d}"


def _meses_previos(referencia: datetime, cantidad: int) -> list[str]:
    claves: list[str] = []
    anio, mes = referencia.year, referencia.month
    for _ in range(cantidad):
        claves.append(f"{anio:04d}-{mes:02d}")
        mes -= 1
        if mes == 0:
            mes = 12
            anio -= 1
    return list(reversed(claves))


def _bucket_estado(estado: EstadoSolicitudGestion) -> str:
    if estado in ESTADOS_REALIZADAS:
        return "realizadas"
    if estado == EstadoSolicitudGestion.CANCELADO:
        return "canceladas"
    return "en_gestion"


def _nombres_proveedor(texto: str) -> list[str]:
    """Extrae los nombres de proveedor del campo libre `proveedor_sugerido`.

    Al elegir del catálogo se guarda una línea "NOMBRE — teléfono — correo — …",
    y pueden acumularse varias líneas. Tomamos solo el nombre (antes del primer
    guion largo) de cada línea y deduplicamos dentro de la misma solicitud.
    """
    nombres: list[str] = []
    vistos: set[str] = set()
    for linea in (texto or "").splitlines():
        # El catálogo separa con "—" (em dash); tomamos el primer segmento.
        nombre = linea.split("—")[0].split(" - ")[0].strip()
        clave = nombre.upper()
        if nombre and clave not in vistos:
            vistos.add(clave)
            nombres.append(nombre)
    return nombres


def _clave_tipo(tipo) -> str:
    if es_flujo_servicios(tipo):
        return "servicios"
    if es_flujo_salidas_almacen(tipo):
        return "salidas_almacen"
    return "compra"


def calcular_indicadores_compras(
    solicitudes: Iterable[SolicitudGestion],
    referencia: Optional[datetime] = None,
) -> IndicadoresCompras:
    ref = referencia or datetime.now()
    anio, mes = ref.year, ref.month

    def en_mes(dt: Optional[datetime]) -> bool:
        return dt is not None and dt.year == anio and dt.month == mes

    recibidas = 0
    gestionadas = 0
    duraciones: list[float] = []
    valor_servicios = Decimal("0")

    claves_serie = _meses_previos(ref, MESES_SERIE)
    serie_recibidas = {k: 0 for k in claves_serie}
    serie_gestionadas = {k: 0 for k in claves_serie}
    por_estado = {"en_gestion": 0, "realizadas": 0, "canceladas": 0}
    por_tipo = {"compra": 0, "servicios": 0, "salidas_almacen": 0}
    gasto_por_area: dict[str, list] = {}  # área -> [total, [códigos]]
    conteo_proveedor: dict[str, list] = {}  # clave -> [nombre_display, conteo]

    for s in solicitudes:
        estado = normalizar_estado(s.estado)
        aprobada_gerencia = aprobada_por_gerencia(estado)
        por_estado[_bucket_estado(estado)] += 1
        por_tipo[_clave_tipo(s.tipo)] += 1

        if s.created_at:
            if en_mes(s.created_at):
                recibidas += 1
            clave = _clave_mes(s.created_at)
            if clave in serie_recibidas:
                serie_recibidas[clave] += 1

        realizada = estado in ESTADOS_REALIZADAS
        cierre = _fecha_cierre(s)
        if realizada and cierre:
            clave_cierre = _clave_mes(cierre)
            if clave_cierre in serie_gestionadas:
                serie_gestionadas[clave_cierre] += 1
            if en_mes(cierre):
                gestionadas += 1
                if s.created_at:
                    dias = (cierre - s.created_at).total_seconds() / 86400.0
                    if dias >= 0:
                        duraciones.append(dias)

        if (
            es_flujo_servicios(s.tipo)
            and s.valor_tramite_oc
            and en_mes(s.created_at)
            and aprobada_gerencia
        ):
            valor_servicios += Decimal(s.valor_tramite_oc)

        # Rankings mensuales: solo solicitudes creadas en el mes, ya aprobadas por gerencia.
        if en_mes(s.created_at) and aprobada_gerencia:
            # ponytail: agrupamos el gasto por el centro/área de la solicitud (nivel
            # cabecera), no por producto; suficiente para "área que más gasta".
            area = (s.centro_costo_area or "").strip()
            if area and s.valor_tramite_oc:
                if area not in gasto_por_area:
                    gasto_por_area[area] = [Decimal("0"), []]
                gasto_por_area[area][0] += Decimal(s.valor_tramite_oc)
                if s.codigo:
                    gasto_por_area[area][1].append(s.codigo)

            for proveedor in _nombres_proveedor(s.proveedor_sugerido):
                # ponytail: agrupamos por nombre en mayúsculas para no fragmentar por
                # diferencias de caja; mostramos la primera variante vista.
                clave = proveedor.upper()
                if clave not in conteo_proveedor:
                    conteo_proveedor[clave] = [proveedor, 0]
                conteo_proveedor[clave][1] += 1

    promedio = round(sum(duraciones) / len(duraciones), 1) if duraciones else None
    serie = [
        PuntoSerie(mes=k, recibidas=serie_recibidas[k], gestionadas=serie_gestionadas[k])
        for k in claves_serie
    ]
    areas_gasto = [
        ItemRanking(etiqueta=a, valor=float(total), detalles=list(codigos))
        for a, (total, codigos) in sorted(
            gasto_por_area.items(), key=lambda kv: kv[1][0], reverse=True
        )[:5]
    ]
    proveedores_frecuentes = [
        ItemRanking(etiqueta=nombre, valor=float(conteo))
        for nombre, conteo in sorted(
            conteo_proveedor.values(), key=lambda v: v[1], reverse=True
        )[:5]
    ]

    return IndicadoresCompras(
        mes=f"{anio:04d}-{mes:02d}",
        recibidas_mes=recibidas,
        gestionadas_mes=gestionadas,
        tiempo_resolucion_dias=promedio,
        valor_servicios=valor_servicios,
        serie=serie,
        por_estado=por_estado,
        por_tipo=por_tipo,
        areas_gasto=areas_gasto,
        proveedores_frecuentes=proveedores_frecuentes,
    )
