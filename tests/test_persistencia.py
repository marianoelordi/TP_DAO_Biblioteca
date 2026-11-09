import unittest
from datetime import date, timedelta

from biblioteca import reportes, servicios as sv
from biblioteca.configuracion import Configuracion
from biblioteca.excepciones import ReglaNegocioError
from biblioteca.modelos import Entregado, Pendiente
from biblioteca.persistencia import Repositorio, conectar


class Base(unittest.TestCase):
    def setUp(self):
        Configuracion.reiniciar()
        self.con = conectar(":memory:")
        repo = Repositorio(self.con)
        sv.alta_sede(repo, "S1", "Centro", "Av. Colón 100", "351-111", "8 a 20")
        sv.alta_sede(repo, "S2", "Norte", "M. P. Cabrera 2000", "351-222", "9 a 18")
        sv.alta_socio(repo, "1001", "Ana Pérez")
        sv.alta_libro(repo, "978-1", "Rayuela", "Julio Cortázar")
        sv.alta_ejemplar(repo, "EJ-1", "978-1", "S1")
        sv.alta_ejemplar(repo, "EJ-2", "978-1", "S1")
        self.con.commit()

    def tearDown(self):
        self.con.close()
        Configuracion.reiniciar()

    def repo(self):
        """Repositorio nuevo: obliga a releer todo desde la base."""
        self.con.commit()
        return Repositorio(self.con)

    def interbibliotecario(self, codigos=("EJ-1",), inicio=None):
        return sv.registrar_prestamo(self.repo(), "1001", "S1", "S2", list(codigos), inicio)

    def avanzar(self, numero, *operaciones):
        for op in operaciones:
            sv.avanzar_remito(self.repo(), numero, op)


class TestDuplicados(Base):
    def test_rechaza_duplicados(self):
        repo = self.repo()
        casos = [
            lambda: sv.alta_sede(repo, "S1", "Otra", "x", "x", "x"),
            lambda: sv.alta_sede(repo, "S9", "Centro", "x", "x", "x"),
            lambda: sv.alta_socio(repo, "1001", "Otro"),
            lambda: sv.alta_libro(repo, "978-1", "Otro", "Otro"),
            lambda: sv.alta_ejemplar(repo, "EJ-1", "978-1", "S2"),
        ]
        for caso in casos:
            with self.assertRaises(ReglaNegocioError):
                caso()

    def test_numero_de_remito_duplicado(self):
        p = self.interbibliotecario()
        repo = self.repo()
        otro = sv.registrar_prestamo(repo, "1001", "S1", "S2", ["EJ-2"])
        self.assertNotEqual(otro.remito.numero_remito, p.remito.numero_remito)
        otro.remito.numero_remito = p.remito.numero_remito
        with self.assertRaises(ReglaNegocioError):
            repo.guardar_prestamo(otro)

    def test_campos_obligatorios(self):
        with self.assertRaises(ReglaNegocioError):
            sv.alta_socio(self.repo(), "2000", "  ")


class TestPersistencia(Base):
    def test_ida_y_vuelta_de_un_prestamo_con_remito(self):
        p = self.interbibliotecario()
        self.avanzar(p.remito.numero_remito, "empaquetar", "despachar")

        repo = self.repo()
        cargado = repo.prestamo(p.id_prestamo)
        self.assertTrue(cargado.es_interbibliotecario())
        self.assertEqual([h.nombre_estado for h in cargado.remito.historial],
                         ["Pendiente", "Empaquetado", "Enviado"])
        ej = repo.ejemplar("EJ-1")
        self.assertIsNone(ej.ubicacion_actual)
        self.assertFalse(ej.disponible)
        self.assertIs(ej.sede_pertenencia, cargado.sede_origen)  # mapa de identidad
        self.assertIs(repo.remito(p.remito.numero_remito), cargado.remito)

    def test_transicion_invalida_desde_la_base(self):
        p = self.interbibliotecario()
        with self.assertRaises(ReglaNegocioError):
            sv.avanzar_remito(self.repo(), p.remito.numero_remito, "recibir")

    def test_ciclo_completo_con_retorno_y_notificaciones(self):
        p = self.interbibliotecario(["EJ-1", "EJ-2"])
        self.avanzar(p.remito.numero_remito, "empaquetar", "despachar", "recibir")
        sv.registrar_devolucion(self.repo(), p.id_prestamo, "EJ-1", "Bueno")
        self.assertIsNone(self.repo().prestamo(p.id_prestamo).remito_retorno)
        sv.registrar_devolucion(self.repo(), p.id_prestamo, "EJ-2", "Dañado")

        retorno = self.repo().prestamo(p.id_prestamo).remito_retorno
        self.assertIsInstance(retorno.estado, Pendiente)
        self.assertFalse(self.repo().ejemplar("EJ-1").disponible)
        self.avanzar(retorno.numero_remito, "empaquetar", "despachar", "recibir")

        repo = self.repo()
        self.assertIsInstance(repo.remito(retorno.numero_remito).estado, Entregado)
        ej2 = repo.ejemplar("EJ-2")
        self.assertTrue(ej2.disponible)
        self.assertEqual(ej2.estado_fisico, "Dañado")
        self.assertEqual(ej2.ubicacion_actual.id_sede, "S1")
        self.assertEqual(len(repo.notificaciones()), 6)

    def test_prestamo_local_y_disponibilidad(self):
        p = sv.registrar_prestamo(self.repo(), "1001", "S1", "S1", ["EJ-1"])
        self.assertIsNone(getattr(p, "remito", None))
        self.assertEqual([e.codigo for e in sv.consultar_disponibilidad(self.repo(), "S1")], ["EJ-2"])
        sv.registrar_devolucion(self.repo(), p.id_prestamo, "EJ-1", "Bueno")
        self.assertEqual(len(sv.consultar_disponibilidad(self.repo(), "S1", "978-1")), 2)

    def test_sede_de_baja_y_socio_inhabilitado(self):
        sv.cambiar_estado_sede(self.repo(), "S2", False)
        with self.assertRaises(ReglaNegocioError):
            self.interbibliotecario()
        sv.cambiar_habilitacion_socio(self.repo(), "1001", False)
        with self.assertRaises(ReglaNegocioError):
            sv.registrar_prestamo(self.repo(), "1001", "S1", "S1", ["EJ-1"])
        self.assertTrue(self.repo().ejemplar("EJ-1").disponible)

    def test_reserva(self):
        r = sv.registrar_reserva(self.repo(), "1001", "978-1", "S1")
        sv.cambiar_estado_reserva(self.repo(), r.id_reserva, "confirmar")
        self.assertEqual(self.repo().reserva(r.id_reserva).estado.nombre, "Confirmada")
        with self.assertRaises(ReglaNegocioError):
            sv.cambiar_estado_reserva(self.repo(), r.id_reserva, "confirmar")


class TestReportes(Base):
    def test_reportes(self):
        inicio = date.today() - timedelta(days=30)
        p = self.interbibliotecario(["EJ-1"], inicio)  # vence a los 21 días: 9 de atraso
        self.avanzar(p.remito.numero_remito, "empaquetar", "despachar")
        repo = self.repo()

        activos, transito = reportes.prestamos_activos_y_en_transito(repo)
        self.assertEqual([a.id_prestamo for a in activos], [p.id_prestamo])
        self.assertEqual(transito[0]["ejemplares"], "EJ-1")

        vencidos, multas = reportes.prestamos_vencidos_y_multas(repo)
        self.assertEqual(vencidos[0]["dias"], 9)
        self.assertEqual(multas[0]["total"], 900)

        self.assertEqual(reportes.libros_mas_solicitados_intersedes(repo)[0]["ejemplares_solicitados"], 1)

        centro = next(f for f in reportes.disponibilidad_por_sede(repo) if f["id_sede"] == "S1")
        self.assertEqual((centro["total"], centro["disponibles"], centro["en_transito"]), (2, 1, 1))

        self.avanzar(p.remito.numero_remito, "recibir")
        mov = reportes.movimientos_entre_sedes(self.repo())[0]
        self.assertEqual((mov["origen"], mov["destino"], mov["entregados"]), ("Centro", "Norte", 1))
        self.assertIsNotNone(mov["horas_promedio_transito"])


if __name__ == "__main__":
    unittest.main()
