# Módulo RQ + Campo

Este módulo permite que el ingeniero cree un requerimiento, lo mantenga como borrador, lo firme desde Flutter y lo envíe como PDF a un máximo de tres correos en una sola operación.

Todos los endpoints requieren el token JWT actual.

## Flujo para Flutter

1. Crear el borrador con `POST /rq-campo`.
2. Consultarlo con `GET /rq-campo/{id}` o listar los propios con `GET /rq-campo`.
3. Reemplazar su contenido mientras esté en borrador con `PUT /rq-campo/{id}`.
4. Capturar la firma como PNG/JPEG base64 y llamar `POST /rq-campo/{id}/firmar-y-enviar`.
5. Si el SMTP falla, el RQ queda en estado `FIRMADO`, conserva la firma y puede reintentarse con `POST /rq-campo/{id}/reenviar`.
6. Consultar stock y faltantes con `GET /rq-campo/{id}/stock`.
7. Obtener el PDF con `GET /rq-campo/{id}/pdf`, también disponible antes de firmar como vista previa de borrador.

La obra debe existir y tener estado `activo`. El servidor toma su nombre registrado; no acepta un nombre libre como sustituto de la obra. Si la obra se cierra después de crear el borrador, no se permite firmarlo.

La validación del jefe queda para su futuro panel. El flujo actual mantiene la firma del solicitante y el envío a Logística.

### Adjuntos y ficha del catálogo

Cada ítem admite `adjuntos`: una lista de objetos con `nombre`, `tipo_mime` y `contenido_base64`. Se permiten PNG, JPEG y PDF, hasta cinco archivos de 5 MB por ítem y 20 MB en todo el requerimiento. El contenido se conserva en el servidor y en las respuestas de consulta.

Los productos catalogados pueden solicitarse con stock cero. Se copian sus medidas, descripción, especificaciones, observación, ficha técnica y fotos cuando esos datos no se proporcionan en el requerimiento. La copia conserva la información emitida aunque el catálogo se edite después.

El PDF incluye las fotografías en un anexo A4 con hasta seis imágenes por página. Las fichas PDF originales se adjuntan al mismo correo junto al requerimiento. El módulo no reserva ni descuenta stock al solicitar.

La ficha del artículo se edita mediante `PUT /articulo/{id}` con `medidas`, `especificaciones` y `observacion`, además de los campos anteriores. La ficha PDF se carga con `POST /articulo/{id}/ficha-tecnica` (multipart, campo `file`) y se consulta con `GET /articulo/{id}/ficha-tecnica`. La carga requiere rol `admin`, `almacenero` o `logistica`; la descarga requiere sesión autenticada.

Las nuevas tablas `almacen_articulo_fichas` y `rq_campo_adjuntos` se crean mediante el mecanismo existente `Base.metadata.create_all` al iniciar el backend. No se modifican columnas de las tablas anteriores.

### Ejemplo de creación

```json
{
  "obra_id": 1,
  "numero_contrato_servicio": "CS-2026-008",
  "numero_cotizacion": "COT-034",
  "descripcion_general": "Material requerido para instalación",
  "items": [
    {
      "tipo": "CATALOGADO",
      "articulo_id": 12,
      "cantidad": 2,
      "observacion": "Uso en campo"
    },
    {
      "tipo": "NO_CATALOGADO",
      "nombre_producto": "Manómetro 2 pulgadas",
      "unidad_medida": "UND",
      "cantidad": 1,
      "medidas": "0-150 PSI"
    }
  ]
}
```

### Ejemplo de firma y envío

```json
{
  "firma_base64": "data:image/png;base64,iVBORw0KGgo...",
  "destinatarios": [
    "compras@empresa.com",
    "logistica@empresa.com",
    "gerencia@empresa.com"
  ]
}
```

Los destinatarios pueden omitirse si `RQ_EMAIL_DESTINATARIOS` está configurado. Para una cuenta Gmail de prueba se debe activar la verificación en dos pasos y crear una contraseña de aplicación; esa contraseña se guarda únicamente en `RQ_SMTP_PASSWORD` del servidor.
