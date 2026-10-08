CREATE TABLE IF NOT EXISTS accion_inspeccion (
    id SERIAL PRIMARY KEY,
    jornada_id INTEGER NOT NULL UNIQUE REFERENCES jornadas_transporte(id) ON DELETE CASCADE,
    fecha_inspeccion DATE NOT NULL,
    fecha_vencimiento DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS accion_cocada (
    id SERIAL PRIMARY KEY,
    jornada_id INTEGER NOT NULL UNIQUE REFERENCES jornadas_transporte(id) ON DELETE CASCADE,
    medida DECIMAL(10,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS accion_torque (
    id SERIAL PRIMARY KEY,
    jornada_id INTEGER NOT NULL UNIQUE REFERENCES jornadas_transporte(id) ON DELETE CASCADE,
    medida DECIMAL(10,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS accion_trabajos_externos (
    id SERIAL PRIMARY KEY,
    jornada_id INTEGER NOT NULL UNIQUE REFERENCES jornadas_transporte(id) ON DELETE CASCADE,
    descripcion_trabajos TEXT NOT NULL
);
