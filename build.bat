@echo off
REM ═══════════════════════════════════════════════════════
REM  Solfaggio Studio Pro v1.0 — Windows Executable Builder
REM  Creates a standalone .exe file (no Python installation needed)
REM ═══════════════════════════════════════════════════════

cd /d "%~dp0"

echo.
echo  Building Solfaggio Studio Pro v1.0 Standalone Executable...
echo.

REM Ensure pyinstaller is installed
pip install pyinstaller --quiet

REM Build the executable
pyinstaller --noconfirm --onefile --windowed ^
    --name "Solfaggio Studio Pro" ^
    --add-data "templates;templates" ^
    --icon=icon.ico 2>nul ^
    tonic_solfa_studio_v5.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Build failed. Trying without icon...
    pyinstaller --noconfirm --onefile --windowed ^
        --name "Solfaggio Studio Pro" ^
        --add-data "templates;templates" ^
        tonic_solfa_studio_v5.py
    
    if %ERRORLEVEL% NEQ 0 (
        echo  Build failed with code %ERRORLEVEL%.
        pause
        exit /b %ERRORLEVEL%
    )
)

echo.
echo  ✓ Build succeeded!
echo.
echo  Executable location:
echo    %cd%\dist\Solfaggio Studio Pro.exe
echo.
echo  You can now distribute this .exe file to other Windows PCs.
echo.
pause
