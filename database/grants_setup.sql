-- =========================================================================
-- Script de configuración inicial — ejecutar con un usuario MySQL root/admin
-- =========================================================================
-- Crea la base de datos `Juridica` si no existe y otorga los permisos
-- necesarios al usuario `usuario_juridica` para que la aplicación pueda
-- crear tablas, leer y escribir.
--
-- Ejecutar UNA SOLA VEZ (idempotente).
-- =========================================================================

-- 1) Crear la base de datos si no existe.
CREATE DATABASE IF NOT EXISTS Juridica
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- 2) Si el usuario aún no existe, descomenta y ejecuta esto:
-- CREATE USER IF NOT EXISTS 'usuario_juridica'@'%'
--     IDENTIFIED BY 'clave_juridica_123';

-- 3) Otorgar permisos completos al usuario sobre la base `Juridica`.
GRANT ALL PRIVILEGES ON Juridica.* TO 'usuario_juridica'@'%';

-- 4) Aplicar cambios.
FLUSH PRIVILEGES;

-- =========================================================================
-- Verificación
-- =========================================================================
-- Para verificar que los permisos quedaron bien aplicados:
--
--   SHOW GRANTS FOR 'usuario_juridica'@'%';
--
-- Debe aparecer una línea con:
--   GRANT ALL PRIVILEGES ON `Juridica`.* TO `usuario_juridica`@`%`
-- =========================================================================
