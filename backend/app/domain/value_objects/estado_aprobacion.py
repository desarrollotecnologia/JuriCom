"""Estados del flujo de aprobación previo a Jurídica."""

from enum import Enum


class EstadoAprobacion(str, Enum):
    PENDIENTE_LIDER = "pendiente_lider"
    PENDIENTE_GERENCIA = "pendiente_gerencia"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"

    @property
    def label(self) -> str:
        return {
            EstadoAprobacion.PENDIENTE_LIDER: "Pendiente líder de proceso",
            EstadoAprobacion.PENDIENTE_GERENCIA: "Pendiente gerencia",
            EstadoAprobacion.APROBADO: "Aprobado",
            EstadoAprobacion.RECHAZADO: "Rechazado",
        }[self]
