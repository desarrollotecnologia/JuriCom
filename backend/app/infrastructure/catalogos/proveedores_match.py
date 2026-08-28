"""Ranking de proveedores por coincidencia de palabras.

No hay IA aquí: se comparan las palabras del servicio (título + descripción +
centro de costo) contra "Nombre" y "Sector al que pertenece" de cada proveedor,
y se ordena por cantidad de palabras que coinciden.

ponytail: heurística simple de solapamiento de tokens. Suficiente para sugerir;
si algún día se quiere semántica real, migrar a embeddings/servicio externo.
"""

from __future__ import annotations

from typing import Iterable

from app.infrastructure.catalogos.proveedores_excel import normalizar_texto


# Palabras vacías (artículos, preposiciones, conjunciones) que no aportan al match.
_STOPWORDS = {
    "de", "del", "la", "el", "los", "las", "un", "una", "unos", "unas",
    "para", "por", "con", "sin", "y", "o", "u", "e", "en", "al", "a",
    "se", "su", "sus", "que", "the", "of", "and", "servicio", "servicios",
}


def _tokens(texto: str) -> set[str]:
    palabras = normalizar_texto(texto).split()
    return {p for p in palabras if len(p) >= 3 and p not in _STOPWORDS}


def rankear_proveedores(
    consulta: str,
    proveedores: Iterable[dict],
    *,
    solo_servicios: bool = True,
    top: int = 8,
) -> list[dict]:
    """Devuelve los proveedores más afines, cada uno con la clave `_score`.

    `proveedores` son dicts con al menos: nombre, sector, para.
    Solo se devuelven los que tengan al menos una palabra en común.
    """
    tokens_consulta = _tokens(consulta)
    if not tokens_consulta:
        return []

    resultados: list[dict] = []
    for p in proveedores:
        if solo_servicios and p.get("para") not in ("servicios", "ambas"):
            continue
        haystack = _tokens(f"{p.get('nombre', '')} {p.get('sector', '')}")
        score = len(tokens_consulta & haystack)
        if score <= 0:
            continue
        resultados.append({**p, "_score": score})

    resultados.sort(key=lambda x: (-x["_score"], normalizar_texto(x.get("nombre", ""))))
    return resultados[:top]
