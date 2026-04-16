"""
audio_player.py
Plays a local audio file (mp3 / wav / ogg) when Jarvis activates.
Uses pygame.mixer so it works independently from the browser.
The mixer is initialised once and reused for every play call.
"""

import os
import threading

try:
    import pygame
    _HAS_PYGAME = True
except ImportError:
    _HAS_PYGAME = False


class AudioPlayer:
    def __init__(self):
        self._ready = False
        self._lock  = threading.Lock()

    def _ensure_init(self):
        if self._ready:
            return True
        if not _HAS_PYGAME:
            print("[Jarvis] pygame not installed — theme song disabled.")
            return False
        try:
            pygame.mixer.init()
            self._ready = True
            return True
        except Exception as e:
            print(f"[Jarvis] pygame.mixer init failed: {e}")
            return False

    def play(self, path: str):
        """Fire-and-forget: play `path` in a background thread."""
        if not path or not os.path.isfile(path):
            return
        threading.Thread(target=self._play, args=(path,), daemon=True).start()

    def stop(self):
        if self._ready and _HAS_PYGAME:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def _play(self, path: str):
        with self._lock:
            if not self._ensure_init():
                return
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()
            except Exception as e:
                print(f"[Jarvis] Could not play '{path}': {e}")


# Singleton
player = AudioPlayer()
