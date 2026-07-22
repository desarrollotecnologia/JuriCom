r"""Genera los tres otrosíes permitidos para Compras listos para Jurídica.

Uso (desde backend/, con el venv):
    .\.venv\Scripts\python.exe scripts\seed_otrosies_prueba.py

Salta el proceso de aprobación líder/gerencia: crea los otrosíes ya en estado
APROBADO y sin PDF, de modo que aparezcan en "Otrosíes pendientes" de Jurídica.
Es solo para pruebas.
"""

import os
import sys
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app.infrastructure.database.session import SessionLocal
from app.infrastructure.database.models import ContratoModel, OtrosiContratoModel


def _elegir_contrato(db):
    return (
        db.query(ContratoModel)
        .filter(
            ContratoModel.estado == "activo",
            ContratoModel.estado_aprobacion == "aprobado",
            ContratoModel.eliminado_at.is_(None),
        )
        .order_by(ContratoModel.id.asc())
        .first()
    )


def _compras_user_id(db):
    row = db.execute(
        text("SELECT id FROM users WHERE role='compras' ORDER BY id ASC LIMIT 1")
    ).first()
    if row:
        return row[0]
    # Fallback: cualquier usuario (solo pruebas).
    row = db.execute(text("SELECT id FROM users ORDER BY id ASC LIMIT 1")).first()
    return row[0] if row else None


def main():
    db = SessionLocal()
    try:
        contrato = _elegir_contrato(db)
        if contrato is None:
            print("No hay contrato activo/aprobado para adjuntar otrosíes.")
            return
        creador = _compras_user_id(db)
        if creador is None:
            print("No hay usuarios en la BD.")
            return

        max_num = (
            db.query(OtrosiContratoModel.numero)
            .filter(OtrosiContratoModel.contrato_id == contrato.id)
            .order_by(OtrosiContratoModel.numero.desc())
            .first()
        )
        siguiente = (max_num[0] if max_num else 0) + 1
        ahora = datetime.now()

        plantillas = [
            dict(
                tipo="prorroga",
                descripcion="[PRUEBA] Prórroga solicitada por Compras.",
                plazo_adicional_cantidad=6,
                plazo_adicional_unidad=contrato.plazo_unidad,
            ),
            dict(
                tipo="adicion",
                descripcion="[PRUEBA] Adición de valor solicitada por Compras.",
                valor_adicional=Decimal("1000000.00"),
            ),
            dict(
                tipo="modificacion",
                descripcion="[PRUEBA] Modificación de descripción solicitada por Compras.",
                nueva_descripcion_servicio="Nuevo alcance del servicio (prueba).",
            ),
        ]

        creados = []
        for i, p in enumerate(plantillas):
            modelo = OtrosiContratoModel(
                contrato_id=contrato.id,
                numero=siguiente + i,
                tipo=p["tipo"],
                descripcion=p["descripcion"],
                plazo_adicional_cantidad=p.get("plazo_adicional_cantidad"),
                plazo_adicional_unidad=p.get("plazo_adicional_unidad"),
                valor_adicional=p.get("valor_adicional"),
                nueva_descripcion_servicio=p.get("nueva_descripcion_servicio"),
                archivo_id=None,
                estado_aprobacion="aprobado",
                aprobado_lider_at=ahora,
                aprobado_gerencia_at=ahora,
                creado_por_id=creador,
                created_at=ahora,
            )
            db.add(modelo)
            creados.append(p["tipo"])

        db.commit()
        print(
            f"Creados {len(creados)} otrosíes ({', '.join(creados)}) en el contrato "
            f"{contrato.codigo} (id={contrato.id}), numeros {siguiente}..{siguiente + len(creados) - 1}."
        )
        print("Aparecerán en 'Otrosíes pendientes' de Jurídica para finalizar.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
