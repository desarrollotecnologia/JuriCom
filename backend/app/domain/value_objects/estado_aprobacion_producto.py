"""Estado de aprobación por ítem en la primera aprobación."""

from enum import Enum


class EstadoAprobacionProducto(str, Enum):
    PENDIENTE = "pendiente"
    APROBADO = "aprobado"
    NO_APROBADO = "no_aprobado"


LABELS: dict[EstadoAprobacionProducto, str] = {
    EstadoAprobacionProducto.PENDIENTE: "Pendiente",
    EstadoAprobacionProducto.APROBADO: "Aprobado",
    EstadoAprobacionProducto.NO_APROBADO: "No aprobado",
}


def normalizar_estado_aprobacion_producto(
    valor: str | EstadoAprobacionProducto | None,
) -> EstadoAprobacionProducto:
    if isinstance(valor, EstadoAprobacionProducto):
        return valor
    if not valor:
        return EstadoAprobacionProducto.PENDIENTE
    try:
        return EstadoAprobacionProducto(valor)
    except ValueError:
        return EstadoAprobacionProducto.PENDIENTE
