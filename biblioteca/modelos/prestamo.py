from abc import ABC, abstractmethod
from datetime import date

from biblioteca.excepciones import ReglaNegocioError
from biblioteca.modelos.estados_remito import Entregado
from biblioteca.modelos.remito import Remito


class DetallePrestamo:
    def __init__(self, ejemplar):
        self.ejemplar = ejemplar
        self.fecha_devolucion_real = None
        self.estado_fisico_devuelto = None

    def esta_pendiente(self):
        return self.fecha_devolucion_real is None

    def registrar_devolucion(self, fecha, estado_fisico, liberar=True):
        """`liberar=False` deja el ejemplar no disponible (debe volver a su sede con un remito)."""
        if not self.esta_pendiente():
            raise ReglaNegocioError(f"El ejemplar {self.ejemplar.codigo} ya fue devuelto.")
        self.fecha_devolucion_real = fecha
        self.estado_fisico_devuelto = estado_fisico
        self.ejemplar.estado_fisico = estado_fisico
        if liberar:
            self.ejemplar.marcar_disponible()

    def dias_atraso(self, vencimiento, fecha):
        """Días de atraso a `fecha` (o a la fecha real de devolución, si ya se devolvió)."""
        referencia = self.fecha_devolucion_real or fecha
        return max((referencia - vencimiento).days, 0)


class Prestamo(ABC):
    """Base de PrestamoLocal y PrestamoInterbibliotecario.

    Al crearse valida todas las condiciones y marca los ejemplares como prestados.
    Cada subclase define PLAZO_DIAS, con el que se calcula el vencimiento al registrarlo.
    """

    MULTA_POR_DIA = 100  # $ por día de atraso y por ejemplar (valor provisorio)

    def __init__(self, id_prestamo, socio, sede_origen, sede_destino, ejemplares,
                 fecha_vencimiento, fecha_inicio=None):
        self.id_prestamo = id_prestamo
        self.socio = socio
        self.sede_origen = sede_origen
        self.sede_destino = sede_destino
        self.fecha_inicio = fecha_inicio or date.today()
        self.fecha_vencimiento = fecha_vencimiento

        self.validar_condiciones(ejemplares)
        self.detalles = [DetallePrestamo(e) for e in ejemplares]
        for ejemplar in ejemplares:
            ejemplar.marcar_prestado()

    @abstractmethod
    def es_interbibliotecario(self):
        pass

    def generar_remito(self, numero_remito):
        raise ReglaNegocioError("Los préstamos locales no generan remito.")

    def validar_sedes_activas(self):
        for sede in (self.sede_origen, self.sede_destino):
            if not sede.esta_activa():
                raise ReglaNegocioError(f"La sede {sede.nombre} está dada de baja.")

    def validar_condiciones(self, ejemplares):
        if not self.socio.esta_habilitado():
            raise ReglaNegocioError(f"El socio {self.socio.numero_socio} está inhabilitado.")
        self.validar_sedes_activas()
        if self.fecha_vencimiento <= self.fecha_inicio:
            raise ReglaNegocioError("La fecha de vencimiento debe ser posterior a la de inicio.")
        if not ejemplares:
            raise ReglaNegocioError("El préstamo debe incluir al menos un ejemplar.")
        if len({e.codigo for e in ejemplares}) != len(ejemplares):
            raise ReglaNegocioError("Un mismo ejemplar no puede figurar dos veces en el préstamo.")
        for ejemplar in ejemplares:
            if not ejemplar.disponible:
                raise ReglaNegocioError(f"El ejemplar {ejemplar.codigo} no está disponible.")
            if not ejemplar.pertenece_a_sede(self.sede_origen):
                raise ReglaNegocioError(
                    f"El ejemplar {ejemplar.codigo} no pertenece a la sede {self.sede_origen.nombre}.")

    def ejemplares(self):
        return [d.ejemplar for d in self.detalles]

    def validar_devolucion(self):
        """Los préstamos locales se pueden devolver en cualquier momento."""

    def registrar_devolucion(self, codigo_ejemplar, fecha, estado_fisico):
        detalle = next((d for d in self.detalles if d.ejemplar.codigo == codigo_ejemplar), None)
        if detalle is None:
            raise ReglaNegocioError(
                f"El ejemplar {codigo_ejemplar} no forma parte del préstamo {self.id_prestamo}.")
        if fecha < self.fecha_inicio:
            raise ReglaNegocioError("La fecha de devolución no puede ser anterior al inicio del préstamo.")
        self.validar_devolucion()
        # En un interbibliotecario el ejemplar sigue sin estar disponible hasta volver a su sede.
        detalle.registrar_devolucion(fecha, estado_fisico, liberar=not self.es_interbibliotecario())

    def esta_activo(self):
        return any(d.esta_pendiente() for d in self.detalles)

    def controlar_vencimiento(self, fecha=None):
        """True si el préstamo sigue activo y ya pasó su fecha de vencimiento."""
        return self.esta_activo() and (fecha or date.today()) > self.fecha_vencimiento

    def calcular_multa(self, fecha=None):
        """Suma la multa de cada ejemplar: MULTA_POR_DIA por cada día de atraso."""
        fecha = fecha or date.today()
        return sum(d.dias_atraso(self.fecha_vencimiento, fecha) * self.MULTA_POR_DIA
                   for d in self.detalles)


class PrestamoLocal(Prestamo):
    PLAZO_DIAS = 14

    def __init__(self, id_prestamo, socio, sede, ejemplares, fecha_vencimiento, fecha_inicio=None):
        super().__init__(id_prestamo, socio, sede, sede, ejemplares, fecha_vencimiento, fecha_inicio)

    def es_interbibliotecario(self):
        return False


class PrestamoInterbibliotecario(Prestamo):
    PLAZO_DIAS = 21

    def __init__(self, id_prestamo, socio, sede_origen, sede_destino, ejemplares,
                 fecha_vencimiento, fecha_inicio=None):
        if sede_origen is sede_destino:
            raise ReglaNegocioError("Un préstamo interbibliotecario requiere sedes distintas.")
        super().__init__(id_prestamo, socio, sede_origen, sede_destino, ejemplares,
                         fecha_vencimiento, fecha_inicio)
        self.remito = None
        self.remito_retorno = None

    def es_interbibliotecario(self):
        return True

    def generar_remito(self, numero_remito):
        if self.remito is not None:
            raise ReglaNegocioError(f"El préstamo {self.id_prestamo} ya tiene un remito.")
        self.validar_sedes_activas()
        self.remito = Remito(numero_remito, self)
        return self.remito

    def validar_devolucion(self):
        if self.remito is None or not isinstance(self.remito.estado, Entregado):
            raise ReglaNegocioError(
                f"El material del préstamo {self.id_prestamo} todavía no llegó a la sede destino.")

    def generar_remito_retorno(self, numero_remito):
        """Remito de vuelta (destino -> origen), una vez devueltos todos los ejemplares."""
        if self.remito_retorno is not None:
            raise ReglaNegocioError(f"El préstamo {self.id_prestamo} ya tiene un remito de retorno.")
        if self.esta_activo():
            raise ReglaNegocioError(f"El préstamo {self.id_prestamo} tiene ejemplares sin devolver.")
        self.validar_sedes_activas()
        self.remito_retorno = Remito(numero_remito, self, Remito.RETORNO)
        return self.remito_retorno
