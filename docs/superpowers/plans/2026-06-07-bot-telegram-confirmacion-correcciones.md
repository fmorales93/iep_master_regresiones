# Bot de Telegram para confirmar subidas de correcciones — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que las correcciones del máster se propongan por Telegram y no se guarden en Moodle hasta que el usuario las apruebe por práctica (con opción de editar antes de aprobar), disparadas por el cron de las 8:00 o por `/corregir`.

**Architecture:** Dos fases con estado persistido en disco (`propuestas/p<N>.json`). Un bot daemon en Python stdlib es el único que habla con Telegram (long-polling): recibe comandos/botones, posta tablas y **lanza procesos**. `claude` (vía wrappers de shell) mantiene todo el juicio: corregir (Fase 1, "modo proponer" → vuelca JSON), guardar (Fase 2, "modo guardar" → lee JSON aprobado y escribe en Moodle) y aplicar ediciones en texto libre. El bot nunca toca Moodle ni mete texto no confiable en la shell.

**Tech Stack:** Python 3 **solo stdlib** (`urllib`, `json`, `subprocess`, `unittest`) — sin pip. Bash para los wrappers. Telegram Bot HTTP API. MCP chrome-devtools (del plugin) para Moodle, ya existente.

Spec: `docs/superpowers/specs/2026-06-07-bot-telegram-confirmacion-correcciones-design.md`

---

## Estructura de archivos

Módulos Python (en `bot/`, importables; testeables con stdlib `unittest`):

| Archivo | Responsabilidad |
|---|---|
| `bot/config.py` | Parsear `.env` y construir la config (token, chat_id, rutas). |
| `bot/propuestas.py` | Contrato JSON: cargar/guardar/listar, validar rúbrica, construir los mensajes de tabla (HTML `<pre>` troceado), helpers de estado. |
| `bot/telegram_api.py` | Cliente fino de la Telegram Bot API sobre `urllib`, con `transport` inyectable para tests. Teclados inline. |
| `bot/dispatch.py` | Lógica pura de manejo de un `update`: autorización por chat_id, comandos, callbacks, flujo de edición. Recibe un `ctx` con dependencias inyectadas (cliente, launcher, dir). |
| `bot/bot-telegram.py` | Entrypoint/daemon: carga config, monta `ctx` real, bucle de long-polling + watcher de propuestas, pidfile. Thin. |

Scripts shell:

| Archivo | Responsabilidad |
|---|---|
| `correccion-diaria.sh` (modificar) | Fase 1 "modo proponer". Resucita el bot si no está vivo. Lo usan cron y `/corregir`. |
| `guardar-aprobadas.sh` (nuevo) | Fase 2: lanza `claude` "modo guardar" para una práctica. |
| `aplicar-edicion.sh` (nuevo) | Lanza `claude` "modo edición" para aplicar `ajustes_pendientes` de un JSON. |
| `iniciar-bot.sh` (nuevo) | Arranca el daemon si no está vivo (pidfile). Lo llaman `@reboot` y el wrapper de Fase 1. |

Otros:

| Archivo | Cambio |
|---|---|
| `skills/corregir-practicas/SKILL.md` | Añadir modos proponer/guardar/edición y captura de `grader_url`. |
| `.env.example` | Documentar `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. |
| `.gitignore` | Añadir `propuestas/`, `bot/bot.pid`. |
| `.claude/settings.local.json` | Allowlist: Read/Write de `propuestas/**` y los nuevos wrappers. |
| `tests/` | Tests `unittest` de los módulos del bot. |

**Convención de import en tests:** cada test añade `bot/` al path:
```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bot"))
```

**Comando de tests:** `python3 -m unittest discover -s tests -t . -v`

**Contrato JSON** (recordatorio del spec), `propuestas/<fecha>-p<N>.json`:
```json
{
  "practica": 2,
  "fecha": "2026-06-07",
  "estado": "pendiente",
  "notificado": false,
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

---

## Task 1: Scaffolding + módulo de configuración

**Files:**
- Create: `bot/__init__.py` (vacío)
- Create: `bot/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Crear paquete vacío**

Crear `bot/__init__.py` con contenido vacío.

- [ ] **Step 2: Write the failing test**

`tests/test_config.py`:
```python
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bot"))
import config

class TestParseEnv(unittest.TestCase):
    def test_parsea_claves_ignorando_comentarios_y_vacias(self):
        contenido = (
            "# comentario\n"
            "TELEGRAM_BOT_TOKEN=123:abc\n"
            "\n"
            "TELEGRAM_CHAT_ID=999\n"
            "MOODLE_USER=fulano\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
            f.write(contenido); ruta = f.name
        try:
            d = config.parse_env(ruta)
        finally:
            os.unlink(ruta)
        self.assertEqual(d["TELEGRAM_BOT_TOKEN"], "123:abc")
        self.assertEqual(d["TELEGRAM_CHAT_ID"], "999")
        self.assertEqual(d["MOODLE_USER"], "fulano")
        self.assertNotIn("# comentario", d)

    def test_load_config_calcula_rutas_y_tipa_chat_id(self):
        contenido = "TELEGRAM_BOT_TOKEN=tok\nTELEGRAM_CHAT_ID=42\n"
        with tempfile.TemporaryDirectory() as proj:
            env = os.path.join(proj, ".env")
            with open(env, "w") as f: f.write(contenido)
            cfg = config.load_config(proj, env)
            self.assertEqual(cfg.token, "tok")
            self.assertEqual(cfg.chat_id, 42)
            self.assertEqual(cfg.propuestas_dir, os.path.join(proj, "propuestas"))

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m unittest tests.test_config -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'config'`.

- [ ] **Step 4: Write minimal implementation**

`bot/config.py`:
```python
import os
from collections import namedtuple

Config = namedtuple("Config", "token chat_id project_dir propuestas_dir")

def parse_env(path):
    valores = {}
    with open(path, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            valores[clave.strip()] = valor.strip()
    return valores

def load_config(project_dir, env_path=None):
    env_path = env_path or os.path.join(project_dir, ".env")
    env = parse_env(env_path)
    return Config(
        token=env["TELEGRAM_BOT_TOKEN"],
        chat_id=int(env["TELEGRAM_CHAT_ID"]),
        project_dir=project_dir,
        propuestas_dir=os.path.join(project_dir, "propuestas"),
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m unittest tests.test_config -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add bot/__init__.py bot/config.py tests/test_config.py
git commit -m "feat(bot): módulo de configuración (parse .env + rutas)"
```

---

## Task 2: Validación del contrato JSON

**Files:**
- Create: `bot/propuestas.py`
- Test: `tests/test_propuestas.py`

- [ ] **Step 1: Write the failing test**

`tests/test_propuestas.py`:
```python
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bot"))
import propuestas

def alumno_ok():
    return {
        "nombre": "Ana López",
        "grader_url": "https://x/grader&userid=1",
        "criterios": {"comprension": 2, "aplicacion": 1.5, "documentacion": 2, "resolucion": 3},
        "total": 8.5,
        "comentario": "ok",
        "guardado": False,
    }

def prop_ok():
    return {"practica": 2, "fecha": "2026-06-07", "estado": "pendiente",
            "notificado": False, "alumnos": [alumno_ok()]}

class TestValidar(unittest.TestCase):
    def test_propuesta_correcta_sin_errores(self):
        self.assertEqual(propuestas.validar(prop_ok()), [])

    def test_criterio_fuera_de_rango(self):
        p = prop_ok(); p["alumnos"][0]["criterios"]["aplicacion"] = 2  # no permitido
        errores = propuestas.validar(p)
        self.assertTrue(any("aplicacion" in e for e in errores))

    def test_total_incoherente(self):
        p = prop_ok(); p["alumnos"][0]["total"] = 10
        errores = propuestas.validar(p)
        self.assertTrue(any("total" in e.lower() for e in errores))

    def test_estado_invalido(self):
        p = prop_ok(); p["estado"] = "loquesea"
        self.assertTrue(any("estado" in e.lower() for e in propuestas.validar(p)))

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_propuestas -v`
Expected: FAIL — `No module named 'propuestas'`.

- [ ] **Step 3: Write minimal implementation**

`bot/propuestas.py`:
```python
ESTADOS = {"pendiente", "editando", "aprobada", "guardada", "rechazada"}
RUBRICA = {
    "comprension": {0, 1, 2},
    "aplicacion": {0, 1.5, 3},
    "documentacion": {0, 1, 2},
    "resolucion": {0, 1.5, 3},
}

def total_alumno(alumno):
    return sum(alumno["criterios"][k] for k in RUBRICA)

def validar(prop):
    errores = []
    if prop.get("estado") not in ESTADOS:
        errores.append("estado inválido: %r" % prop.get("estado"))
    for al in prop.get("alumnos", []):
        nombre = al.get("nombre", "?")
        crit = al.get("criterios", {})
        for k, permitidos in RUBRICA.items():
            if crit.get(k) not in permitidos:
                errores.append("%s: criterio %s con valor inválido %r" % (nombre, k, crit.get(k)))
        if abs(al.get("total", -1) - total_alumno(al)) > 1e-9:
            errores.append("%s: total no coincide con la suma de criterios" % nombre)
    return errores
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_propuestas -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add bot/propuestas.py tests/test_propuestas.py
git commit -m "feat(bot): validación del contrato JSON de propuestas"
```

---

## Task 3: Persistencia y listado de propuestas

**Files:**
- Modify: `bot/propuestas.py`
- Modify: `tests/test_propuestas.py`

- [ ] **Step 1: Write the failing test (añadir al final, antes del `if __name__`)**

```python
import tempfile, json

class TestPersistencia(unittest.TestCase):
    def test_guardar_y_cargar_roundtrip(self):
        p = prop_ok()
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "2026-06-07-p2.json")
            propuestas.guardar(p, ruta)
            self.assertEqual(propuestas.cargar(ruta), p)

    def test_listar_ordena_y_devuelve_pares(self):
        with tempfile.TemporaryDirectory() as d:
            propuestas.guardar(prop_ok(), os.path.join(d, "2026-06-07-p2.json"))
            p1 = prop_ok(); p1["practica"] = 1
            propuestas.guardar(p1, os.path.join(d, "2026-06-07-p1.json"))
            listado = propuestas.listar(d)
            nombres = [os.path.basename(r) for r, _ in listado]
            self.assertEqual(nombres, ["2026-06-07-p1.json", "2026-06-07-p2.json"])
            self.assertEqual(listado[0][1]["practica"], 1)

    def test_listar_dir_inexistente_devuelve_vacio(self):
        self.assertEqual(propuestas.listar("/no/existe/x"), [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_propuestas -v`
Expected: FAIL — `module 'propuestas' has no attribute 'guardar'`.

- [ ] **Step 3: Write minimal implementation (añadir a `bot/propuestas.py`)**

```python
import os, json

def cargar(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def guardar(prop, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(prop, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)  # escritura atómica

def listar(dirpath):
    if not os.path.isdir(dirpath):
        return []
    pares = []
    for nombre in sorted(os.listdir(dirpath)):
        if nombre.endswith(".json"):
            ruta = os.path.join(dirpath, nombre)
            pares.append((ruta, cargar(ruta)))
    return pares
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_propuestas -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add bot/propuestas.py tests/test_propuestas.py
git commit -m "feat(bot): persistencia atómica y listado de propuestas"
```

---

## Task 4: Mensajes de tabla (HTML `<pre>` troceado)

Telegram **no** renderiza `<table>`; sí renderiza `<pre>` (monoespaciado). Construimos una tabla ASCII alineada dentro de `<pre>`, troceada para no pasar de 4096 chars, con `<pre>` balanceado en cada trozo.

**Files:**
- Modify: `bot/propuestas.py`
- Modify: `tests/test_propuestas.py`

- [ ] **Step 1: Write the failing test (añadir al final)**

```python
class TestMensajes(unittest.TestCase):
    def test_un_mensaje_para_pocos_alumnos(self):
        msgs = propuestas.construir_mensajes(prop_ok())
        self.assertEqual(len(msgs), 1)
        self.assertIn("Ana López", msgs[0])
        self.assertIn("Práctica 2", msgs[0])
        self.assertTrue(msgs[0].count("<pre>") == msgs[0].count("</pre>") >= 1)

    def test_escapa_html_en_nombres(self):
        p = prop_ok(); p["alumnos"][0]["nombre"] = "A & <B>"
        msgs = propuestas.construir_mensajes(p)
        self.assertIn("A &amp; &lt;B&gt;", "".join(msgs))

    def test_trocea_y_respeta_limite_con_pre_balanceado(self):
        p = prop_ok()
        p["alumnos"] = [dict(alumno_ok(), nombre="Alumno %02d" % i) for i in range(60)]
        msgs = propuestas.construir_mensajes(p, limite=600)
        self.assertGreater(len(msgs), 1)
        for m in msgs:
            self.assertLessEqual(len(m), 600)
            self.assertEqual(m.count("<pre>"), m.count("</pre>"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_propuestas -v`
Expected: FAIL — `has no attribute 'construir_mensajes'`.

- [ ] **Step 3: Write minimal implementation (añadir a `bot/propuestas.py`)**

```python
NOMBRES_PRACTICA = {
    1: "Análisis de precios Idealista",
    2: "Boston Housing (OLS + Ridge + Lasso)",
    3: "Detección de fraude (regresión logística)",
}

def escapar_html(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _fila_ascii(al):
    c = al["criterios"]
    nombre = al["nombre"][:24].ljust(24)
    return "%s  %3s %3s %3s %3s  %4s" % (
        nombre, c["comprension"], c["aplicacion"],
        c["documentacion"], c["resolucion"], al["total"])

def construir_mensajes(prop, limite=4096):
    titulo = "<b>Práctica %s — %s</b>\n%d alumnos · estado: %s" % (
        prop["practica"], NOMBRES_PRACTICA.get(prop["practica"], ""),
        len(prop["alumnos"]), prop["estado"])
    cabecera = "%s  %3s %3s %3s %3s  %4s" % (
        "Alumno".ljust(24), "CT", "AP", "DO", "RP", "Tot")
    filas = [escapar_html(_fila_ascii(al)) for al in prop["alumnos"]]

    mensajes, bloque, primero = [], [], True
    def cerrar(bloque, primero):
        cuerpo = "<pre>" + "\n".join([escapar_html(cabecera)] + bloque) + "</pre>"
        return (titulo + "\n" + cuerpo) if primero else cuerpo

    for fila in filas:
        candidato = cerrar(bloque + [fila], primero)
        if len(candidato) > limite and bloque:
            mensajes.append(cerrar(bloque, primero)); primero = False; bloque = [fila]
        else:
            bloque.append(fila)
    if bloque:
        mensajes.append(cerrar(bloque, primero))
    return mensajes
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_propuestas -v`
Expected: PASS (10 tests).

- [ ] **Step 5: Commit**

```bash
git add bot/propuestas.py tests/test_propuestas.py
git commit -m "feat(bot): construir mensajes de tabla en <pre> troceado y escapado"
```

---

## Task 5: Cliente de la Telegram Bot API

**Files:**
- Create: `bot/telegram_api.py`
- Test: `tests/test_telegram_api.py`

- [ ] **Step 1: Write the failing test**

`tests/test_telegram_api.py`:
```python
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bot"))
import telegram_api

class FakeTransport:
    def __init__(self, respuestas):
        self.respuestas = respuestas
        self.llamadas = []
    def __call__(self, method, params):
        self.llamadas.append((method, params))
        return self.respuestas.get(method, {"ok": True, "result": []})

class TestTelegramClient(unittest.TestCase):
    def test_get_updates_devuelve_result(self):
        ft = FakeTransport({"getUpdates": {"ok": True, "result": [{"update_id": 5}]}})
        cli = telegram_api.TelegramClient("tok", transport=ft)
        ups = cli.get_updates(offset=3, timeout=10)
        self.assertEqual(ups, [{"update_id": 5}])
        metodo, params = ft.llamadas[0]
        self.assertEqual(metodo, "getUpdates")
        self.assertEqual(params["offset"], 3)

    def test_send_message_pasa_chat_y_markup(self):
        ft = FakeTransport({})
        cli = telegram_api.TelegramClient("tok", transport=ft)
        markup = telegram_api.teclado_aprobacion("2026-06-07-p2.json")
        cli.send_message(42, "hola", reply_markup=markup)
        metodo, params = ft.llamadas[0]
        self.assertEqual(metodo, "sendMessage")
        self.assertEqual(params["chat_id"], 42)
        self.assertEqual(params["parse_mode"], "HTML")
        self.assertIn("reply_markup", params)

    def test_teclado_aprobacion_callback_data(self):
        markup = telegram_api.teclado_aprobacion("2026-06-07-p2.json")
        botones = markup["inline_keyboard"][0]
        datas = [b["callback_data"] for b in botones]
        self.assertIn("aprobar:2026-06-07-p2.json", datas)
        self.assertIn("rechazar:2026-06-07-p2.json", datas)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_telegram_api -v`
Expected: FAIL — `No module named 'telegram_api'`.

- [ ] **Step 3: Write minimal implementation**

`bot/telegram_api.py`:
```python
import json
import urllib.request

def teclado_aprobacion(basename):
    return {"inline_keyboard": [[
        {"text": "✅ Aprobar", "callback_data": "aprobar:" + basename},
        {"text": "✏️ Rechazar", "callback_data": "rechazar:" + basename},
    ]]}

def _http_transport(token):
    base = "https://api.telegram.org/bot%s/" % token
    def transport(method, params):
        datos = json.dumps(params).encode("utf-8")
        req = urllib.request.Request(
            base + method, data=datos,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=params.get("timeout", 30) + 5) as r:
            return json.loads(r.read().decode("utf-8"))
    return transport

class TelegramClient:
    def __init__(self, token, transport=None):
        self.transport = transport or _http_transport(token)

    def get_updates(self, offset=None, timeout=25):
        params = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        return self.transport("getUpdates", params).get("result", [])

    def send_message(self, chat_id, text, parse_mode="HTML", reply_markup=None):
        params = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
        if reply_markup is not None:
            params["reply_markup"] = reply_markup
        return self.transport("sendMessage", params)

    def answer_callback(self, callback_id, text=None):
        params = {"callback_query_id": callback_id}
        if text:
            params["text"] = text
        return self.transport("answerCallbackQuery", params)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_telegram_api -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add bot/telegram_api.py tests/test_telegram_api.py
git commit -m "feat(bot): cliente Telegram API (urllib) con transport inyectable"
```

---

## Task 6: Dispatch — autorización y comandos

**Files:**
- Create: `bot/dispatch.py`
- Test: `tests/test_dispatch.py`

`ctx` es un objeto simple con: `tg` (TelegramClient), `chat_id` (autorizado), `propuestas_dir`, y `lanzar(args)` (callable que ejecuta un wrapper; inyectable para tests).

- [ ] **Step 1: Write the failing test**

`tests/test_dispatch.py`:
```python
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bot"))
import dispatch, telegram_api, propuestas

class FakeTG:
    def __init__(self):
        self.enviados = []
        self.callbacks_respondidos = []
    def send_message(self, chat_id, text, parse_mode="HTML", reply_markup=None):
        self.enviados.append({"chat_id": chat_id, "text": text, "markup": reply_markup})
    def answer_callback(self, cid, text=None):
        self.callbacks_respondidos.append((cid, text))

class Ctx:
    def __init__(self, propuestas_dir):
        self.tg = FakeTG()
        self.chat_id = 42
        self.propuestas_dir = propuestas_dir
        self.lanzado = []
        self.lanzar = lambda args: self.lanzado.append(args)

def update_texto(texto, chat_id=42):
    return {"update_id": 1, "message": {"chat": {"id": chat_id}, "text": texto}}

class TestAutorizacion(unittest.TestCase):
    def test_ignora_chat_no_autorizado(self):
        ctx = Ctx("/tmp")
        dispatch.manejar_update(update_texto("/estado", chat_id=999), ctx)
        self.assertEqual(ctx.tg.enviados, [])
        self.assertEqual(ctx.lanzado, [])

class TestComandos(unittest.TestCase):
    def test_corregir_lanza_wrapper_y_avisa(self):
        ctx = Ctx("/tmp")
        dispatch.manejar_update(update_texto("/corregir"), ctx)
        self.assertEqual(ctx.lanzado, [["correccion-diaria.sh"]])
        self.assertTrue(ctx.tg.enviados)  # acuse "corrigiendo..."

    def test_estado_sin_propuestas(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            ctx = Ctx(d)
            dispatch.manejar_update(update_texto("/estado"), ctx)
            self.assertIn("sin propuestas", ctx.tg.enviados[0]["text"].lower())

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_dispatch -v`
Expected: FAIL — `No module named 'dispatch'`.

- [ ] **Step 3: Write minimal implementation**

`bot/dispatch.py`:
```python
import os
import propuestas

WRAPPER_CORREGIR = "correccion-diaria.sh"

def _autorizado(update, chat_id):
    msg = update.get("message") or update.get("callback_query", {}).get("message")
    if not msg:
        return False
    return msg.get("chat", {}).get("id") == chat_id

def manejar_update(update, ctx):
    if not _autorizado(update, ctx.chat_id):
        return
    if "message" in update and "text" in update["message"]:
        _manejar_texto(update["message"]["text"].strip(), ctx)

def _manejar_texto(texto, ctx):
    if texto == "/corregir":
        ctx.lanzar([WRAPPER_CORREGIR])
        ctx.tg.send_message(ctx.chat_id, "🛠️ Corrigiendo, te aviso cuando tenga la propuesta…")
    elif texto == "/estado":
        ctx.tg.send_message(ctx.chat_id, _texto_estado(ctx.propuestas_dir))
    elif texto == "/pendientes":
        _repostear_pendientes(ctx)

def _texto_estado(propuestas_dir):
    pares = propuestas.listar(propuestas_dir)
    if not pares:
        return "Sin propuestas ahora mismo."
    lineas = ["<b>Estado</b>:"]
    for ruta, p in pares:
        lineas.append("• P%s (%s): %s" % (p["practica"], p["fecha"], p["estado"]))
    return "\n".join(lineas)

def _repostear_pendientes(ctx):
    import telegram_api
    pares = [(r, p) for r, p in propuestas.listar(ctx.propuestas_dir)
             if p["estado"] == "pendiente"]
    if not pares:
        ctx.tg.send_message(ctx.chat_id, "No hay propuestas pendientes.")
        return
    for ruta, p in pares:
        base = os.path.basename(ruta)
        msgs = propuestas.construir_mensajes(p)
        for i, m in enumerate(msgs):
            markup = telegram_api.teclado_aprobacion(base) if i == len(msgs) - 1 else None
            ctx.tg.send_message(ctx.chat_id, m, reply_markup=markup)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_dispatch -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add bot/dispatch.py tests/test_dispatch.py
git commit -m "feat(bot): dispatch de comandos (/corregir, /estado, /pendientes) con autorización"
```

---

## Task 7: Dispatch — callbacks Aprobar/Rechazar y flujo de edición

`callback_data`: `aprobar:<base>` / `rechazar:<base>`. Aprobar → marca `aprobada`, lanza `guardar-aprobadas.sh <base>`. Rechazar → marca `editando`, pide ajustes. El siguiente texto libre (no comando), si hay exactamente una propuesta `editando`, se escribe en `ajustes_pendientes` y se lanza `aplicar-edicion.sh <base>`.

**Files:**
- Modify: `bot/dispatch.py`
- Modify: `tests/test_dispatch.py`

- [ ] **Step 1: Write the failing test (añadir al final, antes de `if __name__`)**

```python
import tempfile, json

def alumno_ok():
    return {"nombre": "Ana", "grader_url": "u", "guardado": False,
            "criterios": {"comprension": 2, "aplicacion": 1.5, "documentacion": 2, "resolucion": 3},
            "total": 8.5, "comentario": "ok"}

def crear_prop(d, base="2026-06-07-p2.json", estado="pendiente"):
    p = {"practica": 2, "fecha": "2026-06-07", "estado": estado,
         "notificado": True, "alumnos": [alumno_ok()]}
    propuestas.guardar(p, os.path.join(d, base))
    return base

def update_callback(data, chat_id=42):
    return {"update_id": 2, "callback_query": {
        "id": "cb1", "data": data, "message": {"chat": {"id": chat_id}}}}

class TestCallbacks(unittest.TestCase):
    def test_aprobar_marca_y_lanza_guardado(self):
        with tempfile.TemporaryDirectory() as d:
            base = crear_prop(d)
            ctx = Ctx(d)
            dispatch.manejar_update(update_callback("aprobar:" + base), ctx)
            p = propuestas.cargar(os.path.join(d, base))
            self.assertEqual(p["estado"], "aprobada")
            self.assertEqual(ctx.lanzado, [["guardar-aprobadas.sh", base]])
            self.assertEqual(ctx.tg.callbacks_respondidos[0][0], "cb1")

    def test_aprobar_ya_guardada_no_relanza(self):
        with tempfile.TemporaryDirectory() as d:
            base = crear_prop(d, estado="guardada")
            ctx = Ctx(d)
            dispatch.manejar_update(update_callback("aprobar:" + base), ctx)
            self.assertEqual(ctx.lanzado, [])

    def test_rechazar_pone_editando_y_pide_ajustes(self):
        with tempfile.TemporaryDirectory() as d:
            base = crear_prop(d)
            ctx = Ctx(d)
            dispatch.manejar_update(update_callback("rechazar:" + base), ctx)
            p = propuestas.cargar(os.path.join(d, base))
            self.assertEqual(p["estado"], "editando")
            self.assertTrue(ctx.tg.enviados)

    def test_texto_libre_en_edicion_guarda_ajustes_y_lanza(self):
        with tempfile.TemporaryDirectory() as d:
            base = crear_prop(d, estado="editando")
            ctx = Ctx(d)
            dispatch.manejar_update(update_texto("Ana: aplicacion 0"), ctx)
            p = propuestas.cargar(os.path.join(d, base))
            self.assertEqual(p["ajustes_pendientes"], "Ana: aplicacion 0")
            self.assertEqual(ctx.lanzado, [["aplicar-edicion.sh", base]])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_dispatch -v`
Expected: FAIL — callbacks no manejados / atributos ausentes.

- [ ] **Step 3: Write minimal implementation**

En `bot/dispatch.py`, añadir constantes y ampliar `manejar_update` y `_manejar_texto`:
```python
WRAPPER_GUARDAR = "guardar-aprobadas.sh"
WRAPPER_EDITAR = "aplicar-edicion.sh"
```
Reemplazar el cuerpo de `manejar_update` por:
```python
def manejar_update(update, ctx):
    if not _autorizado(update, ctx.chat_id):
        return
    if "callback_query" in update:
        _manejar_callback(update["callback_query"], ctx)
    elif "message" in update and "text" in update["message"]:
        _manejar_texto(update["message"]["text"].strip(), ctx)
```
Añadir:
```python
def _manejar_callback(cb, ctx):
    accion, _, base = cb.get("data", "").partition(":")
    ruta = os.path.join(ctx.propuestas_dir, base)
    ctx.tg.answer_callback(cb["id"])
    if not os.path.exists(ruta):
        ctx.tg.send_message(ctx.chat_id, "Esa propuesta ya no existe.")
        return
    p = propuestas.cargar(ruta)
    if accion == "aprobar":
        if p["estado"] in ("guardada", "aprobada"):
            ctx.tg.send_message(ctx.chat_id, "P%s ya estaba %s." % (p["practica"], p["estado"]))
            return
        p["estado"] = "aprobada"; propuestas.guardar(p, ruta)
        ctx.lanzar([WRAPPER_GUARDAR, base])
        ctx.tg.send_message(ctx.chat_id, "✅ Guardando P%s en Moodle…" % p["practica"])
    elif accion == "rechazar":
        p["estado"] = "editando"; propuestas.guardar(p, ruta)
        ctx.tg.send_message(
            ctx.chat_id,
            "✏️ P%s en edición. Mándame los ajustes en un mensaje "
            "(ej. «Ana: aplicacion 0»)." % p["practica"])
```
Y al final de `_manejar_texto`, antes de cerrar la función, añadir una rama `else` para texto libre:
```python
    else:
        _intentar_edicion(texto, ctx)

def _intentar_edicion(texto, ctx):
    editando = [(r, p) for r, p in propuestas.listar(ctx.propuestas_dir)
                if p["estado"] == "editando"]
    if len(editando) == 1:
        ruta, p = editando[0]
        p["ajustes_pendientes"] = texto
        propuestas.guardar(p, ruta)
        ctx.lanzar([WRAPPER_EDITAR, os.path.basename(ruta)])
        ctx.tg.send_message(ctx.chat_id, "🔁 Aplicando ajustes a P%s…" % p["practica"])
    elif len(editando) > 1:
        ctx.tg.send_message(ctx.chat_id, "Hay varias propuestas en edición; usa /pendientes.")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_dispatch -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add bot/dispatch.py tests/test_dispatch.py
git commit -m "feat(bot): callbacks aprobar/rechazar y flujo de edición por texto libre"
```

---

## Task 8: Watcher — postear propuestas pendientes no notificadas

**Files:**
- Modify: `bot/dispatch.py`
- Modify: `tests/test_dispatch.py`

- [ ] **Step 1: Write the failing test (añadir al final)**

```python
class TestWatcher(unittest.TestCase):
    def test_postea_pendiente_no_notificada_y_marca(self):
        with tempfile.TemporaryDirectory() as d:
            p = {"practica": 2, "fecha": "2026-06-07", "estado": "pendiente",
                 "notificado": False, "alumnos": [alumno_ok()]}
            base = "2026-06-07-p2.json"
            propuestas.guardar(p, os.path.join(d, base))
            ctx = Ctx(d)
            dispatch.revisar_pendientes(ctx)
            self.assertTrue(ctx.tg.enviados)
            self.assertTrue(propuestas.cargar(os.path.join(d, base))["notificado"])

    def test_no_repostea_si_ya_notificada(self):
        with tempfile.TemporaryDirectory() as d:
            p = {"practica": 2, "fecha": "2026-06-07", "estado": "pendiente",
                 "notificado": True, "alumnos": [alumno_ok()]}
            propuestas.guardar(p, os.path.join(d, "2026-06-07-p2.json"))
            ctx = Ctx(d)
            dispatch.revisar_pendientes(ctx)
            self.assertEqual(ctx.tg.enviados, [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_dispatch -v`
Expected: FAIL — `module 'dispatch' has no attribute 'revisar_pendientes'`.

- [ ] **Step 3: Write minimal implementation (añadir a `bot/dispatch.py`)**

```python
import telegram_api

def revisar_pendientes(ctx):
    for ruta, p in propuestas.listar(ctx.propuestas_dir):
        if p["estado"] == "pendiente" and not p.get("notificado"):
            base = os.path.basename(ruta)
            msgs = propuestas.construir_mensajes(p)
            for i, m in enumerate(msgs):
                markup = telegram_api.teclado_aprobacion(base) if i == len(msgs) - 1 else None
                ctx.tg.send_message(ctx.chat_id, m, reply_markup=markup)
            p["notificado"] = True
            propuestas.guardar(p, ruta)
```

Nota: mover el `import telegram_api` local de `_repostear_pendientes` a este import de módulo (DRY); dejar uno solo arriba.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_dispatch -v`
Expected: PASS (9 tests).

- [ ] **Step 5: Commit**

```bash
git add bot/dispatch.py tests/test_dispatch.py
git commit -m "feat(bot): watcher que postea propuestas pendientes no notificadas"
```

---

## Task 9: Entrypoint del daemon (bucle + pidfile)

No es unit-testeable (I/O real); se valida arrancándolo. Mantenerlo fino.

**Files:**
- Create: `bot/bot-telegram.py`

- [ ] **Step 1: Escribir el entrypoint**

`bot/bot-telegram.py`:
```python
#!/usr/bin/env python3
"""Daemon del bot de Telegram para aprobar correcciones. Solo stdlib."""
import os, sys, time, subprocess

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import config, dispatch, telegram_api  # noqa: E402

PROYECTO = os.path.dirname(AQUI)
PIDFILE = os.path.join(AQUI, "bot.pid")

class Ctx:
    def __init__(self, cfg, tg):
        self.tg = tg
        self.chat_id = cfg.chat_id
        self.propuestas_dir = cfg.propuestas_dir
    def lanzar(self, args):
        # args[0] es el nombre del wrapper en la raíz del proyecto
        ruta = os.path.join(PROYECTO, args[0])
        subprocess.Popen(["bash", ruta] + args[1:], cwd=PROYECTO)

def _ya_corriendo():
    if not os.path.exists(PIDFILE):
        return False
    try:
        with open(PIDFILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False

def main():
    if _ya_corriendo():
        print("Bot ya en marcha; salgo.")
        return
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))
    cfg = config.load_config(PROYECTO)
    tg = telegram_api.TelegramClient(cfg.token)
    ctx = Ctx(cfg, tg)
    offset = None
    print("Bot arrancado. Escuchando…")
    try:
        while True:
            try:
                updates = tg.get_updates(offset=offset, timeout=25)
                for up in updates:
                    offset = up["update_id"] + 1
                    dispatch.manejar_update(up, ctx)
                dispatch.revisar_pendientes(ctx)
            except Exception as e:  # noqa: BLE001 — el daemon no debe morir por un fallo puntual
                print("ERROR en bucle:", e, file=sys.stderr)
                time.sleep(5)
    finally:
        if os.path.exists(PIDFILE):
            os.remove(PIDFILE)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verificación de arranque (sin credenciales reales todavía)**

Run: `python3 -c "import ast; ast.parse(open('bot/bot-telegram.py').read()); print('sintaxis OK')"`
Expected: `sintaxis OK`

- [ ] **Step 3: Verificar suite completa sigue verde**

Run: `python3 -m unittest discover -s tests -t . -v`
Expected: PASS (todos).

- [ ] **Step 4: Commit**

```bash
git add bot/bot-telegram.py
git commit -m "feat(bot): entrypoint daemon (long-polling + watcher + pidfile)"
```

---

## Task 10: Script de arranque del bot (`iniciar-bot.sh`)

**Files:**
- Create: `iniciar-bot.sh`

- [ ] **Step 1: Escribir el script**

`iniciar-bot.sh`:
```bash
#!/usr/bin/env bash
# Arranca el daemon del bot de Telegram si no está vivo. Idempotente (pidfile).
# Lo llaman el @reboot del cron y el wrapper de Fase 1.
set -uo pipefail
export PATH="/home/framorhid/.nvm/versions/node/v24.16.0/bin:/usr/bin:/bin"
PROYECTO="/home/framorhid/proyectos/master-regresiones"
PIDFILE="$PROYECTO/bot/bot.pid"
LOG="$HOME/bot-telegram.log"

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "[$(date '+%F %T')] Bot ya vivo (pid $(cat "$PIDFILE"))." >> "$LOG"
  exit 0
fi

echo "[$(date '+%F %T')] Arrancando bot…" >> "$LOG"
cd "$PROYECTO" || exit 1
nohup python3 "$PROYECTO/bot/bot-telegram.py" >> "$LOG" 2>&1 &
echo "[$(date '+%F %T')] Bot lanzado (pid $!)." >> "$LOG"
```

- [ ] **Step 2: Hacerlo ejecutable y comprobar sintaxis**

Run: `chmod +x iniciar-bot.sh && bash -n iniciar-bot.sh && echo "shell OK"`
Expected: `shell OK`

- [ ] **Step 3: Commit**

```bash
git add iniciar-bot.sh
git commit -m "feat(bot): script idempotente de arranque del daemon"
```

---

## Task 11: Wrapper de Fase 2 (`guardar-aprobadas.sh`) y edición (`aplicar-edicion.sh`)

**Files:**
- Create: `guardar-aprobadas.sh`
- Create: `aplicar-edicion.sh`

- [ ] **Step 1: Escribir `guardar-aprobadas.sh`**

Reutiliza el patrón de `correccion-diaria.sh` (PATH de cron, `.env`, Chrome en :9222). Recibe el basename del JSON aprobado.

`guardar-aprobadas.sh`:
```bash
#!/usr/bin/env bash
# Fase 2: guarda en Moodle las notas YA APROBADAS de una práctica.
# Uso: guardar-aprobadas.sh <basename.json>   (lo invoca el bot)
set -uo pipefail
export PATH="/home/framorhid/.nvm/versions/node/v24.16.0/bin:/home/framorhid/.local/bin:/usr/bin:/bin"
PROYECTO="/home/framorhid/proyectos/master-regresiones"
LOG="$HOME/guardado-$(date +%F).log"
BASE="${1:?Falta el basename del JSON de propuestas}"

export CORRECCION_DESATENDIDA=1
if [ -f "$PROYECTO/.env" ]; then
  set -a; . "$PROYECTO/.env"; set +a
else
  echo "[$(date '+%T')] ERROR: falta .env. Abortando." >> "$LOG"; exit 1
fi

# Chrome en :9222 (igual que el wrapper de Fase 1)
if ! curl -s http://localhost:9222/json/version >/dev/null 2>&1; then
  google-chrome --remote-debugging-port=9222 \
    --user-data-dir=/home/framorhid/.chrome-moodle \
    --no-first-run --no-default-browser-check --no-sandbox >/dev/null 2>&1 &
  for i in $(seq 1 30); do
    curl -s http://localhost:9222/json/version >/dev/null 2>&1 && break; sleep 1
  done
fi
if ! curl -s http://localhost:9222/json/version >/dev/null 2>&1; then
  echo "[$(date '+%T')] ERROR: Chrome no responde en :9222." >> "$LOG"; exit 1
fi

echo "===== [$(date '+%F %T')] Guardar aprobadas: $BASE =====" >> "$LOG"
cd "$PROYECTO" || exit 1
/home/framorhid/.local/bin/claude -p \
  "Modo desatendido, modo guardar: guarda en Moodle las notas aprobadas del archivo propuestas/$BASE" \
  >> "$LOG" 2>&1
echo "===== [$(date '+%F %T')] Fin guardado (exit $?) =====" >> "$LOG"
```

- [ ] **Step 2: Escribir `aplicar-edicion.sh`**

`aplicar-edicion.sh`:
```bash
#!/usr/bin/env bash
# Aplica los ajustes en lenguaje natural (campo ajustes_pendientes) de un JSON de propuestas.
# Uso: aplicar-edicion.sh <basename.json>   (lo invoca el bot)
set -uo pipefail
export PATH="/home/framorhid/.nvm/versions/node/v24.16.0/bin:/home/framorhid/.local/bin:/usr/bin:/bin"
PROYECTO="/home/framorhid/proyectos/master-regresiones"
LOG="$HOME/edicion-$(date +%F).log"
BASE="${1:?Falta el basename del JSON}"

export CORRECCION_DESATENDIDA=1
[ -f "$PROYECTO/.env" ] && { set -a; . "$PROYECTO/.env"; set +a; }

echo "===== [$(date '+%F %T')] Editar: $BASE =====" >> "$LOG"
cd "$PROYECTO" || exit 1
/home/framorhid/.local/bin/claude -p \
  "Modo desatendido, modo edición: aplica los ajustes del campo ajustes_pendientes de propuestas/$BASE" \
  >> "$LOG" 2>&1
echo "===== [$(date '+%F %T')] Fin edición (exit $?) =====" >> "$LOG"
```

- [ ] **Step 3: Permisos y sintaxis**

Run: `chmod +x guardar-aprobadas.sh aplicar-edicion.sh && bash -n guardar-aprobadas.sh && bash -n aplicar-edicion.sh && echo "shell OK"`
Expected: `shell OK`

- [ ] **Step 4: Commit**

```bash
git add guardar-aprobadas.sh aplicar-edicion.sh
git commit -m "feat(bot): wrappers de Fase 2 (guardar) y de aplicación de ediciones"
```

---

## Task 12: Modificar `correccion-diaria.sh` (Fase 1 = proponer + resucitar bot)

**Files:**
- Modify: `correccion-diaria.sh`

- [ ] **Step 1: Cambiar el prompt de claude a "modo proponer"**

Localizar el bloque (al final del archivo):
```bash
/home/framorhid/.local/bin/claude -p "Corrige las prácticas pendientes en modo desatendido" \
  >> "$LOG" 2>&1
```
Reemplazarlo por:
```bash
/home/framorhid/.local/bin/claude -p "Corrige las prácticas pendientes en modo desatendido, modo proponer" \
  >> "$LOG" 2>&1
```

- [ ] **Step 2: Resucitar el bot antes de la Fase 1**

Justo después de la línea `export CORRECCION_DESATENDIDA=1` (y antes de cargar `.env`), añadir:
```bash
# Asegura que el bot de Telegram está vivo para postear las propuestas
bash /home/framorhid/proyectos/master-regresiones/iniciar-bot.sh
```

- [ ] **Step 3: Comprobar sintaxis**

Run: `bash -n correccion-diaria.sh && echo "shell OK"`
Expected: `shell OK`

- [ ] **Step 4: Commit**

```bash
git add correccion-diaria.sh
git commit -m "feat(bot): Fase 1 pasa a modo proponer y resucita el bot"
```

---

## Task 13: Modificar `skills/corregir-practicas/SKILL.md` (modos proponer/guardar/edición)

Cambios de prosa para que la skill maestra entienda los tres modos y capture `grader_url`.

**Files:**
- Modify: `skills/corregir-practicas/SKILL.md`

- [ ] **Step 1: Añadir sección de modos tras el bloque MODO DESATENDIDO**

Insertar tras el override 7 (línea ~89, antes de `## FASE 1`) este bloque:
```markdown
## SUB-MODOS (proponer / guardar / edición)

Dentro del modo desatendido, la petición indica un sub-modo. **Por defecto, "modo proponer".**

### Modo proponer (Fase 1) — NO guardar en Moodle
Ejecuta las FASES 1–3 **pero no pulses "Guardar"**. Para cada alumno corregido, en vez de guardar,
acumula su evaluación y, al terminar cada práctica, **escribe** `propuestas/<fecha>-p<N>.json`
(crea la carpeta con `Bash(mkdir -p propuestas)`) con esta forma exacta:

​```json
{ "practica": N, "fecha": "AAAA-MM-DD", "estado": "pendiente", "notificado": false,
  "alumnos": [ { "nombre": "...", "grader_url": "<URL del grader con &userid=...>",
    "criterios": {"comprension": C, "aplicacion": A, "documentacion": D, "resolucion": R},
    "total": T, "comentario": "...", "guardado": false } ] }
​```
- `grader_url`: la URL actual del grader del alumno (incluye `&userid=`), para poder volver luego.
- Valores válidos: comprension∈{0,1,2}, aplicacion∈{0,1.5,3}, documentacion∈{0,1,2}, resolucion∈{0,1.5,3}; `total` = suma.
- NO crees borrador de Gmail en este modo. NO toques la rúbrica de Moodle. Solo lees y evalúas.
- Si no hay pendientes (override 4), no escribas JSON y termina limpio.

### Modo guardar (Fase 2) — escribir en Moodle lo ya aprobado
La petición indica el archivo `propuestas/<base>.json`. Léelo con Read. Para cada alumno con
`guardado:false`: navega a su `grader_url`, fija el filtro "Requiere calificación" si hace falta,
rellena la rúbrica con sus `criterios` y el comentario global con `comentario`, y **guarda**
("Guardar cambios"). Marca ese alumno `guardado:true` y vuelve a escribir el JSON tras cada uno
(para que un fallo a mitad sea reintentable). Cuando todos estén `guardado:true`, pon
`estado:"guardada"`. Al final, crea el **borrador de Gmail (FASE 4)** con lo realmente guardado.
Si un alumno falla, regístralo, déjalo `guardado:false` y sigue con el resto.

### Modo edición — aplicar ajustes en lenguaje natural
La petición indica `propuestas/<base>.json`. Léelo: el campo `ajustes_pendientes` contiene
instrucciones en español (p. ej. «Ana: aplicación 0; sube documentación a 2»). Aplícalas a los
`criterios`/`comentario` de los alumnos indicados, **recalcula `total`**, borra el campo
`ajustes_pendientes`, pon `estado:"pendiente"` y `notificado:false`, y guarda el JSON. No toques Moodle.
```

- [ ] **Step 2: Ajustar FASE 3.3 para el modo proponer**

En la sección `### 3.3` (modo desatendido), añadir una frase:
```markdown
- **Modo proponer:** NO guardes en Moodle; acumula la evaluación y vuelca el JSON al terminar la
  práctica (ver SUB-MODOS). El guardado real ocurre en el modo guardar, tras la aprobación humana.
```

- [ ] **Step 3: Verificación (lectura)**

Run: `grep -n "SUB-MODOS\|Modo proponer\|Modo guardar\|Modo edición" skills/corregir-practicas/SKILL.md`
Expected: aparecen las 4 cabeceras añadidas.

- [ ] **Step 4: Commit**

```bash
git add skills/corregir-practicas/SKILL.md
git commit -m "feat(bot): sub-modos proponer/guardar/edición en la skill maestra"
```

---

## Task 14: Config de entorno, gitignore y allowlist

**Files:**
- Modify: `.env.example`
- Modify: `.gitignore`
- Modify: `.claude/settings.local.json`

- [ ] **Step 1: Documentar variables en `.env.example`**

Añadir al final de `.env.example`:
```bash
# --- Bot de Telegram ---
# Token que te da @BotFather al crear el bot:
TELEGRAM_BOT_TOKEN=<TOKEN_DE_BOTFATHER>
# Tu chat_id (el bot solo responde a este). Obtenlo escribiendo al bot y mirando
# https://api.telegram.org/bot<TOKEN>/getUpdates -> message.chat.id
TELEGRAM_CHAT_ID=<TU_CHAT_ID>
```

- [ ] **Step 2: Ignorar artefactos sensibles**

Añadir a `.gitignore`:
```gitignore
propuestas/
bot/bot.pid
```

Verificar que `.env` ya está ignorado:
Run: `git check-ignore .env propuestas/ bot/bot.pid`
Expected: las tres rutas listadas.

- [ ] **Step 3: Ampliar la allowlist para la Fase 2/edición**

En `.claude/settings.local.json`, dentro de `permissions.allow`, añadir (si no están):
```json
"Read(//home/framorhid/proyectos/master-regresiones/propuestas/**)",
"Write(//home/framorhid/proyectos/master-regresiones/propuestas/**)",
"Bash(mkdir -p propuestas)"
```
Leer el archivo primero para respetar el formato existente; las MCP de Chrome y `Bash(python3 *)`
ya están permitidas y las reutiliza la Fase 2.

- [ ] **Step 4: Commit**

```bash
git add .env.example .gitignore .claude/settings.local.json
git commit -m "chore(bot): variables Telegram en .env.example, gitignore y allowlist de propuestas"
```

---

## Task 15: Programar el bot en `@reboot` (cron)

**Files:** crontab del usuario (no versionado).

- [ ] **Step 1: Añadir la línea `@reboot`**

Run: `(crontab -l 2>/dev/null; echo '@reboot /home/framorhid/proyectos/master-regresiones/iniciar-bot.sh') | crontab -`

- [ ] **Step 2: Verificar**

Run: `crontab -l | grep iniciar-bot`
Expected: aparece la línea `@reboot ... iniciar-bot.sh`.

(No hay commit: el crontab no está en el repo. Anotarlo en AUTOMATIZACION.md en la Task 16.)

---

## Task 16: Documentación operativa

**Files:**
- Modify: `AUTOMATIZACION.md`
- Modify: `PROXIMOS-PASOS.md`

- [ ] **Step 1: Documentar el flujo del bot en AUTOMATIZACION.md**

Añadir una sección "## Bot de Telegram (puerta de aprobación)" que describa: las dos fases, los
scripts (`iniciar-bot.sh`, `guardar-aprobadas.sh`, `aplicar-edicion.sh`), el `@reboot`, los comandos
(`/corregir`, `/estado`, `/pendientes`) y la nota de que el cron de las 8:00 ya **no** guarda solo
(Fase 1 propone; el guardado real es tras el OK por Telegram).

- [ ] **Step 2: Actualizar PROXIMOS-PASOS.md**

Marcar el bot como hecho y dejar como pendiente la prueba end-to-end real (Task 17).

- [ ] **Step 3: Commit**

```bash
git add AUTOMATIZACION.md PROXIMOS-PASOS.md
git commit -m "docs(bot): flujo de Telegram, scripts y comandos en la documentación operativa"
```

---

## Task 17: Verificación end-to-end (manual, con credenciales reales)

Requiere: bot creado en @BotFather, `.env` con `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`, Chrome en
:9222 y al menos una entrega de prueba pendiente en Moodle.

- [ ] **Step 1: Suite verde**

Run: `python3 -m unittest discover -s tests -t . -v`
Expected: todos PASS.

- [ ] **Step 2: Arrancar el bot y confirmar conexión**

Run: `bash iniciar-bot.sh && sleep 2 && tail -n 5 ~/bot-telegram.log`
Expected: "Bot arrancado. Escuchando…" sin errores de token.

- [ ] **Step 3: Probar comandos básicos desde Telegram**

Desde tu Telegram, enviar `/estado` → debe responder "Sin propuestas ahora mismo." (o el estado real).
Enviar desde otra cuenta (o chat_id distinto) cualquier cosa → el bot **no** responde.

- [ ] **Step 4: Fase 1 → propuesta**

Run: `bash correccion-diaria.sh && tail -n 30 ~/correccion-$(date +%F).log`
Expected: se crea `propuestas/<fecha>-pN.json` con `estado:pendiente`; en pocos segundos llega a
Telegram la tabla de la práctica con botones ✅/✏️.

- [ ] **Step 5: Aprobar → guardado en Moodle**

Pulsar ✅ Aprobar. Verificar: el bot responde "Guardando…"; el JSON pasa a `estado:guardada` con
`guardado:true`; la nota aparece en Moodle; se crea el borrador en Gmail.
Run (comprobación del JSON): `cat propuestas/*p*.json | python3 -m json.tool | grep -E 'estado|guardado'`

- [ ] **Step 6: Rechazo + edición**

En otra práctica pendiente: pulsar ✏️ Rechazar → mandar «<Alumno>: aplicación 0» → verificar que el
JSON cambia (total recalculado), vuelve a `estado:pendiente` y reaparece la tabla para reaprobar.

- [ ] **Step 7: Limpieza**

Borrar las propuestas de prueba: `rm -f propuestas/*.json` (no se versionan).

---

## Self-review (cobertura del spec)

- Confirmación antes de guardar → Tasks 11–13 (proponer no guarda; guardar es post-aprobación). ✔
- Granularidad por práctica → un JSON por práctica, botones por práctica (Tasks 4,7,8). ✔
- Disparo cron + `/corregir` → Tasks 12 (cron) y 6 (`/corregir`). ✔
- Rechazo con edición en texto libre → Task 7 + modo edición Task 13. ✔
- Bot solo stdlib, sin pip → Tasks 1–9 (urllib/json/unittest). ✔
- Seguridad: solo chat_id autorizado, token en .env, propuestas gitignored → Tasks 6,14. ✔
- Always-on: pidfile + @reboot + resucitar en wrapper → Tasks 9,10,12,15. ✔
- Casos límite: sin pendientes (override 4 + watcher no postea), mensaje largo (Task 4), doble
  aprobación (Task 7), fallo parcial Fase 2 (guardado por alumno, Tasks 11,13). ✔
- Gmail al final de Fase 2 → Task 13 modo guardar. ✔
