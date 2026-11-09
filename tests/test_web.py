import os
import tempfile
import unittest

import datos_demo
from biblioteca.configuracion import Configuracion
from biblioteca.persistencia import conectar
from web import create_app


class TestWeb(unittest.TestCase):
    def setUp(self):
        Configuracion.reiniciar()
        descriptor, self.ruta = tempfile.mkstemp(suffix=".db")
        os.close(descriptor)
        con = conectar(self.ruta)
        datos_demo.cargar(con)
        con.close()
        self.cliente = create_app(self.ruta).test_client()

    def tearDown(self):
        os.remove(self.ruta)
        Configuracion.reiniciar()

    def get(self, url):
        respuesta = self.cliente.get(url)
        self.assertEqual(respuesta.status_code, 200, url)
        return respuesta.get_data(as_text=True)

    def post(self, url, **datos):
        return self.cliente.post(url, data=datos, follow_redirects=True).get_data(as_text=True)

    def test_todas_las_paginas_responden(self):
        for url in ("/", "/sedes", "/sedes/nueva", "/sedes/CEN/editar", "/socios", "/socios/nuevo",
                    "/socios/1001/editar", "/libros", "/libros/nuevo", "/libros/978-950-07-0001-1",
                    "/disponibilidad", "/disponibilidad?sede=CEN", "/prestamos", "/prestamos?todos=1",
                    "/prestamos/nuevo", "/prestamos/nuevo?origen=CEN", "/prestamos/1", "/prestamos/3",
                    "/remitos", "/remitos?estado=Enviado", "/remitos/R-000001", "/reservas", "/reportes",
                    "/notificaciones"):
            self.get(url)

    def test_inexistente_da_404(self):
        self.assertEqual(self.cliente.get("/socios/9999/editar").status_code, 404)

    def test_alta_duplicada_muestra_error(self):
        html = self.post("/socios/nuevo", numero_socio="1001", nombre="Repetido")
        self.assertIn("Ya existe un socio con número 1001", html)

    def test_flujo_prestamo_interbibliotecario(self):
        html = self.post("/prestamos/nuevo", origen="CEN", numero_socio="1002", destino="NOR",
                         ejemplares=["CEN-002-2"])
        self.assertIn("Préstamo registrado", html)
        numero = self.get("/remitos?estado=Pendiente").split('href="/remitos/')[1].split('"')[0]
        self.assertIn("No se puede recibir", self.post(f"/remitos/{numero}/recibir"))
        for op in ("empaquetar", "despachar", "recibir"):
            self.assertIn("registrada", self.post(f"/remitos/{numero}/{op}", observacion="ok"))
        self.assertIn("Entregado", self.get(f"/remitos/{numero}"))

    def test_socio_inhabilitado_no_puede_pedir(self):
        html = self.post("/prestamos/nuevo", origen="NOR", numero_socio="1005", destino="NOR",
                         ejemplares=["NOR-001-1"])
        self.assertIn("inhabilitado", html)


if __name__ == "__main__":
    unittest.main()
