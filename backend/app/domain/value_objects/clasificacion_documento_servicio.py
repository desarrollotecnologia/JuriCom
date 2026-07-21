"""Clasificación documental de una solicitud de servicios según su valor."""

from decimal import Decimal
from enum import Enum


UMBRAL_ORDEN_SERVICIO = Decimal("5000000")
UMBRAL_CONTRATO = Decimal("10000000")


class ClasificacionDocumentoServicio(str, Enum):
    ORDEN_SERVICIO = "orden_servicio"
    ORDEN_TRABAJO = "orden_trabajo"
    CONTRATO = "contrato"


LABELS: dict[ClasificacionDocumentoServicio, str] = {
    ClasificacionDocumentoServicio.ORDEN_SERVICIO: "Orden de Servicio",
    ClasificacionDocumentoServicio.ORDEN_TRABAJO: "Orden de Trabajo",
    ClasificacionDocumentoServicio.CONTRATO: "Contrato",
}


def clasificar_documento_servicio(valor: Decimal) -> ClasificacionDocumentoServicio:
    if valor < UMBRAL_ORDEN_SERVICIO:
        return ClasificacionDocumentoServicio.ORDEN_SERVICIO
    if valor <= UMBRAL_CONTRATO:
        return ClasificacionDocumentoServicio.ORDEN_TRABAJO
    return ClasificacionDocumentoServicio.CONTRATO


def label_clasificacion_documento_servicio(valor: str | ClasificacionDocumentoServicio | None) -> str:
    if not valor:
        return ""
    try:
        key = ClasificacionDocumentoServicio(str(valor))
    except ValueError:
        return str(valor)
    return LABELS.get(key, str(valor))
