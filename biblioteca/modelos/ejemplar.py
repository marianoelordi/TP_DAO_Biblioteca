class Ejemplar:
    """Copia física de un Libro.

    Se distingue la sede de pertenencia (fija) de la ubicación actual, que es
    None mientras el ejemplar está en tránsito entre sedes.
    """

    def __init__(self, codigo, libro, sede_pertenencia, estado_fisico="Bueno"):
        self.codigo = codigo
        self.libro = libro
        self.sede_pertenencia = sede_pertenencia
        self.ubicacion_actual = sede_pertenencia
        self.estado_fisico = estado_fisico
        self.disponible = True

    def marcar_disponible(self):
        self.disponible = True

    def marcar_prestado(self):
        self.disponible = False

    def pertenece_a_sede(self, sede):
        return self.sede_pertenencia is sede

    def __repr__(self):
        return f"Ejemplar({self.codigo!r}, {self.libro.titulo!r})"
