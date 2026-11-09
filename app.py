"""Punto de entrada de la interfaz web.

    pip install -r requirements.txt
    python datos_demo.py     (opcional: crea biblioteca.db con datos de ejemplo)
    python app.py            -> http://127.0.0.1:5000
"""

from web import create_app

app = create_app("biblioteca.db")

if __name__ == "__main__":
    app.run(debug=True)
