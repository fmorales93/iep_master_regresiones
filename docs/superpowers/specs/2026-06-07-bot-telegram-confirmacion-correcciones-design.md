# Bot de Telegram para confirmar las subidas de correcciones — Diseño

Fecha: 2026-06-07
Estado: aprobado (pendiente de plan de implementación)

## Problema

Hoy el cron de las 8:00 (`correccion-diaria.sh` → `claude -p "...desatendido"`) corrige
**y guarda directamente en Moodle**, y deja un borrador de Gmail como red de seguridad que se
revisa *después*. Queremos mover la revisión humana a **antes de guardar**: el agente propone las
notas, y nada se sube a Moodle hasta que la persona lo aprueba desde **Telegram**.

## Decisiones de diseño (acordadas con el usuario)

1. **Momento de confirmación:** antes de guardar en Moodle (Telegram es la puerta real).
2. **Granularidad:** por práctica (lote). Una tabla por práctica; un OK guarda todos sus alumnos.
3. **Disparo:** dos vías que terminan en la misma puerta de aprobación: (a) el cron de las 8:00,
   que ya no guarda solo — corrige, propone por Telegram y espera el OK; (b) `/corregir` manual desde
   Telegram cuando el usuario quiera lanzarla.
4. **Rechazo:** no guardar + permitir editar. El usuario responde ajustes en texto libre por
   Telegram; claude los aplica al JSON y el bot reenvía la tabla para reaprobar.
5. **Enfoque técnico:** dos fases + contrato JSON + bot daemon (enfoque A).
6. **Gmail:** se mantiene el borrador, pero generado al final de la Fase 2 como **registro de lo
   realmente guardado** (no de lo propuesto).

## Restricciones del entorno (de AUTOMATIZACION.md)

- **Sin `pip` ni `sudo` ni librerías externas.** El bot se escribe en **Python solo con stdlib**
  (`urllib` + `json` + `subprocess`), hablando con la Telegram Bot HTTP API por long-polling.
- **`claude -p` es de un solo turno**, no puede quedarse vivo horas esperando el OK → de ahí el
  modelo de dos fases con estado persistido en disco.
- El MCP de Chrome bueno es el del plugin (`mcp__plugin_chrome-devtools-mcp_*`, `--browserUrl
  http://127.0.0.1:9222`). Moodle solo se conduce vía ese MCP, nunca por HTTP a mano.
- **Allowlist estricta** en `.claude/settings.local.json`: cualquier herramienta nueva que use
  claude (Bash/MCP/Read) hay que añadirla o se rechaza en modo `-p`.

## Arquitectura

### Enfoque elegido (A) vs descartados

- **A (elegido):** bot daemon "tonto" que solo maneja Telegram y lanza procesos; claude mantiene
  todo el juicio + Moodle + edición del JSON. Encaja con la arquitectura actual (cron + wrappers +
  allowlist) y respeta "sin pip".
- **B (descartado):** un único `claude` vivo que habla con Telegram por `curl` y hace polling.
  Caro (turnos parado horas), frágil (un crash pierde todo), y `-p` no está pensado para esperas largas.
- **C (descartado):** el bot reimplementa Moodle por HTTP puro, sin claude. Reescritura enorme,
  frágil ante cambios de HTML, y tira el flujo chrome-devtools que ya funciona.

### Componentes

| Pieza | Qué es | Cambio |
|---|---|---|
| `bot/bot-telegram.py` | Demonio Python stdlib (long-polling). Único que habla con Telegram. | Nuevo |
| `propuestas/` | Un JSON por práctica = propuesta **y** estado compartido. Gitignored. | Nuevo |
| `skills/corregir-practicas/SKILL.md` | Añadir 2 sub-modos: **proponer** (vuelca JSON, no guarda) y **guardar** (lee JSON aprobado y guarda en Moodle). | Modificar |
| `correccion-diaria.sh` | Fase 1: lanza el modo "proponer". Además resucita el bot si no está vivo. Lo usan tanto el cron como `/corregir` del bot. | Modificar |
| `guardar-aprobadas.sh` | Wrapper de Fase 2: lanza claude en modo "guardar" para una práctica. Lo invoca el bot. | Nuevo |
| `.env` / `.env.example` | Añadir `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`. | Modificar |
| `.claude/settings.local.json` | Allowlist: lectura/escritura de `propuestas/`, lo que necesite Fase 2. | Modificar |

### Contrato JSON

`propuestas/<fecha>-p<N>.json` es a la vez la propuesta y la máquina de estados. El bot, si se
reinicia, relee `propuestas/` y recupera lo pendiente — **sin base de datos aparte**.

```json
{
  "practica": 2,
  "fecha": "2026-06-07",
  "estado": "pendiente",
  "alumnos": [
    {
      "nombre": "Ana López",
      "grader_url": "https://aulavirtual.../mod/assign/view.php?id=99&action=grader&userid=123",
      "criterios": {"comprension": 2, "aplicacion": 1.5, "documentacion": 2, "resolucion": 3},
      "total": 8.5,
      "comentario": "Buen modelo OLS; faltan métricas en la captura de Ridge.",
      "guardado": false
    }
  ]
}
```

- `estado`: `pendiente` | `editando` | `aprobada` | `guardada` | `rechazada`.
- `criterios`: valores válidos de la rúbrica común — comprension ∈ {0,1,2}, aplicacion ∈ {0,1.5,3},
  documentacion ∈ {0,1,2}, resolucion ∈ {0,1.5,3}.
- `grader_url` incluye el `userid`, para que Fase 2 navegue directo y rellene exactamente esas notas.
- `guardado` por alumno: permite reintentos parciales si Fase 2 falla a mitad.

### Flujo

```
8:00 cron  ─┐
/corregir ──┴→ Fase1 claude (corrige, NO guarda) → escribe propuestas/p<N>.json (estado:pendiente)
         → bot detecta JSON nuevo → manda tabla P_N con [✅ Aprobar] [✏️ Rechazar]
  Aprobar  → bot lanza guardar-aprobadas.sh N → Fase2 claude guarda en Moodle
           → marca alumnos guardado:true, estado:guardada → crea borrador Gmail → bot confirma
  Rechazar → bot pide ajustes → usuario responde texto → claude edita JSON (estado:editando→pendiente)
           → bot reenvía tabla para reaprobar
```

### Reparto de responsabilidades

- **Bot (`bot-telegram.py`, stdlib):** toda la I/O de Telegram (getUpdates, sendMessage con teclados
  inline, answerCallbackQuery), la máquina de estados leyendo/escribiendo `propuestas/`, y el
  lanzamiento de procesos (`guardar-aprobadas.sh`, claude para aplicar ediciones). No tiene juicio
  propio ni toca Moodle.
- **Claude (vía wrappers):** corrección (Fase 1, modo proponer), guardado (Fase 2, modo guardar),
  y aplicación de ediciones en texto libre sobre el JSON. Todo conduciendo Moodle por el MCP de Chrome.

## Operación

### Hosting / always-on

- El bot debe estar vivo para recibir el OK (que puede llegar horas después de las 8:00).
- En WSL (FASE A): arranque con `@reboot` en crontab **y** el wrapper `correccion-diaria.sh` lo
  resucita si no está vivo antes de la Fase 1 (doble red). Requiere PC/WSL encendido, que ya es
  premisa de la FASE A.
- Un único proceso: lockfile `bot/bot.pid` evita duplicados.
- En FASE B (NAS): el bot pasa a ser otro proceso del contenedor, siempre activo.

### Seguridad

- `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en `.env` (gitignored). El bot **solo** responde a ese
  `chat_id`; ignora cualquier otro mensaje o callback.
- El bot no toca Moodle ni guarda credenciales de Moodle; solo lanza wrappers que cargan `.env`.
  La allowlist estricta sigue gobernando lo que claude puede hacer.
- `propuestas/` gitignored (notas reales de alumnos), igual que `.descargas`.

### Comandos del bot

- `/corregir` → lanza la Fase 1 (modo proponer) reusando `correccion-diaria.sh`. El bot responde de
  inmediato ("Corrigiendo, te aviso cuando tenga la propuesta…") y, al terminar, manda las tablas.
  Serializado con lock: si ya hay una Fase 1 en marcha (o el cron está corriendo), avisa y no lanza
  otra.
- `/estado` → lista qué hay en `propuestas/` y su estado.
- `/pendientes` → reenvía las tablas que estén `pendiente` (por si se perdió el mensaje).

### Casos límite

- **Sin pendientes:** Fase 1 no genera JSON → el bot manda "Hoy sin pendientes ✅", sin botones.
- **Mensaje muy largo** (> 4096 chars): el bot trocea; los botones van en el último mensaje.
- **Doble aprobación:** el bot serializa las Fase-2 con lock; si el JSON ya está `guardada`, responde
  "ya estaba guardada" sin relanzar.
- **Fase 2 falla a mitad:** los `guardado:true`/`false` por alumno permiten reintento; el bot avisa
  del fallo y deja el resto reintentable. El login idempotente de la skill re-loguea si la sesión caducó.
- **Concurrencia con Chrome:** Fase 1 ya terminó al aprobar; Fase 2 reusa/levanta Chrome en `:9222`
  como el wrapper actual.

## Cambios concretos en archivos existentes

- `skills/corregir-practicas/SKILL.md`: la FASE 3 deja de guardar en modo desatendido; en su lugar,
  **modo proponer** vuelca el JSON. **Modo guardar** (nuevo) lee el JSON aprobado, navega cada
  `grader_url`, rellena la rúbrica con `criterios` + `comentario` y guarda. La FASE 4 (Gmail) pasa
  al final del modo guardar y refleja lo realmente guardado.
- `correccion-diaria.sh`: el `claude -p` pasa a pedir el modo proponer; añade el bloque que resucita
  el bot si no está vivo.
- `.claude/settings.local.json`: añadir permisos para `propuestas/` (Read/Write) y lo que requiera
  la Fase 2.
- `.gitignore`: añadir `propuestas/` y `bot/bot.pid`.
- `.env.example`: documentar `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`.

## Pruebas

- **Bot (stdlib, aislado):** test del parseo de updates, filtrado por `chat_id`, troceado de
  mensajes largos, y la máquina de estados sobre JSON de ejemplo (sin tocar Telegram real —
  inyectando respuestas simuladas de la API).
- **Contrato JSON:** validación de rangos de `criterios` y coherencia de `total`.
- **End-to-end manual:** una corrida real con una entrega de prueba: Fase 1 genera JSON →
  llega la tabla a Telegram → Aprobar → la nota aparece en Moodle y el borrador en Gmail.
- **Rechazo+edición:** rechazar, mandar un ajuste en texto, comprobar que el JSON cambia y reaparece
  la tabla.

## Fuera de alcance (YAGNI)

- Aprobación por alumno individual (se eligió por práctica).
- Migración a NAS (FASE B; este diseño la deja preparada pero no la ejecuta).
- Práctica final (sigue aplazada en PROXIMOS-PASOS.md).
