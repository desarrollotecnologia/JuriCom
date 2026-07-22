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


def migrar_tipo_codigo_contratos() -> None:
    """Tipo de código documental: C (contrato) u OS (orden de trabajo)."""
    if not _tabla_existe("contratos"):
        return
    if _columna_existe("contratos", "tipo_codigo"):
        return
    with engine.begin() as conn:
        logger.info("Agregando columna 'tipo_codigo' a contratos...")
        conn.execute(
            text(
                "ALTER TABLE contratos "
                "ADD COLUMN tipo_codigo VARCHAR(10) NOT NULL DEFAULT 'C' "
                "AFTER codigo"
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
        "fecha_inicio_original": "ALTER TABLE contratos ADD COLUMN fecha_inicio_original DATE NULL AFTER fecha_inicio",
        "fecha_fin": "ALTER TABLE contratos ADD COLUMN fecha_fin DATE NULL AFTER fecha_inicio",
        "fecha_proxima_notificacion": "ALTER TABLE contratos ADD COLUMN fecha_proxima_notificacion DATE NULL AFTER fecha_fin",
        "hora_proxima_notificacion": "ALTER TABLE contratos ADD COLUMN hora_proxima_notificacion TIME NULL DEFAULT '00:10:00' AFTER fecha_proxima_notificacion",
        "fecha_ultima_notificacion_vencimiento": "ALTER TABLE contratos ADD COLUMN fecha_ultima_notificacion_vencimiento DATETIME NULL AFTER hora_proxima_notificacion",
        "aprobado_lider_at": "ALTER TABLE contratos ADD COLUMN aprobado_lider_at DATETIME NULL AFTER fecha_ultima_notificacion_vencimiento",
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


def migrar_fechas_contratos_activos() -> None:
    """Backfill de vigencia para contratos activos que quedaron sin fechas."""
    if not _tabla_existe("contratos"):
        return
    columnas = ("fecha_inicio", "fecha_fin", "fecha_proxima_notificacion")
    if any(not _columna_existe("contratos", columna) for columna in columnas):
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE contratos
                SET fecha_inicio = COALESCE(fecha_inicio, DATE(updated_at), CURDATE())
                WHERE estado = 'activo'
                  AND fecha_inicio IS NULL
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE contratos
                SET fecha_fin = CASE plazo_unidad
                    WHEN 'dias' THEN DATE_ADD(fecha_inicio, INTERVAL plazo_cantidad DAY)
                    WHEN 'meses' THEN DATE_ADD(fecha_inicio, INTERVAL plazo_cantidad MONTH)
                    WHEN 'anios' THEN DATE_ADD(fecha_inicio, INTERVAL plazo_cantidad YEAR)
                    ELSE fecha_fin
                END
                WHERE estado = 'activo'
                  AND fecha_inicio IS NOT NULL
                  AND fecha_fin IS NULL
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE contratos
                SET fecha_proxima_notificacion = GREATEST(
                    fecha_inicio,
                    DATE_SUB(fecha_fin, INTERVAL 30 DAY)
                )
                WHERE estado = 'activo'
                  AND fecha_inicio IS NOT NULL
                  AND fecha_fin IS NOT NULL
                  AND fecha_proxima_notificacion IS NULL
                """
            )
        )
        if _columna_existe("contratos", "hora_proxima_notificacion"):
            conn.execute(
                text(
                    """
                    UPDATE contratos
                    SET hora_proxima_notificacion = '00:10:00'
                    WHERE hora_proxima_notificacion IS NULL
                       OR hora_proxima_notificacion = '06:00:00'
                    """
                )
            )


def migrar_eliminacion_logica_contratos() -> None:
    """Campos para ver contratos eliminados con motivo obligatorio."""
    if not _tabla_existe("contratos"):
        return
    columnas = {
        "eliminado_at": (
            "ALTER TABLE contratos ADD COLUMN eliminado_at DATETIME NULL "
            "AFTER aprobado_gerencia_at"
        ),
        "eliminado_por_id": (
            "ALTER TABLE contratos ADD COLUMN eliminado_por_id INT NULL "
            "AFTER eliminado_at"
        ),
        "eliminado_observacion": (
            "ALTER TABLE contratos ADD COLUMN eliminado_observacion TEXT NULL "
            "AFTER eliminado_por_id"
        ),
    }
    with engine.begin() as conn:
        for columna, sql in columnas.items():
            if not _columna_existe("contratos", columna):
                logger.info("Agregando columna '%s' a 'contratos'...", columna)
                conn.execute(text(sql))
        if not _indice_existe("contratos", "ix_contratos_eliminado_at"):
            try:
                conn.execute(
                    text("ALTER TABLE contratos ADD INDEX ix_contratos_eliminado_at (eliminado_at)")
                )
            except Exception as e:
                logger.warning("No se pudo crear índice ix_contratos_eliminado_at: %s", e)
        try:
            conn.execute(
                text(
                    "ALTER TABLE contratos ADD CONSTRAINT fk_contratos_eliminado_por "
                    "FOREIGN KEY (eliminado_por_id) REFERENCES users(id) "
                    "ON DELETE SET NULL"
                )
            )
        except Exception as e:
            logger.warning("No se pudo agregar FK fk_contratos_eliminado_por: %s", e)


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


def migrar_campos_solicitud_servicios() -> None:
    """Campos específicos del formulario Solicitud de Servicios."""
    if not _tabla_existe("solicitudes_gestion"):
        return
    columnas = [
        (
            "requiere_visita",
            "ALTER TABLE solicitudes_gestion ADD COLUMN requiere_visita TINYINT(1) NULL "
            "AFTER observaciones_texto",
        ),
        (
            "servicio_programado",
            "ALTER TABLE solicitudes_gestion ADD COLUMN servicio_programado TINYINT(1) NULL "
            "AFTER requiere_visita",
        ),
        (
            "fecha_servicio_programado",
            "ALTER TABLE solicitudes_gestion ADD COLUMN fecha_servicio_programado DATE NULL "
            "AFTER servicio_programado",
        ),
        (
            "descripcion_servicio",
            "ALTER TABLE solicitudes_gestion ADD COLUMN descripcion_servicio TEXT NOT NULL "
            "AFTER fecha_servicio_programado",
        ),
        (
            "descripcion_servicio_texto",
            "ALTER TABLE solicitudes_gestion ADD COLUMN descripcion_servicio_texto TEXT NOT NULL "
            "AFTER descripcion_servicio",
        ),
        (
            "proveedor_sugerido",
            "ALTER TABLE solicitudes_gestion ADD COLUMN proveedor_sugerido VARCHAR(500) NOT NULL "
            "DEFAULT '' AFTER descripcion_servicio_texto",
        ),
    ]
    with engine.begin() as conn:
        for columna, ddl in columnas:
            if not _columna_existe("solicitudes_gestion", columna):
                logger.info("Agregando columna '%s' a solicitudes_gestion...", columna)
                conn.execute(text(ddl))


def migrar_numero_consecutivo_solicitudes() -> None:
    """Consecutivo y código independientes por tipo de solicitud."""
    if not _tabla_existe("solicitudes_gestion"):
        return

    if not _columna_existe("solicitudes_gestion", "numero_consecutivo"):
        with engine.begin() as conn:
            logger.info("Agregando columna 'numero_consecutivo' a solicitudes_gestion...")
            conn.execute(
                text(
                    "ALTER TABLE solicitudes_gestion "
                    "ADD COLUMN numero_consecutivo INT NULL AFTER tipo"
                )
            )

    prefijos = {
        "compra": "SG",
        "salidas_almacen": "SA",
        "insumos_servicios": "SRV",
    }

    with engine.begin() as conn:
        sin_consecutivo = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM solicitudes_gestion
                WHERE numero_consecutivo IS NULL
                """
            )
        ).scalar()
        if not sin_consecutivo:
            if not _indice_existe("solicitudes_gestion", "uq_sg_tipo_numero_consecutivo"):
                logger.info(
                    "Creando índice único uq_sg_tipo_numero_consecutivo en solicitudes_gestion..."
                )
                conn.execute(
                    text(
                        "ALTER TABLE solicitudes_gestion "
                        "ADD UNIQUE KEY uq_sg_tipo_numero_consecutivo (tipo, numero_consecutivo)"
                    )
                )
            return

        logger.info(
            "Asignando consecutivos por tipo a %s solicitud(es)...",
            sin_consecutivo,
        )
        for tipo, prefijo in prefijos.items():
            filas = conn.execute(
                text(
                    """
                    SELECT id FROM solicitudes_gestion
                    WHERE tipo = :tipo AND numero_consecutivo IS NULL
                    ORDER BY id
                    """
                ),
                {"tipo": tipo},
            ).fetchall()
            if not filas:
                continue
            max_num = conn.execute(
                text(
                    """
                    SELECT COALESCE(MAX(numero_consecutivo), 0)
                    FROM solicitudes_gestion
                    WHERE tipo = :tipo
                    """
                ),
                {"tipo": tipo},
            ).scalar()
            for numero, (solicitud_id,) in enumerate(filas, start=int(max_num) + 1):
                codigo = f"{prefijo}-{numero:04d}"
                conn.execute(
                    text(
                        """
                        UPDATE solicitudes_gestion
                        SET numero_consecutivo = :numero, codigo = :codigo
                        WHERE id = :id
                        """
                    ),
                    {"numero": numero, "codigo": codigo, "id": solicitud_id},
                )

        if not _indice_existe("solicitudes_gestion", "uq_sg_tipo_numero_consecutivo"):
            logger.info(
                "Creando índice único uq_sg_tipo_numero_consecutivo en solicitudes_gestion..."
            )
            conn.execute(
                text(
                    "ALTER TABLE solicitudes_gestion "
                    "ADD UNIQUE KEY uq_sg_tipo_numero_consecutivo (tipo, numero_consecutivo)"
                )
            )


def migrar_visitas_programadas_servicios() -> None:
    """Tabla de visitas programadas por el gestor en solicitudes de servicios."""
    if _tabla_existe("solicitudes_gestion_visitas_programadas"):
        return
    with engine.begin() as conn:
        logger.info("Creando tabla solicitudes_gestion_visitas_programadas...")
        conn.execute(
            text(
                """
                CREATE TABLE solicitudes_gestion_visitas_programadas (
                    id                  INT          NOT NULL AUTO_INCREMENT,
                    solicitud_id        INT          NOT NULL,
                    programador_visita  VARCHAR(255) NOT NULL DEFAULT '',
                    proveedor_visita    VARCHAR(500) NOT NULL DEFAULT '',
                    fecha_visita        DATE         NULL,
                    hora_visita         TIME         NULL,
                    created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    KEY ix_sg_visita_solicitud_id (solicitud_id),
                    CONSTRAINT fk_sg_visita_solicitud
                        FOREIGN KEY (solicitud_id)
                        REFERENCES solicitudes_gestion (id)
                        ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
        )


def run_all() -> None:
    migrar_codigo_contratos()
    migrar_tipo_codigo_contratos()
    migrar_estado_contratos()
    migrar_subido_por_archivos()
    migrar_aprobacion_y_vigencia_contratos()
    migrar_fechas_contratos_activos()
    migrar_eliminacion_logica_contratos()
    migrar_aprobacion_otrosies()
    migrar_solicitudes_gestion_legacy()
    migrar_solicitudes_gestion_gestion()
    migrar_observaciones_trazabilidad()
    migrar_archivos_observacion()
    migrar_productos_estado_aprobacion()
    migrar_productos_cantidad()
    migrar_tramite_oc()
    migrar_users_email()
    migrar_users_lider_catalog_id()
    migrar_solicitudes_creado_por_email()
    migrar_productos_cantidad_entregada()
    migrar_valor_tramite_oc()
    migrar_estado_tramitando_oc()
    migrar_numero_tramite_oc_desde_historial()
    migrar_campos_anticipo()
    migrar_productos_cantidad_recibida()
    migrar_estados_flujo_recepcion()
    migrar_factura_solicitud()
    migrar_estado_facturada_existentes()
    migrar_tipo_salidas_almacen()
    migrar_area_consumo_producto()
    migrar_campos_solicitud_servicios()
    migrar_numero_consecutivo_solicitudes()
    migrar_visitas_programadas_servicios()
    migrar_anticipo_gestionado_servicios()


def migrar_anticipo_gestionado_servicios() -> None:
    """Marca anticipo gestionado y habilita cierre con evidencia en servicios."""
    if not _tabla_existe("solicitudes_gestion"):
        return
    if not _columna_existe("solicitudes_gestion", "anticipo_gestionado"):
        with engine.begin() as conn:
            logger.info("Agregando columna 'anticipo_gestionado' a solicitudes_gestion...")
            conn.execute(
                text(
                    """
                    ALTER TABLE solicitudes_gestion
                    ADD COLUMN anticipo_gestionado TINYINT(1) NOT NULL DEFAULT 0
                    AFTER gestor_anticipo_id
                    """
                )
            )
    if not _tabla_existe("solicitudes_gestion_historial_estados"):
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE solicitudes_gestion sg
                SET anticipo_gestionado = 1
                WHERE sg.tipo = 'insumos_servicios'
                  AND sg.anticipo_gestionado = 0
                  AND EXISTS (
                    SELECT 1 FROM solicitudes_gestion_historial_estados h
                    WHERE h.solicitud_id = sg.id
                      AND h.etapa = 'gestion_anticipo'
                  )
                """
            )
        )


def migrar_area_consumo_producto() -> None:
    """Área de consumo por ítem (salidas de almacén)."""
    if not _tabla_existe("solicitudes_gestion_productos"):
        return
    if _columna_existe("solicitudes_gestion_productos", "area_consumo"):
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                ALTER TABLE solicitudes_gestion_productos
                ADD COLUMN area_consumo VARCHAR(100) NOT NULL DEFAULT ''
                AFTER descripcion
                """
            )
        )
    logger.info("Columna area_consumo agregada a solicitudes_gestion_productos.")


def migrar_tipo_salidas_almacen() -> None:
    """Renombra el tipo legacy traslado_bodegas a salidas_almacen."""
    if not _tabla_existe("solicitudes_gestion"):
        return
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                UPDATE solicitudes_gestion
                SET tipo = 'salidas_almacen'
                WHERE tipo = 'traslado_bodegas'
                """
            )
        )
        if result.rowcount:
            logger.info(
                "Migradas %s solicitud(es) de traslado_bodegas a salidas_almacen.",
                result.rowcount,
            )


def migrar_estado_facturada_existentes() -> None:
    """Solicitudes con factura registrada pasan al estado interno Facturada."""
    if not _tabla_existe("solicitudes_gestion"):
        return
    if not _columna_existe("solicitudes_gestion", "factura_registrada_at"):
        return
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                UPDATE solicitudes_gestion
                SET estado = 'facturada'
                WHERE factura_registrada_at IS NOT NULL
                  AND estado = 'entregado'
                """
            )
        )
        if result.rowcount:
            logger.info(
                "Migradas %s solicitud(es) con factura al estado facturada.",
                result.rowcount,
            )


def migrar_factura_solicitud() -> None:
    """Cierre administrativo interno: factura registrada por Compras."""
    if not _tabla_existe("solicitudes_gestion"):
        return
    columnas = {
        "factura_registrada_at": (
            "ALTER TABLE solicitudes_gestion "
            "ADD COLUMN factura_registrada_at DATETIME NULL "
            "AFTER gestor_anticipo_id"
        ),
        "factura_registrada_por_id": (
            "ALTER TABLE solicitudes_gestion "
            "ADD COLUMN factura_registrada_por_id INT NULL "
            "AFTER factura_registrada_at"
        ),
    }
    with engine.begin() as conn:
        for columna, ddl in columnas.items():
            if not _columna_existe("solicitudes_gestion", columna):
                logger.info("Agregando columna '%s' a solicitudes_gestion...", columna)
                conn.execute(text(ddl))
        if _columna_existe("solicitudes_gestion", "factura_registrada_por_id"):
            try:
                conn.execute(
                    text(
                        "ALTER TABLE solicitudes_gestion "
                        "ADD CONSTRAINT fk_sg_factura_registrada_por "
                        "FOREIGN KEY (factura_registrada_por_id) "
                        "REFERENCES users (id) ON DELETE SET NULL"
                    )
                )
            except Exception as e:
                logger.debug("FK factura_registrada_por_id ya existe o no aplicable: %s", e)


def migrar_campos_anticipo() -> None:
    """Campos de anticipo en solicitudes de compra."""
    if not _tabla_existe("solicitudes_gestion"):
        return
    columnas = {
        "requiere_anticipo": (
            "ALTER TABLE solicitudes_gestion "
            "ADD COLUMN requiere_anticipo TINYINT(1) NOT NULL DEFAULT 0 "
            "AFTER lider_segunda_aprobacion_label"
        ),
        "porcentaje_anticipo": (
            "ALTER TABLE solicitudes_gestion "
            "ADD COLUMN porcentaje_anticipo DECIMAL(5,2) NULL "
            "AFTER requiere_anticipo"
        ),
        "lider_anticipo_id": (
            "ALTER TABLE solicitudes_gestion "
            "ADD COLUMN lider_anticipo_id VARCHAR(50) NOT NULL DEFAULT '' "
            "AFTER porcentaje_anticipo"
        ),
        "lider_anticipo_label": (
            "ALTER TABLE solicitudes_gestion "
            "ADD COLUMN lider_anticipo_label VARCHAR(500) NOT NULL DEFAULT '' "
            "AFTER lider_anticipo_id"
        ),
        "monto_anticipo": (
            "ALTER TABLE solicitudes_gestion "
            "ADD COLUMN monto_anticipo DECIMAL(18,2) NULL "
            "AFTER lider_anticipo_label"
        ),
        "observaciones_anticipo": (
            "ALTER TABLE solicitudes_gestion "
            "ADD COLUMN observaciones_anticipo TEXT NOT NULL "
            "AFTER monto_anticipo"
        ),
        "gestor_anticipo_id": (
            "ALTER TABLE solicitudes_gestion "
            "ADD COLUMN gestor_anticipo_id INT NULL "
            "AFTER observaciones_anticipo"
        ),
    }
    with engine.begin() as conn:
        for col, ddl in columnas.items():
            if not _columna_existe("solicitudes_gestion", col):
                logger.info("Agregando columna '%s' a solicitudes_gestion...", col)
                conn.execute(text(ddl))
        if not _indice_existe("solicitudes_gestion", "ix_solicitudes_gestion_gestor_anticipo_id"):
            try:
                conn.execute(
                    text(
                        "ALTER TABLE solicitudes_gestion "
                        "ADD INDEX ix_solicitudes_gestion_gestor_anticipo_id (gestor_anticipo_id)"
                    )
                )
            except Exception as e:
                logger.warning("No se pudo crear índice gestor_anticipo_id: %s", e)


def migrar_productos_cantidad_recibida() -> None:
    """Cantidad físicamente recibida por ítem en Compras."""
    if not _tabla_existe("solicitudes_gestion_productos"):
        return
    if not _columna_existe("solicitudes_gestion_productos", "cantidad_recibida"):
        with engine.begin() as conn:
            logger.info(
                "Agregando columna 'cantidad_recibida' a solicitudes_gestion_productos..."
            )
            conn.execute(
                text(
                    "ALTER TABLE solicitudes_gestion_productos "
                    "ADD COLUMN cantidad_recibida DECIMAL(18,4) NOT NULL DEFAULT 0.0000 "
                    "AFTER cantidad_entregada"
                )
            )


def migrar_estados_flujo_recepcion() -> None:
    """Solicitudes en Tramitada OC pasan a Ítems en camino (nuevo flujo post-OC)."""
    if not _tabla_existe("solicitudes_gestion"):
        return
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                UPDATE solicitudes_gestion
                SET estado = 'items_en_camino'
                WHERE estado IN ('tramitada_oc', 'en_proceso', 'pendiente')
                """
            )
        )
        if result.rowcount:
            logger.info(
                "Migradas %s solicitud(es) de tramitada_oc a items_en_camino.",
                result.rowcount,
            )


def migrar_numero_tramite_oc_desde_historial() -> None:
    """Recupera numero_tramite_oc borrado por update() posterior al guardar trámite OC."""
    if not _tabla_existe("solicitudes_gestion") or not _tabla_existe(
        "solicitudes_gestion_historial_estados"
    ):
        return
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                UPDATE solicitudes_gestion s
                INNER JOIN solicitudes_gestion_historial_estados h
                    ON h.solicitud_id = s.id
                SET s.numero_tramite_oc = TRIM(
                    SUBSTRING_INDEX(
                        SUBSTRING_INDEX(h.comentario, 'Trámite OC general: ', -1),
                        ' (',
                        1
                    )
                )
                WHERE TRIM(COALESCE(s.numero_tramite_oc, '')) = ''
                  AND h.comentario LIKE '%Trámite OC general:%'
                  AND TRIM(
                    SUBSTRING_INDEX(
                        SUBSTRING_INDEX(h.comentario, 'Trámite OC general: ', -1),
                        ' (',
                        1
                    )
                  ) <> ''
                """
            )
        )
        if result.rowcount:
            logger.info(
                "Recuperado numero_tramite_oc en %s solicitud(es) desde historial.",
                result.rowcount,
            )


def migrar_valor_tramite_oc() -> None:
    """Valor monetario asociado al trámite OC (general y por ítem)."""
    if _tabla_existe("solicitudes_gestion") and not _columna_existe(
        "solicitudes_gestion", "valor_tramite_oc"
    ):
        with engine.begin() as conn:
            logger.info("Agregando columna 'valor_tramite_oc' a solicitudes_gestion...")
            conn.execute(
                text(
                    "ALTER TABLE solicitudes_gestion "
                    "ADD COLUMN valor_tramite_oc DECIMAL(18,2) NULL "
                    "AFTER numero_tramite_oc"
                )
            )
    if _tabla_existe("solicitudes_gestion_productos") and not _columna_existe(
        "solicitudes_gestion_productos", "valor_tramite_oc"
    ):
        with engine.begin() as conn:
            logger.info(
                "Agregando columna 'valor_tramite_oc' a solicitudes_gestion_productos..."
            )
            conn.execute(
                text(
                    "ALTER TABLE solicitudes_gestion_productos "
                    "ADD COLUMN valor_tramite_oc DECIMAL(18,2) NULL "
                    "AFTER numero_tramite_oc"
                )
            )


def migrar_estado_tramitando_oc() -> None:
    """Solicitudes en Tramitada OC sin OC registrada pasan a Tramitando OC."""
    if not _tabla_existe("solicitudes_gestion"):
        return
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                UPDATE solicitudes_gestion s
                SET s.estado = 'tramitando_oc'
                WHERE s.estado = 'tramitada_oc'
                  AND TRIM(COALESCE(s.numero_tramite_oc, '')) = ''
                  AND NOT EXISTS (
                      SELECT 1
                      FROM solicitudes_gestion_productos p
                      WHERE p.solicitud_id = s.id
                        AND TRIM(COALESCE(p.numero_tramite_oc, '')) <> ''
                  )
                """
            )
        )
        if result.rowcount:
            logger.info(
                "Corregidas %s solicitud(es) de tramitada_oc a tramitando_oc (sin OC registrada).",
                result.rowcount,
            )

        if _tabla_existe("solicitudes_gestion_historial_estados"):
            hist = conn.execute(
                text(
                    """
                    UPDATE solicitudes_gestion_historial_estados h
                    INNER JOIN (
                        SELECT solicitud_id, MAX(id) AS max_id
                        FROM solicitudes_gestion_historial_estados
                        GROUP BY solicitud_id
                    ) ult ON h.id = ult.max_id
                    INNER JOIN solicitudes_gestion s ON s.id = h.solicitud_id
                    SET h.etapa = 'tramitando_oc'
                    WHERE s.estado = 'tramitando_oc'
                      AND h.etapa = 'tramitada_oc'
                    """
                )
            )
            if hist.rowcount:
                logger.info(
                    "Alineado historial en %s solicitud(es) con estado tramitando_oc.",
                    hist.rowcount,
                )


def migrar_productos_cantidad_entregada() -> None:
    """Cantidad ya entregada por ítem (entrega parcial)."""
    if not _tabla_existe("solicitudes_gestion_productos"):
        return
    if not _columna_existe("solicitudes_gestion_productos", "cantidad_entregada"):
        with engine.begin() as conn:
            logger.info(
                "Agregando columna 'cantidad_entregada' a solicitudes_gestion_productos..."
            )
            conn.execute(
                text(
                    "ALTER TABLE solicitudes_gestion_productos "
                    "ADD COLUMN cantidad_entregada DECIMAL(18,4) NOT NULL DEFAULT 0.0000 "
                    "AFTER cantidad"
                )
            )


def migrar_users_email() -> None:
    """Correo opcional del usuario para notificaciones."""
    if not _tabla_existe("users"):
        return
    if not _columna_existe("users", "email"):
        with engine.begin() as conn:
            logger.info("Agregando columna 'email' a users...")
            conn.execute(
                text(
                    "ALTER TABLE users "
                    "ADD COLUMN email VARCHAR(255) NOT NULL DEFAULT '' AFTER role"
                )
            )


def migrar_users_lider_catalog_id() -> None:
    """Identificador del catálogo de líderes para rol Líder Aprobador."""
    if not _tabla_existe("users"):
        return
    if not _columna_existe("users", "lider_catalog_id"):
        with engine.begin() as conn:
            logger.info("Agregando columna 'lider_catalog_id' a users...")
            conn.execute(
                text(
                    "ALTER TABLE users "
                    "ADD COLUMN lider_catalog_id VARCHAR(50) NOT NULL DEFAULT '' "
                    "AFTER email"
                )
            )


def migrar_solicitudes_creado_por_email() -> None:
    """Correo del solicitante al momento de crear la solicitud."""
    if not _tabla_existe("solicitudes_gestion"):
        return
    if not _columna_existe("solicitudes_gestion", "creado_por_email"):
        with engine.begin() as conn:
            logger.info("Agregando columna 'creado_por_email' a solicitudes_gestion...")
            conn.execute(
                text(
                    "ALTER TABLE solicitudes_gestion "
                    "ADD COLUMN creado_por_email VARCHAR(255) NOT NULL DEFAULT '' "
                    "AFTER creado_por_id"
                )
            )
            if _columna_existe("users", "email"):
                conn.execute(
                    text(
                        "UPDATE solicitudes_gestion sg "
                        "INNER JOIN users u ON u.id = sg.creado_por_id "
                        "SET sg.creado_por_email = u.email "
                        "WHERE u.email IS NOT NULL AND u.email <> ''"
                    )
                )


def migrar_tramite_oc() -> None:
    """Número de trámite OC general y parcial por ítem."""
    if _tabla_existe("solicitudes_gestion") and not _columna_existe(
        "solicitudes_gestion", "numero_tramite_oc"
    ):
        with engine.begin() as conn:
            logger.info("Agregando columna 'numero_tramite_oc' a solicitudes_gestion...")
            conn.execute(
                text(
                    "ALTER TABLE solicitudes_gestion "
                    "ADD COLUMN numero_tramite_oc VARCHAR(100) NOT NULL DEFAULT '' "
                    "AFTER justificacion_cotizaciones"
                )
            )
    if _tabla_existe("solicitudes_gestion_productos") and not _columna_existe(
        "solicitudes_gestion_productos", "numero_tramite_oc"
    ):
        with engine.begin() as conn:
            logger.info(
                "Agregando columna 'numero_tramite_oc' a solicitudes_gestion_productos..."
            )
            conn.execute(
                text(
                    "ALTER TABLE solicitudes_gestion_productos "
                    "ADD COLUMN numero_tramite_oc VARCHAR(100) NOT NULL DEFAULT '' "
                    "AFTER estado_aprobacion"
                )
            )


def migrar_productos_cantidad() -> None:
    """Cantidad por ítem en el detalle de la compra."""
    if not _tabla_existe("solicitudes_gestion_productos"):
        return
    if not _columna_existe("solicitudes_gestion_productos", "cantidad"):
        with engine.begin() as conn:
            logger.info(
                "Agregando columna 'cantidad' a solicitudes_gestion_productos..."
            )
            conn.execute(
                text(
                    "ALTER TABLE solicitudes_gestion_productos "
                    "ADD COLUMN cantidad DECIMAL(18,4) NOT NULL DEFAULT 1.0000 "
                    "AFTER centro_costo"
                )
            )


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
