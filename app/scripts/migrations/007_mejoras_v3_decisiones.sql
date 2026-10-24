-- Fase V3: decisiones D01-D14. PostgreSQL, idempotente.
BEGIN;

UPDATE jornadas_transporte SET severidad = 'critica'
 WHERE severidad IN ('grave', 'grave-critica', 'grave-crítica');
UPDATE incidencias_ruta SET severidad = 'critica'
 WHERE severidad IN ('grave', 'grave-critica', 'grave-crítica');

ALTER TABLE jornadas_transporte ADD COLUMN IF NOT EXISTS motivo_cancelacion TEXT;
ALTER TABLE jornadas_transporte ADD COLUMN IF NOT EXISTS cancelado_por_id INTEGER REFERENCES users(id);
ALTER TABLE jornadas_transporte ADD COLUMN IF NOT EXISTS odometro_evidencia_url VARCHAR(500);
ALTER TABLE jornadas_transporte ADD COLUMN IF NOT EXISTS odometro_motivo TEXT;
ALTER TABLE jornadas_transporte ADD COLUMN IF NOT EXISTS odometro_requiere_revision BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE jornadas_transporte ADD COLUMN IF NOT EXISTS cerrado_por_sistema BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS soat_vencimiento DATE;
ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS rt_vencimiento DATE;
ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS tarjeta_propiedad_url VARCHAR(500);
ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS poliza_vencimiento DATE;
ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS pase_minero_vencimiento DATE;

ALTER TABLE users ADD COLUMN IF NOT EXISTS licencia_vencimiento DATE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS licencia_categoria VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS emo_vencimiento DATE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS pase_minero_vencimiento DATE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS firma_url VARCHAR(500);

ALTER TABLE mantenimientos ADD COLUMN IF NOT EXISTS informe_url VARCHAR(500);
ALTER TABLE mantenimientos ADD COLUMN IF NOT EXISTS firma_admin_url VARCHAR(500);
ALTER TABLE mantenimientos ADD COLUMN IF NOT EXISTS foto_cierre_url VARCHAR(500);
ALTER TABLE mantenimientos ADD COLUMN IF NOT EXISTS aprobado_por_id INTEGER REFERENCES users(id);

CREATE TABLE IF NOT EXISTS documentos_transporte (
    id SERIAL PRIMARY KEY,
    entidad VARCHAR(20) NOT NULL CHECK (entidad IN ('vehiculo', 'conductor')),
    entidad_id INTEGER NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    archivo_url VARCHAR(500),
    fecha_vencimiento DATE,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    aprobado_por_id INTEGER REFERENCES users(id),
    fecha_aprobacion TIMESTAMP WITH TIME ZONE,
    version INTEGER NOT NULL DEFAULT 1,
    archivado BOOLEAN NOT NULL DEFAULT FALSE,
    creado_en TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_documentos_transporte_entidad
    ON documentos_transporte(entidad, entidad_id, tipo, archivado);

CREATE TABLE IF NOT EXISTS auditoria_sistema (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES users(id),
    entidad VARCHAR(50) NOT NULL,
    registro_id INTEGER NOT NULL,
    accion VARCHAR(50) NOT NULL,
    valores_anteriores JSONB,
    valores_nuevos JSONB,
    motivo TEXT,
    fecha TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_auditoria_sistema_entidad
    ON auditoria_sistema(entidad, registro_id, fecha);

ALTER TABLE jornadas_transporte ADD COLUMN IF NOT EXISTS fin_operativo TIMESTAMP;
ALTER TABLE jornadas_transporte ADD COLUMN IF NOT EXISTS solicitud_id VARCHAR(80);
ALTER TABLE jornadas_transporte ADD COLUMN IF NOT EXISTS fotos_observacion JSONB;
ALTER TABLE jornadas_transporte ADD COLUMN IF NOT EXISTS observacion_resuelta BOOLEAN NOT NULL DEFAULT FALSE;
CREATE UNIQUE INDEX IF NOT EXISTS uq_jornada_solicitud ON jornadas_transporte(solicitud_id);
ALTER TABLE incidencias_ruta ADD COLUMN IF NOT EXISTS fotos JSONB;
ALTER TABLE incidencias_ruta ADD COLUMN IF NOT EXISTS resuelta BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE incidencias_ruta ADD COLUMN IF NOT EXISTS solicitud_id VARCHAR(80);
CREATE UNIQUE INDEX IF NOT EXISTS uq_incidencia_solicitud ON incidencias_ruta(solicitud_id);
ALTER TABLE mantenimientos ADD COLUMN IF NOT EXISTS alcance VARCHAR(20) NOT NULL DEFAULT 'menor';
ALTER TABLE mantenimientos ADD COLUMN IF NOT EXISTS fotos_cierre JSONB;
CREATE TABLE IF NOT EXISTS notificaciones_transporte (
 id SERIAL PRIMARY KEY, usuario_id INTEGER NOT NULL REFERENCES users(id),
 clave VARCHAR(180) NOT NULL UNIQUE, titulo VARCHAR(160) NOT NULL, mensaje TEXT NOT NULL,
 entidad VARCHAR(30), entidad_id INTEGER, persistente BOOLEAN NOT NULL DEFAULT FALSE,
 activa BOOLEAN NOT NULL DEFAULT TRUE, leida BOOLEAN NOT NULL DEFAULT FALSE,
 push_enviado BOOLEAN NOT NULL DEFAULT FALSE, fecha TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_notificaciones_usuario ON notificaciones_transporte(usuario_id);
CREATE TABLE IF NOT EXISTS dispositivos_push (
 id SERIAL PRIMARY KEY, usuario_id INTEGER NOT NULL REFERENCES users(id), token VARCHAR(512) NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS ix_dispositivos_usuario ON dispositivos_push(usuario_id);
UPDATE jornadas_transporte SET estado_semaforo = CASE severidad
 WHEN 'critica' THEN 'rojo' WHEN 'moderada' THEN 'amarillo' ELSE 'verde' END
 WHERE severidad IN ('leve', 'moderada', 'critica') AND observacion_resuelta = FALSE;
-- Una novedad leve histórica deja de pintar la unidad de amarillo.
UPDATE vehiculos v SET estado_semaforo = 'verde'
 WHERE v.estado_semaforo = 'amarillo'
 AND NOT EXISTS (SELECT 1 FROM jornadas_transporte j WHERE j.vehiculo_id=v.id
   AND j.severidad IN ('moderada', 'critica') AND j.observacion_resuelta=FALSE)
 AND NOT EXISTS (SELECT 1 FROM incidencias_ruta i JOIN jornadas_transporte j ON j.id=i.jornada_id
   WHERE j.vehiculo_id=v.id AND i.severidad IN ('moderada', 'critica') AND i.resuelta=FALSE);
COMMIT;
