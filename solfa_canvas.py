"""
Tonic Solfa Notation Canvas
A professional tonic solfa notation software with MusicXML import,
editable canvas, and PDF export.
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

# ── PDF export ──────────────────────────────────────────────────────────────
try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors as rl_colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

# ── MusicXML pitch → solfa ────────────────────────────────────────────────
CHROMATIC = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
SOLFA_STEPS = ['d','r','m','f','s','l','t']
MAJOR_SCALE  = [0,2,4,5,7,9,11]

def pitch_to_solfa(step: str, alter: int, octave: int, key_semitone: int) -> str:
    """Return solfa syllable with octave markers.
    Middle (home) octave = 4. Above → prime ('), below → subscript₁"""
    semitone = (CHROMATIC[step] + int(alter or 0)) % 12
    rel = (semitone - key_semitone) % 12
    try:
        idx = MAJOR_SCALE.index(rel)
    except ValueError:
        # Chromatic – find nearest
        idx = min(range(7), key=lambda i: abs(MAJOR_SCALE[i]-rel))
    name = SOLFA_STEPS[idx]
    # octave decoration
    home_oct = 4
    oct_diff = int(octave) - home_oct
    if oct_diff > 0:
        name = name + "'" * oct_diff
    elif oct_diff < 0:
        name = name + "₁" * abs(oct_diff)
    return name

def duration_to_beat_marker(d: float) -> str:
    if d >= 4.0: return ':-:-:-'
    if d >= 3.0: return ':-:-'
    if d >= 2.0: return ':-'
    if d >= 1.5: return ':-.,'
    if d >= 1.0: return ':'
    if d >= 0.75: return '.,'
    if d >= 0.5:  return '.'
    if d >= 0.25: return ','
    return ':'

KEY_NAMES = {0:'C',2:'D',4:'E',5:'F',7:'G',9:'A',11:'B',
             1:'C#',3:'D#',6:'F#',8:'G#',10:'A#'}
FLAT_NAMES = {10:'Bb',8:'Ab',3:'Eb',1:'Db',6:'Gb'}

def semitone_to_key_name(s: int, mode: str = 'major') -> str:
    name = KEY_NAMES.get(s, FLAT_NAMES.get(s, f'K{s}'))
    if mode == 'minor': name += 'm'
    return name


# ── Data Model ───────────────────────────────────────────────────────────────

@dataclass
class SolfaNote:
    syllable: str        # e.g. 'd', 'm'', 's₁'
    beat_marker: str     # e.g. ':', ':-', '.'
    is_rest: bool = False
    lyric: str = ''
    part_idx: int = 0    # voice/part index (0=soprano, etc.)

@dataclass
class SolfaMeasure:
    number: int
    notes: List[SolfaNote] = field(default_factory=list)
    time_sig_num: int = 4
    time_sig_den: int = 4

@dataclass
class SolfaScore:
    title: str = 'Untitled'
    doh_key: str = 'C'
    time_num: int = 4
    time_den: int = 4
    tempo_text: str = ''
    composer: str = ''
    dedication: str = ''
    parts: List[str] = field(default_factory=lambda: ['Soprano','Alto','Tenor','Bass'])
    measures: List[SolfaMeasure] = field(default_factory=list)


# ── MusicXML Parser ──────────────────────────────────────────────────────────

def parse_musicxml(path: str) -> SolfaScore:
    tree = ET.parse(path)
    root = tree.getroot()
    ns = ''
    if root.tag.startswith('{'):
        ns = root.tag.split('}')[0] + '}'

    def tag(t): return f'{ns}{t}'

    score = SolfaScore()

    # Title
    work = root.find(tag('work'))
    if work is not None:
        wt = work.find(tag('work-title'))
        if wt is not None and wt.text: score.title = wt.text.strip()

    mv = root.find(tag('movement-title'))
    if mv is not None and mv.text: score.title = mv.text.strip()

    # Composer / Dedication
    id_el = root.find(tag('identification'))
    if id_el is not None:
        for c in id_el.findall(tag('creator')):
            if c.get('type') == 'composer' and c.text:
                score.composer = c.text.strip()
        for r in id_el.findall(tag('rights')):
            if r.text: score.dedication = r.text.strip()

    # Key signature (from first measure of first part)
    key_semitone = 0
    mode = 'major'
    parts_el = root.findall(f'.//{tag("part")}')
    parts_names = []
    for pn in root.findall(f'.//{tag("score-part")}'):
        nm = pn.find(tag('part-name'))
        parts_names.append(nm.text.strip() if nm is not None and nm.text else 'Part')
    if parts_names: score.parts = parts_names

    measure_dict: Dict[int, SolfaMeasure] = {}

    for p_idx, part_el in enumerate(parts_el):
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
                        fifths = int(fifths_el.text or 0)
                        # Circle of fifths → semitone
                        key_semitone = (fifths * 7) % 12
                    if mode_el is not None and mode_el.text:
                        mode = mode_el.text.strip()
                t = attr.find(tag('time'))
                if t is not None:
                    b = t.find(tag('beats'))
                    bt = t.find(tag('beat-type'))
                    if b is not None and bt is not None:
                        score.time_num = int(b.text or 4)
                        score.time_den = int(bt.text or 4)
                        meas.time_sig_num = score.time_num
                        meas.time_sig_den = score.time_den

            divisions = 1
            attr2 = meas_el.find(tag('attributes'))
            if attr2 is not None:
                d_el = attr2.find(tag('divisions'))
                if d_el is not None: divisions = int(d_el.text or 1)

            # Notes
            for note_el in meas_el.findall(tag('note')):
                is_rest = note_el.find(tag('rest')) is not None
                dur_el  = note_el.find(tag('duration'))
                dur_val = float(dur_el.text) / divisions if dur_el is not None else 1.0

                bm = duration_to_beat_marker(dur_val)

                if is_rest:
                    lyric = ''
                    lyr_el = note_el.find(tag('lyric'))
                    if lyr_el is not None:
                        tx = lyr_el.find(tag('text'))
                        if tx is not None and tx.text: lyric = tx.text
                    meas.notes.append(SolfaNote('-', bm, True, lyric, p_idx))
                else:
                    pitch_el = note_el.find(tag('pitch'))
                    if pitch_el is None: continue
                    step_el  = pitch_el.find(tag('step'))
                    alt_el   = pitch_el.find(tag('alter'))
                    oct_el   = pitch_el.find(tag('octave'))
                    step   = step_el.text if step_el is not None else 'C'
                    alter  = int(float(alt_el.text)) if alt_el is not None and alt_el.text else 0
                    octave = int(oct_el.text) if oct_el is not None else 4
                    syllable = pitch_to_solfa(step, alter, octave, key_semitone)
                    lyric = ''
                    lyr_el = note_el.find(tag('lyric'))
                    if lyr_el is not None:
                        tx = lyr_el.find(tag('text'))
                        if tx is not None and tx.text: lyric = tx.text
                    meas.notes.append(SolfaNote(syllable, bm, False, lyric, p_idx))

    score.doh_key = semitone_to_key_name(key_semitone, mode)
    score.measures = [measure_dict[k] for k in sorted(measure_dict)]
    return score


# ── Canvas Renderer ──────────────────────────────────────────────────────────

class SolfaCanvas(tk.Canvas):
    """Interactive Tonic Solfa notation canvas."""

    MARGIN_X     = 60
    MARGIN_TOP   = 110
    ROW_HEIGHT   = 80     # per part row
    SYSTEM_GAP   = 28
    MEAS_PER_ROW = 4
    MEAS_MIN_W   = 160

    FONT_TITLE   = ('Georgia', 14, 'bold')
    FONT_DEDIC   = ('Georgia', 9, 'italic')
    FONT_DOH     = ('Courier', 11, 'bold')
    FONT_TEMPO   = ('Courier', 10, 'italic')
    FONT_MNUM    = ('Courier', 8)
    FONT_NOTE    = ('Courier', 11)
    FONT_BRACE   = ('Courier', 26)
    FONT_LYRIC   = ('Courier', 9, 'italic')

    BG   = '#FFFFF8'
    INK  = '#1a1a1a'
    SEL  = '#2266cc'
    GRID = '#cccccc'

    def __init__(self, master, score: SolfaScore, **kw):
        super().__init__(master, bg=self.BG, **kw)
        self.score    = score
        self.selected : Optional[Tuple[int,int,int]] = None  # (meas_idx, note_idx, part_idx)
        self._items   : Dict = {}   # canvas_id → (meas_idx, note_idx, part_idx)
        self._note_rects = {}       # (meas_idx, note_idx, part_idx) → canvas_id list
        self.bind('<Configure>', lambda e: self.redraw())
        self.bind('<Button-1>', self._on_click)
        self.bind('<Double-Button-1>', self._on_dbl_click)
        self.bind('<Key>', self._on_key)
        self.bind('<Delete>', self._delete_selected)
        self.configure(highlightthickness=0)
        self.redraw()

    # ── layout helpers ──────────────────────────────────────────────────────

    def _canvas_width(self):
        return max(self.winfo_width(), 800)

    def _measures_per_row(self):
        avail = self._canvas_width() - 2 * self.MARGIN_X - 30
        n = max(1, int(avail / self.MEAS_MIN_W))
        return min(n, 6)

    def _measure_width(self):
        avail = self._canvas_width() - 2 * self.MARGIN_X - 30
        mpr   = self._measures_per_row()
        return avail / mpr

    # ── drawing ─────────────────────────────────────────────────────────────

    def redraw(self):
        self.delete('all')
        self._items.clear()
        self._note_rects.clear()
        self._draw_header()
        self._draw_measures()
        self._update_scrollregion()

    def _draw_header(self):
        cx = self._canvas_width() / 2
        # Title
        self.create_text(cx, 28, text=self.score.title.upper(),
                         font=self.FONT_TITLE, fill=self.INK, anchor='center',
                         tags='header')
        # Underline
        tw = len(self.score.title) * 9
        self.create_line(cx - tw, 36, cx + tw, 36, fill=self.INK, width=1, tags='header')
        # Dedication
        if self.score.dedication:
            self.create_text(cx, 52, text=f'({self.score.dedication})',
                             font=self.FONT_DEDIC, fill=self.INK, anchor='center', tags='header')
        # Doh / Time
        self.create_text(self.MARGIN_X, 72,
                         text=f'Doh is {self.score.doh_key}    Time: {self.score.time_num}/{self.score.time_den}',
                         font=self.FONT_DOH, fill=self.INK, anchor='w', tags='header')
        # Composer / date
        if self.score.composer:
            self.create_text(self._canvas_width() - self.MARGIN_X, 72,
                             text=f'By: {self.score.composer}',
                             font=self.FONT_DOH, fill=self.INK, anchor='e', tags='header')
        # Tempo
        if self.score.tempo_text:
            self.create_text(self.MARGIN_X, 90,
                             text=self.score.tempo_text,
                             font=self.FONT_TEMPO, fill=self.INK, anchor='w', tags='header')

    def _draw_measures(self):
        if not self.score.measures: return
        mpr    = self._measures_per_row()
        mw     = self._measure_width()
        nparts = max(1, len(self.score.parts))
        sys_h  = nparts * self.ROW_HEIGHT + self.SYSTEM_GAP

        for idx, meas in enumerate(self.score.measures):
            row = idx // mpr
            col = idx  % mpr
            x0  = self.MARGIN_X + 30 + col * mw
            y0  = self.MARGIN_TOP + row * sys_h

            # System brace on first column
            if col == 0:
                bh = nparts * self.ROW_HEIGHT
                self.create_text(self.MARGIN_X + 14, y0 + bh / 2,
                                 text='{', font=self.FONT_BRACE,
                                 fill=self.INK, anchor='center')
                # Left double bar
                self.create_line(self.MARGIN_X + 28, y0,
                                 self.MARGIN_X + 28, y0 + bh,
                                 fill=self.INK, width=2)

            # Measure number
            self.create_text(x0 + 4, y0 - 2, text=str(meas.number),
                             font=self.FONT_MNUM, fill='#666', anchor='sw')

            # Draw each part row
            for p_idx, pname in enumerate(self.score.parts):
                py = y0 + p_idx * self.ROW_HEIGHT
                self._draw_part_row(meas, idx, p_idx, x0, py, mw)

            # Right barline
            bh = nparts * self.ROW_HEIGHT
            lw = 2 if (idx + 1) % mpr == 0 or idx == len(self.score.measures)-1 else 1
            self.create_line(x0 + mw, y0, x0 + mw, y0 + bh,
                             fill=self.INK, width=lw)

    def _draw_part_row(self, meas: SolfaMeasure, meas_idx: int,
                       p_idx: int, x0: float, y0: float, mw: float):
        """Draw one voice row inside a measure."""
        notes = [n for n in meas.notes if n.part_idx == p_idx]

        # Row baseline
        base_y = y0 + self.ROW_HEIGHT * 0.45
        lyric_y = y0 + self.ROW_HEIGHT * 0.72

        # Part label on first measure column
        col = (meas_idx) % self._measures_per_row()
        if col == 0:
            self.create_text(self.MARGIN_X + 30, base_y,
                             text=self.score.parts[p_idx][0] if self.score.parts[p_idx] else '',
                             font=('Courier', 9, 'italic'), fill='#888', anchor='e')

        if not notes:
            self.create_text(x0 + mw/2, base_y, text='- :-',
                             font=self.FONT_NOTE, fill='#aaa', anchor='w')
            return

        # Lay notes evenly
        slot_w = mw / max(len(notes), 1)
        for n_idx, note in enumerate(notes):
            nx = x0 + n_idx * slot_w + 4
            # Build display string
            syl  = note.syllable
            bm   = note.beat_marker
            txt  = f'{syl}{bm}' if not note.is_rest else f'-{bm}'

            key  = (meas_idx, n_idx, p_idx)
            is_sel = (key == self.selected)
            clr  = self.SEL if is_sel else self.INK

            # Highlight rect
            rect_id = self.create_rectangle(
                nx - 2, y0 + 4, nx + slot_w - 2, y0 + self.ROW_HEIGHT - 4,
                outline=self.SEL if is_sel else '', fill='#ddeeff' if is_sel else '',
                tags=f'note_{meas_idx}_{n_idx}_{p_idx}')

            # Note text
            tid = self.create_text(nx, base_y, text=txt,
                                   font=self.FONT_NOTE, fill=clr, anchor='w',
                                   tags=f'note_{meas_idx}_{n_idx}_{p_idx}')
            # Lyric
            if note.lyric:
                self.create_text(nx, lyric_y, text=note.lyric,
                                 font=self.FONT_LYRIC, fill='#444', anchor='w',
                                 tags=f'note_{meas_idx}_{n_idx}_{p_idx}')

            for cid in [rect_id, tid]:
                self._items[cid]        = key
                self._note_rects[key]   = self._note_rects.get(key, []) + [cid]

    # ── interaction ─────────────────────────────────────────────────────────

    def _on_click(self, event):
        self.focus_set()
        items = self.find_overlapping(event.x-2, event.y-2, event.x+2, event.y+2)
        for item in reversed(items):
            key = self._items.get(item)
            if key:
                self.selected = key
                self.redraw()
                return
        self.selected = None
        self.redraw()

    def _on_dbl_click(self, event):
        items = self.find_overlapping(event.x-2, event.y-2, event.x+2, event.y+2)
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
        meas  = self.score.measures[mi]
        notes = [n for n in meas.notes if n.part_idx == pi]
        if ni >= len(notes): return
        note  = notes[ni]

        dlg = NoteEditDialog(self, note, title='Edit Note')
        self.wait_window(dlg)
        if dlg.result:
            note.syllable     = dlg.result['syllable']
            note.beat_marker  = dlg.result['beat_marker']
            note.lyric        = dlg.result['lyric']
            note.is_rest      = dlg.result['is_rest']
            self.redraw()

    def _delete_selected(self, event=None):
        if self.selected is None: return
        mi, ni, pi = self.selected
        meas  = self.score.measures[mi]
        part_notes = [(i, n) for i, n in enumerate(meas.notes) if n.part_idx == pi]
        if ni < len(part_notes):
            real_idx = part_notes[ni][0]
            del meas.notes[real_idx]
        self.selected = None
        self.redraw()

    def add_note_to_selected_measure(self):
        if not self.score.measures: return
        mi = self.selected[0] if self.selected else len(self.score.measures) - 1
        pi = self.selected[2] if self.selected else 0
        blank = SolfaNote('d', ':', False, '', pi)
        dlg = NoteEditDialog(self, blank, title='Add Note')
        self.wait_window(dlg)
        if dlg.result:
            blank.syllable    = dlg.result['syllable']
            blank.beat_marker = dlg.result['beat_marker']
            blank.lyric       = dlg.result['lyric']
            blank.is_rest     = dlg.result['is_rest']
            self.score.measures[mi].notes.append(blank)
            self.redraw()

    def _update_scrollregion(self):
        self.update_idletasks()
        bbox = self.bbox('all')
        if bbox:
            self.configure(scrollregion=(bbox[0]-10, bbox[1]-10,
                                         bbox[2]+10, bbox[3]+30))

    # ── public API ──────────────────────────────────────────────────────────

    def load_score(self, score: SolfaScore):
        self.score    = score
        self.selected = None
        self.redraw()

    def export_pdf(self, path: str):
        if not HAS_REPORTLAB:
            messagebox.showerror('Missing library',
                'reportlab is required for PDF export.\n'
                'Install with:  pip install reportlab')
            return
        _render_pdf(self.score, path)
        messagebox.showinfo('Export', f'PDF saved to:\n{path}')


# ── Note Edit Dialog ─────────────────────────────────────────────────────────

class NoteEditDialog(tk.Toplevel):
    BEAT_OPTIONS = [':', ':-', ':-:-', ':-:-:-', ':-:.', '.', ',', '.,']

    def __init__(self, parent, note: SolfaNote, title='Edit Note'):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.result = None
        self._build(note)
        self.grab_set()
        self.transient(parent)
        self.geometry('+%d+%d' % (parent.winfo_rootx()+200,
                                   parent.winfo_rooty()+200))

    def _build(self, note: SolfaNote):
        pad = dict(padx=10, pady=6)

        tk.Label(self, text='Syllable / Rest symbol:', font=('Courier',10)).grid(row=0,column=0,sticky='w',**pad)
        self._syl = tk.Entry(self, font=('Courier',12), width=10)
        self._syl.insert(0, note.syllable if not note.is_rest else '-')
        self._syl.grid(row=0, column=1, **pad)

        tk.Label(self, text='Beat marker:', font=('Courier',10)).grid(row=1,column=0,sticky='w',**pad)
        self._bm = ttk.Combobox(self, values=self.BEAT_OPTIONS, width=12,
                                font=('Courier',11))
        self._bm.set(note.beat_marker)
        self._bm.grid(row=1, column=1, **pad)

        tk.Label(self, text='Lyric:', font=('Courier',10)).grid(row=2,column=0,sticky='w',**pad)
        self._lyric = tk.Entry(self, font=('Courier',10), width=16)
        self._lyric.insert(0, note.lyric)
        self._lyric.grid(row=2, column=1, **pad)

        self._is_rest = tk.BooleanVar(value=note.is_rest)
        tk.Checkbutton(self, text='Rest', variable=self._is_rest,
                       font=('Courier',10)).grid(row=3,column=0,columnspan=2,**pad)

        # Octave helper buttons
        frm = tk.Frame(self)
        frm.grid(row=4, column=0, columnspan=2, pady=4)
        tk.Label(frm, text="Octave:", font=('Courier',9)).pack(side='left')
        for lbl, sfx in [("Normal",""), ("Upper '","'"), ("Lower ₁","₁")]:
            tk.Button(frm, text=lbl, font=('Courier',8),
                      command=lambda s=sfx: self._apply_octave(s)).pack(side='left', padx=3)

        bf = tk.Frame(self)
        bf.grid(row=5, column=0, columnspan=2, pady=8)
        tk.Button(bf, text='OK', width=8, command=self._ok,
                  bg='#2266cc', fg='white', font=('Courier',10,'bold')).pack(side='left', padx=6)
        tk.Button(bf, text='Cancel', width=8, command=self.destroy,
                  font=('Courier',10)).pack(side='left')

        self._syl.focus_set()
        self.bind('<Return>', lambda e: self._ok())
        self.bind('<Escape>', lambda e: self.destroy())

    def _apply_octave(self, suffix):
        cur = self._syl.get()
        # Strip existing markers
        base = cur.rstrip("'₁")
        self._syl.delete(0, 'end')
        self._syl.insert(0, base + suffix)

    def _ok(self):
        syl = self._syl.get().strip() or 'd'
        bm  = self._bm.get().strip()  or ':'
        self.result = dict(syllable=syl, beat_marker=bm,
                           lyric=self._lyric.get(),
                           is_rest=self._is_rest.get())
        self.destroy()


# ── PDF renderer ─────────────────────────────────────────────────────────────

def _render_pdf(score: SolfaScore, path: str):
    """
    Professional engraver-quality PDF — matches hymn-book reference sheets.
    """
    if not HAS_REPORTLAB:
        messagebox.showerror('Missing library', 'pip install reportlab')
        return

    def pdf_safe_text(txt: str) -> str:
        repl = {
            '₁': '1', '₂': '2', '₃': '3', '₄': '4',
            '¹': "'", '²': "'", '³': "'", '⁴': "''",
        }
        for key, val in repl.items():
            txt = txt.replace(key, val)
        return txt

    C_INK    = rl_colors.HexColor('#140e04')
    C_HEAD   = rl_colors.HexColor('#3a0000')
    C_BARNUM = rl_colors.HexColor('#5a4030')
    C_LYRIC  = rl_colors.HexColor('#1a3060')
    C_LINE   = rl_colors.HexColor('#9a8060')
    C_BAR    = rl_colors.HexColor('#2a1800')

    W, H = A4
    MARGIN = 15 * mm
    c = rl_canvas.Canvas(path, pagesize=A4)

    def new_page():
        c.showPage()
        c.setFont('Times-Bold', 11)
        c.setFillColor(C_HEAD)
        c.drawCentredString(W / 2, H - 12 * mm, score.title.upper())
        c.setLineWidth(0.4)
        c.setStrokeColor(C_LINE)
        c.line(MARGIN, H - 14 * mm, W - MARGIN, H - 14 * mm)
        return H - 20 * mm

    y = H - 16 * mm
    c.setFont('Times-Bold', 16)
    c.setFillColor(C_HEAD)
    c.drawCentredString(W / 2, y, score.title.upper())
    title_w = len(score.title) * 7.5
    c.setLineWidth(0.6)
    c.setStrokeColor(C_INK)
    c.line(W/2 - title_w, y - 1*mm, W/2 + title_w, y - 1*mm)
    y -= 6 * mm

    if score.dedication:
        c.setFont('Times-Italic', 9)
        c.setFillColor(C_INK)
        c.drawCentredString(W / 2, y, f'({score.dedication})')
        y -= 5 * mm

    c.setFont('Times-Bold', 10)
    c.setFillColor(C_INK)
    c.drawString(MARGIN, y, f'Doh is {score.doh_key}    Time: {score.time_num}/{score.time_den}')
    if score.composer:
        c.drawRightString(W - MARGIN, y, f'By: {score.composer}')
    y -= 5 * mm

    if score.tempo_text:
        c.setFont('Times-Italic', 9)
        c.drawString(MARGIN, y, score.tempo_text)
        y -= 4 * mm

    c.setLineWidth(0.6)
    c.setStrokeColor(C_LINE)
    c.line(MARGIN, y, W - MARGIN, y)
    y -= 6 * mm

    nparts = max(1, len(score.parts))
    mpr = 4
    voice_h = 11 * mm
    sys_gap = 6 * mm
    brace_x = MARGIN + 2 * mm
    label_w = 8 * mm
    music_x = brace_x + label_w + 2 * mm
    col_w = (W - music_x - MARGIN) / mpr

    for row_start in range(0, len(score.measures), mpr):
        row = score.measures[row_start: row_start + mpr]
        sys_h = nparts * voice_h

        if y - sys_h - sys_gap < MARGIN + 10 * mm:
            y = new_page()

        c.setStrokeColor(C_BAR)
        c.setLineWidth(1.5)
        c.line(brace_x, y, brace_x, y - sys_h)
        c.setLineWidth(0.8)
        c.line(brace_x, y, brace_x + 2*mm, y)
        c.line(brace_x, y-sys_h, brace_x + 2*mm, y-sys_h)

        c.setStrokeColor(C_LINE)
        c.setLineWidth(0.5)
        c.line(music_x, y, W - MARGIN, y)

        for p_idx, pname in enumerate(score.parts):
            py = y - p_idx * voice_h
            py_mid = py - voice_h / 2

            c.setFont('Times-BoldItalic', 8)
            c.setFillColor(C_BAR)
            c.drawRightString(music_x - 1*mm, py_mid + 2, pname[0])

            c.setStrokeColor(C_LINE)
            c.setLineWidth(0.4)
            c.line(music_x, py - voice_h, W - MARGIN, py - voice_h)

            c.setStrokeColor(C_BAR)
            c.setLineWidth(0.8)
            c.line(music_x, py, music_x, py - voice_h)

            for mi, meas in enumerate(row):
                mx = music_x + mi * col_w

                if p_idx == 0:
                    c.setFont('Times-Roman', 6)
                    c.setFillColor(C_BARNUM)
                    c.drawString(mx + 0.5*mm, py + 0.8*mm, str(meas.number))

                notes = [n for n in meas.notes if n.part_idx == p_idx]
                if notes:
                    slot_w = col_w / max(len(notes), 1)
                    for ni, note in enumerate(notes):
                        nx = mx + ni * slot_w + 0.5*mm
                        txt = (note.syllable if not note.is_rest else '-') + note.beat_marker
                        txt = pdf_safe_text(txt)
                        c.setFont('Courier-Bold', 9)
                        c.setFillColor(C_INK)
                        c.drawString(nx, py_mid, txt)
                        if note.lyric:
                            c.setFont('Times-Italic', 7)
                            c.setFillColor(C_LYRIC)
                            c.drawString(nx, py_mid - 3.5*mm, note.lyric)
                else:
                    c.setFont('Times-Roman', 9)
                    c.setFillColor(C_LINE)
                    c.drawCentredString(mx + col_w/2, py_mid, '-:-')

                lw = 1.2 if (mi == len(row)-1 or row_start + mi + 1 == len(score.measures)) else 0.5
                c.setStrokeColor(C_BAR)
                c.setLineWidth(lw)
                c.line(mx + col_w, py, mx + col_w, py - voice_h)

        y -= sys_h + sys_gap

    if y > MARGIN + 8*mm:
        c.setFont('Times-Roman', 6.5)
        c.setFillColor(C_LINE)
        c.drawString(MARGIN, MARGIN + 4*mm,
                     "d=Do  r=Re  m=Mi  f=Fa  s=Sol  l=La  t=Ti  ' =upper octave  1=lower octave  -=rest  :-=half  :-:-=whole")

    c.setFont('Times-Roman', 8)
    c.setFillColor(C_BARNUM)
    c.drawCentredString(W / 2, MARGIN, '1')

    c.save()


# ── Main Application ──────────────────────────────────────────────────────────

class SolfaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Tonic Solfa Notation Software')
        self.geometry('1200x750')
        self.configure(bg='#2b2b2b')
        self._score = SolfaScore()
        self._build_ui()

    def _build_ui(self):
        self._build_menu()
        self._build_toolbar()
        self._build_main()
        self._build_status()

    def _build_menu(self):
        mb = tk.Menu(self, bg='#3c3c3c', fg='white', activebackground='#2266cc')
        self.config(menu=mb)

        file_m = tk.Menu(mb, tearoff=0, bg='#3c3c3c', fg='white',
                         activebackground='#2266cc')
        mb.add_cascade(label='File', menu=file_m)
        file_m.add_command(label='New Score',          command=self._new_score)
        file_m.add_command(label='Import MusicXML…',   command=self._import_xml)
        file_m.add_separator()
        file_m.add_command(label='Export to PDF…',     command=self._export_pdf)
        file_m.add_separator()
        file_m.add_command(label='Exit',               command=self.quit)

        edit_m = tk.Menu(mb, tearoff=0, bg='#3c3c3c', fg='white',
                         activebackground='#2266cc')
        mb.add_cascade(label='Edit', menu=edit_m)
        edit_m.add_command(label='Edit Selected Note  [Dbl-click]',
                           command=lambda: self._canvas._edit_selected())
        edit_m.add_command(label='Add Note to Measure',
                           command=self._canvas.add_note_to_selected_measure
                           if hasattr(self, '_canvas') else lambda: None)
        edit_m.add_command(label='Delete Selected Note  [Del]',
                           command=lambda: self._canvas._delete_selected())
        edit_m.add_separator()
        edit_m.add_command(label='Score Properties…',  command=self._score_props)

        view_m = tk.Menu(mb, tearoff=0, bg='#3c3c3c', fg='white',
                         activebackground='#2266cc')
        mb.add_cascade(label='View', menu=view_m)
        view_m.add_command(label='Refresh Canvas',     command=self._refresh)

    def _build_toolbar(self):
        tb = tk.Frame(self, bg='#3c3c3c', height=44)
        tb.pack(side='top', fill='x')
        tb.pack_propagate(False)

        btn_cfg = dict(bg='#4c4c4c', fg='white', font=('Courier',9,'bold'),
                       relief='flat', padx=10, pady=4,
                       activebackground='#2266cc', activeforeground='white',
                       cursor='hand2')

        tk.Button(tb, text='📂 Import XML', command=self._import_xml, **btn_cfg).pack(side='left', padx=4, pady=6)
        tk.Button(tb, text='🖨 Export PDF',  command=self._export_pdf,  **btn_cfg).pack(side='left', padx=4)
        tk.Button(tb, text='✏ Edit Note',    command=self._edit_note,   **btn_cfg).pack(side='left', padx=4)
        tk.Button(tb, text='➕ Add Note',    command=self._add_note,    **btn_cfg).pack(side='left', padx=4)
        tk.Button(tb, text='🗑 Delete Note', command=self._del_note,    **btn_cfg).pack(side='left', padx=4)
        tk.Button(tb, text='⚙ Properties',  command=self._score_props, **btn_cfg).pack(side='left', padx=4)
        tk.Button(tb, text='🔄 Refresh',     command=self._refresh,     **btn_cfg).pack(side='left', padx=4)

        # Legend
        legend = tk.Label(tb,
            text="  Octave: d r m = normal | d' r' m' = upper | d₁ r₁ m₁ = lower",
            bg='#3c3c3c', fg='#aaaaaa', font=('Courier',8))
        legend.pack(side='right', padx=12)

    def _build_main(self):
        paned = tk.PanedWindow(self, orient='horizontal', bg='#2b2b2b',
                               sashwidth=5, sashrelief='flat')
        paned.pack(fill='both', expand=True)

        # ── Left: editable canvas ──────────────────────────────────────
        left = tk.Frame(paned, bg='#1e1e1e')
        paned.add(left, minsize=600)

        tk.Label(left, text='SCORE CANVAS  (editable)',
                 bg='#1e1e1e', fg='#cccccc',
                 font=('Courier',9,'bold')).pack(anchor='w', padx=8, pady=(4,0))

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

        # ── Right: live text view ──────────────────────────────────────
        right = tk.Frame(paned, bg='#1e1e1e')
        paned.add(right, minsize=260)

        tk.Label(right, text='LIVE TEXT VIEW',
                 bg='#1e1e1e', fg='#cccccc',
                 font=('Courier',9,'bold')).pack(anchor='w', padx=8, pady=(4,0))

        self._live = tk.Text(right, font=('Courier',10),
                             bg='#0d0d0d', fg='#e8e8e8',
                             insertbackground='white',
                             relief='flat', padx=8, pady=8,
                             state='disabled', wrap='none')
        rscroll = tk.Scrollbar(right, command=self._live.yview)
        self._live.configure(yscrollcommand=rscroll.set)
        rscroll.pack(side='right', fill='y')
        self._live.pack(fill='both', expand=True, padx=4, pady=4)

        # Keep live view updated
        self._canvas.bind('<ButtonRelease-1>', lambda e: self._update_live())
        self._canvas.bind('<KeyRelease>',      lambda e: self._update_live())

    def _build_status(self):
        self._status_var = tk.StringVar(value='Ready – Import a MusicXML file to begin.')
        bar = tk.Label(self, textvariable=self._status_var,
                       bg='#1a1a1a', fg='#999999',
                       font=('Courier',8), anchor='w', padx=8)
        bar.pack(side='bottom', fill='x')

    # ── Update live text view ────────────────────────────────────────────────

    def _update_live(self):
        lines = self._score_to_text()
        self._live.configure(state='normal')
        self._live.delete('1.0', 'end')
        self._live.insert('end', lines)
        self._live.configure(state='disabled')

    def _score_to_text(self) -> str:
        s = self._score
        out = []
        out.append(s.title.upper())
        out.append(f'Doh is {s.doh_key}   Time: {s.time_num}/{s.time_den}')
        if s.composer: out.append(f'By: {s.composer}')
        if s.tempo_text: out.append(s.tempo_text)
        out.append('')
        npart = max(1, len(s.parts))
        mpr = 4
        for row_start in range(0, len(s.measures), mpr):
            row_meas = s.measures[row_start:row_start+mpr]
            for p_idx in range(npart):
                line = f'{s.parts[p_idx][:2]:2s}|'
                for meas in row_meas:
                    notes = [n for n in meas.notes if n.part_idx == p_idx]
                    cell  = ' '.join(
                        (n.syllable if not n.is_rest else '-') + n.beat_marker
                        for n in notes) or '-:-'
                    line += f' {cell:<20}|'
                out.append(line)
            out.append('')
        return '\n'.join(out)

    # ── Actions ──────────────────────────────────────────────────────────────

    def _new_score(self):
        self._score = SolfaScore()
        self._canvas.load_score(self._score)
        self._update_live()
        self._status('New score created.')

    def _import_xml(self):
        path = filedialog.askopenfilename(
            title='Import MusicXML',
            filetypes=[('MusicXML files', '*.xml *.musicxml *.mxl'), ('All files', '*.*')])
        if not path: return
        try:
            self._score = parse_musicxml(path)
            self._canvas.load_score(self._score)
            self._update_live()
            self._status(f'Loaded: {path}  |  {len(self._score.measures)} measures')
        except Exception as exc:
            messagebox.showerror('Import Error', str(exc))

    def _export_pdf(self):
        if not HAS_REPORTLAB:
            messagebox.showwarning('reportlab missing',
                'Install reportlab:\n\n  pip install reportlab\n\nThen restart.')
            return
        path = filedialog.asksaveasfilename(
            defaultextension='.pdf',
            filetypes=[('PDF files','*.pdf')],
            initialfile=self._score.title or 'score')
        if not path: return
        try:
            _render_pdf(self._score, path)
            self._status(f'PDF exported: {path}')
            messagebox.showinfo('Export', f'Saved:\n{path}')
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

    def _refresh(self):
        self._canvas.redraw()
        self._update_live()

    def _score_props(self):
        dlg = ScorePropsDialog(self, self._score)
        self.wait_window(dlg)
        if dlg.changed:
            self._canvas.load_score(self._score)
            self._update_live()

    def _status(self, msg: str):
        self._status_var.set(msg)


# ── Score Properties Dialog ───────────────────────────────────────────────────

class ScorePropsDialog(tk.Toplevel):
    def __init__(self, parent, score: SolfaScore):
        super().__init__(parent)
        self.title('Score Properties')
        self.resizable(False, False)
        self.changed = False
        self._score  = score
        self._build()
        self.grab_set(); self.transient(parent)
        self.geometry('+%d+%d' % (parent.winfo_rootx()+150, parent.winfo_rooty()+150))

    def _build(self):
        s = self._score
        pad = dict(padx=10, pady=5)
        fields = [('Title', 'title'), ('Doh Key', 'doh_key'),
                  ('Time (num/den)', None), ('Tempo text', 'tempo_text'),
                  ('Composer', 'composer'), ('Dedication', 'dedication')]
        self._vars = {}
        for r, (lbl, attr) in enumerate(fields):
            tk.Label(self, text=lbl+':', font=('Courier',10), width=18,
                     anchor='w').grid(row=r, column=0, **pad)
            if attr:
                v = tk.StringVar(value=getattr(s, attr, ''))
                self._vars[attr] = v
                tk.Entry(self, textvariable=v, font=('Courier',10),
                         width=28).grid(row=r, column=1, **pad)
            else:
                fr = tk.Frame(self); fr.grid(row=r, column=1, **pad)
                self._tnum = tk.Entry(fr, width=4, font=('Courier',10))
                self._tnum.insert(0, str(s.time_num)); self._tnum.pack(side='left')
                tk.Label(fr, text='/').pack(side='left')
                self._tden = tk.Entry(fr, width=4, font=('Courier',10))
                self._tden.insert(0, str(s.time_den)); self._tden.pack(side='left')

        bf = tk.Frame(self); bf.grid(row=len(fields), column=0, columnspan=2, pady=10)
        tk.Button(bf, text='Apply', width=9, bg='#2266cc', fg='white',
                  font=('Courier',10,'bold'),
                  command=self._apply).pack(side='left', padx=8)
        tk.Button(bf, text='Cancel', width=9,
                  font=('Courier',10), command=self.destroy).pack(side='left')
        self.bind('<Return>', lambda e: self._apply())

    def _apply(self):
        s = self._score
        for attr, v in self._vars.items():
            setattr(s, attr, v.get())
        try:
            s.time_num = int(self._tnum.get())
            s.time_den = int(self._tden.get())
        except ValueError: pass
        self.changed = True
        self.destroy()


# ── Compatibility bridge to Solfa Canvas Pro ─────────────────────────────────

try:
    from solfa_canvas_pro import (
        SolfaCanvas as _ProSolfaCanvas,
        SolfaScore as _ProSolfaScore,
        SolfaNote as _ProSolfaNote,
        SolfaMeasure as _ProSolfaMeasure,
        render_pdf as render_pdf,
        parse_musicxml as parse_musicxml,
        duration_to_beat_marker as duration_to_beat_marker,
        pitch_to_solfa as pitch_to_solfa,
    )

    class SolfaCanvas(_ProSolfaCanvas):
        """Compatibility wrapper exposing legacy sizing attributes."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._compat_measure_width = int(getattr(self, 'MEAS_MIN_W', 150))
            beats = max(1, int(getattr(getattr(self, 'score', None), 'time_num', 4) or 4))
            self._compat_beat_width = max(20, int(self._compat_measure_width / beats))

        @property
        def beat_width(self):
            return self._compat_beat_width

        @beat_width.setter
        def beat_width(self, value):
            self._compat_beat_width = max(20, int(value))
            beats = max(1, int(getattr(getattr(self, 'score', None), 'time_num', 4) or 4))
            self.MEAS_MIN_W = max(80, self._compat_beat_width * beats)
            self._compat_measure_width = self.MEAS_MIN_W

        @property
        def measure_width(self):
            return self._compat_measure_width

        @measure_width.setter
        def measure_width(self, value):
            self._compat_measure_width = max(80, int(value))
            self.MEAS_MIN_W = self._compat_measure_width

        def render(self):
            self.redraw()

    SolfaScore = _ProSolfaScore
    SolfaNote = _ProSolfaNote
    SolfaMeasure = _ProSolfaMeasure
    _render_pdf = render_pdf
except ImportError:
    render_pdf = _render_pdf

__all__ = [
    "SolfaCanvas",
    "SolfaScore",
    "SolfaNote",
    "SolfaMeasure",
    "render_pdf",
    "_render_pdf",
    "parse_musicxml",
    "duration_to_beat_marker",
    "pitch_to_solfa",
]

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    app = SolfaApp()
    app.mainloop()

if __name__ == '__main__':
    main()
