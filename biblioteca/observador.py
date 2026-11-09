"""Patrón Observer: un Sujeto notifica sus cambios a los observadores suscriptos."""

from abc import ABC, abstractmethod


class Observador(ABC):
    @abstractmethod
    def actualizar(self, sujeto):
        pass


class Sujeto:
    def __init__(self):
        self._observadores = []

    def agregar_observador(self, observador):
        if observador not in self._observadores:
            self._observadores.append(observador)

    def quitar_observador(self, observador):
        self._observadores.remove(observador)

    def notificar(self):
        for observador in self._observadores:
            observador.actualizar(self)
