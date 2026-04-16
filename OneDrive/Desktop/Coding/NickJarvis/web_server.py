"""
web_server.py
Local Flask server that:
  - Serves the static HUD web app (index.html / style.css / app.js)
  - Exposes JSON endpoints used by the web UI
  - Proxies Gemini API calls so the key stays server-side
"""

import os
import sys
import random
import subprocess
import threading

import requests
from flask import Flask, jsonify, request, send_from_directory

PORT = 5000
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-1.5-flash:generateContent?key={key}"
)
SYSTEM_PROMPT = (
    "You are J.A.R.V.I.S, a witty, concise, and helpful AI assistant. "
    "Respond in the same language the user writes in. "
    "Keep responses short unless the user asks for detail."
)


def _resource_path(relative: str) -> str:
    """Resolve path to a bundled asset (works both dev and PyInstaller)."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.abspath("."), relative)


class WebServer:
    def __init__(self, config):
        self._config = config
        self._last_greeting: str = ""
        self._app = Flask(__name__)
        self._register_routes()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def run(self):
        """Block. Call from a daemon thread."""
        self._app.run(
            host="127.0.0.1",
            port=PORT,
            debug=False,
            use_reloader=False,
            threaded=True,
        )

    # ------------------------------------------------------------------ #
    #  Routes                                                              #
    # ------------------------------------------------------------------ #

    def _register_routes(self):
        app = self._app
        cfg = self._config
        web_dir = _resource_path("web")

        # --- static files ---

        @app.route("/")
        def index():
            return send_from_directory(web_dir, "index.html")

        @app.route("/<path:filename>")
        def static_files(filename):
            return send_from_directory(web_dir, filename)

        # --- greeting ---

        @app.route("/api/greeting")
        def get_greeting():
            greetings = cfg.get_saludos()
            if len(greetings) > 1:
                choices = [g for g in greetings if g != self._last_greeting]
                chosen = random.choice(choices) if choices else random.choice(greetings)
            else:
                chosen = greetings[0]
            self._last_greeting = chosen
            return jsonify({"greeting": chosen})

        # --- config ---

        @app.route("/api/config", methods=["GET"])
        def get_config():
            song_path = cfg.get("song_path", "")
            import os as _os
            song_name = _os.path.basename(song_path) if song_path else ""
            return jsonify(
                {
                    "has_api_key": bool(cfg.get("gemini_api_key")),
                    "api_key": cfg.get("gemini_api_key", ""),
                    "language": cfg.get("language", "es-ES"),
                    "song_name": song_name,
                }
            )

        @app.route("/api/config", methods=["POST"])
        def set_config():
            data = request.get_json(silent=True) or {}
            if "gemini_api_key" in data:
                cfg.set("gemini_api_key", data["gemini_api_key"])
            if "language" in data:
                cfg.set("language", data["language"])
            return jsonify({"status": "ok"})

        # --- chat (Gemini proxy) ---

        @app.route("/api/chat", methods=["POST"])
        def chat():
            data = request.get_json(silent=True) or {}
            message = data.get("message", "").strip()
            history = data.get("history", [])

            if not message:
                return jsonify({"error": "empty message"}), 400

            api_key = cfg.get("gemini_api_key", "")
            if not api_key:
                return jsonify({"error": "no_api_key"}), 400

            # Build Gemini content list
            contents = []
            for h in history:
                role = "model" if h.get("role") == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": h["content"]}]})
            contents.append({"role": "user", "parts": [{"text": message}]})

            payload = {
                "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "contents": contents,
                "generationConfig": {"maxOutputTokens": 512},
            }

            try:
                resp = requests.post(
                    GEMINI_URL.format(key=api_key),
                    json=payload,
                    timeout=30,
                )
                resp.raise_for_status()
                result = resp.json()
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                return jsonify({"response": text})
            except requests.HTTPError as exc:
                body = exc.response.text if exc.response else str(exc)
                return jsonify({"error": f"Gemini HTTP error: {body}"}), 502
            except Exception as exc:
                return jsonify({"error": str(exc)}), 500

        # --- utility ---

        @app.route("/api/open-saludos", methods=["POST"])
        def open_saludos():
            cfg.ensure_saludos()
            subprocess.Popen(["notepad.exe", cfg.saludos_path])
            return jsonify({"status": "ok"})
