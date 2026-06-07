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
