-- =========================================================
-- Alteraciones incrementales para BD existente
-- =========================================================
-- Ejecutar solo las sentencias que falten (MySQL no tiene
-- ADD COLUMN IF NOT EXISTS). La app aplica lo mismo vía
-- backend/app/infrastructure/database/migrations.py al arrancar.
-- =========================================================

USE Juridica;

-- users.email
-- ALTER TABLE users ADD COLUMN email VARCHAR(255) NOT NULL DEFAULT '' AFTER role;

-- contratos.codigo
-- ALTER TABLE contratos ADD COLUMN codigo VARCHAR(20) NULL AFTER id;
-- UPDATE contratos SET codigo = CONCAT('JC-', LPAD(id, 4, '0')) WHERE codigo IS NULL;
-- ALTER TABLE contratos MODIFY COLUMN codigo VARCHAR(20) NOT NULL;
-- ALTER TABLE contratos ADD UNIQUE INDEX uq_contratos_codigo (codigo);
-- ALTER TABLE contratos ADD COLUMN tipo_codigo VARCHAR(10) NOT NULL DEFAULT 'C' AFTER codigo;

-- contratos: flujo aprobación y vigencia
-- ALTER TABLE contratos ADD COLUMN correo_lider_proceso VARCHAR(255) NOT NULL DEFAULT '' AFTER requiere_poliza;
-- ALTER TABLE contratos ADD COLUMN correo_gerencia VARCHAR(255) NOT NULL DEFAULT '' AFTER correo_lider_proceso;
-- ALTER TABLE contratos ADD COLUMN estado_aprobacion VARCHAR(30) NOT NULL DEFAULT 'aprobado' AFTER correo_gerencia;
-- ALTER TABLE contratos ADD COLUMN fecha_inicio DATE NULL AFTER estado;
-- ALTER TABLE contratos ADD COLUMN fecha_fin DATE NULL AFTER fecha_inicio;
-- ALTER TABLE contratos ADD COLUMN fecha_proxima_notificacion DATE NULL AFTER fecha_fin;
-- ALTER TABLE contratos ADD COLUMN aprobado_lider_at DATETIME NULL AFTER fecha_proxima_notificacion;
-- ALTER TABLE contratos ADD COLUMN aprobado_gerencia_at DATETIME NULL AFTER aprobado_lider_at;

-- archivos_contrato.subido_por_id
-- ALTER TABLE archivos_contrato ADD COLUMN subido_por_id INT NULL;

-- otrosies_contrato: aprobación
-- ALTER TABLE otrosies_contrato ADD COLUMN estado_aprobacion VARCHAR(30) NOT NULL DEFAULT 'aprobado' AFTER archivo_id;
-- ALTER TABLE otrosies_contrato ADD COLUMN aprobado_lider_at DATETIME NULL AFTER estado_aprobacion;
-- ALTER TABLE otrosies_contrato ADD COLUMN aprobado_gerencia_at DATETIME NULL AFTER aprobado_lider_at;

-- solicitudes_gestion: gestión y trámite OC
-- ALTER TABLE solicitudes_gestion ADD COLUMN observaciones_gestion TEXT NULL AFTER observaciones_texto;
-- ALTER TABLE solicitudes_gestion ADD COLUMN justificacion_cotizaciones TEXT NULL AFTER observaciones_gestion;
-- ALTER TABLE solicitudes_gestion ADD COLUMN numero_tramite_oc VARCHAR(100) NOT NULL DEFAULT '' AFTER justificacion_cotizaciones;
-- ALTER TABLE solicitudes_gestion ADD COLUMN gestor_id INT NULL AFTER creado_por_id;
-- ALTER TABLE solicitudes_gestion ADD COLUMN lider_segunda_aprobacion_id VARCHAR(50) NOT NULL DEFAULT '' AFTER lider_area_label;
-- ALTER TABLE solicitudes_gestion ADD COLUMN lider_segunda_aprobacion_label VARCHAR(500) NOT NULL DEFAULT '' AFTER lider_segunda_aprobacion_id;
-- ALTER TABLE solicitudes_gestion ADD COLUMN creado_por_email VARCHAR(255) NOT NULL DEFAULT '' AFTER creado_por_id;

-- solicitudes_gestion_productos
-- ALTER TABLE solicitudes_gestion_productos ADD COLUMN cantidad DECIMAL(18,4) NOT NULL DEFAULT 1.0000 AFTER centro_costo;
-- ALTER TABLE solicitudes_gestion_productos ADD COLUMN estado_aprobacion VARCHAR(20) NOT NULL DEFAULT 'pendiente' AFTER centro_costo;
-- ALTER TABLE solicitudes_gestion_productos ADD COLUMN cantidad_entregada DECIMAL(18,4) NOT NULL DEFAULT 0.0000 AFTER cantidad;
-- ALTER TABLE solicitudes_gestion_productos ADD COLUMN numero_tramite_oc VARCHAR(100) NOT NULL DEFAULT '' AFTER estado_aprobacion;

-- solicitudes_gestion_archivos
-- ALTER TABLE solicitudes_gestion_archivos ADD COLUMN categoria VARCHAR(30) NOT NULL DEFAULT 'solicitud' AFTER tamano_bytes;
-- ALTER TABLE solicitudes_gestion_archivos ADD COLUMN observacion_id INT NULL AFTER categoria;
