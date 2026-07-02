# Documentación del Backend

El backend del sistema Orbit está construido con **FastAPI**, un framework moderno y de alto rendimiento para construir APIs con Python, utilizando **Uvicorn** como servidor ASGI.

## Estructura del Proyecto

El código está organizado siguiendo los principios de Clean Architecture, separando claramente las responsabilidades. Empleamos el patrón **Repositorio / Servicio** para abstraer el acceso a datos y encapsular la lógica de negocio.

```text
backend/
├── app/
│   ├── api/          # Rutas y controladores de FastAPI (Endpoints).
│   ├── core/         # Configuraciones, seguridad y variables de entorno.
│   ├── db/           # Configuración de base de datos y migraciones (Alembic).
│   ├── models/       # Modelos de SQLAlchemy (Tablas de la DB).
│   ├── schemas/      # Modelos Pydantic (Validación de entrada/salida).
│   ├── repositories/ # Patrón Repositorio: Acceso directo a la base de datos.
│   └── services/     # Patrón Servicio: Lógica de negocio (Préstamos, Inventario).
├── tests/            # Pruebas unitarias y de integración.
├── main.py           # Punto de entrada de la aplicación FastAPI.
└── requirements.txt  # Dependencias del proyecto.
```

### Patrón Repositorio y Servicio

- **Repositorios (`repositories/`):** Clases encargadas exclusivamente de interactuar con la base de datos (operaciones CRUD). No contienen reglas de negocio.
- **Servicios (`services/`):** Clases que contienen la lógica central del negocio. Utilizan los repositorios para obtener/guardar datos y aplican reglas (ej. "No se puede prestar una herramienta que está en mantenimiento").

## Variables de Entorno

La configuración del backend se gestiona a través de un archivo `.env`, el cual es inyectado por Docker Compose.

```bash
# Ejemplo de archivo .env
PROJECT_NAME="Orbit - Gestión de Herramientas"
VERSION="1.0.0"
DEBUG=True

# Configuración de Base de Datos
POSTGRES_USER=ramis_admin
POSTGRES_PASSWORD=securepassword123
POSTGRES_SERVER=db
POSTGRES_PORT=5432
POSTGRES_DB=orbit_db

# Seguridad
SECRET_KEY=su_llave_secreta_aqui
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

!!! note "Validación de Entorno"
    FastAPI utiliza `pydantic.BaseSettings` en el módulo `core/config.py` para cargar y validar automáticamente estas variables de entorno en tiempo de ejecución.

## Ejecución de Pruebas

El proyecto utiliza `pytest` para la ejecución de pruebas automatizadas y `Allure` para la generación de reportes detallados.

Para correr los tests localmente (dentro del contenedor o entorno virtual):

```bash
# Instalar dependencias de desarrollo
pip install -r requirements.txt

# Ejecutar pruebas y generar resultados para Allure
pytest --alluredir=allure-results
```

Estos resultados crudos (`allure-results`) son luego procesados por el pipeline de CI/CD para generar un reporte HTML consumible por Nginx.
