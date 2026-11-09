import unittest
from datetime import date, timedelta

from biblioteca.configuracion import Configuracion
from biblioteca.excepciones import ReglaNegocioError
from biblioteca.modelos import (
    Catalogo, Ejemplar, Libro, MultaConTope, MultaPorDia, PrestamoInterbibliotecario,
    PrestamoLocal, Reserva, ReservaCancelada, ReservaCumplida, Sede, SinMulta, Socio,
)
from biblioteca.modelos.fabrica_prestamos import FabricaPrestamos
from biblioteca.notificaciones import NotificadorSocio

HOY = date(2026, 11, 2)


class Escenario(unittest.TestCase):
    def setUp(self):
        Configuracion.reiniciar()
        self.centro = Sede("S1", "Centro", "Av. Colón 100", "351-111", "8 a 20")
        self.norte = Sede("S2", "Norte", "M. P. Cabrera 2000", "351-222", "9 a 18")
        self.socio = Socio("1001", "Ana Pérez")
        self.libro = Libro("978-950-07-0000-1", "Rayuela", "Julio Cortázar")
        self.ej1 = Ejemplar("EJ-1", self.libro, self.centro)
        self.ej2 = Ejemplar("EJ-2", self.libro, self.centro)

    def tearDown(self):
        Configuracion.reiniciar()


class TestSingleton(Escenario):
    def test_misma_instancia_y_estado_compartido(self):
        a = Configuracion()
        a.plazo_prestamo_local_dias = 7
        b = Configuracion()
        self.assertIs(a, b)
        self.assertEqual(b.plazo_prestamo_local_dias, 7)


class TestFactory(Escenario):
    def test_crea_prestamo_local_con_plazo_configurado(self):
        p = FabricaPrestamos.crear_prestamo("P1", self.socio, self.centro, self.centro,
                                            [self.ej1], HOY)
        self.assertIsInstance(p, PrestamoLocal)
        self.assertEqual(p.fecha_vencimiento, HOY + timedelta(days=14))

    def test_crea_prestamo_interbibliotecario_con_plazo_configurado(self):
        Configuracion().plazo_prestamo_interbibliotecario_dias = 30
        p = FabricaPrestamos.crear_prestamo("P1", self.socio, self.centro, self.norte,
                                            [self.ej1], HOY)
        self.assertIsInstance(p, PrestamoInterbibliotecario)
        self.assertEqual(p.fecha_vencimiento, HOY + timedelta(days=30))

    def test_interbibliotecario_exige_sedes_distintas(self):
        with self.assertRaises(ReglaNegocioError):
            PrestamoInterbibliotecario("P1", self.socio, self.centro, self.centro,
                                       [self.ej1], HOY + timedelta(days=5), HOY)


class TestStrategyMultas(Escenario):
    def setUp(self):
        super().setUp()
        self.p = PrestamoLocal("P1", self.socio, self.centro, [self.ej1, self.ej2],
                               HOY + timedelta(days=10), HOY)
        self.vence = self.p.fecha_vencimiento

    def test_sin_atraso_no_hay_multa(self):
        self.assertEqual(self.p.calcular_multa(MultaPorDia(100), self.vence), 0)

    def test_estrategias_intercambiables(self):
        fecha = self.vence + timedelta(days=5)  # 2 ejemplares x 5 días
        self.assertEqual(self.p.calcular_multa(MultaPorDia(100), fecha), 1000)
        self.assertEqual(self.p.calcular_multa(MultaConTope(100, 300), fecha), 600)
        self.assertEqual(self.p.calcular_multa(SinMulta(), fecha), 0)

    def test_ejemplar_devuelto_deja_de_acumular(self):
        self.p.detalles[0].registrar_devolucion(self.vence + timedelta(days=2), "Bueno")
        fecha = self.vence + timedelta(days=5)
        self.assertEqual(self.p.calcular_multa(MultaPorDia(100), fecha), 200 + 500)

    def test_estrategia_tomada_de_la_configuracion(self):
        Configuracion().estrategia_multa = MultaPorDia(50)
        fecha = self.vence + timedelta(days=1)
        self.assertEqual(self.p.calcular_multa(Configuracion().estrategia_multa, fecha), 100)


class TestIteratorDisponibles(Escenario):
    def test_solo_disponibles_de_la_sede(self):
        ej_norte = Ejemplar("EJ-3", self.libro, self.norte)
        catalogo = Catalogo()
        for e in (self.ej1, ej_norte, self.ej2):
            catalogo.agregar_ejemplar(e)
        self.ej1.marcar_prestado()
        it = catalogo.crear_iterador_disponibles(self.centro)
        self.assertIs(it.next(), self.ej2)
        self.assertFalse(it.has_next())
        with self.assertRaises(StopIteration):
            it.next()
        self.assertEqual(list(catalogo.crear_iterador_disponibles(self.norte)), [ej_norte])


class TestStateReserva(Escenario):
    def test_ciclo_confirmar_y_cumplir(self):
        r = Reserva("R1", self.socio, self.libro, self.centro)
        r.confirmar_reserva()
        r.cumplir()
        self.assertIsInstance(r.estado, ReservaCumplida)
        for operacion in (r.confirmar_reserva, r.cancelar, r.cumplir):
            with self.assertRaises(ReglaNegocioError):
                operacion()

    def test_no_se_cumple_sin_confirmar(self):
        r = Reserva("R1", self.socio, self.libro, self.centro)
        with self.assertRaises(ReglaNegocioError):
            r.cumplir()

    def test_cancelar(self):
        r = Reserva("R1", self.socio, self.libro, self.centro)
        r.confirmar_reserva()
        r.cancelar()
        self.assertIsInstance(r.estado, ReservaCancelada)
        with self.assertRaises(ReglaNegocioError):
            r.confirmar_reserva()


class TestObserverRemito(Escenario):
    def test_socio_notificado_en_cada_cambio_de_estado(self):
        p = PrestamoInterbibliotecario("P1", self.socio, self.centro, self.norte,
                                       [self.ej1], HOY + timedelta(days=21), HOY)
        remito = p.generar_remito("R-1")
        notificador = NotificadorSocio()
        remito.agregar_observador(notificador)

        remito.empaquetar()
        remito.despachar()
        remito.recibir()

        self.assertEqual(len(notificador.notificaciones), 3)
        socio, mensaje = notificador.notificaciones[-1]
        self.assertIs(socio, self.socio)
        self.assertIn("Entregado", mensaje)

    def test_observador_quitado_no_recibe_mas(self):
        p = PrestamoInterbibliotecario("P1", self.socio, self.centro, self.norte,
                                       [self.ej1], HOY + timedelta(days=21), HOY)
        remito = p.generar_remito("R-1")
        notificador = NotificadorSocio()
        remito.agregar_observador(notificador)
        remito.empaquetar()
        remito.quitar_observador(notificador)
        remito.despachar()
        self.assertEqual(len(notificador.notificaciones), 1)

    def test_transicion_rechazada_no_notifica(self):
        p = PrestamoInterbibliotecario("P1", self.socio, self.centro, self.norte,
                                       [self.ej1], HOY + timedelta(days=21), HOY)
        remito = p.generar_remito("R-1")
        notificador = NotificadorSocio()
        remito.agregar_observador(notificador)
        with self.assertRaises(ReglaNegocioError):
            remito.recibir()
        self.assertEqual(notificador.notificaciones, [])


if __name__ == "__main__":
    unittest.main()
