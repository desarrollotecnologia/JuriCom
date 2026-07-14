"""Estados de un contrato.

Flujo típico:
    EN_PROCESO  → ACTIVO       (cuando ya se firmó / quedó completo)
    ACTIVO      → FINALIZADO   (cuando se vence o no se renueva)

El estado inicial al radicar es EN_PROCESO (porque le faltan documentos
de jurídica: póliza si aplica, contrato firmado, etc.).

Sólo Jurídica y Admin pueden cambiar el estado.
"""

from enum import Enum


class EstadoContrato(str, Enum):
    EN_PROCESO = "en_proceso"
    ACTIVO = "activo"
    FINALIZADO = "finalizado"

    @classmethod
    def values(cls) -> list[str]:
        return [e.value for e in cls]

    @property
    def label(self) -> str:
        return {
            EstadoContrato.EN_PROCESO: "En proceso",
            EstadoContrato.ACTIVO: "Activo",
            EstadoContrato.FINALIZADO: "Finalizado",
        }[self]
