---
name: correccion-practica3
description: Corrige la Práctica 3 del máster. Usa esta skill siempre que el usuario quiera corregir, evaluar o puntuar una entrega de la Práctica 3, o cuando adjunte un fichero para su corrección mencionando la detección de fraude, la regresión logística, la matriz de confusión, el dataset de tarjetas de crédito o la corrección del trabajo de un alumno sobre fraude. También actívala si el usuario dice "corrígeme esto", "evalúa esta entrega" o similar en el contexto del máster y se refiere a la práctica 3.
---

# Corrección Práctica 3 — Detección de Fraude

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
- Busca el archivo más reciente con:
```bash
python3 -c "
import pdfplumber, glob, os
files = glob.glob('/sessions/epic-great-lamport/mnt/Downloads/*.pdf')
f = sorted(files, key=os.path.getmtime, reverse=True)[0]
print('Archivo:', os.path.basename(f))
with pdfplumber.open(f) as pdf:
    for i, page in enumerate(pdf.pages):
        txt = page.extract_text()
        if txt: print(f'=== PAG {i+1} ===\n{txt}')
" 2>/dev/null
```

**1d. Leer el texto y verificar las capturas (OBLIGATORIO):**

Lee la entrega con el script del proyecto, que extrae el texto y las capturas (ver método del
master). NO improvises la extracción a mano: los PDFs del curso usan CMap, streams sin comprimir
y capturas JPEG o bitmap RGB. Si el `.txt` sale vacío pero el PDF tiene operadores de texto, es un
fallo de extracción, no una entrega sin redacción: no penalices por ello.
```bash
python3 skills/corregir-practicas/leer-entrega.py .descargas/<alumno>.pdf .descargas/caps
```
**Lee el `.descargas/<alumno>.txt`** (interpretación escrita del alumno) y **abre cada captura con
Read**. No basta con contar cuántas hay: esta práctica exige tres capturas concretas y debes
confirmar cada una: (1) resultado del modelo de **regresión logística** en Dataiku con sus
métricas, (2) pesos/coeficientes de las variables, y (3) la **matriz de confusión con valores
numéricos reales**. Una imagen genérica o que no muestre esto no cuenta como entregada. Este
chequeo es el dato para aplicar las penalizaciones 3 y 4.

### PASO 2 — Evaluar la práctica

Con el texto completo, aplica los criterios de la rúbrica (ver sección más abajo) y determina:
- El nivel de cada criterio (No Cumple / Cumple Parcialmente / Cumple)
- El comentario para cada criterio (2-3 frases, tono cercano y directo)
- El **comentario global** (4-6 frases) — **Este paso es obligatorio y no puede omitirse.** Resume el trabajo del alumno en conjunto: qué ha hecho bien, qué le ha faltado y una recomendación de mejora. Es lo primero que el alumno verá al recibir su nota, así que dale el peso que merece.

### PASO 3 — Rellenar la rúbrica en Moodle

Vuelve a la pestaña de calificación (tab de Moodle). Abre el panel expandido de la rúbrica haciendo clic en el icono de expansión junto a "Calificación:".

**3a. Identificar los valores de los niveles:**
```javascript
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

**3b. Hacer clic en las celdas correctas:**
```javascript
const selecciones = ['VALOR_C1', 'VALOR_C2', 'VALOR_C3', 'VALOR_C4'];
selecciones.forEach(val => {
  const levels = document.querySelectorAll('.gradingform_rubric .criterion .level');
  const celda = Array.from(levels).find(l => l.querySelector('input')?.value === val);
  if (celda) celda.click();
});
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
```javascript
const comentarioGlobal = 'COMENTARIO GLOBAL AQUÍ';
if (typeof tinymce !== 'undefined') {
  const editor = tinymce.get('id_assignfeedbackcomments_editor');
  if (editor) editor.setContent(comentarioGlobal);
}
```
Verifica que el editor ha aceptado el contenido antes de continuar.

### PASO 4 — Guardar y pasar al siguiente

Pulsa **"Guardar y mostrar siguiente"** para guardar la corrección y pasar automáticamente al siguiente alumno pendiente. Si no hay más alumnos, pulsa **"Guardar cambios"** para guardar la última corrección.

---

## Contexto de la práctica

La práctica consiste en construir e interpretar un modelo de **regresión logística** para detectar fraude en transacciones financieras. El alumno trabaja en **Dataiku** con el Credit Card Fraud Detection Dataset.

**Dataset clave**: 284.807 transacciones de tarjetas de crédito europeas. Solo 492 son fraude → **0,172% de fraudes** (problema altamente desbalanceado).

Las variables son anónimas (V1-V28, resultado de PCA) más `Time`, `Amount` y `Class` (0=normal, 1=fraude).

El alumno debe entregar:
1. **Resultado del modelo** de regresión logística — captura de pantalla
2. **Peso de las variables** (feature importance / coeficientes) — captura de pantalla
3. **Matriz de confusión** — captura de pantalla con valores reales

---

## Penalizaciones automáticas (aplicar ANTES de puntuar)

1. **Fichero Word (.doc / .docx)**: Sé duro. No es el formato adecuado. Penaliza DOCUMENTACIÓN Y ORGANIZACIÓN (máximo "Cumple Parcialmente") y menciónalo explícitamente.

2. **No usa regresión logística**: Si el alumno usa otro modelo (árbol, SVM, etc.) sin justificarlo, penaliza COMPRENSIÓN TÉCNICA y APLICACIÓN PRÁCTICA (máximo "Cumple Parcialmente" en ambos).

3. **Falta la matriz de confusión (o no es coherente)**: Es un entregable explícito del enunciado. Tras el PASO 1d (extraer y MIRAR las imágenes), confirma visualmente que hay una captura que muestra realmente la **matriz de confusión con valores numéricos**. Si no está, o la imagen no se corresponde con eso, penaliza APLICACIÓN PRÁCTICA y DOCUMENTACIÓN Y ORGANIZACIÓN.

4. **Falta el peso de variables (o no es coherente)**: Entregable obligatorio. Confirma visualmente (PASO 1d) que hay una captura que muestra los **pesos/coeficientes de las variables**. Si no está, o la imagen no se corresponde con eso, penaliza APLICACIÓN PRÁCTICA.

5. **No menciona el desbalanceo de clases**: El 0,172% de fraudes es el elemento más característico del dataset. No mencionarlo indica falta de comprensión básica del problema. Penaliza COMPRENSIÓN TÉCNICA y RESOLUCIÓN DE PROBLEMAS.

---

## Criterios de Evaluación

### 1. COMPRENSIÓN TÉCNICA

Aspectos a valorar:
- Entiende por qué se usa regresión logística (no lineal) para predecir probabilidades de eventos binarios.
- Identifica y menciona el fuerte desbalanceo de clases (0,172% de fraudes) y su impacto en la evaluación.
- Sabe interpretar la matriz de confusión: TP (fraudes detectados), FP (falsas alarmas), TN (operaciones normales correctas), FN (fraudes no detectados).
- Comprende por qué el accuracy solo no es suficiente en datasets desbalanceados y menciona métricas alternativas (precision, recall, AUC-ROC).

| Nivel | Puntuación |
|---|---|
| No Cumple | 0 puntos |
| Cumple Parcialmente | 1 punto |
| Cumple | 2 puntos |

### 2. APLICACIÓN PRÁCTICA

Aspectos a valorar:
- Ajusta correctamente un modelo de regresión logística en Dataiku.
- Muestra los pesos/coeficientes de las variables con una captura de pantalla.
- Incluye la matriz de confusión con los valores numéricos reales.
- Incluye una captura del resumen del modelo con métricas de evaluación.

| Nivel | Puntuación |
|---|---|
| No Cumple | 0 puntos |
| Cumple Parcialmente | 1,5 puntos |
| Cumple | 3 puntos |

### 3. DOCUMENTACIÓN Y ORGANIZACIÓN

Aspectos a valorar:
- Incluye las tres capturas de pantalla solicitadas: resultado del modelo, pesos de variables, matriz de confusión.
- El texto es claro y organizado.
- No entrega en formato Word.

| Nivel | Puntuación |
|---|---|
| No Cumple | 0 puntos |
| Cumple Parcialmente | 1 punto |
| Cumple | 2 puntos |

### 4. RESOLUCIÓN DE PROBLEMAS

Aspectos a valorar:
- Identifica qué variables tienen más peso en la predicción del fraude y lo comenta.
- Interpreta la matriz de confusión en contexto financiero: en detección de fraude, los FN (fraudes no detectados) son mucho más costosos que los FP (falsas alarmas).
- Comenta sobre el desbalanceo de clases y su efecto en los resultados.
- Reflexiona sobre limitaciones del modelo o propone mejoras (oversampling, ajuste de threshold, etc.).

| Nivel | Puntuación |
|---|---|
| No Cumple | 0 puntos |
| Cumple Parcialmente | 1,5 puntos |
| Cumple | 3 puntos |

**Puntuación máxima total: 10 puntos**

---

## Tono de los comentarios

Los comentarios deben ser **cercanos pero profesionales**: habla directamente al alumno de tú. Reconoce lo que ha hecho bien antes de señalar lo que falta. Evita el lenguaje impersonal ("el alumno demuestra...") y usa el directo ("has demostrado...", "te ha faltado...", "se nota que...").

Ejemplos de tono correcto:
- ✅ "Has construido bien el modelo y la matriz de confusión está clara, pero te ha faltado reflexionar sobre el impacto del desbalanceo de clases en los resultados."
- ✅ "Se nota que entiendes la diferencia entre precisión y recall, y eso es lo más importante en este tipo de problemas."
- ❌ "El alumno demuestra comprensión parcial del concepto."

---

## Formato de respuesta (resumen para el usuario)

Después de rellenar Moodle, muestra siempre este resumen en el chat:

---

### 📋 CORRECCIÓN PRÁCTICA 3 — [Nombre del alumno]

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
