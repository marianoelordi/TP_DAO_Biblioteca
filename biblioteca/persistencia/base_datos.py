import sqlite3
from pathlib import Path

ESQUEMA = Path(__file__).with_name("esquema.sql")


def conectar(ruta):
    """Abre la base (la crea si no existe) y aplica el esquema."""
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    conexion.executescript(ESQUEMA.read_text(encoding="utf-8"))
    return conexion
