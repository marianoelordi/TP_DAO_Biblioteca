# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

UTN FRC – Desarrollo de Aplicaciones con Objetos, TP Integrador 2026, **Grupo 93, Tema 1: "Biblioteca: Sistema de Préstamos Interbibliotecarios"**. Layers: domain (`biblioteca/modelos/`), use cases (`biblioteca/servicios.py`), SQLite persistence (`biblioteca/persistencia/`), reports (`biblioteca/reportes.py`), Flask web UI (`web/`).

## Commands

Python 3.13. Only dependency: Flask (`pip install -r requirements.txt`); the domain and persistence layers are stdlib only. Run from the repo root:

- Web app: `python app.py` → http://127.0.0.1:5000 (DB file `biblioteca.db`; `python datos_demo.py` recreates it with sample data)
- All tests: `python -m unittest -v`
- One test: `python -m unittest tests.test_modelos.TestRemitoState.test_transiciones_no_permitidas`

## Code layout

- `biblioteca/excepciones.py` — `ReglaNegocioError`, the single exception raised for every business-rule violation (the diagram's `Boolean` validators raise this instead, so the message reaches the user).
- `biblioteca/modelos/` — one module per diagram class. Method names are the diagram's names in snake_case (`esta_habilitado`, `has_next`, …).
- `REQUISITOS.md` — full requirements list with IDs and implementation status, plus the pattern → class map. Keep its status column up to date when implementing something.
- All six course patterns are applied: State (`estados_remito.py`, `estados_reserva.py`), Iterator (`catalogo.py`), Strategy (`multas.py`), Singleton (`biblioteca/configuracion.py`), Factory (`modelos/fabrica_prestamos.py`), Observer (`biblioteca/observador.py` + `notificaciones.py`; `Remito` is the Sujeto).
- `Prestamo` is abstract; concrete types are `PrestamoLocal` / `PrestamoInterbibliotecario`, normally created via `FabricaPrestamos`. `Prestamo.__init__` runs `validar_condiciones` and marks ejemplares as prestados, so an invalid loan can never exist. Remitos are created only via `PrestamoInterbibliotecario.generar_remito()`.
- `Prestamo.calcular_multa(estrategia, fecha)` takes the strategy as a parameter (Strategy is chosen externally, usually `Configuracion().estrategia_multa`), which also keeps `modelos` free of a dependency on `configuracion`.
- Import cycle to avoid: `configuracion` imports `modelos.multas`, so `modelos/__init__.py` must not import `fabrica_prestamos` (which imports `configuracion`).
- `Configuracion` is a Singleton: tests that touch it call `Configuracion.reiniciar()` in `setUp`/`tearDown`.
- Uniqueness of sedes, socios, libros, ejemplares and remito numbers is enforced by `Repositorio.agregar_*` (friendly `ReglaNegocioError`) with PRIMARY KEY/UNIQUE as backstop.
- `Repositorio` keeps an identity map (the domain compares sedes with `is`) and rebuilds persisted objects with `__new__`, bypassing constructor validations. Create one per request/transaction.
- `servicios.py` never commits; the caller (web `ejecutar` helper, tests) commits or rolls back.
- Inter-library return trip: `Prestamo.registrar_devolucion` keeps the ejemplar unavailable; once all details are returned, `servicios.registrar_devolucion` calls `generar_remito_retorno` (`Remito.tipo == "Retorno"`, sedes reversed); receiving it marks the ejemplares disponible.

Reference documents in the repo (read these before designing anything new):
- `Tema 1 - Biblioteca.pdf` — the assignment statement (mandatory processes, validations, suggested reports).
- `Presentacion-grupo.pdf` / `.docx` — the group's design document: scope, business rules, and the UML class diagram.
- `Diagrama de clases.png` — the class diagram at full resolution; it is the source of truth for class names, attributes, and methods.
- `Patrones (PRESENTACIONES DE CLASES)/` — course slides on design patterns (Strategy, State, Iterator in Python), the style the course expects.

Target language is **Python** (the design doc specifies Python semantics, e.g. `StopIteration`). Domain names are in Spanish; keep them in Spanish to match the diagram (`Socio`, `Sede`, `Ejemplar`, `Remito`, etc.).

## Grading constraints (from the assignment)

- All 8 mandatory business processes and all listed validations must be implemented.
- **At least two design patterns** must be applied (the group chose State and Iterator — see below).
- **At least four non-trivial reports** (candidates: active loans & material in transit; overdue loans & accumulated fines; most-requested books for inter-branch loans; catalog availability per sede; logistics success/incident rate; movements between sedes with average transit time).
- The `Remito` lifecycle and its states are "evaluated critically" — model it carefully.

## Domain model (from the class diagram)

- `Sede` — branch of the network; has `activa` flag with `alta()`/`baja()`/`estaActiva()`.
- `Socio` — member; `inhabilitado` flag with `habilitar()`/`inhabilitar()`/`estaHabilitado()`.
- `Libro` (identified by `isbn`) has many `Ejemplar` (identified by `codigo`). Each `Ejemplar` has **two distinct Sede links**: *pertenencia* (owning sede, required) and *ubicación actual* (0..1 — `None` while in transit).
- `Catalogo` aggregates `Ejemplar`s.
- `Prestamo` (sedeOrigen, sedeDestino, fechaVencimiento) is composed of 1..* `DetallePrestamo`, one per `Ejemplar`; each detail records `fechaDevolucionReal` and `estadoFisicoDevuelto`. An inter-library loan generates 0..1 `Remito`.
- `Reserva` links a `Socio`, a `Libro`, and the `Sede` where it is requested.
- `Remito` is composed of 1..* `HistorialRemito` entries (fechaHora, nombreEstado, sedeUbicacion, observacion).

### Pattern: State (Remito)
`Remito` holds a private `_estado: EstadoRemito` and delegates `empaquetar()`, `despachar()`, `recibir()` to it. Concrete states: `Pendiente`, `Empaquetado`, `Enviado`, `Entregado`. Allowed transitions only:
- Pendiente → Empaquetado via `empaquetar()`
- Empaquetado → Enviado via `despachar()`
- Enviado → Entregado via `recibir()`

Any other operation in the current state must be rejected (raise). Each transition goes through `cambiar_estado(nuevo_estado, sedeActual)`, sets the matching date (`fechaEmpaquetado`/`fechaDespacho`/`fechaRecepcion`) and appends a `HistorialRemito` via `registrarTrazabilidad`. Creating a Remito must record the initial `Pendiente` entry in the history.

### Pattern: Iterator (Catalogo)
`Catalogo.crearIterador()` returns an `IteradorEjemplares` typed as the `Iterador` interface (`hasNext()`, `next()`). The iterator keeps its own `posicion`; `next()` raises `StopIteration` when exhausted.

## Business rules to enforce

- No duplicates: socios, libros (ISBN), ejemplares (código), remito numbers.
- Loans: socio must be habilitado; ejemplares must be disponible **and** belong to the sede de origen; check fecha de vencimiento.
- Inter-library loans require a Remito before dispatch; local loans never create a Remito.
- An Ejemplar cannot have two DetallePrestamo pending return. A Prestamo stays active while any detail is pending return.
- Reservas: socio habilitado and requested sede activa before confirming.
- No loans, reservations, or shipments to/from a sede dada de baja (both origin and destination must be active).


1. Think Before Coding
Don't assume. Don't hide confusion. Surface tradeoffs.

LLMs often pick an interpretation silently and run with it. This principle forces explicit reasoning:

State assumptions explicitly — If uncertain, ask rather than guess
Present multiple interpretations — Don't pick silently when ambiguity exists
Push back when warranted — If a simpler approach exists, say so
Stop when confused — Name what's unclear and ask for clarification
2. Simplicity First
Minimum code that solves the problem. Nothing speculative.

Combat the tendency toward overengineering:

No features beyond what was asked
No abstractions for single-use code
No "flexibility" or "configurability" that wasn't requested
No error handling for impossible scenarios
If 200 lines could be 50, rewrite it
The test: Would a senior engineer say this is overcomplicated? If yes, simplify.

3. Surgical Changes
Touch only what you must. Clean up only your own mess.

When editing existing code:

Don't "improve" adjacent code, comments, or formatting
Don't refactor things that aren't broken
Match existing style, even if you'd do it differently
If you notice unrelated dead code, mention it — don't delete it
When your changes create orphans:

Remove imports/variables/functions that YOUR changes made unused
Don't remove pre-existing dead code unless asked
The test: Every changed line should trace directly to the user's request.

4. Goal-Driven Execution
Define success criteria. Loop until verified.

Transform imperative tasks into verifiable goals:

Instead of...	Transform to...
"Add validation"	"Write tests for invalid inputs, then make them pass"
"Fix the bug"	"Write a test that reproduces it, then make it pass"
"Refactor X"	"Ensure tests pass before and after"
For multi-step tasks, state a brief plan:

1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
Strong success criteria let the LLM loop independently. Weak criteria ("make it work") require constant clarification.