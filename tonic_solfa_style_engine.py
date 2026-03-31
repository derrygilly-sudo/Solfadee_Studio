#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tonic_solfa_style_engine.py
════════════════════════════════════════════════════════════════════
COMPLETE COMBINED FILE — drop into the SolfaDee Studio package.

Six PDF-derived notation style presets:
  ARMAAH       — Afehyiapa (Armaah 2022)         Key C, 6/8
  DOUGLAS      — Aseda Afɔreɛ (Douglas 2024)     Key F, 6/8
  DARKO        — Mitso Aseye (Darko 2010)         Key F, 6/8
  MCPRINCE_2_4 — Monto Dwom (McPrince 2026)       Key G, 2/4
  ARHIN        — Oman Ye Wo Man (Arhin 2016)      Key F, 3/4
  MCPRINCE_4_4 — Wasɔr (McPrince 2026)            Key C, 4/4
  DEFAULT      — Neutral Curwen

Integration into solfadee_studio_v5.py:
  1. import this module at the top of the main file.
  2. In TonicSolfaStudio.__init__:
       self.style_registry = StyleRegistry()
       self.style_renderer = SolfaStyleRenderer(
           self.style_registry.get('DEFAULT'))
  3. In _build_main(), add the selector widget to any panel:
       self.style_selector = StyleSelectorWidget(
           some_frame, self.style_registry,
           on_apply=self._on_style_applied)
  4. Add the handler:
       def _on_style_applied(self, renderer):
           self.style_renderer = renderer
           self.trad_canvas.set_style_renderer(renderer)
           self._on_change()
  5. In TraditionalSolfaCanvas._draw_measure_row, replace the
     note_token call with:
       tok = self.style_renderer.note_token(n, key)
     and replace build_measure_string with:
       mstr = self.style_renderer.measure_string(
           vnotes, key, meas.time_num, meas.time_den)
════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple


# ════════════════════════════════════════════════════════════════
#  UNICODE HELPERS
# ════════════════════════════════════════════════════════════════
_SUB = {str(i): chr(0x2080 + i) for i in range(10)}
_SUP = {'1': '¹', '2': '²', '3': '³', '4': '⁴',
        '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'}


def _to_subscript(n: int) -> str:
    return ''.join(_SUB.get(c, c) for c in str(abs(n)))


def _to_superscript_str(n: int) -> str:
    return ''.join(_SUP.get(c, c) for c in str(abs(n)))


# ════════════════════════════════════════════════════════════════
#  FONT PROFILE
# ════════════════════════════════════════════════════════════════
@dataclass
class FontProfile:
    syllable_family:  str   = "Times New Roman"
    syllable_size:    int   = 13
    syllable_bold:    bool  = True
    lyric_family:     str   = "Times New Roman"
    lyric_size:       int   = 9
    lyric_bold:       bool  = False
    voice_label_size: int   = 10
    header_size:      int   = 18
    bar_num_size:     int   = 7
    annot_size:       int   = 8
    scale:            float = 1.0

    def syllable(self) -> tuple:
        sz = max(6, int(self.syllable_size * self.scale))
        return (self.syllable_family, sz,
                'bold' if self.syllable_bold else 'normal')

    def lyric(self) -> tuple:
        sz = max(6, int(self.lyric_size * self.scale))
        return (self.lyric_family, sz,
                'bold' if self.lyric_bold else 'normal')

    def voice_label(self) -> tuple:
        return (self.syllable_family,
                max(6, int(self.voice_label_size * self.scale)), 'bold')

    def header(self) -> tuple:
        return (self.syllable_family,
                max(8, int(self.header_size * self.scale)), 'bold')

    def bar_num(self) -> tuple:
        return (self.syllable_family,
                max(5, int(self.bar_num_size * self.scale)), 'normal')

    def annotation(self) -> tuple:
        return (self.syllable_family,
                max(6, int(self.annot_size * self.scale)), 'italic')


# ════════════════════════════════════════════════════════════════
#  STYLE DEFINITION
# ════════════════════════════════════════════════════════════════
@dataclass
class StyleDefinition:
    name:        str = "Default"
    description: str = ""
    source:      str = ""

    # Octave marking strategies
    high_oct_style:  str = 'apostrophe'   # 'apostrophe' | 'superscript' | 'inline_num'
    low_oct_style:   str = 'subscript'    # 'subscript'  | 'inline_num'  | 'superscript'

    # Separators
    beat_sep:     str = ':'
    half_bar_sep: str = '|'

    # Tokens
    hold_token:   str = '-'
    rest_token:   str = '-'
    empty_token:  str = ':'

    # Sub-beat / grace / anacrusis
    sub_beat_prefix:  str = ''
    grace_prefix:     str = ','
    anacrusis_marker: str = ''

    # Chromatic display
    uppercase_fe:   bool = False
    flat7_syllable: str  = 'ta'

    # Layout
    voice_layout:         str = 'satb_4'          # 'satb_4' | 'two_voice' | 'single'
    lyric_position:       str = 'between_groups'  # 'between_groups' | 'below_voice' | 'shared_row'
    bar_number_position:  str = 'above_cell'       # 'above_cell' | 'inline_left'
    measures_per_row:     int = 4
    beat_width_px:        int = 50
    voice_height_px:      int = 34

    # Structural symbols
    brace_char:        str = '{'
    dc_label:          str = 'D.C.'
    ds_label:          str = 'D.S.'
    fine_label:        str = 'Fine'
    first_time_label:  str = '1st Time'
    second_time_label: str = '2nd Time'
    repeat_start_sym:  str = '||:'
    repeat_end_sym:    str = ':|'
    double_bar_sym:    str = '||'

    # Colours
    paper_bg:    str = "#f5f0e4"
    paper_ink:   str = "#140e04"
    paper_line:  str = "#9a8060"
    paper_bar:   str = "#2a1800"
    paper_lyric: str = "#1a3060"
    paper_dyn:   str = "#8b0000"
    paper_head:  str = "#3a0000"
    paper_voice: str = "#3e2f1d"
    paper_barnum:str = "#5a4030"
    paper_annot: str = "#8b0000"

    font: FontProfile = field(default_factory=FontProfile)


# ════════════════════════════════════════════════════════════════
#  MUSIC THEORY TABLES
# ════════════════════════════════════════════════════════════════
_INTERVAL_TO_SYLLABLE: Dict[int, str] = {
    0: 'd',  1: 'de',  2: 'r',  3: 're',
    4: 'm',  5: 'f',   6: 'fe', 7: 's',
    8: 'se', 9: 'l',  10: 'ta', 11: 't',
}

_KEY_TONIC_CHROM: Dict[str, int] = {
    'C': 0,  'G': 7,  'D': 2,  'A': 9,  'E': 4,
    'B': 11, 'F#': 6, 'Gb': 6, 'Db': 1, 'Ab': 8,
    'Eb': 3, 'Bb': 10, 'F': 5,
}

_PITCH_TO_CHROM: Dict[str, int] = {
    'C': 0,  'C#': 1, 'Db': 1, 'D': 2,  'D#': 3, 'Eb': 3,
    'E': 4,  'E#': 5, 'Fb': 4, 'F': 5,  'F#': 6, 'Gb': 6,
    'G': 7,  'G#': 8, 'Ab': 8, 'A': 9,  'A#': 10,'Bb': 10,
    'B': 11, 'B#': 0, 'Cb': 11,
}

_UPPERCASE_CHROM = {
    'fe': 'F', 'de': 'De', 're': 'Re',
    'se': 'Se', 'ta': 'Ta', 'le': 'Le',
}


# ════════════════════════════════════════════════════════════════
#  TOKEN BUILDER
# ════════════════════════════════════════════════════════════════
class TokenBuilder:
    """Converts one note's attributes into a display token."""

    def __init__(self, style: StyleDefinition):
        self.s = style

    def build(self, pitch: str, octave: int, duration: float,
              dotted: bool, rest: bool, tied: bool,
              voice: int, key: str = 'C',
              grace: bool = False,
              sub_beat: bool = False) -> str:
        if rest:
            base = self.s.rest_token
        else:
            base = self._syllable(pitch, key)
            base = self._octave(base, octave)
            base = self._dur_suffix(base, duration, dotted)
        if tied:
            base += '~'
        if grace:
            return self.s.grace_prefix + base
        if sub_beat:
            return self.s.sub_beat_prefix + base
        return base

    def _syllable(self, pitch: str, key: str) -> str:
        nc    = _PITCH_TO_CHROM.get(pitch, 0)
        tonic = _KEY_TONIC_CHROM.get(key, 0)
        iv    = (nc - tonic) % 12
        syl   = _INTERVAL_TO_SYLLABLE.get(iv, '?')
        if iv == 10:
            syl = self.s.flat7_syllable
        if self.s.uppercase_fe and syl in _UPPERCASE_CHROM:
            syl = _UPPERCASE_CHROM[syl]
        return syl

    def _octave(self, syl: str, octave: int) -> str:
        diff = octave - 4    # home always = 4
        if diff == 0:
            return syl
        if diff > 0:
            return syl + self._hi(diff)
        return syl + self._lo(abs(diff))

    def _hi(self, n: int) -> str:
        if self.s.high_oct_style == 'superscript':
            return _to_superscript_str(n)
        return "'" * n   # apostrophe and inline_num both use apostrophe for high

    def _lo(self, n: int) -> str:
        if self.s.low_oct_style == 'subscript':
            return _to_subscript(n)
        return str(n)    # inline_num

    def _dur_suffix(self, syl: str, dur: float, dotted: bool) -> str:
        d = dur * 1.5 if dotted else dur
        if d >= 1.0:   return syl
        if d >= 0.75:  return syl + '.·'
        if d >= 0.5:   return syl + '.'
        if d >= 0.25:  return syl + ','
        return syl + ';'


# ════════════════════════════════════════════════════════════════
#  MEASURE STRING BUILDER
# ════════════════════════════════════════════════════════════════
class MeasureStringBuilder:
    Q = 960

    def __init__(self, style: StyleDefinition):
        self.s  = style
        self.tb = TokenBuilder(style)

    def build(self, notes, key: str, time_num: int, time_den: int,
              anacrusis: bool = False) -> str:
        beat_ticks = self.Q * 4 // time_den
        slots      = self._slots(notes, key, time_num, beat_ticks, anacrusis)
        return self._join(slots, time_num, time_den)

    def _slots(self, notes, key, time_num, beat_ticks, anacrusis):
        half_t = beat_ticks // 2
        onset: Dict[int, Tuple[str, int]] = {}
        pos = 0
        for n in notes:
            b     = n.duration * (1.5 if getattr(n, 'dotted', False) else 1.0)
            dur_t = int(round(b * self.Q))
            tok   = self.tb.build(
                pitch    = n.pitch,
                octave   = n.octave,
                duration = n.duration,
                dotted   = getattr(n, 'dotted',    False),
                rest     = getattr(n, 'rest',      False),
                tied     = getattr(n, 'tied',      False),
                voice    = getattr(n, 'voice',     1),
                key      = key,
                grace    = getattr(n, 'grace',     False),
                sub_beat = getattr(n, 'sub_beat',  False),
            )
            onset[pos] = (tok, pos + dur_t)
            pos += dur_t

        slots    = []
        held_end = (beat_ticks
                    if (notes and getattr(notes[0], 'tied', False))
                    else 0)

        for bi in range(time_num):
            bs    = bi * beat_ticks
            bm    = bs + half_t
            entry = onset.get(bs)

            if entry is not None:
                tok, end = entry
                held_end = end
                token    = tok
                sub = onset.get(bm)
                if sub and self.s.sub_beat_prefix:
                    st, se = sub
                    held_end = se
                    token += self.s.sub_beat_prefix + st
            elif held_end > bs:
                token = self.s.hold_token
                sub = onset.get(bm)
                if sub and self.s.sub_beat_prefix:
                    st, se = sub
                    held_end = se
                    token += self.s.sub_beat_prefix + st
            else:
                token = self.s.empty_token

            slots.append(token)

        if anacrusis and self.s.anacrusis_marker:
            for i, sl in enumerate(slots):
                if sl and sl != self.s.empty_token:
                    slots[i] = self.s.anacrusis_marker + sl
                    break
        return slots

    def _join(self, slots, time_num, time_den):
        sep = self.s.beat_sep
        hb  = self.s.half_bar_sep

        if time_num == 6 and time_den == 8:
            return sep.join(slots[:3]) + hb + sep.join(slots[3:])
        if time_num == 12 and time_den == 8:
            parts = [sep.join(slots[i:i+3]) for i in range(0, 12, 3)]
            return hb.join(parts)
        if time_num == 9 and time_den == 8:
            parts = [sep.join(slots[i:i+3]) for i in range(0, 9, 3)]
            return hb.join(parts)
        if time_num == 4 and time_den == 4 and hb:
            return sep.join(slots[:2]) + hb + sep.join(slots[2:])
        return sep.join(slots)


# ════════════════════════════════════════════════════════════════
#  STYLE REGISTRY
# ════════════════════════════════════════════════════════════════
class StyleRegistry:
    def __init__(self):
        self._s: Dict[str, StyleDefinition] = {}
        self._build()

    def register(self, k: str, s: StyleDefinition):
        self._s[k.upper()] = s

    def get(self, k: str) -> StyleDefinition:
        return self._s.get(k.upper(), self._s['DEFAULT'])

    def all_names(self) -> List[Tuple[str, str]]:
        return sorted((k, v.name) for k, v in self._s.items())

    def _build(self):
        FP = FontProfile

        # ── DEFAULT ──────────────────────────────────
        self.register('DEFAULT', StyleDefinition(
            name="Default (Curwen)",
            source="Standard Curwen convention",
            font=FP(syllable_family="Times New Roman",
                    syllable_size=13, syllable_bold=True,
                    lyric_family="Times New Roman", lyric_size=9),
        ))

        # ── ARMAAH — Afehyiapa 2022, Key C, 6/8 ─────
        # Distinguishing features:
        #   • Uppercase F for raised subdominant (fe → F)
        #   • Apostrophe high octave:  d', s:d':-
        #   • Unicode subscript low:   d₁, l₁, s₁
        #   • Hold token: '-'
        #   • 4 bars per row, compact 30px voice rows
        self.register('ARMAAH', StyleDefinition(
            name="Armaah (Afehyiapa 2022)",
            description="Compact SATB cell, 6/8, uppercase F for fe, "
                        "apostrophe high, subscript low",
            source="James Varrick Armaah — Afehyiapa, Dec 2022, Accra",
            high_oct_style='apostrophe',
            low_oct_style='subscript',
            beat_sep=':', half_bar_sep='|',
            hold_token='-', rest_token='-', empty_token=':',
            sub_beat_prefix='', anacrusis_marker='',
            uppercase_fe=True, flat7_syllable='ta',
            voice_layout='satb_4',
            lyric_position='between_groups',
            bar_number_position='above_cell',
            measures_per_row=4, beat_width_px=46, voice_height_px=30,
            paper_bg="#faf6ee", paper_ink="#0a0800", paper_head="#2a0000",
            font=FP(syllable_family="Times New Roman",
                    syllable_size=12, syllable_bold=True,
                    lyric_family="Times New Roman", lyric_size=8,
                    header_size=16),
        ))

        # ── DOUGLAS — Aseda Afɔreɛ 2024, Key F, 6/8 ─
        # Distinguishing features:
        #   • Spaced beat separator:  ' : '
        #   • Inline number low octave: s1, t1, ta1, l1
        #   • Apostrophe high octave
        #   • Lyric printed BELOW each voice row (not grouped)
        #   • Standard fe (not uppercase)
        self.register('DOUGLAS', StyleDefinition(
            name="Douglas (Aseda Afɔreɛ 2024)",
            description="Spaced colons, inline-number low octave, "
                        "lyric below each voice row",
            source="Adomako Douglas — Aseda Afɔreɛ, Dec 2024, Sunyani",
            high_oct_style='apostrophe',
            low_oct_style='inline_num',
            beat_sep=' : ', half_bar_sep='|',
            hold_token='-', rest_token='-', empty_token=' : ',
            sub_beat_prefix='', anacrusis_marker='',
            uppercase_fe=False, flat7_syllable='ta',
            voice_layout='satb_4',
            lyric_position='below_voice',
            bar_number_position='above_cell',
            measures_per_row=4, beat_width_px=52, voice_height_px=36,
            font=FP(syllable_family="Times New Roman",
                    syllable_size=11, syllable_bold=False,
                    lyric_family="Times New Roman", lyric_size=8),
        ))

        # ── DARKO — Mitso Aseye 2010, Key F, 6/8 ────
        # Distinguishing features:
        #   • Unicode subscript low: fi₁, fe₁, s₁
        #   • Red lyric rows (rendered as dark-red paper_lyric)
        #   • DS/DC cue labels
        #   • Compact ':' separators like Armaah but standard fe
        self.register('DARKO', StyleDefinition(
            name="Darko (Mitso Aseye 2010)",
            description="6/8 SATB, unicode subscripts, red lyric rows, "
                        "DS/DC cue labels",
            source="Emmanuel B. Darko — Mitso Aseye, 2010, UEW Mba",
            high_oct_style='apostrophe',
            low_oct_style='subscript',
            beat_sep=':', half_bar_sep='|',
            hold_token='-', rest_token='-', empty_token=':',
            sub_beat_prefix='', anacrusis_marker='',
            uppercase_fe=False, flat7_syllable='ta',
            voice_layout='satb_4',
            lyric_position='between_groups',
            bar_number_position='above_cell',
            measures_per_row=4, beat_width_px=48, voice_height_px=32,
            paper_lyric="#8b0000",   # red lyrics
            paper_annot="#8b0000",
            font=FP(syllable_family="Times New Roman",
                    syllable_size=12, syllable_bold=True,
                    lyric_family="Times New Roman", lyric_size=8),
        ))

        # ── MCPRINCE_2_4 — Monto Dwom 2026, Key G, 2/4
        # Distinguishing features:
        #   • Dot sub-beat:  s :- .s  (space-dot before sub-beat note)
        #   • Comma grace:   d :d . ,d
        #   • Pickup anacrusis: leading ': ' before first note
        #   • Two-voice layout (melody + bass, not full SATB brace)
        #   • Shared lyric row between the two voices
        #   • Six bars per row
        #   • Inline number low octave: s1, d1
        self.register('MCPRINCE_2_4', StyleDefinition(
            name="McPrince 2/4 (Monto Dwom 2026)",
            description="Dot sub-beat, comma grace, pickup anacrusis, "
                        "2-voice rows, 6 bars/line",
            source="O. A. McPrince — Monto Dwom, Feb 2026, Asante Mampong",
            high_oct_style='apostrophe',
            low_oct_style='inline_num',
            beat_sep=' :', half_bar_sep='',
            hold_token='-', rest_token='-', empty_token=' :',
            sub_beat_prefix=' .', grace_prefix=' ,',
            anacrusis_marker=': ',
            uppercase_fe=False, flat7_syllable='ta',
            voice_layout='two_voice',
            lyric_position='shared_row',
            bar_number_position='above_cell',
            measures_per_row=6, beat_width_px=56, voice_height_px=28,
            font=FP(syllable_family="Times New Roman",
                    syllable_size=11, syllable_bold=False,
                    lyric_family="Times New Roman", lyric_size=8,
                    header_size=14),
        ))

        # ── ARHIN — Oman Ye Wo Man 2016, Key F, 3/4 ─
        # Distinguishing features:
        #   • Em-dash hold token:  '—'
        #   • Inline number low octave: l1, s1, ta1
        #   • D/C label (not D.C.)
        #   • 3/4 time, full SATB
        #   • Blank interstitial rows between voice groups
        self.register('ARHIN', StyleDefinition(
            name="Arhin (Oman Ye Wo Man 2016)",
            description="3/4, em-dash hold, inline-number low octave, "
                        "D/C Fine labels",
            source="Alex Arhin — Oman Ye Wo Man, Nov 2016",
            high_oct_style='apostrophe',
            low_oct_style='inline_num',
            beat_sep=':', half_bar_sep='|',
            hold_token='—', rest_token='—', empty_token=':',
            sub_beat_prefix='', anacrusis_marker='',
            uppercase_fe=False, flat7_syllable='ta',
            voice_layout='satb_4',
            lyric_position='between_groups',
            bar_number_position='above_cell',
            measures_per_row=4, beat_width_px=50, voice_height_px=32,
            dc_label='D/C',
            font=FP(syllable_family="Times New Roman",
                    syllable_size=12, syllable_bold=False,
                    lyric_family="Times New Roman", lyric_size=8),
        ))

        # ── MCPRINCE_4_4 — Wasɔr 2026, Key C, 4/4 ──
        # Distinguishing features:
        #   • Superscript-number high octave: r¹, d¹, f¹, l¹
        #   • Dot sub-beat:  : m :m | f :l  with '. :' prefix
        #   • Inline number low octave
        #   • Two-voice layout (melody + bass pairs)
        #   • Shared lyric row
        self.register('MCPRINCE_4_4', StyleDefinition(
            name="McPrince 4/4 (Wasɔr 2026)",
            description="Superscript high octave (r¹), dot sub-beat, "
                        "2-voice rows, 4/4",
            source="O. A. McPrince — Wasɔr, March 2026, Asante Mampong",
            high_oct_style='superscript',   # r¹ d¹
            low_oct_style='inline_num',
            beat_sep=' :', half_bar_sep='|',
            hold_token='-', rest_token='-', empty_token=' :',
            sub_beat_prefix=' .', grace_prefix=' ,',
            anacrusis_marker=': ',
            uppercase_fe=False, flat7_syllable='ta',
            voice_layout='two_voice',
            lyric_position='shared_row',
            bar_number_position='above_cell',
            measures_per_row=4, beat_width_px=56, voice_height_px=30,
            font=FP(syllable_family="Times New Roman",
                    syllable_size=12, syllable_bold=False,
                    lyric_family="Times New Roman", lyric_size=9,
                    header_size=14),
        ))


# ════════════════════════════════════════════════════════════════
#  SOLFA STYLE RENDERER  (main public API)
# ════════════════════════════════════════════════════════════════
class SolfaStyleRenderer:
    def __init__(self, style: StyleDefinition):
        self.style = style
        self._tb   = TokenBuilder(style)
        self._msb  = MeasureStringBuilder(style)

    def note_token(self, note, key: str = 'C') -> str:
        return self._tb.build(
            pitch    = note.pitch,
            octave   = note.octave,
            duration = note.duration,
            dotted   = getattr(note, 'dotted', False),
            rest     = getattr(note, 'rest',   False),
            tied     = getattr(note, 'tied',   False),
            voice    = getattr(note, 'voice',  1),
            key      = key,
        )

    def measure_string(self, notes, key: str,
                       time_num: int, time_den: int,
                       anacrusis: bool = False) -> str:
        return self._msb.build(notes, key, time_num, time_den, anacrusis)

    def canvas_props(self) -> dict:
        s = self.style
        return {
            'measures_per_row':    s.measures_per_row,
            'beat_width':          s.beat_width_px,
            'voice_height':        s.voice_height_px,
            'font_family':         s.font.syllable_family,
            'font_scale':          s.font.scale,
            'lyric_font_family':   s.font.lyric_family,
            'voice_layout':        s.voice_layout,
            'lyric_position':      s.lyric_position,
            'bar_number_position': s.bar_number_position,
            'paper_bg':            s.paper_bg,
            'paper_ink':           s.paper_ink,
            'paper_line':          s.paper_line,
            'paper_bar':           s.paper_bar,
            'paper_lyric':         s.paper_lyric,
            'paper_dyn':           s.paper_dyn,
            'paper_head':          s.paper_head,
            'paper_voice':         s.paper_voice,
            'paper_barnum':        s.paper_barnum,
        }

    def structural_label(self, label_type: str) -> str:
        s = self.style
        return {
            'dc': s.dc_label, 'ds': s.ds_label, 'fine': s.fine_label,
            'first_time': s.first_time_label,
            'second_time': s.second_time_label,
            'repeat_start': s.repeat_start_sym,
            'repeat_end':   s.repeat_end_sym,
            'double_bar':   s.double_bar_sym,
        }.get(label_type.lower(), label_type)


# ════════════════════════════════════════════════════════════════
#  STYLE SELECTOR WIDGET
# ════════════════════════════════════════════════════════════════
_PNL = "#16213e"; _CARD = "#0f3460"; _DARK = "#1a1a2e"
_GLD = "#f5a623"; _TXT  = "#eaeaea"; _MTD  = "#8892a4"
_ACC = "#e94560"; _GRN  = "#00d4aa"; _WHT  = "#ffffff"


class StyleSelectorWidget(tk.Frame):
    """
    Drop-in Tkinter widget for style selection and live preview.

    Usage:
        selector = StyleSelectorWidget(
            parent_frame,
            registry,
            on_apply=lambda renderer: canvas.set_style_renderer(renderer))
        selector.pack(fill='x')
    """

    def __init__(self, master, registry: StyleRegistry,
                 on_apply=None, **kwargs):
        super().__init__(master, bg=_PNL, **kwargs)
        self._registry = registry
        self._on_apply = on_apply
        self._renderer: Optional[SolfaStyleRenderer] = None
        self._build()

    def _build(self):
        # ── Row 1: combobox + apply button ──────────
        r1 = tk.Frame(self, bg=_PNL); r1.pack(fill='x', padx=6, pady=(6, 2))
        tk.Label(r1, text="Notation Style:", bg=_PNL, fg=_GLD,
                 font=('Arial', 8, 'bold')).pack(side='left')

        names = self._registry.all_names()
        self._keys  = [k for k, _ in names]
        self._disp  = [f"{n}  [{k}]" for k, n in names]

        self._var = tk.StringVar()
        self._cb  = ttk.Combobox(r1, textvariable=self._var,
                                  values=self._disp, width=36,
                                  state='readonly', font=('Arial', 9))
        self._cb.pack(side='left', padx=(6, 4))
        try:
            self._cb.current(self._keys.index('DEFAULT'))
        except ValueError:
            self._cb.current(0)
        self._cb.bind('<<ComboboxSelected>>', self._on_sel)

        tk.Button(r1, text="Apply Style",
                  bg=_ACC, fg=_WHT, relief='flat',
                  font=('Arial', 8, 'bold'), padx=8,
                  command=self._apply).pack(side='left', padx=4)

        # ── Row 2: source / description info ────────
        r2 = tk.Frame(self, bg=_CARD); r2.pack(fill='x', padx=6, pady=(0, 2))
        self._info = tk.Label(r2, text="", bg=_CARD, fg=_MTD,
                              font=('Arial', 7), anchor='w', wraplength=560)
        self._info.pack(side='left', padx=8, pady=3)

        # ── Row 3: font override + scale ────────────
        r3 = tk.Frame(self, bg=_PNL); r3.pack(fill='x', padx=6, pady=(2, 2))
        tk.Label(r3, text="Font:", bg=_PNL, fg=_MTD,
                 font=('Arial', 8)).pack(side='left')
        self._fvar = tk.StringVar(value="— style default —")
        ttk.Combobox(r3, textvariable=self._fvar,
                     values=["— style default —",
                             "Times New Roman", "Georgia",
                             "Palatino Linotype", "Courier New",
                             "Arial", "Verdana"],
                     width=20, state='readonly',
                     font=('Arial', 8)).pack(side='left', padx=(4, 10))
        tk.Label(r3, text="Scale:", bg=_PNL, fg=_MTD,
                 font=('Arial', 8)).pack(side='left')
        self._svar = tk.DoubleVar(value=1.0)
        ttk.Spinbox(r3, from_=0.6, to=2.5, increment=0.1,
                    textvariable=self._svar,
                    width=4, font=('Arial', 8)).pack(side='left', padx=4)

        # ── Row 4: live preview strip ────────────────
        r4 = tk.Frame(self, bg='#f5f0e4', height=32)
        r4.pack(fill='x', padx=6, pady=(2, 6))
        r4.pack_propagate(False)
        self._prev = tk.Label(r4, text="", bg='#f5f0e4',
                              fg='#140e04', anchor='w')
        self._prev.pack(side='left', padx=10, pady=4)

        self._on_sel()   # populate initial state

    def _key(self) -> str:
        idx = self._cb.current()
        return self._keys[idx] if idx >= 0 else 'DEFAULT'

    def _on_sel(self, _event=None):
        style = self._registry.get(self._key())
        self._info.config(
            text=(f"Source: {style.source or '—'}  |  "
                  f"Layout: {style.voice_layout}  |  "
                  f"High oct: {style.high_oct_style}  |  "
                  f"Low oct: {style.low_oct_style}  |  "
                  f"Beat sep: {repr(style.beat_sep)}  |  "
                  f"Hold: {repr(style.hold_token)}"))
        self._refresh_preview(style)

    def _refresh_preview(self, style: StyleDefinition):
        tb  = TokenBuilder(style)
        sep = style.beat_sep
        hb  = style.half_bar_sep if style.half_bar_sep else ' '
        # Sample: d  m  s  d' (quarters in C major, 4/4)
        toks = [tb.build(p, o, 1.0, False, False, False, 1, 'C')
                for p, o in [('C',4),('E',4),('G',4),('C',5)]]
        preview = sep.join(toks[:2]) + hb + sep.join(toks[2:])

        ff = style.font.syllable_family
        fs = max(10, int(style.font.syllable_size * style.font.scale))
        fw = 'bold' if style.font.syllable_bold else 'normal'
        self._prev.config(text=preview,
                          font=(ff, fs, fw),
                          bg=style.paper_bg, fg=style.paper_ink)

    def _apply(self):
        style = self._registry.get(self._key())
        fnt   = self._fvar.get()
        if fnt != "— style default —":
            style.font.syllable_family = fnt
            style.font.lyric_family    = fnt
        style.font.scale = self._svar.get()

        self._renderer = SolfaStyleRenderer(style)
        if self._on_apply:
            self._on_apply(self._renderer)

    def active_renderer(self) -> Optional[SolfaStyleRenderer]:
        return self._renderer

    def set_style(self, key: str):
        try:
            self._cb.current(self._keys.index(key.upper()))
            self._on_sel()
        except ValueError:
            pass


# ════════════════════════════════════════════════════════════════
#  CANVAS INTEGRATION PATCH
#  Paste the body of this function into TraditionalSolfaCanvas
#  to wire the style engine into the existing canvas.
# ════════════════════════════════════════════════════════════════
def patch_canvas_for_style_engine(canvas_instance,
                                   renderer: SolfaStyleRenderer):
    """
    Apply a SolfaStyleRenderer to an existing TraditionalSolfaCanvas.

    Call this whenever the user changes the active style:
        patch_canvas_for_style_engine(self.trad_canvas, renderer)
        self.trad_canvas.redraw()

    The patch:
      1. Stores the renderer on the canvas instance.
      2. Overwrites the canvas colour attributes with style colours.
      3. Updates font settings.
    """
    props = renderer.canvas_props()
    c     = canvas_instance
    style = renderer.style

    # Canvas render options
    c.set_render_options(
        measures_per_row  = props['measures_per_row'],
        beat_width        = props['beat_width'],
        font_family       = props['font_family'],
        font_scale        = props['font_scale'],
        lyric_font_family = props['lyric_font_family'],
    )

    # Colour attributes (used in _draw_page, _draw_system, etc.)
    c.PAPER_BG    = style.paper_bg
    c.PAPER_INK   = style.paper_ink
    c.PAPER_LINE  = style.paper_line
    c.PAPER_BAR   = style.paper_bar
    c.PAPER_LYRIC = style.paper_lyric
    c.PAPER_DYN   = style.paper_dyn
    c.PAPER_HEAD  = style.paper_head
    c.PAPER_VOICE = style.paper_voice
    c.PAPER_BARNUM= style.paper_barnum
    c.configure(bg=style.paper_bg)

    # Store renderer for measure-string calls
    c.style_renderer = renderer


# ════════════════════════════════════════════════════════════════
#  SELF-TEST  (run standalone: python tonic_solfa_style_engine.py)
# ════════════════════════════════════════════════════════════════
def _self_test():
    from types import SimpleNamespace

    def N(pitch, oct, dur, voice=1, dotted=False, rest=False, tied=False):
        return SimpleNamespace(pitch=pitch, octave=oct, duration=dur,
                               voice=voice, dotted=dotted, rest=rest,
                               tied=tied, sub_beat=False, grace=False)

    reg = StyleRegistry()

    print("=" * 68)
    print("  TONIC SOLFA STYLE ENGINE — SELF TEST")
    print("=" * 68)

    # Test notes: C-major SATB chord + passing notes
    notes_C = [
        N('C', 5, 1.0, voice=1),   # soprano: d'
        N('G', 4, 1.0, voice=2),   # alto:    s
        N('E', 4, 1.0, voice=3),   # tenor:   m
        N('C', 3, 1.0, voice=4),   # bass:    d₁
    ]
    notes_6_8 = [
        N('C', 5, 0.5, voice=1), N('D', 5, 0.5), N('E', 5, 0.5),
        N('G', 4, 0.5, voice=1), N('A', 4, 0.5), N('B', 4, 0.5),
    ]

    for key in reg.all_names():
        style_key, name = key
        renderer = SolfaStyleRenderer(reg.get(style_key))
        print(f"\n  [{style_key}] {name}")
        print(f"  Source: {reg.get(style_key).source}")

        # Single note tokens for SATB chord
        toks = [renderer.note_token(n, key='C') for n in notes_C]
        print(f"  Chord tokens (S A T B): {' | '.join(toks)}")

        # 4/4 measure for soprano voice
        sop = [n for n in notes_C if n.voice == 1]
        mstr = renderer.measure_string(
            sop + [N('E',5,1.0),N('G',4,1.0),N('E',5,1.0)],
            key='C', time_num=4, time_den=4)
        print(f"  4/4 measure (soprano):  {mstr}")

        # 6/8 measure
        if style_key in ('ARMAAH', 'DOUGLAS', 'DARKO'):
            mstr68 = renderer.measure_string(
                notes_6_8[:6], key='C', time_num=6, time_den=8)
            print(f"  6/8 measure:            {mstr68}")

        # Structural labels
        dc = renderer.structural_label('dc')
        fi = renderer.structural_label('fine')
        rs = renderer.structural_label('repeat_start')
        print(f"  Labels: DC={dc}  Fine={fi}  Repeat={rs}")

    print()
    print("=" * 68)
    print("  All style tokens generated successfully.")
    print("=" * 68)


if __name__ == '__main__':
    _self_test()
