"""Monedas aceptadas en contratos.

COP = Pesos colombianos (moneda local por defecto).
"""

from enum import Enum


class Moneda(str, Enum):
    COP = "COP"
    USD = "USD"
    EUR = "EUR"

    @classmethod
    def values(cls) -> list[str]:
        return [m.value for m in cls]
