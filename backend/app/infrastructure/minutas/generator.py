"""Generador de minutas (.docx) a partir de la información de un contrato.

Toma una de las plantillas base (contratos reales de muestra, con todas sus
cláusulas legales) y reemplaza los datos del contrato de muestra por los del
contrato seleccionado. Los datos que el sistema no almacena (representante
legal, cédula, etc.) se marcan resaltados con «COMPLETAR …» para que Jurídica
los diligencie en Word.

El reemplazo es "run-aware": conserva el formato del resto del párrafo.
"""

from __future__ import annotations

import io
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.text import WD_COLOR_INDEX

from app.infrastructure.minutas.numeros import (
    miles_con_puntos,
    numero_a_letras,
    pesos_en_letras,
)

_DIR = Path(__file__).parent / "plantillas"

PLANTILLAS = {
    "obra": {"archivo": "obra.docx", "nombre": "Contrato de Obra"},
    "orden_trabajo": {"archivo": "orden_trabajo.docx", "nombre": "Orden de Trabajo"},
    "suministro": {"archivo": "suministro.docx", "nombre": "Contrato de Suministro e Instalación"},
    "cps": {"archivo": "cps.docx", "nombre": "Contrato de Prestación de Servicios (CPS)"},
}

_UNIDAD_LABEL = {
    "dias": "DÍAS HÁBILES",
    "dias_calendario": "DÍAS CALENDARIO",
    "meses": "MESES",
    "anios": "AÑOS",
}

_REP = "«COMPLETAR: representante legal del contratista»"


def _all_paragraphs(doc):
    yield from doc.paragraphs
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                yield from cell.paragraphs


def _replace_in_paragraph(paragraph, old: str, new: str, highlight: bool) -> bool:
    """Reemplaza `old` por `new` dentro del párrafo respetando los runs.

    Devuelve True si hubo al menos un reemplazo.
    """
    runs = paragraph.runs
    if not runs:
        return False
    texto = "".join(r.text for r in runs)
    if old not in texto:
        return False

    while old in texto:
        inicio = texto.index(old)
        fin = inicio + len(old)
        pos = 0
        run_ini = off_ini = run_fin = off_fin = None
        for i, r in enumerate(runs):
            largo = len(r.text)
            if run_ini is None and pos + largo > inicio:
                run_ini, off_ini = i, inicio - pos
            if pos + largo >= fin:
                run_fin, off_fin = i, fin - pos
                break
            pos += largo
        if run_ini is None or run_fin is None:
            break
        if run_ini == run_fin:
            r = runs[run_ini]
            r.text = r.text[:off_ini] + new + r.text[off_fin:]
        else:
            runs[run_ini].text = runs[run_ini].text[:off_ini] + new
            for i in range(run_ini + 1, run_fin):
                runs[i].text = ""
            runs[run_fin].text = runs[run_fin].text[off_fin:]
        if highlight:
            runs[run_ini].font.highlight_color = WD_COLOR_INDEX.YELLOW
        texto = "".join(r.text for r in runs)
    return True


def _aplicar(doc, reemplazos):
    for old, new, highlight in reemplazos:
        if not old:
            continue
        for paragraph in _all_paragraphs(doc):
            _replace_in_paragraph(paragraph, old, new or "", highlight)


def _banner(doc, contrato):
    hoy = date.today().strftime("%d/%m/%Y")
    codigo = getattr(contrato, "codigo", "") or ""
    texto = (
        f"MINUTA GENERADA AUTOMÁTICAMENTE DESDE EL CONTRATO {codigo} EL {hoy}. "
        "Revise y complete los campos resaltados «COMPLETAR …» y valide la "
        "información antes de usar este documento."
    )
    primer = doc.paragraphs[0]
    parrafo = primer.insert_paragraph_before()
    run = parrafo.add_run(texto)
    run.bold = True
    run.font.highlight_color = WD_COLOR_INDEX.YELLOW


def _plazo_core(contrato) -> str:
    n = int(getattr(contrato, "plazo_cantidad", 0) or 0)
    unidad = getattr(contrato, "plazo_unidad", None)
    unidad = getattr(unidad, "value", unidad) or "dias"
    return f"{numero_a_letras(n)} ({n}) {_UNIDAD_LABEL.get(unidad, unidad.upper())}"


def _reemplazos(key: str, c) -> list[tuple[str, str, bool]]:
    cod = getattr(c, "codigo", "") or ""
    contratista = getattr(c, "proveedor_contratista", "") or ""
    nit = getattr(c, "nit_proveedor", "") or ""
    objeto = getattr(c, "descripcion_servicio", "") or ""
    valor_letras = pesos_en_letras(getattr(c, "valor", 0) or 0)
    valor_num = "$" + miles_con_puntos(getattr(c, "valor", 0) or 0)
    plazo = _plazo_core(c)

    if key == "obra":
        return [
            ("$148.381.168", valor_num, False),
            ("CIENTO CUARENTA Y OCHO MILLONES TRESCIENTOS OCHENTA Y UN MIL CIENTO SESENTA Y OCHO PESOS M/CTE", valor_letras, False),
            ("Obra civil por precios unitarios firmes correspondiente a desmontes y adecuaciones estructurales en la Planta de Tratamiento de Aguas Residuales (PETAR) de Colbeef, conforme a los términos y condiciones plasmados en la cotización del 29 de MAYO de 2026.", objeto, False),
            ("desmontes y adecuaciones estructurales en la Planta de Tratamiento de Aguas Residuales (PETAR) de Colbeef, conforme a los términos y condiciones plasmados en la cotización del 29 de MAYO de 2026.", objeto, False),
            ("Treinta (30) días calendario contados a partir de la suscripción del contrato.", plazo + " contados a partir de la suscripción del contrato.", False),
            ("Treinta (30) días calendario", plazo, False),
            ("FRANCISCO ANDRES RINCON SOLANO S.A.S", contratista, False),
            ("FRANCISCO ANDRÉS RINCÓN SOLANO", _REP, True),
            ("901.357.967", nit, False),
            ("1.098.741.161", nit, False),
            ("2026-216", cod, False),
        ]
    if key == "orden_trabajo":
        return [
            ("$10.018.062", valor_num, False),
            ("DIEZ MILLONES DIECIOCHO MIL SESENTA Y DOS PESOS M/CTE", valor_letras, False),
            ("Prestación de servicios para el mantenimiento predictivo y preventivo para el generador STAMFORD que se caracteriza por 500KW 1800RPM 440voltios 60Hz 3phases, el cual incluye el desacople, desmontaje, traslado, diagnostico, metrología mecánica, protocolo de pruebas eléctricas (CLZ, MEGGER, HIPOT, SURGE, IP/DAR) verificación plato de rectificación (Diodos, varistor), verificación de balanceo dinámico a rotor, informe técnico, traslado de vuelta y montaje en las instalaciones del CONTRATANTE y demás términos de la cotización del 05 de abril de 2026", objeto, False),
            ("DOCE (12) DÍAS HABILES", plazo, False),
            ("VASQUEZ & RODRIGUEZ LTDA", contratista, False),
            ("MARIA LEONOR VASQUEZ SILVA", _REP, True),
            ("804.015.808-6", nit, False),
            ("91.256.586", nit, False),
            ("2026-222", cod, False),
        ]
    if key == "suministro":
        return [
            ("$20.862.400", valor_num, False),
            ("VEINTE MILLONES OCHOCIENTOS SESENTA Y DOS MIL CUATROCIENTOS PESOS M/CTE", valor_letras, False),
            ("SUMINISTRO E INSTALACIÓN DE DOSCIENTAS DIEZ (210) FRANJAS EPOXICAS ANTIDESLIZANTES DE 50MM DE TIPO INDUSTRIAL PARA TRAFICO PESADO CON UNA RESITENCIA DE USO DE CINCO (05) AÑOS LAS CUALES SE VAN A UBICAR EN (XXXX)", objeto, False),
            ("SUMINISTRO, MONTAJE, INSTALACIÓN Y ADECUACIONES PARA LOS SOPORTES DE LOS FILTROS UBICADOS EN LA PLANTA DE TRATAMIENTO DE AGUA POTABLE (PTAP) DE COLBEEF", objeto, False),
            ("DOCE (12) DIAS hábiles posteriores a la firma del contrato.", plazo + " posteriores a la firma del contrato.", False),
            ("doce (12) dias hábiles", plazo, False),
            ("SOLUCIONES, AUTOMATIZACIONES Y TECNOLOGIA - S.A.S.", contratista, False),
            ("INDUSTRIAS O&C INGENIERIA S.A.S.", contratista, False),
            ("ANDRES FELIPE GARCIA ESTEBAN", _REP, True),
            ("FRANCISCO RODRIGUEZ OVIEDO", _REP, True),
            ("901.550.471-3", nit, False),
            ("901.358.312-9", nit, False),
            ("1.005.260.534", nit, False),
            ("91.269.170", nit, False),
            ("2026-213", cod, False),
        ]
    if key == "cps":
        return [
            ("$13.873.758", valor_num, False),
            ("TRECE MILLONES OCHOCIENTOS SETENTA Y TRES MIL SETECIENTOS CINCUENTA Y OCHO PESOS M/CTE", valor_letras, False),
            ("PRESTACION DE SERVICIOS PARA EL SERVICIO DE MANTENIMIENTO PREVENTIVO DEL EJE Y TORNILLO  SIN FIN SCREW PRESS UBICADOS EN (XXXXXXXXX) EN INSTALACIONES DEN LA PLANTA DE COLBEEF.", objeto, False),
            ("LA PRESTACION DE SERVICIOS PARA EL MANTENIMIENTO PREVENTIVO DEL EJE Y TORNILLO  SIN FIN SCREW PRESS UBICADO EN (XXXXXXXXXXX) DE LA PLANTA DE COLBEEF", objeto, False),
            ("PRESTACION DE SERVICIOS PARA EL MANTENIMIENTO PREVENTIVO DEL EJE Y TORNILLO  SIN FIN SCREW PRESS UBICADO EN (XXXXXXXXXXX) DE LA PLANTA DE COLBEEF", objeto, False),
            ("VEINTE (20) DIAS CONTADOS A PARTIR DE LA FIRMA DEL PRESENTE CONTRATO.", plazo + " CONTADOS A PARTIR DE LA FIRMA DEL PRESENTE CONTRATO.", False),
            ("doce (12) DIAS CALENDARIO", plazo, False),
            ("METAL FULL S.A.S.", contratista, False),
            ("METALFULL S.A.S.", contratista, False),
            ("CESAR AUGUSTO SIERRA GARCIA", _REP, True),
            ("901.118.220", nit, False),
            ("13.746.383", nit, False),
            ("2026-219", cod, False),
        ]
    raise KeyError(key)


def generar_minuta(plantilla: str, contrato) -> bytes:
    if plantilla not in PLANTILLAS:
        raise KeyError(f"Plantilla desconocida: {plantilla}")
    ruta = _DIR / PLANTILLAS[plantilla]["archivo"]
    doc = Document(str(ruta))
    _aplicar(doc, _reemplazos(plantilla, contrato))
    _banner(doc, contrato)
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
