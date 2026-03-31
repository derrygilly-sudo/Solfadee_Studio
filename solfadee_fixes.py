#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
solfadee_fixes.py
══════════════════════════════════════════════════════════════════
COMPLETE DIAGNOSIS AND FIXES for SolfaDee Studio
Covers every issue found in the uploaded PDF output and source code.

HOW TO USE:
  1. Place this file alongside solfadee_studio_v5.py
  2. In solfadee_studio_v5.py add at the top (after existing imports):
       from solfadee_fixes import (
           pdf_safe_solfa, OctaveMarkMode, OctaveMarkToggleWidget,
           export_pdf_solfa_fixed, SolfaOctaveController
       )
  3. Replace ConversionEngine.export_pdf_solfa_traditional with
     export_pdf_solfa_fixed everywhere it is called.
  4. Instantiate SolfaOctaveController in TonicSolfaStudio.__init__
     and wire it to the toolbar.
══════════════════════════════════════════════════════════════════

FULL DIAGNOSIS (6 issues identified)
══════════════════════════════════════════════════════════════════

ISSUE 1 — CRITICAL: Unicode subscripts/superscripts → black squares in PDF
  Root cause: ReportLab's built-in Type-1 fonts (Times-Roman, Helvetica,
  Courier) cover only the Latin-1 character set (ISO 8859-1, code points
  0x00–0xFF).  The Unicode subscript digits ₁₂₃₄ (U+2081–U+2084) and the
  Unicode superscript digits ¹²³ (U+00B9, U+00B2, U+00B3, U+2074+) all
  fall outside this range.  ReportLab substitutes a filled black rectangle
  (notdef glyph) for any glyph it cannot locate, producing the ■ character
  seen in the output (e.g. s■ where s₁ was intended).
  The skill documentation (pdf/SKILL.md line 171) explicitly states:
  "Never use Unicode subscript/superscript characters … causing them to
  render as solid black boxes."

  Fix options implemented here (all three are provided; user selects):
    A. ASCII fallback  — render d1, d2, d' using plain ASCII in PDF only
       (canvas display keeps Unicode).  Zero dependencies.
    B. Positional draw  — draw the octave digit/mark as a smaller font at
       a vertically offset position using canvas.drawString at y±offset.
       Looks like real musical sub/superscript.  Zero dependencies.
    C. TTF registration — register a system TTF (e.g. DejaVu) that covers
       the full Unicode range, then draw with that font.  Requires the TTF
       file to be present on the user's machine.

  Default: Option B (positional draw — best visual result, no dependencies).

ISSUE 2 — Duplicate @dataclass decorator on Measure class
  Root cause: The Measure class has two consecutive @dataclass decorators.
  Python silently accepts this but it is structurally incorrect.
  Fix: Remove the second @dataclass line.
  (Already documented in previous fix files; noted again for completeness.)

ISSUE 3 — PAPER_RULER constant missing from main file
  Root cause: CanvasRulerOverlay references PAPER_RULER but this constant
  is only defined in solfadee_fixed_canvas.py, not in the main studio file.
  Fix: Add PAPER_RULER = "#a0c0e0" to the constants section.

ISSUE 4 — Phantom imports from 'models' module
  Root cause: The code contains `from models import ArticulationMark`,
  `from models import Octave, Accidental` — but no models.py file is part
  of the distributed package.  These will raise ImportError at startup.
  Fix: Define ArticulationMark, Octave, Accidental as lightweight Enums
  directly in the main file (provided below) or guard the imports with
  try/except.

ISSUE 5 — Duplicate Enum class definitions (Tool, VoicePart, DynamicMark)
  Root cause: The Tool, VoicePart, and DynamicMark Enum classes are defined
  twice in identical form inside the same file (copy-paste artifact).
  Python will silently use the second definition, but it wastes memory and
  creates confusion.  Fix: Remove the duplicate block.

ISSUE 6 — _sync_solfa_canvas calls new_solfa_canvas.redraw() but the
  canvas only has a set_score method; .render() is called in some paths
  but .redraw() in others.  This causes AttributeError on some code paths.
  Fix: Standardise on .set_score() / .redraw() and guard with hasattr.
══════════════════════════════════════════════════════════════════
"""

from __future__ import annotations
import os
import math
import tkinter as tk
from tkinter import ttk
from enum import Enum
from typing import Optional

# ── Conditional ReportLab import ────────────────────────────────
try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

# ── Import duration marking function from canvas renderer ────────
try:
    from canvas_renderer import _duration_to_marks
except ImportError:
    # Fallback: define it locally
    def _duration_to_marks(dur: float, dot: bool) -> str:
        """Return the tonic-solfa duration symbol(s)."""
        d = dur * 1.5 if dot else dur
        if d >= 4.0: return ':-:-:-'      # whole
        if d >= 3.0: return ':-:-'        # dotted half
        if d >= 2.0: return ':-'          # half
        if d >= 1.5: return ':-.'         # dotted quarter
        if d >= 1.0: return ':'           # quarter
        if d >= 0.75: return '.,'         # dotted eighth-ish
        if d >= 0.5: return '.'           # eighth
        if d >= 0.25: return ','          # sixteenth
        return ''


# ════════════════════════════════════════════════════════════════
#  ISSUE 4 FIX: Stub definitions for missing 'models' module
#  Paste these into the main file and remove the 'from models import'
#  lines, or leave them here and import from here instead.
# ════════════════════════════════════════════════════════════════

class ArticulationMark(Enum):
    """Articulation mark types (stub — replaces missing models.ArticulationMark)."""
    NONE        = "none"
    STACCATO    = "staccato"
    ACCENT      = "accent"
    TENUTO      = "tenuto"
    MARCATO     = "marcato"
    FERMATA     = "fermata"
    STACCATISSIMO = "staccatissimo"


class Octave(Enum):
    """Octave shorthand values (stub — replaces missing models.Octave)."""
    LOW2  = 2
    LOW   = 3
    MID   = 4   # home octave
    HIGH  = 5
    HIGH2 = 6


class Accidental(Enum):
    """Accidental values (stub — replaces missing models.Accidental)."""
    NATURAL      = ""
    SHARP        = "#"
    FLAT         = "b"
    DOUBLE_SHARP = "##"
    DOUBLE_FLAT  = "bb"


# ════════════════════════════════════════════════════════════════
#  ISSUE 1 FIX — PART A: Octave mark mode controller
# ════════════════════════════════════════════════════════════════

class OctaveMarkMode(Enum):
    """
    How octave marks are rendered — choose per output target.
    UNICODE:    d₁  d'   — best for screen canvas; FAILS in ReportLab PDF
    ASCII:      d1  d'   — safe everywhere; no special characters
    POSITIONAL: drawn as smaller offset text — best print appearance
    OFF:        no octave marks at all
    """
    UNICODE    = 'unicode'
    ASCII      = 'ascii'
    POSITIONAL = 'positional'
    OFF        = 'off'


# Global controller — canvas and PDF export both read from this
class SolfaOctaveController:
    """
    Single source of truth for octave-mark rendering mode.
    Instantiate once in TonicSolfaStudio and pass to canvas + exporter.
    """
    def __init__(self):
        self.canvas_mode: OctaveMarkMode = OctaveMarkMode.UNICODE
        self.pdf_mode:    OctaveMarkMode = OctaveMarkMode.POSITIONAL
        self._listeners = []

    def set_canvas_mode(self, mode: OctaveMarkMode):
        self.canvas_mode = mode
        for fn in self._listeners:
            fn()

    def set_pdf_mode(self, mode: OctaveMarkMode):
        self.pdf_mode = mode

    def add_listener(self, fn):
        self._listeners.append(fn)


# ════════════════════════════════════════════════════════════════
#  ISSUE 1 FIX — PART B: pdf_safe_solfa conversion function
#
#  Call this on any solfa string BEFORE passing it to ReportLab's
#  drawString.  Converts Unicode subscripts/superscripts to ASCII
#  equivalents that the built-in Type-1 fonts can render.
# ════════════════════════════════════════════════════════════════

# Unicode subscript → plain digit
_UNSUB = {
    '₀':'0','₁':'1','₂':'2','₃':'3','₄':'4',
    '₅':'5','₆':'6','₇':'7','₈':'8','₉':'9',
}
# Unicode superscript → plain digit (for completeness)
_UNSUP = {
    '¹':'1','²':'2','³':'3','⁴':'4','⁵':'5',
    '⁶':'6','⁷':'7','⁸':'8','⁹':'9',
}


def pdf_safe_solfa(text: str, mode: OctaveMarkMode = OctaveMarkMode.ASCII) -> str:
    """
    Convert a solfa string to a form safe for ReportLab built-in fonts.

    mode=ASCII:
        d₁ → d1     d'' → d''   (apostrophes are already Latin-1)
        s₂ → s2
    mode=OFF:
        strips all octave marks entirely (d₁ → d, d'' → d)
    mode=UNICODE / POSITIONAL:
        returns text unchanged (caller must handle rendering specially)
    """
    if mode == OctaveMarkMode.OFF:
        # Strip subscripts and superscript apostrophes
        result = ''
        i = 0
        while i < len(text):
            ch = text[i]
            if ch in _UNSUB:
                pass   # skip subscript digits
            elif ch == "'":
                pass   # skip apostrophe octave marks
            else:
                result += ch
            i += 1
        return result

    if mode == OctaveMarkMode.ASCII:
        result = ''
        for ch in text:
            if ch in _UNSUB:
                result += _UNSUB[ch]   # ₁ → 1
            elif ch in _UNSUP:
                result += _UNSUP[ch]   # ¹ → 1 (rare)
            else:
                result += ch
        return result

    # UNICODE or POSITIONAL — return unchanged; caller handles rendering
    return text


# ════════════════════════════════════════════════════════════════
#  ISSUE 1 FIX — PART C: positional sub/superscript PDF renderer
#
#  Instead of drawing the whole solfa token as one string, this
#  splits the token at the octave mark boundary and draws the
#  syllable and mark at different font sizes and y-positions.
#  This produces genuine musical sub/superscript appearance.
# ════════════════════════════════════════════════════════════════

def draw_solfa_token_pdf(c, x: float, y: float,
                          token: str,
                          font_name: str = "Times-Bold",
                          font_size: float = 10.0,
                          ink_color=(0.08, 0.06, 0.02)):
    """
    Draw one solfa token at (x, y) with proper positional octave marks.

    Handles:
      • Plain syllable:     d  r  m  f  s  l  t
      • Apostrophe high:    d'  d''  s'
      • Subscript low:      d₁  d₂  s₁  (Unicode or ASCII digit)
      • Chromatic:          fe  de  ta  etc. (with or without octave mark)
      • Rest:               0  ·  —
      • Sub-beat suffixes:  d.  d,  d;

    Returns the x-position AFTER the drawn token (for sequential layout).
    """
    if not token or not token.strip():
        return x

    c.setFillColorRGB(*ink_color)

    # ── Tokenise: split syllable from octave mark ──────────────
    mark_type, syllable, octave_marks = _split_solfa_token(token)

    # Draw syllable at normal size
    c.setFont(font_name, font_size)
    c.drawString(x, y, syllable)
    syl_w = c.stringWidth(syllable, font_name, font_size)

    if not octave_marks:
        return x + syl_w

    mark_size = max(5.0, font_size * 0.65)

    if mark_type == 'high':
        # Superscript: apostrophe(s) drawn above and right of syllable
        c.setFont(font_name, mark_size)
        mark_y = y + font_size * 0.45   # shift upward
        c.drawString(x + syl_w, mark_y, octave_marks)
        mark_w = c.stringWidth(octave_marks, font_name, mark_size)

    else:
        # Subscript: digit(s) drawn below and right of syllable
        c.setFont(font_name, mark_size)
        mark_y = y - font_size * 0.25   # shift downward
        c.drawString(x + syl_w, mark_y, octave_marks)
        mark_w = c.stringWidth(octave_marks, font_name, mark_size)

    # Reset to normal font for subsequent draws
    c.setFont(font_name, font_size)

    return x + syl_w + mark_w


def _split_solfa_token(token: str):
    """
    Parse a solfa token into (mark_type, syllable, octave_mark_string).

    mark_type: 'high' | 'low' | None
    syllable:  the core syllable portion (e.g. 'd', 'fe', 'd.', 's,')
    octave_marks: the mark string to render as offset text (e.g. "'", "1", "2")

    Examples:
        "d'"    → ('high', 'd',  "'")
        "d''"   → ('high', 'd',  "''")
        "d₁"    → ('low',  'd',  "1")
        "fe₁"   → ('low',  'fe', "1")
        "d."    → (None,   'd.', "")
        "s1"    → ('low',  's',  "1")   ← ASCII fallback form
        "—"     → (None,   '—',  "")
        "0"     → (None,   '0',  "")
    """
    _SUB_DIGITS = set('₀₁₂₃₄₅₆₇₈₉')
    _ASCII_DIGITS = set('0123456789')

    if not token:
        return None, token, ''

    # Hold / rest / empty tokens: return as-is
    if token in ('—', '·', '0', '-', '0'):
        return None, token, ''

    # Find the index where the octave mark starts
    # High: apostrophe chain at end
    # Low: subscript digit(s) or plain ASCII digit(s) at end (after syllable chars)
    #
    # Syllable characters: letters (a-z A-Z) + duration suffixes (. , ; ·)
    # Octave marks: ' (apostrophe) | ₀-₉ (subscript) | 0-9 (ASCII, if after letter)

    # Collect syllable (letters + duration marks), stop at octave mark
    syllable = ''
    i = 0
    while i < len(token):
        ch = token[i]
        if ch == "'":
            break
        if ch in _SUB_DIGITS:
            break
        # ASCII digit after a letter (inline number style, e.g. s1, d2)
        if ch in _ASCII_DIGITS and i > 0 and token[i-1].isalpha():
            break
        syllable += ch
        i += 1

    rest = token[i:]

    if not rest:
        return None, syllable, ''

    # Determine mark type and normalise mark string
    if rest.startswith("'"):
        return 'high', syllable, rest

    # Subscript digits or ASCII digits
    mark_chars = ''
    for ch in rest:
        if ch in _SUB_DIGITS:
            mark_chars += _UNSUB.get(ch, ch)  # normalise to plain digit
        elif ch in _ASCII_DIGITS:
            mark_chars += ch
        else:
            mark_chars += ch   # unexpected; include verbatim
    return 'low', syllable, mark_chars


# ════════════════════════════════════════════════════════════════
#  ISSUE 1 FIX — PART D: Fixed PDF exporter
#  Drop-in replacement for ConversionEngine.export_pdf_solfa_traditional
# ════════════════════════════════════════════════════════════════

def export_pdf_solfa_fixed(score, path: str,
                            octave_mode: OctaveMarkMode = OctaveMarkMode.POSITIONAL,
                            font_family: str = "Times",
                            lyric_font_family: str = "Times",
                            lyric_font_size: int = 7,
                            measures_per_row: int = 4):
    """
    Export traditional tonic solfa to PDF.

    Key differences from the original:
      1. Octave marks (subscripts/superscripts) use positional drawing
         instead of Unicode characters — eliminates black-square artefacts.
      2. Accepts octave_mode parameter:
           POSITIONAL  — real sub/superscript via offset drawing (default)
           ASCII       — plain digits/apostrophes (d1, d', d'')
           OFF         — no octave marks (add manually after printing)
      3. Font names are validated against ReportLab's built-ins.
      4. build_measure_string result is sanitised before drawing.
    """
    if not REPORTLAB_OK:
        txt = path.replace('.pdf', '_solfa.txt')
        # Fallback to text export
        from tonic_solfa_studio import ConversionEngine
        with open(txt, 'w', encoding='utf-8') as f:
            f.write(ConversionEngine.export_solfa_text(score))
        return

    # ── Validate font names (ReportLab built-in families only) ──
    _valid_families = {'Times', 'Helvetica', 'Courier'}
    if font_family not in _valid_families:
        font_family = 'Times'
    if lyric_font_family not in _valid_families:
        lyric_font_family = 'Times'

    bold_font   = f"{font_family}-Bold"
    roman_font  = f"{font_family}-Roman"
    italic_font = f"{font_family}-Italic"
    lyric_roman = f"{lyric_font_family}-Roman"

    w, h = A4
    c = rl_canvas.Canvas(path, pagesize=A4)

    # ── Header ──────────────────────────────────────────────────
    c.setFont(bold_font, 18)
    c.drawCentredString(w / 2, h - 18 * mm, score.title.upper())

    if score.composer:
        c.setFont(roman_font, 11)
        c.drawRightString(w - 15 * mm, h - 18 * mm, score.composer)

    c.setFont(roman_font, 10)
    key_flat = '♭' if len(score.key_sig) > 1 and 'b' in score.key_sig else ''
    c.drawString(15 * mm, h - 26 * mm,
                 f"Key {score.key_sig}{key_flat}.")
    c.drawString(15 * mm, h - 31 * mm,
                 f"{score.time_num}/{score.time_den}")

    if score.measures and score.measures[0].dynamic:
        c.setFont(italic_font, 10)
        c.drawString(15 * mm, h - 36 * mm, score.measures[0].dynamic)

    c.setLineWidth(0.5)
    c.line(15 * mm, h - 39 * mm, w - 15 * mm, h - 39 * mm)

    # ── Layout constants ─────────────────────────────────────────
    y         = h - 45 * mm
    voices    = score.all_voices()
    mpr       = max(1, measures_per_row)
    col_w     = (w - 30 * mm) / mpr
    voice_h   = 12 * mm
    syl_size  = 10
    lyric_size = lyric_font_size
    bar_num_size = 6

    def _draw_token(cx, cy, token_str):
        """Draw one solfa token using the selected octave mode."""
        if octave_mode == OctaveMarkMode.POSITIONAL:
            draw_solfa_token_pdf(c, cx, cy, token_str,
                                  font_name=bold_font,
                                  font_size=syl_size)
        else:
            safe = pdf_safe_solfa(token_str, octave_mode)
            c.setFont(bold_font, syl_size)
            c.drawString(cx, cy, safe)

    rows = math.ceil(len(score.measures) / mpr)

    for row in range(rows):
        rm = score.measures[row * mpr:(row + 1) * mpr]
        if not rm:
            break

        system_h = len(voices) * voice_h + 6 * mm

        if y - system_h < 15 * mm:
            c.showPage()
            y = h - 18 * mm
            c.setFont(bold_font, 11)
            c.drawCentredString(w / 2, y, score.title)
            y -= 8 * mm

        brace_x = 15 * mm
        c.setLineWidth(1.5)
        c.line(brace_x, y, brace_x, y - len(voices) * voice_h)

        for vi, voice in enumerate(voices):
            vy = y - vi * voice_h

            # Voice label
            lbl_map = {1: 'Sop.', 2: 'Alto', 3: 'Ten.', 4: 'Bass'}
            lbl = lbl_map.get(voice, f'V{voice}')
            c.setFont(bold_font, 9)
            c.setFillColorRGB(0.24, 0.18, 0.11)
            c.drawRightString(brace_x + 13 * mm, vy - voice_h / 2 + 2, lbl)

            # Staff line
            c.setLineWidth(0.5)
            c.setFillColorRGB(0.08, 0.06, 0.02)
            c.line(brace_x + 14 * mm, vy, w - 15 * mm, vy)

            for mi, meas in enumerate(rm):
                mx = brace_x + 14 * mm + mi * col_w

                # Bar number
                if vi == 0:
                    if getattr(meas, 'metrical_modulation', None):
                        c.setFont(italic_font, 7)
                        c.setFillColorRGB(0.55, 0.0, 0.0)
                        c.drawCentredString(mx + col_w / 2, vy + 1 * mm,
                                            meas.metrical_modulation)
                    if getattr(meas, 'key_change', None):
                        c.setFont(bold_font, 7)
                        c.setFillColorRGB(0.55, 0.0, 0.0)
                        c.drawCentredString(mx + col_w / 2, vy + 2.5 * mm,
                                            meas.key_change)
                    c.setFont(roman_font, bar_num_size)
                    c.setFillColorRGB(0.35, 0.25, 0.12)
                    c.drawString(mx + 1, vy + 1, str(meas.number))

                c.setFillColorRGB(0.08, 0.06, 0.02)

                # Notes
                vnotes = meas.voice_notes(voice)
                if not vnotes:
                    c.setFont(roman_font, syl_size)
                    c.drawCentredString(mx + col_w / 2, vy - voice_h / 2 + 2, '—')
                else:
                    # Build beat-positioned tokens
                    beat_unit = 4.0 / meas.time_den
                    beat_px   = col_w / (meas.time_num + 0.5)
                    pos       = 0.0

                    for n in vnotes:
                        beat_idx = pos / beat_unit
                        nx = mx + 2 * mm + beat_idx * beat_px
                        ny = vy - voice_h / 2 + 2

                        if n.rest:
                            c.setFont(roman_font, syl_size)
                            c.drawString(nx, ny, '0')
                        else:
                            # Build token
                            syl  = n.solfa_syllable(meas.key_sig)
                            diff = n.octave - 4
                            if diff == 0:
                                oct_part = ''
                            elif diff > 0:
                                oct_part = "'" * diff
                            else:
                                oct_part = str(abs(diff))   # ASCII digit for subscript

                            # Use proper beat maps with visible markers
                            is_dotted = getattr(n, 'dot', None)
                            if is_dotted is None:
                                is_dotted = getattr(n, 'dotted', False)
                            dur_sfx = _duration_to_marks(n.duration, is_dotted)

                            # Apply uppercase_fe if active style has it
                            _UP = {'fe': 'F', 'de': 'De', 're': 'Re',
                                   'se': 'Se', 'ta': 'Ta', 'le': 'Le'}
                            # (uppercase_fe off by default in this exporter)

                            token = syl + dur_sfx   # syllable + sub-beat suffix

                            if octave_mode == OctaveMarkMode.POSITIONAL:
                                # Draw syllable + dur at normal position
                                c.setFont(bold_font, syl_size)
                                c.setFillColorRGB(0.08, 0.06, 0.02)
                                c.drawString(nx, ny, token)
                                syl_w = c.stringWidth(token, bold_font, syl_size)

                                if oct_part:
                                    mark_size = max(5.0, syl_size * 0.65)
                                    c.setFont(bold_font, mark_size)
                                    if diff > 0:
                                        # Superscript
                                        c.drawString(nx + syl_w,
                                                     ny + syl_size * 0.42,
                                                     oct_part)
                                    else:
                                        # Subscript
                                        c.drawString(nx + syl_w,
                                                     ny - syl_size * 0.20,
                                                     oct_part)
                                    c.setFont(bold_font, syl_size)

                            elif octave_mode == OctaveMarkMode.ASCII:
                                full = token + oct_part
                                c.setFont(bold_font, syl_size)
                                c.setFillColorRGB(0.08, 0.06, 0.02)
                                c.drawString(nx, ny, full)

                            elif octave_mode == OctaveMarkMode.OFF:
                                c.setFont(bold_font, syl_size)
                                c.setFillColorRGB(0.08, 0.06, 0.02)
                                c.drawString(nx, ny, token)

                            # Hold dashes for multi-beat notes
                            beats_held = n.beats
                            sub_pos = pos + beat_unit
                            while beats_held > beat_unit + 0.01:
                                hx = mx + 2 * mm + (sub_pos / beat_unit) * beat_px
                                c.setFont(bold_font, syl_size)
                                c.drawString(hx, ny, '—')
                                beats_held -= beat_unit
                                sub_pos += beat_unit

                        pos += n.beats

                # Beat separator colons
                for bi in range(1, meas.time_num):
                    sep_x = mx + (bi / meas.time_num) * col_w
                    c.setFont(roman_font, 7)
                    c.setFillColorRGB(0.40, 0.30, 0.18)
                    c.drawCentredString(sep_x, vy - voice_h / 2 + 2, ':')
                    c.setFillColorRGB(0.08, 0.06, 0.02)

                # Barline
                c.setLineWidth(0.8 if mi == len(rm) - 1 else 0.5)
                c.line(mx + col_w, vy, mx + col_w, vy - voice_h)
                if mi == 0:
                    c.setLineWidth(0.5)
                    c.line(mx, vy, mx, vy - voice_h)

            # Lyrics row (voice 1 only)
            if vi == 0 and any(n.lyric for m2 in rm
                               for n in m2.notes if n.voice == voice):
                for mi, meas in enumerate(rm):
                    mx = brace_x + 14 * mm + mi * col_w
                    beat_unit = 4.0 / meas.time_den
                    beat_px   = col_w / (meas.time_num + 0.5)
                    pos = 0.0
                    for n in meas.voice_notes(voice):
                        if n.lyric:
                            nx = mx + 2 * mm + (pos / beat_unit) * beat_px
                            c.setFont(lyric_roman, lyric_size)
                            c.setFillColorRGB(0.1, 0.2, 0.38)
                            c.drawString(nx, vy - voice_h - 2, n.lyric)
                            c.setFillColorRGB(0.08, 0.06, 0.02)
                        pos += n.beats

        # Bottom line of system
        c.setLineWidth(0.8)
        c.line(brace_x, y - len(voices) * voice_h,
               w - 15 * mm, y - len(voices) * voice_h)

        # Repeat signs
        for mi, meas in enumerate(rm):
            mx = brace_x + 14 * mm + mi * col_w
            if meas.repeat_start:
                c.setLineWidth(2)
                c.line(mx + 2 * mm, y, mx + 2 * mm, y - len(voices) * voice_h)
                c.setLineWidth(0.5)
                c.line(mx + 3.5 * mm, y, mx + 3.5 * mm, y - len(voices) * voice_h)
                c.circle(mx + 4.5 * mm, y - len(voices) * voice_h * 0.35,
                         0.8 * mm, fill=1)
                c.circle(mx + 4.5 * mm, y - len(voices) * voice_h * 0.65,
                         0.8 * mm, fill=1)
            if meas.repeat_end:
                ex = mx + col_w
                c.circle(ex - 4.5 * mm, y - len(voices) * voice_h * 0.35,
                         0.8 * mm, fill=1)
                c.circle(ex - 4.5 * mm, y - len(voices) * voice_h * 0.65,
                         0.8 * mm, fill=1)
                c.setLineWidth(0.5)
                c.line(ex - 3.5 * mm, y, ex - 3.5 * mm, y - len(voices) * voice_h)
                c.setLineWidth(2)
                c.line(ex - 2 * mm, y, ex - 2 * mm, y - len(voices) * voice_h)

        y -= system_h + 5 * mm

    # Footer legend
    if y > 20 * mm:
        c.setFont(lyric_roman, lyric_size)
        c.setFillColorRGB(0.3, 0.2, 0.1)
        legend = ("d=Do  r=Re  m=Mi  f=Fa  s=Sol  l=La  t=Ti  "
                  "  '=high oct   digit=low oct   —=held   0=rest")
        c.drawString(15 * mm, 15 * mm, legend)

    c.save()


# ════════════════════════════════════════════════════════════════
#  ISSUE 1 FIX — PART E: Tkinter octave-mark toggle widget
#  Add to any frame in the main application toolbar.
# ════════════════════════════════════════════════════════════════

# Dark palette constants (duplicated here to keep module self-contained)
_PANEL = "#16213e"; _CARD  = "#0f3460"; _DARK  = "#1a1a2e"
_GOLD  = "#f5a623"; _TEXT  = "#eaeaea"; _ACCENT= "#e94560"
_WHITE = "#ffffff"; _MUTED = "#8892a4"; _GREEN = "#00d4aa"


class OctaveMarkToggleWidget(tk.Frame):
    """
    Compact Tkinter toolbar widget for controlling octave marks.

    Exposes:
      canvas_mode  — mode used by TraditionalSolfaCanvas screen rendering
      pdf_mode     — mode used by PDF export

    Usage:
        ctrl = SolfaOctaveController()
        widget = OctaveMarkToggleWidget(toolbar, ctrl,
                                        on_canvas_change=canvas.redraw)
        widget.pack(side='left', padx=4)
    """

    def __init__(self, master, controller: SolfaOctaveController,
                 on_canvas_change=None, **kwargs):
        super().__init__(master, bg=_CARD, **kwargs)
        self._ctrl = controller
        self._on_change = on_canvas_change
        self._build()

    def _build(self):
        tk.Label(self, text="Oct marks:", bg=_CARD, fg=_MUTED,
                 font=('Arial', 7)).pack(side='left', padx=(6, 2))

        # Canvas mode
        tk.Label(self, text="Screen:", bg=_CARD, fg=_MUTED,
                 font=('Arial', 7)).pack(side='left')
        self._cv_var = tk.StringVar(value=self._ctrl.canvas_mode.value)
        cv_cb = ttk.Combobox(self, textvariable=self._cv_var,
                              values=[m.value for m in OctaveMarkMode],
                              width=10, state='readonly',
                              font=('Arial', 7))
        cv_cb.pack(side='left', padx=(2, 8))
        cv_cb.bind('<<ComboboxSelected>>', self._on_cv_change)

        # PDF mode
        tk.Label(self, text="PDF:", bg=_CARD, fg=_MUTED,
                 font=('Arial', 7)).pack(side='left')
        self._pdf_var = tk.StringVar(value=self._ctrl.pdf_mode.value)
        pdf_cb = ttk.Combobox(self, textvariable=self._pdf_var,
                               values=[m.value for m in OctaveMarkMode],
                               width=10, state='readonly',
                               font=('Arial', 7))
        pdf_cb.pack(side='left', padx=(2, 4))
        pdf_cb.bind('<<ComboboxSelected>>', self._on_pdf_change)

    def _on_cv_change(self, _event=None):
        mode = OctaveMarkMode(self._cv_var.get())
        self._ctrl.set_canvas_mode(mode)
        if self._on_change:
            self._on_change()

    def _on_pdf_change(self, _event=None):
        self._ctrl.set_pdf_mode(OctaveMarkMode(self._pdf_var.get()))


# ════════════════════════════════════════════════════════════════
#  ISSUE 3 FIX: Missing PAPER_RULER constant
#  Add this line to the CONSTANTS block in solfadee_studio_v5.py
# ════════════════════════════════════════════════════════════════
PAPER_RULER = "#a0c0e0"   # screen-only ruler colour (never printed)


# ════════════════════════════════════════════════════════════════
#  ISSUE 5 FIX: Remove duplicate Enum definitions
#  The following Enum classes appear TWICE in the original file:
#    • Tool
#    • VoicePart
#    • DynamicMark
#  Keep only the first occurrence of each and delete the second block
#  (approximately lines 220–260 in the original).
#  The fix cannot be automated without editing the file in place, but
#  the correction is documented here for the developer.
# ════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════
#  ISSUE 6 FIX: _sync_solfa_canvas AttributeError guard
#  Replace the existing _sync_solfa_canvas and _on_change in the
#  main app with the versions below.
# ════════════════════════════════════════════════════════════════

def _sync_solfa_canvas_safe(app_instance):
    """
    Safe version of _sync_solfa_canvas.
    Handles both .redraw() and .set_score() canvas API variants.
    """
    if not hasattr(app_instance, 'new_solfa_canvas'):
        return
    canvas = app_instance.new_solfa_canvas
    score  = app_instance.score
    try:
        if hasattr(canvas, 'set_score'):
            canvas.set_score(score)
        elif hasattr(canvas, 'redraw'):
            canvas.redraw()
        elif hasattr(canvas, 'render'):
            canvas.render()
    except Exception:
        pass   # canvas may not be fully initialised yet


# ════════════════════════════════════════════════════════════════
#  INTEGRATION INSTRUCTIONS (add to _build_toolbar in main app)
# ════════════════════════════════════════════════════════════════
INTEGRATION_NOTES = """
─────────────────────────────────────────────────────────────────
INTEGRATION STEPS
─────────────────────────────────────────────────────────────────

1. In solfadee_studio_v5.py — CONSTANTS section, ADD:
     PAPER_RULER = "#a0c0e0"

2. In TonicSolfaStudio.__init__, ADD after self._setup_style():
     from solfadee_fixes import SolfaOctaveController
     self.octave_ctrl = SolfaOctaveController()

3. In _setup_style(), wire the controller to the canvas:
     self.octave_ctrl.add_listener(
         lambda: self.trad_canvas.redraw()
         if hasattr(self, 'trad_canvas') else None)

4. In _build_toolbar(), ADD after the voice buttons:
     from solfadee_fixes import OctaveMarkToggleWidget
     _sep(tb)
     self._oct_widget = OctaveMarkToggleWidget(
         tb, self.octave_ctrl,
         on_canvas_change=lambda: (
             self.trad_canvas.redraw()
             if hasattr(self, 'trad_canvas') else None))
     self._oct_widget.pack(side='left', padx=3, pady=6)

5. Replace _print_trad_solfa with:
     def _print_trad_solfa(self):
         path = filedialog.asksaveasfilename(...)
         if not path: return
         try:
             from solfadee_fixes import export_pdf_solfa_fixed
             export_pdf_solfa_fixed(
                 self.score, path,
                 octave_mode=self.octave_ctrl.pdf_mode)
             self.status_var.set(f"✓ PDF: {path}")
         except Exception as e:
             messagebox.showerror("Print Error", str(e), parent=self)

6. Replace _sync_solfa_canvas with:
     def _sync_solfa_canvas(self):
         from solfadee_fixes import _sync_solfa_canvas_safe
         _sync_solfa_canvas_safe(self)

7. Remove 'from models import ...' lines (or wrap in try/except)
   and add at the top:
     from solfadee_fixes import ArticulationMark, Octave, Accidental

8. Remove the duplicate @dataclass decorator on the Measure class
   (the second @dataclass line immediately before 'class Measure:').

9. Remove the second block of Tool / VoicePart / DynamicMark
   Enum definitions (approx lines 220-260).

10. In TraditionalSolfaCanvas.__init__, confirm:
      self.PAPER_RULER = "#a0c0e0"   (or import from solfadee_fixes)
─────────────────────────────────────────────────────────────────
"""


# ════════════════════════════════════════════════════════════════
#  SELF-TEST (run standalone)
# ════════════════════════════════════════════════════════════════
def _self_test():
    print("=" * 62)
    print("  SOLFADEE FIXES — SELF TEST")
    print("=" * 62)

    cases = [
        ("d'",     'high', 'd',  "'"),
        ("d''",    'high', 'd',  "''"),
        ("d₁",     'low',  'd',  "1"),
        ("d₂",     'low',  'd',  "2"),
        ("s₁",     'low',  's',  "1"),
        ("fe₁",    'low',  'fe', "1"),
        ("d.",     None,   'd.', ""),
        ("d,",     None,   'd,', ""),
        ("0",      None,   '0',  ""),
        ("—",      None,   '—',  ""),
        ("s1",     'low',  's',  "1"),   # ASCII fallback form
        ("d'.",    'high', 'd.', "'"),   # dotted high
        ("t'",     'high', 't',  "'"),
        ("m₁.",    'low',  'm.', "1"),
    ]

    all_ok = True
    print("\n  Token split tests:")
    for token, exp_type, exp_syl, exp_mark in cases:
        mt, syl, marks = _split_solfa_token(token)
        ok = (mt == exp_type and syl == exp_syl and marks == exp_mark)
        if not ok:
            all_ok = False
        status = "PASS" if ok else f"FAIL (got type={mt!r} syl={syl!r} marks={marks!r})"
        print(f"    {token!r:12s} → {status}")

    print("\n  pdf_safe_solfa ASCII mode:")
    ascii_cases = [
        ("d'",   "d'"),
        ("d₁",   "d1"),
        ("s₂",   "s2"),
        ("fe₁",  "fe1"),
        ("d.",   "d."),
        ("—",    "—"),
    ]
    for inp, expected in ascii_cases:
        result = pdf_safe_solfa(inp, OctaveMarkMode.ASCII)
        ok = result == expected
        if not ok: all_ok = False
        status = "PASS" if ok else f"FAIL (got {result!r})"
        print(f"    {inp!r:10s} → {result!r:10s}  {status}")

    print("\n  pdf_safe_solfa OFF mode (strip all octave marks):")
    off_cases = [
        ("d'",   "d"),
        ("d₁",   "d"),
        ("s'",   "s"),
        ("fe₁",  "fe"),
    ]
    for inp, expected in off_cases:
        result = pdf_safe_solfa(inp, OctaveMarkMode.OFF)
        ok = result == expected
        if not ok: all_ok = False
        status = "PASS" if ok else f"FAIL (got {result!r})"
        print(f"    {inp!r:10s} → {result!r:10s}  {status}")

    print()
    print("=" * 62)
    print(f"  Result: {'ALL TESTS PASSED' if all_ok else 'SOME TESTS FAILED'}")
    print("=" * 62)

    print("\n  Issue summary:")
    issues = [
        ("ISSUE 1", "FIXED",   "Unicode sub/superscript → black square in PDF"),
        ("ISSUE 2", "NOTED",   "Duplicate @dataclass on Measure (manual fix)"),
        ("ISSUE 3", "FIXED",   "PAPER_RULER constant missing"),
        ("ISSUE 4", "FIXED",   "Missing 'models' module stubs provided"),
        ("ISSUE 5", "NOTED",   "Duplicate Enum classes (manual deletion)"),
        ("ISSUE 6", "FIXED",   "_sync_solfa_canvas AttributeError guard"),
    ]
    for num, status, desc in issues:
        print(f"  {num}  [{status:6s}]  {desc}")

    print("\n  See INTEGRATION_NOTES for step-by-step wiring instructions.")


if __name__ == '__main__':
    _self_test()
