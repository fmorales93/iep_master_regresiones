---
name: moodle-caso-practico1
description: >
  Navega automáticamente al campus Moodle de Red Summa Education, hace login con
  las credenciales guardadas, entra al curso de Inteligencia Artificial Estratégica,
  va a Calificaciones, abre Caso Práctico 1 y entra en la vista de calificación de entregas.
  Usa esta skill cuando el usuario diga cosas como "ve a Moodle", "abre el campus",
  "entra al curso de IA", "ve a Calificaciones", "abre Caso Práctico 1", "califica entregas",
  "quiero calificar", o cualquier variante que implique navegar al campus de Red Summa,
  al curso de IA Estratégica, o a la pantalla de calificación de alumnos.
---

# Skill: Navegar y Calificar en Caso Práctico 1 – Moodle

## Propósito

Esta skill automatiza la navegación completa desde el login del campus hasta la
vista de calificación de entregas de "Caso Práctico 1" en el curso de IA Estratégica.

## Credenciales (cargadas desde `.env`, no versionado — ver `.env.example`)

- **URL de login:** variable `MOODLE_LOGIN_URL` (https://campus.redsummaeducation.net/newspring/login)
- **Usuario:** variable `MOODLE_USER`
- **Contraseña:** variable `MOODLE_PASSWORD`

## Pasos de navegación

Sigue estos pasos en orden usando las herramientas de Claude in Chrome:

### 1. Abrir la página de login

Usa `navigate` para ir a:
```
https://campus.redsummaeducation.net/newspring/login
```

### 2. Iniciar sesión

Localiza el campo de usuario (ref con placeholder "Usuario") y rellénalo con el valor de `MOODLE_USER`.
Localiza el campo de contraseña y rellénalo con el valor de `MOODLE_PASSWORD`.
Haz clic en el botón "Entrar".

Después del login aparecerá un panel con el botón **"Entrar a Moodle"**. Haz clic en él.
Espera a que cargue completamente el Área Personal de Moodle (aulavirtual.redsummaeducation.net).

### 3. Entrar al curso de IA Estratégica

En el dashboard busca y haz clic en el curso:
**"Inteligencia Artificial Estratégica: Algoritmos para Transformar la Toma de Decisiones Financieras"**

Está en la sección "Cursos en progreso". Si no lo ves, busca en "Mis cursos".

### 4. Ir a Calificaciones

Dentro del curso aparece una barra de menú con las pestañas: Curso / Información / Participantes / **Calificaciones** / Informes / Más.
Haz clic en **"Calificaciones"**.

Esto abrirá el Informe del calificador con la tabla de notas de todos los alumnos.

### 5. Llegar a Caso Práctico 1

En la tabla de calificaciones el enlace "Caso Práctico 1" puede estar fuera del área visible (scroll horizontal).
Usa `javascript_tool` para localizarlo y hacer scroll hasta él:

```javascript
const ths = Array.from(document.querySelectorAll('th'));
const casoTh = ths.find(el => el.textContent.includes('Caso Práctico 1'));
if (casoTh) {
  const link = casoTh.querySelector('a');
  if (link) {
    link.scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});
    link.href;
  }
}
```

Copia la URL devuelta y navega a ella directamente con `navigate`, o haz clic en el enlace encontrado.

### 6. Hacer clic en "Calificar"

En la página de Caso Práctico 1 aparece un resumen con:
- Número de participantes, enviados y pendientes de calificar
- El botón **"Calificar"** (en color oscuro, antes del sumario de calificaciones)

Haz scroll hasta el botón "Calificar" y haz clic en él.

### 7. Confirmar llegada a la vista de calificación

Tras hacer clic en "Calificar" se abre la pantalla de corrección donde:
- A la izquierda se muestra el PDF de la entrega del alumno (puede tardar en generarse)
- A la derecha aparece la rúbrica con los criterios (Comprensión Técnica, Aplicación Práctica, etc.)
- En la parte inferior hay botones: **Guardar cambios**, **Guardar y mostrar siguiente**, **Reiniciar**
- Arriba a la derecha indica el número de entregas pendientes (ej. "1 de 18")

Informa al usuario del nombre del alumno actual, cuántas entregas hay pendientes y que ya puede empezar a calificar.

## Notas importantes

- El campus puede tardar unos segundos en cargar después del login; espera a que la página esté completamente cargada antes de continuar.
- Si aparece algún aviso de cookies o modal de bienvenida, ciérralo antes de continuar.
- Si el login falla, verifica que las credenciales son correctas e informa al usuario.
- Si el nombre del curso no coincide exactamente, busca el que contenga "Inteligencia Artificial Estratégica".
- El PDF de la entrega puede tardar en generarse ("Generando el PDF...") — es normal, no es un error.
