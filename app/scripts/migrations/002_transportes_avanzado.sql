-- Módulo de transportes avanzado: inspecciones, checklist, averías, incidentes,
-- planes de mantenimiento y ampliación de mantenimiento.
-- Idempotente para PostgreSQL (contenedor ramissac_db).
-- El backend también las crea con Base.metadata.create_all al arrancar.

-- ============================================================
-- 1. Ampliación de vehiculos (kilometraje monotónico)
-- ============================================================
ALTER TABLE vehiculos
    ADD COLUMN IF NOT EXISTS kilometraje_actual FLOAT NOT NULL DEFAULT 0.0;

-- ============================================================
-- 2. Tabla de incidentes (se crea antes que averias porque averias
--    referencia incidentes via origen_incidente_id)
-- ============================================================
CREATE TABLE IF NOT EXISTS incidentes (
    id SERIAL PRIMARY KEY,
    vehiculo_id INTEGER REFERENCES vehiculos (id),
    ruta_id INTEGER REFERENCES rutas_asignaciones (id),
    tipo VARCHAR NOT NULL DEFAULT 'incidente',
    estado VARCHAR NOT NULL DEFAULT 'reportado',
    fecha_reporte TIMESTAMP NOT NULL DEFAULT NOW(),
    descripcion TEXT NOT NULL,
    afecta_personas BOOLEAN NOT NULL DEFAULT FALSE,
    dano_vehiculo BOOLEAN NOT NULL DEFAULT FALSE,
    requiere_acta BOOLEAN NOT NULL DEFAULT FALSE,
    registrado_por INTEGER REFERENCES users (id),
    observaciones TEXT
);
CREATE INDEX IF NOT EXISTS ix_incidentes_id ON incidentes (id);
CREATE INDEX IF NOT EXISTS ix_incidentes_vehiculo_id ON incidentes (vehiculo_id);

-- ============================================================
-- 3. Tabla de averías (referencia incidentes)
-- ============================================================
CREATE TABLE IF NOT EXISTS averias (
    id SERIAL PRIMARY KEY,
    vehiculo_id INTEGER NOT NULL REFERENCES vehiculos (id),
    ruta_id INTEGER REFERENCES rutas_asignaciones (id),
    descripcion TEXT NOT NULL,
    criticidad VARCHAR NOT NULL DEFAULT 'media',
    estado VARCHAR NOT NULL DEFAULT 'reportada',
    origen_incidente_id INTEGER REFERENCES incidentes (id),
    fecha_reporte TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_resolucion TIMESTAMP,
    registrado_por INTEGER REFERENCES users (id),
    detalle_resolucion TEXT
);
CREATE INDEX IF NOT EXISTS ix_averias_id ON averias (id);
CREATE INDEX IF NOT EXISTS ix_averias_vehiculo_id ON averias (vehiculo_id);

-- ============================================================
-- 4. Ampliación de mantenimientos (preventivo/correctivo, historial, costos)
-- ============================================================
CREATE TABLE IF NOT EXISTS planes_mantenimiento (
    id SERIAL PRIMARY KEY,
    vehiculo_id INTEGER NOT NULL REFERENCES vehiculos (id),
    nombre VARCHAR(150) NOT NULL,
    descripcion TEXT,
    tipo_control VARCHAR NOT NULL DEFAULT 'mixto',
    intervalo_kilometraje FLOAT,
    intervalo_dias INTEGER,
    intervalo_horas FLOAT,
    estado_control VARCHAR NOT NULL DEFAULT 'NORMAL',
    activo BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS ix_planes_mantenimiento_id ON planes_mantenimiento (id);
CREATE INDEX IF NOT EXISTS ix_planes_mantenimiento_vehiculo_id ON planes_mantenimiento (vehiculo_id);

CREATE TABLE IF NOT EXISTS plan_detalles_mantenimiento (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES planes_mantenimiento (id),
    descripcion TEXT NOT NULL,
    orden INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_plan_detalles_mantenimiento_id ON plan_detalles_mantenimiento (id);

ALTER TABLE mantenimientos
    ADD COLUMN IF NOT EXISTS averia_id INTEGER REFERENCES averias (id),
    ADD COLUMN IF NOT EXISTS plan_id INTEGER REFERENCES planes_mantenimiento (id),
    ADD COLUMN IF NOT EXISTS tipo VARCHAR NOT NULL DEFAULT 'CORRECTIVO',
    ADD COLUMN IF NOT EXISTS descripcion_trabajo TEXT,
    ADD COLUMN IF NOT EXISTS fecha_cierre TIMESTAMP;

ALTER TABLE mantenimientos
    ADD COLUMN IF NOT EXISTS mecanico_id INTEGER REFERENCES users (id),
    ADD COLUMN IF NOT EXISTS kilometraje_mantenimiento FLOAT,
    ADD COLUMN IF NOT EXISTS proximo_kilometraje_mantenimiento FLOAT,
    ADD COLUMN IF NOT EXISTS fecha TIMESTAMP;

CREATE TABLE IF NOT EXISTS jornadas_transporte (
    id SERIAL PRIMARY KEY,
    vehiculo_id INTEGER NOT NULL REFERENCES vehiculos (id),
    conductor_id INTEGER NOT NULL REFERENCES users (id),
    fecha_inicio TIMESTAMP,
    fecha_fin TIMESTAMP,
    estado VARCHAR NOT NULL DEFAULT 'pendiente'
);
CREATE INDEX IF NOT EXISTS ix_jornadas_transporte_vehiculo_id ON jornadas_transporte (vehiculo_id);
CREATE INDEX IF NOT EXISTS ix_jornadas_transporte_conductor_id ON jornadas_transporte (conductor_id);

CREATE TABLE IF NOT EXISTS checklists_transporte (
    id SERIAL PRIMARY KEY,
    jornada_id INTEGER NOT NULL REFERENCES jornadas_transporte (id) ON DELETE CASCADE,
    tipo VARCHAR NOT NULL,
    kilometraje FLOAT NOT NULL,
    nivel_combustible VARCHAR NOT NULL,
    estado_general VARCHAR NOT NULL,
    conforme BOOLEAN NOT NULL,
    observaciones TEXT
);

CREATE TABLE IF NOT EXISTS incidencias_ruta (
    id SERIAL PRIMARY KEY,
    jornada_id INTEGER NOT NULL REFERENCES jornadas_transporte (id) ON DELETE CASCADE,
    tipo VARCHAR NOT NULL,
    descripcion TEXT NOT NULL,
    fecha TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 5. Tablas de inspecciones (checklist reutilizable)
-- ============================================================
CREATE TABLE IF NOT EXISTS checklist_items (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    nombre VARCHAR(150) NOT NULL,
    descripcion TEXT,
    criticidad VARCHAR NOT NULL DEFAULT 'media',
    activo BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS ix_checklist_items_id ON checklist_items (id);

CREATE TABLE IF NOT EXISTS inspecciones (
    id SERIAL PRIMARY KEY,
    vehiculo_id INTEGER NOT NULL REFERENCES vehiculos (id),
    ruta_id INTEGER REFERENCES rutas_asignaciones (id),
    tipo VARCHAR NOT NULL,
    resultado VARCHAR,
    realizada_por INTEGER REFERENCES users (id),
    fecha TIMESTAMP NOT NULL DEFAULT NOW(),
    observaciones TEXT,
    activa BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS ix_inspecciones_id ON inspecciones (id);
CREATE INDEX IF NOT EXISTS ix_inspecciones_vehiculo_id ON inspecciones (vehiculo_id);
CREATE INDEX IF NOT EXISTS ix_inspecciones_ruta_id ON inspecciones (ruta_id);

CREATE TABLE IF NOT EXISTS inspeccion_detalles (
    id SERIAL PRIMARY KEY,
    inspeccion_id INTEGER NOT NULL REFERENCES inspecciones (id),
    item_id INTEGER NOT NULL REFERENCES checklist_items (id),
    resultado VARCHAR NOT NULL,
    comentario TEXT
);
CREATE INDEX IF NOT EXISTS ix_inspeccion_detalles_id ON inspeccion_detalles (id);
CREATE INDEX IF NOT EXISTS ix_inspeccion_detalles_inspeccion_id ON inspeccion_detalles (inspeccion_id);
