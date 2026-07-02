# Entregable N° 1: Project Charter de Auditoría SDLC

## Universidad Peruana Unión
### Facultad de Ingeniería y Arquitectura
**EAP Ingeniería de Sistemas - Ciclo VII** **Curso:** Ingeniería de Software II  
**Docente responsable:** Ing. Ruben Roque Sucari  

---

## Carátula del Proyecto

* **Proyecto Auditado:** RamisToolX (Sistema de Gestión de Préstamos de Equipos - RAMIS S.A.C.)
* **Nombre de la Startup:** Orbit
* **Nombre del Producto:** RamisToolX
* **Grupo:** 01
* **Equipo Auditor / Integrantes:**
    * Russbel Daniel Cari Mamani - 202310107
    * Reginaldo Dan Mayhuire Buendia - 201910784
    * Pawel Armando Paricahua Adco - 202312725
* **Lugar y Fecha:** Juliaca, junio de 2026

---

## 1. INFORMACIÓN GENERAL DEL PROYECTO

| Campo | Detalle |
| :--- | :--- |
| **Nombre del Proyecto** | Auditoría del Ciclo de Vida del Desarrollo de Software del Sistema RamisToolX |
| **Código del Proyecto** | AUD-SDLC-RAMISTOOLX-2026-001 |
| **Versión del documento** | 1.0 |
| **Fecha de elaboración** | 30 de junio de 2026 |
| **Fecha de inicio estimada** | 30 de junio de 2026 |
| **Fecha de cierre estimada** | 09 de septiembre de 2026 |
| **Patrocinador** | Universidad Peruana Unión - Facultad de Ingeniería y Arquitectura |
| **Auditor líder** | Ing. Ruben Roque Sucari |
| **Equipo auditor** | Russbel Daniel Cari Mamani, Reginaldo Dan Mayhuire Buendia, Pawel Armando Paricahua Adco |
| **Clasificación** | Confidencial - Uso interno académico |
| **Sistema auditado** | RamisToolX |
| **Organización auditada** | Startup Orbit |

---

## 2. ANTECEDENTES

### 2.1 Descripción del Sistema RamisToolX
RamisToolX es un sistema de gestión de almacén, inventario y préstamos desarrollado por la startup Orbit, concebido para automatizar los procesos lógicos y operativos de control de artículos. El sistema elimina los registros manuales que propician la pérdida de información y la falta de control, asegurando una trazabilidad total de los movimientos físicos a través de flujos transaccionales y la generación automatizada de actas de entrega firmadas en formato PDF.

### 2.2 Arquitectura y Tecnología
El sistema adopta una arquitectura Cliente-Servidor optimizada para su ejecución local y móvil:
* **Aplicación Móvil (Frontend):** Desarrollada con el framework Flutter, sirviendo de interfaz interactiva para todos los perfiles de usuario.
* **API REST (Backend):** Desarrollada en Python utilizando el framework FastAPI, la cual expone los endpoints transaccionales y cuenta con documentación técnica autogenerada vía Swagger/OpenAPI.
* **Base de Datos:** Motor relacional estructurado para la persistencia del catálogo de artículos, registros de usuarios y flujos transaccionales de préstamos.
* **Infraestructura y Despliegue:** El backend se aloja localmente mediante Ubuntu-Server, actuando como servidor central en la red local. Administra el sistema de archivos mediante rutas absolutas para garantizar la inmutabilidad y almacenamiento seguro de los comprobantes PDF.

### 2.3 Contexto de la Auditoría
La presente auditoría se origina como un ejercicio de ingeniería riguroso enfocado en evaluar si el ciclo de desarrollo (SDLC) de RamisToolX cumplió con los estándares metodológicos declarados. Se inspeccionará la adherencia al marco de trabajo **Scrum** (Jira) y al modelo de calidad **CMMI-DEV v1.3** en sus áreas de proceso de Solución Técnica (TS), Verificación (VER) e Integración del Producto (IP), junto al pipeline de aseguramiento (GitHub Flow con Peer Reviews, Pytest con cobertura del 82%, análisis estático en SonarQube y escaneos de seguridad en Snyk).

---

## 3. JUSTIFICACIÓN

### 3.1 Necesidad de la Auditoría SDLC
Los reportes históricos de entidades globales como el *Government Accounting Office (GAO)* evidencian fallas estructurales severas en proyectos de software: el 29% se paga pero nunca se entrega; el 47% se entrega pero no se usa; el 19.5% se abandona tras su despliegue; y solo el 1.5% se aprovecha exactamente como fue concebido. Ante este panorama, es indispensable auditar los procesos de ingeniería de RamisToolX para:
* Asegurar que el manejo transaccional de carga masiva (Excel), artículos y flujos de préstamos sea robusto y libre de fallas lógicas.
* Verificar la estabilidad de una arquitectura Cliente-Servidor desplegada en un entorno restrictivo local (Ubuntu-Server), mitigando problemas de concurrencia y persistencia de actas PDF.
* Evaluar si las prácticas de CMMI-DEV v1.3 se institucionalizaron de forma real en el código o si solo quedaron a nivel documental.

### 3.2 Beneficios de la Auditoría
* **Alineación de Requisitos:** Garantiza que los endpoints expuestos cubran con precisión los flujos operativos reales del almacén.
* **Institucionalización de Controles:** Valida el cumplimiento del flujo de control de versiones, como la regla protectora en GitHub que exige un mínimo de 2 aprobaciones de pares (*Peer Reviews*) antes de fusionar código a `main`.
* **Estabilización de Infraestructura:** Minimiza desbordamientos y fallas críticas en el manejo de rutas absolutas de Ubuntu-Server.
* **Línea Base de Calidad:** Proporciona un diagnóstico imparcial basado en métricas objetivas de SonarQube y Pytest.

### 3.3 Riesgos que se Pretenden Mitigar
* Inconsistencia de datos durante transacciones concurrentes de préstamos y devoluciones.
* Brechas de seguridad en la API FastAPI debidas a fallas de autenticación o exposición en Swagger.
* Falso sentido de cobertura de software si el 82% en Pytest no evalúa caminos lógicos críticos.
* Deuda técnica acumulada que comprometa la mantenibilidad y escalabilidad del backend en Python.

---

## 4. PROBLEMA U OPORTUNIDAD

### 4.1 Situación Identificada
A pesar de la implementación de herramientas modernas de desarrollo por parte de la Startup Orbit, se identifican las siguientes situaciones críticas desde la perspectiva de control:
* **Trazabilidad no verificada:** Ausencia de una validación cruzada formal que enlace las Historias de Usuario prioritarias en Jira con los Pull Requests aprobados en GitHub.
* **Falta de un Plan de Pruebas Integral:** Falta constatar si el 82% de cobertura con Pytest responde a una estrategia formal que someta a estrés los flujos excepcionales del negocio.
* **Riesgos de Despliegue Atípico:** El uso de servidores locales sobre Ubuntu-Server representa una solución ingeniosa pero propensa a pérdida de persistencia si no se auditan rigurosamente sus rutas absolutas y políticas de backup.

### 4.2 Oportunidad
La auditoría constituye una oportunidad estratégica para certificar la madurez de la ingeniería de software de la Startup Orbit, consolidando la confianza de los *stakeholders* y construyendo una línea base de software lista para producción bajo el modelo híbrido Scrum + CMMI-DEV.

---

## 5. OBJETIVO GENERAL

Ejecutar una auditoría exhaustiva y sistemática del Ciclo de Vida del Desarrollo de Software (SDLC) del sistema RamisToolX, evaluando el nivel de cumplimiento de las prácticas ágiles de Scrum, los controles de calidad integrados en el repositorio y la institucionalización de las áreas de proceso de CMMI-DEV v1.3 (Solución Técnica [TS], Verificación [VER] e Integración del Producto [IP]) aplicadas por la Startup Orbit, emitiendo un dictamen formal sobre la fiabilidad, seguridad y mantenibilidad de la solución Cliente-Servidor construida.

---

## 6. OBJETIVOS ESPECÍFICOS

* **OE-01:** Verificar la trazabilidad metodológica auditando el tablero de Jira, asegurando que las historias de usuario guíen de manera directa el desarrollo de código en GitHub.
* **OE-02:** Validar el proceso de Verificación (VER) inspeccionando los scripts automatizados de Pytest, comprobando que la suite de testeo cubra las reglas críticas de negocio.
* **OE-03:** Evaluar la calidad y seguridad estática del backend analizando los reportes históricos e indicadores técnicos generados por SonarQube y Snyk.
* **OE-04:** Comprobar la rigurosidad de las revisiones entre pares inspeccionando las bitácoras de GitHub, validando que ningún cambio se integre a la rama `main` sin un mínimo de 2 aprobaciones (*Peer Reviews*).
* **OE-05:** Auditar la Solución Técnica (TS) y la Integración del Producto (IP) verificando el correcto despliegue llocal de la API en Ubuntu-Server, su comunicación con la app en Flutter y el correcto guardado de actas PDF mediante rutas absolutas.

---

## 7. ALCANCE DE LA AUDITORÍA

La auditoría SDLC del proyecto RamisToolX abarcará las siguientes áreas y aspectos específicos:

### 7.1 Gestión del Proyecto
* Existencia y contenido del acta formal de constitución del proyecto (Project Charter).
* Planificación de Sprints, historias de usuario y Product Backlog gestionados en Jira.
* Participación del equipo en ceremonias ágiles (Scrum) y asignación de responsables.
* Mecanismos de control de cambios y revisiones a lo largo del desarrollo.
* Registro de impedimentos y problemas técnicos resueltos durante la ejecución.

### 7.2 Requisitos
* Procedimientos aplicados para el levantamiento de requerimientos de almacén e inventario.
* Existencia de un catálogo formal de historias de usuario con criterios de aceptación definidos.
* Clasificación y priorización de requisitos operativos y de transacciones.
* Trazabilidad de los requisitos iniciales hacia los endpoints construidos.
* Procedimiento de gestión de cambios en las funcionalidades del producto.

### 7.3 Diseño
* Especificación arquitectónica detallada bajo el modelo Cliente-Servidor.
* Coherencia entre los requisitos y el diseño de la API REST (FastAPI) y la App Móvil (Flutter).
* Diseño del modelo lógico y físico de la base de datos relacional.
* Documentación automatizada de las interfaces y endpoints (Swagger/OpenAPI).
* Especificación del flujo de generación y almacenamiento de actas PDF en rutas absolutas.

### 7.4 Desarrollo
* Estándares de programación aplicados en Python (backend) y Dart (frontend).
* Preparación del entorno de desarrollo local y orquestación.
* Control de versiones estructurado mediante la estrategia GitHub Flow.
* Procedimientos de revisión de código exigiendo un mínimo de dos *Peer Reviews* por *Pull Request*.
* Aplicación de buenas prácticas de ingeniería de software para asegurar un código limpio.

### 7.5 Pruebas
* Ejecución y evidencia de pruebas unitarias automatizadas implementadas con Pytest.
* Validación del cumplimiento de la métrica de cobertura de código (verificando el 82% actual).
* Análisis estático de código para la detección de *code smells* utilizando SonarQube/SonarCloud.
* Pruebas de integración para las operaciones concurrentes de inventario y autenticación.
* Gestión y corrección de los defectos o *bugs* encontrados durante la fase de verificación (VER - CMMI).

### 7.6 Implementación
* Procedimientos de instalación y configuración del entorno de servidor central alojado en Ubuntu-Server.
* Configuración de variables de entorno y parámetros de conexión a la base de datos.
* Estrategia de inicialización de datos, incluyendo la carga masiva de inventario vía Excel.
* Gestión de permisos de almacenamiento local requeridos para el correcto guardado de los comprobantes.
* Procedimientos definidos para el empaquetado y liberación (Integración del Producto - IP).

### 7.7 Mantenimiento
* Control de versiones y gestión de actualizaciones directamente en el repositorio principal de GitHub.
* Trazabilidad y registro de las modificaciones realizadas al código fuente.
* Procedimientos documentados para la resolución de incidencias post-despliegue.

### 7.8 Documentación
* Completitud de la documentación técnica de la API (esquemas y rutas autogeneradas).
* Documentación de la configuración del pipeline de integración continua (CI/CD).
* Existencia de guías técnicas claras para la preparación y arranque del entorno en Ubuntu-Server.
* Accesibilidad del código y los artefactos de diseño para todos los integrantes del equipo.

### 7.9 Seguridad
* Evaluación de los mecanismos de autenticación y validación de sesiones en el backend.
* Escaneo y mitigación de vulnerabilidades en las dependencias de software utilizando la herramienta Snyk.
* Manejo seguro de las rutas de directorios para evitar el acceso no autorizado a los archivos PDF generados.
* Verificación de la política de protección de la rama principal (`main`) contra inyecciones de código no revisadas.

### 7.10 Calidad
* Institucionalización de las áreas de proceso de CMMI-DEV v1.3 requeridas: Solución Técnica (TS), Verificación (VER) e Integración del Producto (IP).
* Fiabilidad: manejo adecuado de excepciones y validación de tipos de datos en la API.
* Mantenibilidad: control continuo de la deuda técnica reportada por las herramientas de análisis estático.
* Portabilidad: evaluación de la capacidad de despliegue del backend en entornos restringidos o móviles.

---

## 8. EXCLUSIONES

* Revisión manual línea por línea de la totalidad del código fuente (se confía en herramientas automatizadas como SonarQube y Pytest).
* Evaluación física de la infraestructura de hardware (estado o potencia de los smartphones/laptops usados).
* Análisis de procesos administrativos o contables internos de RAMIS S.A.C. no sistematizados en RamisToolX.
* Auditorías financieras, de costos operativos de la startup o estudios de Retorno de Inversión (ROI).
* Evaluación del rendimiento de la red del proveedor de Internet local.
* Evaluación de áreas de proceso de CMMI-DEV v1.3 fuera de TS, VER e IP.
* Soporte técnico y resolución de bugs operativos detectados tras el cierre de la auditoría.

---

## 9. CRITERIOS DE AUDITORÍA

La evaluación de cumplimiento técnico y metodológico se regirá por los siguientes criterios base:
* **CMMI-DEV v1.3:** Metas y prácticas específicas de las áreas de proceso Solución Técnica (TS), Verificación (VER) e Integración del Producto (IP).
* **Marco Scrum:** Estándares de gestión ágil (historias de usuario con criterios de aceptación claros y Sprints cerrados en Jira).
* **ISO/IEC 25010:** Atributos de calidad de software seleccionados: Adecuación Funcional, Fiabilidad, Seguridad y Mantenibilidad.
* **Métricas Internas de Calidad (Quality Gates):**
    * Cobertura de pruebas automatizadas con Pytest mayor o igual al **80%** (Línea base actual: 82%).
    * Severidad de vulnerabilidades en dependencias (Snyk) en nivel **Cero (0)** para críticas y altas.
    * Control de Deuda Técnica y *Code Smells* bajo indicadores aceptables en SonarQube.
* **Políticas del Repositorio:** Bloqueo y protección estricta de la rama `main` en GitHub, requiriendo un historial mínimo de dos (2) Peer Reviews firmados por PR.

---

## 10. METODOLOGÍA DE AUDITORÍA

El proceso se ejecutará de manera sistemática a través de cuatro (4) fases secuenciales:

+-----------------------------------+     +-----------------------------------+
| Fase 1: Preparar y Planificar     | --> | Fase 2: Trabajo de Campo          |
| - Definición de Checklist SDLC    |     | - Análisis Jira, GitHub, Pytest   |
+-----------------------------------+     +-----------------------------------+
|
v
+-----------------------------------+     +-----------------------------------+
| Fase 4: Seguimiento               | <-- | Fase 3: Evaluar y Reportar        |
| - Verificación del Plan de Acción |     | - Emisión de Informes y Hallazgos |
+-----------------------------------+     +-----------------------------------+


### Fase 1: Preparar y Planificar (Semanas 1 - 2)
* Establecer el alcance, objetivos y el Plan de Auditoría detallado.
* Diseñar y estructurar el **Checklist SDLC** adaptado a la arquitectura técnica de RamisToolX.
* Emitir la comunicación formal de apertura del proceso de auditoría a la Startup Orbit.

### Fase 2: Describir el Proceso y Trabajo de Campo (Semanas 3 - 5)
* Conducir entrevistas técnicas con los desarrolladores para levantar el flujo empírico aplicado.
* Inspeccionar los repositorios en GitHub para contrastar las políticas de revisión y ramas (GitHub Flow).
* Extraer reportes de SonarQube, Snyk y los logs detallados de Pytest para comprobar las métricas de calidad.
* Verificar en el servidor Ubuntu-Server la persistencia de datos y el comportamiento de las rutas absolutas.

### Fase 3: Evaluar y Reportar (Semanas 6 - 8)
* Contrastar la evidencia recopilada contra los Criterios de Auditoría (Fase 1).
* Elaborar la **Matriz de Hallazgos** categorizando conformidades y no conformidades.
* Redactar y discutir el Informe Preliminar con los desarrolladores para recibir descargos técnicos.
* Consolidar y emitir el **Informe Final de Auditoría** con dictámenes definitivos.

### Fase 4: Seguimiento (Semanas 9 - 10)
* Revisar el Plan de Acción Correctiva (CAP) diseñado por la Startup Orbit.
* Monitorear en el repositorio la subsanación de la deuda técnica o debilidades metodológicas halladas.
* Firmar el **Acta de Cierre de Auditoría** y archivar los papeles de trabajo de forma segura.

---

## 11. ENTREGABLES DE LA AUDITORÍA

| N. | Entregable | Descripción | Fase |
| :--- | :--- | :--- | :--- |
| 1 | **Project Charter de Auditoría** | Documento de inicio formal que define los objetivos, el alcance y los recursos de la auditoría de RamisToolX. | Planificación |
| 2 | **Plan de Auditoría SDLC** | Detalle técnico del cronograma, los criterios de evaluación y los responsables del proceso. | Fase 1 |
| 3 | **Checklist SDLC Adaptado** | Lista de verificación estructurada según los requerimientos de Scrum, FastAPI, Flutter y CMMI-DEV. | Fase 1 |
| 4 | **Registro de Evidencias Técnicas** | Compilación sistemática de capturas del tablero de Jira, reportes de Pytest, análisis de SonarQube y escaneos de Snyk. | Fase 2 |
| 5 | **Papeles de Trabajo (Bitácoras GitHub)** | Documentación del análisis de los Pull Requests, verificando la regla de las 2 aprobaciones por pares. | Fases 2 y 3 |
| 6 | **Matriz de Hallazgos** | Registro detallado de conformidades y no conformidades detectadas en el ciclo de vida del software. | Fase 3 |
| 7 | **Matriz de Riesgos del Sistema** | Identificación y valoración de riesgos técnicos derivados de los hallazgos (deuda técnica, seguridad en la API, etc.). | Fase 3 |
| 8 | **Informe Preliminar de Auditoría** | Borrador inicial con las evaluaciones de las áreas CMMI y Scrum para revisión conjunta con la Startup Orbit. | Fase 3 |
| 9 | **Informe Final de Auditoría** | Documento técnico definitivo con las conclusiones concluyentes y recomendaciones para el docente supervisor. | Fase 3 |
| 10 | **Plan de Acción Correctiva (CAP)** | Plan elaborado por el equipo para mitigar la deuda técnica, mejorar la cobertura de código o corregir desvíos. | Fase 4 |
| 11 | **Acta de Cierre de Auditoría** | Documentación formal que certifica la culminación de la auditoría del ciclo de vida de RamisToolX. | Fase 4 |

---

## 12. STAKEHOLDERS

### 12.1 Stakeholders del Proyecto de Auditoría
* **Patrocinador (UPeU):** Representado por la Facultad de Ingeniería y Arquitectura, velando por la excelencia académica y técnica.
* **Ing. Ruben Roque Sucari:** Auditor Líder y Docente Supervisor, encargado de guiar el proceso y validar la aplicación de estándares internacionales.
* **Equipo Auditor (Grupo 01):** Responsables directos de la ejecución metodológica, recolección de evidencias y redacción de informes.
* **Startup Orbit:** Organización auditada, sujeta a evaluación de procesos con el fin de robustecer sus capacidades de entrega.

### 12.2 Stakeholders del Sistema RamisToolX (Usuarios Finales)
* **Administrador del Sistema:** Administra los accesos globales y las configuraciones de seguridad de la API FastAPI.
* **Encargado de Almacén:** Gestiona el stock operativo de artículos y ejecuta la carga masiva mediante planillas Excel.
* **Operador de Préstamos:** Procesa las solicitudes de salida y retorno de equipos desde la aplicación en Flutter, emitiendo el acta PDF.
* **Prestatario / Solicitante:** Estudiante o personal que recibe el bien en préstamo y cuya identidad queda grabada en el comprobante inmutable.

---

## 13. CRONOGRAMA DE ALTO NIVEL

El cronograma detalla un horizonte temporal de 10 semanas (50 días hábiles):

* **Hito de Inicio (30/06/2026):** Aprobación del Project Charter y kick-off.
* **Fase 1 (01/07/2026 - 14/07/2026):** Elaboración de planes de trabajo y Checklist SDLC por el Equipo Auditor.
* **Fase 2 (15/07/2026 - 04/08/2026):** Revisión documental profunda (Jira, PRs de GitHub, endpoints FastAPI, suite Pytest).
* **Fase 3 (05/08/2026 - 25/08/2026):** Análisis de desvíos, redacción de Matriz de Hallazgos y entrega del Informe Final por el Auditor Líder.
* **Fase 4 (26/08/2026 - 08/09/2026):** Diseño del Plan de Acción Correctiva por Startup Orbit y validación de correcciones.
* **Hito de Cierre (09/09/2026):** Firma del Acta de Cierre y archivado documental.

---

### 14. PRESUPUESTO ESTIMADO

| Recurso / Concepto | Horas Est. | Tarifa / Hora | Subtotal |
| :--- | :--- | :--- | :--- |
| Auditor Líder | 120 h | S/ 100.00 | S/ 12,000.00 |
| Auditor de Software | 80 h | S/ 80.00 | S/ 6,400.00 |
| Especialista QA | 60 h | S/ 70.00 | S/ 4,200.00 |
| Analista de Procesos | 60 h | S/ 60.00 | S/ 3,600.00 |
| Gastos operativos y movilidad | ─ | ─ | S/ 500.00 |
| Infraestructura Cloud y Licencias (Jira, Snyk) | ─ | ─ | S/ 1,000.00 |
| Imprevistos y Materiales (5%) | ─ | ─ | S/ 1,385.00 |
| **TOTAL ESTIMADO** | **320 h** | **─** | **S/ 29,085.00** |

---

### 15. RIESGOS DEL PROYECTO DE AUDITORÍA

| ID | Riesgo | Prob. | Impacto | Nivel | Estrategia de Respuesta |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R-01** | Inconsistencia en la trazabilidad entre Jira (historias) y GitHub (código). | Alta | Alto | **Crítico** | Exigir vinculación obligatoria de IDs de historias de usuario en el título de cada Pull Request. |
| **R-02** | Falsa cobertura en pruebas automatizadas (Pytest) sobre flujos críticos. | Alta | Alto | **Crítico** | Realizar inspección de los archivos de prueba para validar aserciones robustas en lógica transaccional. |
| R-03 | Resistencia del equipo a observar hallazgos de calidad de código. | Media | Alto | **Alto** | Establecer un enfoque constructivo orientado a la mejora de notas y madurez del producto. |
| R-04 | Información desactualizada o incompleta en la documentación Swagger. | Alta | Medio | **Alto** | Ejecutar pruebas cruzadas de endpoints contra los esquemas autogenerados de la API en vivo. |
| R-05 | Modificaciones de alcance imprevistas en los flujos de almacén. | Baja | Alto | **Medio** | Congelamiento de alcance metodológico a partir de la firma de este Charter. |
| R-06 | Limitaciones de tiempo para auditar el entorno específico de Ubuntu-Server. | Media | Alto | **Alto** | Concentrar esfuerzos en el análisis de persistencia y permisos lógicos en directorios locales. |
| R-07 | Indisponibilidad de desarrolladores para entrevistas o revisiones. | Media | Medio | **Medio** | Agendar sesiones técnicas con 48 horas de anticipación mediante herramientas colaborativas. |
| R-08 | Acceso restringido al servidor en Ubuntu-Server durante el trabajo de campo. | Alta | Medio | **Alto** | Implementar simulación de red local o captura exhaustiva de logs de ejecución y endpoints. |
| R-09 | Sesgo evaluativo por proximidad académica entre los participantes. | Baja | Alto | **Medio** | Sustentar de forma estricta las conclusiones sobre métricas duras de SonarQube y Pytest. |
| R-10 | Corrupción o desorganización de los papeles de trabajo del equipo. | Baja | Alto | **Medio** | Uso de almacenamiento redundante en la nube de la institución con versionamiento semanal. |

---

### 16. FACTORES CRÍTICOS DE ÉXITO
* **Colaboración activa:** Disposición del equipo Orbit para abrir sus repositorios, tableros de Jira y compartir los logs del servidor local en Ubuntu-Server.
* **Objetividad analítica:** Apoyar los dictámenes e informes en métricas automatizadas verificables, aislando la evaluación del factor de compañerismo.
* **Competencia en el Stack:** Dominio técnico por parte de los evaluadores de las lógicas específicas de FastAPI, inyección de entornos con Pydantic y empaquetamiento móvil.
* **Alineación con CMMI:** Apego estricto a las directrices de las áreas de proceso TS, VER e IP, evitando desvíos hacia lógicas teóricas no requeridas.

---

### 17. CRITERIOS DE ACEPTACIÓN
* Se han ejecutado satisfactoriamente el 100% de las actividades descritas en las 4 fases metodológicas de la auditoría.
* Cada no conformidad o hallazgo cuenta con un papel de trabajo de soporte e identificadores de evidencia claros (ej. link a PR, logs de testeo).
* El Informe Final es revisado con la Startup Orbit y aprobado formalmente por el docente Ing. Ruben Roque Sucari.
* La Startup Orbit hace entrega de un Plan de Acción Correctiva (CAP) viable y formal para subsanar los desvíos críticos detectados.

---

### 18. SUPUESTOS
* La documentación técnica provista por el equipo de desarrollo es íntegra, verídica y corresponde a la versión de código desplegada.
* La Facultad mantendrá el calendario académico estable sin alteraciones en la fecha de cierre de notas.
* El entorno Ubuntu-Server y los dispositivos de prueba se mantendrán operativos durante la ejecución de las fases de campo.
* Los estándares seleccionados (ISO 25010, CMMI v1.3) cubren de forma suficiente las demandas formativas de la asignatura.

---

### 19. RESTRICCIONES
* **Temporal:** Limitación estricta al calendario del ciclo VII, requiriendo concluir todas las fases en un máximo de 10 semanas.
* **De Recursos:** El equipo auditor se autogestiona con los integrantes asignados, sin posibilidad de sumar especialistas externos.
* **Infraestructura:** En caso de caída de conectividad en la red local de Ubuntu-Server, la auditoría se limitará estrictamente al análisis estático de artefactos de software.
* **Confidencialidad:** Toda brecha de seguridad o deuda técnica hallada será tratada bajo estricta reserva y uso exclusivo del curso.

---

## 20. APROBACIONES

Facultad de Ingeniería y Arquitectura (FIA - UPeU)
Firma del Patrocinador / Dirección de Escuela
Fecha: //______

Ing. Ruben Roque Sucari
Firma del Profesor Responsable / Auditor Líder
Fecha: //______

Representante de Startup Orbit
Firma del Líder de Desarrollo / Auditado
Fecha: //______