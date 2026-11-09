"""Patrón Singleton: configuración única y compartida por todo el sistema.

Los valores por defecto son provisorios hasta que el grupo defina los reales.
"""

from biblioteca.modelos.multas import MultaPorDia


class Configuracion:
    _instancia = None
    _inicializada = False

    def __new__(cls):
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
        return cls._instancia

    def __init__(self):
        if Configuracion._inicializada:
            return
        self.plazo_prestamo_local_dias = 14
        self.plazo_prestamo_interbibliotecario_dias = 21
        self.estrategia_multa = MultaPorDia(100)
        Configuracion._inicializada = True

    @classmethod
    def reiniciar(cls):
        """Descarta la instancia actual (uso en tests)."""
        cls._instancia = None
        cls._inicializada = False
