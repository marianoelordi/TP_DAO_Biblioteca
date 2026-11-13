import unittest
from datetime import date, timedelta

from biblioteca.excepciones import ReglaNegocioError
from biblioteca.modelos import (
    Catalogo, Ejemplar, Empaquetado, Entregado, Enviado, Libro, Pendiente,
    PrestamoInterbibliotecario, PrestamoLocal, Reserva, ReservaConfirmada, Sede, Socio,
)

HOY = date.today()
VENCE = HOY + timedelta(days=14)


class Escenario(unittest.TestCase):
    def setUp(self):
        self.centro = Sede("S1", "Centro", "Av. Colón 100", "351-111", "8 a 20")
        self.norte = Sede("S2", "Norte", "Monseñor Pablo Cabrera 2000", "351-222", "9 a 18")
        self.socio = Socio("1001", "Ana Pérez")
        self.libro = Libro("978-950-07-0000-1", "Rayuela", "Julio Cortázar")
        self.ej1 = Ejemplar("EJ-1", self.libro, self.centro)
        self.ej2 = Ejemplar("EJ-2", self.libro, self.centro)

    def prestamo(self, destino=None, ejemplares=None, fecha_vencimiento=VENCE):
        ejemplares = ejemplares or [self.ej1]
        if destino is None:
            return PrestamoLocal("P1", self.socio, self.centro, ejemplares, fecha_vencimiento)
        return PrestamoInterbibliotecario("P1", self.socio, self.centro, destino,
                                          ejemplares, fecha_vencimiento)


class TestCatalogoIterator(Escenario):
    def test_recorre_todos_los_ejemplares_y_lanza_stop_iteration(self):
        catalogo = Catalogo()
        catalogo.agregar_ejemplar(self.ej1)
        catalogo.agregar_ejemplar(self.ej2)
        it = catalogo.crear_iterador()
        self.assertTrue(it.has_next())
        self.assertIs(it.next(), self.ej1)
        self.assertIs(it.next(), self.ej2)
        self.assertFalse(it.has_next())
        with self.assertRaises(StopIteration):
            it.next()

    def test_se_puede_usar_en_for(self):
        catalogo = Catalogo()
        catalogo.agregar_ejemplar(self.ej1)
        catalogo.agregar_ejemplar(self.ej2)
        self.assertEqual([e.codigo for e in catalogo], ["EJ-1", "EJ-2"])

    def test_rechaza_ejemplar_duplicado(self):
        catalogo = Catalogo()
        catalogo.agregar_ejemplar(self.ej1)
        with self.assertRaises(ReglaNegocioError):
            catalogo.agregar_ejemplar(Ejemplar("EJ-1", self.libro, self.norte))


class TestPrestamo(Escenario):
    def test_prestamo_local_marca_ejemplares_prestados(self):
        p = self.prestamo(ejemplares=[self.ej1, self.ej2])
        self.assertFalse(p.es_interbibliotecario())
        self.assertTrue(p.esta_activo())
        self.assertFalse(self.ej1.disponible)
        self.assertFalse(self.ej2.disponible)

    def test_socio_inhabilitado(self):
        self.socio.inhabilitar()
        with self.assertRaises(ReglaNegocioError):
            self.prestamo()

    def test_ejemplar_no_disponible(self):
        self.prestamo()
        with self.assertRaises(ReglaNegocioError):
            self.prestamo()  # EJ-1 ya está prestado: no puede tener dos detalles pendientes

    def test_ejemplar_de_otra_sede(self):
        ajeno = Ejemplar("EJ-9", self.libro, self.norte)
        with self.assertRaises(ReglaNegocioError):
            self.prestamo(ejemplares=[ajeno])

    def test_ejemplar_repetido_en_el_mismo_prestamo(self):
        with self.assertRaises(ReglaNegocioError):
            self.prestamo(ejemplares=[self.ej1, self.ej1])

    def test_sede_origen_o_destino_dada_de_baja(self):
        self.norte.baja()
        with self.assertRaises(ReglaNegocioError):
            self.prestamo(destino=self.norte)
        self.norte.alta()
        self.centro.baja()
        with self.assertRaises(ReglaNegocioError):
            self.prestamo(destino=self.norte)

    def test_vencimiento_anterior_al_inicio(self):
        with self.assertRaises(ReglaNegocioError):
            self.prestamo(fecha_vencimiento=HOY)

    def test_controlar_vencimiento(self):
        p = self.prestamo()
        self.assertFalse(p.controlar_vencimiento(VENCE))
        self.assertTrue(p.controlar_vencimiento(VENCE + timedelta(days=1)))
        p.detalles[0].registrar_devolucion(VENCE + timedelta(days=1), "Bueno")
        self.assertFalse(p.controlar_vencimiento(VENCE + timedelta(days=1)))

    def test_interbibliotecario_exige_sedes_distintas(self):
        with self.assertRaises(ReglaNegocioError):
            self.prestamo(destino=self.centro)


class TestMultas(Escenario):
    def setUp(self):
        super().setUp()
        self.p = self.prestamo(ejemplares=[self.ej1, self.ej2])

    def test_sin_atraso_no_hay_multa(self):
        self.assertEqual(self.p.calcular_multa(VENCE), 0)

    def test_multa_por_dia_y_por_ejemplar(self):
        self.assertEqual(self.p.calcular_multa(VENCE + timedelta(days=5)), 2 * 5 * 100)

    def test_ejemplar_devuelto_deja_de_acumular(self):
        self.p.detalles[0].registrar_devolucion(VENCE + timedelta(days=2), "Bueno")
        self.assertEqual(self.p.calcular_multa(VENCE + timedelta(days=5)), 200 + 500)


class TestDevolucion(Escenario):
    def test_prestamo_activo_mientras_haya_pendientes(self):
        p = self.prestamo(ejemplares=[self.ej1, self.ej2])
        p.detalles[0].registrar_devolucion(HOY, "Dañado")
        self.assertTrue(p.esta_activo())
        self.assertTrue(self.ej1.disponible)
        self.assertEqual(self.ej1.estado_fisico, "Dañado")
        p.detalles[1].registrar_devolucion(HOY, "Bueno")
        self.assertFalse(p.esta_activo())

    def test_no_se_devuelve_dos_veces(self):
        p = self.prestamo()
        p.detalles[0].registrar_devolucion(HOY, "Bueno")
        with self.assertRaises(ReglaNegocioError):
            p.detalles[0].registrar_devolucion(HOY, "Bueno")


class TestRemitoState(Escenario):
    def test_prestamo_local_no_genera_remito(self):
        with self.assertRaises(ReglaNegocioError):
            self.prestamo().generar_remito("R-1")

    def test_un_solo_remito_por_prestamo(self):
        p = self.prestamo(destino=self.norte)
        p.generar_remito("R-1")
        with self.assertRaises(ReglaNegocioError):
            p.generar_remito("R-2")

    def test_ciclo_completo_con_trazabilidad_y_ubicacion(self):
        remito = self.prestamo(destino=self.norte).generar_remito("R-1")
        self.assertIsInstance(remito.estado, Pendiente)

        remito.empaquetar()
        self.assertIsInstance(remito.estado, Empaquetado)
        self.assertIsNotNone(remito.fecha_empaquetado)

        remito.despachar(observacion="Sale en camión 3")
        self.assertIsInstance(remito.estado, Enviado)
        self.assertIsNone(self.ej1.ubicacion_actual)  # en tránsito
        self.assertIs(self.ej1.sede_pertenencia, self.centro)

        remito.recibir()
        self.assertIsInstance(remito.estado, Entregado)
        self.assertIs(self.ej1.ubicacion_actual, self.norte)

        self.assertEqual([h.nombre_estado for h in remito.historial],
                         ["Pendiente", "Empaquetado", "Enviado", "Entregado"])
        self.assertEqual([h.sede_ubicacion for h in remito.historial],
                         [self.centro, self.centro, None, self.norte])
        self.assertEqual(remito.historial[2].observacion, "Sale en camión 3")

    def test_transiciones_no_permitidas(self):
        remito = self.prestamo(destino=self.norte).generar_remito("R-1")
        for operacion in (remito.despachar, remito.recibir):
            with self.assertRaises(ReglaNegocioError):
                operacion()
        remito.empaquetar()
        for operacion in (remito.empaquetar, remito.recibir):
            with self.assertRaises(ReglaNegocioError):
                operacion()
        remito.despachar()
        for operacion in (remito.empaquetar, remito.despachar):
            with self.assertRaises(ReglaNegocioError):
                operacion()
        remito.recibir()
        for operacion in (remito.empaquetar, remito.despachar, remito.recibir):
            with self.assertRaises(ReglaNegocioError):
                operacion()
        self.assertEqual(len(remito.historial), 4)  # los rechazos no dejan rastro

    def test_no_se_despacha_hacia_sede_dada_de_baja(self):
        remito = self.prestamo(destino=self.norte).generar_remito("R-1")
        remito.empaquetar()
        self.norte.baja()
        with self.assertRaises(ReglaNegocioError):
            remito.despachar()
        self.assertIsInstance(remito.estado, Empaquetado)


class TestRemitoRetorno(Escenario):
    def entregado(self):
        p = self.prestamo(destino=self.norte, ejemplares=[self.ej1, self.ej2])
        remito = p.generar_remito("R-1")
        remito.empaquetar()
        remito.despachar()
        remito.recibir()
        return p

    def test_no_se_devuelve_antes_de_que_llegue(self):
        p = self.prestamo(destino=self.norte)
        p.generar_remito("R-1")
        with self.assertRaises(ReglaNegocioError):
            p.registrar_devolucion("EJ-1", HOY, "Bueno")

    def test_devuelto_sigue_no_disponible_hasta_volver(self):
        p = self.entregado()
        p.registrar_devolucion("EJ-1", HOY, "Bueno")
        self.assertFalse(self.ej1.disponible)
        with self.assertRaises(ReglaNegocioError):
            p.generar_remito_retorno("R-2")  # EJ-2 sigue pendiente
        p.registrar_devolucion("EJ-2", HOY, "Regular")

        retorno = p.generar_remito_retorno("R-2")
        self.assertIs(retorno.sede_origen, self.norte)
        self.assertIs(retorno.sede_destino, self.centro)
        self.assertEqual(retorno.historial[0].sede_ubicacion, self.norte)
        retorno.empaquetar()
        retorno.despachar()
        self.assertIsNone(self.ej1.ubicacion_actual)
        retorno.recibir()
        self.assertIs(self.ej1.ubicacion_actual, self.centro)
        self.assertTrue(self.ej1.disponible and self.ej2.disponible)
        with self.assertRaises(ReglaNegocioError):
            p.generar_remito_retorno("R-3")

    def test_ejemplar_ajeno_al_prestamo(self):
        p = self.entregado()
        with self.assertRaises(ReglaNegocioError):
            p.registrar_devolucion("EJ-9", HOY, "Bueno")


class TestReserva(Escenario):
    def test_confirmar_reserva(self):
        r = Reserva("R1", self.socio, self.libro, self.centro)
        r.confirmar_reserva()
        self.assertIsInstance(r.estado, ReservaConfirmada)

    def test_reserva_rechazada(self):
        self.socio.inhabilitar()
        with self.assertRaises(ReglaNegocioError):
            Reserva("R1", self.socio, self.libro, self.centro).confirmar_reserva()
        self.socio.habilitar()
        self.centro.baja()
        with self.assertRaises(ReglaNegocioError):
            Reserva("R2", self.socio, self.libro, self.centro).confirmar_reserva()


if __name__ == "__main__":
    unittest.main()
