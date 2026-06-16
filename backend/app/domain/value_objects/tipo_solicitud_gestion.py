"""Tipos de solicitud del módulo Gestión de Solicitudes."""

from enum import Enum


class TipoSolicitudGestion(str, Enum):
    COMPRA = "compra"
    TRASLADO_BODEGAS = "traslado_bodegas"
    INSUMOS_SERVICIOS = "insumos_servicios"

    @property
    def label(self) -> str:
        return {
            TipoSolicitudGestion.COMPRA: "Solicitud de Compra",
            TipoSolicitudGestion.TRASLADO_BODEGAS: "Traslado entre Bodegas",
            TipoSolicitudGestion.INSUMOS_SERVICIOS: "Solicitud de Insumos/Servicios",
        }[self]
