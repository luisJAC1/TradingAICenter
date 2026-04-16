"""
config_manager.py
Manages all persistent config for Jarvis:
  - %APPDATA%\Jarvis\config.json  (API key, app path, etc.)
  - %APPDATA%\Jarvis\saludos.txt  (greeting lines, UTF-8)
"""

import os
import json

APPDATA = os.environ.get("APPDATA", os.path.expanduser("~"))
JARVIS_DIR = os.path.join(APPDATA, "Jarvis")
CONFIG_FILE = os.path.join(JARVIS_DIR, "config.json")
SALUDOS_FILE = os.path.join(JARVIS_DIR, "saludos.txt")

DEFAULT_SALUDOS = """\
# Jarvis Greetings -- edita este archivo con Notepad para agregar tus propios saludos.
# Las lineas que empiezan con # son comentarios y seran ignoradas.
# Una frase por linea.

Que tal Nicolas, aqui a tu servicio, empecemos modo bestia
Bienvenido hijo de puta, es hora de comer pan y comer culo y ya se nos acabo el pan
Hola nicocado avocado, es momento de brillar
Hola amiguito, bienvenido, en que te puedo ayudar?
Sistemas en linea, listo para dominar el mundo contigo
De vuelta en accion, que necesitas hoy campeon?
Encendido y listo, dime que hacemos
"""

DEFAULT_CONFIG = {
    "gemini_api_key": "",
    "app_path": "",
    "song_path": "",
    "language": "es-ES",
    "startup_enabled": True,
    "first_run_done": False,
}


class ConfigManager:
    def __init__(self):
        os.makedirs(JARVIS_DIR, exist_ok=True)
        self._cfg = {}
        self._load()

    def is_first_run(self):
        return not self._cfg.get("first_run_done", False)

    def get(self, key, default=None):
        return self._cfg.get(key, default)

    def set(self, key, value):
        self._cfg[key] = value
        self._save()

    def mark_setup_done(self):
        self._cfg["first_run_done"] = True
        self._save()

    def ensure_saludos(self):
        if not os.path.exists(SALUDOS_FILE):
            with open(SALUDOS_FILE, "w", encoding="utf-8") as f:
                f.write(DEFAULT_SALUDOS)

    def get_saludos(self):
        self.ensure_saludos()
        try:
            with open(SALUDOS_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            phrases = [
                ln.strip()
                for ln in lines
                if ln.strip() and not ln.strip().startswith("#")
            ]
            return phrases if phrases else ["Listo para servirte"]
        except Exception:
            return ["Listo para servirte"]

    @property
    def saludos_path(self):
        return SALUDOS_FILE

    @property
    def jarvis_dir(self):
        return JARVIS_DIR

    @property
    def config_file(self):
        return CONFIG_FILE

    def _load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self._cfg = json.load(f)
                for k, v in DEFAULT_CONFIG.items():
                    self._cfg.setdefault(k, v)
                return
            except Exception:
                pass
        self._cfg = dict(DEFAULT_CONFIG)

    def _save(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self._cfg, f, indent=2, ensure_ascii=False)
