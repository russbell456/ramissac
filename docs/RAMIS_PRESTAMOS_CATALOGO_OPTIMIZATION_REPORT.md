# RAMIS — Optimización del catálogo de préstamos

Fecha: 11 de noviembre de 2026. Alcance: catálogo Flutter y búsqueda de disponibles FastAPI. Se preservaron los cambios de trabajo encontrados en ambos repositorios.

## Arquitectura y contratos encontrados

- Backend: `ramissac`, FastAPI → router `/articulo` → `AlmacenArticuloService` → `AlmacenArticuloRepository` → SQLAlchemy. Inventario en `AlmacenArticulo` e imágenes relacionadas en `AlmacenArticuloImagen`.
- Frontend: `sistema_ocs/sistema_ocs`, Flutter Material 3, Riverpod 2 y Dio compartido. Pantalla `ArticulosDisponiblesScreen`, `articulosProvider`, `PrestamoArticuloCard` y `PrestamoCantidadDialog` ya existían.
- Se leyó completo `docs/RAMIS_DESIGN_SYSTEM_REPORT.md` antes de editar. Se conservan Emerald Tech V1.0, Inter local, Light/Dark/System y el tema global.
- `carritoProvider.notifier.agregar(articulo, cantidad)` y navegación `MaterialPageRoute` a `CarritoScreen` permanecen. No se editó el carrito, sus modelos, QR, confirmación, devoluciones, navegación global ni seguridad.

## Implementaciones reales inspeccionadas

### `get_all_disponibles()`

Antes: consulta `AlmacenArticulo`, carga `imagenes` mediante `selectinload`, filtra `stock_actual > 0` y `activo IS TRUE`, ordena por nombre ascendente y ejecuta `.all()`. Ya evitaba N+1; esta mejora era preexistente en el workspace y no se atribuye a este trabajo.

Después: conserva exactamente esa consulta cuando `q` está ausente o contiene solo espacios. Si hay texto, agrega una condición OR sobre nombre, código Excel, serie, marca y modelo. No se modifican stock, tipos admitidos ni reglas de inventario. La condición textual se comparte con `search()` para evitar duplicar SQL.

### `buscar_articulos()`

El servicio existente elimina espacios exteriores. Con menos de dos caracteres devuelve `repo.get_all_disponibles()`; con dos o más llama `repo.search(termino.strip())`. `search()` filtra activos, pero NO stock positivo. Busca con ILIKE en nombre/código/serie/marca/modelo y carga imágenes con `selectinload`.

Por eso el catálogo NO utiliza `/articulo/buscar`. Se mantiene su semántica original, incluido el tratamiento previo de comodines. La búsqueda nueva de disponibles interpreta `%`, `_` y `/` literalmente usando escape SQL y parámetros enlazados.

### Elegibilidad y confirmación

La fuente definitiva sigue siendo el backend: activos y stock positivo en catálogo; comprobación actual de activo, cantidad y stock al entregar. Los tipos EQUIPO, HERRAMIENTA y CONSUMIBLE son los tipos actuales del modelo. No se introdujeron nuevas exclusiones por categoría, estado físico o costos.

La solicitud pendiente no descuenta stock. Tanto confirmación QR como registro efectivo consultan el artículo con `bloquear=True`; el repositorio aplica `with_for_update()` antes de validar/descontar stock. `descontar_stock()` rechaza cantidades no positivas y superiores al stock, actualiza `stock_actual` y, cuando corresponde, `en_prestamo`. Se preserva la restricción existente de una unidad para activos de alto valor.

**Pendiente de revisión fuera del alcance:** `AuditoriaService.registrar()` hace `db.commit()` dentro del flujo de préstamo, antes de finalizar las operaciones posteriores y el PDF. Una excepción posterior puede dejar inventario/préstamo persistidos aunque el servicio intente rollback y devuelva error. No se cambió este comportamiento. Revisar la unidad transaccional antes de modificarla. Los bloqueos observados sustentan la protección de stock en una base con bloqueo de filas; no se certifica concurrencia PostgreSQL real con pruebas SQLite. También quedan por probar deadlocks entre préstamos con varios artículos y orden de bloqueo distinto.

## Cambios y responsabilidades

### Flutter

1. `lib/features/almacen/prestamos/providers/articulo_provider.dart`: query autoDispose, debounce 400 ms para texto, carga inmediata para búsqueda vacía, Dio compartido y CancelToken. Cada cambio invalida el future anterior; Riverpod publica únicamente la ejecución actual, aun si llega tarde una respuesta anterior. Se cancelan timer/HTTP al reemplazar la consulta o cerrar el catálogo. No hay caché permanente ni polling.
2. `lib/features/almacen/prestamos/screens/articulos_disponibles_screen.dart`: elimina `.where()` local y la copia filtrada; compone encabezado RAMIS, búsqueda accesible, estados de carga/error/vacío y lista virtualizada. Mantiene carrito en Consumer separado, añade pull-to-refresh y recarga al volver del carrito. No hay HTTP en `build()`.
3. `lib/features/almacen/prestamos/widgets/prestamo_articulo_widgets.dart`: reutiliza las dos clases existentes. Tarjetas compactas con icono por tipo, código y chip de stock; selección mediante acción explícita. El selector existente se presenta en modal inferior, con incremento/decremento deshabilitados en límites y confirmación válida entre 1 y disponible.
4. `test/features/almacen/prestamos/catalogo_test.dart`: pruebas de búsqueda/debounce/respuesta tardía/error/reintento/limpieza, 450 artículos, construcción diferida, desplazamiento al último registro, selección acumulada, carrito y navegación de ida/vuelta con nueva consulta, stock cero y Light/Dark. Genera capturas en `build/catalogo_light.png` y `build/catalogo_dark.png`.

Antes de abrir el selector se valida activo/stock, y se resta lo ya seleccionado en el carrito. Se repite la comprobación de cantidad al cerrar el modal. Esto no reserva stock ni sustituye la validación del servidor. No cambia las operaciones del carrito ni sus otros consumidores.

Se reutilizan RamisScaffold, RamisAppBar, RamisCard, RamisButton, RamisTextField, RamisStatusChip, RamisLoading, RamisEmptyState, RamisErrorView, RamisSpacing, RamisRadius, colorScheme, textTheme y context.ramis. No se crearon componentes paralelos, paquetes, paletas, imágenes por fila ni fondos decorativos.

### Backend

1. `app/repositories/almacen_articulo_repository.py`: `get_all_disponibles(q="")` y predicado textual compartido. Conserva las opciones de carga existentes y no modifica operaciones de escritura.
2. `app/routers/almacen_articulo_router.py`: parámetro opcional `q: str = ""` únicamente en `/articulo/disponibles`.
3. `app/test/unit/test_catalogo_disponibles.py`: tres pruebas de consultas reales SQLite, contrato HTTP, disponibilidad, campos buscables, caracteres especiales, ausencia de N+1 y permisos administrativos conservados.
4. Este informe, disponible en `docs/` de ambos proyectos. Capturas de revisión en `docs/catalogo_light.png` y `docs/catalogo_dark.png` del frontend.

### Compatibilidad HTTP y seguridad

- `/articulo/disponibles` sigue devolviendo `list[ArticuloSchema]`, sin envoltorio, sin paginación ni campos retirados. Ausencia de `q`, cadena vacía y espacios conservan catálogo y orden.
- `/articulo`, `/articulo/buscar` y `/articulo/{id}` conservan contratos. Prueba HTTP verifica los cuatro y 404 para ID inexistente.
- Se mantiene la protección administrativa de creación/actualización/activación/desactivación/imágenes y las dependencias originales. Ningún rol, permiso, token, sesión o autenticación fue editado.
- Las rutas GET de lectura ya carecían de UserDep en el router encontrado; se conserva ese comportamiento, sin ampliar ni reducir accesos.
- Prueba HTTP confirma 403 para trabajador al intentar actualizar o desactivar. Sin migraciones, cambios de esquema ni datos de producción usados en pruebas.

## Mediciones reproducibles y decisión sobre paginación

Datos sintéticos en SQLite en memoria: 450 herramientas disponibles, un consumible disponible con caracteres especiales, un artículo sin stock y otro inactivo. Sin archivos de imágenes; sí se conserva su campo de metadatos. No representa latencia HTTP, PostgreSQL de despliegue ni rendimiento Android físico.

Se midieron 15 iteraciones intercaladas, expulsando el identity map antes de cada consulta; se informa mediana. La consulta inicial se reconstruyó con el código inspeccionado antes de editar, conservando su selectinload preexistente.

| Métrica | Antes / consulta completa original | Después / completa | Después / búsqueda EQ-449 |
| --- | ---: | ---: | ---: |
| Registros elegibles | 451 | 451 | 1 |
| Consultas SQL incluyendo imágenes | 2 | 2 | 2 |
| JSON UTF-8 compacto | 207.786 bytes | 207.786 bytes | 462 bytes |
| Mediana repositorio, corrida de referencia | 15,27 ms | 16,58 ms | 3,67 ms |

No se afirma que la carga completa sea más rápida: es esencialmente la misma consulta y la medición no demuestra una mejora. La búsqueda remota devuelve menos registros cuando el texto es selectivo y evita filtrar/copiar toda la lista en cada build Flutter. Una consulta amplia puede devolver todo el catálogo.

No se añade paginación: el tamaño sintético observado ronda 203 KiB, la consulta no presenta N+1 y la lista ya construye filas bajo demanda. Esto es una decisión provisional con evidencia sintética; medir datos reales, longitud de descripciones y número de imágenes antes de decidir límites opcionales. Se preserva el payload completo para no romper consumidores. Los índices normales de código/serie no garantizan acelerar ILIKE con `%texto%`; evaluar planes y estadísticas reales si crece significativamente el inventario.

Antes el buscador local no hacía HTTP por pulsación, pero no cumplía el requisito de búsqueda remota. Después, la prueba escribe consultas sucesivas dentro del debounce y verifica que no sale la intermedia: una carga inicial y una búsqueda estabilizada. No se presenta como reducción respecto de la búsqueda local original. La recarga al volver del carrito es intencional para obtener stock actualizado.

## Validación ejecutada

- Git inspeccionado antes de editar: numerosos cambios previos, incluidos repositorio backend y todo el módulo Flutter de préstamos sin seguimiento. Se preservaron; el diff contra HEAD incluye trabajo ajeno a esta tarea.
- Intentos iniciales de pruebas: Flutter necesitaba acceder al lock del SDK fuera del workspace. Backend no tenía pytest en `.venv`/Python global; el entorno `venv` sí lo tenía, pero faltaban dependencias.
- Se habilitó la ejecución del SDK y se instalaron solo en `venv` python-dotenv y reportlab ya declarados, y tzdata para ZoneInfo en Windows. No se cambió requirements ni pubspec. Las versiones instaladas preexistentes de FastAPI/SQLAlchemy no coinciden con requirements; las mediciones usan ese entorno existente.
- `dart format`: correcto en tres archivos Dart de implementación y prueba nueva. Se redirigió APPDATA a `build/catalogo_tooling` para evitar permisos de telemetría.
- `dart analyze` de esos cuatro archivos: **No issues found**.
- `flutter analyze --no-pub` global: se ejecutó; encontró incidencias en código existente. La corrida inicial informó 172, incluida una importación no usada de la prueba nueva que se retiró. La corrida global final informa 171 incidencias y ninguna pertenece a los cuatro archivos del alcance; su análisis específico está limpio. Log final: `build/catalogo_analyze.txt` del frontend. No se reparó código de otros módulos.
- `flutter test --no-pub test/features/almacen/prestamos/catalogo_test.dart test/features/almacen/articulos --reporter expanded`: **9 aprobadas**. Catálogo a 390 × 844; 450 artículos; tarjetas construidas inicialmente <15; recorrido hasta artículo 449; navegación real a CarritoScreen y retorno con dos consultas totales del catálogo; cantidades preservadas.
- Pruebas existentes del Design System: **6 aprobadas, 2 fallidas**, relacionadas con superficie del logo y selección del fondo oscuro al cambiar tema. Se observaron en la corrida de referencia de las pruebas existentes; esos componentes universales no fueron modificados.
- `venv/Scripts/python -m pytest app/test/unit/test_catalogo_disponibles.py -q -s`: **3 aprobadas**. Sintaxis Python de archivos modificados también comprobada.
- Suite backend completa: dos módulos no se pueden recolectar por ausencia de pandas (`test_articulo_gestion.py`, `test_articulo_integration.py`). No se alteró el entorno a una versión diferente de pandas para sortear la incompatibilidad con el Python 3.14 existente.
- Suite backend ejecutable, excluyendo esos dos archivos: **67 aprobadas, 48 fallidas, 7 errores**. Se repitió en copia aislada del estado inicial del catálogo (mismos archivos preexistentes del resto del proyecto): **64 aprobadas, 48 fallidas, 7 errores**. Los mismos identificadores fallan; la diferencia son las tres pruebas nuevas aprobadas. Ejemplos de problemas existentes: `upsert_articulo` inexistente en pruebas RF01, esquemas/rutas obsoletos y fixtures ausentes. No se afirma que la suite completa esté verde.
- Las ejecuciones amplias y la comparación inicial se hicieron en `output/catalogo_suite` y `output/catalogo_baseline` con TESTING=1 y SQLite en memoria, aislando archivos generados de los documentos reales. Logs en `output/catalogo_*tests.txt` del backend.
- Capturas Light/Dark revisadas visualmente con Inter e iconos reales. Sin desbordamiento observado en los casos aprobados. El tema System sigue dependiendo de la infraestructura existente sin cambios.

## Pendientes y límites

1. Revisión de transacciones de auditoría/confirmación antes de intervenir ese flujo; no se implementó el cambio fuera del alcance.
2. Prueba simultánea con dos conexiones PostgreSQL reales y stock compartido, incluyendo errores posteriores a auditoría. SQLite no certifica `FOR UPDATE`.
3. Profiling en Android modesto real (frames, memoria, teclado, escalado de accesibilidad y red lenta). La virtualización y las pruebas funcionales están verificadas; FPS y fluidez física no fueron medidos.
4. Rendimiento/payload con datos reales y metadatos de imágenes abundantes; no se consultó ni modificó producción.
5. Reparar las pruebas heredadas y completar dependencias del entorno en una tarea independiente. No hay regresiones conocidas dentro de las pruebas del alcance, pero el estado global tiene los fallos indicados.
6. Stock del catálogo es una instantánea: otros usuarios pueden consumirlo antes de confirmar. Backend mantiene la decisión definitiva. Las pantallas de carrito ajenas al alcance conservan sus validaciones y comportamiento existentes.
