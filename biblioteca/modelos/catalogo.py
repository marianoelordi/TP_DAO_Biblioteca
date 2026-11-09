"""Patrón Iterator: el Catalogo entrega un iterador sin exponer su lista interna."""

from abc import ABC, abstractmethod

from biblioteca.excepciones import ReglaNegocioError


class Iterador(ABC):
    @abstractmethod
    def has_next(self):
        pass

    @abstractmethod
    def next(self):
        pass

    # Protocolo de Python, para poder usar el iterador en un for.
    def __iter__(self):
        return self

    def __next__(self):
        return self.next()


class IteradorEjemplares(Iterador):
    def __init__(self, ejemplares):
        self._ejemplares = ejemplares
        self._posicion = 0

    def has_next(self):
        return self._posicion < len(self._ejemplares)

    def next(self):
        if not self.has_next():
            raise StopIteration
        ejemplar = self._ejemplares[self._posicion]
        self._posicion += 1
        return ejemplar


class IteradorEjemplaresDisponibles(IteradorEjemplares):
    """Recorre solo los ejemplares disponibles que pertenecen a una sede."""

    def __init__(self, ejemplares, sede):
        super().__init__(ejemplares)
        self._sede = sede

    def has_next(self):
        while self._posicion < len(self._ejemplares):
            ejemplar = self._ejemplares[self._posicion]
            if ejemplar.disponible and ejemplar.pertenece_a_sede(self._sede):
                return True
            self._posicion += 1
        return False


class Catalogo:
    def __init__(self):
        self._ejemplares = []

    def agregar_ejemplar(self, ejemplar):
        if any(e.codigo == ejemplar.codigo for e in self._ejemplares):
            raise ReglaNegocioError(f"Ya existe un ejemplar con código {ejemplar.codigo}.")
        self._ejemplares.append(ejemplar)

    def crear_iterador(self):
        return IteradorEjemplares(self._ejemplares)

    def crear_iterador_disponibles(self, sede):
        return IteradorEjemplaresDisponibles(self._ejemplares, sede)

    def __iter__(self):
        return self.crear_iterador()
