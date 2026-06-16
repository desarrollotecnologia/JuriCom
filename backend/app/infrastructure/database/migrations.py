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


def _tabla_existe(tabla: str) -> bool:
    inspector = inspect(engine)
    return tabla in inspector.get_table_names()


def migrar_solicitudes_gestion_legacy() -> None:
    """Normaliza estados legacy y rellena historial inicial faltante."""
    if not _tabla_existe("solicitudes_gestion"):
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE solicitudes_gestion SET estado = 'solicitud' "
                "WHERE estado = 'registrada'"
            )
        )
        conn.execute(
            text(
                "UPDATE solicitudes_gestion SET estado = 'primera_aprobacion' "
                "WHERE estado = 'aprobada'"
            )
        )
        conn.execute(
            text(
                "UPDATE solicitudes_gestion SET estado = 'cancelado' "
                "WHERE estado = 'rechazada'"
            )
        )

    if not _tabla_existe("solicitudes_gestion_historial_estados"):
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO solicitudes_gestion_historial_estados
                    (solicitud_id, etapa, usuario_id, comentario, created_at)
                SELECT
                    s.id,
                    CASE
                        WHEN s.estado IN ('registrada', 'solicitud') THEN 'solicitud'
                        WHEN s.estado = 'aprobada' THEN 'primera_aprobacion'
                        WHEN s.estado = 'rechazada' THEN 'cancelado'
                        ELSE s.estado
                    END,
                    s.creado_por_id,
                    'Solicitud registrada',
                    s.created_at
                FROM solicitudes_gestion s
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM solicitudes_gestion_historial_estados h
                    WHERE h.solicitud_id = s.id
                )
                """
            )
        )


def migrar_solicitudes_gestion_gestion() -> None:
    """Campos para gestión de cotizaciones en el panel."""
    if not _tabla_existe("solicitudes_gestion"):
        return

    columnas_sg = {
        "observaciones_gestion": (
            "ALTER TABLE solicitudes_gestion ADD COLUMN observaciones_gestion TEXT NULL "
            "AFTER observaciones_texto"
        ),
        "justificacion_cotizaciones": (
            "ALTER TABLE solicitudes_gestion ADD COLUMN justificacion_cotizaciones TEXT NULL "
            "AFTER observaciones_gestion"
        ),
        "gestor_id": (
            "ALTER TABLE solicitudes_gestion ADD COLUMN gestor_id INT NULL AFTER creado_por_id"
        ),
        "lider_segunda_aprobacion_id": (
            "ALTER TABLE solicitudes_gestion ADD COLUMN lider_segunda_aprobacion_id "
            "VARCHAR(50) NOT NULL DEFAULT '' AFTER lider_area_label"
        ),
        "lider_segunda_aprobacion_label": (
            "ALTER TABLE solicitudes_gestion ADD COLUMN lider_segunda_aprobacion_label "
            "VARCHAR(500) NOT NULL DEFAULT '' AFTER lider_segunda_aprobacion_id"
        ),
    }
    with engine.begin() as conn:
        for columna, sql in columnas_sg.items():
            if not _columna_existe("solicitudes_gestion", columna):
                logger.info("Agregando columna '%s' a solicitudes_gestion...", columna)
                conn.execute(text(sql))

    if _tabla_existe("solicitudes_gestion_archivos") and not _columna_existe(
        "solicitudes_gestion_archivos", "categoria"
    ):
        with engine.begin() as conn:
            logger.info("Agregando columna 'categoria' a solicitudes_gestion_archivos...")
            conn.execute(
                text(
                    "ALTER TABLE solicitudes_gestion_archivos ADD COLUMN categoria "
                    "VARCHAR(30) NOT NULL DEFAULT 'solicitud' AFTER tamano_bytes"
                )
            )


def migrar_observaciones_trazabilidad() -> None:
    """Tabla 1:N de observaciones y backfill desde columnas legacy."""
    if not _tabla_existe("solicitudes_gestion"):
        return

    if not _tabla_existe("solicitudes_gestion_observaciones"):
        with engine.begin() as conn:
            logger.info("Creando tabla solicitudes_gestion_observaciones...")
            conn.execute(
                text(
                    """
                    CREATE TABLE solicitudes_gestion_observaciones (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        solicitud_id INT NOT NULL,
                        usuario_id INT NULL,
                        autor_nombre VARCHAR(150) NOT NULL,
                        autor_rol VARCHAR(80) NOT NULL,
                        contenido TEXT NOT NULL,
                        contenido_texto TEXT NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        INDEX ix_sg_obs_solicitud_id (solicitud_id),
                        CONSTRAINT fk_sg_obs_solicitud
                            FOREIGN KEY (solicitud_id)
                            REFERENCES solicitudes_gestion (id)
                            ON DELETE CASCADE,
                        CONSTRAINT fk_sg_obs_usuario
                            FOREIGN KEY (usuario_id)
                            REFERENCES users (id)
                            ON DELETE SET NULL
                    )
                    """
                )
            )

    with engine.begin() as conn:
        logger.info("Backfill observaciones iniciales legacy...")
        conn.execute(
            text(
                """
                INSERT INTO solicitudes_gestion_observaciones (
                    solicitud_id, usuario_id, autor_nombre, autor_rol,
                    contenido, contenido_texto, created_at
                )
                SELECT
                    s.id,
                    s.creado_por_id,
                    COALESCE(u.username, 'Usuario'),
                    'Usuario Solicitante',
                    CASE
                        WHEN TRIM(COALESCE(s.observaciones, '')) != ''
                            THEN s.observaciones
                        ELSE CONCAT('<p>', REPLACE(s.observaciones_texto, '\n', '<br>'), '</p>')
                    END,
                    COALESCE(s.observaciones_texto, ''),
                    s.created_at
                FROM solicitudes_gestion s
                LEFT JOIN users u ON u.id = s.creado_por_id
                WHERE (
                    TRIM(COALESCE(s.observaciones_texto, '')) != ''
                    OR TRIM(COALESCE(s.observaciones, '')) != ''
                )
                AND NOT EXISTS (
                    SELECT 1
                    FROM solicitudes_gestion_observaciones o
                    WHERE o.solicitud_id = s.id
                )
                """
            )
        )

        logger.info("Backfill observaciones_gestion legacy...")
        conn.execute(
            text(
                """
                INSERT INTO solicitudes_gestion_observaciones (
                    solicitud_id, usuario_id, autor_nombre, autor_rol,
                    contenido, contenido_texto, created_at
                )
                SELECT
                    s.id,
                    s.gestor_id,
                    COALESCE(g.username, 'Gestor'),
                    'Gestor',
                    s.observaciones_gestion,
                    '',
                    COALESCE(s.updated_at, s.created_at)
                FROM solicitudes_gestion s
                LEFT JOIN users g ON g.id = s.gestor_id
                WHERE TRIM(COALESCE(s.observaciones_gestion, '')) != ''
                AND NOT EXISTS (
                    SELECT 1
                    FROM solicitudes_gestion_observaciones o
                    WHERE o.solicitud_id = s.id
                      AND o.autor_rol = 'Gestor'
                )
                """
            )
        )


def migrar_archivos_observacion() -> None:
    """Vincula archivos existentes con su observación de trazabilidad."""
    if not _tabla_existe("solicitudes_gestion_archivos"):
        return
    if not _tabla_existe("solicitudes_gestion_observaciones"):
        return

    if not _columna_existe("solicitudes_gestion_archivos", "observacion_id"):
        with engine.begin() as conn:
            logger.info("Agregando columna 'observacion_id' a solicitudes_gestion_archivos...")
            conn.execute(
                text(
                    "ALTER TABLE solicitudes_gestion_archivos "
                    "ADD COLUMN observacion_id INT NULL AFTER categoria"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE solicitudes_gestion_archivos "
                    "ADD INDEX ix_sg_arch_observacion_id (observacion_id)"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE solicitudes_gestion_archivos "
                    "ADD CONSTRAINT fk_sg_arch_observacion "
                    "FOREIGN KEY (observacion_id) "
                    "REFERENCES solicitudes_gestion_observaciones (id) "
                    "ON DELETE SET NULL"
                )
            )

    with engine.begin() as conn:
        logger.info("Backfill archivos de solicitud a observación del solicitante...")
        conn.execute(
            text(
                """
                UPDATE solicitudes_gestion_archivos a
                JOIN (
                    SELECT solicitud_id, MIN(id) AS obs_id
                    FROM solicitudes_gestion_observaciones
                    WHERE autor_rol = 'Usuario Solicitante'
                    GROUP BY solicitud_id
                ) o ON o.solicitud_id = a.solicitud_id
                SET a.observacion_id = o.obs_id
                WHERE a.observacion_id IS NULL
                  AND a.categoria = 'solicitud'
                """
            )
        )

        logger.info("Backfill cotizaciones a observación del gestor...")
        conn.execute(
            text(
                """
                UPDATE solicitudes_gestion_archivos a
                JOIN (
                    SELECT solicitud_id, MAX(id) AS obs_id
                    FROM solicitudes_gestion_observaciones
                    WHERE autor_rol = 'Gestor'
                    GROUP BY solicitud_id
                ) o ON o.solicitud_id = a.solicitud_id
                SET a.observacion_id = o.obs_id
                WHERE a.observacion_id IS NULL
                  AND a.categoria = 'cotizacion'
                """
            )
        )


def run_all() -> None:
    migrar_codigo_contratos()
    migrar_estado_contratos()
    migrar_subido_por_archivos()
    migrar_aprobacion_y_vigencia_contratos()
    migrar_aprobacion_otrosies()
    migrar_solicitudes_gestion_legacy()
    migrar_solicitudes_gestion_gestion()
    migrar_observaciones_trazabilidad()
    migrar_archivos_observacion()
    migrar_productos_estado_aprobacion()


def migrar_productos_estado_aprobacion() -> None:
    """Estado por ítem para aprobación parcial en primera aprobación."""
    if not _tabla_existe("solicitudes_gestion_productos"):
        return
    if not _columna_existe("solicitudes_gestion_productos", "estado_aprobacion"):
        with engine.begin() as conn:
            logger.info(
                "Agregando columna 'estado_aprobacion' a solicitudes_gestion_productos..."
            )
            conn.execute(
                text(
                    "ALTER TABLE solicitudes_gestion_productos "
                    "ADD COLUMN estado_aprobacion VARCHAR(20) NOT NULL DEFAULT 'pendiente' "
                    "AFTER centro_costo"
                )
            )
            conn.execute(
                text(
                    """
                    UPDATE solicitudes_gestion_productos p
                    INNER JOIN solicitudes_gestion s ON s.id = p.solicitud_id
                    SET p.estado_aprobacion = 'aprobado'
                    WHERE s.estado NOT IN ('solicitud', 'cancelado')
                    """
                )
            )
