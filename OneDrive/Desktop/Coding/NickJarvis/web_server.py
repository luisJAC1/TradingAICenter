"""
web_server.py
Local Flask server:
  - Serves the HUD web app
  - Proxies Gemini 2.5 Flash for chat (text)
  - Proxies Gemini 2.5 Flash Preview TTS for audio synthesis
  - SSE stream so the open tab is notified on clap (no duplicate tabs)
"""

import base64
import os
import queue
import random
import struct
import subprocess
import threading

import requests
from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context

import sys

PORT = 5000

CHAT_MODEL = "gemini-2.5-flash"
TTS_MODEL  = "gemini-2.5-flash-preview-tts"

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

SYSTEM_PROMPT = (
    "You are J.A.R.V.I.S, a witty, concise, and helpful AI assistant. "
    "Respond in the same language the user writes in. "
    "Keep responses short and punchy unless asked for detail."
)

TTS_VOICES = ["Charon", "Puck", "Kore", "Fenrir", "Aoede", "Zephyr", "Orbit", "Leda"]


def _resource_path(relative: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.abspath("."), relative)


def _pcm_to_wav(pcm: bytes, rate: int = 24000, channels: int = 1, bits: int = 16) -> bytes:
    """Wrap raw PCM bytes in a WAV container so the browser can play them."""
    data_len = len(pcm)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_len, b"WAVE",
        b"fmt ", 16,
        1,                                        # PCM
        channels,
        rate,
        rate * channels * (bits // 8),            # byte rate
        channels * (bits // 8),                   # block align
        bits,
        b"data", data_len,
    )
    return header + pcm


class WebServer:
    def __init__(self, config):
        self._config = config
        self._last_greeting: str = ""

        # SSE clients — each is a queue.Queue
        self._clients: list[queue.Queue] = []
        self._clients_lock = threading.Lock()

        self._app = Flask(__name__)
        self._register_routes()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def run(self):
        self._app.run(
            host="127.0.0.1", port=PORT,
            debug=False, use_reloader=False, threaded=True,
        )

    def notify_activate(self) -> bool:
        """
        Push an 'activate' event to all connected browser tabs.
        Returns True if at least one tab was reachable.
        """
        with self._clients_lock:
            live = list(self._clients)
        if not live:
            return False
        for q in live:
            try:
                q.put_nowait("activate")
            except queue.Full:
                pass
        return True

    def has_clients(self) -> bool:
        with self._clients_lock:
            return len(self._clients) > 0

    # ------------------------------------------------------------------ #
    #  Routes                                                              #
    # ------------------------------------------------------------------ #

    def _register_routes(self):
        app = self._app
        cfg = self._config
        web_dir = _resource_path("web")

        # ---------- static ----------

        @app.route("/")
        def index():
            return send_from_directory(web_dir, "index.html")

        @app.route("/<path:filename>")
        def static_files(filename):
            return send_from_directory(web_dir, filename)

        # ---------- SSE stream ----------

        @app.route("/api/stream")
        def sse_stream():
            q: queue.Queue = queue.Queue(maxsize=10)
            with self._clients_lock:
                self._clients.append(q)
            # Notify main.py that the page has loaded so it can cancel its cooldown
            cb = getattr(self, "on_client_connect", None)
            if cb:
                cb()

            def generate():
                try:
                    while True:
                        try:
                            msg = q.get(timeout=25)
                            yield f"data: {msg}\n\n"
                        except queue.Empty:
                            yield "data: ping\n\n"   # keepalive
                except GeneratorExit:
                    pass
                finally:
                    with self._clients_lock:
                        if q in self._clients:
                            self._clients.remove(q)

            return Response(
                stream_with_context(generate()),
                mimetype="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )

        # ---------- greeting ----------

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

        # ---------- config ----------

        @app.route("/api/config", methods=["GET"])
        def get_config():
            song_path = cfg.get("song_path", "")
            song_name = os.path.basename(song_path) if song_path else ""
            return jsonify({
                "has_api_key": bool(cfg.get("gemini_api_key")),
                "api_key":     cfg.get("gemini_api_key", ""),
                "language":    cfg.get("language", "es-ES"),
                "vol_tts":     cfg.get("vol_tts", 80),
                "vol_song":    cfg.get("vol_song", 80),
                "tts_voice":   cfg.get("tts_voice", "Charon"),
                "song_name":   song_name,
                "tts_voices":  TTS_VOICES,
            })

        @app.route("/api/config", methods=["POST"])
        def set_config():
            data = request.get_json(silent=True) or {}
            for key in ("gemini_api_key", "language", "tts_voice"):
                if key in data:
                    cfg.set(key, data[key])
            for key in ("vol_tts", "vol_song"):
                if key in data:
                    cfg.set(key, int(data[key]))
            return jsonify({"status": "ok"})

        # ---------- chat (Gemini 2.5 Flash) ----------

        @app.route("/api/chat", methods=["POST"])
        def chat():
            data    = request.get_json(silent=True) or {}
            message = data.get("message", "").strip()
            history = data.get("history", [])

            if not message:
                return jsonify({"error": "empty message"}), 400

            api_key = cfg.get("gemini_api_key", "")
            if not api_key:
                return jsonify({"error": "no_api_key"}), 400

            contents = []
            for h in history:
                role = "model" if h.get("role") == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": h["content"]}]})
            contents.append({"role": "user", "parts": [{"text": message}]})

            url = f"{GEMINI_BASE}/{CHAT_MODEL}:generateContent?key={api_key}"
            payload = {
                "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "contents": contents,
                "generationConfig": {"maxOutputTokens": 512},
            }

            try:
                resp = requests.post(url, json=payload, timeout=45)
                resp.raise_for_status()
                result = resp.json()
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                return jsonify({"response": text})
            except requests.HTTPError as exc:
                body = exc.response.text if exc.response else str(exc)
                return jsonify({"error": body}), 502
            except Exception as exc:
                return jsonify({"error": str(exc)}), 500

        # ---------- TTS (Gemini 2.5 Flash Preview TTS) ----------

        @app.route("/api/tts", methods=["POST"])
        def tts():
            data  = request.get_json(silent=True) or {}
            text  = data.get("text", "").strip()
            voice = data.get("voice", cfg.get("tts_voice", "Charon"))

            if not text:
                return jsonify({"error": "empty text"}), 400

            api_key = cfg.get("gemini_api_key", "")
            if not api_key:
                return jsonify({"error": "no_api_key"}), 400

            url = f"{GEMINI_BASE}/{TTS_MODEL}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": text}]}],
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {"voiceName": voice}
                        }
                    },
                },
            }

            try:
                resp = requests.post(url, json=payload, timeout=45)
                resp.raise_for_status()
                result = resp.json()

                part      = result["candidates"][0]["content"]["parts"][0]
                inline    = part["inlineData"]
                mime_type = inline["mimeType"]       # e.g. "audio/pcm;rate=24000"
                audio_b64 = inline["data"]

                # Gemini TTS returns raw PCM — wrap it in WAV for the browser
                if "pcm" in mime_type.lower() or "l16" in mime_type.lower():
                    rate = 24000
                    if "rate=" in mime_type:
                        try:
                            rate = int(mime_type.split("rate=")[1].split(";")[0].strip())
                        except Exception:
                            pass
                    pcm_bytes = base64.b64decode(audio_b64)
                    wav_bytes = _pcm_to_wav(pcm_bytes, rate=rate)
                    audio_b64 = base64.b64encode(wav_bytes).decode()
                    mime_type = "audio/wav"

                return jsonify({"audio_b64": audio_b64, "mime_type": mime_type})

            except requests.HTTPError as exc:
                body = exc.response.text if exc.response else str(exc)
                return jsonify({"error": body}), 502
            except Exception as exc:
                return jsonify({"error": str(exc)}), 500

        # ---------- utility ----------

        @app.route("/api/open-saludos", methods=["POST"])
        def open_saludos():
            cfg.ensure_saludos()
            try:
                os.startfile(cfg.saludos_path)
            except Exception as e:
                return jsonify({"error": str(e)}), 500
            return jsonify({"status": "ok"})
