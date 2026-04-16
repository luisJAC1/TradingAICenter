"""
tray_icon.py
System tray icon using pystray + Pillow.
The icon image is generated in-memory so no external .ico file is needed at runtime.
Menu actions that show dialogs always spawn a fresh Tk root because pystray runs
in its own thread and Tk is not thread-safe.
"""

import os
import sys
import subprocess
import threading
import webbrowser
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox

import pystray
from PIL import Image, ImageDraw

try:
    import winsound  # type: ignore
    _HAS_WINSOUND = True
except ImportError:
    _HAS_WINSOUND = False

from setup_wizard import add_to_startup, remove_from_startup


# ------------------------------------------------------------------ #
#  Icon generation                                                     #
# ------------------------------------------------------------------ #

def _make_icon_image(size: int = 64) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = size // 2
    r = size // 2 - 2

    # Dark background disc
    d.ellipse([2, 2, size - 2, size - 2], fill=(10, 10, 26))

    # Outer cyan ring
    d.ellipse([2, 2, size - 2, size - 2], outline=(0, 200, 255), width=3)

    # Middle ring
    m = size // 4
    d.ellipse([m, m, size - m, size - m], outline=(0, 140, 200), width=2)

    # Centre dot
    dot = size // 2 - 3
    d.ellipse([dot - 4, dot - 4, dot + 4, dot + 4], fill=(0, 220, 255))

    return img


# ------------------------------------------------------------------ #
#  Tray                                                                #
# ------------------------------------------------------------------ #

def _tk_root() -> tk.Tk:
    """Create and immediately hide a throwaway Tk root."""
    root = tk.Tk()
    root.withdraw()
    root.lift()
    root.attributes("-topmost", True)
    return root


class TrayIcon:
    def __init__(self, config, detector):
        self._config = config
        self._detector = detector
        self._test_mode = False
        self._icon = None

    # ------------------------------------------------------------------ #
    #  Run                                                                 #
    # ------------------------------------------------------------------ #

    def run(self):
        img = _make_icon_image(64)
        menu = pystray.Menu(
            pystray.MenuItem("Open Jarvis",            self._open_jarvis, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Configure launch app",   self._configure_app),
            pystray.MenuItem("Configure theme song",   self._configure_song),
            pystray.MenuItem("Set Gemini API Key",     self._set_api_key),
            pystray.MenuItem("Test clap detection",    self._toggle_test_mode),
            pystray.MenuItem("Edit greetings",         self._edit_greetings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._exit),
        )
        self._icon = pystray.Icon(
            "Jarvis",
            img,
            "Jarvis  —  double-clap to activate",
            menu,
        )
        self._icon.run()

    # ------------------------------------------------------------------ #
    #  Menu handlers (all run in pystray's thread)                        #
    # ------------------------------------------------------------------ #

    def _open_jarvis(self, *_):
        webbrowser.open("http://localhost:5000")

    def _configure_app(self, *_):
        def _run():
            root = _tk_root()
            path = filedialog.askopenfilename(
                parent=root,
                title="Select app to launch on double clap",
                filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
            )
            if path:
                self._config.set("app_path", path)
                messagebox.showinfo(
                    "Jarvis", f"App saved:\n{os.path.basename(path)}", parent=root
                )
            root.destroy()

        threading.Thread(target=_run, daemon=True).start()

    def _configure_song(self, *_):
        def _run():
            root = _tk_root()
            path = filedialog.askopenfilename(
                parent=root,
                title="Select theme song to play on activation",
                filetypes=[
                    ("Audio files", "*.mp3 *.wav *.ogg *.flac *.m4a"),
                    ("All files", "*.*"),
                ],
            )
            if path:
                self._config.set("song_path", path)
                messagebox.showinfo(
                    "Jarvis",
                    f"Theme song saved:\n{os.path.basename(path)}\n\n"
                    "It will play every time you double-clap.",
                    parent=root,
                )
            elif path == "":
                # User cancelled — offer to clear
                if messagebox.askyesno("Jarvis", "Clear current theme song?", parent=root):
                    self._config.set("song_path", "")
            root.destroy()

        threading.Thread(target=_run, daemon=True).start()

    def _set_api_key(self, *_):
        def _run():
            root = _tk_root()
            current = self._config.get("gemini_api_key", "")
            key = simpledialog.askstring(
                "Gemini API Key",
                "Paste your Gemini API key:",
                initialvalue=current,
                show="*",
                parent=root,
            )
            if key is not None:
                self._config.set("gemini_api_key", key.strip())
                messagebox.showinfo("Jarvis", "API key saved.", parent=root)
            root.destroy()

        threading.Thread(target=_run, daemon=True).start()

    def _toggle_test_mode(self, icon, item):
        self._test_mode = not self._test_mode

        def _beep():
            if _HAS_WINSOUND:
                winsound.Beep(1200, 150)

        self._detector.set_test_mode(self._test_mode, _beep if self._test_mode else None)

        def _notify():
            root = _tk_root()
            if self._test_mode:
                messagebox.showinfo(
                    "Jarvis — Test Mode ON",
                    "Clap detection test is ACTIVE.\n"
                    "Clap twice and you should hear a beep.\n\n"
                    "Click 'Test clap detection' again to turn it off.",
                    parent=root,
                )
            else:
                messagebox.showinfo("Jarvis", "Test mode OFF.", parent=root)
            root.destroy()

        threading.Thread(target=_notify, daemon=True).start()

    def _edit_greetings(self, *_):
        self._config.ensure_saludos()
        subprocess.Popen(["notepad.exe", self._config.saludos_path])

    def _exit(self, icon, item):
        icon.stop()
        os._exit(0)
