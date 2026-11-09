from biblioteca.observador import Observador


class NotificadorSocio(Observador):
    """Observa remitos y genera un aviso al socio en cada cambio de estado.

    Por ahora guarda los mensajes en una lista; el canal real (mail, pantalla)
    se define cuando exista la interfaz.
    """

    def __init__(self):
        self.notificaciones = []

    def actualizar(self, remito):
        ultimo = remito.historial[-1]
        socio = remito.prestamo.socio
        mensaje = (f"Remito {remito.numero_remito}: su préstamo {remito.prestamo.id_prestamo} "
                   f"pasó a estado {ultimo.nombre_estado}.")
        self.notificaciones.append((socio, mensaje))
