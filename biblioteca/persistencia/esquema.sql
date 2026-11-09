-- Esquema SQLite. Las PRIMARY KEY / UNIQUE son la última barrera contra duplicados
-- (socios, libros, ejemplares, remitos); el Repositorio los controla antes con un mensaje claro.

CREATE TABLE IF NOT EXISTS sede (
    id_sede   TEXT PRIMARY KEY,
    nombre    TEXT NOT NULL UNIQUE,
    direccion TEXT NOT NULL,
    contacto  TEXT NOT NULL,
    horarios  TEXT NOT NULL,
    activa    INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS socio (
    numero_socio TEXT PRIMARY KEY,
    nombre       TEXT NOT NULL,
    inhabilitado INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS libro (
    isbn   TEXT PRIMARY KEY,
    titulo TEXT NOT NULL,
    autor  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ejemplar (
    codigo              TEXT PRIMARY KEY,
    isbn                TEXT NOT NULL REFERENCES libro (isbn),
    id_sede_pertenencia TEXT NOT NULL REFERENCES sede (id_sede),
    id_sede_ubicacion   TEXT REFERENCES sede (id_sede),  -- NULL: en tránsito
    estado_fisico       TEXT NOT NULL,
    disponible          INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS prestamo (
    id_prestamo       INTEGER PRIMARY KEY,
    tipo              TEXT NOT NULL CHECK (tipo IN ('Local', 'Interbibliotecario')),
    numero_socio      TEXT NOT NULL REFERENCES socio (numero_socio),
    id_sede_origen    TEXT NOT NULL REFERENCES sede (id_sede),
    id_sede_destino   TEXT NOT NULL REFERENCES sede (id_sede),
    fecha_inicio      TEXT NOT NULL,
    fecha_vencimiento TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS detalle_prestamo (
    id_prestamo            INTEGER NOT NULL REFERENCES prestamo (id_prestamo),
    codigo_ejemplar        TEXT NOT NULL REFERENCES ejemplar (codigo),
    fecha_devolucion_real  TEXT,
    estado_fisico_devuelto TEXT,
    PRIMARY KEY (id_prestamo, codigo_ejemplar)
);

-- Un ejemplar no puede tener dos detalles pendientes de devolución.
CREATE UNIQUE INDEX IF NOT EXISTS ux_detalle_pendiente
    ON detalle_prestamo (codigo_ejemplar) WHERE fecha_devolucion_real IS NULL;

CREATE TABLE IF NOT EXISTS remito (
    numero_remito     TEXT PRIMARY KEY,
    id_prestamo       INTEGER NOT NULL REFERENCES prestamo (id_prestamo),
    tipo              TEXT NOT NULL CHECK (tipo IN ('Ida', 'Retorno')),
    estado            TEXT NOT NULL,
    fecha_creacion    TEXT NOT NULL,
    fecha_empaquetado TEXT,
    fecha_despacho    TEXT,
    fecha_recepcion   TEXT,
    UNIQUE (id_prestamo, tipo)
);

CREATE TABLE IF NOT EXISTS historial_remito (
    id                INTEGER PRIMARY KEY,
    numero_remito     TEXT NOT NULL REFERENCES remito (numero_remito),
    fecha_hora        TEXT NOT NULL,
    nombre_estado     TEXT NOT NULL,
    id_sede_ubicacion TEXT REFERENCES sede (id_sede),
    observacion       TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS reserva (
    id_reserva    INTEGER PRIMARY KEY,
    numero_socio  TEXT NOT NULL REFERENCES socio (numero_socio),
    isbn          TEXT NOT NULL REFERENCES libro (isbn),
    id_sede       TEXT NOT NULL REFERENCES sede (id_sede),
    fecha_reserva TEXT NOT NULL,
    estado        TEXT NOT NULL
);

-- Avisos generados por el Observer (NotificadorSocio) en cada cambio de estado de un remito.
CREATE TABLE IF NOT EXISTS notificacion (
    id           INTEGER PRIMARY KEY,
    numero_socio TEXT NOT NULL REFERENCES socio (numero_socio),
    fecha_hora   TEXT NOT NULL,
    mensaje      TEXT NOT NULL
);
