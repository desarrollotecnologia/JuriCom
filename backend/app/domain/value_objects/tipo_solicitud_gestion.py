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
            TipoSolicitudGestion.INSUMOS_SERVICIOS: "Solicitud de Insumos/Servicios",
        }[self]


def es_flujo_salidas_almacen(tipo: TipoSolicitudGestion | str) -> bool:
    if isinstance(tipo, TipoSolicitudGestion):
        return tipo == TipoSolicitudGestion.SALIDAS_ALMACEN
    return (str(tipo or "")).strip() == TipoSolicitudGestion.SALIDAS_ALMACEN.value
