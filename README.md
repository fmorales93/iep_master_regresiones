# Máster IA Estratégica — Corrección Automática de Prácticas

Corrige automáticamente las prácticas pendientes del curso *"Inteligencia Artificial Estratégica"*
(Red Summa Education) en Moodle: hace login, detecta entregas sin calificar, las puntúa con la
rúbrica, rellena la nota y el feedback en Moodle, y deja un **borrador de resumen en Gmail** para
que lo revises antes de darlo por bueno.

- Moodle: `aulavirtual.redsummaeducation.net`
- Funciona de dos formas: **a mano** (le hablas a Claude Code) o **automático** (cron diario).

---

## Puesta en marcha (una sola vez)

1. **Credenciales** — copia la plantilla y rellena tus datos de Moodle:
   ```bash
   cp .env.example .env
   # edita .env con tu usuario y contraseña reales
   ```
   El archivo `.env` no se versiona. Contiene `MOODLE_LOGIN_URL`, `MOODLE_USER`, `MOODLE_PASSWORD`.

2. **Chrome de WSL** — el flujo usa el Chrome de WSL con depuración remota en el puerto `9222`.
   Normalmente se arranca solo (hook de sesión / wrapper). Para lanzarlo a mano:
   ```bash
   google-chrome --remote-debugging-port=9222 --user-data-dir=/home/framorhid/.chrome-moodle \
     --no-first-run --no-default-browser-check --no-sandbox &
   ```

---

## Uso A — A mano (interactivo)

Abre Claude Code en la carpeta del proyecto y di cualquiera de estas frases:

- **"Corrige las prácticas pendientes"**
- "Empieza a corregir"
- "Hay trabajos para corregir"

Claude hace todo el proceso y te enseña un resumen de cada corrección. Las notas se guardan en
Moodle y se crea el borrador en Gmail. Tú revisas y das el visto bueno.

---

## Uso B — Automático (cron diario)

Ya está montado. Se ejecuta **todos los días a las 8:00** mediante:

- Wrapper: `/home/framorhid/correccion-diaria.sh`
- Cron: `0 8 * * * /home/framorhid/correccion-diaria.sh`
- Logs: `~/correccion-AAAA-MM-DD.log`

> **Importante (WSL):** el cron solo se dispara si el PC y WSL están encendidos a esa hora.

### Lanzarlo a mano cuando quieras (sin esperar a las 8:00)
```bash
bash /home/framorhid/correccion-diaria.sh
tail -n 40 ~/correccion-$(date +%F).log
```

### Cambiar la hora
```bash
crontab -e        # edita la línea 0 8 * * *
crontab -l        # ver el cron actual
```

### Revisar el resultado
- Mira el **borrador en Gmail** (`franmorales93@gmail.com`) con la tabla de notas.
- Revisa el **log** del día en `~/correccion-AAAA-MM-DD.log`.
- Si no había nada que corregir, el log dirá `Sin pendientes` y no crea borrador (es normal).

---

## Qué corrige

| Práctica | Tema |
|----------|------|
| 1 | Análisis de precios Idealista — regresión lineal + ANOVA |
| 2 | Boston Housing — OLS + Ridge + Lasso |
| 3 | Detección de fraude — regresión logística |

Rúbrica de 10 puntos (Comprensión Técnica, Aplicación Práctica, Documentación, Resolución de
Problemas). La corrección **nunca envía** notas por sí sola: deja un borrador para tu revisión.

---

## Archivos del proyecto

| Archivo | Para qué |
|---------|----------|
| `.env` / `.env.example` | Tus credenciales de Moodle (copia el example a `.env`) |
| `skills/corregir-practicas/SKILL.md` | El flujo maestro (login → detección → corrección → Gmail) |
| `skills/correccion-practica{1,2,3}/SKILL.md` | Rúbrica y criterios de cada práctica |
| `/home/framorhid/correccion-diaria.sh` | Wrapper que lanza el cron |
| `AUTOMATIZACION.md` | Plan de automatización (cron local + futuro NAS) y detalles técnicos |
| `PROXIMOS-PASOS.md` | Lista viva de lo que queda por hacer |

---

## Si algo falla

- **No corrige / login falla**: revisa que `.env` tiene las credenciales correctas y que el Chrome
  de `:9222` está vivo (`curl -s http://localhost:9222/json/version`).
- **El cron no se ejecuta**: comprueba que WSL estaba encendido a las 8:00 y que el demonio cron
  corre (`pgrep -x cron`).
- **Detalle y problemas conocidos**: ver `AUTOMATIZACION.md`.
