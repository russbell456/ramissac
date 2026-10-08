# PLAN DE EJECUCIÓN: Análisis de Brechas (Gap Analysis) y Correcciones

Este documento detalla las discrepancias encontradas entre los requerimientos originales del cliente (extraídos de los documentos de Microsoft Forms `action_1.1.md`, `action_1.7.md` y `action_1.11.md`) y la implementación actual, y sirve como guía estricta para que el agente programador (Codex) aplique los parches necesarios.

## 1. Dropdown de Rutas y Campo Dinámico "Otras" (Ref: action_1.1.md)

**Análisis de Brecha:** 
* La lista actual en Flutter carece de la opción *"Ruta Juliaca a Arequipa (Viceversa)"* especificada en el requerimiento original.
* Aunque la opción *"Otras"* existe en el código actual, **falta la implementación de un campo de texto dinámico** (`TextFormField`) que se muestre condicionalmente cuando el usuario selecciona "Otras", para permitirle escribir la ruta específica. En este momento, si elige "Otras", ese es el string estático que se envía al backend, perdiendo el detalle real del viaje.

**Instrucciones para el Agente (Codex):**
* **Archivo a modificar:** `lib/features/transportes/presentation/widgets/registro_accion_form.dart`
* **Acciones:**
  1. Actualizar la constante `_rutas` para incluir *"Ruta Juliaca a Arequipa (Viceversa)"*.
  2. Crear un nuevo `TextEditingController` (ej. `_otraRutaController`) y no olvidar hacerle `dispose()`.
  3. En la UI, debajo del `DropdownButtonFormField` de Rutas, añadir una condición: `if (_rutaSeleccionada == "Otras")` que renderice un `TextFormField` para ingresar la ruta detallada (con validación obligatoria).
  4. En el método `_submit()`, al construir el objeto `RegistroAccionRequest`, si `_rutaSeleccionada == "Otras"`, el valor a enviar en el campo `ruta` debe ser el texto extraído del `_otraRutaController.text`.

---

## 2. Textos Exactos del Check List Flash (Ref: action_1.7.md)

**Análisis de Brecha:**
Los 11 ítems en el estado actual de Flutter están altamente resumidos (ej. "Documentos", "Linterna"). El requerimiento estipula que deben coincidir letra por letra con las descripciones detalladas para evitar ambigüedades operativas en el terreno.

**Instrucciones para el Agente (Codex):**
* **Archivo a modificar:** `lib/features/transportes/presentation/widgets/registro_accion_form.dart`
* **Acciones:**
  1. Reemplazar las llaves del mapa `_checklistFlash` con los textos literales exactos:
     * `"Documentos en vigencia (Soat, Rev.Tec., Tarjeta propiedad, licencia)"`
     * `"Linterna (deberá estar en la guantera)"`
     * `"Kits de herramientas (gata, cable pasacorriente, triangulo, alicate y desarmadores)"`
     * `"Botiquín"`
     * `"Llanta de repuesto"`
     * `"Extintor"`
     * `"Tacos"`
     * `"Conos"`
     * `"Lampa y pico"`
     * `"Kits antiderrames"`
     * `"Codificación"`
  2. Asegurarse de que el widget que renderiza estos checkboxes (`CheckboxListTile`) permita que el texto haga salto de línea (usualmente por defecto lo hace, pero validar que no esté truncado) dado que los nuevos textos son mucho más largos.

---

## 3. Campo de Observaciones y Comentarios (Ref: action_1.11.md)

**Análisis de Brecha:**
El campo **SÍ** está integrado correctamente tanto en la Base de Datos (`observaciones = Column(Text)` en `jornada_transporte.py`) como en el modelo `RegistroAccionRequest` y la UI actual (`_observacionesController`). 
La única brecha menor es a nivel de Experiencia de Usuario (UX): el texto de ayuda o hint del formulario no guía al conductor según el estándar solicitado.

**Instrucciones para el Agente (Codex):**
* **Archivo a modificar:** `lib/features/transportes/presentation/widgets/registro_accion_form.dart`
* **Acciones:**
  1. Ubicar el `TextFormField` de Observaciones.
  2. Cambiar la propiedad `helperText` (o `hintText`) de su `InputDecoration` al texto literal del requerimiento: *"Informar si hay alguna condición para revisar y/o reparar, reponer, implementar u oportunidades de mejora"*.

---

**Nota Arquitectónica (FastAPI):**
No es necesario realizar modificaciones en el backend (FastAPI) para cumplir estos puntos, ya que el campo `ruta` (String), el campo `checklist_flash` (JSON) y el campo `observaciones` (Text) ya están preparados para recibir la data dinámica corregida desde Flutter. Todo el trabajo se concentra en la capa de Presentación del Frontend.
