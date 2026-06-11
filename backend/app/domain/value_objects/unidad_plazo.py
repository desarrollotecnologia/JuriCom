"""Unidades de tiempo aceptadas para el plazo del contrato.

Se separa "cantidad" + "unidad" para poder calcular fechas de
vencimiento y notificaciones con precisión.
"""

from enum import Enum


class UnidadPlazo(str, Enum):
    DIAS = "dias"
    MESES = "meses"
    ANIOS = "anios"

    @classmethod
    def values(cls) -> list[str]:
        return [u.value for u in cls]
