-- =========================================================
-- Esquema de la base de datos `Juridica` para Colbeef
-- =========================================================
-- Referencia del esquema actual (sincronizado con models.py).
-- La aplicación crea/actualiza tablas al arrancar:
--   Base.metadata.create_all() + migrations.run_all()
--
-- ADVERTENCIA: este script hace DROP TABLE. Solo usar en
-- instalación limpia o entorno de prueba.
-- Para BD existente use alter_columns.sql
-- =========================================================

-- CREATE DATABASE IF NOT EXISTS Juridica
--   CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE Juridica;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS solicitudes_gestion_archivos;
DROP TABLE IF EXISTS solicitudes_gestion_observaciones;
DROP TABLE IF EXISTS solicitudes_gestion_productos;
DROP TABLE IF EXISTS solicitudes_gestion_historial_estados;
DROP TABLE IF EXISTS solicitudes_gestion;
DROP TABLE IF EXISTS otrosies_contrato;
DROP TABLE IF EXISTS archivos_contrato;
DROP TABLE IF EXISTS contratos;
DROP TABLE IF EXISTS users;

-- ---------------------------------------------------------
-- Tabla: users
-- ---------------------------------------------------------
CREATE TABLE users (
    id              INT          NOT NULL AUTO_INCREMENT,
    username        VARCHAR(100) NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20)  NOT NULL,
    email           VARCHAR(255) NOT NULL DEFAULT '',
    is_active       TINYINT(1)   NOT NULL DEFAULT 1,
    created_by_id   INT          NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                  ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_username (username),
    KEY ix_users_role (role),
    CONSTRAINT fk_users_created_by
        FOREIGN KEY (created_by_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------
-- Tabla: contratos
-- ---------------------------------------------------------
CREATE TABLE contratos (
    id                                  INT            NOT NULL AUTO_INCREMENT,
    codigo                              VARCHAR(20)    NOT NULL,
    tipo_codigo                         VARCHAR(10)    NOT NULL DEFAULT 'C',
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
    hora_proxima_notificacion           TIME           NULL DEFAULT '00:10:00',
    fecha_ultima_notificacion_vencimiento DATETIME      NULL,
    aprobado_lider_at                   DATETIME       NULL,
    aprobado_gerencia_at                DATETIME       NULL,
    eliminado_at                        DATETIME       NULL,
    eliminado_por_id                    INT            NULL,
    eliminado_observacion               TEXT           NULL,
    creado_por_id                       INT            NOT NULL,
    created_at                          DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                          DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP
                                                       ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_contratos_codigo (codigo),
    KEY ix_contratos_nit_proveedor (nit_proveedor),
    KEY ix_contratos_creado_por (creado_por_id),
    KEY ix_contratos_estado (estado),
    KEY ix_contratos_estado_aprobacion (estado_aprobacion),
    KEY ix_contratos_eliminado_at (eliminado_at),
    CONSTRAINT fk_contratos_creado_por
        FOREIGN KEY (creado_por_id) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_contratos_eliminado_por
        FOREIGN KEY (eliminado_por_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------
-- Tabla: archivos_contrato
-- ---------------------------------------------------------
CREATE TABLE archivos_contrato (
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
    KEY ix_archivos_contrato_id (contrato_id),
    CONSTRAINT fk_archivos_contrato
        FOREIGN KEY (contrato_id) REFERENCES contratos (id) ON DELETE CASCADE,
    CONSTRAINT fk_archivos_subido_por
        FOREIGN KEY (subido_por_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------
-- Tabla: otrosies_contrato
-- ---------------------------------------------------------
CREATE TABLE otrosies_contrato (
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
    KEY ix_otrosies_contrato_id (contrato_id),
    KEY ix_otrosies_estado_aprobacion (estado_aprobacion),
    CONSTRAINT fk_otrosies_contrato
        FOREIGN KEY (contrato_id) REFERENCES contratos (id) ON DELETE CASCADE,
    CONSTRAINT fk_otrosies_archivo
        FOREIGN KEY (archivo_id) REFERENCES archivos_contrato (id) ON DELETE SET NULL,
    CONSTRAINT fk_otrosies_creado_por
        FOREIGN KEY (creado_por_id) REFERENCES users (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------
-- Tabla: solicitudes_gestion
-- ---------------------------------------------------------
CREATE TABLE solicitudes_gestion (
    id                              INT          NOT NULL AUTO_INCREMENT,
    codigo                          VARCHAR(20)  NOT NULL,
    tipo                            VARCHAR(30)  NOT NULL,
    numero_consecutivo              INT          NULL,
    titulo                          VARCHAR(500) NOT NULL,
    presupuestado                   TINYINT(1)   NULL,
    centro_costo_area               VARCHAR(100) NOT NULL DEFAULT '',
    lider_area_id                   VARCHAR(50)  NOT NULL DEFAULT '',
    lider_area_label                VARCHAR(500) NOT NULL DEFAULT '',
    observaciones                   TEXT         NOT NULL,
    observaciones_texto             TEXT         NOT NULL,
    observaciones_gestion           TEXT         NOT NULL,
    justificacion_cotizaciones      TEXT         NOT NULL,
    numero_tramite_oc               VARCHAR(100) NOT NULL DEFAULT '',
    gestor_id                       INT          NULL,
    lider_segunda_aprobacion_id     VARCHAR(50)  NOT NULL DEFAULT '',
    lider_segunda_aprobacion_label  VARCHAR(500) NOT NULL DEFAULT '',
    estado                          VARCHAR(30)  NOT NULL DEFAULT 'solicitud',
    creado_por_id                   INT          NOT NULL,
    creado_por_email                VARCHAR(255) NOT NULL DEFAULT '',
    created_at                      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                                   ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_solicitudes_gestion_codigo (codigo),
    UNIQUE KEY uq_sg_tipo_numero_consecutivo (tipo, numero_consecutivo),
    KEY ix_solicitudes_gestion_tipo (tipo),
    KEY ix_solicitudes_gestion_estado (estado),
    KEY ix_solicitudes_gestion_gestor_id (gestor_id),
    KEY ix_solicitudes_gestion_creado_por_id (creado_por_id),
    CONSTRAINT fk_sg_creado_por
        FOREIGN KEY (creado_por_id) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_sg_gestor
        FOREIGN KEY (gestor_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------
-- Tabla: solicitudes_gestion_historial_estados
-- ---------------------------------------------------------
CREATE TABLE solicitudes_gestion_historial_estados (
    id           INT          NOT NULL AUTO_INCREMENT,
    solicitud_id INT          NOT NULL,
    etapa        VARCHAR(40)  NOT NULL,
    usuario_id   INT          NULL,
    comentario   TEXT         NOT NULL,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_sg_hist_solicitud_id (solicitud_id),
    CONSTRAINT fk_sg_hist_solicitud
        FOREIGN KEY (solicitud_id) REFERENCES solicitudes_gestion (id) ON DELETE CASCADE,
    CONSTRAINT fk_sg_hist_usuario
        FOREIGN KEY (usuario_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------
-- Tabla: solicitudes_gestion_productos
-- ---------------------------------------------------------
CREATE TABLE solicitudes_gestion_productos (
    id                INT            NOT NULL AUTO_INCREMENT,
    solicitud_id      INT            NOT NULL,
    codigo_siimed     VARCHAR(80)    NOT NULL DEFAULT '',
    unidad            VARCHAR(20)    NOT NULL,
    descripcion       TEXT           NOT NULL,
    centro_costo      VARCHAR(100)   NOT NULL,
    cantidad          DECIMAL(18,4)  NOT NULL DEFAULT 1.0000,
    cantidad_entregada DECIMAL(18,4) NOT NULL DEFAULT 0.0000,
    estado_aprobacion VARCHAR(20)    NOT NULL DEFAULT 'pendiente',
    numero_tramite_oc VARCHAR(100)   NOT NULL DEFAULT '',
    PRIMARY KEY (id),
    KEY ix_sg_prod_solicitud_id (solicitud_id),
    CONSTRAINT fk_sg_prod_solicitud
        FOREIGN KEY (solicitud_id) REFERENCES solicitudes_gestion (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------
-- Tabla: solicitudes_gestion_observaciones
-- ---------------------------------------------------------
CREATE TABLE solicitudes_gestion_observaciones (
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

-- ---------------------------------------------------------
-- Tabla: solicitudes_gestion_archivos
-- ---------------------------------------------------------
CREATE TABLE solicitudes_gestion_archivos (
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
