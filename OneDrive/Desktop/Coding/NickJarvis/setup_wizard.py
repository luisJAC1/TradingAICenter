"""
setup_wizard.py
Tkinter first-run wizard that collects:
  - Gemini API key
  - Optional: path to app to launch on clap
  - Optional: add to Windows startup

Writes startup registry entry and creates the initial saludos.txt.
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    import winreg  # type: ignore
    _HAS_WINREG = True
except ImportError:
    _HAS_WINREG = False

STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _exe_path() -> str:
    """Return the path of the running executable (works in both dev and PyInstaller)."""
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(sys.argv[0])


def add_to_startup():
    if not _HAS_WINREG:
        return
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "Jarvis", 0, winreg.REG_SZ, f'"{_exe_path()}"')
        winreg.CloseKey(key)
    except Exception as e:
        print(f"[Jarvis] Could not add to startup: {e}")


def remove_from_startup():
    if not _HAS_WINREG:
        return
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, "Jarvis")
        winreg.CloseKey(key)
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[Jarvis] Could not remove from startup: {e}")


# ------------------------------------------------------------------ #
#  Colour palette                                                      #
# ------------------------------------------------------------------ #
BG       = "#0a0a1a"
BG2      = "#111126"
CYAN     = "#00ccff"
CYAN_DIM = "#005577"
WHITE    = "#e0e8ff"
DIM      = "#555577"


class SetupWizard:
    def __init__(self, config):
        self._config = config
        self._root = None

    def run(self):
        root = tk.Tk()
        self._root = root
        root.title("J.A.R.V.I.S — First Run Setup")
        root.geometry("520x500")
        root.resizable(False, False)
        root.configure(bg=BG)
        root.lift()
        root.attributes("-topmost", True)
        root.after(100, lambda: root.attributes("-topmost", False))

        self._build_ui(root)
        root.mainloop()

    # ------------------------------------------------------------------ #

    def _build_ui(self, root):
        # ---- Title ----
        tk.Label(
            root, text="J.A.R.V.I.S", bg=BG, fg=CYAN,
            font=("Segoe UI", 28, "bold"),
        ).pack(pady=(28, 2))
        tk.Label(
            root, text="First Run Setup", bg=BG, fg=DIM,
            font=("Segoe UI", 10),
        ).pack(pady=(0, 22))

        # ---- Content frame ----
        frame = tk.Frame(root, bg=BG)
        frame.pack(fill="x", padx=48)

        # API Key
        tk.Label(frame, text="GEMINI API KEY", bg=BG, fg=CYAN,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(frame, text="Get yours free at  aistudio.google.com",
                 bg=BG, fg=DIM, font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 4))

        api_var = tk.StringVar()
        api_entry = tk.Entry(
            frame, textvariable=api_var, show="*",
            bg=BG2, fg=WHITE, insertbackground=CYAN,
            relief="flat", font=("Segoe UI", 10), bd=6,
        )
        api_entry.pack(fill="x", ipady=4, pady=(0, 18))

        # App to launch
        tk.Label(frame, text="APP TO LAUNCH ON DOUBLE CLAP  (optional)",
                 bg=BG, fg=CYAN, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(frame, text="Can be changed later from the tray icon",
                 bg=BG, fg=DIM, font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 4))

        row = tk.Frame(frame, bg=BG)
        row.pack(fill="x", pady=(0, 18))
        path_var = tk.StringVar()
        path_entry = tk.Entry(
            row, textvariable=path_var,
            bg=BG2, fg=WHITE, insertbackground=CYAN,
            relief="flat", font=("Segoe UI", 9), bd=6,
        )
        path_entry.pack(side="left", fill="x", expand=True, ipady=4)

        def browse():
            p = filedialog.askopenfilename(
                parent=root,
                title="Select application",
                filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
            )
            if p:
                path_var.set(p)

        tk.Button(
            row, text="Browse", command=browse,
            bg=CYAN_DIM, fg=CYAN, relief="flat",
            font=("Segoe UI", 9), cursor="hand2", padx=10,
        ).pack(side="right", padx=(6, 0))

        # Greetings note
        tk.Label(
            frame,
            text=(
                r"A saludos.txt file will be created in %APPDATA%\Jarvis" + "\n"
                "Edit it with Notepad to add your own custom greetings."
            ),
            bg=BG, fg=DIM, font=("Segoe UI", 8), justify="left",
        ).pack(anchor="w", pady=(0, 14))

        # Startup checkbox
        startup_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            frame, text="Start Jarvis automatically when Windows starts",
            variable=startup_var,
            bg=BG, fg=WHITE, selectcolor=BG2,
            activebackground=BG, activeforeground=CYAN,
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        # ---- Button ----
        def finish():
            key = api_var.get().strip()
            if not key:
                messagebox.showwarning(
                    "Missing API Key",
                    "Please enter your Gemini API key.\n\n"
                    "Get it free (no credit card) at:\naistudio.google.com",
                    parent=root,
                )
                return

            self._config.set("gemini_api_key", key)

            app_path = path_var.get().strip()
            if app_path:
                self._config.set("app_path", app_path)

            if startup_var.get():
                add_to_startup()
                self._config.set("startup_enabled", True)
            else:
                remove_from_startup()
                self._config.set("startup_enabled", False)

            self._config.ensure_saludos()
            self._config.mark_setup_done()
            root.destroy()

        tk.Button(
            root, text="LAUNCH JARVIS",
            command=finish,
            bg=CYAN, fg=BG,
            font=("Segoe UI", 13, "bold"),
            relief="flat", cursor="hand2",
            pady=10, padx=30,
        ).pack(pady=24)
