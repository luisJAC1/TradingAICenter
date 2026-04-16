"""
main.py
Entry point for J.A.R.V.I.S.

Startup sequence
----------------
1. First-run check  -> show SetupWizard if needed
2. Start Flask web server in a daemon thread
3. Start ClapDetector in a daemon thread
4. Run pystray TrayIcon (blocks main thread)

On double-clap:
  a) Launch the configured app (if set)
  b) Open http://localhost:5000 in the default browser
"""

import os
import sys
import time
import threading
import webbrowser


def _resource_path(relative: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.abspath("."), relative)


def main():
    from config_manager import ConfigManager
    from setup_wizard import SetupWizard
    from web_server import WebServer
    from clap_detector import ClapDetector
    from tray_icon import TrayIcon
    from audio_player import player as audio_player

    config = ConfigManager()

    # ---- First-run wizard ----
    if config.is_first_run():
        wizard = SetupWizard(config)
        wizard.run()
        # If the user closed without completing, still proceed
        # (they can set the key later from the tray icon).

    # ---- Web server ----
    server = WebServer(config)
    t_server = threading.Thread(target=server.run, daemon=True, name="flask-server")
    t_server.start()

    # Give Flask a moment to bind the port before the tray icon is ready
    time.sleep(1.2)

    # ---- Double-clap callback ----
    def on_clap():
        # 1. Play theme song (non-blocking, fires immediately)
        song_path = config.get("song_path", "")
        if song_path:
            audio_player.play(song_path)

        # 2. Launch configured app
        app_path = config.get("app_path", "")
        if app_path and os.path.isfile(app_path):
            try:
                os.startfile(app_path)
            except Exception as exc:
                print(f"[Jarvis] Could not launch app: {exc}")

        # 3. Open Jarvis HUD
        webbrowser.open("http://localhost:5000")

    # ---- Clap detector ----
    detector = ClapDetector(on_clap)
    t_det = threading.Thread(target=detector.start, daemon=True, name="clap-detector")
    t_det.start()

    # ---- System tray (blocks until Exit is chosen) ----
    tray = TrayIcon(config, detector)
    tray.run()


if __name__ == "__main__":
    main()
