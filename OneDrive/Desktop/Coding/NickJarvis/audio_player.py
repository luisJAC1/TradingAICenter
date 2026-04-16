"""
audio_player.py
Plays audio files (mp3, wav, wma, ogg …) using the Windows Multimedia
Control Interface (MCI) via ctypes.windll.winmm.
Zero pip dependencies — MCI is built into every Windows installation.
"""

import os
import ctypes
import threading


class AudioPlayer:
    ALIAS = "jarvis_song"

    def __init__(self):
        self._lock  = threading.Lock()
        self._vol   = 80          # 0-100
        try:
            self._winmm = ctypes.windll.winmm
        except Exception as e:
            print(f"[Jarvis] winmm unavailable: {e}")
            self._winmm = None

    def play(self, path: str):
        if not path or not os.path.isfile(path):
            return
        threading.Thread(target=self._play, args=(path,), daemon=True).start()

    def stop(self):
        self._mci(f"stop {self.ALIAS}")
        self._mci(f"close {self.ALIAS}")

    def set_volume(self, percent: int):
        """Set volume 0-100. Applied on next play call."""
        self._vol = max(0, min(100, int(percent)))

    # ------------------------------------------------------------------ #

    def _play(self, path: str):
        with self._lock:
            self._mci(f"close {self.ALIAS}")
            win_path = os.path.abspath(path).replace("/", "\\")

            ret = self._mci(f'open "{win_path}" alias {self.ALIAS}')
            if ret != 0:
                print(f"[Jarvis] MCI open failed (code {ret}): {win_path}")
                return

            # Set volume before playing (MCI scale 0-1000)
            mci_vol = self._vol * 10
            self._mci(f"setaudio {self.ALIAS} volume to {mci_vol}")

            ret = self._mci(f"play {self.ALIAS}")
            if ret != 0:
                print(f"[Jarvis] MCI play failed (code {ret})")

    def _mci(self, command: str) -> int:
        if not self._winmm:
            return -1
        try:
            return self._winmm.mciSendStringW(command, None, 0, 0)
        except Exception as e:
            print(f"[Jarvis] MCI '{command}': {e}")
            return -1


player = AudioPlayer()
