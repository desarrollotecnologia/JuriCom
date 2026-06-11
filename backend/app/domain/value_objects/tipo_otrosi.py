"""Tipos de otrosí aplicables a un contrato.

Un "otrosí" es un documento legal que modifica o añade condiciones a un
contrato existente sin crear uno nuevo. Sirve para:
- PRORROGA      → extender el plazo
- ADICION       → aumentar el valor / presupuesto
- MODIFICACION  → cambiar las actividades / descripción del servicio
- OTRO          → cualquier otra modificación (sólo deja constancia)
"""

from enum import Enum


class TipoOtrosi(str, Enum):
    PRORROGA = "prorroga"
    ADICION = "adicion"
    MODIFICACION = "modificacion"
    OTRO = "otro"

    @classmethod
    def values(cls) -> list[str]:
        return [t.value for t in cls]

    @property
    def label(self) -> str:
        return {
            TipoOtrosi.PRORROGA: "Prórroga",
            TipoOtrosi.ADICION: "Adición",
            TipoOtrosi.MODIFICACION: "Modificación",
            TipoOtrosi.OTRO: "Otro",
        }[self]
