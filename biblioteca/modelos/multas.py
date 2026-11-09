"""Patrón Strategy: forma de calcular la multa por atraso en la devolución.

La estrategia se elige desde afuera (Configuracion), no la decide el Prestamo.
"""

from abc import ABC, abstractmethod


class EstrategiaMulta(ABC):
    @abstractmethod
    def calcular(self, dias_atraso):
        pass


class SinMulta(EstrategiaMulta):
    def calcular(self, dias_atraso):
        return 0


class MultaPorDia(EstrategiaMulta):
    def __init__(self, monto_diario):
        self.monto_diario = monto_diario

    def calcular(self, dias_atraso):
        return dias_atraso * self.monto_diario


class MultaConTope(EstrategiaMulta):
    """Monto diario, pero sin superar un máximo por ejemplar."""

    def __init__(self, monto_diario, tope):
        self.monto_diario = monto_diario
        self.tope = tope

    def calcular(self, dias_atraso):
        return min(dias_atraso * self.monto_diario, self.tope)
