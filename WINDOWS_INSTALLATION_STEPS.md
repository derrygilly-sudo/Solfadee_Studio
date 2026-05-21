# SolfaDee Studio — Windows Installation Guide

This guide explains how to install SolfaDee Studio on a Windows computer so it runs correctly without requiring Python to be installed.

## What you need
- A Windows 10 or Windows 11 PC
- The installer file produced by the build process:
  - `installer\Output\Solfadee_Studio_Setup.exe`
- Administrator rights if you want to install to `Program Files`

## Recommended install workflow

### Step 1: Copy the installer to the target PC
1. Build the installer on your development machine.
2. Copy the file `installer\Output\Solfadee_Studio_Setup.exe` to the other computer.
   - Use USB, network share, email, or cloud storage.

### Step 2: Run the installer
1. Double-click `Solfadee_Studio_Setup.exe`.
2. If Windows asks for permission, click **Yes**.
3. In the setup wizard:
   - Click **Next**.
   - Accept the license terms if prompted.
   - Choose the install folder, or keep the default `C:\Program Files\Solfadee Studio`.
   - Optionally enable the desktop shortcut.
   - Click **Install**.
4. Wait for the installer to finish.
5. Click **Finish**.

### Step 3: Launch SolfaDee Studio
- Use the Start Menu shortcut:
  - `Start Menu → SolfaDee Studio`
- Or use the desktop shortcut if you created one.

### Step 4: Confirm the app works
- The app should start immediately.
- Open one of the sample files from the `examples` folder if available.
- Verify `templates` and built-in resources load successfully.

## Why this installer is the right method
- The installer wraps a PyInstaller-generated executable.
- The executable already bundles Python and all required libraries.
- The target computer does not need Python installed.

## Portable alternative (not recommended for general users)
If you prefer not to install, you can run the standalone executable directly from the build output:

```text
C:\Users\HP\Documents\TONIC SOLFA SOFTWARE\dist\Solfadee Studio.exe
```

However, the recommended method for a stable user experience is the installer.

## Troubleshooting

### Windows blocks the installer or app
- If SmartScreen warns you, click **More info** and then **Run anyway**.
- If the installer is blocked, verify that the file was copied correctly and is not corrupted.

### The app does not start
- Make sure you launched the installer version, not the `.py` file.
- Run the Start Menu shortcut.
- If it still fails, reinstall using administrator rights.

### Source files missing after install
- The installer copies `templates` and `examples` into the installed program folder.
- If those files are missing, rebuild the installer and verify `Solfadee Studio.spec` includes:
  - `('templates', 'templates')`
  - `('examples', 'examples')`

## Notes for support teams
- The installed program is self-contained.
- It should work on clean Windows systems without Python.
- If a dependency issue appears, it is usually because the build step did not include the right data or the installer used a stale `dist` folder.

## File locations after installation
- Installed executable: `C:\Program Files\Solfadee Studio\Solfadee Studio.exe`
- Templates folder: `C:\Program Files\Solfadee Studio\templates`
- Examples folder: `C:\Program Files\Solfadee Studio\examples`
- User data/settings are stored in: `C:\Users\<username>\.tonicsolfa6_settings.json`

## Summary
To install SolfaDee Studio on another computer:
1. Copy `installer\Output\Solfadee_Studio_Setup.exe`.
2. Run the setup wizard.
3. Launch from the Start Menu or desktop shortcut.
4. Verify the app loads templates and opens sample files.

This is the supported installation path for Windows users.
