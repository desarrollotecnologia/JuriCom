-- =========================================================
-- Esquema de la base de datos `Juridica` para Colbeef
-- =========================================================
-- Nota: la aplicación crea estas tablas automáticamente al
-- arrancar (vía SQLAlchemy `Base.metadata.create_all`).
-- Este archivo queda como respaldo / referencia.
-- =========================================================

-- Si todavía no existe la BD (en algunos entornos hay que crearla):
-- CREATE DATABASE IF NOT EXISTS Juridica
--   CHARACTER SET utf8mb4
--   COLLATE utf8mb4_unicode_ci;
-- USE Juridica;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------------------------------------
-- Tabla: users
-- ---------------------------------------------------------
DROP TABLE IF EXISTS archivos_contrato;
DROP TABLE IF EXISTS contratos;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id              INT          NOT NULL AUTO_INCREMENT,
    username        VARCHAR(100) NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20)  NOT NULL,  -- admin | juridica | compras
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
-- Tabla: contratos (Solicitud Radicar)
-- ---------------------------------------------------------
CREATE TABLE contratos (
    id                                  INT            NOT NULL AUTO_INCREMENT,
    compania                            VARCHAR(150)   NOT NULL DEFAULT 'Colbeef',
    proveedor_contratista               VARCHAR(255)   NOT NULL,
    nit_proveedor                       VARCHAR(50)    NOT NULL,
    descripcion_servicio                TEXT           NOT NULL,
    obligaciones_colbeef                TEXT           NOT NULL,
    obligaciones_proveedor              TEXT           NOT NULL,
    valor                               DECIMAL(18,2)  NOT NULL,
    moneda                              VARCHAR(3)     NOT NULL,   -- COP | USD | EUR
    plazo_cantidad                      INT            NOT NULL,
    plazo_unidad                        VARCHAR(10)    NOT NULL,   -- dias | meses | anios
    renovacion_automatica               TINYINT(1)     NOT NULL DEFAULT 0,
    condiciones_recibido_satisfactorio  TEXT           NOT NULL,
    requiere_poliza                     TINYINT(1)     NOT NULL DEFAULT 0,
    estado                              VARCHAR(30)    NOT NULL DEFAULT 'radicado',
    creado_por_id                       INT            NOT NULL,
    created_at                          DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                          DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP
                                                       ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_contratos_nit_proveedor (nit_proveedor),
    KEY ix_contratos_creado_por (creado_por_id),
    CONSTRAINT fk_contratos_creado_por
        FOREIGN KEY (creado_por_id) REFERENCES users (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------
-- Tabla: archivos_contrato
-- ---------------------------------------------------------
CREATE TABLE archivos_contrato (
    id                   INT          NOT NULL AUTO_INCREMENT,
    contrato_id          INT          NOT NULL,
    tipo                 VARCHAR(40)  NOT NULL, -- camara_comercio | cotizacion | cedula_rep_legal
                                                -- correo_aprobacion_gerencia | correo_aprobacion_lider | opcional
    nombre_original      VARCHAR(255) NOT NULL,
    ruta_almacenamiento  VARCHAR(500) NOT NULL,
    mime_type            VARCHAR(100) NOT NULL,
    tamano_bytes         BIGINT       NOT NULL,
    created_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_archivos_contrato_id (contrato_id),
    CONSTRAINT fk_archivos_contrato
        FOREIGN KEY (contrato_id) REFERENCES contratos (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
