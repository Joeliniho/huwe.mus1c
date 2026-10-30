"""Idioma de la app: inglés por defecto, español opcional. Uso: L("Hola", "Hello")."""
import json
import os
from pathlib import Path

CARPETA = Path(os.environ.get("APPDATA", Path.home())) / "huwe.mus1c"
CONFIG = CARPETA / "config.json"


def leer_config():
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception:
        return {}


def guardar_config(**cambios):
    cfg = leer_config()
    cfg.update(cambios)
    CARPETA.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


ACTUAL = leer_config().get("idioma", "en")


def L(es, en):
    return es if ACTUAL == "es" else en
