"""Carga datos de ejemplo usando los mismos casos de uso que la interfaz.

    python datos_demo.py            -> recrea biblioteca.db con datos de ejemplo
"""

import sys
from datetime import date, timedelta
from pathlib import Path

from biblioteca import servicios as sv
from biblioteca.persistencia import Repositorio, conectar

SEDES = [
    ("CEN", "Biblioteca Central", "Av. Colón 100", "351-4111111 · central@red.org", "Lun a Vie 8 a 20"),
    ("NOR", "Sede Norte", "Monseñor Pablo Cabrera 2000", "351-4222222 · norte@red.org", "Lun a Vie 9 a 18"),
    ("SUR", "Sede Sur", "Av. Vélez Sarsfield 3500", "351-4333333 · sur@red.org", "Lun a Sáb 9 a 17"),
]
SOCIOS = [("1001", "Ana Pérez"), ("1002", "Bruno Díaz"), ("1003", "Carla Gómez"),
          ("1004", "Diego Fernández"), ("1005", "Elena Ruiz")]
LIBROS = [
    ("978-950-07-0001-1", "Rayuela", "Julio Cortázar", {"CEN": 3, "NOR": 1}),
    ("978-950-07-0002-8", "Ficciones", "Jorge Luis Borges", {"CEN": 2, "SUR": 1}),
    ("978-950-07-0003-5", "El túnel", "Ernesto Sabato", {"NOR": 2}),
    ("978-950-07-0004-2", "Martín Fierro", "José Hernández", {"CEN": 1, "NOR": 1, "SUR": 2}),
    ("978-950-07-0005-9", "Cien años de soledad", "Gabriel García Márquez", {"CEN": 2, "SUR": 1}),
    ("978-950-07-0006-6", "Clean Code", "Robert C. Martin", {"CEN": 2}),
    ("978-950-07-0007-3", "Patrones de diseño", "Gamma, Helm, Johnson, Vlissides", {"CEN": 1, "SUR": 1}),
]


def _ejemplar(repo, sede, isbn):
    """Primer ejemplar disponible de ese libro en esa sede."""
    return next(e.codigo for e in sv.consultar_disponibilidad(repo, sede, isbn))


def _simular_viaje(con, numero_remito, dias_atras, horas_transito):
    """Mueve hacia atrás las fechas de un remito para que el reporte de tránsito tenga datos."""
    recepcion = f"-{dias_atras * 24} hours"
    despacho = f"-{dias_atras * 24 + horas_transito} hours"
    empaque = f"-{dias_atras * 24 + horas_transito + 3} hours"
    for estado, desfase, columna in (("Pendiente", f"-{dias_atras * 24 + horas_transito + 20} hours", "fecha_creacion"),
                                     ("Empaquetado", empaque, "fecha_empaquetado"),
                                     ("Enviado", despacho, "fecha_despacho"),
                                     ("Entregado", recepcion, "fecha_recepcion")):
        con.execute(f"UPDATE remito SET {columna} = strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime', ?) "
                    f"WHERE numero_remito = ?", (desfase, numero_remito))
        con.execute("UPDATE historial_remito SET fecha_hora = strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime', ?) "
                    "WHERE numero_remito = ? AND nombre_estado = ?", (desfase, numero_remito, estado))


def cargar(con):
    repo = Repositorio(con)
    for sede in SEDES:
        sv.alta_sede(repo, *sede)
    for socio in SOCIOS:
        sv.alta_socio(repo, *socio)
    for isbn, titulo, autor, por_sede in LIBROS:
        sv.alta_libro(repo, isbn, titulo, autor)
        for id_sede, cantidad in por_sede.items():
            for i in range(cantidad):
                sv.alta_ejemplar(repo, f"{id_sede}-{isbn[-5:-2]}-{i + 1}", isbn, id_sede)
    hoy = date.today()

    # Préstamo local vigente y otro local vencido (con multa).
    sv.registrar_prestamo(repo, "1001", "CEN", "CEN", [_ejemplar(repo, "CEN", LIBROS[5][0])])
    sv.registrar_prestamo(repo, "1002", "CEN", "CEN", [_ejemplar(repo, "CEN", LIBROS[1][0])],
                          hoy - timedelta(days=20))

    # Interbibliotecario completo: ida, devolución y retorno a la sede de origen.
    p = sv.registrar_prestamo(repo, "1003", "CEN", "NOR", [_ejemplar(repo, "CEN", LIBROS[0][0])],
                              hoy - timedelta(days=12))
    for op in ("empaquetar", "despachar", "recibir"):
        sv.avanzar_remito(repo, p.remito.numero_remito, op, "Viaje en camioneta de la red" if op == "despachar" else "")
    sv.registrar_devolucion(repo, p.id_prestamo, p.detalles[0].ejemplar.codigo, "Regular", hoy - timedelta(days=3))
    for op in ("empaquetar", "despachar", "recibir"):
        sv.avanzar_remito(repo, p.remito_retorno.numero_remito, op)
    _simular_viaje(con, p.remito.numero_remito, 10, 26)
    _simular_viaje(con, p.remito_retorno.numero_remito, 1, 30)

    # Interbibliotecario entregado y vencido (el socio todavía no lo devolvió).
    p = sv.registrar_prestamo(repo, "1004", "SUR", "CEN", [_ejemplar(repo, "SUR", LIBROS[3][0]),
                                                           _ejemplar(repo, "SUR", LIBROS[4][0])],
                              hoy - timedelta(days=25))
    for op in ("empaquetar", "despachar", "recibir"):
        sv.avanzar_remito(repo, p.remito.numero_remito, op)
    _simular_viaje(con, p.remito.numero_remito, 22, 48)

    # Interbibliotecario en tránsito y otro recién solicitado.
    p = sv.registrar_prestamo(repo, "1001", "CEN", "SUR", [_ejemplar(repo, "CEN", LIBROS[0][0])])
    sv.avanzar_remito(repo, p.remito.numero_remito, "empaquetar")
    sv.avanzar_remito(repo, p.remito.numero_remito, "despachar", "Sale con el reparto de la tarde")
    sv.registrar_prestamo(repo, "1005", "NOR", "CEN", [_ejemplar(repo, "NOR", LIBROS[2][0])])

    # Reservas en distintos estados y un socio inhabilitado.
    r = sv.registrar_reserva(repo, "1002", LIBROS[0][0], "NOR")
    sv.cambiar_estado_reserva(repo, r.id_reserva, "confirmar")
    sv.registrar_reserva(repo, "1003", LIBROS[6][0], "SUR")
    sv.cambiar_habilitacion_socio(repo, "1005", False)
    con.commit()


if __name__ == "__main__":
    ruta = Path(sys.argv[1] if len(sys.argv) > 1 else "biblioteca.db")
    ruta.unlink(missing_ok=True)
    conexion = conectar(ruta)
    cargar(conexion)
    conexion.close()
    print(f"Datos de ejemplo cargados en {ruta}.")
