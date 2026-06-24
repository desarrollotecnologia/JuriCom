-- =========================================================================
-- JuriCom / Juridica — Migración de esquema y datos a otra base de datos
-- =========================================================================
-- Uso típico (mismo servidor MySQL):
--   1. Edita @db_origen y @db_destino (abajo) con los nombres reales.
--   2. Ejecuta TODO el script con un usuario con permisos (root o DBA).
--
-- Uso en otro servidor:
--   1. Ejecuta solo la PARTE A (esquema) en la BD destino.
--   2. En el servidor origen genera un dump de datos:
--        mysqldump -u USUARIO -p --no-create-info --complete-insert Juridica > datos.sql
--   3. Importa datos.sql en la BD destino.
--
-- Orden de copia respeta claves foráneas (usuarios → contratos → solicitudes…).
-- =========================================================================

SET NAMES utf8mb4;
SET @db_origen  := 'Juridica';          -- ← BD actual (origen)
SET @db_destino := 'Juridica_destino';  -- ← BD nueva (destino)

-- =========================================================================
-- PARTE A — Crear BD destino y esquema completo (estado actual del sistema)
-- =========================================================================

SET @sql := CONCAT(
    'CREATE DATABASE IF NOT EXISTS `', @db_destino, '` ',
    'CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := CONCAT('USE `', @db_destino, '`');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET FOREIGN_KEY_CHECKS = 0;

-- -------------------------------------------------------------------------
-- users
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              INT          NOT NULL AUTO_INCREMENT,
    username        VARCHAR(100) NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20)  NOT NULL COMMENT 'admin | juridica | compras',
    email           VARCHAR(255) NOT NULL DEFAULT '',
    is_active       TINYINT(1)   NOT NULL DEFAULT 1,
    created_by_id   INT          NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                  ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_username (username),
    KEY ix_users_username (username),
    CONSTRAINT fk_users_created_by
        FOREIGN KEY (created_by_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- contratos
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS contratos (
    id                                  INT            NOT NULL AUTO_INCREMENT,
    codigo                              VARCHAR(20)    NOT NULL,
    compania                            VARCHAR(150)   NOT NULL DEFAULT 'Colbeef',
    proveedor_contratista               VARCHAR(255)   NOT NULL,
    nit_proveedor                       VARCHAR(50)    NOT NULL,
    descripcion_servicio                TEXT           NOT NULL,
    obligaciones_colbeef                TEXT           NOT NULL,
    obligaciones_proveedor              TEXT           NOT NULL,
    valor                               DECIMAL(18,2)  NOT NULL,
    moneda                              VARCHAR(3)     NOT NULL,
    plazo_cantidad                      INT            NOT NULL,
    plazo_unidad                        VARCHAR(10)    NOT NULL,
    renovacion_automatica               TINYINT(1)     NOT NULL DEFAULT 0,
    condiciones_recibido_satisfactorio  TEXT           NOT NULL,
    requiere_poliza                     TINYINT(1)     NOT NULL DEFAULT 0,
    correo_lider_proceso                VARCHAR(255)   NOT NULL DEFAULT '',
    correo_gerencia                     VARCHAR(255)   NOT NULL DEFAULT '',
    estado_aprobacion                   VARCHAR(30)    NOT NULL DEFAULT 'pendiente_lider',
    estado                              VARCHAR(20)    NOT NULL DEFAULT 'en_proceso',
    fecha_inicio                        DATE           NULL,
    fecha_fin                           DATE           NULL,
    fecha_proxima_notificacion          DATE           NULL,
    aprobado_lider_at                   DATETIME       NULL,
    aprobado_gerencia_at                DATETIME       NULL,
    creado_por_id                       INT            NOT NULL,
    created_at                          DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                          DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP
                                                       ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_contratos_codigo (codigo),
    KEY ix_contratos_codigo (codigo),
    KEY ix_contratos_nit_proveedor (nit_proveedor),
    KEY ix_contratos_estado_aprobacion (estado_aprobacion),
    KEY ix_contratos_estado (estado),
    CONSTRAINT fk_contratos_creado_por
        FOREIGN KEY (creado_por_id) REFERENCES users (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- archivos_contrato
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS archivos_contrato (
    id                   INT          NOT NULL AUTO_INCREMENT,
    contrato_id          INT          NOT NULL,
    tipo                 VARCHAR(40)  NOT NULL,
    nombre_original      VARCHAR(255) NOT NULL,
    ruta_almacenamiento  VARCHAR(500) NOT NULL,
    mime_type            VARCHAR(100) NOT NULL,
    tamano_bytes         BIGINT       NOT NULL,
    subido_por_id        INT          NULL,
    created_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_archivos_contrato_contrato_id (contrato_id),
    CONSTRAINT fk_archivos_contrato
        FOREIGN KEY (contrato_id) REFERENCES contratos (id) ON DELETE CASCADE,
    CONSTRAINT fk_archivos_subido_por
        FOREIGN KEY (subido_por_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- otrosies_contrato
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS otrosies_contrato (
    id                       INT            NOT NULL AUTO_INCREMENT,
    contrato_id              INT            NOT NULL,
    numero                   INT            NOT NULL,
    tipo                     VARCHAR(20)    NOT NULL,
    descripcion              TEXT           NOT NULL,
    plazo_adicional_cantidad INT            NULL,
    plazo_adicional_unidad   VARCHAR(10)    NULL,
    valor_adicional          DECIMAL(18,2)  NULL,
    nueva_descripcion_servicio TEXT         NULL,
    archivo_id               INT            NULL,
    estado_aprobacion        VARCHAR(30)    NOT NULL DEFAULT 'aprobado',
    aprobado_lider_at        DATETIME       NULL,
    aprobado_gerencia_at     DATETIME       NULL,
    creado_por_id            INT            NOT NULL,
    created_at               DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_otrosies_contrato_contrato_id (contrato_id),
    KEY ix_otrosies_estado_aprobacion (estado_aprobacion),
    CONSTRAINT fk_otrosies_contrato
        FOREIGN KEY (contrato_id) REFERENCES contratos (id) ON DELETE CASCADE,
    CONSTRAINT fk_otrosies_archivo
        FOREIGN KEY (archivo_id) REFERENCES archivos_contrato (id) ON DELETE SET NULL,
    CONSTRAINT fk_otrosies_creado_por
        FOREIGN KEY (creado_por_id) REFERENCES users (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- solicitudes_gestion
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS solicitudes_gestion (
    id                              INT          NOT NULL AUTO_INCREMENT,
    codigo                          VARCHAR(20)  NOT NULL,
    tipo                            VARCHAR(30)  NOT NULL,
    titulo                          VARCHAR(500) NOT NULL,
    presupuestado                   TINYINT(1)   NULL,
    centro_costo_area               VARCHAR(100) NOT NULL DEFAULT '',
    lider_area_id                   VARCHAR(50)  NOT NULL DEFAULT '',
    lider_area_label                VARCHAR(500) NOT NULL DEFAULT '',
    lider_segunda_aprobacion_id     VARCHAR(50)  NOT NULL DEFAULT '',
    lider_segunda_aprobacion_label  VARCHAR(500) NOT NULL DEFAULT '',
    observaciones                   TEXT         NOT NULL,
    observaciones_texto             TEXT         NOT NULL,
    observaciones_gestion           TEXT         NOT NULL,
    justificacion_cotizaciones      TEXT         NOT NULL,
    numero_tramite_oc               VARCHAR(100) NOT NULL DEFAULT '',
    gestor_id                       INT          NULL,
    estado                          VARCHAR(30)  NOT NULL DEFAULT 'solicitud',
    creado_por_id                   INT          NOT NULL,
    creado_por_email                VARCHAR(255) NOT NULL DEFAULT '',
    created_at                      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                                    ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_solicitudes_gestion_codigo (codigo),
    KEY ix_solicitudes_gestion_codigo (codigo),
    KEY ix_solicitudes_gestion_tipo (tipo),
    KEY ix_solicitudes_gestion_estado (estado),
    KEY ix_solicitudes_gestion_gestor_id (gestor_id),
    KEY ix_solicitudes_gestion_creado_por_id (creado_por_id),
    CONSTRAINT fk_sg_gestor
        FOREIGN KEY (gestor_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT fk_sg_creado_por
        FOREIGN KEY (creado_por_id) REFERENCES users (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- solicitudes_gestion_historial_estados
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS solicitudes_gestion_historial_estados (
    id           INT         NOT NULL AUTO_INCREMENT,
    solicitud_id INT         NOT NULL,
    etapa        VARCHAR(40) NOT NULL,
    usuario_id   INT         NULL,
    comentario   TEXT        NOT NULL,
    created_at   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_sg_hist_solicitud_id (solicitud_id),
    CONSTRAINT fk_sg_hist_solicitud
        FOREIGN KEY (solicitud_id) REFERENCES solicitudes_gestion (id) ON DELETE CASCADE,
    CONSTRAINT fk_sg_hist_usuario
        FOREIGN KEY (usuario_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- solicitudes_gestion_productos
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS solicitudes_gestion_productos (
    id                INT           NOT NULL AUTO_INCREMENT,
    solicitud_id      INT           NOT NULL,
    codigo_siimed     VARCHAR(80)   NOT NULL DEFAULT '',
    unidad            VARCHAR(20)   NOT NULL,
    descripcion       TEXT          NOT NULL,
    centro_costo      VARCHAR(100)  NOT NULL,
    cantidad          DECIMAL(18,4) NOT NULL DEFAULT 1.0000,
    cantidad_entregada DECIMAL(18,4) NOT NULL DEFAULT 0.0000,
    estado_aprobacion VARCHAR(20)   NOT NULL DEFAULT 'pendiente',
    numero_tramite_oc VARCHAR(100)  NOT NULL DEFAULT '',
    PRIMARY KEY (id),
    KEY ix_sg_prod_solicitud_id (solicitud_id),
    CONSTRAINT fk_sg_prod_solicitud
        FOREIGN KEY (solicitud_id) REFERENCES solicitudes_gestion (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- solicitudes_gestion_observaciones
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS solicitudes_gestion_observaciones (
    id              INT          NOT NULL AUTO_INCREMENT,
    solicitud_id    INT          NOT NULL,
    usuario_id      INT          NULL,
    autor_nombre    VARCHAR(150) NOT NULL DEFAULT '',
    autor_rol       VARCHAR(80)  NOT NULL DEFAULT '',
    contenido       TEXT         NOT NULL,
    contenido_texto TEXT         NOT NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_sg_obs_solicitud_id (solicitud_id),
    CONSTRAINT fk_sg_obs_solicitud
        FOREIGN KEY (solicitud_id) REFERENCES solicitudes_gestion (id) ON DELETE CASCADE,
    CONSTRAINT fk_sg_obs_usuario
        FOREIGN KEY (usuario_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- solicitudes_gestion_archivos
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS solicitudes_gestion_archivos (
    id                  INT          NOT NULL AUTO_INCREMENT,
    solicitud_id        INT          NOT NULL,
    nombre_original     VARCHAR(255) NOT NULL,
    ruta_almacenamiento VARCHAR(500) NOT NULL,
    mime_type           VARCHAR(100) NOT NULL,
    tamano_bytes        BIGINT       NOT NULL,
    categoria           VARCHAR(30)  NOT NULL DEFAULT 'solicitud',
    observacion_id      INT          NULL,
    subido_por_id       INT          NULL,
    created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_sg_arch_solicitud_id (solicitud_id),
    KEY ix_sg_arch_observacion_id (observacion_id),
    CONSTRAINT fk_sg_arch_solicitud
        FOREIGN KEY (solicitud_id) REFERENCES solicitudes_gestion (id) ON DELETE CASCADE,
    CONSTRAINT fk_sg_arch_observacion
        FOREIGN KEY (observacion_id) REFERENCES solicitudes_gestion_observaciones (id) ON DELETE SET NULL,
    CONSTRAINT fk_sg_arch_subido_por
        FOREIGN KEY (subido_por_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- =========================================================================
-- PARTE B — Copiar datos del origen al destino (mismo servidor MySQL)
-- =========================================================================
-- Si la BD destino ya tiene datos, descomenta el TRUNCATE de abajo primero
-- (solo en destino, nunca en origen).
-- =========================================================================

SET FOREIGN_KEY_CHECKS = 0;

-- TRUNCATE TABLE Juridica_destino.solicitudes_gestion_archivos;
-- TRUNCATE TABLE Juridica_destino.solicitudes_gestion_observaciones;
-- TRUNCATE TABLE Juridica_destino.solicitudes_gestion_productos;
-- TRUNCATE TABLE Juridica_destino.solicitudes_gestion_historial_estados;
-- TRUNCATE TABLE Juridica_destino.solicitudes_gestion;
-- TRUNCATE TABLE Juridica_destino.otrosies_contrato;
-- TRUNCATE TABLE Juridica_destino.archivos_contrato;
-- TRUNCATE TABLE Juridica_destino.contratos;
-- TRUNCATE TABLE Juridica_destino.users;

SET @sql := CONCAT(
    'INSERT INTO `', @db_destino, '`.users ',
    'SELECT * FROM `', @db_origen, '`.users'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql := CONCAT(
    'INSERT INTO `', @db_destino, '`.contratos ',
    'SELECT * FROM `', @db_origen, '`.contratos'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql := CONCAT(
    'INSERT INTO `', @db_destino, '`.archivos_contrato ',
    'SELECT * FROM `', @db_origen, '`.archivos_contrato'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql := CONCAT(
    'INSERT INTO `', @db_destino, '`.otrosies_contrato ',
    'SELECT * FROM `', @db_origen, '`.otrosies_contrato'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql := CONCAT(
    'INSERT INTO `', @db_destino, '`.solicitudes_gestion ',
    'SELECT * FROM `', @db_origen, '`.solicitudes_gestion'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql := CONCAT(
    'INSERT INTO `', @db_destino, '`.solicitudes_gestion_historial_estados ',
    'SELECT * FROM `', @db_origen, '`.solicitudes_gestion_historial_estados'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql := CONCAT(
    'INSERT INTO `', @db_destino, '`.solicitudes_gestion_productos ',
    'SELECT * FROM `', @db_origen, '`.solicitudes_gestion_productos'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql := CONCAT(
    'INSERT INTO `', @db_destino, '`.solicitudes_gestion_observaciones ',
    'SELECT * FROM `', @db_origen, '`.solicitudes_gestion_observaciones'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql := CONCAT(
    'INSERT INTO `', @db_destino, '`.solicitudes_gestion_archivos ',
    'SELECT * FROM `', @db_origen, '`.solicitudes_gestion_archivos'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET FOREIGN_KEY_CHECKS = 1;

-- =========================================================================
-- PARTE C — Verificación (conteo origen vs destino)
-- =========================================================================

DROP TEMPORARY TABLE IF EXISTS _migrate_check;
CREATE TEMPORARY TABLE _migrate_check (
    tabla   VARCHAR(80) NOT NULL,
    origen  BIGINT      NOT NULL DEFAULT 0,
    destino BIGINT      NOT NULL DEFAULT 0
);

-- users
SET @sql := CONCAT('SELECT COUNT(*) INTO @cnt FROM `', @db_origen, '`.users');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SET @orig := @cnt;
SET @sql := CONCAT('SELECT COUNT(*) INTO @cnt FROM `', @db_destino, '`.users');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
INSERT INTO _migrate_check VALUES ('users', @orig, @cnt);

-- contratos
SET @sql := CONCAT('SELECT COUNT(*) INTO @cnt FROM `', @db_origen, '`.contratos');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SET @orig := @cnt;
SET @sql := CONCAT('SELECT COUNT(*) INTO @cnt FROM `', @db_destino, '`.contratos');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
INSERT INTO _migrate_check VALUES ('contratos', @orig, @cnt);

-- archivos_contrato
SET @sql := CONCAT('SELECT COUNT(*) INTO @cnt FROM `', @db_origen, '`.archivos_contrato');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SET @orig := @cnt;
SET @sql := CONCAT('SELECT COUNT(*) INTO @cnt FROM `', @db_destino, '`.archivos_contrato');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
INSERT INTO _migrate_check VALUES ('archivos_contrato', @orig, @cnt);

-- otrosies_contrato
SET @sql := CONCAT('SELECT COUNT(*) INTO @cnt FROM `', @db_origen, '`.otrosies_contrato');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SET @orig := @cnt;
SET @sql := CONCAT('SELECT COUNT(*) INTO @cnt FROM `', @db_destino, '`.otrosies_contrato');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
INSERT INTO _migrate_check VALUES ('otrosies_contrato', @orig, @cnt);

-- solicitudes_gestion
SET @sql := CONCAT('SELECT COUNT(*) INTO @cnt FROM `', @db_origen, '`.solicitudes_gestion');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SET @orig := @cnt;
SET @sql := CONCAT('SELECT COUNT(*) INTO @cnt FROM `', @db_destino, '`.solicitudes_gestion');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
INSERT INTO _migrate_check VALUES ('solicitudes_gestion', @orig, @cnt);

-- solicitudes_gestion_historial_estados
SET @sql := CONCAT('SELECT COUNT(*) INTO @cnt FROM `', @db_origen, '`.solicitudes_gestion_historial_estados');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SET @orig := @cnt;
SET @sql := CONCAT('SELECT COUNT(*) INTO @cnt FROM `', @db_destino, '`.solicitudes_gestion_historial_estados');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
INSERT INTO _migrate_check VALUES ('solicitudes_gestion_historial_estados', @orig, @cnt);

-- solicitudes_gestion_productos
SET @sql := CONCAT('SELECT COUNT(*) INTO @cnt FROM `', @db_origen, '`.solicitudes_gestion_productos');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SET @orig := @cnt;
SET @sql := CONCAT('SELECT COUNT(*) INTO @cnt FROM `', @db_destino, '`.solicitudes_gestion_productos');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
INSERT INTO _migrate_check VALUES ('solicitudes_gestion_productos', @orig, @cnt);

-- solicitudes_gestion_observaciones
SET @sql := CONCAT('SELECT COUNT(*) INTO @cnt FROM `', @db_origen, '`.solicitudes_gestion_observaciones');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SET @orig := @cnt;
SET @sql := CONCAT('SELECT COUNT(*) INTO @cnt FROM `', @db_destino, '`.solicitudes_gestion_observaciones');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
INSERT INTO _migrate_check VALUES ('solicitudes_gestion_observaciones', @orig, @cnt);

-- solicitudes_gestion_archivos
SET @sql := CONCAT('SELECT COUNT(*) INTO @cnt FROM `', @db_origen, '`.solicitudes_gestion_archivos');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SET @orig := @cnt;
SET @sql := CONCAT('SELECT COUNT(*) INTO @cnt FROM `', @db_destino, '`.solicitudes_gestion_archivos');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
INSERT INTO _migrate_check VALUES ('solicitudes_gestion_archivos', @orig, @cnt);

SELECT * FROM _migrate_check ORDER BY tabla;
DROP TEMPORARY TABLE _migrate_check;

-- =========================================================================
-- NOTA: Los archivos PDF/imágenes en uploads/ NO están en MySQL.
-- Debes copiar manualmente las carpetas:
--   uploads/contratos/
--   uploads/solicitudes/
-- =========================================================================
