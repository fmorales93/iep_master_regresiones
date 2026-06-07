# Próximos pasos

Lista viva de lo que queda por hacer. Detalle ampliado en [AUTOMATIZACION.md](AUTOMATIZACION.md).
Estado a 2026-06-06.

---

## 1. Conectar `.env` con el flujo desatendido — ✅ HECHO (2026-06-06)

- [x] El wrapper hace `set -a; . "$PROYECTO/.env"; set +a` y aborta si falta `.env`.
- [x] La FASE 1.1 del SKILL lee las credenciales con `printenv` (desatendido) y, si están vacías, del archivo `.env` con Read (interactivo).
- [x] Allowlist ampliada: `Bash(printenv MOODLE_*)` y `Read(.../.env)`.
- [ ] **Falta**: confirmar una corrida desatendida real completa con login OK tras el cambio (validación en la FASE A).

## 2. Validar la FASE A (cron local) ~1 semana

- [ ] Dejar correr el cron de las 8:00 unos días con el PC/WSL encendido.
- [ ] Revisar cada día `~/correccion-AAAA-MM-DD.log` y el borrador en Gmail.
- [ ] Criterios OK: nota guardada en Moodle, borrador creado, `Sin pendientes` cuando no hay nada, nunca se queda colgado.
- [ ] Prueba manual cuando quieras: `bash /home/framorhid/correccion-diaria.sh && tail -n 40 ~/correccion-$(date +%F).log`.

## 3. Corrección de la práctica final (aplazado)

- [ ] Crear `skills/correccion-practica-final/SKILL.md` con su rúbrica/criterios.
- [ ] Ampliar la **FASE 2** del master (hoy el detector solo busca "Caso Práctico 1/2/3") y el enrutado de la **FASE 3.2** para la nueva práctica.

## 4. FASE B — Migración al NAS UGREEN

- [ ] Contenedor Docker: Node + Claude Code + **Chromium headless** (`--headless=new`).
- [ ] Volúmenes persistentes: perfil `.chrome-moodle`, `~/.claude` (auth), `.env`, `.descargas`.
- [ ] Cron del NAS (siempre encendido) en lugar del de WSL.
- [ ] Detalle y riesgos en `AUTOMATIZACION.md` (FASE B).

## Higiene

- [ ] Si el proyecto pasa a ser repo git, añadir `.gitignore` con `.env` (versionar solo `.env.example`). Ahora no es repo git.
