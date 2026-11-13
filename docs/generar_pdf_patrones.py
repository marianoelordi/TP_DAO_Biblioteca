"""Genera 'Patrones de diseño aplicados.pdf' a partir del código real del proyecto."""

import sys
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from pygments import lex
from pygments.lexers import PythonLexer
from pygments.token import Token
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    CondPageBreak, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    XPreformatted,
)

RAIZ = Path(sys.argv[1])
SALIDA = RAIZ / "Patrones de diseño aplicados.pdf"

FUENTES = Path("C:/Windows/Fonts")
for nombre, archivo in [("Cuerpo", "calibri.ttf"), ("Cuerpo-N", "calibrib.ttf"), ("Cuerpo-I", "calibrii.ttf"),
                        ("Cuerpo-NI", "calibriz.ttf"), ("Codigo", "consola.ttf"), ("Codigo-N", "consolab.ttf"),
                        ("Codigo-I", "consolai.ttf"), ("Codigo-NI", "consolaz.ttf")]:
    pdfmetrics.registerFont(TTFont(nombre, str(FUENTES / archivo)))
pdfmetrics.registerFontFamily("Cuerpo", normal="Cuerpo", bold="Cuerpo-N", italic="Cuerpo-I", boldItalic="Cuerpo-NI")
pdfmetrics.registerFontFamily("Codigo", normal="Codigo", bold="Codigo-N", italic="Codigo-I", boldItalic="Codigo-NI")

AZUL = colors.HexColor("#1e3a8a")
AZUL_CLARO = colors.HexColor("#dbeafe")
GRIS = colors.HexColor("#6b7280")
GRIS_FONDO = colors.HexColor("#f6f8fa")
BORDE = colors.HexColor("#d0d7de")

E = {
    "titulo": ParagraphStyle("titulo", fontName="Cuerpo-N", fontSize=26, leading=31, textColor=AZUL, alignment=TA_CENTER),
    "subtitulo": ParagraphStyle("subtitulo", fontName="Cuerpo", fontSize=15, leading=20, alignment=TA_CENTER),
    "portada": ParagraphStyle("portada", fontName="Cuerpo", fontSize=11.5, leading=16, alignment=TA_CENTER, textColor=GRIS),
    "h1": ParagraphStyle("h1", fontName="Cuerpo-N", fontSize=17, leading=22, textColor=AZUL, spaceBefore=4, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName="Cuerpo-N", fontSize=12.5, leading=16, textColor=AZUL, spaceBefore=10, spaceAfter=4,
                         keepWithNext=1),
    "p": ParagraphStyle("p", fontName="Cuerpo", fontSize=10.5, leading=14.5, spaceAfter=5),
    "p_sig": ParagraphStyle("p_sig", fontName="Cuerpo", fontSize=10.5, leading=14.5, spaceAfter=5, keepWithNext=1),
    "vineta": ParagraphStyle("vineta", fontName="Cuerpo", fontSize=10.5, leading=14.5, leftIndent=14, bulletIndent=3, spaceAfter=3),
    "celda": ParagraphStyle("celda", fontName="Cuerpo", fontSize=9.5, leading=12),
    "celda_n": ParagraphStyle("celda_n", fontName="Cuerpo-N", fontSize=9.5, leading=12, textColor=colors.white),
    "archivo": ParagraphStyle("archivo", fontName="Codigo", fontSize=8, leading=10, textColor=colors.white),
    "codigo": ParagraphStyle("codigo", fontName="Codigo", fontSize=7.6, leading=9.6),
    "nota": ParagraphStyle("nota", fontName="Cuerpo-I", fontSize=9.5, leading=13, textColor=GRIS, spaceAfter=6),
}

COLORES_TOKEN = [
    (Token.Comment, "#6a737d", "i"), (Token.Literal.String.Doc, "#6a737d", "i"),
    (Token.Literal.String, "#0a7d33", None), (Token.Keyword, "#8250df", "b"),
    (Token.Name.Builtin.Pseudo, "#bf3989", None), (Token.Name.Decorator, "#b35900", None),
    (Token.Name.Function, "#0550ae", "b"), (Token.Name.Class, "#0550ae", "b"),
    (Token.Literal.Number, "#b35900", None), (Token.Name.Builtin, "#0550ae", None),
]


def _formato(tipo):
    for base, color, estilo in COLORES_TOKEN:
        if tipo in base:
            return color, estilo
    return None, None


def resaltar(codigo, primera_linea):
    lineas, actual = [], []
    for tipo, valor in lex(codigo, PythonLexer(stripnl=False)):
        color, estilo = _formato(tipo)
        for i, trozo in enumerate(valor.split("\n")):
            if i:
                lineas.append("".join(actual))
                actual = []
            if not trozo:
                continue
            texto = escape(trozo)
            if estilo:
                texto = f"<{estilo}>{texto}</{estilo}>"
            if color:
                texto = f'<font color="{color}">{texto}</font>'
            actual.append(texto)
    if actual:
        lineas.append("".join(actual))
    while lineas and not lineas[-1].strip():
        lineas.pop()
    ancho = len(str(primera_linea + len(lineas)))
    return "\n".join(f'<font color="#8c959f">{str(primera_linea + i).rjust(ancho)}</font>  {l}'
                     for i, l in enumerate(lineas))


def codigo(ruta, desde, hasta, debe_contener):
    """Extracto real del archivo, con el número de línea original."""
    lineas = (RAIZ / ruta).read_text(encoding="utf-8").splitlines()[desde - 1:hasta]
    while lineas and not lineas[-1].strip():
        lineas.pop()
        hasta -= 1
    texto = "\n".join(lineas)
    assert debe_contener in texto, f"{ruta}:{desde}-{hasta} ya no contiene {debe_contener!r}"
    cabecera = Paragraph(f"{escape(ruta)} · líneas {desde}–{hasta}", E["archivo"])
    cuerpo = XPreformatted(resaltar(texto, desde), E["codigo"])
    tabla = Table([[cabecera], [cuerpo]], colWidths=[17 * cm])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#24292f")),
        ("BACKGROUND", (0, 1), (-1, 1), GRIS_FONDO),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDE),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, 0), 3), ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
        ("TOPPADDING", (0, 1), (-1, 1), 6), ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
    ]))
    # Una tabla de una sola celda no se parte entre páginas, y deja actuar al keepWithNext del párrafo previo.
    bloque = Table([[tabla]], colWidths=[17 * cm])
    bloque.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return [bloque, Spacer(1, 8)]


def tabla(filas, anchos, encabezado=True):
    datos = [[Paragraph(c, E["celda_n"] if encabezado and i == 0 else E["celda"]) for c in fila]
             for i, fila in enumerate(filas)]
    t = Table(datos, colWidths=[a * cm for a in anchos], repeatRows=1 if encabezado else 0)
    estilo = [("GRID", (0, 0), (-1, -1), 0.5, BORDE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
              ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
              ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if encabezado:
        estilo.append(("BACKGROUND", (0, 0), (-1, 0), AZUL))
        estilo += [("BACKGROUND", (0, i), (-1, i), GRIS_FONDO) for i in range(2, len(filas), 2)]
    t.setStyle(TableStyle(estilo))
    return [t, Spacer(1, 8)]


def p(texto):
    return Paragraph(texto, E["p"])


def pc(texto):
    """Párrafo que presenta un código: queda en la misma página que el código."""
    return Paragraph(texto, E["p_sig"])


def h1(texto):
    return [CondPageBreak(6 * cm), Paragraph(texto, E["h1"])]


def h2(texto):
    return [CondPageBreak(3 * cm), Paragraph(texto, E["h2"])]


def vinetas(items):
    return [Paragraph(i, E["vineta"], bulletText="•") for i in items]


def c(texto):
    """Código en línea."""
    return f'<font name="Codigo" size="9.3" color="#0550ae">{escape(texto)}</font>'


# ---- Diagramas -------------------------------------------------------------------
def _flecha(d, x1, y, x2, color=colors.black):
    d.add(Line(x1, y, x2 - 6, y, strokeColor=color, strokeWidth=1.2))
    d.add(Polygon([x2, y, x2 - 7, y + 3.5, x2 - 7, y - 3.5], fillColor=color, strokeColor=color))


def _caja(d, x, y, ancho, alto, texto, fondo, borde=AZUL, negrita=True):
    d.add(Rect(x, y, ancho, alto, rx=7, ry=7, fillColor=fondo, strokeColor=borde, strokeWidth=1.2))
    d.add(String(x + ancho / 2, y + alto / 2 - 4, texto, fontName="Cuerpo-N" if negrita else "Cuerpo",
                 fontSize=10.5, textAnchor="middle"))


def diagrama_estados(estados, operaciones, efectos, titulo_final=None):
    ancho_total, ancho, alto = 17 * cm, 88, 30
    hueco = (ancho_total - 4 * ancho - 4) / 3
    d = Drawing(ancho_total, 132)
    y = 58
    xs = [2 + i * (ancho + hueco) for i in range(4)]
    for i, (x, nombre) in enumerate(zip(xs, estados)):
        final = i == len(estados) - 1
        _caja(d, x, y, ancho, alto, nombre, colors.HexColor("#dcfce7") if final else AZUL_CLARO,
              colors.HexColor("#15803d") if final else AZUL)
    for i in range(3):
        x1, x2 = xs[i] + ancho, xs[i + 1]
        _flecha(d, x1 + 2, y + alto / 2, x2 - 2)
        medio = (x1 + x2) / 2
        d.add(String(medio, y + alto + 6, operaciones[i], fontName="Codigo-N", fontSize=8.5, textAnchor="middle"))
        for j, linea in enumerate(efectos[i]):
            d.add(String(medio, y - 12 - j * 10, linea, fontName="Cuerpo", fontSize=8, textAnchor="middle",
                         fillColor=GRIS))
    d.add(String(ancho_total / 2, 122, "Cualquier otra operación en cualquier estado → ReglaNegocioError "
                 "(no cambia el estado ni deja rastro en el historial)",
                 fontName="Cuerpo-I", fontSize=8.5, textAnchor="middle", fillColor=colors.HexColor("#b91c1c")))
    if titulo_final:
        d.add(String(xs[3] + ancho / 2, y - 12, titulo_final, fontName="Cuerpo-I", fontSize=8,
                     textAnchor="middle", fillColor=GRIS))
    return [d, Spacer(1, 6)]


def diagrama_reserva():
    d = Drawing(17 * cm, 112)
    ancho, alto = 100, 28
    _caja(d, 10, 66, ancho, alto, "Pendiente", AZUL_CLARO)
    _caja(d, 190, 66, ancho, alto, "Confirmada", AZUL_CLARO)
    _caja(d, 370, 66, ancho, alto, "Cumplida", colors.HexColor("#dcfce7"), colors.HexColor("#15803d"))
    _caja(d, 190, 6, ancho, alto, "Cancelada", colors.HexColor("#fee2e2"), colors.HexColor("#b91c1c"))
    _flecha(d, 112, 80, 188)
    d.add(String(150, 86, "confirmar()", fontName="Codigo-N", fontSize=8.5, textAnchor="middle"))
    d.add(String(150, 56, "valida socio y sede", fontName="Cuerpo", fontSize=8, textAnchor="middle", fillColor=GRIS))
    _flecha(d, 292, 80, 368)
    d.add(String(330, 86, "cumplir()", fontName="Codigo-N", fontSize=8.5, textAnchor="middle"))
    # cancelar desde Pendiente y Confirmada
    d.add(Line(60, 64, 60, 20, strokeWidth=1.2))
    _flecha(d, 60, 20, 188)
    d.add(String(110, 26, "cancelar()", fontName="Codigo-N", fontSize=8.5, textAnchor="middle"))
    d.add(Line(240, 64, 240, 42, strokeWidth=1.2))
    d.add(Polygon([240, 35, 236.5, 42, 243.5, 42], fillColor=colors.black))
    d.add(String(275, 48, "cancelar()", fontName="Codigo-N", fontSize=8.5, textAnchor="middle"))
    d.add(String(420, 40, "Cumplida y Cancelada son finales:", fontName="Cuerpo-I", fontSize=8.5,
                 textAnchor="middle", fillColor=GRIS))
    d.add(String(420, 29, "rechazan toda operación", fontName="Cuerpo-I", fontSize=8.5,
                 textAnchor="middle", fillColor=GRIS))
    return [d, Spacer(1, 6)]


# ---- Contenido ---------------------------------------------------------------------
def portada():
    return [
        Spacer(1, 5 * cm),
        Paragraph("Patrones de diseño aplicados", E["titulo"]), Spacer(1, 10),
        Paragraph("Sistema de Préstamos Interbibliotecarios", E["subtitulo"]), Spacer(1, 1.6 * cm),
        Paragraph("TP Integrador 2026 · Tema 1: Biblioteca · Grupo 93", E["portada"]),
        Paragraph("Desarrollo de Aplicaciones con Objetos · UTN – Facultad Regional Córdoba", E["portada"]),
        Spacer(1, 1.6 * cm),
        Paragraph(f"Noviembre de {date.today().year}", E["portada"]),
        PageBreak(),
    ]


def introduccion():
    s = h1("1. Introducción")
    s += [p("La consigna exige aplicar <b>al menos dos patrones de diseño</b>. El sistema aplica <b>State</b> "
            "(en dos lugares: el ciclo de vida del remito y el de la reserva) e <b>Iterator</b> (el recorrido "
            "del catálogo). Son los patrones que el grupo definió en el diagrama de clases, y cada uno "
            "resuelve un problema concreto del dominio de la biblioteca. Este documento explica, para cada "
            "uno, qué problema resuelve en el TP, cómo se implementó y por qué se eligió."),
          p("Cada patrón se presenta con el esquema de la cátedra: <b>problema</b>, <b>solución</b> "
            "(qué clase cumple cada rol del patrón), <b>implementación</b> (extractos reales del código con "
            "archivo y número de línea), <b>justificación</b>, <b>consecuencias</b> y <b>verificación</b> "
            "(los tests automáticos que lo comprueban).")]
    s += h2("Resumen")
    s += tabla([
        ["Patrón", "Tipo", "Clases", "Problema que resuelve"],
        ["State", "Comportamiento", "Remito, EstadoRemito, Pendiente, Empaquetado, Enviado, Entregado",
         "Qué operación logística admite un remito según la etapa del envío (ida y retorno)."],
        ["State", "Comportamiento", "Reserva, EstadoReserva y sus cuatro estados",
         "Ciclo de una reserva: confirmar, cumplir o cancelar según corresponda."],
        ["Iterator", "Comportamiento", "Catalogo, Iterador, IteradorEjemplares, IteradorEjemplaresDisponibles",
         "Recorrer el catálogo completo o solo lo disponible de una sede, sin exponer la colección."],
    ], [1.8, 2.9, 5.4, 6.9])
    s += h2("Dónde están los patrones")
    s += [p(f"El sistema está organizado en capas: el <b>dominio</b> ({c('biblioteca/modelos/')}), los "
            f"<b>casos de uso</b> ({c('biblioteca/servicios.py')}), la <b>persistencia</b> en SQLite "
            f"({c('biblioteca/persistencia/')}), los <b>reportes</b> ({c('biblioteca/reportes.py')}) y la "
            f"<b>interfaz web</b> con Flask ({c('web/')}). Los dos patrones viven en el dominio y no dependen "
            "de Flask ni de SQLite: por eso se prueban con tests unitarios sin base de datos. Los casos de "
            "uso los combinan, y la interfaz web nunca crea clases concretas del dominio por su cuenta.")]
    return s


def state_remito():
    s = h1("2. State — Ciclo de vida del Remito")
    s += [p("<b>Es el patrón central del TP</b>: la consigna indica que «el ciclo de vida del remito y sus "
            "estados será evaluado críticamente».")]
    s += h2("Problema")
    s += [p("Un remito de un préstamo interbibliotecario pasa por <b>Pendiente → Empaquetado → Enviado → "
            "Entregado</b>. En cada etapa hay una sola operación válida, y cada transición tiene efectos "
            "propios: registrar su fecha, sacar los ejemplares de la sede (en tránsito no tienen ubicación), "
            "validar que ambas sedes sigan activas antes de despachar, ubicarlos en la sede destino al "
            "recibirlos y dejar la trazabilidad en el historial."),
          p(f"Sin el patrón, {c('Remito')} tendría un atributo de texto {c('estado')} y cada uno de sus tres "
            "métodos un <i>if/elif</i> sobre los cuatro estados: doce combinaciones repartidas en tres "
            "métodos. Agregar o cambiar un estado obligaría a revisarlos todos, y es fácil olvidar un caso "
            "y permitir, por ejemplo, recibir algo que nunca se despachó.")]
    s += h2("Solución")
    s += tabla([
        ["Rol del patrón", "Clase", "Responsabilidad"],
        ["Contexto", "Remito (remito.py)", "Guarda el estado actual en _estado y delega empaquetar(), "
         "despachar() y recibir(). Expone cambiar_estado(), que registra el historial."],
        ["Estado (interfaz)", "EstadoRemito (estados_remito.py)", "Clase abstracta que declara las tres "
         "operaciones; _rechazar() centraliza el error."],
        ["Estados concretos", "Pendiente, Empaquetado, Enviado, Entregado", "Cada uno implementa la única "
         "operación que admite y rechaza las demás. Entregado rechaza todo: es el estado final."],
        ["Trazabilidad", "HistorialRemito (remito.py)", "Una entrada por estado: fecha y hora, nombre del "
         "estado, sede (None en tránsito) y observación."],
    ], [3.2, 4.6, 9.2])
    s += diagrama_estados(
        ["Pendiente", "Empaquetado", "Enviado", "Entregado"],
        ["empaquetar()", "despachar()", "recibir()"],
        [["fecha_empaquetado", "sede: origen"],
         ["valida sedes activas", "fecha_despacho", "ubicación = None (en tránsito)"],
         ["fecha_recepcion", "ubicación = sede destino", "retorno: ejemplar disponible"]])
    s += [Paragraph("Figura 1. Transiciones del remito y sus efectos. Al crearse, el remito registra en el "
                    "historial el estado inicial Pendiente.", E["nota"])]
    s += h2("Implementación")
    s += [pc("El contexto no decide nada: solo delega en el objeto estado. Todas las transiciones pasan por "
            f"{c('cambiar_estado()')}, que agrega la entrada de historial.")]
    s += codigo("biblioteca/modelos/remito.py", 55, 69, "self._estado.empaquetar(self, observacion)")
    s += [pc("La interfaz del estado y el estado inicial. Pendiente solo acepta empaquetar(); las otras dos "
            "operaciones se rechazan con un mensaje para el usuario:")]
    s += codigo("biblioteca/modelos/estados_remito.py", 14, 45, "class EstadoRemito(ABC):")
    s += [pc("Despachar y recibir concentran las reglas de negocio de cada etapa: al despachar se verifica "
            "que ninguna sede esté dada de baja y los ejemplares quedan en tránsito; al recibir se ubican "
            "en la sede destino y, si es el remito de retorno, vuelven a estar disponibles para prestar:")]
    s += codigo("biblioteca/modelos/estados_remito.py", 53, 81, "def despachar(self, remito, observacion=\"\"):")
    s += h2("Remito de retorno")
    s += [pc("Cuando el socio devuelve todos los ejemplares en la sede destino, estos vuelven a su sede de "
            f"pertenencia con un segundo remito ({c('tipo = Retorno')}). <b>No hizo falta ningún estado "
            "nuevo</b>: el retorno recorre los mismos cuatro estados. Solo se agregó el tipo, y las "
            f"propiedades {c('sede_origen')} y {c('sede_destino')} invierten el trayecto. Es una muestra "
            "concreta de lo que aporta el patrón: el ciclo se reutiliza sin tocar las reglas de transición."),
          p("El préstamo también consulta el estado del remito: la devolución solo se admite cuando el "
            "remito de ida ya está Entregado, y el retorno solo se genera cuando no quedan ejemplares "
            "pendientes:")]
    s += codigo("biblioteca/modelos/prestamo.py", 149, 162, "def generar_remito_retorno(self, numero_remito):")
    s += h2("Justificación")
    s += vinetas([
        "<b>Cada regla está en un solo lugar.</b> Para saber qué pasa si se intenta despachar un remito "
        f"pendiente basta con leer {c('Pendiente.despachar')}.",
        "<b>No se pueden saltear etapas.</b> El remito no tiene un setter público del estado; la única "
        f"forma de cambiarlo es que el estado actual llame a {c('cambiar_estado()')}.",
        "<b>La trazabilidad no se puede olvidar (RN04).</b> Como toda transición pasa por "
        f"{c('cambiar_estado()')}, cada cambio deja su HistorialRemito con fecha, sede y observación.",
        "<b>Un intento inválido no deja rastro.</b> Los rechazos se lanzan antes de modificar nada: el "
        "historial y las fechas quedan intactos (lo verifica un test).",
        "<b>Alternativas descartadas.</b> Un <i>if/elif</i> sobre un texto (problema descripto arriba) o "
        "una tabla de transiciones permitidas: la tabla dice qué transición es válida, pero no resuelve "
        "que cada una tenga efectos distintos (fechas, ubicación, validación de sedes).",
    ])
    s += h2("Consecuencias")
    s += vinetas([
        "<b>Ventajas:</b> se puede agregar un estado (por ejemplo «Extraviado», del opcional de revisión "
        "de recepción) creando una clase, sin modificar las existentes; el ciclo de vida coincide uno a "
        "uno con el diagrama de clases.",
        "<b>Desventajas:</b> hay más clases, y cada estado repite los métodos que rechaza (se mitigó con "
        f"{c('_rechazar()')} en la clase base). Cada estado conoce a su sucesor; es aceptable porque el "
        "flujo es lineal y fijo.",
        "<b>Persistencia:</b> en la base se guarda el nombre del estado y el Repositorio reconstruye el "
        "objeto estado correspondiente (ver sección 6).",
    ])
    s += h2("Verificación")
    s += [p(f"{c('test_ciclo_completo_con_trazabilidad_y_ubicacion')}, {c('test_transiciones_no_permitidas')}, "
            f"{c('test_no_se_despacha_hacia_sede_dada_de_baja')}, la clase {c('TestRemitoRetorno')} "
            f"({c('tests/test_modelos.py')}) y {c('test_transicion_invalida_desde_la_base')} "
            f"({c('tests/test_persistencia.py')}).")]
    return s


def state_reserva():
    s = h1("3. State — Ciclo de vida de la Reserva")
    s += h2("Problema")
    s += [p("Una reserva nace <b>Pendiente</b>, se <b>confirma</b> y termina <b>cumplida</b> (el socio retiró "
            "el libro) o <b>cancelada</b>, ya sea desde Pendiente o desde Confirmada. Confirmar exige que el "
            "socio esté habilitado y la sede activa (RN14). A diferencia del remito, el ciclo <b>se bifurca</b> "
            "y tiene dos estados finales.")]
    s += diagrama_reserva()
    s += [Paragraph("Figura 2. Estados de la reserva.", E["nota"])]
    s += h2("Solución")
    s += tabla([
        ["Rol del patrón", "Clase", "Responsabilidad"],
        ["Contexto", "Reserva (reserva.py)", "Delega confirmar_reserva(), cancelar() y cumplir() en su estado."],
        ["Estado (interfaz)", "EstadoReserva (estados_reserva.py)", "Declara las tres operaciones."],
        ["Estados concretos", "ReservaPendiente, ReservaConfirmada, ReservaCumplida, ReservaCancelada",
         "Implementan las transiciones válidas; los dos estados finales rechazan todo."],
    ], [3.2, 6.3, 7.5])
    s += h2("Implementación")
    s += codigo("biblioteca/modelos/estados_reserva.py", 32, 56, "class ReservaPendiente(EstadoReserva):")
    s += codigo("biblioteca/modelos/reserva.py", 32, 39, "def confirmar_reserva(self):")
    s += h2("Justificación")
    s += vinetas([
        "<b>La validación está solo donde corresponde.</b> Únicamente "
        f"{c('ReservaPendiente.confirmar')} llama a {c('validar_reserva')}: cancelar una reserva de un "
        "socio que luego fue inhabilitado sigue siendo posible, lo cual es correcto.",
        "<b>Un mismo mecanismo para todo el equipo.</b> Remito y Reserva resuelven su ciclo de vida igual, "
        "y la interfaz web solo necesita saber qué botones mostrar según el nombre del estado.",
        "<b>El patrón también sirve para ciclos no lineales:</b> la cancelación desde dos estados y los dos "
        "estados finales no requieren ninguna condición extra.",
    ])
    s += h2("Consecuencias y verificación")
    s += [p("Las mismas que en la sección 2: más clases a cambio de reglas localizadas y fáciles de extender. "
            f"Tests: {c('test_ciclo_confirmar_y_cumplir')}, {c('test_no_se_cumple_sin_confirmar')}, "
            f"{c('test_cancelar')}, {c('test_confirmar_reserva')}, {c('test_reserva_rechazada')} y "
            f"{c('test_reserva')} (con la base de datos).")]
    return s


def iterator():
    s = h1("4. Iterator — Recorrido del Catálogo")
    s += h2("Problema")
    s += [p("El catálogo reúne los ejemplares de todas las sedes de la red. Hay que recorrerlo completo, y "
            "también solo los ejemplares <b>disponibles que pertenecen a una sede</b>: es la consulta de "
            "disponibilidad (proceso obligatorio 6) y la lista de la que se eligen los ejemplares al "
            "registrar un préstamo."),
          p(f"Si {c('Catalogo')} expusiera su lista interna, cada cliente repetiría el filtro «disponible y "
            "de esta sede», y además podría agregar ejemplares directamente a la lista, salteando el control "
            f"de códigos duplicados de {c('agregar_ejemplar()')} (RN07).")]
    s += h2("Solución")
    s += tabla([
        ["Rol del patrón", "Clase", "Responsabilidad"],
        ["Iterador (interfaz)", "Iterador", "Declara has_next() y next(), como en el diagrama de clases."],
        ["Iterador concreto", "IteradorEjemplares", "Recorre todos los ejemplares y guarda su propia posición."],
        ["Iterador concreto", "IteradorEjemplaresDisponibles", "Hereda del anterior y solo redefine has_next() "
         "para saltear los que no están disponibles o son de otra sede."],
        ["Agregado", "Catalogo", "Guarda la lista privada _ejemplares y crea los iteradores."],
        ["Cliente", "servicios.consultar_disponibilidad", "Usa el iterador sin conocer la lista."],
    ], [3.2, 5.2, 8.6])
    s += h2("Implementación")
    s += codigo("biblioteca/modelos/catalogo.py", 8, 55, "class Iterador(ABC):")
    s += codigo("biblioteca/modelos/catalogo.py", 57, 73, "class Catalogo:")
    s += [pc("El cliente, la consulta de disponibilidad que usan la web y el formulario de préstamos:")]
    s += codigo("biblioteca/servicios.py", 85, 89, "crear_iterador_disponibles")
    s += h2("Justificación")
    s += vinetas([
        f"<b>Encapsulamiento:</b> la colección es privada y la única forma de agregar es {c('agregar_ejemplar()')}, "
        "que impide códigos repetidos.",
        "<b>El filtro está en un solo lugar.</b> «Disponible y perteneciente a la sede» se define una vez, "
        f"en {c('IteradorEjemplaresDisponibles.has_next()')}.",
        "<b>Recorridos independientes:</b> cada iterador tiene su propia posición, así que se pueden hacer "
        "varios recorridos simultáneos sin interferir.",
        f"<b>Interfaz de la cátedra y de Python a la vez:</b> se respeta {c('has_next()')} / {c('next()')} "
        f"con {c('StopIteration')} al agotarse, y la interfaz además implementa {c('__iter__')} y "
        f"{c('__next__')}, de modo que el iterador funciona en un {c('for')} o con {c('list()')}.",
    ])
    s += h2("Consecuencias")
    s += vinetas([
        "<b>Ventajas:</b> se pueden agregar recorridos nuevos (por ejemplo, por libro o por estado físico) "
        "con otra subclase, sin tocar Catalogo ni sus clientes.",
        "<b>Desventajas:</b> en Python las listas ya son iterables, así que el patrón agrega clases; se "
        "justifica por el filtrado y por ocultar la colección. El filtro se hace en memoria: con un catálogo "
        "muy grande convendría filtrar directamente en SQL.",
    ])
    s += h2("Verificación")
    s += [p(f"{c('test_recorre_todos_los_ejemplares_y_lanza_stop_iteration')}, {c('test_se_puede_usar_en_for')}, "
            f"{c('test_rechaza_ejemplar_duplicado')}, {c('test_solo_disponibles_de_la_sede')} y "
            f"{c('test_prestamo_local_y_disponibilidad')}.")]
    return s


def colaboracion():
    s = h1("5. Cómo colaboran los patrones en un caso de uso")
    s += [p("Los patrones no están aislados. Este es el recorrido de un préstamo interbibliotecario completo, "
            "tal como se ejecuta desde la interfaz web:")]
    s += tabla([
        ["Paso", "Qué ocurre", "Patrones"],
        ["1. Consultar disponibilidad", "El formulario lista los ejemplares disponibles de la sede de origen.",
         "Iterator"],
        ["2. Registrar préstamo", "Como las sedes son distintas, se crea un PrestamoInterbibliotecario con "
         "vencimiento a 21 días; el constructor valida las reglas; se genera el remito en estado Pendiente "
         "con su primera entrada de historial.", "State"],
        ["3. Empaquetar, despachar, recibir", "El estado actual decide si la operación es válida y ejecuta sus "
         "efectos; cada transición queda registrada en el historial del remito.", "State"],
        ["4. Devolución", "Solo se admite si el remito de ida está Entregado; el ejemplar sigue no disponible. "
         "Al devolver todo se genera el remito de retorno.", "State"],
        ["5. Retorno", "El remito de retorno recorre los mismos estados; al recibirse, los ejemplares quedan "
         "disponibles en su sede y vuelven a aparecer en el paso 1.", "State, Iterator"],
    ], [3.6, 10.2, 3.2])
    return s


def complementos():
    s = h1("6. Técnicas complementarias")
    s += [p("No son patrones exigidos por la cátedra, pero sostienen a los anteriores al guardar los datos en "
            "SQLite:")]
    s += vinetas([
        f"<b>Repositorio</b> ({c('biblioteca/persistencia/repositorio.py')}): concentra todo el SQL. Ni el "
        "dominio ni la web escriben consultas para leer o guardar objetos.",
        "<b>Mapa de identidad:</b> dentro de una petición, cada fila se convierte en un único objeto. Es "
        f"necesario porque el dominio compara sedes por identidad ({c('is')}), por ejemplo en "
        f"{c('Ejemplar.pertenece_a_sede()')}.",
        "<b>Reconstrucción del estado (State persistido):</b> en la base se guarda el nombre del estado; al "
        "leer, un diccionario lo traduce a la clase de estado correspondiente:",
    ])
    s += codigo("biblioteca/persistencia/repositorio.py", 18, 20, "ESTADOS_REMITO")
    s += codigo("biblioteca/persistencia/repositorio.py", 260, 264, "ESTADOS_REMITO[f[\"estado\"]]()")
    s += [p("Además, las restricciones de la base (claves primarias, UNIQUE y un índice único parcial que "
            "impide que un ejemplar tenga dos préstamos pendientes) funcionan como última barrera para las "
            "reglas de no duplicación, por si alguna validación se saltea por error.")]
    return s


def pie(canvas, doc):
    if doc.page == 1:
        return
    canvas.saveState()
    canvas.setFont("Cuerpo", 8.5)
    canvas.setFillColor(GRIS)
    canvas.drawString(2 * cm, 1.2 * cm, "Grupo 93 · Patrones de diseño aplicados")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Página {doc.page}")
    canvas.setStrokeColor(BORDE)
    canvas.line(2 * cm, 1.55 * cm, A4[0] - 2 * cm, 1.55 * cm)
    canvas.restoreState()


def main():
    doc = SimpleDocTemplate(str(SALIDA), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=2 * cm, title="Patrones de diseño aplicados",
                            author="Grupo 93", subject="TP Integrador DAO 2026 - Tema 1")
    historia = (portada() + introduccion() + state_remito() + state_reserva() + iterator() + colaboracion()
                + complementos())
    doc.build(historia, onFirstPage=pie, onLaterPages=pie)
    print(SALIDA)


if __name__ == "__main__":
    main()
