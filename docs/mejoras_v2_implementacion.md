# Implementación de mejoras V2

Fecha: 15 de octubre de 2026.

## Cambios implementados

- Empezar a Conducir abre una jornada; las demás actividades nuevas requieren la jornada activa del mismo conductor y vehículo. Los registros históricos conservan su independencia. Se impide abrir o asignar otra jornada al mismo conductor. Las escrituras se serializan mediante bloqueos de fila en PostgreSQL.
- Semáforo persistido en vehículo y jornada. Observación leve: amarillo; falla grave: rojo, vehículo en mantenimiento y avería crítica visible para administración. El checklist de apertura no conforme cancela la apertura; los reportes en ruta conservan la jornada en curso, sin fecha ni odómetro de cierre. La jornada solo se liquida con Finalizar Jornada. Una subacción propaga la alerta y su evidencia a la jornada principal. La inspección posterior al mantenimiento aprobada restaura el verde.
- Restricción de grúa validada en servidor y formulario mediante tipo de vehículo, con compatibilidad para las dos placas históricas cuando falta el tipo. Camionetas y coaster restringen las mediciones y trabajos externos según la tabla del plan.
- Checklist agrupado en Fluidos y Motor, Sistema Eléctrico y Luces, Neumáticos y Ruedas y Seguridad y Documentos. Se conservan los once textos originales y se agregan los controles mecánicos del plan. Los ítems desmarcados representan no conformidades: para registrarlos se requieren observaciones y evidencia.
- Observaciones apagadas por defecto; al activarlas se exigen descripción, severidad y fotografía. Reportar una incidencia exige evidencia. Cámara y galería, previsualización, eliminación y reemplazo, tanto en actividades como en los checklists y las incidencias de Mi Jornada.
- POST /api/jornadas/fotos admite imágenes JPEG, PNG y WebP verificadas por contenido, de hasta 5 MB y 25 megapíxeles, con nombre aleatorio. Las rutas de evidencia se restringen al almacenamiento de transportes.
- La vista inicial del conductor es Seguimiento de la Jornada Actual, con vehículo, conductor, semáforo inherente, odómetro inicial y timeline cronológico del día. Historial queda en una pestaña separada. Mi Jornada y el panel de administración muestran actividades relacionadas y fotografías ampliables. Administración muestra conteo de vehículos por color, kilometraje, consumo y rendimiento; los datos se refrescan cada 30 segundos y mediante actualización manual.
- Abastecimientos conservan galones, costo, factura/vale y odómetro. El cierre suma todos los abastecimientos de la jornada y estima consumo como (porcentaje inicial - porcentaje final) / 100 × capacidad del tanque en galones + galones abastecidos. Rendimiento: km recorridos / galones consumidos. Se aceptan porcentajes y los niveles históricos 1/4, 1/2, 3/4 y Lleno. Si falta capacidad o los datos arrojan consumo negativo, el consumo y rendimiento quedan sin estimación; no se inventan valores. El rendimiento de consumo cero queda sin estimación.
- En Administración > Flota, tocar un vehículo permite registrar su tipo y capacidad real de tanque. No se presuponen capacidades del catálogo.

## Aplicación y revisión

1. Respaldar la base de datos del entorno y ejecutar app/scripts/migrations/006_mejoras_v2.sql antes de iniciar el backend actualizado. La migración es aditiva y repetible; no reagrupa ni elimina jornadas históricas. La migración no se ha ejecutado sobre una base operativa en este trabajo.
2. Publicar servidor y app conjuntamente: la versión anterior de la app permitía actividades sin jornada activa. Las jornadas asignadas continúan usando checklist inicial y final.
3. Configurar capacidades reales desde Flota. Las jornadas cerradas sin esta información conservan su consumo sin estimar.
4. Persistir uploads/transportes en el despliegue, de igual manera que los demás archivos de uploads.
5. Flutter incorporó image_picker y permisos de cámara/galería en iOS. En Windows, la preparación de plugins requiere Modo de desarrollador para crear enlaces simbólicos; la resolución de dependencias se completó y las pruebas se ejecutaron con --no-pub. La cámara física, la compilación móvil y la migración en PostgreSQL requieren verificación en sus entornos respectivos.
6. Preparado para auditoría del Tech Lead/Gemini. No se enviaron mensajes externos ni se realizó despliegue.

## Verificación

- Jornadas y mejoras V2: 34 pruebas del servidor aprobadas, incluyendo jerarquía, concurrencia lógica de apertura, restricciones, semáforo, evidencia, carga real de imágenes, consumo y recuperación posterior al mantenimiento.
- Flutter: 23 pruebas aprobadas; análisis sin errores. Los avisos generales previos del proyecto se registran en analyze-v2.log.
- Suite completa del servidor: 138 aprobadas y 56 fallidas. Se exportó HEAD a una copia aislada y se compararon los identificadores de los fallos fuera de las pruebas de jornada modificadas: los mismos 56 fallos ya estaban presentes, sin fallos nuevos. Incluyen fixtures de transportes con rol almacenero rechazado por permisos existentes, y pruebas de almacén/préstamos que requieren mantenimiento independiente.
- Las pruebas de persistencia usan SQLite en memoria. No sustituyen una prueba de concurrencia con múltiples conexiones en PostgreSQL.


## Actualización de seguimiento continuo (15/10/2026)

- Selector de vehículo compartido para apertura y asignación: verde seleccionable, amarillo seleccionable con advertencia y descripción previa pendiente, rojo visible pero deshabilitado. El servidor responde 400 ante apertura, asignación o checklist inicial sobre una unidad roja.
- La consola consulta la jornada y el estado del vehículo cada 30 segundos, además de actualizarse al guardar una acción o una observación y mediante actualización manual. Los fallos de carga se muestran con opción de reintento, sin asumir que no hay jornada.
- Reportar Observación abre un formulario con switch, severidad, foto y descripción. Un reporte grave deja la unidad inoperativa y genera la alerta, pero no cierra la jornada. Una observación leve posterior no degrada el rojo ni oculta la descripción crítica pendiente. La unidad permanece roja incluso tras cerrar la jornada, hasta la inspección posterior al mantenimiento aprobada.
- Operar Grúa solicita actividad y horómetros inicial/final; omite kilometraje y combustible. La petición incluye jornada_padre_id. El servidor acepta esta subacción sin odómetro y no modifica el kilometraje del vehículo, el odómetro final ni la fecha de cierre de la jornada padre, incluso si un cliente anterior envía un kilometraje.
- Finalizar Jornada muestra odómetro inicial y galones abastecidos, exige odómetro final y combustible de cierre y presenta consumo/rendimiento preliminares. Tras confirmar se muestra la liquidación del servidor y se vuelve a la vista sin jornada activa.
- Las respuestas de detalle incluyen los datos de las subacciones para el timeline (galones, costo, vale y horómetros). El vehículo expone observaciones_pendientes para la advertencia preventiva. No se agregan columnas nuevas respecto a la migración 006 ya preparada.
- Pruebas nuevas de interfaz cubren selector rojo/amarillo, consola, reporte grave con fotografía sin cerrar, grúa vinculada sin kilómetros y cierre con liquidación. Las pruebas del servidor verifican los mismos contratos y la persistencia del estado crítico.
