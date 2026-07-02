@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "NO_PAUSE="
if /I "%~1"=="--no-pause" set "NO_PAUSE=1"

echo.
echo Installing Python dependencies...
echo.
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo [ERROR] Dependency install failed.
    if not defined NO_PAUSE pause
    exit /b 1
)

echo.
echo Building Solfadee Studio installer...
echo.

echo Building branded executables first...
call "%~dp0build.bat" --no-pause
if errorlevel 1 (
    echo.
    echo [ERROR] Executable build failed.
    if not defined NO_PAUSE pause
    exit /b 1
)

echo.
echo Building branded installer package...
echo.

set "ISCC_PATH="
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC_PATH=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"

if not defined ISCC_PATH (
    where ISCC >nul 2>&1
    if not errorlevel 1 set "ISCC_PATH=ISCC"
)

if not defined ISCC_PATH (
    echo [ERROR] Inno Setup 6 was not found.
    echo Install it from: https://jrsoftware.org/isinfo.php
    echo Or run:
    echo   winget install --id JRSoftware.InnoSetup -e --source winget
    if not "%~1"=="--no-pause" pause
    exit /b 1
)

"%ISCC_PATH%" "Solfadee_Studio_Installer.iss"
if errorlevel 1 (
    echo.
    echo [ERROR] Installer build failed.
    if not "%~1"=="--no-pause" pause
    exit /b 1
)

echo.
echo Installer created successfully:
echo   %cd%\installer\Output\Solfadee_Studio_Setup.exe
echo.
if not "%~1"=="--no-pause" pause
