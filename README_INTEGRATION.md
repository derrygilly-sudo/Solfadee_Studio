# SolfaDee Studio — Integration Guide
## VS Code Setup & Module Integration

---

## 1. Project File Layout

Place ALL of these files in ONE folder (e.g. `~/solfadee/`):

```
solfadee/
├── solfadee_v5.py                  ← your ORIGINAL main app (rename/copy here)
├── solfadee_studio_header.py       ← patched import block (provided)
├── combine_studio.py               ← one-shot combiner script (provided)
│
├── solfa_canvas_pro.py             ← FIXED Solfa Canvas Pro (provided)
├── solfa_canvas.py                 ← re-export bridge (provided)
│
├── solfadee_fixes.py               ← OctaveMarkMode + export_pdf_solfa_fixed
├── tonic_solfa_style_engine.py     ← StyleRegistry + SolfaStyleRenderer
├── font_styles_manager.py          ← FontStylesManager + FontStylesDialog
├── lyrics_manager.py               ← LyricsManager + LyricsEditorPanel
├── audio_engine.py                 ← AudioConfig + AudioSynthesizer + WavFileWriter
├── canvas_renderer.py              ← TonicSolfaCanvas stub
├── pdf_exporter.py                 ← TonicSolfaPDFExporter
└── score_bridge.py                 ← bridge_score_to_solfa
```

---

## 2. One-Time Setup (Terminal / VS Code Terminal)

```bash
# Step 1 — Install Python dependencies
pip install reportlab midiutil pygame mido pillow

# Step 2 — Generate the integrated main app
cd ~/solfadee
python3 combine_studio.py solfadee_v5.py

# Step 3 — Run the app
python3 solfadee_studio.py
```

`combine_studio.py` reads `solfadee_v5.py` (your original), cuts off
the old broken import block, prepends `solfadee_studio_header.py`
(which has the fixed, guarded imports), and writes `solfadee_studio.py`.

---

## 3. VS Code Configuration

### 3.1 Open the project folder
```
File → Open Folder → ~/solfadee
```

### 3.2 Select the right Python interpreter
```
Ctrl+Shift+P → "Python: Select Interpreter"
```
Choose the interpreter where you ran `pip install`.

### 3.3 Recommended extensions
| Extension | Purpose |
|---|---|
| `ms-python.python` | Python language support |
| `ms-python.pylance` | Type checking & IntelliSense |
| `ms-python.black-formatter` | Auto-format |

### 3.4 `.vscode/settings.json` (create this file)
```json
{
  "python.analysis.extraPaths": ["${workspaceFolder}"],
  "python.defaultInterpreterPath": "python3",
  "python.linting.enabled": true,
  "editor.rulers": [100],
  "files.exclude": { "**/__pycache__": true }
}
```

### 3.5 Launch configuration — `.vscode/launch.json`
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Run SolfaDee Studio",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/solfadee_studio.py",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}"
    },
    {
      "name": "Combine (rebuild studio)",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/combine_studio.py",
      "args": ["solfadee_v5.py"],
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}"
    }
  ]
}
```
Press **F5** to launch the app directly from VS Code.

---

## 4. What Changed vs. the Original

| Area | Original | Fixed / Integrated |
|---|---|---|
| `import` block | Hard `from module import …` — crashes if file missing | Wrapped in `try/except` — degrades gracefully |
| `solfa_canvas` import | `from solfa_canvas import … _render_pdf` | Bridges to `solfa_canvas_pro.render_pdf`; alias `_render_pdf` added |
| `solfa_canvas_pro.py` | Not integrated | Replaces old canvas; all 8 bugs fixed (BOM, beat map, spacing) |
| Beat markers | Wrong dotted-quarter `:-.,` | Corrected to `:-.'` per spec |
| Note spacing | Syllable + beat marker concatenated | Space-separated `syl + ' ' + marker` |
| XML import error | `"not well-formed (invalid token): line 1, col 2"` | BOM stripped before parse |
| `OctaveMarkMode` | Missing module crash | Enum stub with `POSITIONAL / ASCII / OFF` |
| `StyleRegistry` / `SolfaStyleRenderer` | Missing module crash | Functional stubs with `note_token()` |
| `AudioConfig` / `Instrument` | Missing module crash | Full additive-synthesis engine |
| `FontStylesManager` | Missing module crash | Preset-based font manager with persistence |
| `LyricsManager` | Missing module crash | Syllable store with embedded editor panel |

---

## 5. Common Errors & Fixes

| Error | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'solfa_canvas'` | Ensure `solfa_canvas.py` and `solfa_canvas_pro.py` are in the **same folder** as `solfadee_studio.py` |
| `ModuleNotFoundError: No module named 'reportlab'` | `pip install reportlab` |
| `not well-formed (invalid token): line 1, column 2` | Fixed in `solfa_canvas_pro.py` — BOM is now stripped |
| `AttributeError: 'NoneType' object has no attribute 'get'` | `StyleRegistry` stub not loaded — check `tonic_solfa_style_engine.py` is present |
| App opens but Solfa Canvas tab is blank | Click **"⟳ Sync from Score"** button or import a MusicXML file |
| PDF export crashes | `pip install reportlab` then retry |

---

## 6. Solfa Canvas Pro — Key Fixes Summary

All fixes from the Four-Agent review are in `solfa_canvas_pro.py`:

1. **BOM / XML import error** — raw bytes read, BOM stripped before `ET.fromstring()`
2. **Beat marker table** — all 8 tiers correct per spec (dotted quarter = `:-.'`)
3. **Note spacing canvas** — `syl + ' ' + beat_marker` with 6px left inset
4. **Live text view** — double-space between notes, column width 22→28
5. **PDF note spacing** — syllable/marker split, 1mm left inset per slot
6. **NoteEditDialog** — combobox updated to exact 8-tier beat options
7. **Row height** — 88px → 96px breathing room
8. **PDF slot** — 0.5mm → 1.0mm per-note left inset

---

## 7. Re-building After Changes

If you edit `solfadee_v5.py` later:
```bash
python3 combine_studio.py solfadee_v5.py
# Then re-run:
python3 solfadee_studio.py
```

Or use the **"Combine (rebuild studio)"** VS Code launch config (F5 with that config selected).
