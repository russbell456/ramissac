# API Reference

El backend de Orbit expone una API RESTful documentada automáticamente mediante **Swagger UI** y **ReDoc**, gracias a las capacidades integradas de FastAPI.

!!! tip "Documentación Interactiva"
    En un entorno en ejecución, puedes acceder e interactuar con todos los endpoints de la API navegando a la ruta `http://<IP_SERVIDOR>:8000/docs` (Swagger UI) o `http://<IP_SERVIDOR>:8000/redoc` (ReDoc).

A continuación, se presenta un template profesional de cómo se estructuran y documentan los endpoints clave del dominio de Herramientas.

---

## Módulo: Herramientas (`/api/v1/tools`)

### Obtener Inventario
Recupera una lista paginada de todas las herramientas en el inventario.

- **URL:** `/api/v1/tools/`
- **Método:** `GET`
- **Autenticación requerida:** Sí (Bearer Token)

**Parámetros de Consulta (Query Parameters):**
- `skip` (int, opcional): Número de registros a omitir (default: 0).
- `limit` (int, opcional): Número máximo de registros a retornar (default: 100).

**Respuesta Exitosa (200 OK):**
```json
[
  {
    "id": 1,
    "name": "Taladro Inalámbrico Bosch",
    "status": "AVAILABLE",
    "serial_number": "BOSCH-12345",
    "created_at": "2023-10-15T10:00:00Z"
  }
]
```

---

### Registrar Nueva Herramienta
Añade una nueva herramienta al inventario del sistema.

- **URL:** `/api/v1/tools/`
- **Método:** `POST`
- **Autenticación requerida:** Sí (Rol Administrador)

**Cuerpo de la Petición (Request Body):**
```json
{
  "name": "Amoladora Angular Makita",
  "serial_number": "MAK-9876",
  "category": "Herramienta Eléctrica"
}
```

**Respuestas:**
- **201 Created:** Herramienta registrada exitosamente.
- **400 Bad Request:** Número de serie duplicado o datos inválidos.

---

### Solicitar Préstamo de Herramienta
Registra un nuevo préstamo para un usuario.

- **URL:** `/api/v1/tools/{tool_id}/loan`
- **Método:** `POST`
- **Autenticación requerida:** Sí

**Parámetros de Ruta:**
- `tool_id` (int): ID único de la herramienta.

**Cuerpo de la Petición:**
```json
{
  "expected_return_date": "2023-11-20T17:00:00Z",
  "project_reference": "Obra Sur - Fase 2"
}
```

**Respuestas:**
- **200 OK:** Préstamo registrado y estado de herramienta actualizado a `IN_USE`.
- **404 Not Found:** Herramienta no existe.
- **409 Conflict:** La herramienta no está disponible (`status != AVAILABLE`).
