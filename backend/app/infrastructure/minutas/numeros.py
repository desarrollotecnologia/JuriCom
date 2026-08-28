"""Conversión de números enteros a letras en español (para minutas).

Sin dependencias externas. Cubre hasta miles de millones, suficiente para
valores de contrato y cantidades de plazo. Devuelve MAYÚSCULAS, como se usa
en los contratos.
"""

_UNIDADES = [
    "", "UNO", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO",
    "NUEVE", "DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISÉIS",
    "DIECISIETE", "DIECIOCHO", "DIECINUEVE", "VEINTE", "VEINTIUNO", "VEINTIDÓS",
    "VEINTITRÉS", "VEINTICUATRO", "VEINTICINCO", "VEINTISÉIS", "VEINTISIETE",
    "VEINTIOCHO", "VEINTINUEVE",
]
_DECENAS = ["", "", "", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"]
_CENTENAS = [
    "", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS",
    "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS",
]


def _tres_cifras(n: int) -> str:
    """0..999 en letras."""
    if n == 0:
        return ""
    if n == 100:
        return "CIEN"
    centena, resto = divmod(n, 100)
    partes = []
    if centena:
        partes.append(_CENTENAS[centena])
    if resto:
        if resto < 30:
            partes.append(_UNIDADES[resto])
        else:
            decena, unidad = divmod(resto, 10)
            if unidad:
                partes.append(f"{_DECENAS[decena]} Y {_UNIDADES[unidad]}")
            else:
                partes.append(_DECENAS[decena])
    return " ".join(partes)


def _apocope(texto: str) -> str:
    """'...UNO' -> '...UN' / 'VEINTIUNO' -> 'VEINTIÚN' (antes de MIL/MILLONES)."""
    if texto.endswith("VEINTIUNO"):
        return texto[:-9] + "VEINTIÚN"
    if texto.endswith("UNO"):
        return texto[:-3] + "UN"
    return texto


def numero_a_letras(n: int) -> str:
    n = int(n)
    if n == 0:
        return "CERO"
    if n < 0:
        return "MENOS " + numero_a_letras(-n)

    millones, resto = divmod(n, 1_000_000)
    miles, unidades = divmod(resto, 1_000)
    partes = []

    if millones:
        if millones == 1:
            partes.append("UN MILLÓN")
        else:
            partes.append(_apocope(_tres_cifras(millones)) + " MILLONES")
    if miles:
        if miles == 1:
            partes.append("MIL")
        else:
            partes.append(_apocope(_tres_cifras(miles)) + " MIL")
    if unidades:
        partes.append(_tres_cifras(unidades))

    return " ".join(p for p in partes if p)


def pesos_en_letras(valor) -> str:
    """Entero de pesos -> '... PESOS M/CTE'."""
    return f"{numero_a_letras(int(round(float(valor))))} PESOS M/CTE"


def miles_con_puntos(valor) -> str:
    """148381168 -> '148.381.168'."""
    return f"{int(round(float(valor))):,}".replace(",", ".")


if __name__ == "__main__":
    # Autocomprobación contra los 4 contratos de muestra.
    casos = {
        148381168: "CIENTO CUARENTA Y OCHO MILLONES TRESCIENTOS OCHENTA Y UN MIL CIENTO SESENTA Y OCHO",
        10018062: "DIEZ MILLONES DIECIOCHO MIL SESENTA Y DOS",
        20862400: "VEINTE MILLONES OCHOCIENTOS SESENTA Y DOS MIL CUATROCIENTOS",
        13873758: "TRECE MILLONES OCHOCIENTOS SETENTA Y TRES MIL SETECIENTOS CINCUENTA Y OCHO",
        0: "CERO",
        1000: "MIL",
        21000: "VEINTIÚN MIL",
        1000000: "UN MILLÓN",
        100: "CIEN",
        21: "VEINTIUNO",
    }
    for numero, esperado in casos.items():
        obtenido = numero_a_letras(numero)
        assert obtenido == esperado, f"{numero}: {obtenido!r} != {esperado!r}"
    assert miles_con_puntos(148381168) == "148.381.168"
    print("numeros.py OK")
