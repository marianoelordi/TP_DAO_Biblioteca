"""Patrón Factory: el cliente pide un préstamo sin conocer la clase concreta.

La fábrica decide entre PrestamoLocal y PrestamoInterbibliotecario y calcula la
fecha de vencimiento con el plazo configurado para cada tipo.
"""

from datetime import date, timedelta

from biblioteca.configuracion import Configuracion
from biblioteca.modelos.prestamo import PrestamoInterbibliotecario, PrestamoLocal


class FabricaPrestamos:
    @staticmethod
    def crear_prestamo(id_prestamo, socio, sede_origen, sede_destino, ejemplares, fecha_inicio=None):
        config = Configuracion()
        inicio = fecha_inicio or date.today()
        if sede_origen is sede_destino:
            vence = inicio + timedelta(days=config.plazo_prestamo_local_dias)
            return PrestamoLocal(id_prestamo, socio, sede_origen, ejemplares, vence, inicio)
        vence = inicio + timedelta(days=config.plazo_prestamo_interbibliotecario_dias)
        return PrestamoInterbibliotecario(id_prestamo, socio, sede_origen, sede_destino,
                                          ejemplares, vence, inicio)
