from datetime import datetime

from biblioteca.modelos.estados_remito import Pendiente


class HistorialRemito:
    def __init__(self, nombre_estado, sede_ubicacion, observacion=""):
        self.fecha_hora = datetime.now()
        self.nombre_estado = nombre_estado
        self.sede_ubicacion = sede_ubicacion  # None mientras está en tránsito
        self.observacion = observacion

    def __repr__(self):
        return f"HistorialRemito({self.nombre_estado!r}, {self.sede_ubicacion!r})"


class Remito:
    """Remito de un préstamo interbibliotecario.

    Delega empaquetar/despachar/recibir en su estado actual (patrón State).
    Se crea a través de PrestamoInterbibliotecario.generar_remito() (ida: origen -> destino)
    o generar_remito_retorno() (vuelta: destino -> origen, cuando el socio devolvió todo).
    """

    IDA = "Ida"
    RETORNO = "Retorno"

    def __init__(self, numero_remito, prestamo, tipo=IDA):
        self.numero_remito = numero_remito
        self.prestamo = prestamo
        self.tipo = tipo
        self.fecha_creacion = datetime.now()
        self.fecha_empaquetado = None
        self.fecha_despacho = None
        self.fecha_recepcion = None
        self._estado = Pendiente()
        self.historial = []
        self.registrar_trazabilidad(self._estado.nombre, self.sede_origen)

    @property
    def estado(self):
        return self._estado

    def es_retorno(self):
        return self.tipo == Remito.RETORNO

    @property
    def sede_origen(self):
        return self.prestamo.sede_destino if self.es_retorno() else self.prestamo.sede_origen

    @property
    def sede_destino(self):
        return self.prestamo.sede_origen if self.es_retorno() else self.prestamo.sede_destino

    def empaquetar(self, observacion=""):
        self._estado.empaquetar(self, observacion)

    def despachar(self, observacion=""):
        self._estado.despachar(self, observacion)

    def recibir(self, observacion=""):
        self._estado.recibir(self, observacion)

    def cambiar_estado(self, nuevo_estado, sede_actual, observacion=""):
        self._estado = nuevo_estado
        self.registrar_trazabilidad(nuevo_estado.nombre, sede_actual, observacion)

    def registrar_trazabilidad(self, estado, sede, observacion=""):
        self.historial.append(HistorialRemito(estado, sede, observacion))
