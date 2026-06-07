---
name: correccion-practica1
description: Corrige la Práctica 1 del máster. Usa esta skill siempre que el usuario quiera corregir, evaluar o puntuar una entrega de la Práctica 1, o cuando adjunte un fichero para su corrección mencionando la práctica, el enunciado o la corrección del trabajo de un alumno. También actívala si el usuario dice "corrígeme esto", "evalúa esta entrega" o similar en el contexto del máster.
---

# Corrección Práctica 1 — Análisis de precios de Idealista

---

## FLUJO DE TRABAJO COMPLETO

Cuando estés en la pantalla de calificación de Moodle (vista del calificador con el PDF del alumno a la izquierda y la rúbrica a la derecha), sigue estos pasos **siempre en este orden**:

### PASO 1 — Descargar y leer el PDF completo

No uses el visor integrado de Moodle para leer la práctica: el visor corta el texto de los márgenes. Descarga el PDF y léelo completo con pdfplumber.

**1a. Obtener la URL del PDF:**
```javascript
// En javascript_tool (tabId de la página de calificación)
const links = Array.from(document.querySelectorAll('a'));
const pdfLink = links.find(l => l.href && l.href.includes('pluginfile'));
pdfLink ? pdfLink.href : 'no encontrado';
```

**1b. Abrir el PDF en una nueva pestaña para que se descargue:**
- Crea una nueva pestaña con `tabs_create_mcp`
- Navega a la URL del PDF **sin** el parámetro `?forcedownload=1`
- El navegador lo descargará automáticamente a la carpeta de Descargas del usuario

**1c. Leer el PDF con pdfplumber:**
- Solicita acceso a `C:\Users\Usuario\Downloads` con `request_cowork_directory` si no lo tienes
- Busca el archivo con `Glob("Caso*.pdf", path="C:\Users\Usuario\Downloads")`
- Extrae el texto completo:
```bash
pip install pdfplumber --break-system-packages -q
python3 -c "
import pdfplumber
with pdfplumber.open('/sessions/epic-great-lamport/mnt/Downloads/NOMBRE_ARCHIVO.pdf') as pdf:
    for i, page in enumerate(pdf.pages):
        print(f'=== PÁGINA {i+1} ===')
        print(page.extract_text())
"
```

### PASO 2 — Evaluar la práctica

Con el texto completo, aplica los criterios de la rúbrica (ver sección más abajo) y determina:
- El nivel de cada criterio (No Cumple / Cumple Parcialmente / Cumple)
- El comentario para cada criterio (2-3 frases, tono cercano y directo)
- El **comentario global** (4-6 frases) — **Este paso es obligatorio y no puede omitirse.** Resume el trabajo del alumno en conjunto: qué ha hecho bien, qué le ha faltado y una recomendación de mejora. Es lo primero que el alumno verá al recibir su nota, así que dale el peso que merece.

### PASO 3 — Rellenar la rúbrica en Moodle

Vuelve a la pestaña de calificación (tab de Moodle). Abre el panel expandido de la rúbrica haciendo clic en el icono de expansión junto a "Calificación:".

**3a. Identificar los valores de los niveles:**
```javascript
// En javascript_tool — obtener valores de inputs de cada criterio
const rows = document.querySelectorAll('.gradingform_rubric .criterion');
const info = [];
rows.forEach((row, i) => {
  const levels = row.querySelectorAll('.level');
  const textarea = row.querySelector('textarea');
  info.push({
    criterio: i,
    levels: Array.from(levels).map(l => ({val: l.querySelector('input')?.value})),
    textareaName: textarea?.name
  });
});
JSON.stringify(info);
```

Los criterios son siempre en este orden:
- Criterio 0 → COMPRENSIÓN TÉCNICA (No Cumple=idx0, Cumple Parcialmente=idx1, Cumple=idx2)
- Criterio 1 → APLICACIÓN PRÁCTICA
- Criterio 2 → DOCUMENTACIÓN Y ORGANIZACIÓN
- Criterio 3 → RESOLUCIÓN DE PROBLEMAS

**3b. Hacer clic en las celdas correctas (las TDs tienen onclick):**
```javascript
// Sustituir los valores concretos por los obtenidos en el paso anterior
const selecciones = ['VALOR_C1', 'VALOR_C2', 'VALOR_C3', 'VALOR_C4'];
selecciones.forEach(val => {
  const levels = document.querySelectorAll('.gradingform_rubric .criterion .level');
  const celda = Array.from(levels).find(l => l.querySelector('input')?.value === val);
  if (celda) celda.click();
});

// Verificar que tienen clase 'checked'
const levels = document.querySelectorAll('.gradingform_rubric .criterion .level');
Array.from(levels).filter(l => selecciones.includes(l.querySelector('input')?.value))
  .map(l => ({val: l.querySelector('input')?.value, classes: l.className}));
```

**3c. Rellenar los comentarios de cada criterio:**
```javascript
const comentarios = {
  'advancedgrading[criteria][XXXX][remark]': 'COMENTARIO C1',
  'advancedgrading[criteria][YYYY][remark]': 'COMENTARIO C2',
  'advancedgrading[criteria][ZZZZ][remark]': 'COMENTARIO C3',
  'advancedgrading[criteria][WWWW][remark]': 'COMENTARIO C4'
};
Object.entries(comentarios).forEach(([name, texto]) => {
  const ta = document.querySelector(`textarea[name="${name}"]`);
  if (ta) {
    ta.value = texto;
    ta.dispatchEvent(new Event('input', {bubbles: true}));
    ta.dispatchEvent(new Event('change', {bubbles: true}));
  }
});
```
Los nombres de los textarea los obtienes en el paso 3a (campo `textareaName`).

**3d. Rellenar el comentario global (TinyMCE) — OBLIGATORIO:**

Este campo es el comentario general de feedback que el alumno recibe junto con su nota. Siempre debe rellenarse; no termines el proceso de corrección sin haberlo completado.

```javascript
const comentarioGlobal = 'COMENTARIO GLOBAL AQUÍ';
if (typeof tinymce !== 'undefined') {
  const editor = tinymce.get('id_assignfeedbackcomments_editor');
  if (editor) editor.setContent(comentarioGlobal);
}
```

Verifica que el editor ha aceptado el contenido antes de continuar (el campo TinyMCE debe mostrar el texto).

### PASO 4 — Guardar y pasar al siguiente

Pulsa **"Guardar y mostrar siguiente"** para guardar la corrección y pasar automáticamente al siguiente alumno pendiente. Si no hay más alumnos, pulsa **"Guardar cambios"** para guardar la última corrección.

---

## Contexto de la práctica

La práctica consiste en un análisis del mercado inmobiliario de Madrid usando un dataset de Idealista. El alumno trabaja en **Dataiku** y debe completar estas secciones en orden:

1. **Carga y exploración del dataset** en Dataiku — descripción de variables, foco en `price` y `sqft`.
2. **Análisis ANOVA** — relación entre `price` y `sqft`, interpretación de resultados.
3. **Regresión lineal simple** — `sqft` → `price`, con captura de pantalla del modelo en Dataiku.
4. **Mejora del modelo tras limpieza** — justificación, limpieza de outliers, nuevo modelo, comparación y captura.
5. **Regresión lineal múltiple** — añadir variables numéricas y categóricas, análisis de coeficientes/R²/significancia, captura.
6. **Resumen y conclusiones** — responder a las preguntas guía del enunciado.

El modelo estadístico exigido es **OLS (Ordinary Least Squares / Mínimos Cuadrados Ordinarios)**, que es el método de regresión lineal estándar de Dataiku.

---

## Penalizaciones automáticas (aplicar ANTES de puntuar)

1. **Fichero Word (.doc / .docx)**: Sé duro. No es el formato adecuado para una práctica de análisis de datos. Penaliza DOCUMENTACIÓN Y ORGANIZACIÓN (máximo "Cumple Parcialmente") y menciónalo explícitamente en el comentario final. El sesgo debe ser hacia el suspenso.

2. **No usa OLS**: Si el alumno usa otro método de regresión sin justificarlo (e.g., árbol de decisión, regresión ridge sin motivo aparente), penaliza en COMPRENSIÓN TÉCNICA y APLICACIÓN PRÁCTICA (máximo "Cumple Parcialmente" en ambos).

3. **No sigue la estructura del enunciado**: Si faltan secciones o el orden es muy diferente, penaliza en DOCUMENTACIÓN Y ORGANIZACIÓN (máximo "Cumple Parcialmente").

4. **Faltan capturas de pantalla**: El enunciado exige capturas de los modelos en Dataiku. Si faltan, penaliza en DOCUMENTACIÓN Y ORGANIZACIÓN.

---

## Criterios de Evaluación

### 1. COMPRENSIÓN TÉCNICA
El estudiante demuestra comprensión de los conceptos técnicos relevantes y su aplicación en el caso práctico.

Aspectos a valorar:
- Entiende qué mide ANOVA y cómo interpretar el p-valor.
- Sabe interpretar los coeficientes de regresión, el R² y la significancia estadística.
- Comprende la diferencia entre regresión simple y múltiple.
- Sabe por qué limpiar datos mejora el modelo.

| Nivel | Puntuación |
|---|---|
| No Cumple | 0 puntos |
| Cumple Parcialmente | 1 punto |
| Cumple | 2 puntos |

### 2. APLICACIÓN PRÁCTICA
El estudiante demuestra la capacidad de aplicar los conceptos técnicos aprendidos en situaciones prácticas del mundo real.

Aspectos a valorar:
- Carga correctamente el dataset y explora las variables relevantes.
- Ejecuta correctamente ANOVA, regresión simple, limpieza y regresión múltiple en Dataiku.
- Las capturas de pantalla muestran resultados reales del modelo.
- Selecciona variables relevantes para la regresión múltiple.

| Nivel | Puntuación |
|---|---|
| No Cumple | 0 puntos |
| Cumple Parcialmente | 1,5 puntos |
| Cumple | 3 puntos |

### 3. DOCUMENTACIÓN Y ORGANIZACIÓN
El estudiante presenta la respuesta de manera clara, organizada y correctamente documentada.

Aspectos a valorar:
- Sigue la estructura de las 5 secciones del enunciado.
- Incluye todas las capturas de pantalla solicitadas.
- El texto es claro, bien redactado y organizado.
- No entrega en formato Word.

| Nivel | Puntuación |
|---|---|
| No Cumple | 0 puntos |
| Cumple Parcialmente | 1 punto |
| Cumple | 2 puntos |

### 4. RESOLUCIÓN DE PROBLEMAS
El estudiante demuestra habilidades para identificar, analizar y resolver problemas técnicos de manera eficaz.

Aspectos a valorar:
- Identifica correctamente si la relación precio-sqft es significativa (ANOVA).
- Justifica y aplica una limpieza de datos coherente (outliers en `price` o `sqft`).
- Compara los modelos antes y después de la limpieza de forma crítica.
- Las conclusiones responden a las preguntas del enunciado y son coherentes con los resultados.

| Nivel | Puntuación |
|---|---|
| No Cumple | 0 puntos |
| Cumple Parcialmente | 1,5 puntos |
| Cumple | 3 puntos |

**Puntuación máxima total: 10 puntos**

---

## Tono de los comentarios

Los comentarios deben ser **cercanos pero profesionales**: habla directamente al alumno de tú, como lo haría un profesor que se preocupa por su progreso. Reconoce lo que ha hecho bien antes de señalar lo que falta. Evita el lenguaje impersonal ("el alumno demuestra...") y usa el directo ("has demostrado...", "te ha faltado...", "se nota que..."). El tono es el de un feedback constructivo, no el de un informe burocrático.

Ejemplos de tono correcto:
- ✅ "Se nota que has entendido bien la lógica del ANOVA, aunque te han faltado los valores numéricos para apoyar esa interpretación."
- ✅ "Has hecho un buen trabajo con la limpieza de datos, pero necesitabas incluir la captura del modelo resultante."
- ❌ "El alumno demuestra comprensión parcial del concepto."

---

## Formato de respuesta (resumen para el usuario)

Después de rellenar Moodle, muestra siempre este resumen en el chat:

---

### 📋 CORRECCIÓN PRÁCTICA 1 — [Nombre del alumno]

**Formato de entrega:** [tipo de fichero + penalización si aplica]

---

#### 1. COMPRENSIÓN TÉCNICA
- **Nivel:** [No Cumple / Cumple Parcialmente / Cumple]
- **Puntuación:** [0 / 1 / 2] puntos
- **Comentario:** [texto introducido en Moodle]

#### 2. APLICACIÓN PRÁCTICA
- **Nivel:** [No Cumple / Cumple Parcialmente / Cumple]
- **Puntuación:** [0 / 1,5 / 3] puntos
- **Comentario:** [texto introducido en Moodle]

#### 3. DOCUMENTACIÓN Y ORGANIZACIÓN
- **Nivel:** [No Cumple / Cumple Parcialmente / Cumple]
- **Puntuación:** [0 / 1 / 2] puntos
- **Comentario:** [texto introducido en Moodle]

#### 4. RESOLUCIÓN DE PROBLEMAS
- **Nivel:** [No Cumple / Cumple Parcialmente / Cumple]
- **Puntuación:** [0 / 1,5 / 3] puntos
- **Comentario:** [texto introducido en Moodle]

---

#### 🧮 PUNTUACIÓN TOTAL: [X] / 10

#### 💬 COMENTARIO GLOBAL
[texto introducido en Moodle]

---

Termina siempre mostrando el resumen de la corrección.
