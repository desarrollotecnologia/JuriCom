"""Tipo de precio del contrato (formas de pago)."""

from enum import Enum


class TipoPrecio(str, Enum):
    MAS_IVA = "mas_iva"
    AUI = "aui"
    NO_APLICA = "no_aplica"

    @property
    def label(self) -> str:
        return {
            TipoPrecio.MAS_IVA: "Más IVA",
            TipoPrecio.AUI: "AUI",
            TipoPrecio.NO_APLICA: "No aplica",
        }[self]

    @classmethod
    def values(cls) -> list[str]:
        return [item.value for item in cls]
