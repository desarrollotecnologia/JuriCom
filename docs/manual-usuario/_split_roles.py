"""Divide el manual Word (ya con imágenes) en un documento por rol.

Cada doc = portada del rol + "Introducción y acceso" (reutilizada) + capítulo del rol.
Reutiliza las imágenes incrustadas (se copian con su relación).
"""

import copy
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "Manual-de-Usuario-JURICOM.docx")
OUT_DIR = os.path.join(HERE, "por-rol")

# Título exacto del capítulo en el Word -> (nombre visible del rol, archivo).
ROLES = [
    ("Rol: Administrador", "Administrador", "Manual JURICOM - Administrador.docx"),
    ("Rol: Supervisor (Solicitante)", "Supervisor", "Manual JURICOM - Supervisor.docx"),
    ("Rol: Compras", "Compras", "Manual JURICOM - Compras.docx"),
    ("Rol: Proyectos", "Proyectos", "Manual JURICOM - Proyectos.docx"),
    ("Rol: Líder Aprobador", "Líder Aprobador", "Manual JURICOM - Lider Aprobador.docx"),
    ("Rol: Contabilidad", "Contabilidad", "Manual JURICOM - Contabilidad.docx"),
    ("Rol: Tesorería", "Tesorería", "Manual JURICOM - Tesoreria.docx"),
    ("Rol: Jurídica", "Jurídica", "Manual JURICOM - Juridica.docx"),
]

# Todos los textos que marcan inicio de capítulo (para delimitar secciones).
BOUNDARIES_ROLE = {t for t, _, _ in ROLES}


def p_text(el):
    if el.tag != qn("w:p"):
        return None
    return "".join(t.text or "" for t in el.findall(".//" + qn("w:t"))).strip()


def es_boundary(txt):
    if txt is None:
        return False
    if txt in BOUNDARIES_ROLE:
        return True
    if txt == "Trazabilidad del proceso":
        return True
    if txt.startswith("Manual de Usuario") and "JURICOM" in txt:
        return True
    return False


class ImgCopier:
    def __init__(self):
        self._docpr_id = 1000

    def copy_into(self, dst, src, el):
        new = copy.deepcopy(el)
        # Reasigna ids de objetos de dibujo para que Word no se queje de duplicados.
        for docpr in new.findall(".//" + qn("wp:docPr")):
            self._docpr_id += 1
            docpr.set("id", str(self._docpr_id))
        # Reenlaza las imágenes (a:blip r:embed) al nuevo documento.
        for blip in new.findall(".//" + qn("a:blip")):
            for attr in ("r:embed", "r:link"):
                rid = blip.get(qn(attr))
                if not rid:
                    continue
                try:
                    image_part = src.part.related_parts[rid]
                except KeyError:
                    continue
                new_rid = dst.part.relate_to(image_part, RT.IMAGE)
                blip.set(qn(attr), new_rid)
        sectPr = dst.element.body.find(qn("w:sectPr"))
        sectPr.addprevious(new)


def portada(dst, rol):
    t = dst.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("Manual de Usuario")
    r.bold = True
    r.font.size = Pt(28)
    r.font.color.rgb = RGBColor(0x16, 0x39, 0x66)
    s = dst.add_paragraph()
    s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rs = s.add_run("JURICOM · Colbeef")
    rs.font.size = Pt(16)
    rs.font.color.rgb = RGBColor(0x47, 0x55, 0x69)
    s2 = dst.add_paragraph()
    s2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = s2.add_run(f"Rol: {rol}")
    r2.bold = True
    r2.font.size = Pt(14)
    r2.font.color.rgb = RGBColor(0x0F, 0x76, 0x6E)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    src = Document(SRC)
    body = list(src.element.body)
    # Posiciones de inicio de cada capítulo.
    cortes = []  # (pos, titulo)
    for i, el in enumerate(body):
        txt = p_text(el)
        if es_boundary(txt):
            cortes.append((i, txt))

    def rango(titulo):
        """Elementos [inicio, siguiente_corte) para el capítulo con ese título."""
        for idx, (pos, t) in enumerate(cortes):
            if t == titulo:
                fin = cortes[idx + 1][0] if idx + 1 < len(cortes) else None
                if fin is None:
                    # hasta el final, sin sectPr
                    fin = len(body)
                    while fin > pos and body[fin - 1].tag == qn("w:sectPr"):
                        fin -= 1
                return body[pos:fin]
        return []

    # Sección "Introducción y acceso": dentro del capítulo intro, desde el H2
    # "1. Introducción y acceso" hasta el inicio de "Trazabilidad del proceso".
    intro_titulo = next(t for _, t in cortes if t.startswith("Manual de Usuario"))
    intro_pos = next(pos for pos, t in cortes if t == intro_titulo)
    traza_pos = next(pos for pos, t in cortes if t == "Trazabilidad del proceso")
    acceso_ini = None
    for i in range(intro_pos, traza_pos):
        if p_text(body[i]) == "1. Introducción y acceso":
            acceso_ini = i
            break
    acceso_els = body[acceso_ini:traza_pos] if acceso_ini is not None else []

    # Sección "Trazabilidad del proceso": desde su H1 hasta el primer capítulo de rol.
    primer_rol_pos = min(pos for pos, t in cortes if t in BOUNDARIES_ROLE)
    traza_els = body[traza_pos:primer_rol_pos]

    generados = []
    # Roles presentes en el Word.
    for titulo, rol, archivo in ROLES:
        cap_els = rango(titulo)
        dst = Document()
        dst.styles["Normal"].font.name = "Calibri"
        dst.styles["Normal"].font.size = Pt(11)
        portada(dst, rol)
        cop = ImgCopier()
        for el in acceso_els:
            cop.copy_into(dst, src, el)
        dst.add_page_break()
        for el in traza_els:
            cop.copy_into(dst, src, el)
        dst.add_page_break()
        if not cap_els:
            dst.add_paragraph(f"(No se encontró el capítulo '{titulo}' en el Word origen.)")
        for el in cap_els:
            cop.copy_into(dst, src, el)
        # Reaplica estilo de título al encabezado del rol (algunos quedaron 'normal').
        path = os.path.join(OUT_DIR, archivo)
        dst.save(path)
        generados.append((archivo, len(cap_els)))

    print("Generados en:", OUT_DIR)
    for a, n in generados:
        print(f"  - {a}  (elementos capitulo: {n})")


if __name__ == "__main__":
    main()
