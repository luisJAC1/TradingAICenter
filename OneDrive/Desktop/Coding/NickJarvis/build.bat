@echo off
setlocal

echo ==============================================
echo  J.A.R.V.I.S -- Build Script
echo ==============================================
echo.

:: Step 1 – install / verify deps
echo [1/4] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: pip install failed. Aborting.
    pause
    exit /b 1
)

:: Step 2 – generate icon
echo.
echo [2/4] Generating icon...
python create_icon.py
if errorlevel 1 (
    echo ERROR: Icon generation failed. Aborting.
    pause
    exit /b 1
)

:: Step 3 – run PyInstaller
echo.
echo [3/4] Running PyInstaller...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "Jarvis" ^
    --icon "assets\icon.ico" ^
    --add-data "web;web" ^
    --add-data "assets;assets" ^
    --hidden-import "pystray._win32" ^
    --hidden-import "PIL._tkinter_finder" ^
    --hidden-import "sounddevice" ^
    --hidden-import "pygame" ^
    --hidden-import "flask" ^
    --hidden-import "engineio.async_drivers.threading" ^
    main.py

if errorlevel 1 (
    echo ERROR: PyInstaller failed. See output above.
    pause
    exit /b 1
)

:: Step 4 – done
echo.
echo [4/4] Done!
echo.
echo Output: dist\Jarvis.exe
echo.
echo Give Nico the file:  dist\Jarvis.exe
echo He just double-clicks it to install and run -- no Python needed.
echo.
pause
