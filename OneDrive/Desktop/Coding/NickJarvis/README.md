# J.A.R.V.I.S

A Windows desktop voice assistant that activates on a double clap.

---

## What it does

- Sits silently in the **system tray** at all times.
- Listens to the microphone in the background for **two claps within ~800 ms**.
- On double-clap:
  1. Plays your configured **theme song**.
  2. Launches a configured **app** (e.g. Spotify, a game).
  3. Opens a **sci-fi voice assistant HUD** at `localhost:5000` in your browser.
- The HUD greets you aloud, then listens and responds via Gemini AI.

---

## Components

| File | Purpose |
|------|---------|
| `main.py` | Entry point. Starts Flask, clap detector, tray icon. |
| `clap_detector.py` | Mic audio analysis using sounddevice. Detects double-clap via energy spike algorithm. |
| `tray_icon.py` | System tray icon and right-click menu (pystray). |
| `web_server.py` | Local Flask server. Serves the HUD and proxies Gemini API calls. |
| `config_manager.py` | Reads/writes `%APPDATA%\Jarvis\config.json` and `saludos.txt`. |
| `setup_wizard.py` | Tkinter first-run wizard for Gemini key + app path. |
| `audio_player.py` | Plays the theme song via pygame.mixer. |
| `create_icon.py` | Generates `assets/icon.ico` before building. |
| `web/index.html` | Sci-fi HUD single-page app. |
| `web/style.css` | Dark glowing HUD styles. |
| `web/app.js` | Web Audio visualiser, Web Speech API STT, SpeechSynthesis TTS, Gemini chat. |

---

## Quick start (development)

```bat
pip install -r requirements.txt
python main.py
```

---

## Building the distributable .exe

```bat
build.bat
```

The output is `dist\Jarvis.exe` — a single file Nico can download and run with no Python required.

---

## Configuration

All config lives in `%APPDATA%\Jarvis\` (usually `C:\Users\<name>\AppData\Roaming\Jarvis\`).

| File | Contents |
|------|---------|
| `config.json` | Gemini API key, app path, song path, language, startup flag. |
| `saludos.txt` | Custom greeting lines (one per line, UTF-8). Edit with Notepad. |

### Tray icon right-click menu

- **Open Jarvis** — opens the HUD in the browser.
- **Configure launch app** — choose an .exe to open on clap.
- **Configure theme song** — pick an mp3/wav/ogg file to play on activation.
- **Set Gemini API Key** — paste your key (free at aistudio.google.com).
- **Test clap detection** — clap twice to hear a beep; confirms the mic is working.
- **Edit greetings** — opens `saludos.txt` in Notepad.
- **Exit** — stops Jarvis.

---

## Getting a free Gemini API key

1. Go to **https://aistudio.google.com**
2. Sign in with a Google account.
3. Click **Get API key** → **Create API key**.
4. Copy and paste it into Jarvis (tray → "Set Gemini API Key" or the HUD settings panel).

No credit card needed.

---

## Clap detection tips

- Works best in a quiet-ish room with a decent microphone.
- If it triggers too easily, raise the threshold in the HUD settings panel.
- If it misses claps, lower the threshold or clap louder/closer to the mic.
- Use **Test clap detection** from the tray to calibrate before using normally.

---

## Greetings (saludos.txt)

The file lives at `%APPDATA%\Jarvis\saludos.txt`. Open it with Notepad and add your own lines:

```
# This is a comment — ignored
Que tal Nicolas, aqui a tu servicio
Hola crack, listo para dominar el mundo
```

One greeting is picked at random each time Jarvis activates (never the same one twice in a row).
