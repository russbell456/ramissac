# Infraestructura y DevOps

La infraestructura de Orbit está definida como código (IaC) mediante un archivo `docker-compose.yml`, que coordina el ciclo de vida de los servicios, sus dependencias, variables de entorno y mapeo de puertos.

## Rol de cada Contenedor

### 1. Aplicación y Datos
- **`fastapi_app`**: Servidor de aplicaciones corriendo Python. Expone el puerto `8000`. Es el núcleo funcional que procesa las solicitudes de los clientes.
- **`postgres_db`**: Instancia de PostgreSQL 15 optimizada. Está configurada con volúmenes persistentes (`postgres_data`) y no expone puertos al exterior en el entorno de producción (solo se accede desde `devops_network`).

### 2. CI/CD y Calidad
- **`jenkins_server`**: Automatiza el flujo de trabajo. Configurado con acceso al `docker.sock` para poder levantar contenedores efímeros durante las fases de pruebas y construcción.
- **`sonarqube`**: Servicio web de análisis estático de código. Procesa los reportes generados durante las construcciones en Jenkins.
- **`sonar_db`**: Base de datos Postgres dedicada a SonarQube. Aislada del resto del sistema.

### 3. Proxy e Interfaz (Nginx)

El contenedor de **Nginx** sirve como la puerta de enlace a la infraestructura y como servidor web estático.

```yaml
# Extracto representativo de configuración en Docker Compose
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - allure_reports:/usr/share/nginx/html/allure:ro
    depends_on:
      - fastapi_app
```

#### Configuración del Proxy Nginx

Nginx cumple dos funciones vitales en Orbit:

1. **Proxy Inverso (Reverse Proxy):** Redirige el tráfico entrante. Por ejemplo, puede rutear peticiones al prefijo `/api` hacia el contenedor de FastAPI en el puerto `8000`.
2. **Servidor de Reportes (Allure):** Al finalizar los tests en el pipeline de CI/CD, se genera un reporte HTML de Allure en un volumen compartido (`allure_reports`). Nginx monta este volumen en modo lectura y lo sirve estáticamente.

!!! tip "Visualización de Reportes"
    Una vez que el pipeline finaliza, los reportes de calidad y pruebas están disponibles instantáneamente a través de Nginx accediendo a `http://<IP_SERVIDOR>/allure`.
