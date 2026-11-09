class Socio:
    def __init__(self, numero_socio, nombre, inhabilitado=False):
        self.numero_socio = numero_socio
        self.nombre = nombre
        self.inhabilitado = inhabilitado

    def habilitar(self):
        self.inhabilitado = False

    def inhabilitar(self):
        self.inhabilitado = True

    def esta_habilitado(self):
        return not self.inhabilitado

    def __repr__(self):
        return f"Socio({self.numero_socio!r}, {self.nombre!r})"
