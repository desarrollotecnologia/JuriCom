"""Regla de aprobación gerencial según el valor del contrato.

≤ umbral (COP): Diego Serrano (Director Administrativo y Financiero).
> umbral (COP): Gerencia General.
Otras monedas: Gerencia General (sin tasa de cambio parametrizada).
"""

from decimal import Decimal

from app.domain.value_objects.moneda import Moneda
from app.infrastructure.config import settings


def correo_aprobacion_gerencia(valor: Decimal, moneda: Moneda) -> tuple[str, str]:
    """Devuelve (correo, etiqueta) del aprobador gerencial según el valor."""
    umbral = settings.aprobacion_umbral_cop
    diego = settings.APROBACION_DIEGO_SERRANO_EMAIL.strip()
    gerencia = (
        settings.APROBACION_GERENCIA_GENERAL_EMAIL.strip()
        or settings.GERENCIA_EMAIL.strip()
    )

    if moneda == Moneda.COP and Decimal(valor) <= umbral:
        return diego, "Diego Serrano (Director Administrativo y Financiero)"
    return gerencia, "Gerencia General"
