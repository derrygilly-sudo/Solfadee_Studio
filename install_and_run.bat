@echo off
REM ═══════════════════════════════════════════════════════
REM  Tonic Solfa Studio — Windows Installer & Launcher
REM  Run this file to install dependencies and launch
REM ═══════════════════════════════════════════════════════

title Tonic Solfa Studio Installer

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║        TONIC SOLFA STUDIO  v1.1 Enhanced         ║
echo  ║   Professional Music Notation Software           ║
echo  ║   Staff ↔ Tonic Solfa Conversion                ║
echo  ╚══════════════════════════════════════════════════╝
echo.

REM Check Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python is not installed or not on PATH.
    echo.
    echo  Please download Python 3.8+ from:
    echo  https://www.python.org/downloads/
    echo.
    echo  Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

echo  Python found:
python --version
echo.

REM Install/upgrade pip
echo  [1/8] Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install CORE dependencies
echo  [2/8] Installing midiutil (MIDI export/import)...
python -m pip install midiutil --quiet

echo  [3/8] Installing reportlab (PDF export)...
python -m pip install reportlab --quiet

echo  [4/8] Installing music21 (MusicXML + advanced MIDI)...
python -m pip install music21 --quiet

echo  [5/8] Installing pygame (audio playback)...
python -m pip install pygame --quiet

echo  [6/8] Installing Pillow (image processing)...
python -m pip install Pillow --quiet

REM Install NEW OPTIONAL dependencies for v1.1 features
echo  [7/8] Installing numpy (audio synthesis)...
python -m pip install numpy --quiet

echo  [8/8] Installing scipy (WAV file generation)...
python -m pip install scipy --quiet

echo.
echo  ═════════════════════════════════════════════════════
echo  ✓ Installation complete!
echo  ═════════════════════════════════════════════════════
echo.
echo  Available features:
echo  • Staff notation editing
echo  • Tonic solfa conversion
echo  • Multiple fonts & styles (NEW!)
echo  • Speedy entry tool (NEW!)
echo  • Advanced lyrics editor (NEW!)
echo  • Audio synthesis & WAV export (NEW!)
echo  • MusicXML import/export
echo  • MIDI support
echo  • PDF export
echo.
echo  Launching Tonic Solfa Studio v1.1…
echo.

REM Launch the application
python tonic_solfa_studio.py

if errorlevel 1 (
    echo.
    echo  [ERROR] Application failed to start.
    echo  Try running from command line for more details:
    echo  python tonic_solfa_studio.py
    echo.
)

pause

