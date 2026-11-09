# Biblioteca: Sistema de Préstamos Interbibliotecarios

Trabajo Práctico Integrador 2026 de **Desarrollo de Aplicaciones con Objetos** (UTN FRC), realizado por el **Grupo 93** sobre el **Tema 1**.

## Introducción

El sistema administra una red de bibliotecas formada por varias sedes. Cada sede tiene sus propios ejemplares, y un socio puede pedir prestado un libro que está en **otra sede**. En ese caso el ejemplar se envía con un **remito**, que registra el trayecto completo: *Pendiente → Empaquetado → Enviado → Entregado*. Cuando el socio devuelve el material, se genera un **remito de retorno** hacia la sede dueña del ejemplar.

El proyecto está hecho en Python con orientación a objetos y tiene cuatro capas:

| Capa | Tecnología | Responsabilidad |
|------|------------|-----------------|
| Dominio | Python (sin dependencias) | Clases del diagrama, reglas de negocio y patrones de diseño |
| Casos de uso | Python | Coordinan el dominio con la persistencia |
| Persistencia | SQLite (`sqlite3`) | Esquema relacional y repositorio |
| Interfaz | Flask (web) | Pantallas de ABM, préstamos, remitos, reservas y reportes |

Se aplican **seis patrones de diseño**: State, Iterator, Strategy, Singleton, Factory y Observer. El documento [`Patrones de diseño aplicados.pdf`](Patrones%20de%20diseño%20aplicados.pdf) explica cada uno con el código correspondiente y su justificación.

## Contenido y organización

```
├── app.py                      Punto de entrada de la aplicación web
├── datos_demo.py               Crea biblioteca.db con datos de ejemplo
├── requirements.txt            Dependencias (Flask)
├── biblioteca/
│   ├── excepciones.py          ReglaNegocioError: toda violación de una regla de negocio
│   ├── configuracion.py        Configuracion (Singleton): plazos y estrategia de multa
│   ├── observador.py           Sujeto / Observador (Observer)
│   ├── notificaciones.py       NotificadorSocio: avisa al socio los cambios del remito
│   ├── servicios.py            Casos de uso (alta de sedes, préstamos, devoluciones, etc.)
│   ├── reportes.py             Reportes
│   ├── modelos/                Dominio: una clase del diagrama por módulo
│   │   ├── sede.py, socio.py, libro.py, ejemplar.py
│   │   ├── catalogo.py         Catalogo + iteradores (Iterator)
│   │   ├── prestamo.py         Prestamo (abstracta), PrestamoLocal, PrestamoInterbibliotecario
│   │   ├── fabrica_prestamos.py FabricaPrestamos (Factory)
│   │   ├── remito.py           Remito + HistorialRemito
│   │   ├── estados_remito.py   Pendiente, Empaquetado, Enviado, Entregado (State)
│   │   ├── reserva.py, estados_reserva.py   Reserva y sus estados (State)
│   │   └── multas.py           Estrategias de multa (Strategy)
│   └── persistencia/
│       ├── esquema.sql         Tablas, claves e índices
│       ├── base_datos.py       Conexión a SQLite
│       └── repositorio.py      Repositorio: carga y guarda los objetos del dominio
├── web/
│   ├── __init__.py             Aplicación Flask y rutas
│   ├── templates/              Vistas HTML (Jinja2)
│   └── static/estilos.css
├── tests/                      Pruebas unitarias (dominio, patrones, persistencia, web)
├── REQUISITOS.md               Requisitos con su identificador y estado
├── Tema 1 - Biblioteca.pdf     Consigna del trabajo práctico
├── Presentacion-grupo.pdf      Documento de diseño del grupo
├── Diagrama de clases.png      Diagrama de clases UML
└── Patrones de diseño aplicados.pdf  Explicación de los patrones con el código
```

## Instalación y uso

**Requisitos:** Python 3.13 (versión con la que se desarrolló y probó) y `pip`.

1. Clonar el repositorio y entrar a la carpeta:
   ```bash
   git clone <url-del-repositorio>
   cd <carpeta-del-repositorio>
   ```
2. *(Opcional)* Crear y activar un entorno virtual:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   source .venv/bin/activate     # Linux / macOS
   ```
3. Instalar las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Cargar los datos de ejemplo. Este paso es opcional, pero sirve para probar el sistema. Crea `biblioteca.db` desde cero:
   ```bash
   python datos_demo.py
   ```
5. Iniciar la aplicación y abrir http://127.0.0.1:5000 en el navegador:
   ```bash
   python app.py
   ```

Para ejecutar las pruebas:

```bash
python -m unittest -v
```

**Datos de ejemplo:**
- Sedes: `CEN`, `NOR` y `SUR`.
- Socios: del `1001` al `1005`. El `1005` está inhabilitado, para probar que se rechazan sus préstamos.
- Siete libros con ejemplares repartidos entre las sedes. Los códigos tienen la forma `CEN-002-2`.
- Algunos préstamos y remitos ya avanzados, para que los reportes muestren datos.

## Consignas cumplidas

### Procesos de negocio obligatorios

| # | Proceso | Cómo se resuelve |
|---|---------|------------------|
| 1 | Administrar sedes (dirección, contacto, horarios, estado) | Pantalla `/sedes`: alta, modificación, alta y baja lógica |
| 2 | Administrar socios | Pantalla `/socios`: alta, modificación, habilitar e inhabilitar |
| 3 | Administrar el catálogo de libros y ejemplares, con su sede | Pantalla `/libros`: los ejemplares se gestionan dentro de cada libro |
| 4 | Registrar préstamos locales e interbibliotecarios | `FabricaPrestamos` elige el tipo de préstamo. El interbibliotecario genera su remito al registrarse |
| 5 | Empaquetar, despachar y recibir con remito y trazabilidad | `Remito` con estados (State) y `HistorialRemito`. Incluye el remito de retorno |
| 6 | Consultar disponibilidad | Pantalla `/disponibilidad`, que recorre el catálogo con un iterador (Iterator) |
| 7 | Gestionar reservas | Pantalla `/reservas`: registrar, confirmar, cancelar y cumplir (State) |
| 8 | Registrar devoluciones con fecha real y estado físico | Se registran desde el detalle del préstamo. Al devolver todo, se genera el remito de retorno |

### Validaciones

- No se prestan ejemplares que no están disponibles.
- No se presta a socios inhabilitados.
- Se controlan las fechas de vencimiento. Las multas se calculan con la estrategia configurada.
- La trazabilidad del remito se mantiene en todo el trayecto. Cada paso guarda el estado, la fecha y hora, la sede y una observación.
- No se admiten duplicados de socios, libros (ISBN), ejemplares (código) ni números de remito. Lo controla el repositorio y, como respaldo, las claves de SQLite.
- No se prestan ejemplares que pertenecen a otra sede distinta de la de origen.
- No se hacen préstamos, reservas ni envíos hacia o desde una sede dada de baja.
- Solo se permiten las transiciones de remito Pendiente → Empaquetado → Enviado → Entregado. Cualquier otra se rechaza.
- Un ejemplar no puede tener dos préstamos pendientes de devolución a la vez.
- Los préstamos locales no generan remito.

### Patrones de diseño (se pedían al menos dos)

| Patrón | Dónde se aplica | Para qué |
|--------|-----------------|----------|
| State | `Remito`, `Reserva` | Permitir solo las operaciones válidas en cada etapa del ciclo de vida |
| Iterator | `Catalogo` | Recorrer los ejemplares, todos o solo los disponibles de una sede, sin exponer la colección |
| Strategy | `EstrategiaMulta` | Cambiar la forma de calcular la multa: sin multa, por día, o por día con tope |
| Singleton | `Configuracion` | Tener una única configuración de plazos y multas para todo el sistema |
| Factory | `FabricaPrestamos` | Crear el tipo de préstamo correcto y calcular su vencimiento |
| Observer | `Remito` → `NotificadorSocio` | Avisar al socio cada vez que cambia el estado de su envío |

### Reportes (se pedían al menos cuatro)

Están en la pantalla `/reportes`:

1. Préstamos activos y material en tránsito.
2. Préstamos vencidos y multas acumuladas, por préstamo y por socio.
3. Libros más solicitados en préstamos entre sedes.
4. Disponibilidad del catálogo por sede.
5. Movimiento de ejemplares entre sedes y tiempo promedio de tránsito.

### Otros requisitos

- **Persistencia:** base de datos SQLite.
- **Interfaz de usuario:** aplicación web hecha con Flask.
- **Notificaciones (opcional):** el sistema genera los avisos al socio y se pueden ver en `/notificaciones`. No envía correos reales.
- **Pruebas:** 53 pruebas unitarias que cubren el dominio, los patrones, la persistencia y la interfaz web.

[`REQUISITOS.md`](REQUISITOS.md) tiene el detalle de cada requisito. Los que quedan pendientes son opcionales o no obligatorios: el reporte de envíos exitosos e incidencias, el historial de lecturas, las recomendaciones, el inventario con códigos y la revisión del estado de recepción.
