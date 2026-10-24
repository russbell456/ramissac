# Transportes V3 — despliegue y operación

Fecha: 22/10/2026. Especificación: decisiones D01–D14 de la sección 5 del documento aprobado del directorio PPP.

## Orden de despliegue

1. Respaldar la base y el almacenamiento de `uploads/transportes` del entorno elegido.
2. Aplicar `app/scripts/migrations/006_mejoras_v2.sql` si el entorno aún no tiene V2.
3. Aplicar `app/scripts/migrations/007_mejoras_v3_decisiones.sql` antes de iniciar el backend nuevo. Está envuelta en una transacción y permite repetición.
4. Instalar `requirements.txt` en el entorno Python del servidor y desplegar el backend.
5. Desplegar Flutter usando el mismo backend. La nueva campana abre documentos, alertas, reportes PDF y funciones administrativas.

La migración fue probada en una instancia PostgreSQL 18 separada, en `127.0.0.1:55437`, base `codex_v3_verify`. No se aplicó a `DATABASE_URL` ni a producción.

## Horarios y alertas

El ciclo se inicia con el lifespan de FastAPI, cada 30 segundos. Usa hora fija de Lima, UTC−5:

- Recordatorios de jornadas abiertas a las 19:00 y 21:00, una notificación por destinatario/jornada/hora.
- Cierre a las 23:59, conservando el odómetro conocido y marcando regularización pendiente.
- Recuperación de cierres atrasados después de reiniciar el servidor.
- Reconciliación de condiciones documentales, unidades rojas y mantenimiento por kilometraje a 500 km y 0 km.

`TRANSPORTES_SCHEDULER=0` deshabilita el ciclo, por ejemplo durante un mantenimiento técnico. En pruebas se deshabilita por `TESTING=1`. Las réplicas PostgreSQL se coordinan mediante un advisory lock en conexión dedicada. Las alertas persisten aunque FCM no esté configurado; la campana consulta las notificaciones almacenadas.

## Firebase

El servidor usa `firebase-admin` y las credenciales de aplicación de Google. Configurar `GOOGLE_APPLICATION_CREDENTIALS` con la ruta al archivo de cuenta de servicio autorizado. Ese archivo no se incluye en el repositorio.

Flutter recibe opciones del proyecto en compilación:

```text
--dart-define=FIREBASE_API_KEY=...
--dart-define=FIREBASE_APP_ID=...
--dart-define=FIREBASE_SENDER_ID=...
--dart-define=FIREBASE_PROJECT_ID=...
```

El `APP_ID` debe corresponder a la plataforma compilada. En iOS también se requieren firma/provisionamiento con Push Notifications y APNs configurado en Firebase. La campana web funciona por HTTP; los push web necesitan además VAPID y un service worker Firebase configurado en el alojamiento. No se ha verificado entrega real a Firebase/APNs porque no se proporcionaron credenciales ni dispositivos del proyecto.

Al faltar opciones Firebase, la aplicación mantiene la campana y las alertas en su almacenamiento del backend. Los tokens se registran por sesión y se invalidan al salir; el envío fallido queda para reintento.

## Trabajo sin señal

Las fotografías se seleccionan con límite de resolución 1920 y calidad JPEG 80. Cada observación admite cinco fotos y cada archivo como máximo 10 MB. La API verifica contenido real de imágenes y limita informes PDF.

Los reportes y fotografías sin señal quedan en una cola persistente cifrada mediante el almacenamiento seguro de Flutter, separada por servidor y usuario. El mismo identificador de solicitud se conserva durante reintentos. La cola no guarda contraseñas ni JWT y no se elimina al cerrar sesión. Las lecturas ya consultadas de jornada/flota se conservan para recuperar la consola offline.

La aplicación reintenta cada 30 segundos mientras está abierta. Workmanager registra reintentos con red disponible en Android/iOS; el sistema operativo decide la oportunidad real de ejecución y puede retrasarla por ahorro de batería. En web la sincronización se realiza mientras la aplicación está abierta. El panel muestra pendientes y último error, y permite reintento manual. No se simulan aperturas de conducción offline: los reportes se adjuntan a una jornada conocida. Las incidencias capturadas durante el intervalo de una jornada se pueden sincronizar después de su cierre.

## Operación administrativa

- Alta rápida: vehículo con placa/modelo, conductor con nombre/DNI. Los documentos faltantes generan alertas sin bloquear el inicio por motivos documentales.
- Los conductores dados de alta rápidamente tienen credenciales aleatorias no utilizables. Administración configura correo y contraseña inicial desde el listado de conductores antes de que ingresen a la app.
- Renovar documentos desde el historial documental; cada renovación archiva la versión anterior y registra la aprobación.
- Los mantenimientos mayores o preventivos exigen informe PDF y firma; las reparaciones menores exigen fotografía y descripción. La ejecución del mecánico no aprueba ni libera la unidad.
- La firma puede precargarse dibujándola en el perfil administrativo. La API también acepta firma táctil en el cierre. El acta PDF estampa nombre, usuario, fecha/hora de Lima, firma y fotografías.
- Resolver observaciones conserva la evidencia original y audita la aprobación de la reparación.
- Las correcciones de kilometraje se realizan por sus endpoints específicos, con motivo de 15 caracteres y ventana de 72 horas sobre el cierre. La edición general de vehículo no permite saltarse la auditoría.
- La placa no cambia si existen jornadas. Las bajas son lógicas y las unidades inactivas se conservan en su listado.

## Validación reproducible

```powershell
python -m pytest app/test/integration/test_transportes_integration.py app/test/integration/test_transportes_avanzado_integration.py app/test/integration/test_v3_decisiones.py app/test/unit/test_mejoras_v3.py app/test/unit/test_mejoras_v2.py app/test/unit/test_jornada_transporte.py -q
```

Para repetir sobre la instancia temporal ya preparada, establecer `TRANSPORTES_TEST_DATABASE_URL=postgresql+psycopg2://codex_test@127.0.0.1:55437/codex_v3_verify`. El conftest rechaza cualquier otra URL PostgreSQL para evitar limpiar datos de un entorno real.

`python -m app.scripts.verify_v3_postgres` verifica esquema V2, aplicación de 006/007 y repetición de 007 exclusivamente en esa instancia de prueba. No arranca ni modifica servidores externos.

En Flutter: `flutter test --no-pub`, `flutter analyze --no-pub lib/features/transportes test/transport_queue_test.dart lib/main.dart`, `flutter build web --no-pub`.

Windows requiere Developer Mode o permisos de enlaces simbólicos para construir plugins nativos. `flutter pub get` resolvió y descargó las dependencias, pero informó esa restricción del equipo. La suite Flutter y la compilación web sí se ejecutaron. No se ha generado ni firmado un APK/IPA de distribución en esta sesión.

Los umbrales específicos por ruta siguen pendientes del jefe de transportes, tal como establece D12; se usan los generales aprobados de 300/600 km.
