"""Tipos de solicitud del módulo Gestión de Solicitudes."""

from enum import Enum


class TipoSolicitudGestion(str, Enum):
    COMPRA = "compra"
    SALIDAS_ALMACEN = "salidas_almacen"
    INSUMOS_SERVICIOS = "insumos_servicios"
    SALIDA_CONSUMIBLES = "salida_consumibles"

    @property
    def label(self) -> str:
        return {
            TipoSolicitudGestion.COMPRA: "Solicitud de Compra",
            TipoSolicitudGestion.SALIDAS_ALMACEN: "Salidas de Almacén",
            TipoSolicitudGestion.INSUMOS_SERVICIOS: "Solicitud de Servicios",
            TipoSolicitudGestion.SALIDA_CONSUMIBLES: "Salida de Consumibles",
        }[self]

    @property
    def codigo_prefix(self) -> str:
        return {
            TipoSolicitudGestion.COMPRA: "SG",
            TipoSolicitudGestion.SALIDAS_ALMACEN: "SA",
            TipoSolicitudGestion.INSUMOS_SERVICIOS: "SRV",
            TipoSolicitudGestion.SALIDA_CONSUMIBLES: "SC",
        }[self]


def es_flujo_salidas_almacen(tipo: TipoSolicitudGestion | str) -> bool:
    if isinstance(tipo, TipoSolicitudGestion):
        return tipo == TipoSolicitudGestion.SALIDAS_ALMACEN
    return (str(tipo or "")).strip() == TipoSolicitudGestion.SALIDAS_ALMACEN.value


def es_flujo_servicios(tipo: TipoSolicitudGestion | str) -> bool:
    if isinstance(tipo, TipoSolicitudGestion):
        return tipo == TipoSolicitudGestion.INSUMOS_SERVICIOS
    return (str(tipo or "")).strip() == TipoSolicitudGestion.INSUMOS_SERVICIOS.value


def es_flujo_salida_consumibles(tipo: TipoSolicitudGestion | str) -> bool:
    if isinstance(tipo, TipoSolicitudGestion):
        return tipo == TipoSolicitudGestion.SALIDA_CONSUMIBLES
    return (str(tipo or "")).strip() == TipoSolicitudGestion.SALIDA_CONSUMIBLES.value


def es_entrega_directa(tipo: TipoSolicitudGestion | str) -> bool:
    """Tipos que Compras entrega directamente: sin OC, sin recepción física previa.

    Aplica a salidas de almacén y a salida de consumibles (esta última, además,
    salta la aprobación del líder y nace lista para entrega).
    """
    return es_flujo_salidas_almacen(tipo) or es_flujo_salida_consumibles(tipo)
