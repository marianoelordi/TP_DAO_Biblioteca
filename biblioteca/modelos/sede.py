class Sede:
    def __init__(self, id_sede, nombre, direccion, contacto, horarios, activa=True):
        self.id_sede = id_sede
        self.nombre = nombre
        self.direccion = direccion
        self.contacto = contacto
        self.horarios = horarios
        self.activa = activa

    def alta(self):
        self.activa = True

    def baja(self):
        self.activa = False

    def esta_activa(self):
        return self.activa

    def __repr__(self):
        return f"Sede({self.id_sede!r}, {self.nombre!r})"
