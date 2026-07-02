@echo off
setlocal EnableDelayedExpansion
REM ═══════════════════════════════════════════════════════
REM  Solfaggio Studio Pro v1.0 — Windows Executable Builder
REM  Creates a standalone .exe file (no Python installation needed)
REM ═══════════════════════════════════════════════════════

cd /d "%~dp0"

set "NO_PAUSE="
if /I "%~1"=="--no-pause" set "NO_PAUSE=1"

echo.
echo  Building Solfadee Studio Standalone Executable...
echo.

set "SPEC_MAIN=Solfadee Studio.spec"
set "SPEC_PRO=solfa_canvas_pro.spec"
set "SPEC_TRAD=solfa_canvas.spec"
set "APP_ICON=branding\solfadee_icon.ico"

REM Ensure pyinstaller is installed
python -m pip install pyinstaller --quiet
if errorlevel 1 goto :build_failed
set "PYINSTALLER_CMD=python -m PyInstaller"

REM Build the main app executable
if exist "%SPEC_MAIN%" (
    %PYINSTALLER_CMD% --noconfirm --clean "%SPEC_MAIN%"
) else (
    %PYINSTALLER_CMD% --noconfirm --clean --onefile --windowed ^
        --name "Solfadee Studio" ^
        --add-data "templates;templates" ^
        --add-data "examples;examples" ^
        --icon="%APP_ICON%" ^
        tonic_solfa_studio.py
)
if errorlevel 1 goto :build_failed
if not exist "dist\Solfadee Studio.exe" goto :build_failed

echo.
echo  Building Solfa Canvas Pro standalone executable...
echo.
if exist "%SPEC_PRO%" (
    pyinstaller --noconfirm --clean "%SPEC_PRO%"
) else (
    pyinstaller --noconfirm --clean --onefile --windowed ^
        --name "Solfa Canvas Pro" ^
        --add-data "templates;templates" ^
        --add-data "examples;examples" ^
        --icon="%APP_ICON%" ^
        solfa_canvas_pro.py
)
if errorlevel 1 goto :build_failed
if not exist "dist\Solfa Canvas Pro.exe" goto :build_failed

echo.
echo  Building Traditional Solfa Canvas standalone executable...
echo.
if exist "%SPEC_TRAD%" (
    pyinstaller --noconfirm --clean "%SPEC_TRAD%"
) else (
    pyinstaller --noconfirm --clean --onefile --windowed ^
        --name "Traditional Solfa Canvas" ^
        --add-data "templates;templates" ^
        --add-data "examples;examples" ^
        --icon="%APP_ICON%" ^
        solfa_canvas.py
)
if errorlevel 1 goto :build_failed
if not exist "dist\Traditional Solfa Canvas.exe" goto :build_failed

echo.
echo  ✓ Build succeeded!
echo.
echo  Executable location:
echo    %cd%\dist\Solfadee Studio.exe
if exist "dist\Solfa Canvas Pro.exe" echo    %cd%\dist\Solfa Canvas Pro.exe
if exist "dist\Traditional Solfa Canvas.exe" echo    %cd%\dist\Traditional Solfa Canvas.exe
 echo.
echo  You can now distribute these .exe files to other Windows PCs.
echo.
if not defined NO_PAUSE pause
exit /b 0

:build_failed
    echo.
    echo  [ERROR] Build failed or executable missing.
    echo  Check the log above for details.
    if not defined NO_PAUSE pause
    exit /b 1
