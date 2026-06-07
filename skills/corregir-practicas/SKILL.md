---
name: corregir-practicas
description: >
  Skill maestra que corrige TODAS las prácticas pendientes del curso de IA Estratégica en Moodle.
  Usa esta skill cuando el usuario diga "corrige las prácticas pendientes", "empieza a corregir",
  "corrige los trabajos", "corrige las entregas", "ponme las notas", "hay prácticas para corregir",
  "quiero corregir" o cualquier frase que implique iniciar o continuar la corrección de entregas de
  alumnos del máster. Esta skill gestiona de forma autónoma la navegación, la detección de pendientes
  y la corrección de las tres prácticas en orden, y al final crea un borrador de Gmail con el resumen.
---

# Skill Maestra — Corregir Todas las Prácticas Pendientes

## Propósito

Orquesta todo el flujo de corrección: navega a Moodle, detecta qué prácticas tienen entregas
pendientes y las corrige en orden (Práctica 1 → 2 → 3) usando las skills específicas de cada
una. Al finalizar, crea un borrador de Gmail con el resumen de la sesión.

---

## MODO DESATENDIDO (cron / NAS)

**Activa este modo** cuando se cumpla cualquiera de estas condiciones:
- La petición incluye las palabras `desatendido`, `automático`, `modo cron` o `sin supervisión`.
- La variable de entorno `CORRECCION_DESATENDIDA=1` está presente (compruébalo con `Bash(printenv CORRECCION_DESATENDIDA)`).

En modo desatendido **no hay ningún humano delante**. Aplica estos overrides sobre el flujo normal
de las FASES 1–4. Son la diferencia entre que el cron funcione o se quede colgado esperando:

1. **Nunca pidas confirmación ni esperes input.** En cualquier punto donde el flujo normal diga
   "informa al usuario antes de continuar" o "después de que el usuario confirme", **continúa tú
   directamente**. Registra el progreso por stdout (el cron lo redirige al log) y sigue.

2. **Guardado automático de cada alumno.** Tras rellenar la rúbrica y el comentario global de un
   alumno (PASO 3 de la skill de práctica), **guarda tú sin esperar**:
   - Si quedan más pendientes → "Guardar y mostrar siguiente".
   - En el último alumno → "Guardar cambios".
   El borrador de Gmail final (FASE 4) es la verificación humana: tú corriges y guardas en Moodle,
   pero la persona revisa el resumen por la mañana antes de dar las notas por buenas.

3. **Login idempotente.** Al navegar a Moodle, primero comprueba si ya hay sesión activa
   (el perfil de Chrome `/home/framorhid/.chrome-moodle` es persistente y suele conservarla).
   Si ya estás dentro del Área Personal, **salta el login**. Solo si la sesión ha caducado
   (te redirige a `campus.redsummaeducation.net/newspring/login`) ejecuta la FASE 1.1.

4. **Sin pendientes = éxito, no error.** Si la FASE 2 detecta que ninguna práctica tiene entregas
   pendientes, registra `Sin pendientes — nada que corregir` por stdout y **termina limpiamente**.
   No crees borrador de Gmail. No es un fallo.

5. **Errores fatales → registra y termina.** Nunca te quedes esperando. Concretamente:
   - Login falla 2 veces → registra `ERROR: login fallido` y termina.
   - Moodle no carga / Chrome no responde en `:9222` → registra el error y termina.
   - Un PDF concreto no se puede descargar → sáltate ese alumno, regístralo y sigue con el resto.
     No abortes toda la sesión por una entrega.

6. **Lectura de PDFs en local (NO cowork) — método probado.** Las skills de práctica (PASO 1c)
   referencian un entorno antiguo: `request_cowork_directory`, `C:\Users\Usuario\Downloads`,
   `/sessions/.../mnt/Downloads`, `pdfplumber`/`pip`. **Nada de eso existe aquí.** Este entorno WSL
   **no tiene pip, ni sudo, ni librerías PDF**, y `evaluate_script` con `filePath` solo escribe
   **dentro del workspace** (`/home/framorhid/proyectos/master-regresiones`). Método que funciona:
   - **No descargues con el navegador.** Obtén el PDF con un `fetch(url, {credentials:'include'})`
     dentro de `evaluate_script` (usa la sesión autenticada y las cookies HttpOnly), conviértelo a
     base64 y vuélcalo con la opción `filePath` a una carpeta del proyecto, p. ej.
     `.descargas/<alumno>.json` (créala con `Bash(mkdir -p .../.descargas)`).
   - Decodifica el base64 a `.pdf` en Bash y **extrae el texto solo con la stdlib de Python**
     (`zlib` + `re`): descomprime cada `stream` FlateDecode y extrae los operadores `Tj`/`TJ`
     **únicamente dentro de los bloques `BT...ET`** (así evitas el ruido binario de las imágenes).
   - **Extrae y MIRA SIEMPRE las capturas antes de evaluar.** El texto que extraes NO
     incluye las imágenes, así que sácalas a disco y ábrelas con la herramienta Read. No
     basta con que existan: hay que comprobar que **muestran lo que pide el enunciado**
     (todas las prácticas penalizan tanto su ausencia como que sean incoherentes). Es un
     paso **obligatorio**, no opcional:
     ```bash
     python3 skills/corregir-practicas/extraer-capturas.py .descargas/<alumno>.pdf .descargas/caps
     ```
     El script imprime `CAPTURAS_EXTRAIDAS: N` y la ruta de cada `.jpg`. **Abre cada una con
     Read** y juzga si se corresponde con la captura exigida en esa sección (p. ej. el
     resumen real del modelo en Dataiku con sus métricas, la matriz de confusión con valores,
     los coeficientes/pesos de variables…). Pasa a la skill de práctica tanto el recuento
     como qué se ve realmente en las capturas. Aplica la penalización que indique esa skill
     cuando falten **o** cuando las imágenes no se correspondan con lo solicitado (capturas
     genéricas, de otra herramienta, ilegibles, o que no muestran el modelo/resultado pedido).
   - Borra la carpeta `.descargas` al terminar la sesión (contiene PDFs de alumnos).
   - La URL del PDF sin `?forcedownload=1` es la del enlace `pluginfile` de la entrega.

7. **Idempotencia entre ejecuciones.** Cada práctica solo muestra como "pendientes" las entregas
   sin calificar. Una vez corregido y guardado un alumno, deja de aparecer. Por eso es seguro
   ejecutar el cron a diario: si no hay nada nuevo, termina por el punto 4.

---

## FASE 1 — Navegar a Moodle y llegar a Calificaciones

### 1.1 — Login

Credenciales en el archivo `.env` (no versionado — ver `.env.example`). **Obtén los valores así:**
- En **modo desatendido** el wrapper ya exportó las variables; léelas con
  `Bash(printenv MOODLE_LOGIN_URL)`, `Bash(printenv MOODLE_USER)`, `Bash(printenv MOODLE_PASSWORD)`.
- Si alguna sale vacía (**modo interactivo**, sin variables exportadas), léelas del archivo `.env`
  con la herramienta Read sobre `/home/framorhid/proyectos/master-regresiones/.env`.

Nunca escribas las credenciales en el SKILL ni en logs; úsalas solo para rellenar el formulario.

Pasos:
1. Navega a la URL de login (`MOODLE_LOGIN_URL`).
2. Localiza el campo de usuario (placeholder "Usuario") y rellénalo.
3. Localiza el campo de contraseña y rellénalo.
4. Haz clic en "Entrar".
5. Cuando aparezca el botón "Entrar a Moodle", haz clic en él.
6. Espera a que cargue completamente el Área Personal de Moodle (`aulavirtual.redsummaeducation.net`).
7. Si aparece algún aviso de cookies o modal de bienvenida, ciérralo.

### 1.2 — Entrar al curso

Busca en "Cursos en progreso" (o "Mis cursos") y haz clic en:
**"Inteligencia Artificial Estratégica: Algoritmos para Transformar la Toma de Decisiones Financieras"**

### 1.3 — Ir a Calificaciones

Haz clic en la pestaña **"Calificaciones"** del menú del curso (Curso / Información / Participantes / **Calificaciones** / Informes / Más).

---

## FASE 2 — Detectar prácticas con entregas pendientes

Una vez cargada la tabla del Informe del calificador, ejecuta este JavaScript para localizar los tres Casos Prácticos:

```javascript
const ths = Array.from(document.querySelectorAll('th'));
const casos = [1, 2, 3].map(n => {
  const th = ths.find(el => el.textContent.trim().includes(`Caso Práctico ${n}`));
  if (!th) return null;
  const link = th.querySelector('a');
  return link ? {n, href: link.href} : {n, href: null};
}).filter(Boolean);
JSON.stringify(casos);
```

Para cada Caso Práctico con enlace:
1. Navega a su URL en una pestaña nueva (o la misma, volviendo después).
2. En la página de resumen de esa tarea, localiza el número de entregas pendientes de calificar.
   Suele aparecer como "X entregas necesitan ser calificadas" o similar junto al botón "Calificar".
3. Anota el número de pendientes.

Informa del recuento (en modo desatendido esto va al log por stdout, **sin esperar respuesta**;
en modo interactivo es un mensaje al usuario):
> "He encontrado los siguientes Casos Prácticos:
> - Caso Práctico 1: [X pendientes / sin pendientes]
> - Caso Práctico 2: [X pendientes / sin pendientes]
> - Caso Práctico 3: [X pendientes / sin pendientes]
> Empiezo con los que tienen pendientes."

Si ninguna práctica tiene pendientes, infórmalo y detente aquí (en modo desatendido, ver override 4:
registra `Sin pendientes` y termina limpiamente, sin crear borrador).

---

## FASE 3 — Corregir cada práctica pendiente en orden

Para **cada práctica con entregas pendientes** (primero 1, luego 2, luego 3):

### 3.1 — Navegar a la vista de calificación

1. Navega a la URL del Caso Práctico (obtenida en Fase 2).
2. Haz scroll hasta el botón **"Calificar"** y haz clic en él (o navega directo a
   `.../mod/assign/view.php?id=<ID>&action=grader`).
3. **Fija SIEMPRE el filtro a "Requiere calificación" antes de corregir.** No te fíes de la
   preferencia guardada en Moodle: el grader a menudo abre con el filtro en "Todo" y aterriza en
   un alumno cualquiera (incluso uno ya calificado). Pasos:
   - Localiza el control de filtro junto al indicador "N de M" (enlace "Cambiar filtros", suele
     mostrar "Todo"). Ábrelo y selecciona la opción **"Requiere calificación"** del desplegable.
   - **Recarga el grader** (`action=grader` sin `userid`) para que el filtro se aplique: debe
     aterrizar en el primer pendiente y el indicador pasar a "1 de N" (N = pendientes reales).
   - **Verifica que el alumno mostrado está "Sin calificar"** (estado "Sin calificar" / rúbrica
     vacía / "N de M" coherente con el recuento de Fase 2). Si el alumno aparece como "Calificado"
     o con la rúbrica ya rellena, **NO lo toques**: el filtro no se aplicó; vuelve a fijarlo.
4. Espera a que cargue la pantalla de corrección:
   - Izquierda: PDF de la entrega del alumno (puede tardar en generarse)
   - Derecha: rúbrica con 4 criterios y campo de comentario global
   - Arriba derecha: indicador "N de M" con el número de entrega actual

### 3.2 — Aplicar la skill de corrección correspondiente

Cuando estés en la pantalla de corrección de un alumno, **invoca la skill de corrección específica**:
- Entrega de **Práctica 1** → invoca y sigue la skill `correccion-practica1` desde el Paso 1
- Entrega de **Práctica 2** → invoca y sigue la skill `correccion-practica2` desde el Paso 1
- Entrega de **Práctica 3** → invoca y sigue la skill `correccion-practica3` desde el Paso 1

La skill de corrección se encarga de descargar el PDF, evaluar y rellenar la rúbrica. Al terminar
cada alumno, guarda el resumen de corrección (nombre, puntuaciones, comentario global) para el
informe final.

### 3.3 — Repetir para cada alumno pendiente

- **Modo interactivo:** después de que el usuario confirme o pulse "Guardar y mostrar siguiente",
  pasa al siguiente alumno.
- **Modo desatendido:** guarda tú directamente (override 2 — "Guardar y mostrar siguiente", o
  "Guardar cambios" en el último) **sin esperar confirmación**.

Repite hasta que el indicador muestre que no quedan más entregas pendientes.

### 3.4 — Confirmar al terminar cada práctica

Cuando termines todos los pendientes de una práctica:
> "He terminado con los pendientes de Práctica [N] ([M] correcciones rellenadas). Pasando a Práctica [N+1]..."

---

## FASE 4 — Crear borrador en Gmail con el resumen de la sesión

Al finalizar **todas** las correcciones, usa la herramienta `mcp__claude_ai_Gmail__create_draft` con estos parámetros:

- **to**: `franmorales93@gmail.com`
- **subject**: `Correcciones Máster IA — [fecha de hoy] — [total alumnos] alumnos`
- **body** (HTML):

```html
<h2>Resumen de correcciones — [fecha]</h2>
<p>Sesión de corrección del curso <em>IA Estratégica · Red Summa Education</em>.</p>

[Repetir por cada práctica corregida:]
<h3>Práctica [N]: [nombre de la práctica]</h3>
<table border="1" cellpadding="6" style="border-collapse:collapse">
  <tr style="background:#f0f0f0">
    <th>Alumno</th>
    <th>Comprensión Técnica</th>
    <th>Aplicación Práctica</th>
    <th>Doc. y Organización</th>
    <th>Resolución Problemas</th>
    <th>Total</th>
  </tr>
  [Una fila por alumno corregido:]
  <tr>
    <td>[nombre alumno]</td>
    <td>[0 / 1 / 2]</td>
    <td>[0 / 1,5 / 3]</td>
    <td>[0 / 1 / 2]</td>
    <td>[0 / 1,5 / 3]</td>
    <td><strong>[total]/10</strong></td>
  </tr>
</table>
<br>
```

Informa al usuario al terminar:
> "Sesión completada. He corregido [N] entregas en total. Puedes ver el borrador del resumen en Gmail."

---

## Comportamiento ante errores o interrupciones

(En modo desatendido prevalecen los overrides 4 y 5: nunca esperar input; registrar y terminar.)

- **Login falla**: informa e intenta de nuevo una vez. En interactivo, si sigue fallando pide al
  usuario que verifique credenciales; en desatendido, registra `ERROR: login fallido` y termina.
- **Caso Práctico no aparece en la tabla**: informa y continúa con los que sí están.
- **PDF no se puede descargar**: intenta de nuevo. Si falla, en interactivo describe el visor
  integrado e indica la limitación; en desatendido, sáltate ese alumno (override 5) y sigue.
- **Usuario interrumpe**: guarda el estado actual e informa del progreso alcanzado (alumnos ya rellenados).

---

## Referencia rápida de la rúbrica

Todos los Casos Prácticos usan la misma rúbrica de 10 puntos:

| Criterio | No Cumple | Cumple Parcialmente | Cumple |
|---|---|---|---|
| Comprensión Técnica | 0 | 1 | 2 |
| Aplicación Práctica | 0 | 1,5 | 3 |
| Documentación y Organización | 0 | 1 | 2 |
| Resolución de Problemas | 0 | 1,5 | 3 |
