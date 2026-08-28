"""Tipos de otrosí aplicables a un contrato.

Un "otrosí" es un documento legal que modifica o añade condiciones a un
contrato existente sin crear uno nuevo. Hoy sólo se ofrecen dos efectos, que
pueden ir por separado o combinados en un mismo otrosí:
- PRORROGA          → extender el plazo
- ADICION           → aumentar el valor / presupuesto
- PRORROGA_ADICION  → ambos a la vez (más tiempo y más valor)

MODIFICACION y OTRO quedan sólo por compatibilidad con otrosíes históricos;
ya no se ofrecen al crear uno nuevo.
"""

from enum import Enum


class TipoOtrosi(str, Enum):
    PRORROGA = "prorroga"
    ADICION = "adicion"
    PRORROGA_ADICION = "prorroga_adicion"
    MODIFICACION = "modificacion"  # histórico
    OTRO = "otro"  # histórico

    @classmethod
    def values(cls) -> list[str]:
        return [t.value for t in cls]

    @property
    def label(self) -> str:
        return {
            TipoOtrosi.PRORROGA: "Prórroga",
            TipoOtrosi.ADICION: "Adición",
            TipoOtrosi.PRORROGA_ADICION: "Prórroga + Adición",
            TipoOtrosi.MODIFICACION: "Modificación",
            TipoOtrosi.OTRO: "Otro",
        }[self]

    @property
    def incluye_prorroga(self) -> bool:
        return self in (TipoOtrosi.PRORROGA, TipoOtrosi.PRORROGA_ADICION)

    @property
    def incluye_adicion(self) -> bool:
        return self in (TipoOtrosi.ADICION, TipoOtrosi.PRORROGA_ADICION)
