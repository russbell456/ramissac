# Entregable N° 2: Plan de Auditoría SDLC

**SISTEMA:** RamisToolX  
**ORGANIZACIÓN:** Startup Orbit  
**CÓDIGO DEL DOCUMENTO:** AUD-SDLC-RAMISTOOLX-2026-001-PLAN  
**FECHA DE EMISIÓN:** 01 de julio de 2026  

---

## 1. OBJETIVOS DE LA AUDITORÍA

### 1.1 Objetivo General
Evaluar y dictaminar de manera sistemática la conformidad y madurez de los procesos de ingeniería de software implementados en el Ciclo de Vida de Desarrollo de Software (SDLC) de la aplicación Cliente-Servidor **RamisToolX**, confrontándolos con las áreas de proceso de **CMMI-DEV v1.3** (Solución Técnica [TS], Verificación [VER], Integración del Producto [IP]) y las prácticas ágiles del marco **Scrum**, con el fin de asegurar la entrega de un producto robusto, seguro y mantenible en el servidor privado de la organización.

### 1.2 Objetivos Específicos
* **OE1 (Gestión y Requisitos):** Verificar la trazabilidad del 100% de las Historias de Usuario priorizadas en el Backlog de Jira con respecto a las funcionalidades codificadas en los Pull Requests de GitHub.
* **OE2 (Calidad de Código):** Auditar los reportes estáticos obtenidos mediante el ejecutable `.jar` de SonarCloud para comprobar el estado real de la mantenibilidad, confiabilidad y el cumplimiento estricto del **89% de cobertura de código (Code Coverage)** mediante Pytest.
* **OE3 (Seguridad):** Analizar el archivo estructurado JSON emitido por Snyk para identificar, clasificar y corroborar la mitigación de vulnerabilidades o dependencias obsoletas en el backend desarrollado con FastAPI.
* **OE4 (Solución Técnica e Integración):** Evaluar los procedimientos y scripts de despliegue en el nuevo entorno del Servidor Privado, validando la persistencia de datos, el flujo de carga masiva vía Excel y el almacenamiento seguro de las actas de préstamo generadas en formato PDF.
* **OE5 (Revisiones por Pares):** Inspeccionar el cumplimiento de las políticas de control de versiones de GitHub Flow, asegurando que cada integración cuente con el registro de al menos dos (2) Peer Reviews aprobadas.

---

## 2. ALCANCE DETALLADO

El alcance operativo de esta auditoría se delimita estrictamente a los siguientes componentes técnicos y metodológicos:

* **Dimensión Metodológica:** Procesos de gestión ágil Scrum (Sprints, daily logs, criterios de aceptación en Jira) y prácticas de ingeniería basadas en CMMI-DEV v1.3.
* **Dimensión Tecnológica (Backend):** Código fuente de la API REST en Python (FastAPI), validación de la documentación interactiva en Swagger/OpenAPI y orquestación del entorno.
* **Dimensión Tecnológica (Frontend):** Código de la aplicación móvil en Dart utilizando el framework Flutter.
* **Pipeline de QA y Seguridad:** Análisis de scripts de pruebas automatizadas unitarias en Pytest, reportes en formato Word y Excel extraídos desde el `.jar` de SonarCloud, y el archivo JSON de diagnóstico de Snyk.
* **Infraestructura de Despliegue:** Análisis técnico del proceso de migración, configuración de variables de entorno y persistencia en el **Servidor Privado** (excluyendo el entorno descartado en Termux).

---

## 3. ASIGNACIÓN DE ROLES Y RESPONSABILIDADES (EQUIPO AUDITOR)

Para mantener la coherencia metodológica y asegurar la segregación de funciones dentro de la Startup Orbit, se distribuyen las responsabilidades de la auditoría de la siguiente manera:

* **Líder del Proyecto de Auditoría / Supervisor General:** Ing. Ruben Roque Sucari.

* **Auditor 1: Russbel Daniel Cari Mamani**
  * *Especialidad:* Auditor de Infraestructura, Despliegue y Base de Datos.
  * *Responsabilidades:* Inspeccionar la configuración física y lógica del Servidor Privado; auditar la persistencia de datos, el almacenamiento de actas PDF mediante rutas del servidor y el proceso de carga masiva de inventarios por Excel; redactar el Acta de Cierre.

* **Auditor 2: Pawel Armando Paricahua Adco**
  * *Especialidad:* Auditor de Calidad de Software, Código y QA.
  * *Responsabilidades:* Auditar el repositorio de GitHub y el pipeline de pruebas; analizar los reportes en Word y Excel extraídos del `.jar` de SonarCloud; validar que la cobertura en Pytest cumpla efectivamente el 89% establecido; estructurar la Matriz de Hallazgos y la Matriz de Riesgos.

* **Auditor 3: Reginaldo Dan Mayhuire Buendia**
  * *Especialidad:* Auditor de Gestión de Proyectos, Requisitos y Seguridad.
  * *Responsabilidades:* Verificar la trazabilidad de historias de usuario en Jira frente a los Pull Requests; inspeccionar las políticas de protección de ramas en GitHub (doble aprobación); analizar el archivo JSON de Snyk para la auditoría de seguridad del código; consolidar el Informe Preliminar e Informe Final.

---

## 4. CRONOGRAMA DETALLADO DE ACTIVIDADES Y AGENDA DE AUDITORÍA

A continuación se detalla la planificación operativa distribuida en las 10 semanas de duración del proyecto (01 de julio de 2026 al 09 de septiembre de 2026):

| Cód. | Fase / Tarea Operativa | Fecha Inicio | Fecha Fin | Responsable Directo | Evidencia / Entregable Asociado |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **F1.1** | Configuración de criterios, objetivos y lineamientos base. | 01/07/2026 | 02/07/2026 | Equipo Completo | Acta de inicio / Project Charter |
| **F1.2** | Diseño y adaptación de la Lista de Verificación (Checklist SDLC). | 03/07/2026 | 08/07/2026 | R. Dan Mayhuire | Checklist SDLC en formato Word |
| **F1.3** | Consolidación y firma del Plan de Auditoría formal. | 09/07/2026 | 14/07/2026 | R. Cari Mamani | **Entregable 2: Plan de Auditoría** |
| **F2.1** | **Entrevista Técnica N°1:** Gestión de Requisitos y Ceremonias Ágiles en Jira. | 15/07/2026 | 18/07/2026 | R. Dan Mayhuire | Minuta de entrevista / Log Jira |
| **F2.2** | **Entrevista Técnica N°2:** Ingeniería de Calidad y Pruebas Unitarias. | 21/07/2026 | 25/07/2026 | P. Paricahua | Registro de entrevistas de QA |
| **F2.3** | Extracción y descodificación de reportes Word/Excel del `.jar` de SonarCloud. | 28/07/2026 | 31/07/2026 | P. Paricahua | Documentos de inspección SonarCloud |
| **F2.4** | Parseo y análisis de vulnerabilidades del JSON de Snyk. | 01/08/2026 | 04/08/2026 | R. Dan Mayhuire | Reporte analítico de seguridad / JSON |
| **F2.5** | Inspección técnica en sitio / remota de la arquitectura en el Servidor Privado. | 05/08/2026 | 08/08/2026 | R. Cari Mamani | **Entregable 4: Registro de Evidencias** |
| **F3.1** | Procesamiento de datos de campo y documentación de Papeles de Trabajo. | 11/08/2026 | 14/08/2026 | Equipo Completo | **Entregable 5: Papeles de Trabajo** |
| **F3.2** | Estructuración cualitativa de desvíos y brechas detectadas. | 15/08/2026 | 18/08/2026 | P. Paricahua | **Entregable 6: Matriz de Hallazgos** |
| **F3.3** | Mapeo y cálculo probabilístico de riesgos del sistema. | 19/08/2026 | 21/08/2026 | P. Paricahua | **Entregable 7: Matriz de Riesgos** |
| **F3.4** | Redacción y revisión interna del borrador técnico de la auditoría. | 22/08/2026 | 25/08/2026 | R. Dan Mayhuire | **Entregable 8: Informe Preliminar** |
| **F3.5** | Emisión final y firma del Dictamen de Auditoría de RamisToolX. | 26/08/2026 | 28/08/2026 | Equipo Completo | **Entregable 9: Informe Final** |
| **F4.1** | Diseño de estrategias de remediación de bugs y deudas técnicas. | 29/08/2026 | 02/09/2026 | Startup Orbit | **Entregable 10: Plan de Acción Correctiva** |
| **F4.2** | Cierre formal del proceso, firmas y archivo definitivo de artefactos. | 03/09/2026 | 09/09/2026 | R. Cari Mamani | **Entregable 11: Acta de Cierre** |

---

## 5. PROCEDIMIENTOS DETALLADOS DE AUDITORÍA

### PROCEDIMIENTO A: Auditoría de Gestión de Requisitos y Trazabilidad (Scrum)
* **Objetivo:** Garantizar que el sistema RamisToolX responda fielmente a las necesidades del negocio.
* **Paso 1:** Acceder al tablero Kanban/Scrum de Jira de la Startup Orbit.
* **Paso 2:** Seleccionar una muestra aleatoria del 30% de las Historias de Usuario etiquetadas como "Done" (Finalizadas).
* **Paso 3:** Verificar que cada funcionalidad cuente con criterios de aceptación explícitos en lenguaje Gherkin o formato estándar.
* **Paso 4:** Cruzar el ID de la Historia de Jira con el identificador del Pull Request en GitHub.
* **Paso 5:** Corroborar la firma o marcas de validación de al menos 2 integrantes del equipo en la bitácora del repositorio.

### PROCEDIMIENTO B: Auditoría de Calidad de Código y Mantenibilidad (CMMI-DEV VER / SonarCloud)
* **Objetivo:** Validar la solidez estructural del código y la veracidad de las métricas de prueba.
* **Paso 1:** Ejecutar la herramienta empaquetada en el archivo `.jar` de SonarCloud configurada para el entorno local/académico.
* **Paso 2:** Exportar los resultados consolidados de análisis estático en formatos Word y Excel generados de manera nativa por la utilidad.
* **Paso 3:** Verificar en las hojas de datos que la métrica de **cobertura de código alcance el 89%**, inspeccionando qué bloques lógicos de FastAPI o Flutter se encuentran excluidos del pipeline.
* **Paso 4:** Analizar el índice de deuda técnica detectado en el reporte de Excel, prestando especial atención a la presencia de Code Smells (código sucio) en los controladores de la base de datos.

### PROCEDIMIENTO C: Auditoría de Seguridad de Componentes (Snyk)
* **Objetivo:** Asegurar la API frente a brechas de seguridad y librerías comprometidas.
* **Paso 1:** Localizar el archivo JSON crudo generado en el último escaneo automatizado por la herramienta Snyk sobre el archivo de dependencias (`requirements.txt` o `pubspec.yaml`).
* **Paso 2:** Examinar la estructura de datos del JSON, aislando los nodos clasificados con severidad "High" (Alta) o "Critical" (Crítica).
* **Paso 3:** Constatar si las dependencias vulnerables identificadas en el JSON han sido actualizadas o parchadas en el entorno actual del servidor.

### PROCEDIMIENTO D: Auditoría de Solución Técnica e Integración en Servidor Privado (CMMI-DEV TS / IP)
* **Objetivo:** Verificar la estabilidad de la arquitectura y la correcta persistencia de datos en producción.
* **Paso 1:** Solicitar las credenciales y rutas de acceso seguro (SSH/SFTP) al **Servidor Privado** donde se aloja el backend de FastAPI.
* **Paso 2:** Inspeccionar el archivo de configuración del servidor y las variables de entorno para corroborar el correcto aislamiento de las llaves secretas de autenticación.
* **Paso 3:** Evaluar el módulo de generación de actas en PDF, comprobando mediante pruebas de inserción que los archivos se escriban en rutas absolutas controladas y protegidas contra accesos externos directos.
* **Paso 4:** Simular el flujo de carga masiva de inventario mediante el procesamiento de un archivo Excel de prueba, auditando los logs de FastAPI para verificar el control de excepciones ante entradas de datos erróneas.