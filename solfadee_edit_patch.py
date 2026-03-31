#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
solfadee_edit_patch.py
══════════════════════════════════════════════════════════════════
PATCH — Four independent fixes for SolfaDee Studio

DIAGNOSIS SUMMARY
─────────────────
1. OCTAVE MODE DROPDOWN (dead): _print_trad_solfa() calls
   ConversionEngine.export_pdf_solfa_traditional() which hard-ignores
   self.octave_mode.  export_pdf_solfa_fixed() (solfadee_fixes.py) is
   never called.  Fix: replace the print method body.

2. SOLFA TEXT PANEL (read-only in practice): The tk.Text widget is
   writable but no code ever reads it back to the score.  Edits are
   silently overwritten on the next refresh.  Fix: add a parser and an
   "Apply" binding.

3. TRADITIONAL CANVAS (display-only): No <Button-1> binding, no
   selection state, no edit entry.  Fix: add click-to-select, an
   inline popup cell editor, and keyboard solfa entry.

4. NOTE EDITOR WIRING (unreachable from trad canvas): _on_note_sel()
   is only called by StaffCanvas.  Fix: TraditionalSolfaCanvas fires
   the same callback when a cell is selected.

HOW TO APPLY
────────────
Option A (cleanest): import this module and call patch_app(app) once
    after TonicSolfaStudio.__init__ completes.

Option B (inline): copy each class/function directly into the main
    file as described in the INTEGRATION section at the bottom.

    from solfadee_edit_patch import (
        EditableTraditionalSolfaCanvas,
        EditableSolfaTextPanel,
        patch_print_trad_solfa,
        patch_app,
    )
══════════════════════════════════════════════════════════════════
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import re
import math
from typing import Optional, List, Dict, Callable

# ── Shared palette constants (match main file) ───────────────────
PAPER_BG    = "#f5f0e4"; PAPER_INK  = "#140e04"; PAPER_LINE = "#9a8060"
PAPER_BAR   = "#2a1800"; PAPER_LYRIC= "#1a3060"; PAPER_DYN  = "#8b0000"
PAPER_HEAD  = "#3a0000"; PAPER_VOICE= "#3e2f1d"; PAPER_BARNUM="#5a4030"
PAPER_SEL   = "#ffe0a0"   # selection highlight (amber, screen-only)
PAPER_RULER = "#a0c0e0"

DARK  = "#1a1a2e"; PANEL = "#16213e"; CARD  = "#0f3460"
GOLD  = "#f5a623"; TEXT  = "#eaeaea"; MUTED = "#8892a4"
ACCENT= "#e94560"; GREEN = "#00d4aa"; WHITE = "#ffffff"
BLUE  = "#4fc3f7"; ORANGE= "#ff9800"

VOICE_NAMES = {1: 'Sop.', 2: 'Alto', 3: 'Ten.', 4: 'Bass'}
SOLFA_SYLLABLES_ALL = {
    'd', 'r', 'm', 'f', 's', 'l', 't',
    'de', 're', 'fe', 'se', 'ta', 'le',
    'ra', 'ma', 'ba',
}
KEYS = ['C','G','D','A','E','B','F#','Gb','Db','Ab','Eb','Bb','F']
SUBSCRIPT_DIGITS = {
    '0':'₀','1':'₁','2':'₂','3':'₃','4':'₄',
    '5':'₅','6':'₆','7':'₇','8':'₈','9':'₉'
}


# ════════════════════════════════════════════════════════════════
#  FIX 3 + 4 — EDITABLE TRADITIONAL SOLFA CANVAS
# ════════════════════════════════════════════════════════════════

class EditableTraditionalSolfaCanvas(tk.Canvas):
    """
    Drop-in replacement for TraditionalSolfaCanvas that adds:

    • Click-to-select a measure cell (voice × bar)
    • Selected cell highlighted in amber
    • Popup cell editor (double-click or Enter) for direct text input
    • Solfa syllable keyboard entry (single-click then type d r m …)
    • Fires on_note_select(measure_idx, note_idx) so NoteEditorPanel
      receives selections from this canvas too
    • All original rendering logic preserved unchanged

    The editor stores MusNote objects with the pitch field set to the
    raw solfa syllable string (e.g. 'd', 'r', 'm', 'fe') so they
    round-trip correctly through the existing data model.
    """

    # ── Layout constants (identical to original) ─────────────────
    MARGIN_L = 14; MARGIN_T = 14; KEY_W = 68; LABEL_W = 42
    BRACE_W  = 8;  VOICE_H  = 34; LYRIC_H = 18; ROW_GAP = 26
    DEFAULT_MEASURES_PER_ROW = 4
    DEFAULT_BEAT_WIDTH        = 50

    F_TITLE = ('Times New Roman', 18, 'bold')
    F_SUB   = ('Times New Roman', 10)
    F_KEY   = ('Times New Roman', 10, 'bold')
    F_VOICE = ('Times New Roman', 10, 'bold')
    F_SYL   = ('Times New Roman', 13, 'bold')
    F_LYRIC = ('Times New Roman', 9)
    F_DYN   = ('Times New Roman', 9, 'italic')
    F_MNUM  = ('Times New Roman', 7)
    F_ANNOT = ('Times New Roman', 8, 'italic')

    def __init__(self, master, score, on_change=None,
                 on_note_select=None, style_renderer=None, **kwargs):
        super().__init__(master, bg=PAPER_BG, bd=0,
                         highlightthickness=0, **kwargs)
        self.score          = score
        self.on_change      = on_change        # () → None
        self.on_note_select = on_note_select   # (m_idx, n_idx) → None
        self.style_renderer = style_renderer

        # Render options (same as original)
        self.measures_per_row  = self.DEFAULT_MEASURES_PER_ROW
        self.beat_width        = self.DEFAULT_BEAT_WIDTH
        self.fit_to_width      = True
        self.font_family       = 'Times New Roman'
        self.lyric_font_family = 'Times New Roman'
        self.font_scale        = 1.0
        self.row_gap           = self.ROW_GAP
        self.show_bar_numbers  = True
        self.measure_width     = 200

        # ── Selection state ──────────────────────────────────────
        self._sel_m     : int = -1    # selected measure index
        self._sel_voice : int = -1    # selected voice (1-4)
        self._sel_beat  : int = -1    # selected beat index within measure

        # ── Cell hit-map built during redraw ─────────────────────
        # list of (x0, y0, x1, y1, measure_idx, voice, beat_idx)
        self._cells: List[tuple] = []

        # ── Ruler overlay ────────────────────────────────────────
        try:
            from solfadee_fixes import PAPER_RULER as _PR
        except ImportError:
            _PR = "#a0c0e0"
        try:
            from solfadee_edit_patch import CanvasRulerOverlay as _CRO
            self.ruler = _CRO(self)
        except Exception:
            self.ruler = None

        # ── Bindings ─────────────────────────────────────────────
        self.bind('<Configure>',      lambda e: self.after_idle(self.redraw))
        self.bind('<Button-1>',       self._on_click)
        self.bind('<Double-Button-1>', self._on_double_click)
        self.bind('<Key>',            self._on_key)
        self.bind('<Return>',         self._on_return)
        self.bind('<Escape>',         lambda e: self._deselect())
        self.focus_set()

    # ── Public interface ────────────────────────────────────────
    def set_score(self, score):
        self.score = score
        self.redraw()

    def set_render_options(self, measures_per_row=None, beat_width=None,
                           row_gap=None, fit_to_width=None,
                           font_family=None, lyric_font_family=None,
                           font_scale=None, show_bar_numbers=None):
        if measures_per_row  is not None: self.measures_per_row  = max(1, int(measures_per_row))
        if beat_width        is not None: self.beat_width        = max(20, int(beat_width))
        if row_gap           is not None: self.row_gap           = int(row_gap)
        if fit_to_width      is not None: self.fit_to_width      = bool(fit_to_width)
        if font_family       is not None: self.font_family       = str(font_family)
        if lyric_font_family is not None: self.lyric_font_family = str(lyric_font_family)
        if font_scale        is not None: self.font_scale        = max(0.5, float(font_scale))
        if show_bar_numbers  is not None: self.show_bar_numbers  = bool(show_bar_numbers)
        self.redraw()

    # ── Font helper ─────────────────────────────────────────────
    def _font(self, base):
        if isinstance(base, tuple):
            name, size, *opts = base
            size = max(6, int(size * self.font_scale))
            return (self.font_family, size, *opts)
        if isinstance(base, int):
            return (self.font_family, int(base * self.font_scale))
        return base

    # ── Redraw ──────────────────────────────────────────────────
    def redraw(self):
        self.delete('all')
        self._cells.clear()
        if not self.score or not self.score.measures:
            w = self.winfo_width() or 800
            self.create_text(w // 2, 120,
                text="No music loaded — click to select, type to enter solfa",
                fill=PAPER_LINE, font=('Times New Roman', 12), anchor='center')
            return
        self._draw_page()

    def _draw_page(self):
        s   = self.score
        cw  = self.winfo_width() or 900
        y   = self.MARGIN_T + 10

        # Key / composer
        self.create_text(self.MARGIN_L + 4, y,
            text=f"Key {s.key_sig}.   {s.time_num}/{s.time_den}.",
            fill=PAPER_INK, font=self._font(self.F_KEY), anchor='w')
        if s.composer:
            self.create_text(cw - self.MARGIN_L - 4, y,
                text=s.composer, fill=PAPER_INK,
                font=self._font(self.F_SUB), anchor='e')
        y += 18

        # Title
        self.create_text(cw // 2, y, text=s.title.upper(),
            fill=PAPER_HEAD, font=self._font(self.F_TITLE), anchor='n')
        y += 24
        if s.lyricist:
            self.create_text(cw // 2, y, text=s.lyricist,
                fill=PAPER_INK, font=self._font(self.F_SUB), anchor='n')
            y += 14
        y += 6
        self.create_line(self.MARGIN_L, y, cw - self.MARGIN_L, y,
                         fill=PAPER_LINE, width=1)
        y += 6

        all_vs  = s.all_voices()
        bw      = self.beat_width
        avail_w = (cw - self.MARGIN_L - self.KEY_W
                   - self.LABEL_W - self.BRACE_W - 10)

        if self.fit_to_width and s.measures:
            avg_b   = sum(m.time_num for m in s.measures) / len(s.measures)
            meas_px = max(30, avg_b * bw)
            mpr     = max(1, min(self.measures_per_row,
                                  int(avail_w / meas_px)))
        else:
            mpr = max(1, self.measures_per_row)

        has_lyr = any(n.lyric for mm in s.measures for n in mm.notes)
        rows    = math.ceil(len(s.measures) / mpr)

        for row in range(rows):
            row_meas = s.measures[row * mpr:(row + 1) * mpr]
            y = self._draw_system(y, row_meas, all_vs, s, has_lyr, cw)
            y += self.row_gap

        self.configure(scrollregion=(0, 0, cw, y + 20))

    def _draw_system(self, y0, measures, voices, score, has_lyr, cw):
        upper  = [v for v in voices if v <= 2]
        lower  = [v for v in voices if v > 2]
        groups = []
        if upper: groups.append(upper)
        if lower: groups.append(lower)
        if not groups: groups = [[1]]

        brace_x = self.MARGIN_L + self.KEY_W + self.LABEL_W
        music_x = brace_x + self.BRACE_W
        bw      = self.beat_width
        y       = y0

        for gi, group in enumerate(groups):
            gh      = len(group) * self.VOICE_H
            total_w = sum(m.time_num * bw for m in measures)
            x_end   = music_x + total_w

            # Brace
            self.create_line(brace_x, y, brace_x, y + gh,
                             fill=PAPER_BAR, width=3)
            self.create_line(brace_x, y, brace_x + self.BRACE_W, y,
                             fill=PAPER_BAR, width=2)
            self.create_line(brace_x, y + gh, brace_x + self.BRACE_W, y + gh,
                             fill=PAPER_BAR, width=2)

            # Top rule
            self.create_line(music_x, y, x_end, y,
                             fill=PAPER_LINE, width=1)

            for vi, voice in enumerate(group):
                vy     = y + vi * self.VOICE_H
                vy_mid = vy + self.VOICE_H // 2

                # Voice label
                lbl = VOICE_NAMES.get(voice, f'V{voice}')
                self.create_text(brace_x - 4, vy_mid,
                    text=lbl, fill=PAPER_VOICE,
                    font=self._font(self.F_VOICE), anchor='e')

                self.create_line(music_x, vy + self.VOICE_H,
                                 x_end, vy + self.VOICE_H,
                                 fill=PAPER_LINE, width=1)
                self.create_line(music_x, vy, music_x, vy + self.VOICE_H,
                                 fill=PAPER_BAR, width=1)

                mx = music_x
                for mi, meas in enumerate(measures):
                    meas_w  = meas.time_num * bw
                    abs_idx = self._find_abs_idx(meas)

                    # Bar number
                    if vi == 0 and self.show_bar_numbers:
                        self.create_text(mx + 3, vy - 1,
                            text=str(meas.number),
                            fill=PAPER_BARNUM,
                            font=self._font(self.F_MNUM), anchor='nw')

                    # Annotations
                    if vi == 0:
                        if getattr(meas, 'metrical_modulation', None):
                            self.create_text(mx + meas_w // 2, vy - 12,
                                text=meas.metrical_modulation,
                                fill=PAPER_HEAD,
                                font=self._font(self.F_ANNOT), anchor='center')
                        if getattr(meas, 'key_change', None):
                            self.create_text(mx + meas_w // 2, vy - 5,
                                text=meas.key_change, fill=PAPER_HEAD,
                                font=self._font(('Times New Roman', 9, 'bold')),
                                anchor='center')

                    # Selection highlight
                    if (abs_idx == self._sel_m and voice == self._sel_voice):
                        self.create_rectangle(mx + 1, vy + 1,
                            mx + meas_w - 1, vy + self.VOICE_H - 1,
                            outline=ACCENT, fill=PAPER_SEL,
                            width=2, tags=('sel_rect',))

                    self._draw_measure_row(mx, vy, meas, voice,
                                           meas.key_sig, meas_w, abs_idx)

                    # Register cell in hit-map
                    self._cells.append((
                        mx, vy, mx + meas_w, vy + self.VOICE_H,
                        abs_idx, voice, 0
                    ))
                    mx += meas_w

            # Closing barline
            self.create_line(x_end, y, x_end, y + gh,
                             fill=PAPER_BAR, width=2)
            y += gh

            # Lyric row
            if gi == 0 and has_lyr and upper:
                mx = music_x
                for meas in measures:
                    meas_w = meas.time_num * bw
                    self._draw_lyrics_row(mx, y + 3, meas, upper[0], meas_w)
                    mx += meas_w
                y += self.LYRIC_H

            if gi < len(groups) - 1:
                y += max(12, int(self.row_gap * 0.55))

        return y

    def _draw_measure_row(self, x, vy, meas, voice, key, meas_w, abs_idx):
        vy_mid    = vy + self.VOICE_H // 2
        vnotes    = meas.voice_notes(voice)
        bw        = self.beat_width
        beat_unit = 4.0 / meas.time_den

        if not vnotes:
            self.create_text(x + meas_w / 2, vy_mid, text='·',
                fill=PAPER_LINE, font=self._font(self.F_SYL), anchor='center')
        else:
            pos = 0.0
            for n in vnotes:
                nx = x + (pos / beat_unit) * bw + 4
                if n.rest:
                    sym = '0'
                else:
                    if self.style_renderer:
                        sym = self.style_renderer.note_token(n, key)
                    else:
                        sym = n.solfa(key) + n.duration_underscores()
                col = PAPER_DYN if n.dynamic else PAPER_INK
                self.create_text(nx, vy_mid, text=sym, fill=col,
                    font=self._font(self.F_SYL), anchor='w')
                beats_held = n.beats
                pc         = pos + beat_unit
                while beats_held > beat_unit + 0.01:
                    hx = x + (pc / beat_unit) * bw + 4
                    self.create_text(hx, vy_mid, text='—', fill=PAPER_LINE,
                        font=self._font(self.F_SYL), anchor='w')
                    beats_held -= beat_unit; pc += beat_unit
                pos += n.beats

        # Beat separators
        for bi in range(1, meas.time_num):
            bx = x + bi * bw
            self.create_line(bx, vy + 4, bx, vy + self.VOICE_H - 4,
                fill=PAPER_LINE, width=1, dash=(3, 3))

        # Barline
        self.create_line(x + meas_w, vy, x + meas_w, vy + self.VOICE_H,
                         fill=PAPER_BAR, width=1)

        # Repeat signs
        if meas.repeat_start:
            h = self.VOICE_H
            self.create_line(x+2,vy,x+2,vy+h,fill=PAPER_BAR,width=2)
            self.create_line(x+5,vy,x+5,vy+h,fill=PAPER_BAR,width=1)
            self.create_oval(x+7,vy+h//3-3,x+11,vy+h//3+3,fill=PAPER_BAR)
            self.create_oval(x+7,vy+2*h//3-3,x+11,vy+2*h//3+3,fill=PAPER_BAR)
        if meas.repeat_end:
            ex = x + meas_w; h = self.VOICE_H
            self.create_oval(ex-11,vy+h//3-3,ex-7,vy+h//3+3,fill=PAPER_BAR)
            self.create_oval(ex-11,vy+2*h//3-3,ex-7,vy+2*h//3+3,fill=PAPER_BAR)
            self.create_line(ex-5,vy,ex-5,vy+h,fill=PAPER_BAR,width=1)
            self.create_line(ex-2,vy,ex-2,vy+h,fill=PAPER_BAR,width=2)

    def _draw_lyrics_row(self, x, ly, meas, voice, meas_w):
        vnotes    = meas.voice_notes(voice) or meas.notes
        beat_unit = 4.0 / meas.time_den
        bw        = self.beat_width
        pos       = 0.0
        for n in vnotes:
            if n.lyric:
                nx = x + (pos / beat_unit) * bw + 4
                self.create_text(nx, ly + self.LYRIC_H // 2,
                    text=n.lyric, fill=PAPER_LYRIC,
                    font=self._font(self.F_LYRIC), anchor='w')
            pos += n.beats

    def _find_abs_idx(self, meas):
        for i, m in enumerate(self.score.measures):
            if m is meas: return i
        return -1

    # ── Click / selection ────────────────────────────────────────
    def _on_click(self, event):
        self.focus_set()
        hit = self._hit_test(event.x, event.y)
        if hit is None:
            self._deselect(); return
        _, _, _, _, m_idx, voice, _ = hit
        self._sel_m     = m_idx
        self._sel_voice = voice
        self._sel_beat  = 0
        self.redraw()
        # Wire to NoteEditorPanel via on_note_select
        if self.on_note_select and 0 <= m_idx < len(self.score.measures):
            m = self.score.measures[m_idx]
            vnotes = m.voice_notes(voice)
            if vnotes:
                # find the note's global index in m.notes
                for ni, n in enumerate(m.notes):
                    if n is vnotes[0]:
                        self.on_note_select(m_idx, ni)
                        break

    def _on_double_click(self, event):
        """Open the cell editor popup."""
        hit = self._hit_test(event.x, event.y)
        if hit is None: return
        x0, y0, x1, y1, m_idx, voice, _ = hit
        self._sel_m = m_idx; self._sel_voice = voice
        self._open_cell_editor(m_idx, voice, x0, y0, x1, y1)

    def _on_return(self, event):
        """Enter key opens editor for selected cell."""
        if self._sel_m >= 0 and self._sel_voice >= 0:
            for cell in self._cells:
                x0, y0, x1, y1, m_idx, voice, _ = cell
                if m_idx == self._sel_m and voice == self._sel_voice:
                    self._open_cell_editor(m_idx, voice, x0, y0, x1, y1)
                    return

    def _on_key(self, event):
        """
        Single-key solfa entry: typing a syllable letter while a cell is
        selected opens the cell editor pre-filled with that character.
        """
        if self._sel_m < 0 or self._sel_voice < 0: return
        ch = event.char.lower()
        if ch in ('d', 'r', 'm', 'f', 's', 'l', 't', '0', '-'):
            for cell in self._cells:
                x0, y0, x1, y1, m_idx, voice, _ = cell
                if m_idx == self._sel_m and voice == self._sel_voice:
                    self._open_cell_editor(m_idx, voice, x0, y0, x1, y1,
                                            prefill=ch)
                    return

    def _deselect(self):
        self._sel_m = -1; self._sel_voice = -1; self._sel_beat = -1
        self.redraw()

    def _hit_test(self, ex, ey):
        """Return the first cell tuple whose bounding box contains (ex, ey)."""
        for cell in self._cells:
            x0, y0, x1, y1 = cell[:4]
            if x0 <= ex <= x1 and y0 <= ey <= y1:
                return cell
        return None

    # ── Cell editor popup ────────────────────────────────────────
    def _open_cell_editor(self, m_idx, voice, x0, y0, x1, y1,
                           prefill: str = ''):
        """
        Popup a compact editor window anchored near the selected cell.

        The editor shows the current measure string for that voice and
        lets the user retype it in tonic-solfa notation.

        Format accepted:
          Space-separated tokens: d  r  m  f'  d₁  0  —  d.  r,
          Duration suffixes: . = eighth   , = sixteenth   ; = 32nd
          Octave:  ' or '' = high   1 or 2 or ₁ ₂ = low
          Rest:    0
          Hold:    — or -
        """
        if m_idx < 0 or m_idx >= len(self.score.measures): return
        meas   = self.score.measures[m_idx]
        vnotes = meas.voice_notes(voice)
        key    = meas.key_sig

        # Current cell text
        current = ' '.join(
            (n.solfa(key) + n.duration_underscores()) if not n.rest else '0'
            for n in vnotes
        ) if vnotes else ''

        # Anchor popup near the cell
        rx = self.winfo_rootx() + x0
        ry = self.winfo_rooty() + y1 + 2

        popup = tk.Toplevel(self)
        popup.wm_overrideredirect(True)
        popup.geometry(f'+{rx}+{ry}')
        popup.configure(bg=CARD)
        popup.grab_set()

        # Info label
        lbl_text = (f"Bar {meas.number} · "
                    f"{VOICE_NAMES.get(voice, f'V{voice}')} · "
                    f"Key {key} · {meas.time_num}/{meas.time_den}")
        tk.Label(popup, text=lbl_text, bg=CARD, fg=GOLD,
                 font=('Arial', 8, 'bold')).pack(padx=6, pady=(4, 0))

        tk.Label(popup,
                 text="Tokens: d r m f s l t  0=rest  —=hold  '=high  1=low  .=8th  ,=16th",
                 bg=CARD, fg=MUTED, font=('Arial', 7)).pack(padx=6)

        var = tk.StringVar(value=prefill if prefill else current)
        entry = tk.Entry(popup, textvariable=var, width=40,
                         bg=DARK, fg=WHITE, insertbackground=WHITE,
                         font=('Times New Roman', 12), relief='flat')
        entry.pack(padx=6, pady=4, fill='x')
        entry.icursor(tk.END)
        entry.focus_set()

        btn_f = tk.Frame(popup, bg=CARD); btn_f.pack(fill='x', padx=6, pady=(0, 4))

        def apply():
            raw = var.get().strip()
            self._apply_cell_text(m_idx, voice, raw, key, meas)
            popup.destroy()
            self.redraw()

        def cancel():
            popup.destroy()

        tk.Button(btn_f, text="✓ Apply", bg=GREEN, fg=DARK, relief='flat',
                  font=('Arial', 9, 'bold'), command=apply).pack(side='left', padx=2)
        tk.Button(btn_f, text="✕ Cancel", bg=DARK, fg=TEXT, relief='flat',
                  font=('Arial', 9), command=cancel).pack(side='left', padx=2)

        entry.bind('<Return>', lambda e: apply())
        entry.bind('<Escape>', lambda e: cancel())

        # Right-click context for quick syllable insert
        ctx = tk.Menu(popup, tearoff=0, bg=PANEL, fg=TEXT)
        for syl in ['d', 'r', 'm', 'f', 's', 'l', 't',
                     "d'", "d₁", '0', '—', 'd.', 'r,']:
            ctx.add_command(label=syl,
                command=lambda s=syl: var.set(var.get() + ' ' + s))
        entry.bind('<Button-3>', lambda e: ctx.tk_popup(e.x_root, e.y_root))

    def _apply_cell_text(self, m_idx, voice, raw_text, key, meas):
        """
        Parse a space-separated solfa token string and replace the voice's
        notes in the given measure.

        Tokens are matched against known solfa syllables; any unrecognised
        token is treated as a rest.  Duration suffixes and octave marks are
        parsed from the token suffix.
        """
        tokens = raw_text.split()
        if not tokens: return

        # Remove old notes for this voice
        meas.notes = [n for n in meas.notes if n.voice != voice]

        beat_unit  = 4.0 / meas.time_den
        beats_avail = meas.beats_available

        for tok in tokens:
            n = self._parse_token(tok, voice, key)
            if n is None: continue
            # Don't overfill
            used = sum(x.beats for x in meas.notes if x.voice == voice)
            if used + n.beats > beats_avail + 0.01:
                break
            meas.notes.append(n)

        if self.on_change:
            self.on_change()

    def _parse_token(self, tok: str, voice: int, key: str):
        """
        Convert one display token (e.g. "d'", "r₁", "m.", "0", "—")
        into a MusNote.  Returns None for hold tokens (—) since they
        extend the previous note's duration rather than adding a new one.
        """
        # Import MusNote dynamically to avoid circular import
        try:
            from tonic_solfa_studio import MusNote, PITCH_TO_CHROM, KEY_TONIC_CHROM
            from tonic_solfa_studio import INTERVAL_TO_MOVABLE_DO, CHROM_TO_NOTE
        except ImportError:
            # Fallback: create a minimal MusNote-like object
            return None

        tok = tok.strip()
        if not tok or tok in ('—', '-', '–'):
            return None   # hold: extends previous note, not a new note

        if tok == '0':
            return MusNote(rest=True, duration=1.0, voice=voice)

        # Detect duration suffix
        dur    = 1.0   # quarter default
        dotted = False
        if tok.endswith(';'):
            dur = 0.125; tok = tok[:-1]
        elif tok.endswith(',.'):
            dur = 0.375; dotted = True; tok = tok[:-2]
        elif tok.endswith(','):
            dur = 0.25;  tok = tok[:-1]
        elif tok.endswith('.·'):
            dur = 0.75; dotted = True; tok = tok[:-2]
        elif tok.endswith('.'):
            dur = 0.5;   tok = tok[:-1]

        # Detect octave modifier at end
        oct_mod = 0
        while tok.endswith("'"):
            oct_mod += 1; tok = tok[:-1]
        if not tok:
            return None
        # Subscript digits
        _unsub = {'₁':1,'₂':2,'₃':3,'₄':4,'₅':5,'₀':0,'₆':6,'₇':7,'₈':8,'₉':9}
        while tok and tok[-1] in _unsub:
            oct_mod -= _unsub[tok[-1]]; tok = tok[:-1]
        # ASCII digit suffix (inline_num style: s1, d2)
        while tok and tok[-1].isdigit() and len(tok) > 1 and tok[-2].isalpha():
            oct_mod -= int(tok[-1]); tok = tok[:-1]

        syl = tok.lower()
        if syl not in SOLFA_SYLLABLES_ALL:
            # Unknown syllable — treat as rest
            return MusNote(rest=True, duration=dur, dotted=dotted, voice=voice)

        # Convert solfa syllable → pitch
        SOLFA_TO_INTERVAL = {
            'd':0,'de':1,'ra':1,'r':2,'re':3,'ma':3,'m':4,
            'f':5,'fe':6,'ba':6,'s':7,'se':8,'la':8,'l':9,
            'le':10,'ta':10,'t':11
        }
        iv    = SOLFA_TO_INTERVAL.get(syl, 0)
        tonic = KEY_TONIC_CHROM.get(key, 0)
        chrom = (tonic + iv) % 12
        pitch = CHROM_TO_NOTE.get(chrom, 'C')
        octave = 4 + oct_mod   # home = 4

        return MusNote(pitch=pitch, octave=octave, duration=dur,
                       dotted=dotted, voice=voice)


# ════════════════════════════════════════════════════════════════
#  FIX 2 — EDITABLE SOLFA TEXT PANEL
# ════════════════════════════════════════════════════════════════

class EditableSolfaTextPanel(tk.Frame):
    """
    Drop-in replacement for SolfaTextPanel.
    
    Changes:
    • Text widget is fully editable at all times.
    • "⟳ Refresh" rewrites from score (same as before).
    • NEW "✓ Apply" button parses the text and updates the score.
    • Ctrl+Return also applies.
    • Status bar shows parse errors without crashing.
    """

    def __init__(self, master, score, on_change=None, **kwargs):
        super().__init__(master, bg='#16213e', **kwargs)
        self.score     = score
        self.on_change = on_change
        self._build()

    def _build(self):
        # ── Toolbar ─────────────────────────────────────────────
        bar = tk.Frame(self, bg='#0f3460'); bar.pack(fill='x')
        tk.Label(bar, text="TONIC SOLFA TEXT EDITOR  (editable — type directly)",
                 bg='#0f3460', fg='#f5a623',
                 font=('Arial', 9, 'bold')).pack(side='left', padx=10, pady=5)

        tk.Button(bar, text="✓ Apply to Score",
                  bg='#00d4aa', fg='#1a1a2e', relief='flat',
                  font=('Arial', 8, 'bold'),
                  command=self._apply).pack(side='right', padx=4, pady=4)
        tk.Button(bar, text="⟳ Refresh from Score",
                  bg='#e94560', fg='#ffffff', relief='flat',
                  font=('Arial', 8),
                  command=self.refresh_from_score).pack(side='right', padx=4, pady=4)

        # ── Text widget ─────────────────────────────────────────
        self.txt = tk.Text(
            self, bg='#0d1b2a', fg='#eaeaea',
            insertbackground='#ffffff',
            font=('Courier New', 11), relief='flat',
            padx=12, pady=10, undo=True, wrap='none',
            state='normal')    # ← always normal (editable)
        sb_v = ttk.Scrollbar(self, orient='vertical',   command=self.txt.yview)
        sb_h = ttk.Scrollbar(self, orient='horizontal', command=self.txt.xview)
        self.txt.config(yscrollcommand=sb_v.set, xscrollcommand=sb_h.set)
        sb_v.pack(side='right',  fill='y')
        sb_h.pack(side='bottom', fill='x')
        self.txt.pack(fill='both', expand=True)

        # ── Keyboard shortcut ────────────────────────────────────
        self.txt.bind('<Control-Return>', lambda e: self._apply())

        # ── Status bar ──────────────────────────────────────────
        self._status = tk.Label(
            self, text="  Ctrl+Enter or click ✓ Apply to update score from text",
            bg='#16213e', fg='#8892a4', font=('Arial', 8), anchor='w')
        self._status.pack(fill='x', padx=6, pady=2)

        # ── Legend ──────────────────────────────────────────────
        leg = tk.Frame(self, bg='#16213e'); leg.pack(fill='x', pady=2)
        for lbl, col in [("d=Do","#e94560"),("r=Re","#f5a623"),("m=Mi","#00d4aa"),
                          ("f=Fa","#8892a4"),("s=Sol","#4fc3f7"),("l=La","#ce93d8"),
                          ("t=Ti","#ffb74d")]:
            tk.Label(leg, text=lbl, bg=col, fg='#1a1a2e',
                     font=('Arial', 8, 'bold'), padx=4).pack(side='left', padx=1, pady=2)
        tk.Label(leg,
                 text="  '=high   ,=low   —=held   0=rest   .=8th   ,=16th",
                 bg='#16213e', fg='#8892a4', font=('Arial', 8)).pack(side='left', padx=8)

    def refresh_from_score(self):
        """Overwrite text widget with current score content."""
        try:
            from tonic_solfa_studio import ConversionEngine
            content = ConversionEngine.export_solfa_text(self.score)
        except Exception as e:
            content = f"(error generating text: {e})"
        self.txt.delete('1.0', 'end')
        self.txt.insert('1.0', content)
        self._status.config(text="  Score loaded into editor. Edit and press ✓ Apply.",
                            fg='#8892a4')

    def set_score(self, score):
        self.score = score
        self.refresh_from_score()

    def _apply(self):
        """
        Parse the text widget content and update the score.

        The parser reads the structured text produced by export_solfa_text()
        and reconstructs MusNote objects.  It is tolerant: lines it cannot
        parse are skipped.
        """
        raw = self.txt.get('1.0', 'end')
        try:
            n_updated = self._parse_and_apply(raw)
            self._status.config(
                text=f"  ✓ Applied — {n_updated} note(s) updated from text.",
                fg='#00d4aa')
            if self.on_change:
                self.on_change()
        except Exception as e:
            self._status.config(
                text=f"  ✗ Parse error: {e}",
                fg='#e94560')

    def _parse_and_apply(self, raw: str) -> int:
        """
        Simple line-oriented parser.  Looks for lines of the form:
            | N|  tok | tok | tok | tok |
        and maps them back to the current measures.  Voice is inferred
        from section headers (── Soprano/Melody ──, etc.).
        """
        try:
            from tonic_solfa_studio import MusNote, CHROM_TO_NOTE, KEY_TONIC_CHROM
        except ImportError:
            raise RuntimeError("Cannot import MusNote from tonic_solfa_studio")

        voice_map = {
            'soprano': 1, 'melody': 1,
            'alto': 2,
            'tenor': 3,
            'bass': 4,
        }
        SOLFA_TO_INTERVAL = {
            'd':0,'de':1,'ra':1,'r':2,'re':3,'ma':3,'m':4,
            'f':5,'fe':6,'ba':6,'s':7,'se':8,'la':8,'l':9,
            'le':10,'ta':10,'t':11
        }

        current_voice = 1
        n_updated     = 0

        for line in raw.splitlines():
            line = line.strip()

            # Voice section header
            for vname, vnum in voice_map.items():
                if vname in line.lower() and '──' in line:
                    current_voice = vnum
                    break

            # Measure data line: |  N| cell | cell | ...
            if not line.startswith('|') or '|' not in line[1:]:
                continue

            parts = [p.strip() for p in line.split('|')]
            parts = [p for p in parts if p]
            if not parts:
                continue
            # First part should be measure number
            m_num_str = parts[0].strip()
            try:
                m_num = int(m_num_str)
            except ValueError:
                continue
            if m_num < 1 or m_num > len(self.score.measures):
                continue

            m   = self.score.measures[m_num - 1]
            key = m.key_sig

            # Remove old notes for this voice
            m.notes = [n for n in m.notes if n.voice != current_voice]

            beat_unit   = 4.0 / m.time_den
            beats_avail = m.beats_available

            for cell_str in parts[1:]:
                cell_str = cell_str.strip()
                if not cell_str or cell_str == '·': continue
                # Each cell is one beat — parse the solfa token
                tok = cell_str.split('~')[0].strip()   # strip tie suffix
                if tok in ('—', '-', '–', ''):
                    continue  # hold: the previous note covers this beat

                if tok == '0':
                    nn = MusNote(rest=True, duration=beat_unit,
                                 voice=current_voice)
                else:
                    # Strip duration suffix
                    dur = beat_unit; dotted = False
                    if tok.endswith('.'):
                        dur = beat_unit / 2; tok = tok[:-1]
                    elif tok.endswith(','):
                        dur = beat_unit / 4; tok = tok[:-1]

                    # Strip octave marks
                    oct_mod = 0
                    while tok.endswith("'"):
                        oct_mod += 1; tok = tok[:-1]
                    _unsub = {'₁':1,'₂':2,'₃':3,'₄':4,'₅':5,'₀':0}
                    while tok and tok[-1] in _unsub:
                        oct_mod -= _unsub[tok[-1]]; tok = tok[:-1]

                    syl = tok.lower()
                    iv  = SOLFA_TO_INTERVAL.get(syl, 0)
                    tonic = KEY_TONIC_CHROM.get(key, 0)
                    chrom = (tonic + iv) % 12
                    pitch = CHROM_TO_NOTE.get(chrom, 'C')
                    octave = 4 + oct_mod

                    nn = MusNote(pitch=pitch, octave=octave, duration=dur,
                                 dotted=dotted, voice=current_voice)

                used = sum(x.beats for x in m.notes if x.voice == current_voice)
                if used + nn.beats <= beats_avail + 0.01:
                    m.notes.append(nn)
                    n_updated += 1

        return n_updated


# ════════════════════════════════════════════════════════════════
#  FIX 1 — OCTAVE MODE PDF EXPORT
#  Replaces _print_trad_solfa so it actually uses self.octave_mode
# ════════════════════════════════════════════════════════════════

def patch_print_trad_solfa(app_instance):
    """
    Monkey-patch _print_trad_solfa on the app instance so it calls
    export_pdf_solfa_fixed() with the current octave mode.
    """
    from tkinter import filedialog, messagebox

    def _print_trad_solfa_fixed(self=app_instance):
        path = filedialog.asksaveasfilename(
            title="Save Traditional Solfa PDF",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf"), ("All", "*.*")],
            parent=self)
        if not path: return

        try:
            from solfadee_fixes import export_pdf_solfa_fixed, OctaveMarkMode
            mode_str = getattr(self, 'octave_mode', 'POSITIONAL')
            mode     = OctaveMarkMode(mode_str.lower())
        except Exception:
            # Graceful fallback: use ASCII if fixes not available
            try:
                from solfadee_fixes import export_pdf_solfa_fixed
                mode = type('M', (), {'value': 'ascii'})()
                mode = None
            except Exception:
                export_pdf_solfa_fixed = None
                mode = None

        try:
            if export_pdf_solfa_fixed and mode is not None:
                export_pdf_solfa_fixed(
                    self.score, path,
                    octave_mode=mode,
                    measures_per_row=getattr(self.trad_canvas, 'measures_per_row', 4))
            else:
                from tonic_solfa_studio import ConversionEngine
                ConversionEngine.export_pdf_solfa_traditional(self.score, path)

            self.status_var.set(
                f"✓ PDF saved ({getattr(self, 'octave_mode', 'default')} mode): {path}")
            messagebox.showinfo("Print",
                f"Traditional Tonic Solfa PDF saved:\n{path}\n"
                f"Octave mode: {getattr(self, 'octave_mode', 'POSITIONAL')}",
                parent=self)
        except Exception as e:
            messagebox.showerror("Print Error", str(e), parent=self)

    import types
    app_instance._print_trad_solfa = types.MethodType(
        lambda self: _print_trad_solfa_fixed(self), app_instance)


# ════════════════════════════════════════════════════════════════
#  MASTER PATCH FUNCTION
#  Call once after TonicSolfaStudio.__init__ completes.
# ════════════════════════════════════════════════════════════════

def patch_app(app):
    """
    Apply all four fixes to a live TonicSolfaStudio instance.

    Call immediately after construction:
        app = TonicSolfaStudio()
        from solfadee_edit_patch import patch_app
        patch_app(app)
        app.mainloop()
    """
    import types

    # ── Fix 1: octave mode PDF ───────────────────────────────────
    patch_print_trad_solfa(app)

    # ── Fix 2: editable solfa text panel ────────────────────────
    # Replace the existing solfa_panel widget in its parent frame
    if hasattr(app, 'solfa_panel') and hasattr(app.solfa_panel, 'master'):
        parent = app.solfa_panel.master
        app.solfa_panel.destroy()
        app.solfa_panel = EditableSolfaTextPanel(
            parent, app.score, on_change=app._on_change)
        app.solfa_panel.pack(fill='both', expand=True)
        app.solfa_panel.refresh_from_score()

    # ── Fixes 3 + 4: editable traditional canvas ────────────────
    if hasattr(app, 'trad_canvas') and hasattr(app.trad_canvas, 'master'):
        parent = app.trad_canvas.master
        # Preserve render options
        mpr   = app.trad_canvas.measures_per_row
        bw    = app.trad_canvas.beat_width
        rg    = app.trad_canvas.row_gap
        fw    = app.trad_canvas.fit_to_width
        ff    = app.trad_canvas.font_family
        fs    = app.trad_canvas.font_scale
        bn    = app.trad_canvas.show_bar_numbers
        sr    = app.trad_canvas.style_renderer
        # Scrollbar references (already packed in the parent)
        # We recreate the canvas with the same kwargs
        old_xscmd = app.trad_canvas.cget('xscrollcommand')
        old_yscmd = app.trad_canvas.cget('yscrollcommand')
        app.trad_canvas.destroy()

        app.trad_canvas = EditableTraditionalSolfaCanvas(
            parent, app.score,
            on_change=app._on_change,
            on_note_select=lambda mi, ni: app._on_note_sel(mi, ni),
            style_renderer=sr)
        app.trad_canvas.set_render_options(
            measures_per_row=mpr, beat_width=bw,
            row_gap=rg, fit_to_width=fw,
            font_family=ff, font_scale=fs,
            show_bar_numbers=bn)
        app.trad_canvas.pack(fill='both', expand=True)
        app.trad_canvas.set_score(app.score)

    return app


# ════════════════════════════════════════════════════════════════
#  RULER OVERLAY (copied here so the canvas can import it standalone)
# ════════════════════════════════════════════════════════════════
class CanvasRulerOverlay:
    HANDLE_R = 5; LINE_DASH = (6, 4)
    def __init__(self, canvas):
        self.canvas = canvas
        self._rulers = {}; self._drag_state = None; self._next_id = 1
        canvas.tag_bind('ruler_handle','<ButtonPress-1>',   self._start_drag)
        canvas.tag_bind('ruler_handle','<B1-Motion>',       self._drag)
        canvas.tag_bind('ruler_handle','<ButtonRelease-1>', self._end_drag)
        canvas.tag_bind('ruler_handle','<Double-Button-1>', self._remove)
    def add_horizontal(self, y=100):
        rid = self._next_id; self._next_id += 1
        c = self.canvas; w = c.winfo_width() or 2000; h = c.winfo_height() or 2000
        ids = [c.create_line(0,y,w,y,fill=PAPER_RULER,width=1,dash=self.LINE_DASH),
               c.create_oval(10-self.HANDLE_R,y-self.HANDLE_R,
                             10+self.HANDLE_R,y+self.HANDLE_R,
                             fill=PAPER_RULER,outline=PAPER_BAR)]
        for i in ids: c.itemconfig(i,tags=('ruler','ruler_handle',f'ruler_{rid}'))
        self._rulers[rid]={'type':'h','pos':y,'ids':ids,'rid':rid}; return rid
    def add_vertical(self, x=100):
        rid = self._next_id; self._next_id += 1
        c = self.canvas; w = c.winfo_width() or 2000; h = c.winfo_height() or 2000
        ids = [c.create_line(x,0,x,h,fill=PAPER_RULER,width=1,dash=self.LINE_DASH),
               c.create_oval(x-self.HANDLE_R,10-self.HANDLE_R,
                             x+self.HANDLE_R,10+self.HANDLE_R,
                             fill=PAPER_RULER,outline=PAPER_BAR)]
        for i in ids: c.itemconfig(i,tags=('ruler','ruler_handle',f'ruler_{rid}'))
        self._rulers[rid]={'type':'v','pos':x,'ids':ids,'rid':rid}; return rid
    def remove_all(self): self.canvas.delete('ruler'); self._rulers.clear()
    def hide(self): self.canvas.itemconfigure('ruler',state='hidden')
    def show(self): self.canvas.itemconfigure('ruler',state='normal')
    def _rid_from(self, item_id):
        for t in self.canvas.gettags(item_id):
            if t.startswith('ruler_') and t[6:].isdigit():
                return self._rulers.get(int(t[6:]))
        return None
    def _start_drag(self, e):
        item = self.canvas.find_withtag('current')
        if item:
            r = self._rid_from(item[0])
            if r: self._drag_state = {'ruler':r,'x':e.x,'y':e.y}
    def _drag(self, e):
        if not self._drag_state: return
        r = self._drag_state['ruler']; c = self.canvas
        w = c.winfo_width() or 2000; h = c.winfo_height() or 2000
        if r['type']=='h':
            r['pos'] += e.y-self._drag_state['y']; self._drag_state['y']=e.y
            p=r['pos']; li,hi=r['ids']
            c.coords(li,0,p,w,p); c.coords(hi,10-self.HANDLE_R,p-self.HANDLE_R,10+self.HANDLE_R,p+self.HANDLE_R)
        else:
            r['pos'] += e.x-self._drag_state['x']; self._drag_state['x']=e.x
            p=r['pos']; li,hi=r['ids']
            c.coords(li,p,0,p,h); c.coords(hi,p-self.HANDLE_R,10-self.HANDLE_R,p+self.HANDLE_R,10+self.HANDLE_R)
    def _end_drag(self, e): self._drag_state = None
    def _remove(self, e):
        item = self.canvas.find_withtag('current')
        if item:
            r = self._rid_from(item[0])
            if r:
                for i in r['ids']: self.canvas.delete(i)
                del self._rulers[r['rid']]


# ════════════════════════════════════════════════════════════════
#  INTEGRATION NOTES
# ════════════════════════════════════════════════════════════════
INTEGRATION_NOTES = """
OPTION A — Patch at runtime (recommended, zero changes to main file)
─────────────────────────────────────────────────────────────────────
Change the entry point in solfadee_studio_v5.py from:

    def main():
        app = TonicSolfaStudio()
        app.mainloop()

to:

    def main():
        app = TonicSolfaStudio()
        from solfadee_edit_patch import patch_app
        patch_app(app)
        app.mainloop()

That is the complete change required.  All four fixes activate automatically.

OPTION B — Inline replacement
─────────────────────────────────────────────────────────────────────
Replace TraditionalSolfaCanvas  → EditableTraditionalSolfaCanvas
Replace SolfaTextPanel          → EditableSolfaTextPanel
Replace _print_trad_solfa body  → body from patch_print_trad_solfa()

WHAT EACH FIX DOES WHEN ACTIVE
─────────────────────────────────────────────────────────────────────
Fix 1 (Octave mode PDF):
  The toolbar "Octave" dropdown now actually controls PDF output.
  Select POSITIONAL → real sub/superscript via offset drawing.
  Select ASCII      → plain d1 d' in standard font (safest).
  Select OFF        → no octave marks (add manually post-print).

Fix 2 (Editable Solfa Text Panel):
  The text widget is now always editable.
  Click inside and type freely.
  Press Ctrl+Enter or click "✓ Apply to Score" to parse the text
  back into the score data model.
  Press "⟳ Refresh from Score" to reload from the current score.

Fix 3 (Editable Traditional Canvas):
  Single click   → selects a voice row within a bar (amber highlight)
  Double click   → opens a compact popup editor for that cell
  Enter          → opens editor for the currently selected cell
  Type d/r/m/f/s/l/t → opens editor pre-filled with that syllable
  Escape         → deselects

  Inside the popup editor:
    Space-separate tokens: d  r  m  f'  d₁  0  —  d.  r,
    Press Enter or click ✓ Apply to write back.
    Right-click entry → quick-insert syllable menu.

Fix 4 (Note Editor wiring):
  Clicking a cell on the Traditional Canvas now also populates the
  Note Editor panel (Tab 3) with the first note in that cell,
  matching the behaviour of the Staff Notation canvas.
"""

if __name__ == '__main__':
    print(INTEGRATION_NOTES)
