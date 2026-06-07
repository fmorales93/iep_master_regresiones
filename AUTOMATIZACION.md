# Automatización diaria de la corrección — Plan

Objetivo: que una vez al día se corrijan automáticamente todas las prácticas pendientes,
**sin intervención humana**, y quede un borrador de Gmail con el resumen para revisar.

La skill ya está preparada para esto: ver el bloque **MODO DESATENDIDO** en
`skills/corregir-practicas/SKILL.md`. Este documento cubre el *despliegue*.

> **Principio de seguridad:** el flujo corrige y guarda las notas en Moodle, pero termina creando
> un **borrador** de Gmail (no lo envía). La revisión humana del resumen por la mañana es la red de
> seguridad. No automatizar el envío.

---

## Cómo se dispara el modo desatendido

La skill entra en modo desatendido si la petición incluye la palabra `desatendido` **o** si existe
la variable de entorno `CORRECCION_DESATENDIDA=1`. El comando de cron usa ambas, por redundancia.

Comando base:

```bash
CORRECCION_DESATENDIDA=1 claude -p "Corrige las prácticas pendientes en modo desatendido"
```

---

## Hallazgos de la primera corrida real (3 jun 2026)

La primera ejecución desatendida completa funcionó (corrigió 1 entrega de Práctica 2 y creó el
borrador), pero destapó cosas que el plan inicial daba por hechas y **no** se cumplían. Tenerlas en
cuenta antes de automatizar:

1. **Hay dos servidores MCP de Chrome registrados; solo uno sirve.**
   - ✅ El del **plugin**: `mcp__plugin_chrome-devtools-mcp_chrome-devtools__*`, configurado con
     `--browserUrl http://127.0.0.1:9222` → se **conecta** al Chrome del perfil persistente. Es el bueno.
   - ❌ `mcp__chrome-devtools-mcp__*` (referenciado en `enabledMcpjsonServers: ["chrome-devtools-mcp"]`
     de `.claude/settings.local.json`, pero sin `.mcp.json` que lo defina) → intenta **lanzar su
     propio Chrome** y falla (`Code: 21`). **Acción pendiente:** quitar ese `enabledMcpjsonServers`
     roto para no tropezar con él en cada arranque.

2. **No hay `pip`, ni `sudo`, ni librerías PDF** (`pdfplumber`, `pypdf`, `pdftotext`...). Las skills de
   práctica que dicen `pip install pdfplumber` **no funcionan aquí**. La lectura del PDF se hace solo
   con la stdlib de Python (`zlib`+`re`, extrayendo texto de los bloques `BT...ET`). Ya está recogido
   en el override 6 del SKILL.

3. **`evaluate_script` con `filePath` solo escribe dentro del workspace.** Por eso la carpeta de
   descargas va a `master-regresiones/.descargas`, no a `~/correccion-descargas`. El PDF se baja con
   un `fetch` autenticado dentro de la página (no con descarga del navegador) → más fiable y headless-safe.

4. **La sesión de Moodle caduca.** En esta corrida el perfil ya no tenía sesión y el login idempotente
   se relogueó solo con credenciales. Funciona, pero confirma que **no puedes depender** de la sesión
   guardada: las credenciales del SKILL son el mecanismo real.

---

## FASE A — Validación en local con cron (WSL)

Meta: demostrar que el flujo corre de principio a fin sin que tengas que tocar nada.
Hazlo durante ~1 semana antes de pasar al NAS.

### A.1 — Requisitos previos (una sola vez)

- [ ] Claude Code CLI instalado y **autenticado** en WSL (`claude` arranca sin pedir login).
- [ ] MCP `chrome-devtools-mcp` habilitado (ya está en `.claude/settings.local.json`).
- [ ] Conectores de Claude.ai (Gmail) autorizados desde la cuenta `franmorales93@gmail.com`.
- [ ] Carpeta temporal de descargas **dentro del workspace** (obligatorio: `evaluate_script` solo
  escribe dentro del root del proyecto):
  ```bash
  mkdir -p /home/framorhid/proyectos/master-regresiones/.descargas
  ```
- [ ] Sesión de Moodle iniciada al menos una vez en el perfil persistente
  `/home/framorhid/.chrome-moodle`, para que el login idempotente la reaproveche.
  (Si caduca, la skill vuelve a loguearse sola con las credenciales del SKILL.)

### A.2 — Permisos no interactivos — INSTALADO: allowlist estricta

Elegido el modelo de **allowlist estricta** (no `--dangerously-skip-permissions`). El cron solo puede
ejecutar lo permitido en `.claude/settings.local.json`. Permisos que usa el flujo (ya añadidos):
las MCP del plugin chrome-devtools (`navigate_page`, `list_pages`, `evaluate_script`, `fill_form`,
`click`, `take_snapshot`, `wait_for`), `mcp__claude_ai_Gmail__create_draft`, `Bash(python3 *)`,
`Bash(google-chrome *)`, los `curl` de comprobación, `Bash(mkdir -p .../.descargas)` y
`Bash(rm -rf .../.descargas)`.

> Si amplías el flujo (nuevas herramientas Bash/MCP), **añádelas a la allowlist** o la corrida las
> rechazará silenciosamente en modo `-p`.

### A.3 — Script wrapper — INSTALADO

Está en **`/home/framorhid/correccion-diaria.sh`** (ejecutable). Resumen de lo que hace:
fija el `PATH` de cron (incluye el bin de nvm para que el MCP arranque con `npx`), exporta
`CORRECCION_DESATENDIDA=1`, arranca Chrome en `:9222` si no está vivo y espera hasta 30 s, y luego
lanza `claude -p "Corrige las prácticas pendientes en modo desatendido"` (sin skip-permissions),
volcando todo a `~/correccion-AAAA-MM-DD.log`. Aborta con error si Chrome no responde.

### A.4 — Programar el cron — INSTALADO (8:00 diario)

Instalado en el crontab del usuario:

```cron
0 8 * * *  /home/framorhid/correccion-diaria.sh
```

Para cambiar la hora: `crontab -e`. Para probar ya: `bash /home/framorhid/correccion-diaria.sh`
y revisar `~/correccion-$(date +%F).log`.

> **Nota WSL:** WSL no se arranca solo si el PC está apagado, y cron no corre si WSL no está vivo.
> Durante la validación, deja el PC y WSL encendidos a las 8:00. El "siempre encendido" lo resuelve
> la FASE B (NAS). El demonio `cron` está activo y `enabled`.

### A.5 — Criterios de validación (qué mirar cada día)

- [ ] El log muestra el recuento de pendientes y una línea por alumno corregido.
- [ ] Las notas aparecen correctamente guardadas en Moodle.
- [ ] Se ha creado el borrador en Gmail con la tabla de notas.
- [ ] Cuando **no** hay pendientes, el log dice `Sin pendientes` y termina limpio (sin borrador).
- [ ] No se queda colgado esperando confirmación en ningún punto.

Si una semana de ejecuciones pasa estos criterios sin intervención → listo para el NAS.

---

## FASE B — Migración al NAS UGREEN

Meta: mover el cron validado a una máquina **siempre encendida**. Los UGREEN con UGOS Pro
(sobre todo modelos x86, p. ej. la serie DXP) soportan **Docker**, que es la vía.

### B.1 — Estrategia

Un contenedor Linux que reproduzca el entorno de WSL:

- Node + Claude Code CLI
- **Chromium headless** (`--headless=new --remote-debugging-port=9222`) — en el NAS no hay
  pantalla, así que headless es obligatorio (en WSL valía con Chrome normal).
- Volúmenes persistentes para:
  - el proyecto (`/home/framorhid/proyectos/master-regresiones` → `/proyecto`)
  - el perfil de Chrome con la sesión de Moodle (`.chrome-moodle`)
  - la config/credenciales de Claude Code (`~/.claude`)
  - la carpeta de descargas
- Cron dentro del contenedor (o el cron del NAS lanzando `docker exec`).

### B.2 — Pasos

1. [ ] Confirmar que tu modelo de NAS soporta **Docker / Container Manager** en UGOS Pro.
2. [ ] Construir una imagen basada en `node:lts-slim` + `chromium` + Claude Code CLI.
3. [ ] Migrar credenciales/sesiones a volúmenes montados:
   - `~/.claude` (auth de Claude Code) — reautenticar si el token no es portable.
   - `.chrome-moodle` (sesión de Moodle) — copiar el perfil ya logueado desde WSL.
   - Conectores Gmail de Claude.ai — reautorizar desde el contenedor si hace falta.
4. [ ] Ajustar el wrapper para **headless**: cambiar el arranque de Chrome a
   `chromium --headless=new --remote-debugging-port=9222 --user-data-dir=... --no-sandbox`.
   (Con descargas en headless, la skill ya fija el `downloadPath` vía CDP — override 6.)
5. [ ] Programar el cron del NAS (Container Manager → tarea programada, o crontab dentro del contenedor).
6. [ ] Ejecutar una vez a mano (`docker exec ... correccion-diaria.sh`) y revisar el log + el borrador.

### B.3 — Riesgos/fricciones a vigilar en el NAS

| Fricción | Mitigación |
|---|---|
| Token de Claude Code no portable a headless | Reautenticar dentro del contenedor; documentar el procedimiento. |
| Sesión de Moodle caduca | El login idempotente de la skill se reloguea solo con credenciales. |
| Descargas en Chromium headless | La skill fija `downloadPath` por CDP; verificar que el PDF aparece en la carpeta. |
| Recursos del NAS (RAM/CPU) | Chromium + Claude consumen; revisar que el modelo aguanta. |
| Coste por ejecución | Cada corrida gasta créditos; el modo "sin pendientes" sale barato y termina pronto. |

---

## Resumen de archivos tocados

- `skills/corregir-practicas/SKILL.md` — añadido el bloque **MODO DESATENDIDO** (overrides 1–7) y
  hechos condicionales los puntos que esperaban confirmación humana (FASE 2, 3.3, errores).
- `AUTOMATIZACION.md` — este plan.
