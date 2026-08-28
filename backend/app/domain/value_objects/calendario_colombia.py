"""Días hábiles Colombia: lun-vie, sin festivos (Ley Emiliani)."""

from datetime import date, timedelta
from functools import lru_cache


def _pascua(anio: int) -> date:
    a = anio % 19
    b, c = divmod(anio, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes, dia = divmod(h + l - 7 * m + 114, 31)
    return date(anio, mes, dia + 1)


def _siguiente_lunes(d: date) -> date:
    if d.weekday() == 0:
        return d
    return d + timedelta(days=(7 - d.weekday()))


@lru_cache(maxsize=32)
def festivos_colombia(anio: int) -> frozenset[date]:
    pascua = _pascua(anio)
    fijos = (
        date(anio, 1, 1),
        date(anio, 5, 1),
        date(anio, 7, 20),
        date(anio, 8, 7),
        date(anio, 12, 8),
        date(anio, 12, 25),
        pascua - timedelta(days=3),
        pascua - timedelta(days=2),
    )
    trasladables = (
        date(anio, 1, 6),
        date(anio, 3, 19),
        date(anio, 6, 29),
        date(anio, 8, 15),
        date(anio, 10, 12),
        date(anio, 11, 1),
        date(anio, 11, 11),
        pascua + timedelta(days=39),
        pascua + timedelta(days=60),
        pascua + timedelta(days=68),
    )
    return frozenset((*fijos, *(_siguiente_lunes(d) for d in trasladables)))


def es_dia_habil(d: date) -> bool:
    return d.weekday() < 5 and d not in festivos_colombia(d.year)


def siguiente_dia_habil(d: date) -> date:
    while not es_dia_habil(d):
        d += timedelta(days=1)
    return d
