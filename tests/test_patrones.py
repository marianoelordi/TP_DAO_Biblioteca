import unittest

from biblioteca.excepciones import ReglaNegocioError
from biblioteca.modelos import (
    Catalogo, Ejemplar, Libro, Reserva, ReservaCancelada, ReservaCumplida, Sede, Socio,
)


class Escenario(unittest.TestCase):
    def setUp(self):
        self.centro = Sede("S1", "Centro", "Av. Colón 100", "351-111", "8 a 20")
        self.norte = Sede("S2", "Norte", "M. P. Cabrera 2000", "351-222", "9 a 18")
        self.socio = Socio("1001", "Ana Pérez")
        self.libro = Libro("978-950-07-0000-1", "Rayuela", "Julio Cortázar")
        self.ej1 = Ejemplar("EJ-1", self.libro, self.centro)
        self.ej2 = Ejemplar("EJ-2", self.libro, self.centro)


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


if __name__ == "__main__":
    unittest.main()
