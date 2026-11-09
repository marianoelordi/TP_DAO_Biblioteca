# Requisitos — Sistema de Préstamos Interbibliotecarios (Grupo 93)

Fuentes: **[T]** consigna `Tema 1 - Biblioteca.pdf` · **[P]** `Presentacion-grupo.pdf` · **[C]** material de la cátedra.

Estado: ✅ implementado y testeado en el dominio · 🟡 parcial · ⬜ pendiente.
Capas: dominio (`biblioteca/modelos`), casos de uso (`biblioteca/servicios.py`), persistencia SQLite (`biblioteca/persistencia`), reportes (`biblioteca/reportes.py`) e interfaz web Flask (`web/`).

## 1. Requisitos funcionales obligatorios

| ID | Requisito | Fuente | Estado |
|----|-----------|--------|--------|
| RF01 | Administrar sedes: dirección, contacto, horarios, estado activo/baja | T1, P | ✅ ABM web `/sedes` |
| RF02 | Administrar socios (alta, modificación, habilitar/inhabilitar) | T2, P | ✅ ABM web `/socios` |
| RF03 | Administrar catálogo de libros y ejemplares, indicando la sede de cada ejemplar | T3, P | ✅ ABM web `/libros` (ejemplares dentro de cada libro) |
| RF04 | Registrar préstamos locales e interbibliotecarios (sede origen y destino) | T4, P | ✅ `FabricaPrestamos` + `/prestamos/nuevo`; el interbibliotecario genera su remito al registrarse |
| RF05 | Empaquetar, despachar y recibir ejemplares con remito y trazabilidad por estados | T5, P | ✅ `Remito` + estados + `HistorialRemito`; `/remitos`. Incluye remito de retorno destino → origen |
| RF06 | Consultar disponibilidad | T6 | ✅ `/disponibilidad` (usa `IteradorEjemplaresDisponibles`) |
| RF07 | Gestionar reservas (registrar, confirmar, cancelar, cumplir) | T7, P | ✅ `Reserva` + estados; `/reservas` |
| RF08 | Registrar devoluciones con fecha real y estado físico del material | T8, P | ✅ `Prestamo.registrar_devolucion`; en interbibliotecarios, al devolver todo se genera el remito de retorno |

## 2. Reglas de negocio y validaciones

| ID | Regla | Fuente | Estado |
|----|-------|--------|--------|
| RN01 | No prestar ejemplares no disponibles | T, P4 | ✅ |
| RN02 | No prestar a socios inhabilitados | T, P1 | ✅ |
| RN03 | Controlar fechas de vencimiento de préstamos | T, P4 | ✅ `controlar_vencimiento`; vencimiento calculado por plazo configurado |
| RN04 | Mantener la trazabilidad del remito en todo el trayecto (estado, fecha/hora, sede, observación) | T, P8 | ✅ |
| RN05 | Evitar duplicados de socios | T, P1 | ✅ `Repositorio.agregar_socio` + PK |
| RN06 | Evitar duplicados de libros (ISBN) | T, P3 | ✅ `Repositorio.agregar_libro` + PK |
| RN07 | Evitar duplicados de ejemplares (código) | T, P3 | ✅ en `Catalogo` y en `Repositorio` + PK |
| RN08 | No admitir números de remito duplicados | P8 | ✅ numeración automática + `Repositorio` + PK |
| RN09 | No prestar ejemplares que no pertenezcan a la sede de origen | T, P4 | ✅ |
| RN10 | No iniciar préstamos, reservas ni envíos hacia/desde una sede dada de baja | T, P2, P6 | ✅ (al prestar, al crear el remito, al despachar y al confirmar reserva) |
| RN11 | Los préstamos interbibliotecarios requieren remito antes del despacho; los locales no generan remito | P4 | ✅ |
| RN12 | Un ejemplar no puede tener dos detalles de préstamo pendientes de devolución | P5 | ✅ (vía disponibilidad + sin repetidos en un préstamo + índice único parcial en SQLite) |
| RN13 | El préstamo sigue activo mientras tenga ejemplares pendientes de devolución | P5 | ✅ |
| RN14 | Reserva: verificar socio habilitado y sede activa antes de confirmar | P6 | ✅ |
| RN15 | Distinguir sede de pertenencia y ubicación actual; en tránsito, sin ubicación | P7 | ✅ |
| RN16 | Al crear el remito se registra el estado inicial Pendiente | P8 | ✅ |
| RN17 | Transiciones de remito solo Pendiente→Empaquetado→Enviado→Entregado; el resto se rechaza | P9 | ✅ |

## 3. Reportes (mínimo 4 no triviales)

| ID | Reporte | Fuente | Estado |
|----|---------|--------|--------|
| RR01 | Préstamos activos y material en tránsito | T | ✅ `/reportes` |
| RR02 | Préstamos vencidos y multas acumuladas | T | ✅ (por préstamo y por socio, con la estrategia configurada) |
| RR03 | Libros más solicitados para préstamos inter-sedes | T | ✅ |
| RR04 | Disponibilidad de catálogo por sede | T | ✅ |
| RR05 | Tasa de envíos logísticos exitosos e incidencias | T | ⬜ requiere modelar incidencias (RO05) |
| RR06 | Movimiento de ejemplares entre sedes y tiempo promedio de tránsito | T | ✅ (ida y retorno) |

## 4. Requisitos opcionales

| ID | Requisito | Estado |
|----|-----------|--------|
| RO01 | Envío de notificaciones | 🟡 `NotificadorSocio` observa remitos; se guardan en la tabla `notificacion` y se ven en `/notificaciones` (sin mail real) |
| RO02 | Historial de lecturas | ⬜ |
| RO03 | Recomendaciones | ⬜ |
| RO04 | Inventario con códigos | ⬜ |
| RO05 | Revisión del estado de recepción (extravío, daño, destrucción) | ⬜ |

## 5. Requisitos de diseño y no funcionales

| ID | Requisito | Fuente | Estado |
|----|-----------|--------|--------|
| RD01 | Aplicar al menos dos patrones de diseño | T | ✅ (se aplican seis, ver abajo) |
| RD02 | El ciclo de vida del remito se evalúa críticamente | T | ✅ State + historial |
| RD03 | Implementación en Python orientada a objetos | P, C | ✅ |
| RD04 | Persistencia de datos | C ("POO · Persistencia · Interfaces · Patrones") | ✅ SQLite (`esquema.sql` + `Repositorio`) |
| RD05 | Interfaz de usuario | C | ✅ web con Flask |

### Patrones aplicados

| Patrón | Dónde | Problema que resuelve |
|--------|-------|-----------------------|
| State | `Remito` (`estados_remito.py`) | Operaciones permitidas según la etapa del envío |
| State | `Reserva` (`estados_reserva.py`) | Ciclo Pendiente → Confirmada → Cumplida / Cancelada |
| Iterator | `Catalogo` → `IteradorEjemplares`, `IteradorEjemplaresDisponibles` | Recorrer el catálogo (completo o disponibles por sede) sin exponer la lista |
| Strategy | `EstrategiaMulta` (`multas.py`) | Cálculo de multa intercambiable: `SinMulta`, `MultaPorDia`, `MultaConTope` |
| Singleton | `Configuracion` | Plazos de préstamo y estrategia de multa únicos para todo el sistema |
| Factory | `FabricaPrestamos` | Elegir `PrestamoLocal` / `PrestamoInterbibliotecario` y calcular el vencimiento |
| Observer | `Remito` (Sujeto) → `NotificadorSocio` | Avisar al socio en cada cambio de estado del envío |

## 6. Decisiones abiertas

1. ~~Interfaz~~: web con Flask. ~~Persistencia~~: SQLite.
2. ~~Regreso del ejemplar~~: sí, con un remito de retorno (destino → origen) que se genera cuando el socio devolvió **todos** los ejemplares del préstamo; el ejemplar vuelve a estar disponible al recibirse en su sede.
3. **Diagrama de clases**: falta reflejar `Remito.tipo` (Ida/Retorno), `PrestamoInterbibliotecario.remito_retorno` y los patrones agregados después (Strategy, Singleton, Factory, Observer).
4. **Valores de negocio**: plazos (14 y 21 días) y multa ($100 por día y ejemplar) son provisorios.
