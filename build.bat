@echo off
REM Build a single-file Windows executable for Tonic Solfa Studio v5
REM Usage: build.bat

cd /d "%~dp0"

REM Ensure venv and dependencies are installed before building:
REM python -m pip install -r requirements.txt

pyinstaller --noconfirm --onefile --windowed --name "TonicSolfaStudioPro" \
    --add-data "templates;templates" \
    tonic_solfa_studio_v5.py

if %ERRORLEVEL% NEQ 0 (
    echo Build failed with code %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)

echo Build succeeded.

echo Executable location:
	echo dist\TonicSolfaStudioPro.exe
