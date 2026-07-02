# Entregable N° 6: Matriz de Hallazgos de Auditoría

**SISTEMA:** RamisToolX  
**ORGANIZACIÓN:** Startup Orbit  
**CÓDIGO DEL DOCUMENTO:** AUD-SDLC-RAMISTOOLX-2026-006-MH  
**FECHA DE EMISIÓN:** 18 de agosto de 2026  

---

## 1. ESTRUCTURA DE LA MATRIZ DE HALLAZGOS

La presente matriz consolida los desvíos, oportunidades de mejora y conformidades excepcionales identificadas durante la Fase 2 (Ejecución) de la auditoría aplicada al Ciclo de Vida de Desarrollo de Software (SDLC) de RamisToolX. Cada hallazgo se desglosa bajo el estándar de auditoría de sistemas: *Condición, Criterio, Evidencia, Impacto y Recomendación*.

---

## 2. DETALLE DE HALLAZGOS

### HALLAZGO N° 01: Superación Excepcional de la Meta de Cobertura de Código (Pytest / SonarCloud)
* **Tipo de Hallazgo:** Fortaleza / Conformidad Destacada.
* **Descripción (Condición):** Se verificó que el equipo de desarrollo Startup Orbit alcanzó un 89% de cobertura de código (Code Coverage) en el backend y frontend mediante pruebas unitarias automatizadas con Pytest, superando la meta inicial establecida del 82%.
* **Criterio:** Plan de Auditoría (AUD-SDLC-RAMISTOOLX-2026-001-PLAN) y métricas de calidad exigidas en los lineamientos del proyecto (Mínimo 82%).
* **Evidencia:** Reportes analíticos consolidados en formatos Word y Excel, extraídos mediante la ejecución del componente `.jar` de SonarCloud.
* **Impacto (Positivo):** Minimiza drásticamente la probabilidad de fallos lógicos en producción, asegurando que el 89% de los caminos de ejecución del negocio (módulos core de préstamos e inventario) estén validados automáticamente.
* **Recomendación:** Mantener la política estricta de pruebas automatizadas en el pipeline y documentar el set de pruebas de Pytest como estándar de calidad técnica para futuros proyectos de la Startup Orbit.

---

### HALLAZGO N° 02: Transición de Infraestructura y Estabilización del Entorno de Despliegue
* **Tipo de Hallazgo:** Oportunidad de Mejora Corregida.
* **Descripción (Condición):** Inicialmente se detectaron fallos críticos de inestabilidad y limitaciones físicas al intentar desplegar el backend en Termux empleando rutas absolutas para las actas en PDF. Ante esto, el equipo reorientó oportunamente el despliegue hacia un Servidor Privado, estabilizando la API REST.
* **Criterio:** Project Charter de Auditoría (Sección de Infraestructura de Despliegue) y CMMI-DEV v1.3 (Área de proceso: Integración del Producto [IP]).
* **Evidencia:** Inspección técnica por consola SSH del Servidor Privado, donde se constató el servicio FastAPI corriendo de manera continua y el almacenamiento controlado de PDFs.

**CAPTURA DE PANTALLA N° 17:** Consola SSH del Servidor Privado evidenciando el despliegue exitoso y activo de FastAPI, en sustitución del entorno Termux.
![Consola SSH Servidor Privado](../assets/nombre_imagen_17.png)

* **Impacto:** Evita la pérdida de disponibilidad del servicio RamisToolX, soluciona las restricciones de red de Termux y garantiza la persistencia segura de las actas de la Corporación Ramis SAC.
* **Recomendación:** Formalizar el Servidor Privado como el entorno oficial de producción en el manual de despliegue, eliminando permanentemente cualquier script remanente asociado a Termux.

---

### HALLAZGO N° 03: Detección y Remediación Inmediata de Vulnerabilidades en Dependencias Secundarias
* **Tipo de Hallazgo:** Debilidad Menor (Subsanada en caliente).
* **Descripción (Condición):** El análisis automatizado identificó dos (2) vulnerabilidades de severidad media/baja en librerías secundarias encargadas del procesamiento de datos de entrada dentro del entorno del backend de FastAPI.
* **Criterio:** Estándares de seguridad de software y el TOP 10 de vulnerabilidades OWASP (Componentes vulnerables y desactualizados).
* **Evidencia:** Archivo estructurado en formato JSON exportado directamente por la herramienta de escaneo de seguridad Snyk.
* **Impacto:** De no haberse mitigado, estas dependencias secundarias obsoletas habrían expuesto la API a potenciales denegaciones de servicio (DoS) o inyecciones de datos manipulados a través de las cargas masivas.
* **Recomendación:** El equipo de desarrollo actualizó con éxito las librerías mediante parches durante la auditoría. Se recomienda programar escaneos mensuales preventivos con Snyk sobre el archivo `requirements.txt` para mantener el estatus de "0 vulnerabilidades".

---

### HALLAZGO N° 04: Control de Versiones Riguroso y Trazabilidad de Requisitos (Git Flow)
* **Tipo de Hallazgo:** Conformidad / Cumplimiento Normativo.
* **Descripción (Condición):** Se constató el cumplimiento estricto del flujo de trabajo Git Flow, verificando que el 100% de las fusiones de ramas (Merges) hacia la rama principal contaron con la validación de doble firma técnica (mínimo dos revisores del equipo: Russbel, Pawel o Dan).
* **Criterio:** CMMI-DEV v1.3 (Área de proceso: Verificación [VER]) y políticas de desarrollo ágil de la Startup Orbit.
* **Evidencia:** Historial de Pull Requests aprobados en la plataforma GitHub cruzados con los identificadores de tareas finalizadas en el tablero Jira.
* **Impacto:** Garantiza la integridad del repositorio de código de RamisToolX, previniendo que modificaciones unilaterales o código sin revisar afecten la estabilidad del servidor privado.
* **Recomendación:** Mantener la configuración de protección de ramas activada en GitHub para asegurar que el mecanismo de doble aprobación técnica sea permanente e indestructible.

---

### HALLAZGO N° 05: Tolerancia a Fallos en el Módulo de Carga Masiva desde Excel
* **Tipo de Hallazgo:** Fortaleza Técnica.
* **Descripción (Condición):** El script encargado de procesar la carga por lotes de inventario mediante archivos de Microsoft Excel demostró un correcto control de excepciones al interceptar y aislar de manera segura registros corruptos o con tipos de datos erróneos, sin interrumpir el funcionamiento de FastAPI.
* **Criterio:** CMMI-DEV v1.3 (Área de proceso: Solución Técnica [TS]) y criterios de aceptación funcionales del sistema.
* **Evidencia:** Logs de depuración interceptados en tiempo real en el Servidor Privado y respuestas HTTP (Código 200 OK con resumen de omisión de errores) reflejadas en Swagger.
* **Impacto:** Asegura la continuidad operativa del sistema de la Corporación Ramis SAC, permitiendo a los usuarios administrativos subir inventarios masivos con la certeza de que un error en una celda no corromperá toda la base de datos.
* **Recomendación:** Expandir esta misma lógica de validación por excepciones a los módulos móviles de Flutter que interactúen con la edición de perfiles y registros de firmas digitales.

<br><br>

**Validación de la Matriz de Hallazgos:**

<br>

______________________________________  
**Reginaldo Dan Mayhuire Buendia** *Auditor de Gestión y Seguridad*

<br>

______________________________________  
**Pawel Armando Paricahua Adco** *Auditor de Calidad y QA*