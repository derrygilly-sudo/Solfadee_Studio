"""
=============================================================================
  TONIC SOLFA NOTATION CANVAS  –  Professional Edition
=============================================================================
  Architecture   : Four-agent design (Architecture, Engineer, Reviewer, Optimizer)
  Font           : Times New Roman throughout (PDF + Canvas)
  Features       : MusicXML import · Editable canvas · PDF export (hymn-book quality)
                   Resize toolbar · Auto/manual note fitting · Font size buttons
                   Curly-brace systems · Italic blue lyrics · Grey measure numbers
                   Double barline at row-end/final · Part initials flush-left
                   Multiple solfa style modes · Legend footer · Page numbering
=============================================================================
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import xml.etree.ElementTree as ET
import json
import re
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
import copy
import os

# ── PDF export ────────────────────────────────────────────────────────────────
try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4, LETTER
    from reportlab.lib.units import mm, pt
    from reportlab.lib import colors as rl_colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


# ═══════════════════════════════════════════════════════════════════════════════
#  SOLFA STYLE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

SOLFA_STYLES = {
    "Standard"    : {"upper": "'", "lower": ",", "rest": "-", "bar": "|", "tie": ":"},
    "Classic"     : {"upper": "'", "lower": ",", "rest": "-", "bar": "|", "tie": ";"},
    "Curwen"      : {"upper": "'", "lower": ",", "rest": "0", "bar": "|", "tie": "-"},
    "Methodist"   : {"upper": "'", "lower": ",", "rest": "-", "bar": "|", "tie": "="},
    "Continental" : {"upper": "'", "lower": ",", "rest": "r", "bar": "|", "tie": "·"},
}

STYLE_VISUALS: Dict[str, Dict[str, object]] = {
    "Standard": {
        "bg": "#FFFDF5", "ink": "#110900", "sel": "#1a4da8", "grid": "#d4c8b0",
        "lyric": "#1a3a7a", "mnum": "#888888", "brace": "#333333",
        "font": "Times New Roman", "pdf_font": "Times", "row_scale": 1.00, "gap_scale": 1.00,
    },
    "Classic": {
        "bg": "#fbf6ea", "ink": "#4a2415", "sel": "#944b2d", "grid": "#d9c5a5",
        "lyric": "#7a4aa0", "mnum": "#9a7452", "brace": "#6b4423",
        "font": "Georgia", "pdf_font": "Times", "row_scale": 1.10, "gap_scale": 1.10,
    },
    "Curwen": {
        "bg": "#f4fbf7", "ink": "#0f5a46", "sel": "#0e8b6f", "grid": "#b9ddcb",
        "lyric": "#1b6aa8", "mnum": "#5a9c84", "brace": "#0f5a46",
        "font": "Segoe UI", "pdf_font": "Helvetica", "row_scale": 1.05, "gap_scale": 1.15,
    },
    "Methodist": {
        "bg": "#f7f8ff", "ink": "#1d2d6b", "sel": "#5a42c8", "grid": "#c9d2ee",
        "lyric": "#8a255a", "mnum": "#6a78a8", "brace": "#2e3f88",
        "font": "Cambria", "pdf_font": "Helvetica", "row_scale": 1.12, "gap_scale": 1.18,
    },
    "Continental": {
        "bg": "#f6f7f8", "ink": "#1f1f1f", "sel": "#0c7c86", "grid": "#cad2d8",
        "lyric": "#0c7281", "mnum": "#5f6b72", "brace": "#27424a",
        "font": "Courier New", "pdf_font": "Courier", "row_scale": 0.98, "gap_scale": 1.05,
    },
}


def _style_profile(style: str = "Standard") -> Dict[str, str]:
    return SOLFA_STYLES.get(style, SOLFA_STYLES["Standard"])


def _style_visuals(style: str = "Standard") -> Dict[str, object]:
    visual = dict(STYLE_VISUALS["Standard"])
    visual.update(STYLE_VISUALS.get(style, {}))
    return visual


def _pdf_font_name(family: str, variant: str = 'regular') -> str:
    variants = {
        'Times': {
            'regular': 'Times-Roman', 'bold': 'Times-Bold',
            'italic': 'Times-Italic', 'bolditalic': 'Times-BoldItalic'
        },
        'Helvetica': {
            'regular': 'Helvetica', 'bold': 'Helvetica-Bold',
            'italic': 'Helvetica-Oblique', 'bolditalic': 'Helvetica-BoldOblique'
        },
        'Courier': {
            'regular': 'Courier', 'bold': 'Courier-Bold',
            'italic': 'Courier-Oblique', 'bolditalic': 'Courier-BoldOblique'
        },
    }
    return variants.get(family, variants['Times']).get(variant, variants['Times']['regular'])


def _display_syllable(score: 'SolfaScore', note: 'SolfaNote') -> str:
    profile = _style_profile(getattr(score, 'solfa_style', 'Standard'))
    if note.is_rest:
        return profile['rest']
    return note.syllable or profile['rest']


def _display_beat_marker(score: 'SolfaScore', note: 'SolfaNote') -> str:
    profile = _style_profile(getattr(score, 'solfa_style', 'Standard'))
    marker = note.beat_marker or ''
    return marker.replace(':', profile.get('tie', ':'))


def _legend_text(style: str = "Standard") -> str:
    profile = _style_profile(style)
    beat = profile.get('tie', ':')
    half = ':-'.replace(':', beat)
    whole = ':-:-'.replace(':', beat)
    return (
        "d=Do  r=Re  m=Mi  f=Fa  s=Sol  l=La  t=Ti  "
        f"{profile['upper']}=upper oct   {profile['lower']}=lower oct   "
        f"{profile['rest']}=rest   {half}=half   {whole}=whole"
    )

# ── MusicXML pitch → solfa ────────────────────────────────────────────────────
CHROMATIC    = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
SOLFA_STEPS  = ['d','r','m','f','s','l','t']
MAJOR_SCALE  = [0,2,4,5,7,9,11]

def pitch_to_solfa(step: str, alter: int, octave: int,
                   key_semitone: int, style: str = "Standard") -> str:
    """Return solfa syllable with octave markers, respecting chosen style."""
    semitone = (CHROMATIC.get(step, 0) + int(alter or 0)) % 12
    rel      = (semitone - key_semitone) % 12
    try:
        idx = MAJOR_SCALE.index(rel)
    except ValueError:
        idx = min(range(7), key=lambda i: abs(MAJOR_SCALE[i] - rel))
    name     = SOLFA_STEPS[idx]
    sd       = _style_profile(style)
    home_oct = 4
    oct_diff = int(octave) - home_oct
    if oct_diff > 0:
        name = name + sd["upper"] * oct_diff
    elif oct_diff < 0:
        name = name + sd["lower"] * abs(oct_diff)
    return name

def duration_to_beat_marker(d: float) -> str:
    """Map note duration (in quarter-note beats) to tonic-solfa beat marker."""
    if d >= 4.0:  return ':-:-:-'    # double underline marker (whole)
    if d >= 3.0:  return ':-:-'      # 3-beat (dotted half)
    if d >= 2.0:  return ':-'        # single underline marker (half)
    if d >= 1.5:  return ':-.'       # dotted quarter
    if d >= 1.0:  return ':'         # quarter, no underline
    if d >= 0.75: return '.,'        # dotted eighth-ish
    if d >= 0.5:  return '.'         # eighth
    if d >= 0.25: return ','         # sixteenth
    return ':'

KEY_NAMES  = {0:'C',2:'D',4:'E',5:'F',7:'G',9:'A',11:'B',
              1:'C#',3:'D#',6:'F#',8:'G#',10:'A#'}
FLAT_NAMES = {10:'Bb',8:'Ab',3:'Eb',1:'Db',6:'Gb'}

def semitone_to_key_name(s: int, mode: str = 'major') -> str:
    name = KEY_NAMES.get(s, FLAT_NAMES.get(s, f'K{s}'))
    if mode == 'minor': name += 'm'
    return name


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SolfaNote:
    syllable    : str        # e.g. 'd', "m'", 's1'
    beat_marker : str        # e.g. ':', ':-', '.'
    is_rest     : bool = False
    lyric       : str  = ''
    part_idx    : int  = 0   # 0=Soprano / Treble, 1=Alto, 2=Tenor, 3=Bass

@dataclass
class SolfaMeasure:
    number       : int
    notes        : List[SolfaNote] = field(default_factory=list)
    time_sig_num : int = 4
    time_sig_den : int = 4

@dataclass
class SolfaScore:
    title       : str        = 'Untitled'
    doh_key     : str        = 'C'
    time_num    : int        = 4
    time_den    : int        = 4
    tempo_text  : str        = ''
    composer    : str        = ''
    dedication  : str        = ''
    date_str    : str        = ''
    arranger    : str        = ''
    copyright   : str        = ''
    parts       : List[str]  = field(default_factory=lambda: ['Soprano','Alto','Tenor','Bass'])
    measures    : List[SolfaMeasure] = field(default_factory=list)
    solfa_style : str        = 'Standard'


# ═══════════════════════════════════════════════════════════════════════════════
#  MUSICXML PARSER
# ═══════════════════════════════════════════════════════════════════════════════

def parse_musicxml(path: str, style: str = "Standard") -> SolfaScore:
    # ── Robust XML load: strip UTF-8 BOM, handle encoding declarations ────────
    with open(path, 'rb') as _fh:
        _raw = _fh.read()
    # Strip UTF-8 BOM (EF BB BF) that causes "not well-formed" SAX errors
    if _raw.startswith(b'\xef\xbb\xbf'):
        _raw = _raw[3:]
    # Strip UTF-16 BOMs
    if _raw.startswith(b'\xff\xfe') or _raw.startswith(b'\xfe\xff'):
        _raw = _raw[2:]
    # Some MusicXML exporters write a standalone <?xml …?> without proper
    # encoding declaration – force UTF-8 parse via BytesIO
    import io as _io
    try:
        root = ET.fromstring(_raw)
    except ET.ParseError:
        # Last resort: try stripping the XML declaration line entirely
        _txt = _raw.decode('utf-8', errors='replace')
        _txt = re.sub(r'^<\?xml[^?]*\?>\s*', '', _txt, flags=re.DOTALL)
        root = ET.fromstring(_txt.encode('utf-8'))
    ns   = ''
    if root.tag.startswith('{'):
        ns = root.tag.split('}')[0] + '}'

    def tag(t): return f'{ns}{t}'

    score = SolfaScore(solfa_style=style)

    # Title
    work = root.find(tag('work'))
    if work is not None:
        wt = work.find(tag('work-title'))
        if wt is not None and wt.text: score.title = wt.text.strip()
    mv = root.find(tag('movement-title'))
    if mv is not None and mv.text: score.title = mv.text.strip()

    # Composer / Dedication / Copyright
    id_el = root.find(tag('identification'))
    if id_el is not None:
        for c in id_el.findall(tag('creator')):
            t = c.get('type', '')
            if t == 'composer'  and c.text: score.composer  = c.text.strip()
            if t == 'arranger'  and c.text: score.arranger  = c.text.strip()
        for r in id_el.findall(tag('rights')):
            if r.text: score.dedication = r.text.strip()
        enc = id_el.find(tag('encoding'))
        if enc is not None:
            ed = enc.find(tag('encoding-date'))
            if ed is not None and ed.text: score.date_str = ed.text.strip()

    # Tempo from directions
    for d in root.findall(f'.//{tag("words")}'):
        if d.text and any(w in d.text.lower() for w in
                          ['allegro','moderato','andante','adagio','vivace','largo','lento']):
            score.tempo_text = d.text.strip()
            break

    # Parts names
    parts_names = []
    for pn in root.findall(f'.//{tag("score-part")}'):
        nm = pn.find(tag('part-name'))
        parts_names.append(nm.text.strip() if nm is not None and nm.text else 'Part')
    if parts_names: score.parts = parts_names

    key_semitone = 0
    mode         = 'major'
    measure_dict : Dict[int, SolfaMeasure] = {}
    divisions    = 1

    for p_idx, part_el in enumerate(root.findall(f'.//{tag("part")}')):
        for meas_el in part_el.findall(tag('measure')):
            mnum = int(meas_el.get('number', 1))
            if mnum not in measure_dict:
                measure_dict[mnum] = SolfaMeasure(number=mnum)
            meas = measure_dict[mnum]

            # Attributes
            attr = meas_el.find(tag('attributes'))
            if attr is not None:
                k = attr.find(tag('key'))
                if k is not None:
                    fifths_el = k.find(tag('fifths'))
                    mode_el   = k.find(tag('mode'))
                    if fifths_el is not None:
                        fifths       = int(fifths_el.text or 0)
                        key_semitone = (fifths * 7) % 12
                    if mode_el is not None and mode_el.text:
                        mode = mode_el.text.strip()
                t = attr.find(tag('time'))
                if t is not None:
                    b  = t.find(tag('beats'))
                    bt = t.find(tag('beat-type'))
                    if b is not None and bt is not None:
                        score.time_num        = int(b.text  or 4)
                        score.time_den        = int(bt.text or 4)
                        meas.time_sig_num     = score.time_num
                        meas.time_sig_den     = score.time_den
                d_el = attr.find(tag('divisions'))
                if d_el is not None:
                    divisions = int(d_el.text or 1)

            # Notes
            for note_el in meas_el.findall(tag('note')):
                is_rest = note_el.find(tag('rest')) is not None
                dur_el  = note_el.find(tag('duration'))
                dur_val = float(dur_el.text) / divisions if dur_el is not None else 1.0
                bm      = duration_to_beat_marker(dur_val)

                lyric = ''
                lyr_el = note_el.find(tag('lyric'))
                if lyr_el is not None:
                    tx = lyr_el.find(tag('text'))
                    if tx is not None and tx.text: lyric = tx.text

                if is_rest:
                    meas.notes.append(SolfaNote('-', bm, True, lyric, p_idx))
                else:
                    pitch_el = note_el.find(tag('pitch'))
                    if pitch_el is None: continue
                    step_el  = pitch_el.find(tag('step'))
                    alt_el   = pitch_el.find(tag('alter'))
                    oct_el   = pitch_el.find(tag('octave'))
                    step     = step_el.text  if step_el  is not None else 'C'
                    alter    = int(float(alt_el.text)) if alt_el is not None and alt_el.text else 0
                    octave   = int(oct_el.text) if oct_el is not None else 4
                    syllable = pitch_to_solfa(step, alter, octave, key_semitone, style)
                    meas.notes.append(SolfaNote(syllable, bm, False, lyric, p_idx))

    score.doh_key  = semitone_to_key_name(key_semitone, mode)
    score.measures = [measure_dict[k] for k in sorted(measure_dict)]
    return score


# ═══════════════════════════════════════════════════════════════════════════════
#  INTERACTIVE CANVAS
# ═══════════════════════════════════════════════════════════════════════════════

class SolfaCanvas(tk.Canvas):
    """
    Interactive Tonic Solfa notation canvas.
    Hymn-book layout: curly brace · measure numbers · part initials · barlines.
    """

    # ── Layout constants (adjustable via resize toolbar) ─────────────────────
    MARGIN_X     = 70
    MARGIN_TOP   = 120
    ROW_HEIGHT   = 96      # per part row (voice) – extra breathing room
    SYSTEM_GAP   = 36
    MEAS_PER_ROW = 4       # default; auto-adjusts if ROW_HEIGHT changed
    MEAS_MIN_W   = 150
    FONT_SIZE    = 11      # note font size

    # Palette  ── dynamically themed per solfa style
    BG    = '#FFFDF5'
    INK   = '#110900'
    SEL   = '#1a4da8'
    GRID  = '#d4c8b0'
    LYRIC = '#1a3a7a'
    MNUM  = '#888888'
    BRACE = '#333333'

    def _current_visuals(self):
        return _style_visuals(getattr(getattr(self, 'score', None), 'solfa_style', 'Standard'))

    def _row_metrics(self):
        visual = self._current_visuals()
        row_h = max(50, int(self.ROW_HEIGHT * float(visual.get('row_scale', 1.0))))
        sys_gap = max(16, int(self.SYSTEM_GAP * float(visual.get('gap_scale', 1.0))))
        return row_h, sys_gap

    # ── Font factories (rebuilt whenever font_size changes) ──────────────────
    def _fonts(self):
        sz = self.FONT_SIZE
        visual = self._current_visuals()
        family = str(visual.get('font', 'Times New Roman'))
        return dict(
            title  = (family, sz + 4, 'bold'),
            dedic  = (family, max(7, sz - 2), 'italic'),
            doh    = (family, sz, 'bold'),
            tempo  = (family, max(7, sz - 1), 'italic'),
            mnum   = (family, max(6, sz - 4)),
            note   = (family, sz, 'bold'),
            lyric  = (family, max(7, sz - 3), 'italic'),
            brace  = (family, int(sz * 2.4), 'bold'),
            part   = (family, max(7, sz - 2), 'bold italic'),
            footer = (family, max(6, sz - 4)),
        )

    def __init__(self, master, score: SolfaScore, **kw):
        super().__init__(master, bg=self.BG, **kw)
        self.score      = score
        self.selected   : Optional[Tuple[int,int,int]] = None
        self._items     : Dict = {}
        self._note_rects: Dict = {}
        self._compat_measure_width = int(self.MEAS_MIN_W)
        beats = max(1, int(getattr(getattr(self, 'score', None), 'time_num', 4) or 4))
        self._compat_beat_width = max(20, int(self._compat_measure_width / beats))
        self.bind('<Configure>',      lambda e: self.redraw())
        self.bind('<Button-1>',       self._on_click)
        self.bind('<Double-Button-1>',self._on_dbl_click)
        self.bind('<Key>',            self._on_key)
        self.bind('<Delete>',         self._delete_selected)
        self.configure(highlightthickness=0)
        self.redraw()

    @property
    def beat_width(self) -> int:
        return self._compat_beat_width

    @beat_width.setter
    def beat_width(self, value: int):
        beats = max(1, int(getattr(getattr(self, 'score', None), 'time_num', 4) or 4))
        self._compat_beat_width = max(20, int(value))
        self.MEAS_MIN_W = max(80, self._compat_beat_width * beats)
        self._compat_measure_width = self.MEAS_MIN_W

    @property
    def measure_width(self) -> int:
        return self._compat_measure_width

    @measure_width.setter
    def measure_width(self, value: int):
        self._compat_measure_width = max(80, int(value))
        self.MEAS_MIN_W = self._compat_measure_width

    def render(self):
        self.redraw()

    # ── layout helpers ────────────────────────────────────────────────────────

    def _cw(self):
        return max(self.winfo_width(), 820)

    def _mpr(self):
        avail = self._cw() - 2 * self.MARGIN_X - 40
        return max(1, min(6, int(avail / self.MEAS_MIN_W)))

    def _mw(self):
        avail = self._cw() - 2 * self.MARGIN_X - 40
        return avail / self._mpr()

    # ── drawing ───────────────────────────────────────────────────────────────

    def redraw(self):
        visual = self._current_visuals()
        self.BG = str(visual.get('bg', self.BG))
        self.INK = str(visual.get('ink', self.INK))
        self.SEL = str(visual.get('sel', self.SEL))
        self.GRID = str(visual.get('grid', self.GRID))
        self.LYRIC = str(visual.get('lyric', self.LYRIC))
        self.MNUM = str(visual.get('mnum', self.MNUM))
        self.BRACE = str(visual.get('brace', self.BRACE))
        self.configure(bg=self.BG)
        self.delete('all')
        self._items.clear()
        self._note_rects.clear()
        F = self._fonts()
        self._draw_header(F)
        self._draw_measures(F)
        self._draw_footer(F)
        self._update_scrollregion()

    def _draw_header(self, F):
        cx  = self._cw() / 2
        y   = 22
        # ── thin rule above title ──
        self.create_line(self.MARGIN_X, y - 4, self._cw() - self.MARGIN_X, y - 4,
                         fill=self.INK, width=1, tags='header')
        # ── Title centred + underlined ──
        tid = self.create_text(cx, y, text=self.score.title.upper(),
                               font=F['title'], fill=self.INK,
                               anchor='n', tags='header')
        bb  = self.bbox(tid)
        if bb:
            self.create_line(bb[0], bb[3] + 2, bb[2], bb[3] + 2,
                             fill=self.INK, width=1, tags='header')
        y = (bb[3] if bb else y + 20) + 8
        # ── Dedication italic ──
        if self.score.dedication:
            self.create_text(cx, y, text=f'({self.score.dedication})',
                             font=F['dedic'], fill=self.INK,
                             anchor='n', tags='header')
            y += 18
        # ── Doh / Time (left)   Composer (right) ──
        y += 4
        self.create_text(self.MARGIN_X, y,
                         text=f'Doh is {self.score.doh_key}   '
                              f'Time: {self.score.time_num}/{self.score.time_den}',
                         font=F['doh'], fill=self.INK, anchor='w', tags='header')
        if self.score.composer:
            comp = f'By: {self.score.composer}'
            if self.score.date_str:
                comp += f'  {self.score.date_str}'
            self.create_text(self._cw() - self.MARGIN_X, y,
                             text=comp, font=F['doh'],
                             fill=self.INK, anchor='e', tags='header')
        y += 18
        # ── Tempo italic ──
        if self.score.tempo_text:
            self.create_text(self.MARGIN_X, y,
                             text=self.score.tempo_text,
                             font=F['tempo'], fill=self.INK,
                             anchor='w', tags='header')
            y += 16
        # ── thin rule below header ──
        self.create_line(self.MARGIN_X, y + 4,
                         self._cw() - self.MARGIN_X, y + 4,
                         fill=self.GRID, width=1, tags='header')
        self.MARGIN_TOP = y + 16   # dynamic header height

    def _draw_measures(self, F):
        if not self.score.measures: return
        mpr    = self._mpr()
        mw     = self._mw()
        nparts = max(1, len(self.score.parts))
        row_h, sys_gap = self._row_metrics()
        sys_h  = nparts * row_h + sys_gap
        left_x = self.MARGIN_X + 40   # music starts after brace + label

        for idx, meas in enumerate(self.score.measures):
            row  = idx // mpr
            col  = idx  % mpr
            x0   = left_x + col * mw
            y0   = self.MARGIN_TOP + row * sys_h

            # ── System brace on first column ──
            if col == 0:
                bh = nparts * row_h
                # Curly brace character
                self.create_text(self.MARGIN_X + 16, y0 + bh / 2,
                                 text='{', font=F['brace'],
                                 fill=self.BRACE, anchor='center', tags='barline')
                # Left system double-barline
                self.create_line(left_x - 4, y0, left_x - 4, y0 + bh,
                                 fill=self.INK, width=2.5, tags='barline')
                self.create_line(left_x - 1, y0, left_x - 1, y0 + bh,
                                 fill=self.INK, width=0.7, tags='barline')

            # ── Measure number (small grey above) ──
            self.create_text(x0 + 3, y0 - 1,
                             text=str(meas.number),
                             font=F['mnum'], fill=self.MNUM,
                             anchor='sw', tags='mnum')

            # ── Each part row ──
            for p_idx in range(nparts):
                py = y0 + p_idx * row_h
                self._draw_part_row(meas, idx, p_idx, x0, py, mw, row_h, F)

            # ── Right barline (double at row-end / final, single otherwise) ──
            bh   = nparts * row_h
            is_final  = (idx == len(self.score.measures) - 1)
            is_rowend = ((idx + 1) % mpr == 0)
            if is_final:
                self.create_line(x0+mw-3, y0, x0+mw-3, y0+bh,
                                 fill=self.INK, width=3.5, tags='barline')
                self.create_line(x0+mw+1, y0, x0+mw+1, y0+bh,
                                 fill=self.INK, width=1,   tags='barline')
            elif is_rowend:
                self.create_line(x0+mw-2, y0, x0+mw-2, y0+bh,
                                 fill=self.INK, width=2,   tags='barline')
                self.create_line(x0+mw+1, y0, x0+mw+1, y0+bh,
                                 fill=self.INK, width=0.8, tags='barline')
            else:
                self.create_line(x0+mw, y0, x0+mw, y0+bh,
                                 fill=self.INK, width=1,   tags='barline')

    def _draw_part_row(self, meas: SolfaMeasure, meas_idx: int,
                       p_idx: int, x0: float, y0: float, mw: float, row_h: int, F):
        notes    = [n for n in meas.notes if n.part_idx == p_idx]
        base_y   = y0 + row_h * 0.44
        lyric_y  = y0 + row_h * 0.70
        col      = meas_idx % self._mpr()

        # ── Part initial flush-left ──
        if col == 0:
            init = self.score.parts[p_idx][0] if p_idx < len(self.score.parts) else ''
            self.create_text(self.MARGIN_X + 40, base_y,
                             text=init, font=F['part'],
                             fill=self.BRACE, anchor='e', tags='partlabel')

        # ── Row background line ──
        self.create_line(x0, y0 + row_h,
                         x0 + mw, y0 + row_h,
                         fill=self.GRID, width=0.4, tags='gridline')

        if not notes:
            self.create_text(x0 + 6, base_y, text='-:-',
                             font=F['note'], fill='#bbbbbb', anchor='w')
            return

        # Leave generous inter-note padding (min 8px gap between slots)
        slot_w = mw / max(len(notes), 1)
        for n_idx, note in enumerate(notes):
            nx   = x0 + n_idx * slot_w + 6   # +6px left-inset per slot
            syl  = _display_syllable(self.score, note)
            bm   = _display_beat_marker(self.score, note)
            # Separate syllable and beat marker with thin space for readability
            txt  = syl + ' ' + bm if bm else syl
            key  = (meas_idx, n_idx, p_idx)
            sel  = (key == self.selected)
            clr  = self.SEL if sel else self.INK

            rect_id = self.create_rectangle(
                nx - 2, y0 + 3, nx + slot_w - 2, y0 + row_h - 3,
                outline=self.SEL if sel else '',
                fill='#dce8f8' if sel else '',
                tags=f'note_{meas_idx}_{n_idx}_{p_idx}')

            tid = self.create_text(nx, base_y, text=txt,
                                   font=F['note'], fill=clr,
                                   anchor='w',
                                   tags=f'note_{meas_idx}_{n_idx}_{p_idx}')

            # Lyrics in italic blue below SA rows
            if note.lyric and p_idx < 2:
                self.create_text(nx, lyric_y, text=note.lyric,
                                 font=F['lyric'], fill=self.LYRIC,
                                 anchor='w',
                                 tags=f'note_{meas_idx}_{n_idx}_{p_idx}')

            for cid in (rect_id, tid):
                self._items[cid]      = key
                self._note_rects[key] = self._note_rects.get(key,[]) + [cid]

    def _draw_footer(self, F):
        """Legend + page number at bottom of canvas."""
        all_bb = self.bbox('all')
        if not all_bb: return
        fy = all_bb[3] + 12
        cx = self._cw() / 2
        legend = _legend_text(getattr(self.score, 'solfa_style', 'Standard'))
        self.create_line(self.MARGIN_X, fy - 4,
                         self._cw() - self.MARGIN_X, fy - 4,
                         fill=self.GRID, width=0.7)
        self.create_text(cx, fy, text=legend,
                         font=F['footer'], fill=self.MNUM,
                         anchor='n', tags='footer')
        self.create_text(self._cw() - self.MARGIN_X, fy,
                         text='1', font=F['footer'],
                         fill=self.MNUM, anchor='ne', tags='footer')

    # ── interaction ───────────────────────────────────────────────────────────

    def _on_click(self, event):
        self.focus_set()
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        items = self.find_overlapping(x-3, y-3, x+3, y+3)
        for item in reversed(items):
            key = self._items.get(item)
            if key:
                self.selected = key
                self.redraw()
                return
        self.selected = None
        self.redraw()

    def _on_dbl_click(self, event):
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        items = self.find_overlapping(x-3, y-3, x+3, y+3)
        for item in reversed(items):
            key = self._items.get(item)
            if key:
                self.selected = key
                self._edit_selected()
                return

    def _on_key(self, event):
        if self.selected and event.char and event.char.isprintable():
            self._edit_selected(event.char)

    def _edit_selected(self, prefill=''):
        if self.selected is None: return
        mi, ni, pi = self.selected
        if mi >= len(self.score.measures): return
        meas  = self.score.measures[mi]
        notes = [n for n in meas.notes if n.part_idx == pi]
        if ni >= len(notes): return
        note  = notes[ni]
        dlg   = NoteEditDialog(self, note, title='Edit Note')
        self.wait_window(dlg)
        if dlg.result:
            note.syllable    = dlg.result['syllable']
            note.beat_marker = dlg.result['beat_marker']
            note.lyric       = dlg.result['lyric']
            note.is_rest     = dlg.result['is_rest']
            self.redraw()

    def _delete_selected(self, event=None):
        if self.selected is None: return
        mi, ni, pi = self.selected
        meas       = self.score.measures[mi]
        part_notes = [(i, n) for i, n in enumerate(meas.notes) if n.part_idx == pi]
        if ni < len(part_notes):
            del meas.notes[part_notes[ni][0]]
        self.selected = None
        self.redraw()

    def add_note_to_selected_measure(self):
        if not self.score.measures: return
        mi    = self.selected[0] if self.selected else len(self.score.measures) - 1
        pi    = self.selected[2] if self.selected else 0
        blank = SolfaNote('d', ':', False, '', pi)
        dlg   = NoteEditDialog(self, blank, title='Add Note')
        self.wait_window(dlg)
        if dlg.result:
            blank.syllable    = dlg.result['syllable']
            blank.beat_marker = dlg.result['beat_marker']
            blank.lyric       = dlg.result['lyric']
            blank.is_rest     = dlg.result['is_rest']
            self.score.measures[mi].notes.append(blank)
            self.redraw()

    def add_measure(self):
        n = len(self.score.measures) + 1
        self.score.measures.append(
            SolfaMeasure(n, [], self.score.time_num, self.score.time_den))
        self.redraw()

    def auto_fit_notes(self):
        """Distribute notes evenly into measures (one note per beat)."""
        for meas in self.score.measures:
            beats = meas.time_sig_num
            for p_idx in range(len(self.score.parts)):
                pnotes = [n for n in meas.notes if n.part_idx == p_idx]
                if not pnotes: continue
                for i, note in enumerate(pnotes):
                    if beats == 2:
                        note.beat_marker = ':' if i < beats else '.'
                    elif beats == 4:
                        note.beat_marker = ':' if i == 0 else (':-' if i == 1 else '.')
        self.redraw()

    def _update_scrollregion(self):
        self.update_idletasks()
        bb = self.bbox('all')
        if bb:
            self.configure(scrollregion=(bb[0]-12, bb[1]-12, bb[2]+12, bb[3]+24))

    def load_score(self, score: SolfaScore):
        self.score    = score
        self.selected = None
        self.redraw()

    def set_font_size(self, sz: int):
        self.FONT_SIZE = max(7, min(22, sz))
        self.redraw()

    def set_row_height(self, rh: int):
        self.ROW_HEIGHT = max(50, min(160, rh))
        self.redraw()

    def set_meas_per_row(self, mpr: int):
        self.MEAS_PER_ROW = max(1, min(8, mpr))
        self.MEAS_MIN_W   = max(100, (self._cw() - 2*self.MARGIN_X - 40) // self.MEAS_PER_ROW - 1)
        self.redraw()

    def set_meas_width(self, mw: int):
        self.MEAS_MIN_W = max(80, min(400, mw))
        self.redraw()


# ═══════════════════════════════════════════════════════════════════════════════
#  NOTE EDIT DIALOG
# ═══════════════════════════════════════════════════════════════════════════════

class NoteEditDialog(tk.Toplevel):
    BEAT_OPTIONS = [
        ':',         # quarter
        ':-',        # half
        ':-:-',      # dotted half (3-beat)
        ':-:-:-',    # whole
        ':-.',       # dotted quarter
        '.,' ,       # dotted eighth
        '.',         # eighth
        ',',         # sixteenth
    ]

    def __init__(self, parent, note: SolfaNote, title='Edit Note'):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.result = None
        self._build(note)
        self.grab_set()
        self.transient(parent)
        geom = f'+{parent.winfo_rootx()+200}+{parent.winfo_rooty()+200}'
        self.geometry(geom)

    def _build(self, note: SolfaNote):
        pad = dict(padx=10, pady=5)
        TNR = 'Times New Roman'

        tk.Label(self, text='Syllable / Rest:', font=(TNR,10)).grid(row=0,column=0,sticky='w',**pad)
        self._syl = tk.Entry(self, font=(TNR,12,'bold'), width=10)
        self._syl.insert(0, note.syllable if not note.is_rest else '-')
        self._syl.grid(row=0, column=1, **pad)

        tk.Label(self, text='Beat marker:', font=(TNR,10)).grid(row=1,column=0,sticky='w',**pad)
        self._bm = ttk.Combobox(self, values=self.BEAT_OPTIONS, width=14, font=(TNR,11))
        self._bm.set(note.beat_marker)
        self._bm.grid(row=1, column=1, **pad)

        tk.Label(self, text='Lyric text:', font=(TNR,10)).grid(row=2,column=0,sticky='w',**pad)
        self._lyric = tk.Entry(self, font=(TNR,10,'italic'), width=18)
        self._lyric.insert(0, note.lyric)
        self._lyric.grid(row=2, column=1, **pad)

        self._is_rest = tk.BooleanVar(value=note.is_rest)
        tk.Checkbutton(self, text='Rest', variable=self._is_rest,
                       font=(TNR,10)).grid(row=3, column=0, columnspan=2, **pad)

        # Octave helper
        frm = tk.Frame(self); frm.grid(row=4, column=0, columnspan=2, pady=4)
        tk.Label(frm, text='Octave:', font=(TNR,9)).pack(side='left')
        for lbl, sfx in [("Normal",""), ("Upper  '","'"), ("Lower  ,",",")]:
            tk.Button(frm, text=lbl, font=(TNR,8),
                      command=lambda s=sfx: self._apply_octave(s)).pack(side='left',padx=3)

        # Solfa quick-insert
        qf = tk.LabelFrame(self, text='Quick insert', font=(TNR,8), padx=6, pady=4)
        qf.grid(row=5, column=0, columnspan=2, padx=10, pady=4, sticky='ew')
        for i, syl in enumerate(['d','r','m','f','s','l','t']):
            tk.Button(qf, text=syl, width=3, font=(TNR,10,'bold'),
                      command=lambda s=syl: self._quick(s)).grid(row=0,column=i,padx=2)

        bf = tk.Frame(self); bf.grid(row=6, column=0, columnspan=2, pady=8)
        tk.Button(bf, text='OK', width=9, command=self._ok,
                  bg='#1a4da8', fg='white', font=(TNR,10,'bold')).pack(side='left',padx=6)
        tk.Button(bf, text='Cancel', width=9, command=self.destroy,
                  font=(TNR,10)).pack(side='left')

        self._syl.focus_set()
        self.bind('<Return>', lambda e: self._ok())
        self.bind('<Escape>', lambda e: self.destroy())

    def _quick(self, syl):
        self._syl.delete(0,'end')
        self._syl.insert(0, syl)

    def _apply_octave(self, suffix):
        base = self._syl.get().rstrip("'1₁,")
        self._syl.delete(0,'end')
        self._syl.insert(0, base + suffix)

    def _ok(self):
        syl = self._syl.get().strip() or 'd'
        bm  = self._bm.get().strip()  or ':'
        self.result = dict(syllable=syl, beat_marker=bm,
                           lyric=self._lyric.get(),
                           is_rest=self._is_rest.get())
        self.destroy()


# ═══════════════════════════════════════════════════════════════════════════════
#  SCORE PROPERTIES DIALOG
# ═══════════════════════════════════════════════════════════════════════════════

class ScorePropsDialog(tk.Toplevel):
    def __init__(self, parent, score: SolfaScore):
        super().__init__(parent)
        self.title('Score Properties')
        self.resizable(False, False)
        self.changed = False
        self._score  = score
        self._build()
        self.grab_set(); self.transient(parent)
        self.geometry(f'+{parent.winfo_rootx()+120}+{parent.winfo_rooty()+120}')

    def _build(self):
        s   = self._score
        pad = dict(padx=12, pady=5)
        TNR = 'Times New Roman'
        fields = [
            ('Title',          'title'),
            ('Doh Key',        'doh_key'),
            ('Composer',       'composer'),
            ('Date',           'date_str'),
            ('Dedication',     'dedication'),
            ('Arranger',       'arranger'),
            ('Copyright',      'copyright'),
            ('Tempo text',     'tempo_text'),
            ('Time (num/den)', None),
        ]
        self._vars = {}
        for r, (lbl, attr) in enumerate(fields):
            tk.Label(self, text=lbl+':', font=(TNR,10), width=18,
                     anchor='w').grid(row=r, column=0, **pad)
            if attr:
                v = tk.StringVar(value=getattr(s, attr, ''))
                self._vars[attr] = v
                tk.Entry(self, textvariable=v, font=(TNR,10),
                         width=32).grid(row=r, column=1, **pad)
            else:
                fr = tk.Frame(self); fr.grid(row=r, column=1, **pad)
                self._tnum = tk.Entry(fr, width=4, font=(TNR,11))
                self._tnum.insert(0, str(s.time_num)); self._tnum.pack(side='left')
                tk.Label(fr, text='/').pack(side='left')
                self._tden = tk.Entry(fr, width=4, font=(TNR,11))
                self._tden.insert(0, str(s.time_den)); self._tden.pack(side='left')

        # Solfa style selector
        row_s = len(fields)
        tk.Label(self, text='Solfa Style:', font=(TNR,10),
                 width=18, anchor='w').grid(row=row_s, column=0, **pad)
        self._style_var = tk.StringVar(value=s.solfa_style)
        ttk.Combobox(self, textvariable=self._style_var,
                     values=list(SOLFA_STYLES.keys()),
                     state='readonly', width=20,
                     font=(TNR,10)).grid(row=row_s, column=1, **pad)

        # Parts list
        row_p = row_s + 1
        tk.Label(self, text='Parts (comma sep):', font=(TNR,10),
                 width=18, anchor='w').grid(row=row_p, column=0, **pad)
        self._parts_var = tk.StringVar(value=', '.join(s.parts))
        tk.Entry(self, textvariable=self._parts_var, font=(TNR,10),
                 width=32).grid(row=row_p, column=1, **pad)

        bf = tk.Frame(self); bf.grid(row=row_p+1, column=0, columnspan=2, pady=10)
        tk.Button(bf, text='Apply', width=10, bg='#1a4da8', fg='white',
                  font=(TNR,10,'bold'), command=self._apply).pack(side='left',padx=8)
        tk.Button(bf, text='Cancel', width=10,
                  font=(TNR,10), command=self.destroy).pack(side='left')
        self.bind('<Return>', lambda e: self._apply())

    def _apply(self):
        s = self._score
        for attr, v in self._vars.items():
            setattr(s, attr, v.get())
        try:
            s.time_num = int(self._tnum.get())
            s.time_den = int(self._tden.get())
        except ValueError: pass
        s.solfa_style = self._style_var.get()
        parts_raw     = self._parts_var.get()
        if parts_raw.strip():
            s.parts = [p.strip() for p in parts_raw.split(',') if p.strip()]
        self.changed = True
        self.destroy()


# ═══════════════════════════════════════════════════════════════════════════════
#  PDF RENDERER  –  Hymn-book engraver quality
# ═══════════════════════════════════════════════════════════════════════════════

def _pdf_safe(txt: str) -> str:
    """Ensure text is safe for standard PDF fonts (strip unicode subscripts)."""
    repl = {'₁':'1','₂':'2','₃':'3','₄':'4',
            '¹':"'",'²':"''",'³':"'''",
            '\u2019':"'",'\u2018':"'",}
    for k, v in repl.items():
        txt = txt.replace(k, v)
    return txt


def render_pdf(score: SolfaScore, path: str,
               pagesize=None, measures_per_row: int = 4,
               font_size: float = 9.0, row_height: Optional[int] = None):
    """
    Engraver-quality PDF that follows the current Solfa Canvas Pro look.
    Style theme, font family, bar density, and row spacing are preserved in export.
    """
    # Local imports so the function works even when module-level names
    # are shadowed by mocking in test environments.
    try:
        from reportlab.pdfgen import canvas as _rl_canvas
        from reportlab.lib.pagesizes import A4 as _A4, LETTER as _LETTER
        from reportlab.lib.units import mm as _mm
        from reportlab.lib import colors as _rl_colors
    except ImportError:
        try:
            import tkinter.messagebox as _mb
            _mb.showerror('Missing library', 'pip install reportlab')
        except Exception:
            print('ERROR: pip install reportlab')
        return

    if pagesize is None:
        pagesize = _A4

    # ── Colours & fonts (mirrors canvas theme) ──────────────────────────────
    mm = _mm
    rl_colors = _rl_colors
    rl_canvas = _rl_canvas

    style_name = getattr(score, 'solfa_style', 'Standard')
    visual = _style_visuals(style_name)
    pdf_family = str(visual.get('pdf_font', 'Times'))

    C_BG     = rl_colors.HexColor(str(visual.get('bg', '#FFFDF5')))
    C_INK    = rl_colors.HexColor(str(visual.get('ink', '#110900')))
    C_HEAD   = rl_colors.HexColor(str(visual.get('brace', '#1a0a00')))
    C_BARNUM = rl_colors.HexColor(str(visual.get('mnum', '#888888')))
    C_LYRIC  = rl_colors.HexColor(str(visual.get('lyric', '#1a3a7a')))
    C_GRID   = rl_colors.HexColor(str(visual.get('grid', '#c8bda8')))
    C_BAR    = rl_colors.HexColor(str(visual.get('brace', '#221100')))

    W, H   = pagesize
    ML     = 16 * mm   # left margin
    MR     = 16 * mm   # right margin
    MT     = 18 * mm   # top margin
    MB     = 14 * mm   # bottom margin

    # ── Font aliases (built-ins chosen per style for reliable PDF output) ───
    F_TITLE   = (_pdf_font_name(pdf_family, 'bold'),       font_size + 5)
    F_DEDIC   = (_pdf_font_name(pdf_family, 'italic'),     max(6.5, font_size - 1))
    F_DOH     = (_pdf_font_name(pdf_family, 'bold'),       font_size)
    F_TEMPO   = (_pdf_font_name(pdf_family, 'italic'),     max(6.5, font_size - 1))
    F_MNUM    = (_pdf_font_name(pdf_family, 'regular'),    max(5.5, font_size - 3.5))
    F_NOTE    = (_pdf_font_name(pdf_family, 'bold'),       font_size)
    F_LYRIC   = (_pdf_font_name(pdf_family, 'italic'),     max(6, font_size - 2))
    F_PART    = (_pdf_font_name(pdf_family, 'bolditalic'), max(6.5, font_size - 1))
    F_FOOTER  = (_pdf_font_name(pdf_family, 'regular'),    max(5.5, font_size - 3))
    F_LEGEND  = (_pdf_font_name(pdf_family, 'regular'),    max(5,   font_size - 3.5))

    c = rl_canvas.Canvas(path, pagesize=pagesize)
    page_num = [1]

    def paint_page_background():
        c.saveState()
        c.setFillColor(C_BG)
        c.rect(0, 0, W, H, stroke=0, fill=1)
        c.restoreState()

    paint_page_background()

    # ── Layout dims ──────────────────────────────────────────────────────────
    mpr      = measures_per_row
    music_w  = W - ML - MR
    brace_x  = ML
    label_w  = 7  * mm
    music_x0 = ML + label_w + 3 * mm
    col_w    = (W - music_x0 - MR) / mpr
    base_voice_h = (font_size + 2) * mm
    if row_height is not None:
        base_voice_h = max(base_voice_h, (float(row_height) / 7.5) * mm)
    voice_h  = base_voice_h * float(visual.get('row_scale', 1.0))
    sys_gap  = max(4 * mm, voice_h * 0.32 * float(visual.get('gap_scale', 1.0)))
    lyric_h  = (font_size - 1) * mm

    # ── Footer helper ─────────────────────────────────────────────────────────
    def draw_footer():
        c.setFont(*F_LEGEND)
        c.setFillColor(C_BARNUM)
        legend = _legend_text(getattr(score, 'solfa_style', 'Standard'))
        c.drawString(ML, MB - 3*mm, legend)
        c.setFont(*F_MNUM)
        c.drawCentredString(W/2, MB - 3*mm, str(page_num[0]))

    def new_page():
        draw_footer()
        c.showPage()
        page_num[0] += 1
        paint_page_background()
        # Running title
        c.setFont(*F_DOH)
        c.setFillColor(C_HEAD)
        c.drawCentredString(W/2, H - MT/2, _pdf_safe(score.title.upper()))
        c.setStrokeColor(C_GRID)
        c.setLineWidth(0.4)
        c.line(ML, H - MT/2 - 2*mm, W - MR, H - MT/2 - 2*mm)
        return H - MT - 4*mm

    # ── First page header ─────────────────────────────────────────────────────
    y = H - MT

    # thin top rule
    c.setStrokeColor(C_INK)
    c.setLineWidth(0.5)
    c.line(ML, y, W - MR, y)
    y -= 5 * mm

    c.setFont(*F_TITLE)
    c.setFillColor(C_HEAD)
    title_txt = _pdf_safe(score.title.upper())
    c.drawCentredString(W/2, y, title_txt)
    # underline
    tw = c.stringWidth(title_txt, F_TITLE[0], F_TITLE[1])
    c.setLineWidth(0.5)
    c.line(W/2 - tw/2, y - 1*mm, W/2 + tw/2, y - 1*mm)
    y -= 6 * mm

    if score.dedication:
        c.setFont(*F_DEDIC)
        c.setFillColor(C_INK)
        ded = _pdf_safe(f'({score.dedication})')
        c.drawCentredString(W/2, y, ded)
        y -= 5 * mm

    c.setFont(*F_DOH)
    c.setFillColor(C_INK)
    c.drawString(ML, y, f'Doh is {score.doh_key}    Time: {score.time_num}/{score.time_den}')
    if score.composer:
        comp = f'By: {score.composer}'
        if score.date_str: comp += f'   {score.date_str}'
        c.drawRightString(W - MR, y, comp)
    y -= 5 * mm

    if score.tempo_text:
        c.setFont(*F_TEMPO)
        c.setFillColor(C_INK)
        c.drawString(ML, y, _pdf_safe(score.tempo_text))
        y -= 4 * mm

    # thin rule under header
    c.setStrokeColor(C_GRID)
    c.setLineWidth(0.5)
    c.line(ML, y, W - MR, y)
    y -= 6 * mm

    # ── Systems ───────────────────────────────────────────────────────────────
    nparts = max(1, len(score.parts))

    for row_start in range(0, len(score.measures), mpr):
        row    = score.measures[row_start: row_start + mpr]
        n_row  = len(row)
        sys_h  = nparts * voice_h

        # Page break?
        if y - sys_h - sys_gap < MB + 6*mm:
            y = new_page()

        sys_top = y
        sys_bot = y - sys_h

        # ── Curly brace (approximated with thick L-bracket) ──────────────────
        c.setStrokeColor(C_BAR)
        c.setLineWidth(2.0)
        c.line(brace_x + 1*mm, sys_top, brace_x + 1*mm, sys_bot)
        c.setLineWidth(0.8)
        c.line(brace_x + 1*mm, sys_top, brace_x + 3*mm, sys_top)
        c.line(brace_x + 1*mm, sys_bot, brace_x + 3*mm, sys_bot)
        # Draw '{' character for elegance
        c.setFont('Times-Bold', sys_h * 0.72)
        c.setFillColor(C_BAR)
        c.drawString(brace_x - 1.5*mm, sys_bot + sys_h*0.06,
                     '{' if sys_h > 12 else '|')

        # Left double barline
        c.setStrokeColor(C_BAR)
        c.setLineWidth(1.5)
        c.line(music_x0 - 2*mm, sys_top, music_x0 - 2*mm, sys_bot)
        c.setLineWidth(0.5)
        c.line(music_x0 - 0.5*mm, sys_top, music_x0 - 0.5*mm, sys_bot)

        # Top system line
        c.setStrokeColor(C_GRID)
        c.setLineWidth(0.4)
        c.line(music_x0, sys_top, W - MR, sys_top)

        # ── Part rows ─────────────────────────────────────────────────────────
        for p_idx, pname in enumerate(score.parts):
            row_top = sys_top - p_idx * voice_h
            row_bot = row_top - voice_h
            row_mid = row_top - voice_h * 0.45
            lyr_y   = row_top - voice_h * 0.72

            # Part initial flush-left
            c.setFont(*F_PART)
            c.setFillColor(C_BAR)
            c.drawRightString(music_x0 - 1*mm, row_mid, pname[0])

            # Bottom part rule
            c.setStrokeColor(C_GRID)
            c.setLineWidth(0.35)
            c.line(music_x0, row_bot, W - MR, row_bot)

            # Left part barline
            c.setStrokeColor(C_BAR)
            c.setLineWidth(0.7)
            c.line(music_x0, row_top, music_x0, row_bot)

            for mi, meas in enumerate(row):
                mx       = music_x0 + mi * col_w
                is_final = (row_start + mi == len(score.measures) - 1)
                is_end   = (mi == n_row - 1)

                # Measure number (top-left, small grey)
                if p_idx == 0:
                    c.setFont(*F_MNUM)
                    c.setFillColor(C_BARNUM)
                    c.drawString(mx + 0.5*mm, row_top + 0.5*mm, str(meas.number))

                # Notes
                notes = [n for n in meas.notes if n.part_idx == p_idx]
                if notes:
                    slot = col_w / max(len(notes), 1)
                    for ni, note in enumerate(notes):
                        nx  = mx + ni * slot + 1.0*mm   # 1mm left-inset + natural gap
                        _syl = _display_syllable(score, note)
                        _bmv = _display_beat_marker(score, note)
                        _bm  = (' ' + _bmv) if _bmv else ''
                        txt  = _pdf_safe(_syl + _bm)
                        c.setFont(*F_NOTE)
                        c.setFillColor(C_INK)
                        c.drawString(nx, row_mid, txt)
                        # Italic blue lyrics below SA (parts 0+1)
                        if note.lyric and p_idx < 2:
                            c.setFont(*F_LYRIC)
                            c.setFillColor(C_LYRIC)
                            c.drawString(nx, lyr_y, _pdf_safe(note.lyric))
                else:
                    c.setFont(*F_NOTE)
                    c.setFillColor(C_GRID)
                    c.drawCentredString(mx + col_w/2, row_mid, '-:-')

                # Right barline
                c.setStrokeColor(C_BAR)
                if is_final:
                    c.setLineWidth(3.0)
                    c.line(mx + col_w - 1.5*mm, row_top, mx + col_w - 1.5*mm, row_bot)
                    c.setLineWidth(0.8)
                    c.line(mx + col_w + 0.3*mm, row_top, mx + col_w + 0.3*mm, row_bot)
                elif is_end:
                    c.setLineWidth(1.8)
                    c.line(mx + col_w - 0.8*mm, row_top, mx + col_w - 0.8*mm, row_bot)
                    c.setLineWidth(0.5)
                    c.line(mx + col_w + 0.5*mm, row_top, mx + col_w + 0.5*mm, row_bot)
                else:
                    c.setLineWidth(0.5)
                    c.line(mx + col_w, row_top, mx + col_w, row_bot)

        y -= sys_h + sys_gap

    draw_footer()
    c.save()


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

class SolfaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Tonic Solfa Notation  –  Professional Edition')
        self.geometry('1280x820')
        self.configure(bg='#2b2b2b')
        self._score = SolfaScore()
        self._build_ui()

    def _build_ui(self):
        self._build_menu()
        self._build_toolbar()
        self._build_resize_bar()
        self._build_main()
        self._build_status()

    # ── Menu ──────────────────────────────────────────────────────────────────

    def _build_menu(self):
        mb = tk.Menu(self, bg='#3c3c3c', fg='white',
                     activebackground='#1a4da8')
        self.config(menu=mb)

        def fm(label, items):
            m = tk.Menu(mb, tearoff=0, bg='#3c3c3c', fg='white',
                        activebackground='#1a4da8')
            mb.add_cascade(label=label, menu=m)
            for item in items:
                if item is None:
                    m.add_separator()
                else:
                    m.add_command(label=item[0], command=item[1])
            return m

        fm('File', [
            ('New Score',         self._new_score),
            ('Import MusicXML…',  self._import_xml),
            None,
            ('Export to PDF…',    self._export_pdf),
            None,
            ('Exit',              self.quit),
        ])
        fm('Edit', [
            ('Edit Selected Note  [Dbl-click]', self._edit_note),
            ('Add Note to Measure',             self._add_note),
            ('Delete Selected Note  [Del]',     self._del_note),
            ('Add Measure',                     self._add_measure),
            None,
            ('Auto-Fit Notes',                  self._auto_fit),
            ('Score Properties…',               self._score_props),
        ])
        fm('View', [
            ('Refresh Canvas',   self._refresh),
            ('Zoom In  (+)',      lambda: self._zoom(+1)),
            ('Zoom Out  (-)',     lambda: self._zoom(-1)),
        ])
        fm('Style', [
            (s, lambda st=s: self._set_style(st))
            for s in SOLFA_STYLES.keys()
        ])

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def _build_toolbar(self):
        tb = tk.Frame(self, bg='#3a3a3a', height=46)
        tb.pack(side='top', fill='x')
        tb.pack_propagate(False)

        BCF = dict(bg='#4d4d4d', fg='white',
                   font=('Times New Roman', 9, 'bold'),
                   relief='flat', padx=9, pady=5,
                   activebackground='#1a4da8', activeforeground='white',
                   cursor='hand2')

        btns = [
            ('📂 Import XML',    self._import_xml),
            ('🖨  Export PDF',   self._export_pdf),
            ('✏  Edit Note',     self._edit_note),
            ('➕ Add Note',      self._add_note),
            ('🗑 Delete',        self._del_note),
            ('📏 Add Measure',   self._add_measure),
            ('🔧 Auto-Fit',      self._auto_fit),
            ('⚙  Properties',   self._score_props),
            ('🔄 Refresh',       self._refresh),
        ]
        for lbl, cmd in btns:
            tk.Button(tb, text=lbl, command=cmd, **BCF).pack(
                side='left', padx=3, pady=6)

        # Font size buttons
        sep = tk.Label(tb, text='│', bg='#3a3a3a', fg='#666', font=('Times New Roman',14))
        sep.pack(side='left', padx=4)

        tk.Label(tb, text='Font:', bg='#3a3a3a', fg='#bbbbbb',
                 font=('Times New Roman',9)).pack(side='left')

        self._fs_var = tk.IntVar(value=11)
        for sz in [8, 9, 10, 11, 12, 14, 16]:
            tk.Button(tb, text=str(sz), width=3,
                      bg='#555' if sz != 11 else '#1a4da8',
                      fg='white', font=('Times New Roman',8,'bold'),
                      relief='flat', padx=2, pady=5,
                      activebackground='#1a4da8', activeforeground='white',
                      cursor='hand2',
                      command=lambda s=sz: self._set_font_size(s)
                      ).pack(side='left', padx=1, pady=6)

        # Style selector
        sep2 = tk.Label(tb, text='│', bg='#3a3a3a', fg='#666', font=('Times New Roman',14))
        sep2.pack(side='left', padx=4)
        tk.Label(tb, text='Style:', bg='#3a3a3a', fg='#bbbbbb',
                 font=('Times New Roman',9)).pack(side='left')
        self._style_cb = ttk.Combobox(tb, values=list(SOLFA_STYLES.keys()),
                                       state='readonly', width=12,
                                       font=('Times New Roman',9))
        self._style_cb.set(self._score.solfa_style)
        self._style_cb.pack(side='left', padx=4, pady=6)
        self._style_cb.bind('<<ComboboxSelected>>',
                             lambda e: self._set_style(self._style_cb.get()))

    # ── Resize / Layout Bar ───────────────────────────────────────────────────

    def _build_resize_bar(self):
        rb = tk.Frame(self, bg='#333333', height=36)
        rb.pack(side='top', fill='x')
        rb.pack_propagate(False)

        TNR = 'Times New Roman'
        LCF = dict(bg='#333333', fg='#aaaaaa', font=(TNR, 8))

        # Measures per row
        tk.Label(rb, text='Measures/Row:', **LCF).pack(side='left', padx=(8,2), pady=8)
        self._mpr_var = tk.IntVar(value=4)
        mpr_sb = tk.Spinbox(rb, from_=1, to=8, textvariable=self._mpr_var,
                             width=3, font=(TNR, 9),
                             command=lambda: self._apply_layout())
        mpr_sb.pack(side='left', padx=2, pady=6)

        # Row height
        tk.Label(rb, text='  Row Height:', **LCF).pack(side='left', padx=(10,2))
        self._rh_var = tk.IntVar(value=88)
        rh_sb = tk.Spinbox(rb, from_=50, to=160, textvariable=self._rh_var,
                            width=4, font=(TNR,9),
                            command=lambda: self._apply_layout())
        rh_sb.pack(side='left', padx=2)

        # Measure width
        tk.Label(rb, text='  Meas Width:', **LCF).pack(side='left', padx=(10,2))
        self._mw_var = tk.IntVar(value=160)
        mw_sb = tk.Spinbox(rb, from_=80, to=400, textvariable=self._mw_var,
                            width=4, font=(TNR,9),
                            command=lambda: self._apply_layout())
        mw_sb.pack(side='left', padx=2)

        # PDF Measures/Row
        tk.Label(rb, text='  PDF Meas/Row:', **LCF).pack(side='left', padx=(10,2))
        self._pdf_mpr = tk.IntVar(value=4)
        tk.Spinbox(rb, from_=1, to=8, textvariable=self._pdf_mpr,
                   width=3, font=(TNR,9)).pack(side='left', padx=2)

        # PDF Font size
        tk.Label(rb, text='  PDF Font:', **LCF).pack(side='left', padx=(10,2))
        self._pdf_fs = tk.DoubleVar(value=9.0)
        tk.Spinbox(rb, from_=6.0, to=14.0, increment=0.5,
                   textvariable=self._pdf_fs,
                   width=4, font=(TNR,9)).pack(side='left', padx=2)

        # Apply button
        tk.Button(rb, text='Apply Layout', bg='#1a4da8', fg='white',
                  font=(TNR, 8, 'bold'), relief='flat', padx=8, pady=3,
                  activebackground='#2266cc',
                  command=self._apply_layout).pack(side='left', padx=10, pady=6)

        # Auto-layout toggle
        self._auto_layout = tk.BooleanVar(value=True)
        tk.Checkbutton(rb, text='Auto layout', variable=self._auto_layout,
                       bg='#333333', fg='#aaaaaa',
                       font=(TNR,8), selectcolor='#444'
                       ).pack(side='left', padx=6)

    # ── Main paned area ───────────────────────────────────────────────────────

    def _build_main(self):
        paned = tk.PanedWindow(self, orient='horizontal', bg='#2b2b2b',
                               sashwidth=5, sashrelief='flat')
        paned.pack(fill='both', expand=True)

        # Left: canvas
        left = tk.Frame(paned, bg='#1e1e1e')
        paned.add(left, minsize=640)

        tk.Label(left, text='SCORE CANVAS  (click to select · double-click to edit)',
                 bg='#1e1e1e', fg='#aaaaaa',
                 font=('Times New Roman', 9, 'bold')).pack(anchor='w', padx=8, pady=(4,0))

        hbar = tk.Scrollbar(left, orient='horizontal')
        vbar = tk.Scrollbar(left, orient='vertical')
        hbar.pack(side='bottom', fill='x')
        vbar.pack(side='right',  fill='y')

        self._canvas = SolfaCanvas(left, self._score,
                                   xscrollcommand=hbar.set,
                                   yscrollcommand=vbar.set)
        self._canvas.pack(fill='both', expand=True, padx=2, pady=2)
        hbar.config(command=self._canvas.xview)
        vbar.config(command=self._canvas.yview)

        # Right: live text view
        right = tk.Frame(paned, bg='#1e1e1e')
        paned.add(right, minsize=260)

        tk.Label(right, text='LIVE TEXT VIEW',
                 bg='#1e1e1e', fg='#aaaaaa',
                 font=('Times New Roman', 9, 'bold')).pack(anchor='w', padx=8, pady=(4,0))

        self._live = tk.Text(right, font=('Times New Roman', 10),
                             bg='#0d0d0d', fg='#e8e8e8',
                             insertbackground='white',
                             relief='flat', padx=8, pady=8,
                             state='disabled', wrap='none')
        rs = tk.Scrollbar(right, command=self._live.yview)
        self._live.configure(yscrollcommand=rs.set)
        rs.pack(side='right', fill='y')
        self._live.pack(fill='both', expand=True, padx=4, pady=4)

        self._canvas.bind('<ButtonRelease-1>', lambda e: self._update_live())
        self._canvas.bind('<KeyRelease>',      lambda e: self._update_live())

    def _build_status(self):
        self._status_var = tk.StringVar(value='Ready  –  Import MusicXML or edit manually.')
        bar = tk.Label(self, textvariable=self._status_var,
                       bg='#1a1a1a', fg='#888888',
                       font=('Times New Roman', 8), anchor='w', padx=8)
        bar.pack(side='bottom', fill='x')

    # ── Live text view ────────────────────────────────────────────────────────

    def _update_live(self):
        txt = self._score_to_text()
        self._live.configure(state='normal')
        self._live.delete('1.0', 'end')
        self._live.insert('end', txt)
        self._live.configure(state='disabled')

    def _score_to_text(self) -> str:
        s   = self._score
        out = [s.title.upper(),
               f'Doh is {s.doh_key}   Time: {s.time_num}/{s.time_den}']
        if s.composer:    out.append(f'By: {s.composer}')
        if s.tempo_text:  out.append(s.tempo_text)
        out.append('')
        npart = max(1, len(s.parts))
        mpr   = self._canvas.MEAS_PER_ROW if hasattr(self,'_canvas') else 4
        for rs in range(0, len(s.measures), mpr):
            row = s.measures[rs:rs+mpr]
            for p_idx in range(npart):
                init = s.parts[p_idx][0] if p_idx < len(s.parts) else ' '
                line = f'{init} |'
                for meas in row:
                    notes = [n for n in meas.notes if n.part_idx == p_idx]
                    cell_parts = []
                    for n in notes:
                        syl = _display_syllable(s, n)
                        bmv = _display_beat_marker(s, n)
                        bm  = (' ' + bmv) if bmv else ''
                        cell_parts.append(syl + bm)
                    cell = '  '.join(cell_parts) or '- :-'
                    line += f' {cell:<28}|'
                out.append(line)
            out.append('')
        return '\n'.join(out)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _new_score(self):
        self._score = SolfaScore()
        self._canvas.load_score(self._score)
        self._update_live()
        self._status('New score created.')

    def _import_xml(self):
        path = filedialog.askopenfilename(
            title='Import MusicXML',
            filetypes=[('MusicXML', '*.xml *.musicxml *.mxl'), ('All', '*.*')])
        if not path: return
        try:
            style = self._score.solfa_style
            self._score = parse_musicxml(path, style)
            self._canvas.load_score(self._score)
            self._style_cb.set(self._score.solfa_style)
            self._update_live()
            self._status(f'Loaded: {os.path.basename(path)}  '
                         f'| {len(self._score.measures)} measures '
                         f'| {len(self._score.parts)} parts')
        except Exception as exc:
            messagebox.showerror('Import Error', str(exc))

    def _export_pdf(self):
        if not HAS_REPORTLAB:
            messagebox.showwarning('reportlab missing',
                'Install reportlab:\n\n  pip install reportlab\n\nThen restart.')
            return
        path = filedialog.asksaveasfilename(
            defaultextension='.pdf',
            filetypes=[('PDF files', '*.pdf')],
            initialfile=self._score.title or 'score')
        if not path: return
        try:
            render_pdf(
                self._score, path,
                measures_per_row=getattr(self._canvas, 'MEAS_PER_ROW', self._pdf_mpr.get()),
                font_size=float(getattr(self._canvas, 'FONT_SIZE', self._pdf_fs.get())),
                row_height=int(getattr(self._canvas, 'ROW_HEIGHT', 96))
            )
            self._status(f'PDF exported: {path}')
            messagebox.showinfo('Export complete', f'Saved:\n{path}')
        except Exception as exc:
            messagebox.showerror('Export Error', str(exc))

    def _edit_note(self):
        if hasattr(self, '_canvas'):
            self._canvas._edit_selected()
            self._update_live()

    def _add_note(self):
        if hasattr(self, '_canvas'):
            self._canvas.add_note_to_selected_measure()
            self._update_live()

    def _del_note(self):
        if hasattr(self, '_canvas'):
            self._canvas._delete_selected()
            self._update_live()

    def _add_measure(self):
        if hasattr(self, '_canvas'):
            self._canvas.add_measure()
            self._update_live()
            self._status(f'Measure {len(self._score.measures)} added.')

    def _auto_fit(self):
        if hasattr(self, '_canvas'):
            self._canvas.auto_fit_notes()
            self._update_live()
            self._status('Notes auto-fitted to beats.')

    def _refresh(self):
        self._canvas.redraw()
        self._update_live()

    def _score_props(self):
        dlg = ScorePropsDialog(self, self._score)
        self.wait_window(dlg)
        if dlg.changed:
            self._canvas.load_score(self._score)
            self._update_live()

    def _set_font_size(self, sz: int):
        if hasattr(self, '_canvas'):
            self._canvas.set_font_size(sz)
        self._status(f'Canvas font size: {sz}pt')

    def _set_style(self, style: str):
        self._score.solfa_style = style
        if hasattr(self, '_style_cb'):
            self._style_cb.set(style)
        self._status(f'Solfa style: {style}')
        if hasattr(self, '_canvas'):
            self._canvas.redraw()

    def _zoom(self, delta: int):
        if hasattr(self, '_canvas'):
            new_sz = max(7, min(22, self._canvas.FONT_SIZE + delta))
            self._canvas.set_font_size(new_sz)

    def _apply_layout(self):
        if not hasattr(self, '_canvas'): return
        self._canvas.set_meas_per_row(self._mpr_var.get())
        self._canvas.set_row_height(self._rh_var.get())
        self._canvas.set_meas_width(self._mw_var.get())
        self._update_live()
        self._status('Layout applied.')

    def _status(self, msg: str):
        self._status_var.set(msg)


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    app = SolfaApp()
    app.mainloop()

if __name__ == '__main__':
    main()
