# CI/CD y Automatización

El ciclo de Integración Continua (CI) y Entrega Continua (CD) de Orbit está diseñado para asegurar la calidad del código, evitar regresiones y mantener la documentación siempre actualizada.

## Flujo de Trabajo en Jenkins

Jenkins actúa como el orquestador principal. El pipeline (definido en un `Jenkinsfile`) sigue los siguientes pasos (Stages) de forma automatizada:

1. **Checkout:** Clona el repositorio desde el sistema de control de versiones.
2. **Build:** Construye la imagen Docker del backend.
3. **Unit Tests:** Levanta contenedores efímeros de prueba (usando el `docker.sock`), ejecuta `pytest` y guarda los resultados en formato Allure.
4. **Code Quality (SonarQube):** Envía el código y los resultados de cobertura al contenedor de SonarQube. Jenkins espera por el "Quality Gate". Si el código no cumple con los estándares, el pipeline falla.
5. **Generate Reports:** Procesa los resultados crudos de las pruebas y genera el reporte HTML estático en el volumen compartido con Nginx.
6. **Deploy (Opcional):** Si está en la rama principal, reinicia o actualiza el servicio de backend de producción.

```groovy
// Ejemplo conceptual del Stage de Pruebas en Jenkins
stage('Test & Report') {
    steps {
        sh 'docker-compose -f docker-compose.test.yml up --build --exit-code-from tests'
        sh 'allure generate allure-results -o /allure_reports_volume --clean'
    }
}
```

## Automatización de la Documentación (GitHub Actions)

La documentación que estás leyendo ahora mismo es gestionada como código bajo el modelo de **MkDocs Material** y desplegada automáticamente mediante **GitHub Actions**.

### Despliegue con `gh-deploy`

El proyecto incluye un flujo de trabajo de GitHub Actions (`deploy-docs.yml`) configurado para observar la rama `main`. Cada vez que se hace un `push` que modifica archivos en la carpeta `docs/` o el `mkdocs.yml`, ocurre lo siguiente:

1. **Trigger:** GitHub Actions detecta el push a la rama `main`.
2. **Setup:** Levanta un entorno Ubuntu virtual y configura Python.
3. **Dependencias:** Instala `mkdocs-material` y cualquier otro plugin necesario.
4. **Build & Deploy:** Ejecuta el comando `mkdocs gh-deploy --force`.

```yaml
# Extracto del workflow
name: Despliegue de Documentación
on:
  push:
    branches:
      - main
    paths:
      - 'docs/**'
      - 'mkdocs.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install mkdocs-material
      - run: mkdocs gh-deploy --force
```

!!! note "GitHub Pages"
    El comando `gh-deploy` compila los archivos Markdown en HTML estático y los sube automáticamente a una rama especial llamada `gh-pages`, la cual GitHub utiliza para servir este sitio web de forma gratuita y automática.
