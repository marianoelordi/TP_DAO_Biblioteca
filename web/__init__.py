"""Interfaz web (Flask). Cada petición abre su conexión y su Repositorio; las acciones
que modifican datos hacen commit solo si el dominio no lanzó ReglaNegocioError."""

import sqlite3
from datetime import date, datetime

from flask import Flask, flash, g, redirect, render_template, request, url_for

from biblioteca import reportes, servicios as sv
from biblioteca.excepciones import ReglaNegocioError
from biblioteca.persistencia import Repositorio, conectar

# Próxima operación válida según el estado (las demás las rechaza el patrón State).
OPERACION_REMITO = {"Pendiente": ("empaquetar", "Empaquetar"),
                    "Empaquetado": ("despachar", "Despachar"),
                    "Enviado": ("recibir", "Registrar recepción")}
OPERACIONES_RESERVA = {"Pendiente": [("confirmar", "Confirmar"), ("cancelar", "Cancelar")],
                       "Confirmada": [("cumplir", "Marcar retirada"), ("cancelar", "Cancelar")]}


def create_app(ruta_db="biblioteca.db"):
    app = Flask(__name__)
    app.config.update(SECRET_KEY="tp-dao-grupo-93", RUTA_DB=ruta_db)

    @app.before_request
    def abrir_conexion():
        g.con = conectar(app.config["RUTA_DB"])
        g.repo = Repositorio(g.con)

    @app.teardown_request
    def cerrar_conexion(_error):
        con = g.pop("con", None)
        if con is not None:
            con.close()

    @app.errorhandler(ReglaNegocioError)
    def no_encontrado(error):
        return render_template("error.html", mensaje=str(error)), 404

    @app.template_filter("fecha")
    def formato_fecha(valor):
        if isinstance(valor, str):
            valor = datetime.fromisoformat(valor)
        if isinstance(valor, datetime):
            return valor.strftime("%d/%m/%Y %H:%M")
        return valor.strftime("%d/%m/%Y") if isinstance(valor, date) else "—"

    @app.template_filter("pesos")
    def formato_pesos(valor):
        return f"$ {valor:,.0f}".replace(",", ".")

    @app.context_processor
    def globales():
        return {"hoy": date.today(), "OPERACION_REMITO": OPERACION_REMITO,
                "OPERACIONES_RESERVA": OPERACIONES_RESERVA, "ESTADOS_FISICOS": sv.ESTADOS_FISICOS}

    def ejecutar(accion, mensaje_ok):
        """Corre un caso de uso dentro de una transacción. Devuelve True si se confirmó."""
        try:
            accion()
            g.con.commit()
            flash(mensaje_ok, "ok")
            return True
        except (ReglaNegocioError, sqlite3.IntegrityError) as error:
            g.con.rollback()
            flash(str(error) if isinstance(error, ReglaNegocioError)
                  else "La operación viola una restricción de la base de datos.", "error")
            return False

    def volver(endpoint, **valores):
        return redirect(url_for(endpoint, **valores))

    # ---- Inicio --------------------------------------------------------------
    @app.get("/")
    def inicio():
        _, transito = reportes.prestamos_activos_y_en_transito(g.repo)
        vencidos, _ = reportes.prestamos_vencidos_y_multas(g.repo)
        contar = lambda tabla: g.con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
        resumen = {
            "Sedes": contar("sede"), "Socios": contar("socio"), "Libros": contar("libro"),
            "Ejemplares": contar("ejemplar"),
            "Préstamos activos": len(g.repo.prestamos(solo_activos=True)),
            "Remitos en tránsito": len(transito), "Préstamos vencidos": len(vencidos),
        }
        pendientes = [r for r in g.repo.remitos() if r.estado.nombre in ("Pendiente", "Empaquetado")]
        return render_template("inicio.html", resumen=resumen, pendientes=pendientes)

    # ---- Sedes ---------------------------------------------------------------
    @app.get("/sedes")
    def sedes():
        return render_template("sedes.html", sedes=g.repo.sedes())

    @app.route("/sedes/nueva", methods=["GET", "POST"])
    def sede_nueva():
        if request.method == "POST" and ejecutar(
                lambda: sv.alta_sede(g.repo, request.form["id_sede"], request.form["nombre"], request.form["direccion"],
                                     request.form["contacto"], request.form["horarios"]), "Sede creada."):
            return volver("sedes")
        return render_template("sede_form.html", sede=None, datos=request.form)

    @app.route("/sedes/<id_sede>/editar", methods=["GET", "POST"])
    def sede_editar(id_sede):
        if request.method == "POST" and ejecutar(
                lambda: sv.modificar_sede(g.repo, id_sede, request.form["nombre"], request.form["direccion"],
                                          request.form["contacto"], request.form["horarios"]), "Sede modificada."):
            return volver("sedes")
        sede = g.repo.sede(id_sede)
        return render_template("sede_form.html", sede=sede, datos=request.form or vars(sede))

    @app.post("/sedes/<id_sede>/estado")
    def sede_estado(id_sede):
        activa = request.form["activa"] == "1"
        ejecutar(lambda: sv.cambiar_estado_sede(g.repo, id_sede, activa),
                 "Sede dada de alta." if activa else "Sede dada de baja.")
        return volver("sedes")

    # ---- Socios --------------------------------------------------------------
    @app.get("/socios")
    def socios():
        return render_template("socios.html", socios=g.repo.socios())

    @app.route("/socios/nuevo", methods=["GET", "POST"])
    def socio_nuevo():
        if request.method == "POST" and ejecutar(
                lambda: sv.alta_socio(g.repo, request.form["numero_socio"], request.form["nombre"]), "Socio creado."):
            return volver("socios")
        return render_template("socio_form.html", socio=None, datos=request.form)

    @app.route("/socios/<numero>/editar", methods=["GET", "POST"])
    def socio_editar(numero):
        if request.method == "POST" and ejecutar(
                lambda: sv.modificar_socio(g.repo, numero, request.form["nombre"]), "Socio modificado."):
            return volver("socios")
        socio = g.repo.socio(numero)
        return render_template("socio_form.html", socio=socio, datos=request.form or vars(socio))

    @app.post("/socios/<numero>/habilitacion")
    def socio_habilitacion(numero):
        habilitado = request.form["habilitado"] == "1"
        ejecutar(lambda: sv.cambiar_habilitacion_socio(g.repo, numero, habilitado),
                 "Socio habilitado." if habilitado else "Socio inhabilitado.")
        return volver("socios")

    # ---- Catálogo ------------------------------------------------------------
    @app.get("/libros")
    def libros():
        cantidades = dict(g.con.execute("SELECT isbn, COUNT(*) FROM ejemplar GROUP BY isbn").fetchall())
        return render_template("libros.html", libros=g.repo.libros(), cantidades=cantidades)

    @app.route("/libros/nuevo", methods=["GET", "POST"])
    def libro_nuevo():
        if request.method == "POST" and ejecutar(
                lambda: sv.alta_libro(g.repo, request.form["isbn"], request.form["titulo"], request.form["autor"]), "Libro creado."):
            return volver("libro", isbn=request.form["isbn"].strip())
        return render_template("libro_form.html", libro=None, datos=request.form)

    @app.route("/libros/<isbn>", methods=["GET", "POST"])
    def libro(isbn):
        if request.method == "POST" and ejecutar(
                lambda: sv.modificar_libro(g.repo, isbn, request.form["titulo"], request.form["autor"]), "Libro modificado."):
            return volver("libro", isbn=isbn)
        libro = g.repo.libro(isbn)
        return render_template("libro.html", libro=libro, ejemplares=g.repo.ejemplares(isbn),
                               sedes=g.repo.sedes(solo_activas=True), datos=request.form or vars(libro))

    @app.post("/libros/<isbn>/ejemplares")
    def ejemplar_nuevo(isbn):
        ejecutar(lambda: sv.alta_ejemplar(g.repo, request.form["codigo"], isbn, request.form["id_sede"], request.form["estado_fisico"]),
                 "Ejemplar agregado.")
        return volver("libro", isbn=isbn)

    @app.get("/disponibilidad")
    def disponibilidad():
        id_sede, isbn = request.args.get("sede"), request.args.get("isbn")
        resultado = sv.consultar_disponibilidad(g.repo, id_sede, isbn) if id_sede else None
        return render_template("disponibilidad.html", sedes=g.repo.sedes(), libros=g.repo.libros(),
                               id_sede=id_sede, isbn=isbn, resultado=resultado)

    # ---- Préstamos -----------------------------------------------------------
    @app.get("/prestamos")
    def prestamos():
        solo_activos = request.args.get("todos") is None
        return render_template("prestamos.html", prestamos=g.repo.prestamos(solo_activos),
                               solo_activos=solo_activos)

    @app.route("/prestamos/nuevo", methods=["GET", "POST"])
    def prestamo_nuevo():
        origen = request.values.get("origen")
        if request.method == "POST":
            resultado = {}
            if ejecutar(lambda: resultado.update(p=sv.registrar_prestamo(
                    g.repo, request.form["numero_socio"], origen, request.form["destino"], request.form.getlist("ejemplares"))),
                    "Préstamo registrado."):
                return volver("prestamo", id_prestamo=resultado["p"].id_prestamo)
        disponibles = sv.consultar_disponibilidad(g.repo, origen) if origen else []
        return render_template("prestamo_nuevo.html", origen=origen, disponibles=disponibles,
                               sedes=g.repo.sedes(solo_activas=True),
                               socios=g.repo.socios(solo_habilitados=True), datos=request.form)

    @app.get("/prestamos/<int:id_prestamo>")
    def prestamo(id_prestamo):
        p = g.repo.prestamo(id_prestamo)
        multa = p.calcular_multa()
        return render_template("prestamo.html", p=p, multa=multa)

    @app.post("/prestamos/<int:id_prestamo>/devolucion")
    def devolucion(id_prestamo):
        fecha = date.fromisoformat(request.form["fecha"]) if request.form.get("fecha") else None
        ejecutar(lambda: sv.registrar_devolucion(g.repo, id_prestamo, request.form["codigo"], request.form["estado_fisico"], fecha),
                 f"Devolución del ejemplar {request.form['codigo']} registrada.")
        return volver("prestamo", id_prestamo=id_prestamo)

    # ---- Remitos -------------------------------------------------------------
    @app.get("/remitos")
    def remitos():
        estado = request.args.get("estado") or None
        return render_template("remitos.html", remitos=g.repo.remitos(estado), estado=estado)

    @app.get("/remitos/<numero>")
    def remito(numero):
        return render_template("remito.html", r=g.repo.remito(numero))

    @app.post("/remitos/<numero>/<operacion>")
    def remito_operacion(numero, operacion):
        ejecutar(lambda: sv.avanzar_remito(g.repo, numero, operacion, request.form.get("observacion", "")),
                 f"Remito {numero}: operación '{operacion}' registrada.")
        return volver("remito", numero=numero)

    # ---- Reservas ------------------------------------------------------------
    @app.route("/reservas", methods=["GET", "POST"])
    def reservas():
        if request.method == "POST" and ejecutar(
                lambda: sv.registrar_reserva(g.repo, request.form["numero_socio"], request.form["isbn"], request.form["id_sede"]),
                "Reserva registrada."):
            return volver("reservas")
        return render_template("reservas.html", reservas=g.repo.reservas(), socios=g.repo.socios(),
                               libros=g.repo.libros(), sedes=g.repo.sedes(solo_activas=True))

    @app.post("/reservas/<int:id_reserva>/<operacion>")
    def reserva_operacion(id_reserva, operacion):
        ejecutar(lambda: sv.cambiar_estado_reserva(g.repo, id_reserva, operacion),
                 f"Reserva {id_reserva} actualizada.")
        return volver("reservas")

    # ---- Reportes y notificaciones --------------------------------------------
    @app.get("/reportes")
    def ver_reportes():
        activos, transito = reportes.prestamos_activos_y_en_transito(g.repo)
        vencidos, multas = reportes.prestamos_vencidos_y_multas(g.repo)
        return render_template(
            "reportes.html", activos=activos, transito=transito, vencidos=vencidos, multas=multas,
            solicitados=reportes.libros_mas_solicitados_intersedes(g.repo),
            por_sede=reportes.disponibilidad_por_sede(g.repo),
            movimientos=reportes.movimientos_entre_sedes(g.repo))

    @app.get("/notificaciones")
    def notificaciones():
        return render_template("notificaciones.html", notificaciones=g.repo.notificaciones())

    return app
