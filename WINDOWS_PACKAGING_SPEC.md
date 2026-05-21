# Windows Packaging Specification for SolfaDee Studio

## Goal
Create a Windows-ready distribution for SolfaDee Studio with:
- a bundled standalone `.exe` using PyInstaller
- a Windows installer wrapper using Inno Setup
- all runtime resources included and discoverable by the executable

## Packaging Files
- `Solfadee Studio.spec`: PyInstaller spec file for building `dist\Solfadee Studio.exe`
- `Solfadee_Studio_Installer.iss`: Inno Setup script for producing `installer\Output\Solfadee_Studio_Setup.exe`
- `tonic_solfa_studio.py`: main application entry point with runtime resource helper
- `tonic_solfa_studio_v5.py`: compatibility launcher and GUI entry point
- `templates\`: shipped template assets
- `examples\`: example score/project files
- `branding\`: installer graphics and icon

## Prerequisites
1. Windows 10 or 11
2. Python 3.8+ installed for development and build purposes
3. Project virtual environment created in `.venv`
4. Install dependencies:
   ```powershell
   cd "C:\Users\HP\Documents\TONIC SOLFA SOFTWARE"
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
   ```
5. Install Inno Setup 6 from https://jrsoftware.org/

## Stage 1 — Source readiness

### Required fixes already applied
- `score_bridge.py`: `_STD_DURS` only contains base durations:
  - `[4.0, 2.0, 1.0, 0.5, 0.25, 0.125, 0.0625]`
- `tonic_solfa_studio_v5.py`: file is saved with `# -*- coding: utf-8-sig -*-` and no BOM startup issue
- `tonic_solfa_studio.py`: added `_resource_path()` helper for PyInstaller compatibility

### Runtime resource helper
In `tonic_solfa_studio.py` the helper was added:
```python
import sys


def _resource_path(relative_path: str) -> str:
    """Return an absolute path to a resource, compatible with PyInstaller."""
    base_path = getattr(sys, '_MEIPASS', None)
    if base_path is None:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)
```

This ensures `templates` and other data files are found both during development and after bundling.

## Stage 2 — Build with PyInstaller

### Spec file
Use `Solfadee Studio.spec` for the PyInstaller build. It already includes:
- `templates` folder
- `examples` folder
- application icon `branding/solfadee_icon.ico`

### Build command
```powershell
cd "C:\Users\HP\Documents\TONIC SOLFA SOFTWARE"
.\.venv\Scripts\python.exe -m PyInstaller "Solfadee Studio.spec"
```

### Expected output
- `dist\Solfadee Studio.exe`
- `build\` directory with intermediate PyInstaller files

### Verification
- Double-click `dist\Solfadee Studio.exe`
- Confirm the app launches without requiring a separate Python install
- Confirm templates open correctly from the packaged executable

## Stage 3 — Build the Windows installer

### Inno Setup script
Use `Solfadee_Studio_Installer.iss` in Inno Setup 6.
It installs:
- the executable `dist\Solfadee Studio.exe`
- the `README.md`
- `templates\*` assets
- `examples\*` assets

It also creates:
- Start Menu shortcuts
- optional desktop shortcut
- uninstaller entry

### Compile command
Open the script in Inno Setup and press `F9`, or run from the command line if Inno Setup is installed:
```powershell
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "C:\Users\HP\Documents\TONIC SOLFA SOFTWARE\Solfadee_Studio_Installer.iss"
```

### Installer output
- `installer\Output\Solfadee_Studio_Setup.exe`

## Notes for packaging
- Make sure the current working directory is the repository root when running PyInstaller.
- `Solfadee Studio.spec` uses relative data paths, so it must be invoked from the project root.
- The Inno Setup script relies on `dist\Solfadee Studio.exe`; build that first.
- If the app is built on a 64-bit machine, the installer will install in 64-bit-compatible mode.

## Recommended release checklist
- [ ] `dist\Solfadee Studio.exe` tested on a clean Windows machine
- [ ] `installer\Output\Solfadee_Studio_Setup.exe` generated successfully
- [ ] Start Menu shortcut launches the app
- [ ] `templates` and `examples` are accessible from the installed application
- [ ] README and uninstaller are present

## Additional implementation details
- The packaging process bundles Python, dependencies, templates, and examples into a single executable plus installer.
- The `Solfadee Studio.spec` file defines the build artifact name as `Solfadee Studio`, matching the installer script.
- The `Solfadee_Studio_Installer.iss` script sets `OutputDir=installer\Output` and uses modern wizard styling.

## Troubleshooting
- If the executable fails to load resources after packaging, verify `templates` is present in the extracted `_MEIPASS` folder.
- If Inno Setup cannot find `dist\Solfadee Studio.exe`, rebuild the PyInstaller artifact first.
- If a missing module error appears at runtime, confirm it is included in `requirements.txt` and rebuild.
