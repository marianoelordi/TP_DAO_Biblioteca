from datetime import date

from biblioteca.excepciones import ReglaNegocioError
from biblioteca.modelos.estados_reserva import ReservaPendiente


class Reserva:
    """Delega confirmar/cancelar/cumplir en su estado actual (patrón State)."""

    def __init__(self, id_reserva, socio, libro, sede, fecha_reserva=None):
        self.id_reserva = id_reserva
        self.socio = socio
        self.libro = libro
        self.sede = sede
        self.fecha_reserva = fecha_reserva or date.today()
        self._estado = ReservaPendiente()

    @property
    def estado(self):
        return self._estado

    def cambiar_estado(self, nuevo_estado):
        self._estado = nuevo_estado

    @staticmethod
    def validar_reserva(socio, sede):
        if not socio.esta_habilitado():
            raise ReglaNegocioError(f"El socio {socio.numero_socio} está inhabilitado.")
        if not sede.esta_activa():
            raise ReglaNegocioError(f"La sede {sede.nombre} está dada de baja.")

    def confirmar_reserva(self):
        self._estado.confirmar(self)

    def cancelar(self):
        self._estado.cancelar(self)

    def cumplir(self):
        """El socio retiró el libro reservado."""
        self._estado.cumplir(self)
