# Entregable N° 3: Lista de Verificación SDLC (Audit Checklist)

**SISTEMA:** RamisToolX  
**ORGANIZACIÓN:** Startup Orbit  
**CÓDIGO DEL DOCUMENTO:** AUD-SDLC-RAMISTOOLX-2026-001-CHK  
**FECHA DE EMISIÓN:** 03 de julio de 2026  

La siguiente lista de verificación se basa en el *System Development Life Cycle Audit Checklist* estándar. Constituye el instrumento operativo de recolección de evidencia para cada objetivo de auditoría, validando la institucionalización de Scrum, CMMI-DEV v1.3 y las herramientas de integración continua.

---

| Código | Objetivo / Item de Verificación | Cumple | No Cumple | Observaciones (Evidencia Técnica RamisToolX) |
| :---: | :--- | :---: | :---: | :--- |
|  | | **METODOLOGÍA SDLC**| | |
| CL-01-01 | ¿Se han determinado el alcance de las responsabilidades de la dirección, auditoría interna, usuarios, QA y procesamiento de datos durante el diseño, desarrollo y mantenimiento del sistema? | ✅ | - | Roles definidos formalmente en la sección 3 del Plan de Auditoría (Especialista QA, Infra y Requisitos). |
| CL-01-02 | ¿Los workpapers del SDLC evidencian que se obtuvieron los niveles de autorización apropiados para cada fase? | ✅ | - | Evidenciado mediante la obligatoriedad de 2 *Peer Reviews* aprobatorios en GitHub antes de cada *Merge*. |
| CL-01-03 | ¿Existe una metodología formal de desarrollo implantada y soportada por herramientas CASE? | ✅ | - | Se utiliza Jira Software para orquestar los Sprints bajo el marco Scrum y CMMI-DEV (TS, VER, IP). |
| CL-01-04 | ¿El proyecto tiene un plan formal de proyecto documentado? | ✅ | - | Sustentado en el "Project Charter" y el "Plan de Auditoría SDLC" aprobados. |
| CL-01-05 | ¿El proyecto tiene definición de alcance y marco formal? | ✅ | - | Alcance estrictamente delimitado a la arquitectura Cliente-Servidor y áreas TS, VER e IP. |
| CL-01-06 | ¿Están especificados los entregables principales, plazos y roles/responsabilidades? | ✅ | - | Cronograma de 10 semanas detallado en el entregable F1.3 del plan. |
| CL-01-07 | ¿Se realiza análisis de riesgos del proyecto? | ✅ | - | Matriz de Riesgos documentada (Sección 15 del Charter) evaluando integraciones y cobertura. |
| CL-01-08 | ¿Se están siguiendo los procedimientos definidos para el área de desarrollo? | ✅ | - | Trazabilidad asegurada mediante GitHub Flow y Quality Gates en SonarCloud. |
|  | | **ANÁLISIS DE NECESIDADES**| | |
| CL-02-01 | ¿Existen procedimientos formales para realizar el análisis de necesidades? | ✅ | - | Levantamiento de requerimientos gestionado mediante el Product Backlog en Jira. |
| CL-02-02 | ¿El análisis de necesidades de un proyecto reciente cumple con los estándares establecidos? | ✅ | - | El módulo de inventario y actas PDF cumple con los criterios operativos de RAMIS S.A.C. |
| CL-02-03 | ¿Existe un mecanismo para registrar necesidades de desarrollo con descripción, riesgos y análisis coste/beneficio? | ✅ | - | Uso de "Issues" en Jira parametrizados por Puntos de Historia y Prioridad. |
| CL-02-04 | ¿Qué tipo de especificaciones de requisitos se están empleando? | ✅ | - | Historias de usuario estándar con criterios de aceptación explícitos. |
| CL-02-05 | ¿Dónde se almacenan los requisitos? ¿Se usa una herramienta estándar? | ✅ | - | Repositorio centralizado en la nube mediante los tableros Kanban/Scrum de Jira. |
| CL-02-06 | ¿Existe un proceso de revisión de requisitos? | ✅ | - | Revisión continua mediante ceremonias ágiles (Sprint Planning y Refinement). |
| CL-02-07 | ¿Se gestiona la trazabilidad de requisitos? | ✅ | - | Enlace directo validado entre IDs de Historias de Jira y títulos de Pull Requests en GitHub. |
| | |**DISEÑO Y DESARROLLO** | | |
| CL-03-01 | ¿Se han revisado las especificaciones de diseño y hay evidencia escrita de aprobación? | ✅ | - | Aprobación arquitectónica de micro-endpoints en FastAPI validada por el Tech Lead. |
| CL-03-02 | ¿Las especificaciones de diseño cumplen con los estándares? | ✅ | - | Diseño basado en separación de capas (Routers, Services, Repositories). |
| CL-03-03 | ¿Se incorporan pista de auditoría y controles programados en las especificaciones de diseño? | ✅ | - | Control de autenticación mediante JWT (Argon2) y protección de endpoints documentado. |
| CL-03-04 | ¿Los documentos fuente para entrada de datos están diseñados para facilitar la captura precisa? | ✅ | - | Validación estricta de esquemas de entrada y salida mediante *Pydantic* en Python. |
| CL-03-05 | ¿Los programas cumplen con los estándares de programación del área? | ✅ | - | Calidad avalada mediante análisis estático; cero vulnerabilidades críticas reportadas en Snyk. |
| CL-03-06 | ¿Existen estándares documentados de codificación en una wiki colaborativa? | ✅ | - | Manuales y estándares publicados en la plataforma interactiva MkDocs. |
| CL-03-07 | ¿El equipo trabaja con un diseñador desde el inicio del proyecto? | ✅ | - | Interfaz móvil conceptualizada desde el Sprint 1 utilizando el framework Flutter. |
| CL-03-08 | ¿Se utiliza un sistema de control de versiones conforme a las mejores prácticas? | ✅ | - | Uso riguroso de Git/GitHub bajo estrategia de ramas cortas y protección de la rama `main`. |
| CL-03-09 | ¿Existe integración continua / despliegue continuo (CI/CD)? | ✅ | - | Ejecución automatizada de Pytest y SonarCloud previa a integraciones. |
| | |**PROCEDIMIENTOS DE PRUEBA** | | |
| CL-04-01 | ¿Existen procedimientos documentados de prueba de sistemas y programas? | ✅ | - | Scripts de testeo implementados en la carpeta `/test` del backend de FastAPI. |
| CL-04-02 | ¿Los procedimientos de prueba, datos de prueba y resultados son comprensivos y siguen los estándares? | ✅ | - | Se reporta y valida una cobertura de código (Code Coverage) de entre 82% y 89%. |
| CL-04-03 | ¿Son adecuadas las pruebas realizadas sobre las fases manuales de la aplicación? | ✅ | - | Simulación controlada de carga masiva de inventario mediante archivos Excel. |
| CL-04-04 | ¿Existe una estrategia de pruebas documentada? | ✅ | - | Alineada directamente con las prácticas específicas del área Verificación (VER) de CMMI. |
| CL-04-05 | ¿Hay proceso de revisión de calidad y métricas de software? | ✅ | - | Exportación y análisis de reportes de deuda técnica y *Code Smells* desde SonarQube. |
| CL-04-06 | ¿Se gestiona la integración de software y la documentación de pruebas? | ✅ | - | Logs de Pytest y resultados de *Quality Gates* adjuntos en los anexos técnicos. |
| CL-04-07 | ¿Existe un sistema de gestión de defectos? | ✅ | - | Clasificación de tareas tipo "Bug" o "Fix" dentro del ciclo de Sprints en Jira. |
| CL-04-08 | ¿Cómo funciona el proceso de revisión de código? | ✅ | - | Regla en GitHub: Ningún desarrollador puede fusionar su propio PR sin el "Approve" de los otros 2 miembros. |
| | | **PROCEDIMIENTOS DE IMPLEMENTACIÓN**| | |
| CL-05-01 | ¿Existen procedimientos formales de promoción e implementación de programas? | ✅ | - | Empaquetado y migración gestionado bajo el área Integración del Producto (IP) de CMMI. |
| CL-05-02 | ¿La documentación del procedimiento de promoción muestra que los estándares se siguen? | ✅ | - | Scripts de configuración de Termux y clonación de repositorio listos para ejecución. |
| CL-05-03 | ¿Los cambios seleccionados tienen registros de soporte que evidencian aprobación adecuada? | ✅ | - | Trazabilidad del código validado hacia la infraestructura de producción local. |
| CL-05-04 | ¿La documentación de la implementación de nuevas aplicaciones muestra que se siguieron los procedimientos? | ✅ | - | Configuración de almacenamiento validada (`termux-setup-storage`) para manejo de rutas absolutas de actas PDF. |
| CL-05-05 | ¿Existe un proceso de gestión de cambios con autorización formal? | ✅ | - | Autorización liderada por el Tech Lead de Startup Orbit previo al release. |
| CL-05-06 | ¿Cómo funciona el workflow configurado para el despliegue? | ✅ | - | Despliegue en servidor móvil/privado local, garantizando aislamiento de la red. |
| | | **REVISIÓN POST-IMPLEMENTACIÓN** | | |
| CL-06-01 | ¿Existen procedimientos formales de revisión post-implementación? | ✅ | - | Ejecución de *Smoke Tests* conectándose a la URL de Swagger desde la red WiFi local. |
| CL-06-02 | ¿Las modificaciones de programas, procedimientos de prueba y documentación de soporte siguen los estándares? | ✅ | - | Los parches post-despliegue requieren pasar nuevamente por todo el flujo de Pytest. |
| CL-06-03 | ¿Se documentan y gestionan las lecciones aprendidas? | ✅ | - | Registradas durante las ceremonias de "Sprint Retrospective" del equipo. |
| CL-06-04 | ¿Se realiza seguimiento de los objetivos del sistema tras la implementación? | ✅ | - | Validación de la inmutabilidad de los comprobantes PDF almacenados. |
| | | **MANTENIMIENTO DE APLICACIONES** | | |
| CL-07-01 | ¿Existen procedimientos formales de mantenimiento de aplicaciones? | ✅ | - | Resolución planificada de dependencias obsoletas marcadas por Snyk. |
| CL-07-02 | ¿Las modificaciones de programas, pruebas y documentación siguen los estándares? | ✅ | - | Todo cambio genera una actualización automática en Swagger. |
| CL-07-03 | ¿Se gestiona el mantenimiento evolutivo y correctivo de manera diferenciada? | ✅ | - | Diferenciación clara entre "Historias de Usuario" (Evolutivo) y "Defectos" (Correctivo). |
| CL-07-04 | ¿Existe un catálogo de componentes software reutilizables accesible y actualizado? | ✅ | - | Inyección de dependencias modularizada (Ej. Sesión de Base de Datos, utilidades PDF). |
| | | **CONTROL SOBRE SOFTWARE DE SISTEMA** | | |
| CL-08-01 | ¿Existen procedimientos formales de modificación de software de sistema? | ✅ | - | Archivo `.env` estrictamente excluido del repositorio para aislar credenciales. |
| CL-08-02 | ¿Las modificaciones de software de sistema tienen pruebas y documentación de soporte siguiendo los estándares? | ✅ | - | Dependencias fijadas y testeadas en el archivo `requirements.txt` de Python. |
| CL-08-03 | ¿Existe documentación del software de sistema desarrollado internamente y de las características del software propietario? | ✅ | - | Se especifica el uso de librerías open-source (FastAPI, Pytest, SQLAlchemy). |
| CL-08-04 | ¿Los lenguajes, compiladores y herramientas CASE han sido previamente homologados? | ✅ | - | Estándar unificado de Python para Backend y Dart para Frontend. |
| | | **ESTÁNDARES DE DOCUMENTACIÓN** | | |
| CL-09-01 | ¿Los estándares de documentación son completos y cubren todos los artefactos del SDLC? | ✅ | - | Todo el ecosistema SDLC documentado y desplegado de forma interactiva en MkDocs. |
| CL-09-02 | ¿Existe un estándar general para documentación técnica? | ✅ | - | Swagger/OpenAPI activo para documentar *schemas*, cabeceras y *status codes* de FastAPI. |
| CL-09-03 | ¿Existe un estándar para manuales de usuario y procedimientos de operación? | ✅ | - | Entregables formateados en Markdown detallando el flujo de auditoría y despliegue. |
| CL-09-04 | ¿Los estándares son conocidos y respetados en el área? | ✅ | - | El equipo Startup Orbit adhiere a las prácticas CMMI y reglas de codificación SOLID. |
| CL-09-05 | ¿Las modificaciones a estándares se difunden oportunamente dentro del área? | ✅ | - | Comunicación centralizada vía repositorios y ceremonias de Daily Standup. |
| CL-09-06 | ¿La documentación permite la trazabilidad completa a lo largo del ciclo de vida? | ✅ | - | Trazabilidad end-to-step (Requisito Jira ➔ Código GitHub ➔ Prueba Pytest ➔ Deploy Termux). |s