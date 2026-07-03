"""Roles disponibles en el sistema.

Mantener este Enum como única fuente de verdad para los roles.
Cualquier capa (BD, API, frontend) debe basarse en estos valores.
"""

from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    JURIDICA = "juridica"
    COMPRAS = "compras"
    SOLICITANTE = "solicitante"
    ANTICIPOS = "anticipos"
    LIDER_APROBADOR = "lider_aprobador"

    @classmethod
    def values(cls) -> list[str]:
        return [r.value for r in cls]
