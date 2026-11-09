class Libro:
    def __init__(self, isbn, titulo, autor):
        self.isbn = isbn
        self.titulo = titulo
        self.autor = autor

    def __repr__(self):
        return f"Libro({self.isbn!r}, {self.titulo!r})"
