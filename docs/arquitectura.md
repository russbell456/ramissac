# Arquitectura del Sistema

La arquitectura del proyecto Orbit está basada en microservicios, gestionados mediante Docker Compose. Todos los contenedores se comunican a través de una red interna dedicada, garantizando seguridad y aislamiento.

## Red de Contenedores

Todos los servicios del ecosistema están conectados a una red de tipo *bridge* llamada `devops_network`. Esta red permite la resolución de nombres por DNS interno, lo que significa que los contenedores se comunican entre sí utilizando su nombre de servicio (ej. `http://db:5432` o `http://sonarqube:9000`).

!!! tip "Aislamiento de Red"
    El uso de `devops_network` asegura que la base de datos y SonarDB no estén expuestas directamente a internet, añadiendo una capa de seguridad esencial. Sólo el proxy inverso (Nginx) y los puertos explícitamente mapeados interactúan con el exterior.

## Servicios del Ecosistema

El sistema se compone de 6 servicios principales:

| Servicio | Tecnología | Descripción | Puerto Expuesto |
| :--- | :--- | :--- | :--- |
| **Backend** | FastAPI (Python), Uvicorn | Expone la API RESTful y maneja la lógica de negocio de préstamos de herramientas. | `8000:8000` |
| **Base de Datos** | PostgreSQL 15 | Almacena los registros de usuarios, herramientas, inventario y préstamos. | `5432:5432` |
| **Proxy** | Nginx | Actúa como proxy inverso, gestiona el tráfico entrante y sirve los reportes estáticos de Allure. | `80:80` |
| **CI/CD** | Jenkins Server | Orquesta los pipelines de construcción, pruebas y despliegue. Tiene acceso al socket de Docker. | `8080:8080`, `50000:50000` |
| **Calidad de Código** | SonarQube | Plataforma para la inspección continua de la calidad del código (análisis estático). | `9000:9000` |
| **Base de Datos Sonar**| Postgres Alpine | Base de datos dedicada exclusivamente para almacenar las métricas y configuraciones de SonarQube. | N/A (Interno) |

## Volúmenes Persistentes

Para garantizar que la información no se pierda cuando los contenedores se reinician o destruyen, la arquitectura implementa los siguientes volúmenes de Docker:

```yaml
volumes:
  postgres_data:
    # Almacena de forma persistente los datos de la base de datos principal de Orbit.
  jenkins_home:
    # Mantiene la configuración, plugins, jobs y el workspace de Jenkins.
  sonarqube_data:
    # Persiste los datos de la aplicación SonarQube.
  sonarqube_extensions:
    # Guarda los plugins y extensiones de SonarQube.
  sonarqube_logs:
    # Almacena los logs de SonarQube para auditoría y depuración.
  sonar_db_data:
    # Persiste los datos de PostgreSQL utilizado por SonarQube.
  allure_results:
    # Volumen compartido para almacenar los resultados crudos de las pruebas.
  allure_reports:
    # Volumen compartido donde se generan los reportes HTML estáticos (servidos por Nginx).
```

### Gestión Especial: Jenkins y Docker Socket

El contenedor de Jenkins requiere la capacidad de interactuar con el demonio de Docker del host para poder construir y levantar contenedores dentro de sus pipelines (patrón Docker-out-of-Docker o DooD). Esto se logra montando el socket:

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
```

!!! warning "Privilegios"
    El contenedor de Jenkins se ejecuta a menudo con privilegios elevados (`privileged: true` o con el grupo Docker) para permitir esta interacción con el socket. Es vital mantener el servidor Jenkins asegurado y con políticas de acceso estrictas.
