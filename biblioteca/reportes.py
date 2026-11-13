"""Reportes. Los que solo agregan datos se resuelven en SQL; el de multas usa el dominio
porque el monto lo calcula Prestamo.calcular_multa."""

from datetime import date


def prestamos_activos_y_en_transito(repo):
    """RR01: préstamos con ejemplares sin devolver, y remitos con material viajando."""
    activos = repo.prestamos(solo_activos=True)
    en_transito = repo.con.execute("""
        SELECT r.numero_remito, r.tipo, r.fecha_despacho, r.id_prestamo,
               CASE r.tipo WHEN 'Ida' THEN so.nombre ELSE sd.nombre END AS origen,
               CASE r.tipo WHEN 'Ida' THEN sd.nombre ELSE so.nombre END AS destino,
               GROUP_CONCAT(d.codigo_ejemplar, ', ') AS ejemplares
        FROM remito r
        JOIN prestamo p USING (id_prestamo)
        JOIN sede so ON so.id_sede = p.id_sede_origen
        JOIN sede sd ON sd.id_sede = p.id_sede_destino
        JOIN detalle_prestamo d USING (id_prestamo)
        WHERE r.estado = 'Enviado'
        GROUP BY r.numero_remito
        ORDER BY r.fecha_despacho""").fetchall()
    return activos, en_transito


def prestamos_vencidos_y_multas(repo, fecha=None):
    """RR02: préstamos vencidos (activos) y multas acumuladas por socio, a `fecha`."""
    fecha = fecha or date.today()
    vencidos, por_socio = [], {}
    for p in repo.prestamos():
        multa = p.calcular_multa(fecha)
        if p.controlar_vencimiento(fecha):
            vencidos.append({"prestamo": p, "dias": (fecha - p.fecha_vencimiento).days, "multa": multa})
        if multa:
            fila = por_socio.setdefault(p.socio.numero_socio, {"socio": p.socio, "prestamos": 0, "total": 0})
            fila["prestamos"] += 1
            fila["total"] += multa
    multas = sorted(por_socio.values(), key=lambda f: f["total"], reverse=True)
    return vencidos, multas


def libros_mas_solicitados_intersedes(repo, limite=10):
    """RR03: libros con más ejemplares pedidos en préstamos interbibliotecarios."""
    return repo.con.execute("""
        SELECT l.isbn, l.titulo, l.autor,
               COUNT(*) AS ejemplares_solicitados,
               COUNT(DISTINCT p.id_prestamo) AS prestamos,
               COUNT(DISTINCT p.id_sede_destino) AS sedes_destino
        FROM detalle_prestamo d
        JOIN prestamo p USING (id_prestamo)
        JOIN ejemplar e ON e.codigo = d.codigo_ejemplar
        JOIN libro l USING (isbn)
        WHERE p.tipo = 'Interbibliotecario'
        GROUP BY l.isbn
        ORDER BY ejemplares_solicitados DESC, l.titulo
        LIMIT ?""", (limite,)).fetchall()


def disponibilidad_por_sede(repo):
    """RR04: estado del catálogo propio de cada sede."""
    return repo.con.execute("""
        SELECT s.id_sede, s.nombre, s.activa,
               COUNT(e.codigo) AS total,
               COALESCE(SUM(e.disponible), 0) AS disponibles,
               COALESCE(SUM(e.disponible = 0 AND e.id_sede_ubicacion IS NOT NULL), 0) AS no_disponibles,
               COALESCE(SUM(e.id_sede_ubicacion IS NULL AND e.codigo IS NOT NULL), 0) AS en_transito,
               COALESCE(SUM(e.id_sede_ubicacion <> e.id_sede_pertenencia), 0) AS en_otra_sede,
               COUNT(DISTINCT e.isbn) AS titulos
        FROM sede s LEFT JOIN ejemplar e ON e.id_sede_pertenencia = s.id_sede
        GROUP BY s.id_sede
        ORDER BY s.nombre""").fetchall()


def movimientos_entre_sedes(repo):
    """RR06: envíos por par origen/destino y tiempo promedio de tránsito (despacho -> recepción)."""
    return repo.con.execute("""
        SELECT CASE r.tipo WHEN 'Ida' THEN so.nombre ELSE sd.nombre END AS origen,
               CASE r.tipo WHEN 'Ida' THEN sd.nombre ELSE so.nombre END AS destino,
               COUNT(*) AS remitos,
               SUM(r.estado = 'Entregado') AS entregados,
               SUM(r.estado = 'Enviado') AS en_viaje,
               ROUND(AVG(CASE WHEN r.fecha_recepcion IS NOT NULL
                         THEN (julianday(r.fecha_recepcion) - julianday(r.fecha_despacho)) * 24 END), 1)
                   AS horas_promedio_transito
        FROM remito r
        JOIN prestamo p USING (id_prestamo)
        JOIN sede so ON so.id_sede = p.id_sede_origen
        JOIN sede sd ON sd.id_sede = p.id_sede_destino
        GROUP BY origen, destino
        ORDER BY remitos DESC, origen, destino""").fetchall()
