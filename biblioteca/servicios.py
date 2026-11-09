"""Casos de uso: cargan objetos del Repositorio, aplican la lógica del dominio y guardan.

No hacen commit: la transacción la cierra quien llama (la interfaz web), así una
ReglaNegocioError deja la base sin cambios.
"""

from datetime import date

from biblioteca.excepciones import ReglaNegocioError
from biblioteca.modelos import Ejemplar, Libro, Reserva, Sede, Socio
from biblioteca.modelos.fabrica_prestamos import FabricaPrestamos
from biblioteca.notificaciones import NotificadorSocio

ESTADOS_FISICOS = ("Bueno", "Regular", "Dañado")


def _requerido(**campos):
    for nombre, valor in campos.items():
        if not (valor or "").strip():
            raise ReglaNegocioError(f"El campo {nombre.replace('_', ' ')} es obligatorio.")


# ---- Sedes, socios y catálogo (ABM) -------------------------------------------
def alta_sede(repo, id_sede, nombre, direccion, contacto, horarios):
    _requerido(codigo=id_sede, nombre=nombre, direccion=direccion, contacto=contacto, horarios=horarios)
    repo.agregar_sede(Sede(id_sede.strip(), nombre.strip(), direccion.strip(), contacto.strip(),
                           horarios.strip()))


def modificar_sede(repo, id_sede, nombre, direccion, contacto, horarios):
    _requerido(nombre=nombre, direccion=direccion, contacto=contacto, horarios=horarios)
    sede = repo.sede(id_sede)
    sede.nombre, sede.direccion = nombre.strip(), direccion.strip()
    sede.contacto, sede.horarios = contacto.strip(), horarios.strip()
    repo.guardar_sede(sede)


def cambiar_estado_sede(repo, id_sede, activa):
    sede = repo.sede(id_sede)
    sede.alta() if activa else sede.baja()
    repo.guardar_sede(sede)


def alta_socio(repo, numero_socio, nombre):
    _requerido(numero_de_socio=numero_socio, nombre=nombre)
    repo.agregar_socio(Socio(numero_socio.strip(), nombre.strip()))


def modificar_socio(repo, numero_socio, nombre):
    _requerido(nombre=nombre)
    socio = repo.socio(numero_socio)
    socio.nombre = nombre.strip()
    repo.guardar_socio(socio)


def cambiar_habilitacion_socio(repo, numero_socio, habilitado):
    socio = repo.socio(numero_socio)
    socio.habilitar() if habilitado else socio.inhabilitar()
    repo.guardar_socio(socio)


def alta_libro(repo, isbn, titulo, autor):
    _requerido(isbn=isbn, titulo=titulo, autor=autor)
    repo.agregar_libro(Libro(isbn.strip(), titulo.strip(), autor.strip()))


def modificar_libro(repo, isbn, titulo, autor):
    _requerido(titulo=titulo, autor=autor)
    libro = repo.libro(isbn)
    libro.titulo, libro.autor = titulo.strip(), autor.strip()
    repo.guardar_libro(libro)


def alta_ejemplar(repo, codigo, isbn, id_sede, estado_fisico="Bueno"):
    _requerido(codigo=codigo)
    if estado_fisico not in ESTADOS_FISICOS:
        raise ReglaNegocioError(f"Estado físico inválido: {estado_fisico}.")
    sede = repo.sede(id_sede)
    if not sede.esta_activa():
        raise ReglaNegocioError(f"La sede {sede.nombre} está dada de baja.")
    repo.agregar_ejemplar(Ejemplar(codigo.strip(), repo.libro(isbn), sede, estado_fisico))


# ---- Disponibilidad (Iterator) -------------------------------------------------
def consultar_disponibilidad(repo, id_sede, isbn=None):
    """Ejemplares disponibles de una sede, recorridos con el iterador del Catalogo."""
    catalogo = repo.catalogo(isbn or None)
    return list(catalogo.crear_iterador_disponibles(repo.sede(id_sede)))


# ---- Préstamos, remitos y devoluciones ----------------------------------------
def registrar_prestamo(repo, numero_socio, id_sede_origen, id_sede_destino, codigos, fecha_inicio=None):
    _requerido(socio=numero_socio, sede_de_origen=id_sede_origen, sede_de_destino=id_sede_destino)
    if not codigos:
        raise ReglaNegocioError("Seleccione al menos un ejemplar.")
    prestamo = FabricaPrestamos.crear_prestamo(
        repo.siguiente_id_prestamo(), repo.socio(numero_socio), repo.sede(id_sede_origen),
        repo.sede(id_sede_destino), [repo.ejemplar(c) for c in codigos], fecha_inicio)
    if prestamo.es_interbibliotecario():
        # El remito se genera al registrar el préstamo: así existe antes del despacho.
        prestamo.generar_remito(repo.siguiente_numero_remito())
    repo.guardar_prestamo(prestamo)
    return prestamo


def avanzar_remito(repo, numero_remito, operacion, observacion=""):
    """operacion: 'empaquetar', 'despachar' o 'recibir' (el estado actual decide si se admite)."""
    if operacion not in ("empaquetar", "despachar", "recibir"):
        raise ReglaNegocioError(f"Operación desconocida: {operacion}.")
    remito = repo.remito(numero_remito)
    notificador = NotificadorSocio()
    remito.agregar_observador(notificador)
    getattr(remito, operacion)(observacion.strip())
    remito.quitar_observador(notificador)
    repo.guardar_prestamo(remito.prestamo)
    repo.guardar_notificaciones(notificador)
    return remito


def registrar_devolucion(repo, id_prestamo, codigo_ejemplar, estado_fisico, fecha=None):
    """Si es interbibliotecario y ya se devolvió todo, genera el remito de retorno."""
    if estado_fisico not in ESTADOS_FISICOS:
        raise ReglaNegocioError(f"Estado físico inválido: {estado_fisico}.")
    if fecha and fecha > date.today():
        raise ReglaNegocioError("La fecha de devolución no puede ser futura.")
    prestamo = repo.prestamo(id_prestamo)
    prestamo.registrar_devolucion(codigo_ejemplar, fecha or date.today(), estado_fisico)
    if prestamo.es_interbibliotecario() and not prestamo.esta_activo():
        prestamo.generar_remito_retorno(repo.siguiente_numero_remito())
    repo.guardar_prestamo(prestamo)
    return prestamo


# ---- Reservas (State) ----------------------------------------------------------
def registrar_reserva(repo, numero_socio, isbn, id_sede):
    socio, sede = repo.socio(numero_socio), repo.sede(id_sede)
    Reserva.validar_reserva(socio, sede)
    reserva = Reserva(repo.siguiente_id_reserva(), socio, repo.libro(isbn), sede)
    repo.guardar_reserva(reserva)
    return reserva


def cambiar_estado_reserva(repo, id_reserva, operacion):
    acciones = {"confirmar": "confirmar_reserva", "cancelar": "cancelar", "cumplir": "cumplir"}
    if operacion not in acciones:
        raise ReglaNegocioError(f"Operación desconocida: {operacion}.")
    reserva = repo.reserva(id_reserva)
    getattr(reserva, acciones[operacion])()
    repo.guardar_reserva(reserva)
    return reserva
