"""Calendario de festivos Colombia y días hábiles."""

from datetime import date

from app.domain.entities.contrato import sumar_dias_habiles
from app.domain.value_objects.calendario_colombia import (
    es_dia_habil,
    festivos_colombia,
)


def test_festivos_2026_conocidos():
    f = festivos_colombia(2026)
    assert date(2026, 1, 1) in f
    assert date(2026, 1, 12) in f
    assert date(2026, 4, 2) in f
    assert date(2026, 4, 3) in f
    assert date(2026, 5, 1) in f
    assert date(2026, 7, 20) in f
    assert date(2026, 12, 25) in f
    assert not es_dia_habil(date(2026, 12, 25))
    assert es_dia_habil(date(2026, 12, 24))


def test_sumar_habiles_salta_navidad():
    assert sumar_dias_habiles(date(2026, 12, 24), 1) == date(2026, 12, 28)
