#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║   SOLFADEE STUDIO  v5.0  —  INTEGRATED                      ║
║   Professional Music Notation & Tonic Solfa Software         ║
║   Staff Notation ↔ Traditional Tonic Solfa  (SATB)           ║
║   MusicXML · MIDI · WAV · PDF · ABC · TSS Project            ║
║   Smart Entry · Full Keyboard Shortcuts · SATB Palettes      ║
║   ── Solfa Canvas PRO integrated (solfa_canvas_pro.py) ──    ║
╚══════════════════════════════════════════════════════════════╝

Install optional libs:
    pip install midiutil reportlab pygame pillow mido

Project layout (all files in same folder):
    solfadee_studio.py          ← this file  (main app)
    solfa_canvas_pro.py         ← fixed canvas (four-agent version)
    solfa_canvas.py             ← re-export bridge
    solfadee_fixes.py           ← OctaveMarkMode + export_pdf_solfa_fixed
    tonic_solfa_style_engine.py ← StyleRegistry + SolfaStyleRenderer
    font_styles_manager.py      ← FontStylesManager + FontStylesDialog
    lyrics_manager.py           ← LyricsManager + LyricsEditorPanel
    audio_engine.py             ← AudioConfig + AudioSynthesizer + WavFileWriter
    canvas_renderer.py          ← TonicSolfaCanvas stub
    pdf_exporter.py             ← TonicSolfaPDFExporter
    score_bridge.py             ← bridge_score_to_solfa
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import json, os, math, copy, struct, io, zipfile, time
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict

# ── External component integrations ──────────────────────────────────────────
# All modules live in the same folder. Wrapped in try/except so the app
# degrades gracefully if a stub hasn't been placed yet.
try:
    from font_styles_manager import FontStylesManager, FontStylesDialog
except ImportError:
    FontStylesManager = None          # type: ignore
    FontStylesDialog  = None          # type: ignore

try:
    from lyrics_manager import LyricsManager, LyricsEditorPanel
except ImportError:
    LyricsManager    = None           # type: ignore
    LyricsEditorPanel = None          # type: ignore

try:
    from audio_engine import AudioConfig, AudioSynthesizer, WavFileWriter, Instrument
except ImportError:
    AudioConfig      = None           # type: ignore
    AudioSynthesizer = None           # type: ignore
    WavFileWriter    = None           # type: ignore
    Instrument       = None           # type: ignore

try:
    from canvas_renderer import TonicSolfaCanvas
except ImportError:
    TonicSolfaCanvas = None           # type: ignore

# ── Core Solfa Canvas Pro ─────────────────────────────────────────────────────
try:
    from solfa_canvas_pro import (
        SolfaCanvas,
        SolfaScore,
        SolfaNote,
        SolfaMeasure,
        render_pdf as _render_solfa_pdf,  # the main-app alias
    )
except ImportError:
    from solfa_canvas import (
        SolfaCanvas,
        SolfaScore,
        SolfaNote,
        SolfaMeasure,
        render_pdf as _render_solfa_pdf,
    )
_render_pdf = _render_solfa_pdf       # second alias used in _export_new_pdf

try:
    from pdf_exporter import TonicSolfaPDFExporter
except ImportError:
    TonicSolfaPDFExporter = None      # type: ignore

try:
    from score_bridge import bridge_score_to_solfa
except ImportError:
    bridge_score_to_solfa = None      # type: ignore

try:
    from tonic_solfa_style_engine import StyleRegistry, SolfaStyleRenderer
except ImportError:
    StyleRegistry      = None         # type: ignore
    SolfaStyleRenderer = None         # type: ignore

try:
    from solfadee_fixes import export_pdf_solfa_fixed, OctaveMarkMode
except ImportError:
    export_pdf_solfa_fixed = None     # type: ignore
    OctaveMarkMode         = None     # type: ignore

# ── Guard: StyleRegistry / SolfaStyleRenderer fallbacks ──────────────────────
# Used in _setup_style(); if the real module is missing we use a no-op class.
if StyleRegistry is None:
    class StyleRegistry:                          # type: ignore
        def get(self, name):
            return {}
if SolfaStyleRenderer is None:
    class SolfaStyleRenderer:                     # type: ignore
        def __init__(self, style=None): pass
        def note_token(self, note, key="C"):
            try:   return note.solfa(key) + " :"
            except: return "? :"

# ── Guard: OctaveMarkMode fallback ────────────────────────────────────────────
if OctaveMarkMode is None:
    from enum import Enum
    class OctaveMarkMode(Enum):                   # type: ignore
        POSITIONAL = "POSITIONAL"
        ASCII      = "ASCII"
        OFF        = "OFF"

# ── Guard: AudioConfig / Instrument fallbacks ─────────────────────────────────
if AudioConfig is None:
    class AudioConfig:                            # type: ignore
        def __init__(self, **kw):
            self.tempo_bpm = kw.get("tempo_bpm", 120)
            self.instrument = None
if Instrument is None:
    class Instrument:                             # type: ignore
        PIANO = "piano"
if AudioSynthesizer is None:
    class AudioSynthesizer:                       # type: ignore
        def __init__(self, cfg): pass
        def generate_from_score(self, score): return []
if WavFileWriter is None:
    class WavFileWriter:                          # type: ignore
        @staticmethod
        def write_wav(path, samples, cfg): pass

# ── Guard: FontStylesManager / FontStylesDialog fallbacks ─────────────────────
if FontStylesManager is None:
    class FontStylesManager:                      # type: ignore
        pass
if FontStylesDialog is None:
    def FontStylesDialog(parent, mgr):            # type: ignore
        messagebox.showinfo("Font Styles", "font_styles_manager.py not found.", parent=parent)

# ── Guard: LyricsManager / LyricsEditorPanel fallbacks ────────────────────────
if LyricsManager is None:
    class LyricsManager:                          # type: ignore
        pass
if LyricsEditorPanel is None:
    class LyricsEditorPanel(tk.Frame):            # type: ignore
        def __init__(self, master, mgr, **kw):
            super().__init__(master, **kw)
            tk.Label(self, text="lyrics_manager.py not found.").pack()

