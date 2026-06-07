# Máster IA Estratégica — Corrección Automática de Prácticas

## Qué es este proyecto

Automatiza la corrección de prácticas del curso **"Inteligencia Artificial Estratégica: Algoritmos para Transformar la Toma de Decisiones Financieras"** (Red Summa Education).  
Moodle: `aulavirtual.redsummaeducation.net` · Login: `https://campus.redsummaeducation.net/newspring/login`

## Comando principal

Di cualquiera de estas frases para iniciar la corrección automática completa:
- **"Corrige las prácticas pendientes"**
- "Empieza a corregir"
- "Hay trabajos para corregir"

Lee y sigue `skills/corregir-practicas/SKILL.md` para hacer todo: login, detección de pendientes, corrección y resumen por Gmail.

## Prácticas del curso

| Práctica | Tema | Herramienta | Enunciado |
|----------|------|-------------|-----------|
| 1 | Análisis de precios Idealista — regresión lineal + ANOVA | Dataiku | `materiales/Práctica 1.docx` |
| 2 | Boston Housing — OLS + Ridge + Lasso | Dataiku | `materiales/Práctica 2.docx` |
| 3 | Detección de fraude — regresión logística | Dataiku | `materiales/Práctica 3.docx` |

## Skills disponibles

Lee el archivo correspondiente cuando necesites seguir el flujo de corrección:

| Archivo | Cuándo usarla |
|---------|---------------|
| `skills/corregir-practicas/SKILL.md` | **Skill maestra**: navega a Moodle, detecta pendientes, corrige todo, crea borrador Gmail |
| `skills/correccion-practica1/SKILL.md` | Cuando ya estás en la vista de calificación de P1 |
| `skills/correccion-practica2/SKILL.md` | Cuando ya estás en la vista de calificación de P2 |
| `skills/correccion-practica3/SKILL.md` | Cuando ya estás en la vista de calificación de P3 |

## Rúbrica común (todas las prácticas — 10 puntos)

| Criterio | No Cumple | Cumple Parcialmente | Cumple |
|----------|-----------|---------------------|--------|
| Comprensión Técnica | 0 | 1 | 2 |
| Aplicación Práctica | 0 | 1,5 | 3 |
| Documentación y Organización | 0 | 1 | 2 |
| Resolución de Problemas | 0 | 1,5 | 3 |

## Contenido del curso (en `materiales/`)

- `Unidad 1 - Clase 1.docx` — Repaso ML, regresión, etapas del modelo
- `Unidad 1 - Clase2.docx` — Correlación, mínimos cuadrados, ANOVA
- `Unidad 2 - Clase 3.docx` — Evaluación: MSE, MAE, R², RMSE
- `Unidad 2 - Clase 4.docx` — Regularización: Ridge (L2), Lasso (L1)
- `Unidad 3 - Clase 5.docx` — Árboles de regresión (CART)
- `Unidad 3 - Clase 6.docx` — Regresión logística, clasificación binaria

## Integración Google MCP

Al terminar una sesión de corrección, `corregir-practicas` usa `mcp__claude_ai_Gmail__create_draft`
para crear un borrador en `franmorales93@gmail.com` con la tabla de notas de todos los alumnos corregidos.
