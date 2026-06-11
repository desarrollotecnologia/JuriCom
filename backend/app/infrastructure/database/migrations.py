"""Migraciones simples e idempotentes.

Cada función debe poder ejecutarse muchas veces sin romper nada.
Si en el futuro se vuelve más complejo, migrar a Alembic.
"""

import logging

from sqlalchemy import inspect, text

from app.infrastructure.database.session import engine


logger = logging.getLogger(__name__)


def _columna_existe(tabla: str, columna: str) -> bool:
    inspector = inspect(engine)
    return columna in [c["name"] for c in inspector.get_columns(tabla)]


def _indice_existe(tabla: str, nombre_indice: str) -> bool:
    inspector = inspect(engine)
    return nombre_indice in [i["name"] for i in inspector.get_indexes(tabla)]


def migrar_codigo_contratos() -> None:
    """Agrega la columna `codigo` a `contratos` si no existe y rellena
    los contratos antiguos con un código generado a partir del id.
    """
    if _columna_existe("contratos", "codigo"):
        return

    with engine.begin() as conn:
        logger.info("Agregando columna 'codigo' a tabla 'contratos'...")
        conn.execute(
            text(
                "ALTER TABLE contratos ADD COLUMN codigo VARCHAR(20) NULL AFTER id"
            )
        )
        conn.execute(
            text(
                "UPDATE contratos "
                "SET codigo = CONCAT('JC-', LPAD(id, 4, '0')) "
                "WHERE codigo IS NULL"
            )
        )
        conn.execute(
            text("ALTER TABLE contratos MODIFY COLUMN codigo VARCHAR(20) NOT NULL")
        )
        if not _indice_existe("contratos", "uq_contratos_codigo"):
            conn.execute(
                text(
                    "ALTER TABLE contratos "
                    "ADD UNIQUE INDEX uq_contratos_codigo (codigo)"
                )
            )
        logger.info("Columna 'codigo' creada y poblada.")


def migrar_estado_contratos() -> None:
    """Migra el estado por defecto de los contratos:
    - Convierte cualquier valor antiguo 'radicado' a 'en_proceso'.
    """
    if not _columna_existe("contratos", "estado"):
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE contratos SET estado = 'en_proceso' "
                "WHERE estado NOT IN ('en_proceso','activo','finalizado')"
            )
        )


def migrar_subido_por_archivos() -> None:
    """Agrega la columna `subido_por_id` a `archivos_contrato` si no existe."""
    if _columna_existe("archivos_contrato", "subido_por_id"):
        return
    with engine.begin() as conn:
        logger.info("Agregando columna 'subido_por_id' a 'archivos_contrato'...")
        conn.execute(
            text(
                "ALTER TABLE archivos_contrato "
                "ADD COLUMN subido_por_id INT NULL"
            )
        )
        # FK opcional — si la base lo permite, agregamos restricción.
        try:
            conn.execute(
                text(
                    "ALTER TABLE archivos_contrato "
                    "ADD CONSTRAINT fk_archivos_subido_por "
                    "FOREIGN KEY (subido_por_id) REFERENCES users(id) "
                    "ON DELETE SET NULL"
                )
            )
        except Exception as e:
            logger.warning("No se pudo agregar FK fk_archivos_subido_por: %s", e)


def migrar_aprobacion_y_vigencia_contratos() -> None:
    """Agrega campos del flujo líder→gerencia y vigencia del contrato."""
    columnas = {
        "correo_lider_proceso": "ALTER TABLE contratos ADD COLUMN correo_lider_proceso VARCHAR(255) NOT NULL DEFAULT '' AFTER requiere_poliza",
        "correo_gerencia": "ALTER TABLE contratos ADD COLUMN correo_gerencia VARCHAR(255) NOT NULL DEFAULT '' AFTER correo_lider_proceso",
        "estado_aprobacion": "ALTER TABLE contratos ADD COLUMN estado_aprobacion VARCHAR(30) NOT NULL DEFAULT 'aprobado' AFTER correo_gerencia",
        "fecha_inicio": "ALTER TABLE contratos ADD COLUMN fecha_inicio DATE NULL AFTER estado",
        "fecha_fin": "ALTER TABLE contratos ADD COLUMN fecha_fin DATE NULL AFTER fecha_inicio",
        "fecha_proxima_notificacion": "ALTER TABLE contratos ADD COLUMN fecha_proxima_notificacion DATE NULL AFTER fecha_fin",
        "aprobado_lider_at": "ALTER TABLE contratos ADD COLUMN aprobado_lider_at DATETIME NULL AFTER fecha_proxima_notificacion",
        "aprobado_gerencia_at": "ALTER TABLE contratos ADD COLUMN aprobado_gerencia_at DATETIME NULL AFTER aprobado_lider_at",
    }
    with engine.begin() as conn:
        for columna, sql in columnas.items():
            if not _columna_existe("contratos", columna):
                logger.info("Agregando columna '%s' a 'contratos'...", columna)
                conn.execute(text(sql))
        if not _indice_existe("contratos", "ix_contratos_estado_aprobacion"):
            try:
                conn.execute(
                    text(
                        "ALTER TABLE contratos ADD INDEX "
                        "ix_contratos_estado_aprobacion (estado_aprobacion)"
                    )
                )
            except Exception as e:
                logger.warning(
                    "No se pudo crear índice ix_contratos_estado_aprobacion: %s", e
                )


def migrar_aprobacion_otrosies() -> None:
    """Agrega aprobación líder→gerencia para solicitudes de otrosí."""
    columnas = {
        "estado_aprobacion": "ALTER TABLE otrosies_contrato ADD COLUMN estado_aprobacion VARCHAR(30) NOT NULL DEFAULT 'aprobado' AFTER archivo_id",
        "aprobado_lider_at": "ALTER TABLE otrosies_contrato ADD COLUMN aprobado_lider_at DATETIME NULL AFTER estado_aprobacion",
        "aprobado_gerencia_at": "ALTER TABLE otrosies_contrato ADD COLUMN aprobado_gerencia_at DATETIME NULL AFTER aprobado_lider_at",
    }
    with engine.begin() as conn:
        for columna, sql in columnas.items():
            if not _columna_existe("otrosies_contrato", columna):
                logger.info("Agregando columna '%s' a 'otrosies_contrato'...", columna)
                conn.execute(text(sql))
        if not _indice_existe("otrosies_contrato", "ix_otrosies_estado_aprobacion"):
            try:
                conn.execute(
                    text(
                        "ALTER TABLE otrosies_contrato ADD INDEX "
                        "ix_otrosies_estado_aprobacion (estado_aprobacion)"
                    )
                )
            except Exception as e:
                logger.warning(
                    "No se pudo crear índice ix_otrosies_estado_aprobacion: %s", e
                )


def run_all() -> None:
    migrar_codigo_contratos()
    migrar_estado_contratos()
    migrar_subido_por_archivos()
    migrar_aprobacion_y_vigencia_contratos()
    migrar_aprobacion_otrosies()
