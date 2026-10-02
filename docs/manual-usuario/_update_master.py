"""Genera el manual maestro actualizado: toma el Word editado (con imágenes),
quita las referencias sueltas al rol Anticipos (ya no existe) y lo guarda en docs.
"""

import shutil

from docx import Document

SRC = r"C:\Users\USUARIO\Downloads\Manual-de-Usuario-JURICOM.docx"
DST = r"C:\Users\USUARIO\Documents\Juridica\docs\manual-usuario\Manual-de-Usuario-JURICOM.docx"

# Enlaces/entradas sueltas al rol Anticipos (sin capítulo destino).
A_ELIMINAR = {"Anticipos"}

shutil.copyfile(SRC, DST)
d = Document(DST)
quitados = 0
for p in list(d.paragraphs):
    if p.text.strip() in A_ELIMINAR:
        p._element.getparent().remove(p._element)
        quitados += 1
d.save(DST)
print(f"Maestro actualizado. Parrafos 'Anticipos' quitados: {quitados}")
print("Guardado en:", DST)
