-- Aplicar antes de desplegar el backend V2. No altera los registros históricos.

BEGIN;

ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS estado_semaforo VARCHAR(20) NOT NULL DEFAULT 'verde';

ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS tipo VARCHAR(40);

ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS capacidad_tanque_galones DOUBLE PRECISION CHECK (capacidad_tanque_galones > 0);

ALTER TABLE jornadas_transporte ADD COLUMN IF NOT EXISTS estado_semaforo VARCHAR(20) NOT NULL DEFAULT 'verde';

ALTER TABLE jornadas_transporte ADD COLUMN IF NOT EXISTS tiene_observaciones BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE jornadas_transporte ADD COLUMN IF NOT EXISTS severidad VARCHAR(20);

ALTER TABLE jornadas_transporte ADD COLUMN IF NOT EXISTS foto_observacion VARCHAR(500);

ALTER TABLE jornadas_transporte ADD COLUMN IF NOT EXISTS jornada_padre_id INTEGER REFERENCES jornadas_transporte(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_jornadas_padre ON jornadas_transporte(jornada_padre_id);

ALTER TABLE jornadas_transporte ADD COLUMN IF NOT EXISTS nivel_combustible_final DOUBLE PRECISION;

ALTER TABLE jornadas_transporte ADD COLUMN IF NOT EXISTS galones_abastecidos DOUBLE PRECISION;

ALTER TABLE jornadas_transporte ADD COLUMN IF NOT EXISTS galones_consumidos DOUBLE PRECISION;

ALTER TABLE jornadas_transporte ADD COLUMN IF NOT EXISTS rendimiento_km_galon DOUBLE PRECISION;

ALTER TABLE incidencias_ruta ADD COLUMN IF NOT EXISTS foto_incidencia VARCHAR(500);

ALTER TABLE incidencias_ruta ADD COLUMN IF NOT EXISTS severidad VARCHAR(20);

ALTER TABLE accion_combustible ADD COLUMN IF NOT EXISTS costo DOUBLE PRECISION;

ALTER TABLE accion_combustible ADD COLUMN IF NOT EXISTS comprobante VARCHAR(100);

ALTER TABLE accion_combustible ADD COLUMN IF NOT EXISTS odometro DOUBLE PRECISION;

UPDATE vehiculos SET tipo = 'Camión Grúa' WHERE placa IN ('Z7F-777', 'Z7M-813') AND tipo IS NULL;

UPDATE vehiculos SET tipo = 'Camioneta' WHERE placa IN ('Z7P-702', 'Z8I-845') AND tipo IS NULL;
UPDATE vehiculos SET tipo = 'Coaster' WHERE placa IN ('ZDO-953', 'ZDX-965') AND tipo IS NULL;
UPDATE vehiculos SET tipo = 'Camión de Carga' WHERE placa IN ('Z7G-937', 'Z8K-916') AND tipo IS NULL;
UPDATE vehiculos SET estado_semaforo = 'rojo' WHERE estado = 'en_mantenimiento';

COMMIT;

