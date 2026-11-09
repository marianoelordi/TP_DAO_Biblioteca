"""Patrón State: cada estado decide qué operaciones admite y a qué estado transiciona.

Transiciones válidas:
    Pendiente --empaquetar()--> Empaquetado --despachar()--> Enviado --recibir()--> Entregado
Cualquier otra operación se rechaza con ReglaNegocioError.
"""

from abc import ABC, abstractmethod
from datetime import datetime

from biblioteca.excepciones import ReglaNegocioError


class EstadoRemito(ABC):
    nombre = ""

    @abstractmethod
    def empaquetar(self, remito, observacion=""):
        pass

    @abstractmethod
    def despachar(self, remito, observacion=""):
        pass

    @abstractmethod
    def recibir(self, remito, observacion=""):
        pass

    def _rechazar(self, operacion):
        raise ReglaNegocioError(f"No se puede {operacion} un remito en estado {self.nombre}.")


class Pendiente(EstadoRemito):
    nombre = "Pendiente"

    def empaquetar(self, remito, observacion=""):
        remito.fecha_empaquetado = datetime.now()
        remito.cambiar_estado(Empaquetado(), remito.sede_origen, observacion)

    def despachar(self, remito, observacion=""):
        self._rechazar("despachar")

    def recibir(self, remito, observacion=""):
        self._rechazar("recibir")


class Empaquetado(EstadoRemito):
    nombre = "Empaquetado"

    def empaquetar(self, remito, observacion=""):
        self._rechazar("empaquetar")

    def despachar(self, remito, observacion=""):
        remito.prestamo.validar_sedes_activas()
        remito.fecha_despacho = datetime.now()
        for ejemplar in remito.prestamo.ejemplares():
            ejemplar.ubicacion_actual = None  # en tránsito
        remito.cambiar_estado(Enviado(), None, observacion)

    def recibir(self, remito, observacion=""):
        self._rechazar("recibir")


class Enviado(EstadoRemito):
    nombre = "Enviado"

    def empaquetar(self, remito, observacion=""):
        self._rechazar("empaquetar")

    def despachar(self, remito, observacion=""):
        self._rechazar("despachar")

    def recibir(self, remito, observacion=""):
        destino = remito.sede_destino
        remito.fecha_recepcion = datetime.now()
        for ejemplar in remito.prestamo.ejemplares():
            ejemplar.ubicacion_actual = destino
            if remito.es_retorno():
                ejemplar.marcar_disponible()  # volvió a su sede: se puede prestar otra vez
        remito.cambiar_estado(Entregado(), destino, observacion)


class Entregado(EstadoRemito):
    nombre = "Entregado"

    def empaquetar(self, remito, observacion=""):
        self._rechazar("empaquetar")

    def despachar(self, remito, observacion=""):
        self._rechazar("despachar")

    def recibir(self, remito, observacion=""):
        self._rechazar("recibir")
