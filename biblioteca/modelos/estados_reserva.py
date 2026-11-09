"""Patrón State para el ciclo de vida de una Reserva.

    ReservaPendiente --confirmar()--> ReservaConfirmada --cumplir()--> ReservaCumplida
    ReservaPendiente / ReservaConfirmada --cancelar()--> ReservaCancelada
Cumplida y Cancelada son estados finales.
"""

from abc import ABC, abstractmethod

from biblioteca.excepciones import ReglaNegocioError


class EstadoReserva(ABC):
    nombre = ""

    @abstractmethod
    def confirmar(self, reserva):
        pass

    @abstractmethod
    def cancelar(self, reserva):
        pass

    @abstractmethod
    def cumplir(self, reserva):
        pass

    def _rechazar(self, operacion):
        raise ReglaNegocioError(f"No se puede {operacion} una reserva en estado {self.nombre}.")


class ReservaPendiente(EstadoReserva):
    nombre = "Pendiente"

    def confirmar(self, reserva):
        reserva.validar_reserva(reserva.socio, reserva.sede)
        reserva.cambiar_estado(ReservaConfirmada())

    def cancelar(self, reserva):
        reserva.cambiar_estado(ReservaCancelada())

    def cumplir(self, reserva):
        self._rechazar("cumplir")


class ReservaConfirmada(EstadoReserva):
    nombre = "Confirmada"

    def confirmar(self, reserva):
        self._rechazar("confirmar")

    def cancelar(self, reserva):
        reserva.cambiar_estado(ReservaCancelada())

    def cumplir(self, reserva):
        reserva.cambiar_estado(ReservaCumplida())


class ReservaCumplida(EstadoReserva):
    nombre = "Cumplida"

    def confirmar(self, reserva):
        self._rechazar("confirmar")

    def cancelar(self, reserva):
        self._rechazar("cancelar")

    def cumplir(self, reserva):
        self._rechazar("cumplir")


class ReservaCancelada(EstadoReserva):
    nombre = "Cancelada"

    def confirmar(self, reserva):
        self._rechazar("confirmar")

    def cancelar(self, reserva):
        self._rechazar("cancelar")

    def cumplir(self, reserva):
        self._rechazar("cumplir")
