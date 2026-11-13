"""Traduce entre las tablas de SQLite y los objetos del dominio.

Mantiene un mapa de identidad: dentro de un mismo Repositorio cada fila se convierte en
un único objeto, porque el dominio compara sedes con `is` (ej. Ejemplar.pertenece_a_sede).
Los objetos ya persistidos se reconstruyen sin pasar por el constructor (que validaría
de nuevo, por ejemplo, que los ejemplares de un préstamo estén disponibles).
"""

from datetime import date, datetime

from biblioteca.excepciones import ReglaNegocioError
from biblioteca.modelos import (
    Catalogo, DetallePrestamo, Ejemplar, Empaquetado, Entregado, Enviado, HistorialRemito, Libro,
    Pendiente, PrestamoInterbibliotecario, PrestamoLocal, Remito, Reserva, ReservaCancelada,
    ReservaConfirmada, ReservaCumplida, ReservaPendiente, Sede, Socio,
)

ESTADOS_REMITO = {c.nombre: c for c in (Pendiente, Empaquetado, Enviado, Entregado)}
ESTADOS_RESERVA = {c.nombre: c for c in (ReservaPendiente, ReservaConfirmada,
                                         ReservaCumplida, ReservaCancelada)}


def _fecha(texto):
    return date.fromisoformat(texto) if texto else None


def _fecha_hora(texto):
    return datetime.fromisoformat(texto) if texto else None


def _iso(valor):
    return valor.isoformat() if valor else None


def _id_sede(sede):
    return sede.id_sede if sede else None


class Repositorio:
    def __init__(self, conexion):
        self.con = conexion
        self._sedes = {}
        self._socios = {}
        self._libros = {}
        self._ejemplares = {}
        self._prestamos = {}
        self._reservas = {}

    # ---- utilidades -------------------------------------------------------------
    def _fila(self, sql, *parametros):
        return self.con.execute(sql, parametros).fetchone()

    def _claves(self, sql, *parametros):
        return [fila[0] for fila in self.con.execute(sql, parametros)]

    def _existe(self, tabla, columna, valor):
        return self._fila(f"SELECT 1 FROM {tabla} WHERE {columna} = ?", valor) is not None

    def _siguiente_id(self, tabla, columna):
        return self._fila(f"SELECT COALESCE(MAX({columna}), 0) + 1 FROM {tabla}")[0]

    def siguiente_id_prestamo(self):
        return self._siguiente_id("prestamo", "id_prestamo")

    def siguiente_id_reserva(self):
        return self._siguiente_id("reserva", "id_reserva")

    def siguiente_numero_remito(self):
        return f"R-{self._fila('SELECT COUNT(*) + 1 FROM remito')[0]:06d}"

    # ---- Sede -------------------------------------------------------------------
    def sede(self, id_sede):
        if id_sede is None:
            return None
        if id_sede not in self._sedes:
            f = self._fila("SELECT * FROM sede WHERE id_sede = ?", id_sede)
            if f is None:
                raise ReglaNegocioError(f"No existe la sede {id_sede}.")
            self._sedes[id_sede] = Sede(f["id_sede"], f["nombre"], f["direccion"], f["contacto"],
                                        f["horarios"], bool(f["activa"]))
        return self._sedes[id_sede]

    def sedes(self, solo_activas=False):
        sql = "SELECT id_sede FROM sede" + (" WHERE activa = 1" if solo_activas else "")
        return [self.sede(i) for i in self._claves(sql + " ORDER BY nombre")]

    def agregar_sede(self, sede):
        if self._existe("sede", "id_sede", sede.id_sede):
            raise ReglaNegocioError(f"Ya existe una sede con código {sede.id_sede}.")
        if self._existe("sede", "nombre", sede.nombre):
            raise ReglaNegocioError(f"Ya existe una sede llamada {sede.nombre}.")
        self.con.execute("INSERT INTO sede (id_sede, nombre, direccion, contacto, horarios, activa) "
                         "VALUES (?, ?, ?, ?, ?, ?)",
                         (sede.id_sede, sede.nombre, sede.direccion, sede.contacto, sede.horarios,
                          int(sede.activa)))
        self._sedes[sede.id_sede] = sede

    def guardar_sede(self, sede):
        otra = self._fila("SELECT id_sede FROM sede WHERE nombre = ? AND id_sede <> ?",
                          sede.nombre, sede.id_sede)
        if otra:
            raise ReglaNegocioError(f"Ya existe una sede llamada {sede.nombre}.")
        self.con.execute("UPDATE sede SET nombre = ?, direccion = ?, contacto = ?, horarios = ?, "
                         "activa = ? WHERE id_sede = ?",
                         (sede.nombre, sede.direccion, sede.contacto, sede.horarios,
                          int(sede.activa), sede.id_sede))

    # ---- Socio ------------------------------------------------------------------
    def socio(self, numero_socio):
        if numero_socio not in self._socios:
            f = self._fila("SELECT * FROM socio WHERE numero_socio = ?", numero_socio)
            if f is None:
                raise ReglaNegocioError(f"No existe el socio {numero_socio}.")
            self._socios[numero_socio] = Socio(f["numero_socio"], f["nombre"], bool(f["inhabilitado"]))
        return self._socios[numero_socio]

    def socios(self, solo_habilitados=False):
        sql = "SELECT numero_socio FROM socio" + (" WHERE inhabilitado = 0" if solo_habilitados else "")
        return [self.socio(n) for n in self._claves(sql + " ORDER BY nombre")]

    def agregar_socio(self, socio):
        if self._existe("socio", "numero_socio", socio.numero_socio):
            raise ReglaNegocioError(f"Ya existe un socio con número {socio.numero_socio}.")
        self.con.execute("INSERT INTO socio (numero_socio, nombre, inhabilitado) VALUES (?, ?, ?)",
                         (socio.numero_socio, socio.nombre, int(socio.inhabilitado)))
        self._socios[socio.numero_socio] = socio

    def guardar_socio(self, socio):
        self.con.execute("UPDATE socio SET nombre = ?, inhabilitado = ? WHERE numero_socio = ?",
                         (socio.nombre, int(socio.inhabilitado), socio.numero_socio))

    # ---- Libro ------------------------------------------------------------------
    def libro(self, isbn):
        if isbn not in self._libros:
            f = self._fila("SELECT * FROM libro WHERE isbn = ?", isbn)
            if f is None:
                raise ReglaNegocioError(f"No existe el libro con ISBN {isbn}.")
            self._libros[isbn] = Libro(f["isbn"], f["titulo"], f["autor"])
        return self._libros[isbn]

    def libros(self):
        return [self.libro(i) for i in self._claves("SELECT isbn FROM libro ORDER BY titulo")]

    def agregar_libro(self, libro):
        if self._existe("libro", "isbn", libro.isbn):
            raise ReglaNegocioError(f"Ya existe un libro con ISBN {libro.isbn}.")
        self.con.execute("INSERT INTO libro (isbn, titulo, autor) VALUES (?, ?, ?)",
                         (libro.isbn, libro.titulo, libro.autor))
        self._libros[libro.isbn] = libro

    def guardar_libro(self, libro):
        self.con.execute("UPDATE libro SET titulo = ?, autor = ? WHERE isbn = ?",
                         (libro.titulo, libro.autor, libro.isbn))

    # ---- Ejemplar / Catalogo ----------------------------------------------------
    def ejemplar(self, codigo):
        if codigo not in self._ejemplares:
            f = self._fila("SELECT * FROM ejemplar WHERE codigo = ?", codigo)
            if f is None:
                raise ReglaNegocioError(f"No existe el ejemplar {codigo}.")
            e = Ejemplar(f["codigo"], self.libro(f["isbn"]), self.sede(f["id_sede_pertenencia"]),
                         f["estado_fisico"])
            e.ubicacion_actual = self.sede(f["id_sede_ubicacion"])
            e.disponible = bool(f["disponible"])
            self._ejemplares[codigo] = e
        return self._ejemplares[codigo]

    def ejemplares(self, isbn=None):
        if isbn:
            codigos = self._claves("SELECT codigo FROM ejemplar WHERE isbn = ? ORDER BY codigo", isbn)
        else:
            codigos = self._claves("SELECT codigo FROM ejemplar ORDER BY codigo")
        return [self.ejemplar(c) for c in codigos]

    def catalogo(self, isbn=None):
        """Arma el Catalogo (agregado del patrón Iterator) con los ejemplares guardados."""
        catalogo = Catalogo()
        for e in self.ejemplares(isbn):
            catalogo.agregar_ejemplar(e)
        return catalogo

    def agregar_ejemplar(self, ejemplar):
        if self._existe("ejemplar", "codigo", ejemplar.codigo):
            raise ReglaNegocioError(f"Ya existe un ejemplar con código {ejemplar.codigo}.")
        self.con.execute("INSERT INTO ejemplar (codigo, isbn, id_sede_pertenencia, id_sede_ubicacion, "
                         "estado_fisico, disponible) VALUES (?, ?, ?, ?, ?, ?)",
                         (ejemplar.codigo, ejemplar.libro.isbn, ejemplar.sede_pertenencia.id_sede,
                          _id_sede(ejemplar.ubicacion_actual), ejemplar.estado_fisico,
                          int(ejemplar.disponible)))
        self._ejemplares[ejemplar.codigo] = ejemplar

    def guardar_ejemplar(self, ejemplar):
        self.con.execute("UPDATE ejemplar SET id_sede_ubicacion = ?, estado_fisico = ?, disponible = ? "
                         "WHERE codigo = ?",
                         (_id_sede(ejemplar.ubicacion_actual), ejemplar.estado_fisico,
                          int(ejemplar.disponible), ejemplar.codigo))

    # ---- Prestamo (con detalles y remitos) --------------------------------------
    def prestamo(self, id_prestamo):
        id_prestamo = int(id_prestamo)
        if id_prestamo not in self._prestamos:
            f = self._fila("SELECT * FROM prestamo WHERE id_prestamo = ?", id_prestamo)
            if f is None:
                raise ReglaNegocioError(f"No existe el préstamo {id_prestamo}.")
            clase = PrestamoInterbibliotecario if f["tipo"] == "Interbibliotecario" else PrestamoLocal
            p = clase.__new__(clase)
            p.id_prestamo = f["id_prestamo"]
            p.socio = self.socio(f["numero_socio"])
            p.sede_origen = self.sede(f["id_sede_origen"])
            p.sede_destino = self.sede(f["id_sede_destino"])
            p.fecha_inicio = _fecha(f["fecha_inicio"])
            p.fecha_vencimiento = _fecha(f["fecha_vencimiento"])
            p.detalles = []
            for d in self.con.execute("SELECT * FROM detalle_prestamo WHERE id_prestamo = ? "
                                      "ORDER BY codigo_ejemplar", (id_prestamo,)):
                detalle = DetallePrestamo(self.ejemplar(d["codigo_ejemplar"]))
                detalle.fecha_devolucion_real = _fecha(d["fecha_devolucion_real"])
                detalle.estado_fisico_devuelto = d["estado_fisico_devuelto"]
                p.detalles.append(detalle)
            self._prestamos[id_prestamo] = p
            if p.es_interbibliotecario():
                p.remito = self._remito_de(p, Remito.IDA)
                p.remito_retorno = self._remito_de(p, Remito.RETORNO)
        return self._prestamos[id_prestamo]

    def prestamos(self, solo_activos=False):
        sql = "SELECT id_prestamo FROM prestamo"
        if solo_activos:
            sql += (" WHERE id_prestamo IN (SELECT id_prestamo FROM detalle_prestamo "
                    "WHERE fecha_devolucion_real IS NULL)")
        return [self.prestamo(i) for i in self._claves(sql + " ORDER BY id_prestamo DESC")]

    def guardar_prestamo(self, p):
        """Inserta o actualiza el préstamo, sus detalles, sus ejemplares y sus remitos."""
        self.con.execute("INSERT OR IGNORE INTO prestamo (id_prestamo, tipo, numero_socio, id_sede_origen, "
                         "id_sede_destino, fecha_inicio, fecha_vencimiento) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (p.id_prestamo, "Interbibliotecario" if p.es_interbibliotecario() else "Local",
                          p.socio.numero_socio, p.sede_origen.id_sede, p.sede_destino.id_sede,
                          _iso(p.fecha_inicio), _iso(p.fecha_vencimiento)))
        for d in p.detalles:
            self.con.execute("INSERT INTO detalle_prestamo (id_prestamo, codigo_ejemplar, "
                             "fecha_devolucion_real, estado_fisico_devuelto) VALUES (?, ?, ?, ?) "
                             "ON CONFLICT (id_prestamo, codigo_ejemplar) DO UPDATE SET "
                             "fecha_devolucion_real = excluded.fecha_devolucion_real, "
                             "estado_fisico_devuelto = excluded.estado_fisico_devuelto",
                             (p.id_prestamo, d.ejemplar.codigo, _iso(d.fecha_devolucion_real),
                              d.estado_fisico_devuelto))
            self.guardar_ejemplar(d.ejemplar)
        if p.es_interbibliotecario():
            for remito in (p.remito, p.remito_retorno):
                if remito is not None:
                    self._guardar_remito(remito)
        self._prestamos[p.id_prestamo] = p

    # ---- Remito -----------------------------------------------------------------
    def _remito_de(self, prestamo, tipo):
        f = self._fila("SELECT * FROM remito WHERE id_prestamo = ? AND tipo = ?", prestamo.id_prestamo, tipo)
        if f is None:
            return None
        r = Remito.__new__(Remito)
        r.numero_remito = f["numero_remito"]
        r.prestamo = prestamo
        r.tipo = f["tipo"]
        r._estado = ESTADOS_REMITO[f["estado"]]()
        r.fecha_creacion = _fecha_hora(f["fecha_creacion"])
        r.fecha_empaquetado = _fecha_hora(f["fecha_empaquetado"])
        r.fecha_despacho = _fecha_hora(f["fecha_despacho"])
        r.fecha_recepcion = _fecha_hora(f["fecha_recepcion"])
        r.historial = []
        for h in self.con.execute("SELECT * FROM historial_remito WHERE numero_remito = ? ORDER BY id",
                                  (r.numero_remito,)):
            entrada = HistorialRemito(h["nombre_estado"], self.sede(h["id_sede_ubicacion"]), h["observacion"])
            entrada.fecha_hora = _fecha_hora(h["fecha_hora"])
            r.historial.append(entrada)
        return r

    def remito(self, numero_remito):
        f = self._fila("SELECT id_prestamo, tipo FROM remito WHERE numero_remito = ?", numero_remito)
        if f is None:
            raise ReglaNegocioError(f"No existe el remito {numero_remito}.")
        p = self.prestamo(f["id_prestamo"])
        return p.remito_retorno if f["tipo"] == Remito.RETORNO else p.remito

    def remitos(self, estado=None):
        sql = "SELECT numero_remito FROM remito"
        parametros = ()
        if estado:
            sql += " WHERE estado = ?"
            parametros = (estado,)
        return [self.remito(n) for n in self._claves(sql + " ORDER BY numero_remito DESC", *parametros)]

    def _guardar_remito(self, r):
        if self._existe("remito", "numero_remito", r.numero_remito):
            fila = self._fila("SELECT id_prestamo, tipo FROM remito WHERE numero_remito = ?", r.numero_remito)
            if (fila["id_prestamo"], fila["tipo"]) != (r.prestamo.id_prestamo, r.tipo):
                raise ReglaNegocioError(f"Ya existe un remito con número {r.numero_remito}.")
        self.con.execute("INSERT INTO remito (numero_remito, id_prestamo, tipo, estado, fecha_creacion, "
                         "fecha_empaquetado, fecha_despacho, fecha_recepcion) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                         "ON CONFLICT (numero_remito) DO UPDATE SET estado = excluded.estado, "
                         "fecha_empaquetado = excluded.fecha_empaquetado, "
                         "fecha_despacho = excluded.fecha_despacho, fecha_recepcion = excluded.fecha_recepcion",
                         (r.numero_remito, r.prestamo.id_prestamo, r.tipo, r.estado.nombre,
                          _iso(r.fecha_creacion), _iso(r.fecha_empaquetado), _iso(r.fecha_despacho),
                          _iso(r.fecha_recepcion)))
        # El historial solo crece: se insertan las entradas que todavía no están guardadas.
        guardadas = self._fila("SELECT COUNT(*) FROM historial_remito WHERE numero_remito = ?",
                               r.numero_remito)[0]
        for h in r.historial[guardadas:]:
            self.con.execute("INSERT INTO historial_remito (numero_remito, fecha_hora, nombre_estado, "
                             "id_sede_ubicacion, observacion) VALUES (?, ?, ?, ?, ?)",
                             (r.numero_remito, _iso(h.fecha_hora), h.nombre_estado,
                              _id_sede(h.sede_ubicacion), h.observacion))

    # ---- Reserva ----------------------------------------------------------------
    def reserva(self, id_reserva):
        id_reserva = int(id_reserva)
        if id_reserva not in self._reservas:
            f = self._fila("SELECT * FROM reserva WHERE id_reserva = ?", id_reserva)
            if f is None:
                raise ReglaNegocioError(f"No existe la reserva {id_reserva}.")
            r = Reserva(f["id_reserva"], self.socio(f["numero_socio"]), self.libro(f["isbn"]),
                        self.sede(f["id_sede"]), _fecha(f["fecha_reserva"]))
            r.cambiar_estado(ESTADOS_RESERVA[f["estado"]]())
            self._reservas[id_reserva] = r
        return self._reservas[id_reserva]

    def reservas(self):
        return [self.reserva(i) for i in self._claves("SELECT id_reserva FROM reserva ORDER BY id_reserva DESC")]

    def guardar_reserva(self, r):
        self.con.execute("INSERT INTO reserva (id_reserva, numero_socio, isbn, id_sede, fecha_reserva, estado) "
                         "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (id_reserva) DO UPDATE SET estado = excluded.estado",
                         (r.id_reserva, r.socio.numero_socio, r.libro.isbn, r.sede.id_sede,
                          _iso(r.fecha_reserva), r.estado.nombre))
        self._reservas[r.id_reserva] = r

    # ---- Notificaciones ---------------------------------------------------------
    def agregar_notificacion(self, socio, mensaje):
        self.con.execute("INSERT INTO notificacion (numero_socio, fecha_hora, mensaje) VALUES (?, ?, ?)",
                         (socio.numero_socio, datetime.now().isoformat(timespec="seconds"), mensaje))

    def notificaciones(self, limite=100):
        return self.con.execute("SELECT n.*, s.nombre FROM notificacion n JOIN socio s USING (numero_socio) "
                                "ORDER BY n.id DESC LIMIT ?", (limite,)).fetchall()
