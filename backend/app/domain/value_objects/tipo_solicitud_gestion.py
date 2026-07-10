"""Tipos de solicitud del módulo Gestión de Solicitudes."""

from enum import Enum


class TipoSolicitudGestion(str, Enum):
    COMPRA = "compra"
    SALIDAS_ALMACEN = "salidas_almacen"
    INSUMOS_SERVICIOS = "insumos_servicios"

    @property
    def label(self) -> str:
        return {
            TipoSolicitudGestion.COMPRA: "Solicitud de Compra",
            TipoSolicitudGestion.SALIDAS_ALMACEN: "Salidas de Almacén",
            TipoSolicitudGestion.INSUMOS_SERVICIOS: "Solicitud de Servicios",
        }[self]

    @property
    def codigo_prefix(self) -> str:
        return {
            TipoSolicitudGestion.COMPRA: "SG",
            TipoSolicitudGestion.SALIDAS_ALMACEN: "SA",
            TipoSolicitudGestion.INSUMOS_SERVICIOS: "SRV",
        }[self]


def es_flujo_salidas_almacen(tipo: TipoSolicitudGestion | str) -> bool:
    if isinstance(tipo, TipoSolicitudGestion):
        return tipo == TipoSolicitudGestion.SALIDAS_ALMACEN
    return (str(tipo or "")).strip() == TipoSolicitudGestion.SALIDAS_ALMACEN.value


def es_flujo_servicios(tipo: TipoSolicitudGestion | str) -> bool:
    if isinstance(tipo, TipoSolicitudGestion):
        return tipo == TipoSolicitudGestion.INSUMOS_SERVICIOS
    return (str(tipo or "")).strip() == TipoSolicitudGestion.INSUMOS_SERVICIOS.value
