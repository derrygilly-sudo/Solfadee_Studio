#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║   TONIC SOLFA STUDIO  v5.0                                   ║
║   Professional Music Notation & Tonic Solfa Software         ║
║   Staff Notation ↔ Traditional Tonic Solfa  (SATB)           ║
║   MusicXML · MIDI · WAV · PDF · ABC · TSS Project            ║
║   Smart Entry · Full Keyboard Shortcuts · SATB Palettes      ║
╚══════════════════════════════════════════════════════════════╝

Install optional libs:
    pip install midiutil reportlab pygame pillow mido
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import json, os, math, copy, struct, io, zipfile, time
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict

# External component integrations
from font_styles_manager import FontStylesManager, FontStylesDialog
from lyrics_manager import LyricsManager, LyricsEditorPanel
from audio_engine import AudioConfig, AudioSynthesizer, WavFileWriter, Instrument

# ═══════════════════════════════════════════════════════
#  OPTIONAL LIBRARIES
# ═══════════════════════════════════════════════════════
try:
    from midiutil import MIDIFile
    MIDIUTIL_OK = True
except ImportError:
    MIDIUTIL_OK = False

try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

try:
    import pygame
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    PYGAME_OK = True
except ImportError:
    PYGAME_OK = False

try:
    import mido
    MIDO_OK = True
except ImportError:
    MIDO_OK = False

try:
    import wave
    WAVE_OK = True
except ImportError:
    WAVE_OK = False

# ═══════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════
APP_NAME    = "SolfaDee Studio Pro v1.0"
APP_VERSION = "1.0"
SETTINGS_FILE = os.path.expanduser("~/.tonicsolfa6_settings.json")

# Dark UI palette
DARK   = "#1a1a2e"; PANEL  = "#16213e"; CARD   = "#0f3460"
ACCENT = "#e94560"; GOLD   = "#f5a623"; TEXT   = "#eaeaea"
MUTED  = "#8892a4"; GREEN  = "#00d4aa"; WHITE  = "#ffffff"
BLUE   = "#4fc3f7"; PURPLE = "#ce93d8"; ORANGE = "#ff9800"

# Paper (traditional solfa print — matches historical hymn-book images)
PAPER_BG    = "#f5f0e4"
PAPER_INK   = "#140e04"
PAPER_LINE  = "#9a8060"
PAPER_BAR   = "#2a1800"
PAPER_LYRIC = "#1a3060"
PAPER_DYN   = "#8b0000"
PAPER_HEAD  = "#3a0000"
PAPER_VOICE = "#3e2f1d"
PAPER_BARNUM= "#5a4030"

# Staff colours
STAFF_LINE_COL = "#4a6a90"; STAFF_BAR_COL = "#7090b0"
LEDGER_COL     = "#4a6a90"; NOTE_COL      = "#e8e8e8"
NOTE_SEL       = "#e94560"

# Music theory
NOTE_TO_CHROM = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
CHROM_TO_NOTE = {0:'C',1:'C#',2:'D',3:'Eb',4:'E',5:'F',
                 6:'F#',7:'G',8:'Ab',9:'A',10:'Bb',11:'B'}
CHROMATIC_SOLFA_SHARP = {1:'de',3:'re',6:'fe',8:'se',10:'le'}
CHROMATIC_SOLFA_FLAT  = {1:'ra',3:'ma',6:'fe',8:'la',10:'ta'}
CHROM_TO_SOLFA = {
    0:'d',2:'r',4:'m',5:'f',7:'s',9:'l',11:'t',
    1:'de',3:'re',6:'fe',8:'se',10:'le'
}
# Complete pitch-to-chromatic lookup — handles all enharmonic spellings
PITCH_TO_CHROM = {
    'C': 0,  'C#': 1,  'Db': 1,  'D': 2,  'D#': 3,  'Eb': 3,
    'E': 4,  'E#': 5,  'Fb': 4,  'F': 5,  'F#': 6,  'Gb': 6,
    'G': 7,  'G#': 8,  'Ab': 8,  'A': 9,  'A#': 10, 'Bb': 10,
    'B': 11, 'B#': 0,  'Cb': 11
}

# Chromatic value of each key's tonic — no formula, no ambiguity
KEY_TONIC_CHROM = {
    'C': 0,  'G': 7,  'D': 2,  'A': 9,  'E': 4,
    'B': 11, 'F#': 6, 'Gb': 6, 'Db': 1, 'Ab': 8,
    'Eb': 3, 'Bb': 10,'F': 5
}

# Interval above tonic (semitones) → movable do syllable
INTERVAL_TO_MOVABLE_DO = {
    0:  'd',   # Tonic
    1:  'de',  # Raised tonic (chromatic)
    2:  'r',   # Supertonic
    3:  're',  # Raised supertonic (chromatic)
    4:  'm',   # Mediant
    5:  'f',   # Subdominant
    6:  'fe',  # Raised subdominant / tritone (chromatic)
    7:  's',   # Dominant
    8:  'se',  # Raised dominant (chromatic)
    9:  'l',   # Submediant
    10: 'le',  # Raised submediant (chromatic)
    11: 't',   # Leading tone
}

# Key-to-scale mapping (cycle of fourths/fifths style)
KEY_TO_SCALE = {
    'C':  ['C', 'D', 'E', 'F', 'G', 'A', 'B'],
    'G':  ['G', 'A', 'B', 'C', 'D', 'E', 'F#'],
    'D':  ['D', 'E', 'F#', 'G', 'A', 'B', 'C#'],
    'A':  ['A', 'B', 'C#', 'D', 'E', 'F#', 'G#'],
    'E':  ['E', 'F#', 'G#', 'A', 'B', 'C#', 'D#'],
    'B':  ['B', 'C#', 'D#', 'E', 'F#', 'G#', 'A#'],
    'F#': ['F#', 'G#', 'A#', 'B', 'C#', 'D#', 'E#'],
    'C#': ['C#', 'D#', 'E#', 'F#', 'G#', 'A#', 'B#'],
    'F':  ['F', 'G', 'A', 'Bb', 'C', 'D', 'E'],
    'Bb': ['Bb', 'C', 'D', 'Eb', 'F', 'G', 'A'],
    'Eb': ['Eb', 'F', 'G', 'Ab', 'Bb', 'C', 'D'],
    'Ab': ['Ab', 'Bb', 'C', 'Db', 'Eb', 'F', 'G'],
    'Db': ['Db', 'Eb', 'F', 'Gb', 'Ab', 'Bb', 'C'],
    'Gb': ['Gb', 'Ab', 'Bb', 'Cb', 'Db', 'Eb', 'F'],
    'B♭': ['Bb', 'C', 'D', 'Eb', 'F', 'G', 'A'],  # Alt spellings
    'E♭': ['Eb', 'F', 'G', 'Ab', 'Bb', 'C', 'D'],
    'A♭': ['Ab', 'Bb', 'C', 'Db', 'Eb', 'F', 'G'],
}

# SOLFA_SYLLABLES for display
SOLFA_SYLLABLES = ['d', 'r', 'm', 'f', 's', 'l', 't']

# Subscript and superscript Unicode mappings
SUBSCRIPT_MAP = {'0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅',
                 '6': '₆', '7': '₇', '8': '₈', '9': '₉'}
SUPERSCRIPT_MAP = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵',
                   '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'}
KEY_SIGS = {
    'C':0,'G':1,'D':2,'A':3,'E':4,'B':5,'F#':6,
    'Gb':-6,'Db':-5,'Ab':-4,'Eb':-3,'Bb':-2,'F':-1
}
FIFTHS_TO_KEY  = {v:k for k,v in KEY_SIGS.items()}
KEYS           = ['C','G','D','A','E','B','F#','Gb','Db','Ab','Eb','Bb','F']
TIME_SIGS      = ['2/4','3/4','4/4','6/8','9/8','12/8','2/2','3/8','5/4','7/8']
VOICE_NAMES    = {1:'Sop.',2:'Alto',3:'Ten.',4:'Bass'}
VOICE_NAMES_FULL = {1:'Soprano',2:'Alto',3:'Tenor',4:'Bass'}
NOTE_STEPS     = ['C','D','E','F','G','A','B']
DUR_TYPE_MAP   = {'whole':4.0,'half':2.0,'quarter':1.0,'eighth':0.5,
                  '16th':0.25,'32nd':0.125,'64th':0.0625,'breve':8.0}
SHARP_TREBLE_SLOTS = [4,7,3,6,2,5,1]
FLAT_TREBLE_SLOTS  = [6,3,7,4,8,5,9]
SHARP_BASS_SLOTS   = [6,9,5,8,4,7,3]
FLAT_BASS_SLOTS    = [8,5,9,6,10,7,11]

# Dynamics ordered list
DYNAMICS_LIST = ['pppp','ppp','pp','p','mp','mf','f','ff','fff','ffff',
                 'sf','sfz','sfp','fp','fz','rf','rfz','cresc.','dim.']

# Font settings for traditional solfa
SOLFA_FONT_FAMILY = "Times"  # Default font family
SOLFA_FONT_SIZE = 10         # Default font size
LYRIC_FONT_FAMILY = "Times"  # Font for lyrics
LYRIC_FONT_SIZE = 7          # Size for lyrics
ENGRAVER_FONTS = {
    'Times': 'Times',
    'Helvetica': 'Helvetica',
    'Courier': 'Courier',
    'Twi': 'Times',  # Placeholder, would need actual font
    'Cape Coast': 'Times'  # Placeholder
}

# Articulations
ARTICULATIONS = ['staccato','accent','tenuto','marcato','fermata',
                 'trill','mordent','turn','arpeggio','slur','tie']

# Special symbols for solfa
ORNAMENTS = ['~','tr','m','M','arp','^','v','<','>','(',')','-','—']

def _xml_escape(s:str)->str:
    return (s.replace('&','&amp;').replace('<','&lt;')
             .replace('>','&gt;').replace('"','&quot;'))

# Superscript/subscript for octave
def octave_mark(n:int)->str:
    """Return superscript for positive, subscript for negative octave offset."""
    if n == 0: return ''
    if n > 0:  return "'" * n          # e.g. d' = high do
    else:       return ',' * abs(n)    # e.g. d, = low do

# ═══════════════════════════════════════════════════════
#  DATA MODEL
# ═══════════════════════════════════════════════════════
@dataclass
class MusNote:
    pitch:       str   = 'C'
    octave:      int   = 4
    duration:    float = 1.0      # quarter-note beats
    dotted:      bool  = False
    rest:        bool  = False
    tied:        bool  = False
    lyric:       str   = ''
    dynamic:     str   = ''
    accidental:  str   = ''
    voice:       int   = 1
    special:     str   = ''       # slur, fermata, etc.
    articulation:str   = ''
    fingering:   str   = ''
    slur_start:  bool  = False
    slur_stop:   bool  = False
    x:           float = field(default=0.0, repr=False)
    y:           float = field(default=0.0, repr=False)

    @property
    def beats(self)->float:
        b = self.duration
        if self.dotted: b *= 1.5
        return b

    @property
    def midi_num(self)->int:
        base = NOTE_TO_CHROM.get(self.pitch.rstrip('#b'),0)
        if '#' in self.pitch: base += 1
        if 'b' in self.pitch: base -= 1
        return max(0,min(127, base+(self.octave+1)*12))

    def duration_underscores(self)->str:
        """Traditional solfa beam notation: quarter=none, half=one underline, whole=two."""
        d = self.beats
        if d >= 4.0: return ':-:-:-'      # double underline marker (whole)
        if d >= 3.0: return ':-:-'        # 3-beat (dotted half)
        if d >= 2.0: return ':-'          # single underline marker (half)
        if d >= 1.5: return ':-.'         # dotted quarter
        if d >= 1.0: return ':'           # quarter, no underline
        if d >= 0.75: return '.,'         # dotted eighth-ish
        if d >= 0.5: return '.'           # eighth
        if d >= 0.25: return ','          # sixteenth
        return ';'

    def solfa_syllable(self, key: str = 'C') -> str:
        """
        Return movable-do syllable relative to the given key tonic.
        Diatonic notes in any major key always produce d r m f s l t.
        Chromatic syllables only appear for genuinely non-diatonic pitches.
        """
        if self.rest:
            return '0'

        # Resolve pitch to chromatic number 0-11
        nc = PITCH_TO_CHROM.get(self.pitch)
        if nc is None:
            # Fallback for any unusual pitch string
            base = self.pitch.rstrip('#b')
            nc = NOTE_TO_CHROM.get(base, 0)
            if '#' in self.pitch: nc = (nc + 1) % 12
            if 'b' in self.pitch: nc = (nc - 1) % 12
            nc = nc % 12

        # Tonic chromatic value for this key
        tonic = KEY_TONIC_CHROM.get(key, 0)

        # Interval above tonic → movable do syllable
        interval = (nc - tonic) % 12
        return INTERVAL_TO_MOVABLE_DO.get(interval, '?')

    def solfa(self,key:str='C')->str:
        """Full solfa symbol with octave markers (subscripts/superscripts).
        Reference: C4-B4 = plain text, C3-B3 = subscript 1, C5-B5 = superscript 1, etc."""
        if self.rest:
            return '0'

        syl = self.solfa_syllable(key)
        
        # Octave-offset from reference octave (4 = C4-B4 as plain text)
        octave_offset = self.octave - 4
        
        if octave_offset < 0:
            # Subscript range: C3-B3 = 1, C2-B2 = 2, etc.
            num_str = str(abs(octave_offset))
            syl += ''.join(SUBSCRIPT_MAP.get(c, c) for c in num_str)
        elif octave_offset > 0:
            # Superscript range: C5-B5 = 1, C6-B6 = 2, etc.
            num_str = str(octave_offset)
            syl += ''.join(SUPERSCRIPT_MAP.get(c, c) for c in num_str)
        # octave_offset == 0 → no mark (plain)
        
        return syl

    def to_dict(self)->dict:
        return {'pitch':self.pitch,'octave':self.octave,'duration':self.duration,
                'dotted':self.dotted,'rest':self.rest,'tied':self.tied,
                'lyric':self.lyric,'dynamic':self.dynamic,
                'accidental':self.accidental,'voice':self.voice,
                'special':self.special,'articulation':self.articulation,
                'fingering':self.fingering,'slur_start':self.slur_start,
                'slur_stop':self.slur_stop}

    @classmethod
    def from_dict(cls,d:dict)->'MusNote':
        n=cls()
        for k,v in d.items():
            if hasattr(n,k) and k not in ('x','y'): setattr(n,k,v)
        return n


@dataclass
class Measure:
    notes:        List[MusNote] = field(default_factory=list)
    time_num:     int           = 4
    time_den:     int           = 4
    key_sig:      str           = 'C'
    clef:         str           = 'treble'
    tempo_bpm:    Optional[int] = None
    repeat_start: bool          = False
    repeat_end:   bool          = False
    double_bar:   bool          = False
    number:       int           = 1
    dynamic:      str           = ''
    rehearsal:    str           = ''   # rehearsal mark A B C...

    @property
    def beats_available(self)->float:
        return self.time_num*(4.0/self.time_den)

    def beats_used_for_voice(self,voice:int)->float:
        return sum(n.beats for n in self.notes if n.voice==voice)

    @property
    def beats_used(self)->float:
        voices = self.all_voices()
        if not voices: return 0.0
        return max(self.beats_used_for_voice(v) for v in voices) if voices else 0.0

    def voice_notes(self,voice:int)->List[MusNote]:
        return [n for n in self.notes if n.voice==voice]

    def all_voices(self)->List[int]:
        vs={n.voice for n in self.notes}
        return sorted(vs) if vs else []

    def to_dict(self)->dict:
        return {'notes':[n.to_dict() for n in self.notes],
                'time_num':self.time_num,'time_den':self.time_den,
                'key_sig':self.key_sig,'clef':self.clef,
                'tempo_bpm':self.tempo_bpm,'repeat_start':self.repeat_start,
                'repeat_end':self.repeat_end,'double_bar':self.double_bar,
                'number':self.number,'dynamic':self.dynamic,'rehearsal':self.rehearsal}

    @classmethod
    def from_dict(cls,d:dict)->'Measure':
        m=cls()
        m.notes=[MusNote.from_dict(nd) for nd in d.get('notes',[])]
        for k in ['time_num','time_den','key_sig','clef','tempo_bpm',
                  'repeat_start','repeat_end','double_bar','number','dynamic','rehearsal']:
            if k in d: setattr(m,k,d[k])
        return m


@dataclass
class Score:
    title:     str           = "Untitled"
    composer:  str           = ""
    lyricist:  str           = ""
    arranger:  str           = ""
    key_sig:   str           = "C"
    time_num:  int           = 4
    time_den:  int           = 4
    tempo_bpm: int           = 100
    clef:      str           = "treble"  # base clef for whole score (can be overridden per measure)
    measures:  List[Measure] = field(default_factory=list)

    def all_voices(self)->List[int]:
        vs:set=set()
        for m in self.measures:
            for n in m.notes: vs.add(n.voice)
        return sorted(vs) if vs else [1]

    def add_measure(self)->Measure:
        m=Measure(time_num=self.time_num,time_den=self.time_den,
                  key_sig=self.key_sig,clef=self.clef,number=len(self.measures)+1)
        self.measures.append(m); return m

    def ensure_measures(self,n:int=4):
        while len(self.measures)<n: self.add_measure()

    def to_dict(self)->dict:
        return {'title':self.title,'composer':self.composer,
                'lyricist':self.lyricist,'arranger':self.arranger,
                'key_sig':self.key_sig,'time_num':self.time_num,
                'time_den':self.time_den,'tempo_bpm':self.tempo_bpm,
                'clef':self.clef,'measures':[m.to_dict() for m in self.measures]}

    @classmethod
    def from_dict(cls,d:dict)->'Score':
        s=cls()
        for k in ['title','composer','lyricist','arranger','key_sig',
                  'time_num','time_den','tempo_bpm','clef']:
            if k in d: setattr(s,k,d[k])
        s.measures=[Measure.from_dict(md) for md in d.get('measures',[])]
        return s


# ═══════════════════════════════════════════════════════
#  CONVERSION ENGINE
# ═══════════════════════════════════════════════════════
class ConversionEngine:

    SOLFA_TO_CHROM={'d':0,'de':1,'ra':1,'r':2,'re':3,'ma':3,'m':4,
                    'f':5,'fe':6,'ba':6,'s':7,'se':8,'la':8,'l':9,
                    'le':10,'ta':10,'t':11}

    # ── MusicXML Import ───────────────────────────────
    @staticmethod
    def import_mxl(path:str)->Score:
        ext=os.path.splitext(path)[1].lower()
        if ext=='.mxl': return ConversionEngine._import_mxl_zip(path)
        return ConversionEngine._parse_xml_file(path)

    @staticmethod
    def _import_mxl_zip(path:str)->Score:
        with zipfile.ZipFile(path,'r') as z:
            names=z.namelist()
            root_file=None
            if 'META-INF/container.xml' in names:
                try:
                    ct=ET.fromstring(z.read('META-INF/container.xml').decode('utf-8',errors='replace'))
                    rf=(ct.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile')
                        or ct.find('.//rootfile'))
                    if rf is not None: root_file=rf.get('full-path')
                except: pass
            if root_file is None:
                for n in names:
                    if (n.endswith('.musicxml') or (n.endswith('.xml') and 'META' not in n)):
                        if not n.startswith('p') or not n[1:2].isdigit():
                            root_file=n; break
                if root_file is None:
                    for n in names:
                        if n.endswith('.musicxml') or (n.endswith('.xml') and 'META' not in n):
                            root_file=n; break
            if root_file and root_file in names:
                for enc in ['utf-8','utf-16','latin-1']:
                    try:
                        text=z.read(root_file).decode(enc,errors='replace').lstrip('\ufeff')
                        score=ConversionEngine._parse_xml_text(text)
                        vs=score.all_voices()
                        if len(vs)>=2 or any(m.notes for m in score.measures): return score
                    except: continue
            for n in names:
                if (n.endswith('.xml') or n.endswith('.musicxml')) and 'META' not in n:
                    try:
                        text=z.read(n).decode('utf-8',errors='replace').lstrip('\ufeff')
                        score=ConversionEngine._parse_xml_text(text)
                        if score.all_voices(): return score
                    except: continue
            raise ValueError("No parseable MusicXML in MXL archive.")

    @staticmethod
    def _parse_xml_file(path:str)->Score:
        for enc in ['utf-8','utf-16','latin-1','cp1252']:
            try:
                with open(path,'rb') as f: raw=f.read()
                text=raw.decode(enc,errors='replace').lstrip('\ufeff').replace('\x00','')
                return ConversionEngine._parse_xml_text(text)
            except ET.ParseError: continue
        raise ValueError("Could not parse MusicXML.")

    @staticmethod
    def _parse_xml_text(xml_text:str)->Score:
        score=Score()
        root=ET.fromstring(xml_text)
        wt=root.find('.//work-title'); mt=root.find('.//movement-title')
        if wt is not None and wt.text: score.title=wt.text.strip()
        elif mt is not None and mt.text: score.title=mt.text.strip()
        comp=root.find('.//creator[@type="composer"]')
        lyr=root.find('.//creator[@type="lyricist"]')
        if comp is not None and comp.text: score.composer=comp.text.strip()
        if lyr  is not None and lyr.text:  score.lyricist=lyr.text.strip()

        # ── Determine voice offset per part ────────────────────
        # Maps part id → integer offset added to all voice numbers in that part
        part_voice_offsets = {}
        score_parts = root.findall('.//score-part')
        for order, sp in enumerate(score_parts):
            pid  = sp.get('id', f'P{order+1}')
            name = ''
            ne   = sp.find('part-name')
            if ne is not None and ne.text: name = ne.text.strip().lower()
            # Derive voice base from part name; fall back to order
            if any(k in name for k in ('sop',)):
                offset = 0   # voice 1 → Soprano
            elif any(k in name for k in ('alt', 'alto')):
                offset = 1   # voice 1 → Alto
            elif any(k in name for k in ('ten', 'tenor')):
                offset = 2   # voice 1 → Tenor
            elif any(k in name for k in ('bas', 'bass')):
                offset = 3   # voice 1 → Bass
            else:
                offset = order  # generic fallback
            part_voice_offsets[pid] = offset

        multi_part = len(score_parts) > 1

        # ── Process each part ──────────────────────────────────
        parts = root.findall('part')
        if not parts:
            parts = root.findall('.//part')

        for part in parts:
            pid = part.get('id', 'P1')
            voice_offset = part_voice_offsets.get(pid, 0) if multi_part else 0

            cur_divs  = 1; cur_key = 'C'; cur_tnum = 4; cur_tden = 4
            cur_clef  = 'treble'; cur_tempo = 100
            cur_transpose_semitones = 0   # ← NEW: for tenor 8va-bassa clef

            for mel in part.findall('measure'):
                m_num = 1
                try: m_num = int(mel.get('number', '1'))
                except: pass

                # Ensure score has enough measures
                while len(score.measures) < m_num:
                    score.add_measure()
                m = score.measures[m_num - 1]

                for attr in mel.findall('attributes'):
                    d_el = attr.find('divisions')
                    if d_el is not None and d_el.text:
                        try: cur_divs = max(1, int(d_el.text))
                        except: pass
                    k_el = attr.find('key')
                    if k_el is not None:
                        fi = k_el.find('fifths')
                        if fi is not None and fi.text:
                            try: cur_key = FIFTHS_TO_KEY.get(int(fi.text), 'C')
                            except: pass
                    t_el = attr.find('time')
                    if t_el is not None:
                        be = t_el.find('beats'); bt = t_el.find('beat-type')
                        if be is not None and be.text:
                            try: cur_tnum = int(be.text)
                            except: pass
                        if bt is not None and bt.text:
                            try: cur_tden = int(bt.text)
                            except: pass
                    c_el = attr.find('clef')
                    if c_el is not None:
                        se = c_el.find('sign')
                        if se is not None and se.text:
                            sg = se.text.upper()
                            cur_clef = ('treble' if sg == 'G'
                                        else ('bass' if sg == 'F' else 'alto'))

                    # ── Transpose element (tenor 8va-bassa, etc.) ──
                    tr_el = attr.find('transpose')
                    if tr_el is not None:
                        ch_el = tr_el.find('chromatic')
                        if ch_el is not None and ch_el.text:
                            try: cur_transpose_semitones = int(ch_el.text)
                            except: cur_transpose_semitones = 0

                for snd in mel.findall('.//sound'):
                    t = snd.get('tempo')
                    if t:
                        try: cur_tempo = int(float(t))
                        except: pass

                m.time_num = cur_tnum; m.time_den = cur_tden
                m.key_sig  = cur_key;  m.clef     = cur_clef
                if m.tempo_bpm is None: m.tempo_bpm = cur_tempo

                for nel in mel.findall('note'):
                    n = MusNote()

                    # Voice number + per-part offset
                    v_el = nel.find('voice')
                    if v_el is not None and v_el.text:
                        try: n.voice = int(v_el.text) + voice_offset
                        except: pass

                    # Staff-based voice remapping (single-part grand staff only)
                    if not multi_part:
                        st_el = nel.find('staff')
                        if st_el is not None and st_el.text:
                            try:
                                st = int(st_el.text)
                                if st == 2 and n.voice <= 2:
                                    n.voice = n.voice + 2
                            except: pass

                    if nel.find('chord') is not None: continue

                    if nel.find('rest') is not None:
                        n.rest = True
                    else:
                        pe = nel.find('pitch')
                        if pe is not None:
                            step  = pe.findtext('step',  'C')
                            alter = pe.findtext('alter', '0')
                            octs  = pe.findtext('octave','4')
                            try: n.octave = int(octs)
                            except: n.octave = 4
                            try:
                                alt = int(float(alter))
                                n.pitch = step + ('#' if alt > 0 else ('b' if alt < 0 else ''))
                            except: n.pitch = step

                        # ── Apply transpose to get concert pitch ──────────
                        if cur_transpose_semitones != 0:
                            midi_n = n.midi_num + cur_transpose_semitones
                            midi_n = max(0, min(127, midi_n))
                            n.pitch  = CHROM_TO_NOTE.get(midi_n % 12, 'C')
                            n.octave = (midi_n // 12) - 1

                    te = nel.find('type')
                    if te is not None and te.text:
                        n.duration = DUR_TYPE_MAP.get(te.text.lower(), 1.0)
                    else:
                        de = nel.find('duration')
                        if de is not None and de.text:
                            try: n.duration = int(de.text) / cur_divs
                            except: pass
                    if nel.find('dot') is not None: n.dotted = True
                    for tie in nel.findall('tie'):
                        if tie.get('type') == 'start': n.tied = True
                    le = nel.find('lyric')
                    if le is not None:
                        txe = le.find('text')
                        if txe is not None and txe.text: n.lyric = txe.text.strip()

                    # ── Slur detection (see Issue 2) ─────────────────────
                    notations_el = nel.find('notations')
                    if notations_el is not None:
                        for slur_el in notations_el.findall('slur'):
                            stype = slur_el.get('type', '')
                            if stype == 'start':
                                n.slur_start = True
                            elif stype == 'stop':
                                n.slur_stop = True

                    m.notes.append(n)
        if not score.measures: score.ensure_measures(4)
        if score.measures:
            first=score.measures[0]
            score.key_sig=first.key_sig; score.time_num=first.time_num
            score.time_den=first.time_den; score.tempo_bpm=first.tempo_bpm or 100
            score.clef=first.clef
        return score

    # ── MIDI Import ───────────────────────────────────
    @staticmethod
    def import_midi(path:str)->Score:
        """Import MIDI file. Requires mido."""
        score=Score(title=os.path.splitext(os.path.basename(path))[0])
        if not MIDO_OK:
            messagebox.showwarning("MIDI Import","Install mido:\npip install mido")
            score.ensure_measures(4); return score
        try:
            mid=mido.MidiFile(path)
            tpb=mid.ticks_per_beat
            tempo=500000  # default 120 BPM
            notes_by_track=[]
            for i,track in enumerate(mid.tracks):
                events=[]; abs_tick=0
                pending:Dict[int,dict]={}
                cur_tempo=tempo
                for msg in track:
                    abs_tick+=msg.time
                    if msg.type=='set_tempo': cur_tempo=msg.tempo; tempo=msg.tempo
                    elif msg.type=='note_on' and msg.velocity>0:
                        pending[msg.note]={'tick':abs_tick,'vel':msg.velocity,'ch':msg.channel}
                    elif msg.type in ('note_off',) or (msg.type=='note_on' and msg.velocity==0):
                        if msg.note in pending:
                            start=pending.pop(msg.note)
                            dur_ticks=abs_tick-start['tick']
                            dur_beats=dur_ticks/tpb
                            midi_n=msg.note
                            oct_=(midi_n//12)-1
                            pitch=CHROM_TO_NOTE.get(midi_n%12,'C')
                            events.append({'pitch':pitch,'octave':oct_,
                                           'duration':dur_beats,
                                           'start_beat':start['tick']/tpb,
                                           'channel':start['ch']})
                if events: notes_by_track.append(events)
            if not notes_by_track:
                score.ensure_measures(4); return score
            # Determine time signature from score
            beats_per_measure=score.time_num*(4.0/score.time_den)
            # Build measures from track 0
            all_events=sorted([e for t in notes_by_track for e in t],
                              key=lambda x:x['start_beat'])
            if not all_events:
                score.ensure_measures(4); return score
            max_beat=max(e['start_beat']+e['duration'] for e in all_events)
            n_measures=max(4,math.ceil(max_beat/beats_per_measure))
            score.ensure_measures(n_measures)
            # Place notes
            channel_voice={0:1,1:2,2:3,3:4}
            for e in all_events:
                mi=int(e['start_beat']/beats_per_measure)
                if mi>=len(score.measures): continue
                m=score.measures[mi]
                voice=channel_voice.get(e['channel'],1)
                dur=e['duration']
                # Quantize to nearest standard duration
                std_durs=[4.0,2.0,1.5,1.0,0.75,0.5,0.25,0.125]
                dur=min(std_durs,key=lambda x:abs(x-dur))
                dotted=False
                if dur in (1.5,0.75,3.0): dotted=True; dur=dur/1.5
                n=MusNote(pitch=e['pitch'],octave=e['octave'],
                          duration=dur,dotted=dotted,voice=voice)
                m.notes.append(n)
        except Exception as ex:
            messagebox.showerror("MIDI Import Error",str(ex))
            score.ensure_measures(4)
        return score

    # ── WAV Import (metadata only) ────────────────────
    @staticmethod
    def import_wav(path:str)->Score:
        """Import WAV — creates placeholder score with metadata."""
        score=Score(title=os.path.splitext(os.path.basename(path))[0])
        if WAVE_OK:
            try:
                with wave.open(path,'r') as wf:
                    frames=wf.getnframes(); rate=wf.getframerate()
                    dur_sec=frames/rate
                    messagebox.showinfo("WAV Import",
                        f"WAV file: {os.path.basename(path)}\n"
                        f"Duration: {dur_sec:.1f}s\n"
                        f"Sample rate: {rate} Hz\n\n"
                        "Note: Direct pitch detection requires additional\n"
                        "libraries (aubio/librosa). A blank score has been\n"
                        "created — please add notes manually or use MIDI import.")
            except Exception as ex:
                messagebox.showerror("WAV Error",str(ex))
        score.ensure_measures(4)
        return score

    # ── Finale 2012/2014 Import ───────────────────────
    @staticmethod
    def import_finale(path:str)->Score:
        """
        Import Finale 2012/2014 files.
        .mus = proprietary binary (limited), .musx = ZIP with XML.
        Strategy: try to extract embedded MusicXML from musx/mus ZIP.
        """
        score=Score(title=os.path.splitext(os.path.basename(path))[0])
        ext=os.path.splitext(path)[1].lower()
        try:
            with zipfile.ZipFile(path,'r') as z:
                names=z.namelist()
                # Look for embedded XML
                xml_files=[n for n in names if
                           (n.endswith('.xml') or n.endswith('.musicxml'))
                           and 'META' not in n and 'metadata' not in n.lower()]
                if xml_files:
                    for xf in xml_files:
                        try:
                            text=z.read(xf).decode('utf-8',errors='replace')
                            s=ConversionEngine._parse_xml_text(text)
                            if s.measures and any(m.notes for m in s.measures):
                                s.title=score.title; return s
                        except: continue
                # Metadata from NotationMetadata.xml
                meta_names=[n for n in names if 'Metadata' in n or 'metadata' in n]
                for mn in meta_names:
                    try:
                        meta=ET.fromstring(z.read(mn).decode('utf-8',errors='replace'))
                        for elem in meta.iter():
                            tag=elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                            if 'title' in tag.lower() and elem.text:
                                score.title=elem.text.strip()
                            if 'key' in tag.lower() and elem.text and elem.text in KEYS:
                                score.key_sig=elem.text.strip()
                            if 'tempo' in tag.lower() and elem.text:
                                try: score.tempo_bpm=int(float(elem.text))
                                except: pass
                    except: continue
        except zipfile.BadZipFile:
            # Binary .mus file — can't parse without Finale SDK
            messagebox.showinfo("Finale Import",
                f"Binary Finale file detected ({ext}).\n\n"
                "For full import from Finale 2012/2014:\n"
                "1. Open in Finale\n"
                "2. File → Export → MusicXML\n"
                "3. Import the .xml here via File → Import MusicXML\n\n"
                "A blank score has been created with available metadata.")
        except Exception as ex:
            messagebox.showerror("Finale Import Error",str(ex))
        score.ensure_measures(4)
        return score

    @staticmethod
    def import_abc(path:str)->Score:
        import re
        score=Score(title=os.path.basename(path))
        for enc in ['utf-8','latin-1','cp1252']:
            try:
                with open(path,encoding=enc) as f: content=f.read()
                break
            except (UnicodeDecodeError,FileNotFoundError): continue
        else:
            score.ensure_measures(4); return score
        for line in content.split('\n'):
            line=line.strip()
            if   line.startswith('T:'): score.title=line[2:].strip()
            elif line.startswith('C:'): score.composer=line[2:].strip()
            elif line.startswith('K:'):
                k=line[2:].strip().split()[0]
                score.key_sig=k if k in KEYS else 'C'
            elif line.startswith('M:'):
                tp=line[2:].strip()
                if '/' in tp:
                    try:
                        a,b=tp.split('/'); score.time_num=int(a); score.time_den=int(b)
                    except: pass
            elif line.startswith('Q:'):
                mm=re.search(r'\d+',line[2:])
                if mm:
                    try: score.tempo_bpm=int(mm.group())
                    except: pass
        score.ensure_measures(4)
        return score

    # ── Export MusicXML ───────────────────────────────
    @staticmethod
    def export_musicxml(score:Score)->str:
        fifths=KEY_SIGS.get(score.key_sig,0)
        xml=[
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN"',
            '  "http://www.musicxml.org/dtds/partwise.dtd">',
            '<score-partwise version="3.1">',
            f'  <work><work-title>{_xml_escape(score.title)}</work-title></work>',
            '  <identification>',
            f'    <creator type="composer">{_xml_escape(score.composer)}</creator>',
            '    <encoding><software>Tonic Solfa Studio v6</software></encoding>',
            '  </identification>',
            '  <part-list><score-part id="P1"><part-name>Music</part-name></score-part></part-list>',
            '  <part id="P1">',
        ]
        for mi,meas in enumerate(score.measures):
            xml.append(f'    <measure number="{mi+1}">')
            if mi==0:
                xml+=[
                    '      <attributes>',
                    '        <divisions>4</divisions>',
                    f'        <key><fifths>{fifths}</fifths><mode>major</mode></key>',
                    f'        <time><beats>{meas.time_num}</beats><beat-type>{meas.time_den}</beat-type></time>',
                    '        <staves>2</staves>',
                    '        <clef number="1"><sign>G</sign><line>2</line></clef>',
                    '        <clef number="2"><sign>F</sign><line>4</line></clef>',
                    '      </attributes>',
                    f'      <direction><direction-type><metronome>'
                    f'<beat-unit>quarter</beat-unit><per-minute>{score.tempo_bpm}</per-minute>'
                    f'</metronome></direction-type></direction>',
                ]
            if meas.repeat_start:
                xml.append('      <barline location="left"><repeat direction="forward"/></barline>')
            if meas.dynamic:
                xml.append(f'      <direction placement="above"><direction-type>'
                           f'<dynamics><{meas.dynamic}/></dynamics></direction-type></direction>')
            for n in meas.notes:
                dur_div=max(1,int(round(n.duration*4)))
                if n.dotted: dur_div=int(dur_div*1.5)
                type_str={4:'whole',2:'half',1:'quarter',0.5:'eighth',
                          0.25:'16th',0.125:'32nd'}.get(n.duration,'quarter')
                staff_num='2' if n.voice>=3 else '1'
                xml.append('      <note>')
                if n.rest:
                    xml.append('        <rest/>')
                else:
                    step=n.pitch.rstrip('#b')
                    alter=1 if '#' in n.pitch else (-1 if 'b' in n.pitch else 0)
                    xml.append('        <pitch>')
                    xml.append(f'          <step>{step}</step>')
                    if alter: xml.append(f'          <alter>{alter}</alter>')
                    xml.append(f'          <octave>{n.octave}</octave>')
                    xml.append('        </pitch>')
                xml+=[
                    f'        <duration>{dur_div}</duration>',
                    f'        <voice>{n.voice}</voice>',
                    f'        <type>{type_str}</type>',
                    f'        <staff>{staff_num}</staff>',
                ]
                if n.dotted: xml.append('        <dot/>')
                if n.tied:   xml.append('        <tie type="start"/>')
                if n.dynamic:
                    xml.append(f'        <notations><dynamics><{n.dynamic}/></dynamics></notations>')
                if n.lyric:
                    xml+=['        <lyric number="1"><syllabic>single</syllabic>',
                          f'          <text>{_xml_escape(n.lyric)}</text></lyric>']
                xml.append('      </note>')
            if meas.repeat_end:
                xml.append('      <barline location="right">'
                           '<bar-style>light-heavy</bar-style>'
                           '<repeat direction="backward"/></barline>')
            xml.append('    </measure>')
        xml+=['  </part>','</score-partwise>']
        return '\n'.join(xml)

    @staticmethod
    def export_abc(score:Score)->str:
        def d2a(b):
            return {4:'4',2:'2',1:'',0.5:'/2',0.25:'/4'}.get(b,'')
        lines=['X:1',f'T:{score.title}',f'C:{score.composer}',
               f'M:{score.time_num}/{score.time_den}','L:1/4',
               f'Q:{score.tempo_bpm}',f'K:{score.key_sig}']
        abc=[]
        for meas in score.measures:
            mn=[]
            for n in meas.notes:
                if n.voice!=1: continue
                if n.rest: mn.append(f'z{d2a(n.duration)}'); continue
                p=n.pitch.rstrip('#b')
                acc='^' if '#' in n.pitch else ('_' if 'b' in n.pitch else '')
                if n.octave<=3: pn=acc+p.upper()+','*(4-n.octave)
                elif n.octave==4: pn=acc+p.upper()
                elif n.octave==5: pn=acc+p.lower()
                else: pn=acc+p.lower()+"'"*(n.octave-5)
                mn.append(pn+d2a(n.duration))
            abc.append(''.join(mn)+'|')
        lines.append(' '.join(abc))
        return '\n'.join(lines)

    @staticmethod
    def export_midi_bytes_harmony(score:Score)->bytes:
        voices=score.all_voices()
        if not voices: voices=[1]
        if MIDIUTIL_OK:
            midi=MIDIFile(len(voices))
            voice_progs={1:0,2:0,3:0,4:32}
            voice_vols={1:80,2:72,3:75,4:85}
            for ti,voice in enumerate(voices):
                channel=ti%16
                midi.addTempo(ti,0,score.tempo_bpm)
                midi.addProgramChange(ti,channel,0,voice_progs.get(voice,0))
                t=0.0
                for meas in score.measures:
                    notes=meas.voice_notes(voice)
                    if not notes:
                        t+=meas.beats_available; continue
                    for n in notes:
                        if not n.rest:
                            vel=voice_vols.get(voice,75)
                            if n.dynamic:
                                dmap={'pppp':20,'ppp':30,'pp':40,'p':50,'mp':60,
                                      'mf':70,'f':80,'ff':90,'fff':100,'ffff':110,
                                      'sf':95,'sfz':95,'sfp':85,'fp':75}
                                vel=dmap.get(n.dynamic,vel)
                            elif meas.dynamic:
                                dmap={'pppp':20,'ppp':30,'pp':40,'p':50,'mp':60,
                                      'mf':70,'f':80,'ff':90,'fff':100,'ffff':110}
                                vel=dmap.get(meas.dynamic,vel)
                            midi.addNote(ti,channel,n.midi_num,t,n.beats,vel)
                        t+=n.beats
            buf=io.BytesIO(); midi.writeFile(buf); return buf.getvalue()
        # Raw MIDI fallback
        tpb=480; tempo_us=int(60_000_000/max(1,score.tempo_bpm))
        def var_len(v):
            r=bytearray(); r.insert(0,v&0x7F); v>>=7
            while v: r.insert(0,(v&0x7F)|0x80); v>>=7
            return bytes(r)
        def make_track(voice,channel):
            ev=bytearray()
            ev+=b'\x00\xff\x51\x03'+struct.pack('>I',tempo_us)[1:]
            nm=(VOICE_NAMES_FULL.get(voice,'Voice')).encode('ascii','replace')[:20]
            ev+=b'\x00\xff\x03'+bytes([len(nm)])+nm
            for meas in score.measures:
                notes=meas.voice_notes(voice)
                if not notes:
                    ticks=int(meas.beats_available*tpb)
                    ev+=var_len(ticks)+bytes([0x90,0,0]); continue
                for n in notes:
                    ticks=int(n.beats*tpb)
                    if not n.rest:
                        mn=n.midi_num
                        ev+=var_len(0)+bytes([0x90|channel,mn,80])
                        ev+=var_len(ticks)+bytes([0x80|channel,mn,0])
                    else:
                        ev+=var_len(ticks)+bytes([0x90|channel,0,0])
            ev+=b'\x00\xff\x2f\x00'
            return b'MTrk'+struct.pack('>I',len(ev))+bytes(ev)
        tracks=[]
        for ti,voice in enumerate(voices): tracks.append(make_track(voice,ti%16))
        hdr=b'MThd'+struct.pack('>IHHH',6,1,len(tracks),tpb)
        return hdr+b''.join(tracks)

    @staticmethod
    def export_pdf_solfa_traditional(score:Score,path:str):
        """
        Export traditional tonic solfa to PDF, matching historical hymn-book style.
        Layout follows the uploaded reference images.
        """
        if not REPORTLAB_OK:
            txt=path.replace('.pdf','_solfa.txt')
            with open(txt,'w',encoding='utf-8') as f:
                f.write(ConversionEngine.export_solfa_text(score))
            messagebox.showinfo("PDF",
                f"ReportLab not installed. Saved as text:\n{txt}\npip install reportlab")
            return

        font_base = ENGRAVER_FONTS.get(SOLFA_FONT_FAMILY, "Times")
        lyric_font_base = ENGRAVER_FONTS.get(LYRIC_FONT_FAMILY, "Times")

        w,h=A4
        c=rl_canvas.Canvas(path,pagesize=A4)

        # Header
        c.setFont("Times-Bold",18)
        c.drawCentredString(w/2,h-18*mm,score.title.upper())
        c.setFont("Times-Roman",11)
        if score.composer:
            c.drawRightString(w-15*mm,h-18*mm,score.composer)
        c.setFont("Times-Roman",10)
        key_time=f"Key {score.key_sig}♭."
        c.drawString(15*mm,h-26*mm,key_time)
        time_sig=f"{score.time_num}/{score.time_den}"
        c.drawString(15*mm,h-31*mm,time_sig)
        if score.measures and score.measures[0].dynamic:
            c.setFont("Times-Italic",10)
            c.drawString(15*mm,h-36*mm,score.measures[0].dynamic)

        # Horizontal rule
        c.setLineWidth(0.5)
        c.line(15*mm,h-39*mm,w-15*mm,h-39*mm)

        y=h-45*mm
        voices=score.all_voices()
        mpr=4  # measures per row
        rows=math.ceil(len(score.measures)/mpr)
        col_w=(w-30*mm)/mpr
        voice_h=12*mm
        bar_num_shown=set()

        for row in range(rows):
            rm=score.measures[row*mpr:(row+1)*mpr]
            if not rm: break
            system_h=len(voices)*voice_h+6*mm

            if y-system_h<15*mm:
                c.showPage()
                y=h-18*mm
                c.setFont("Times-Bold",11)
                c.drawCentredString(w/2,y,score.title)
                y-=8*mm

            # Brace { on left
            brace_x=15*mm; brace_y=y-system_h+voice_h
            c.setLineWidth(1.5)
            c.line(brace_x,y,brace_x,y-len(voices)*voice_h)

            # Voice label + notes
            for vi,voice in enumerate(voices):
                vy=y-vi*voice_h
                # Voice label
                c.setFont("Times-Bold",9)
                lbl=VOICE_NAMES.get(voice,f'V{voice}')
                c.drawRightString(brace_x+13*mm,vy-voice_h/2+2,lbl)
                # Horizontal line
                c.setLineWidth(0.5)
                c.line(brace_x+14*mm,vy,w-15*mm,vy)
                # Measures
                for mi,meas in enumerate(rm):
                    mx=brace_x+14*mm+mi*col_w
                    # Bar number
                    abs_mn=meas.number
                    if abs_mn not in bar_num_shown and vi==0:
                        c.setFont("Times-Roman",6)
                        c.setFillColorRGB(0.35,0.25,0.12)
                        c.drawString(mx+1,vy+1,str(abs_mn))
                        bar_num_shown.add(abs_mn)
                    c.setFillColorRGB(0.08,0.06,0.02)

                    # Notes in this measure for this voice
                    vnotes=meas.voice_notes(voice)
                    if not vnotes:
                        c.setFont("Times-Roman",10)
                        c.drawCentredString(mx+col_w/2,vy-voice_h/2+2,'—')
                    else:
                        beat_unit=4.0/meas.time_den
                        n_beats=meas.time_num
                        beat_w=col_w/(n_beats+0.5)
                        # merge tied notes into previous note
                        render_notes=[]
                        for n in vnotes:
                            if (n.tied
                                    and render_notes
                                    and n.pitch == render_notes[-1].pitch
                                    and not n.slur_start
                                    and not n.slur_stop):
                                last=render_notes[-1]
                                last.duration += n.duration
                                last.dotted = last.dotted or n.dotted
                                last.tied = n.tied
                                last.special = (last.special+' '+n.special).strip()
                                # Do NOT merge slur boundary flags across tied notes
                                continue
                            render_notes.append(copy.copy(n))
                        pos=0.0
                        # Track slur underline state (initialise before the render_notes loop):
                        slur_pdf_x0  = None
                        slur_pdf_y   = vy - voice_h/2 - 2.0   # position underline below syllable baseline
                        for n in render_notes:
                            beat_idx=round(pos/beat_unit)
                            nx=mx+beat_idx*beat_w+beat_w*0.3
                            ny=vy-voice_h/2+2
                            syl=n.solfa(meas.key_sig)
                            # Underline for half/whole
                            ul=n.duration_underscores()
                            # Duration visual markers
                            c.setFont(font_base + "-Bold", SOLFA_FONT_SIZE)
                            c.setFillColorRGB(0.08,0.06,0.02)
                            c.drawString(nx,ny,syl)
                            sw=c.stringWidth(syl, font_base + "-Bold", SOLFA_FONT_SIZE)
                            if ul.startswith(':-:-:-'):
                                c.setLineWidth(0.6)
                                c.line(nx,ny-1.5,nx+sw,ny-1.5)
                                c.line(nx,ny-3,nx+sw,ny-3)
                            elif ul.startswith(':-:-'):
                                c.setLineWidth(0.6)
                                c.line(nx,ny-1.5,nx+sw,ny-1.5)
                                c.line(nx,ny-3.0,nx+sw,ny-3.0)
                                c.setFont(lyric_font_base + "-Roman", LYRIC_FONT_SIZE-1)
                                c.drawString(nx+sw+0.5,ny+6,'·')
                            elif ul.startswith(':-.'):
                                c.setLineWidth(0.6)
                                c.line(nx,ny-1.5,nx+sw,ny-1.5)
                                c.setFont(lyric_font_base + "-Roman", LYRIC_FONT_SIZE-1)
                                c.drawString(nx+sw+0.5,ny+6,'·')
                            elif ul.startswith(':-'):
                                c.setLineWidth(0.6)
                                c.line(nx,ny-1.5,nx+sw,ny-1.5)
                            elif ul=='.,':
                                c.setFont(lyric_font_base + "-Roman", LYRIC_FONT_SIZE-1)
                                c.drawString(nx+sw+0.5,ny+6,'·,')
                            elif ul=='.':
                                c.setFont(lyric_font_base + "-Roman", LYRIC_FONT_SIZE-1)
                                c.drawString(nx+sw+0.5,ny+6,'·')
                            elif ul==',':
                                c.setFont(lyric_font_base + "-Roman", LYRIC_FONT_SIZE-1)
                                c.drawString(nx+sw+0.5,ny+6,',')
                            # ── Slur underline ────────────────────────────────────────
                            if n.slur_start:
                                slur_pdf_x0 = nx

                            if slur_pdf_x0 is not None:
                                slur_x1 = nx + sw
                                c.setLineWidth(0.7)
                                c.setStrokeColorRGB(0.08, 0.06, 0.02)
                                c.line(slur_pdf_x0, slur_pdf_y, slur_x1, slur_pdf_y)

                            if n.slur_stop:
                                slur_pdf_x0 = None
                            # Tied
                            if n.tied:
                                c.setFont(font_base + "-Italic", SOLFA_FONT_SIZE-2)
                                c.drawString(nx+sw,ny,'~')
                            # Dynamic
                            if n.dynamic:
                                c.setFont("Times-Italic",7)
                                c.setFillColorRGB(0.55,0,0)
                                c.drawString(nx,ny-5,n.dynamic)
                                c.setFillColorRGB(0.08,0.06,0.02)
                            pos+=n.beats

                    # Barline
                    c.setLineWidth(0.8 if mi==len(rm)-1 else 0.5)
                    c.line(mx+col_w,vy,mx+col_w,vy-voice_h)
                    # Opening barline
                    if mi==0:
                        c.setLineWidth(0.5)
                        c.line(mx,vy,mx,vy-voice_h)

                # Lyric row (below voice 1 group for SA, below TB)
                if vi==0 and any(n.lyric for m2 in rm for n in m2.notes if n.voice==voice):
                    for mi,meas in enumerate(rm):
                        mx=brace_x+14*mm+mi*col_w
                        vnotes=meas.voice_notes(voice)
                        beat_unit=4.0/meas.time_den; pos=0.0
                        for n in vnotes:
                            if n.lyric:
                                beat_idx=round(pos/beat_unit)
                                beat_w=col_w/(meas.time_num+0.5)
                                nx=mx+beat_idx*beat_w+beat_w*0.3
                                c.setFont(lyric_font_base + "-Roman", LYRIC_FONT_SIZE)
                                c.setFillColorRGB(0.1,0.2,0.38)
                                c.drawString(nx,vy-voice_h-2,n.lyric)
                                c.setFillColorRGB(0.08,0.06,0.02)
                            pos+=n.beats

            # Bottom line of system
            c.setLineWidth(0.8)
            c.line(brace_x,y-len(voices)*voice_h,w-15*mm,y-len(voices)*voice_h)

            # Repeat signs
            for mi,meas in enumerate(rm):
                mx=brace_x+14*mm+mi*col_w
                if meas.repeat_start:
                    c.setLineWidth(2)
                    c.line(mx+2*mm,y,mx+2*mm,y-len(voices)*voice_h)
                    c.setLineWidth(0.5)
                    c.line(mx+3.5*mm,y,mx+3.5*mm,y-len(voices)*voice_h)
                    c.circle(mx+4.5*mm,y-len(voices)*voice_h*0.35,0.8*mm,fill=1)
                    c.circle(mx+4.5*mm,y-len(voices)*voice_h*0.65,0.8*mm,fill=1)
                if meas.repeat_end:
                    ex=mx+col_w
                    c.circle(ex-4.5*mm,y-len(voices)*voice_h*0.35,0.8*mm,fill=1)
                    c.circle(ex-4.5*mm,y-len(voices)*voice_h*0.65,0.8*mm,fill=1)
                    c.setLineWidth(0.5)
                    c.line(ex-3.5*mm,y,ex-3.5*mm,y-len(voices)*voice_h)
                    c.setLineWidth(2)
                    c.line(ex-2*mm,y,ex-2*mm,y-len(voices)*voice_h)

            y-=system_h+5*mm

        # Footer key legend
        if y>20*mm:
            lyric_font_base = ENGRAVER_FONTS.get(LYRIC_FONT_FAMILY, "Times")
            c.setFont(lyric_font_base + "-Roman", LYRIC_FONT_SIZE)
            c.setFillColorRGB(0.3,0.2,0.1)
            c.drawString(15*mm,15*mm,
                "d=Do  r=Re  m=Mi  f=Fa  s=Sol  l=La  t=Ti  "
                "ᶦ=high octave  ̲=low octave  —=held  0=rest  _=half  ==whole")
        c.save()

    @staticmethod
    def export_solfa_text(score:Score)->str:
        voices=score.all_voices()
        vnames={1:'Soprano/Melody',2:'Alto',3:'Tenor',4:'Bass'}
        lines=['═'*66,f'  {score.title}',
               f'  Composer: {score.composer}  Lyricist: {score.lyricist}',
               f'  Key: {score.key_sig}  Time: {score.time_num}/{score.time_den}  Tempo: ♩={score.tempo_bpm}',
               '═'*66,'TONIC SOLFA NOTATION  (Movable Do — SATB)','─'*66]
        for voice in voices:
            lines.append(f'\n  ── {vnames.get(voice,f"Voice {voice}")} ──')
            row,lyrs=[],[]
            for mi,meas in enumerate(score.measures):
                vnotes=meas.voice_notes(voice)
                if not vnotes:
                    cell=' | '.join(['·']*meas.time_num)
                else:
                    beat_unit=4.0/meas.time_den; pos=0.0
                    cells=['·']*meas.time_num
                    for n in vnotes:
                        bi=int(round(pos/beat_unit))
                        if bi<meas.time_num:
                            s=n.solfa(meas.key_sig)
                            ul=n.duration_underscores()
                            if ul=='_': s=s+'_'
                            elif ul=='=': s=s+'='
                            elif ul=='.': s=s+'.'
                            if n.tied: s=s+'~'
                            cells[bi]=s
                            held=int(round(n.beats/beat_unit))
                            for k in range(1,held):
                                if bi+k<meas.time_num: cells[bi+k]='—'
                        pos+=n.beats
                    cell=' | '.join(cells)
                row.append(f'|{meas.number:2d}| {cell} ')
                lyr=' '.join(n.lyric for n in vnotes if n.lyric)
                lyrs.append(f'|   | {lyr:<{len(cell)}}')
                if (mi+1)%4==0:
                    lines.append('  '+''.join(row)+'|')
                    if any(l.strip('| ') for l in lyrs):
                        lines.append('  '+''.join(lyrs)+'|')
                    row,lyrs=[],[]
                    lines.append('')
            if row:
                lines.append('  '+''.join(row)+'|')
                if any(l.strip('| ') for l in lyrs):
                    lines.append('  '+''.join(lyrs)+'|')
        lines+=['','─'*66,
                "KEY: d=Do r=Re m=Mi f=Fa s=Sol l=La t=Ti",
                "     chromatic: de/re/fe/se/le (sharp)  ra/ma/la/ta (flat)",
                "     ᶦ=high octave  ̲=low octave  —=held  0=rest",
                "     _=half note  ==whole note  .=eighth  :=semiquaver"]
        return '\n'.join(lines)


# ═══════════════════════════════════════════════════════
#  TRADITIONAL TONIC SOLFA CANVAS
#  Matches historical SATB hymn-book publications
#  Reference: uploaded images (images.jpg, tonic_image_5.jpg, tonic_image_6.jpg)
# ═══════════════════════════════════════════════════════
class TraditionalSolfaCanvas(tk.Canvas):
    MARGIN_L  = 12
    MARGIN_T  = 12
    KEY_W     = 60
    LABEL_W   = 40
    BRACE_W   = 6
    BEAT_W    = 30
    VOICE_H   = 28
    LYRIC_H   = 18
    ROW_GAP   = 22
    DEFAULT_MEASURES_PER_ROW = 4

    F_TITLE  = ('Times New Roman',18,'bold')
    F_SUB    = ('Times New Roman',10)
    F_KEY    = ('Times New Roman',10,'bold')
    F_VOICE  = ('Times New Roman',10,'bold')
    F_SYL    = ('Times New Roman',13,'bold')
    F_SEP    = ('Times New Roman',9)
    F_LYRIC  = ('Times New Roman',9)
    F_DYN    = ('Times New Roman',9,'italic')
    F_MNUM   = ('Times New Roman',7)
    F_UL     = ('Times New Roman',8)   # underline markers

    def __init__(self,master,score:Score,**kwargs):
        super().__init__(master,bg=PAPER_BG,bd=0,highlightthickness=0,**kwargs)
        self.score=score
        self.measures_per_row=self.DEFAULT_MEASURES_PER_ROW
        self.fit_to_width=True
        self.font_family='Times New Roman'
        self.font_scale=1.0
        self.row_gap=self.ROW_GAP
        self.beat_width=self.BEAT_W
        self.show_bar_numbers=True
        self.bind('<Configure>',lambda e:self.after_idle(self.redraw))

    def set_score(self,score:Score):
        self.score=score; self.redraw()

    def set_render_options(self,measures_per_row=None,fit_to_width=None,
                           row_gap=None,beat_width=None,
                           font_family=None,font_scale=None,show_bar_numbers=None):
        if measures_per_row is not None: self.measures_per_row=max(1,int(measures_per_row))
        if fit_to_width is not None:     self.fit_to_width=bool(fit_to_width)
        if row_gap is not None:          self.row_gap=int(row_gap)
        if beat_width is not None:       self.beat_width=int(beat_width)
        if font_family is not None:      self.font_family=str(font_family)
        if font_scale is not None:       self.font_scale=max(0.6,float(font_scale))
        if show_bar_numbers is not None: self.show_bar_numbers=bool(show_bar_numbers)
        self.redraw()

    def _font(self,base):
        if isinstance(base,tuple):
            name,size,*opts=base
            size=max(6,int(size*self.font_scale))
            return (self.font_family,size,*opts)
        if isinstance(base,int):
            return (self.font_family,int(base*self.font_scale))
        return base

    def redraw(self):
        self.delete('all')
        if not self.score or not self.score.measures:
            w=self.winfo_width() or 800
            self.create_text(w//2,120,
                text="No music loaded — import a file or add notes",
                fill=PAPER_LINE,font=('Times New Roman',13),anchor='center')
            return
        self._draw_page()

    def _draw_page(self):
        s=self.score; cw=self.winfo_width() or 900; y=self.MARGIN_T

        # Key/composer line
        y+=10
        self.create_text(self.MARGIN_L+4,y,
            text=f"Key {s.key_sig}.   {s.time_num}/{s.time_den}.",
            fill=PAPER_INK,font=self._font(self.F_KEY),anchor='w')
        if s.composer:
            self.create_text(cw-self.MARGIN_L-4,y,
                text=s.composer,fill=PAPER_INK,font=self._font(self.F_SUB),anchor='e')
        y+=18

        # Title
        self.create_text(cw//2,y,text=s.title.upper(),
            fill=PAPER_HEAD,font=self._font(self.F_TITLE),anchor='n')
        y+=24
        if s.lyricist:
            self.create_text(cw//2,y,text=s.lyricist,
                fill=PAPER_INK,font=self._font(self.F_SUB),anchor='n')
            y+=14
        y+=6

        # Divider
        self.create_line(self.MARGIN_L,y,cw-self.MARGIN_L,y,fill=PAPER_LINE,width=1)
        y+=6

        all_vs=s.all_voices()
        beat_num=s.time_num
        base_meas_w=beat_num*self.beat_width+10
        avail_w=cw-self.MARGIN_L-self.KEY_W-self.LABEL_W-self.BRACE_W-10
        if self.fit_to_width:
            mpr=min(max(1,self.measures_per_row),max(1,avail_w//base_meas_w))
        else:
            mpr=max(1,self.measures_per_row)
        has_lyr=any(n.lyric for mm in s.measures for n in mm.notes)

        rows=math.ceil(len(s.measures)/mpr)
        for row in range(rows):
            row_meas=s.measures[row*mpr:(row+1)*mpr]
            y=self._draw_system(y,row_meas,all_vs,s,has_lyr,cw)
            y+=self.row_gap

        self.configure(scrollregion=(0,0,cw,y+20))

    def _draw_system(self,y0,measures,voices,score,has_lyr,cw):
        upper=[v for v in voices if v<=2]
        lower=[v for v in voices if v>2]
        groups=[]
        if upper: groups.append(upper)
        if lower: groups.append(lower)
        if not groups: groups=[[1]]

        x_key=self.MARGIN_L
        x_label=x_key+self.KEY_W
        x_music=x_label+self.LABEL_W+self.BRACE_W

        if measures:
            meas_w=measures[0].time_num*self.beat_width+10
        else:
            meas_w=score.time_num*self.beat_width+10
        total_w=len(measures)*meas_w
        x_end=x_music+total_w
        y=y0

        for gi,group in enumerate(groups):
            gh=len(group)*self.VOICE_H

            # Brace [
            bx=x_label+self.LABEL_W
            self.create_line(bx,y,bx,y+gh,fill=PAPER_BAR,width=3)
            self.create_line(bx,y,bx+self.BRACE_W,y,fill=PAPER_BAR,width=2)
            self.create_line(bx,y+gh,bx+self.BRACE_W,y+gh,fill=PAPER_BAR,width=2)

            # Top rule
            self.create_line(x_music,y,x_end,y,fill=PAPER_LINE,width=1)

            for vi,voice in enumerate(group):
                vy=y+vi*self.VOICE_H
                vy_mid=vy+self.VOICE_H//2

                # Voice label
                lbl=VOICE_NAMES.get(voice,f'V{voice}')
                self.create_text(x_label+self.LABEL_W-4,vy_mid,
                    text=lbl,fill=PAPER_VOICE,font=self._font(self.F_VOICE),anchor='e')

                # Row bottom line
                self.create_line(x_music,vy+self.VOICE_H,x_end,vy+self.VOICE_H,
                    fill=PAPER_LINE,width=1)
                # Opening barline
                self.create_line(x_music,vy,x_music,vy+self.VOICE_H,fill=PAPER_BAR,width=1)

                mx=x_music
                for mi,meas in enumerate(measures):
                    # Bar number (above first voice of each group)
                    if vi==0 and self.show_bar_numbers:
                        self.create_text(mx+3,vy-1,
                            text=str(meas.number),
                            fill=PAPER_BARNUM,font=self._font(self.F_MNUM),anchor='nw')
                    # Dynamic for measure
                    if meas.dynamic and vi==0:
                        self.create_text(mx+3,vy+3,
                            text=meas.dynamic,fill=PAPER_DYN,font=self._font(self.F_DYN),anchor='nw')
                    self._draw_measure_row(mx,vy,meas,voice,meas.key_sig,meas_w)
                    mx+=meas_w

            # Closing double barline
            self.create_line(x_end,y,x_end,y+gh,fill=PAPER_BAR,width=2)

            y+=gh

            # Lyrics row below SA group
            if gi==0 and has_lyr and upper:
                mx=x_music
                for meas in measures:
                    self._draw_lyrics_row(mx,y+3,meas,upper[0],meas_w)
                    mx+=meas_w
                y+=self.LYRIC_H

            if gi<len(groups)-1:
                y+=max(12,int(self.row_gap*0.55))

        return y

    def _draw_measure_row(self,x,vy,meas,voice,key,meas_w):
        beat_num=meas.time_num
        vy_mid=vy+self.VOICE_H//2
        bw=self.beat_width
        beat_unit=4.0/meas.time_den
        vnotes=meas.voice_notes(voice)

        # Build a direct beat-position → note mapping for slur tracking
        beat_note_map = {}
        pos = 0.0
        for n in vnotes:
            bi = int(round(pos / beat_unit))
            if bi < beat_num:
                beat_note_map[bi] = n
            pos += n.beats

        # Build beat grid
        grid_syls=['·']*beat_num
        grid_dur =['']  *beat_num
        grid_tie =[False]*beat_num
        grid_dyn =['']  *beat_num

        pos=0.0
        for n in vnotes:
            bi=int(round(pos/beat_unit))
            if bi>=beat_num: break
            if n.rest:
                grid_syls[bi]='0'
            else:
                grid_syls[bi]=n.solfa(key)
                grid_dur[bi]=n.duration_underscores()
                grid_tie[bi]=n.tied
                grid_dyn[bi]=n.dynamic or ''
            held=int(round(n.beats/beat_unit))
            for k in range(1,held):
                if bi+k<beat_num:
                    grid_syls[bi+k]='—'
            pos+=n.beats

        slur_underline_x0 = None   # x start of current slur underline
        slur_underline_y  = vy_mid + int(11 * self.font_scale)

        for bi,sym in enumerate(grid_syls):
            bx=x+bi*bw
            bx_mid=bx+bw//2+(1 if bi>0 else 0)
            note   = beat_note_map.get(bi)

            # Beat separator '|' between beats (traditional style from images)
            if bi>0:
                sep_x=bx-1
                self.create_text(sep_x,vy_mid,text=':',
                    fill=PAPER_LINE,font=self._font(self.F_SEP),anchor='center')

            # Syllable
            if sym=='·' or sym=='':
                pass  # empty beat, show nothing
            elif sym=='—':
                self.create_text(bx_mid,vy_mid,text='—',
                    fill=PAPER_LINE,font=self._font(self.F_SEP),anchor='center')
            elif sym=='0':
                # Rest: traditional solfa uses 0 for rest
                self.create_text(bx_mid,vy_mid,text='0',
                    fill=PAPER_LINE,font=self._font(self.F_SYL),anchor='center')
            else:
                # Draw syllable
                item=self.create_text(bx_mid,vy_mid,text=sym,
                    fill=PAPER_INK,font=self._font(self.F_SYL),anchor='center')

                # Underlines for duration
                ul=grid_dur[bi]
                if ul.startswith(':-:-:-'):
                    tw = int(len(sym) * 7 * self.font_scale)
                    lx0 = bx_mid - tw // 2; lx1 = bx_mid + tw // 2
                    self.create_line(lx0, vy_mid + 9,  lx1, vy_mid + 9,  fill=PAPER_INK, width=1)
                    self.create_line(lx0, vy_mid + 12, lx1, vy_mid + 12, fill=PAPER_INK, width=1)
                elif ul.startswith(':-:-') or ul.startswith(':-:'):
                    tw = int(len(sym) * 7 * self.font_scale)
                    lx0 = bx_mid - tw // 2; lx1 = bx_mid + tw // 2
                    self.create_line(lx0, vy_mid + 9,  lx1, vy_mid + 9,  fill=PAPER_INK, width=1)
                    self.create_line(lx0, vy_mid + 12, lx1, vy_mid + 12, fill=PAPER_INK, width=1)
                    self.create_text(bx_mid + len(sym) * 4, vy_mid - 10, text='·',
                        fill=PAPER_INK, font=self._font(self.F_UL), anchor='center')
                elif ul.startswith(':-'):
                    tw = int(len(sym) * 7 * self.font_scale)
                    lx0 = bx_mid - tw // 2; lx1 = bx_mid + tw // 2
                    self.create_line(lx0, vy_mid + 9, lx1, vy_mid + 9, fill=PAPER_INK, width=1)
                elif ul in ('.', '.,'):
                    self.create_text(bx_mid + len(sym) * 4, vy_mid - 10, text='·',
                        fill=PAPER_INK, font=self._font(self.F_UL), anchor='center')
                elif ul == ',':
                    self.create_text(bx_mid + len(sym) * 4, vy_mid - 10, text=',',
                        fill=PAPER_INK, font=self._font(self.F_UL), anchor='center')

                # ── Slur underline (tonic solfa convention) ────────────────
                if note is not None:
                    if note.slur_start:
                        slur_underline_x0 = bx_mid - int(len(sym) * 3 * self.font_scale)

                    if slur_underline_x0 is not None:
                        # Extend underline to end of this syllable
                        slur_x1 = bx_mid + int(len(sym) * 4 * self.font_scale)
                        self.create_line(
                            slur_underline_x0, slur_underline_y,
                            slur_x1, slur_underline_y,
                            fill=PAPER_INK, width=1
                        )

                    if note.slur_stop:
                        slur_underline_x0 = None   # close the underline

                # Tie mark
                if grid_tie[bi]:
                    self.create_text(bx_mid+len(sym)*4+4,vy_mid,text='~',
                        fill=PAPER_DYN,font=('Courier New',8),anchor='w')

                # Note-level dynamic
                if grid_dyn[bi]:
                    self.create_text(bx_mid,vy_mid-12,text=grid_dyn[bi],
                        fill=PAPER_DYN,font=self._font(self.F_DYN),anchor='center')

        # Closing barline
        self.create_line(x+beat_num*bw+4,vy,x+beat_num*bw+4,vy+self.VOICE_H,
            fill=PAPER_BAR,width=1)

        # Repeat signs
        if meas.repeat_start:
            self.create_line(x+2,vy,x+2,vy+self.VOICE_H,fill=PAPER_BAR,width=2)
            self.create_line(x+5,vy,x+5,vy+self.VOICE_H,fill=PAPER_BAR,width=1)
            self.create_oval(x+7,vy+self.VOICE_H//3-3,x+11,vy+self.VOICE_H//3+3,fill=PAPER_BAR)
            self.create_oval(x+7,vy+2*self.VOICE_H//3-3,x+11,vy+2*self.VOICE_H//3+3,fill=PAPER_BAR)
        if meas.repeat_end:
            ex=x+beat_num*bw+4
            self.create_oval(ex-11,vy+self.VOICE_H//3-3,ex-7,vy+self.VOICE_H//3+3,fill=PAPER_BAR)
            self.create_oval(ex-11,vy+2*self.VOICE_H//3-3,ex-7,vy+2*self.VOICE_H//3+3,fill=PAPER_BAR)
            self.create_line(ex-5,vy,ex-5,vy+self.VOICE_H,fill=PAPER_BAR,width=1)
            self.create_line(ex-2,vy,ex-2,vy+self.VOICE_H,fill=PAPER_BAR,width=2)

    def _draw_lyrics_row(self,x,ly,meas,voice,meas_w):
        vnotes=meas.voice_notes(voice) or meas.notes
        beat_unit=4.0/meas.time_den; bw=self.beat_width; pos=0.0
        for n in vnotes:
            if n.lyric:
                bi=min(meas.time_num-1,int(round(pos/beat_unit)))
                bx=x+bi*bw+bw//2
                self.create_text(bx,ly+self.LYRIC_H//2,
                    text=n.lyric,fill=PAPER_LYRIC,font=self._font(self.F_LYRIC),anchor='center')
            pos+=n.beats


# ═══════════════════════════════════════════════════════
#  STAFF NOTATION CANVAS  (editable)
# ═══════════════════════════════════════════════════════
class StaffCanvas(tk.Canvas):
    LG=10; MARG_L=110; MARG_T=90; MARG_R=30
    MEAS_W=200; SYS_GAP=85; NR=5; STEM_H=32; STAFF_LINES=5

    def __init__(self,master,score:Score,on_change=None,on_select=None,**kwargs):
        super().__init__(master,bg=DARK,bd=0,highlightthickness=0,**kwargs)
        self.score=score; self.on_change=on_change; self.on_select=on_select
        self.tool='select'; self.cur_dur=1.0; self.cur_voice=1; self.cur_acc=''
        self.sel_m=-1; self.sel_n=-1; self.cur_dotted=False
        self.bind('<Button-1>',self._click)
        self.bind('<Button-3>',self._context_menu)
        self.bind('<Configure>',lambda e:self.after_idle(self.redraw))

    def set_score(self,s:Score):
        self.score=s; self.redraw()

    def redraw(self):
        self.delete('all')
        if not self.score: return
        cw=self.winfo_width() or 900
        self._draw_score(cw)

    def _mpr(self,cw):
        return max(1,(cw-self.MARG_L-self.MARG_R)//self.MEAS_W)

    def _sys_h(self):
        return (self.STAFF_LINES-1)*self.LG+8*self.LG+(self.STAFF_LINES-1)*self.LG

    def _treble_top(self,sy): return sy
    def _bass_top(self,sy):   return sy+(self.STAFF_LINES-1)*self.LG+8*self.LG

    def _draw_score(self,cw):
        s=self.score; mpr=self._mpr(cw)
        rows=math.ceil(max(1,len(s.measures))/mpr); sy=self.MARG_T
        self.create_text(cw//2,18,text=s.title,fill=WHITE,font=('Georgia',14,'bold'),anchor='n')
        self.create_text(cw//2,38,text=s.composer,fill=MUTED,font=('Georgia',10),anchor='n')
        for row in range(rows):
            rm=s.measures[row*mpr:(row+1)*mpr]
            if not rm: break
            self._draw_system(sy,rm,s,row,cw)
            sy+=self._sys_h()+self.SYS_GAP
        self.configure(scrollregion=(0,0,cw,sy+40))

    def _draw_system(self,sy,measures,score,row_idx,cw):
        t_top=self._treble_top(sy); b_top=self._bass_top(sy)
        s_h=(self.STAFF_LINES-1)*self.LG
        row_end=self.MARG_L+len(measures)*self.MEAS_W

        # Bracket
        bx=self.MARG_L-14
        self.create_line(bx,t_top,bx,b_top+s_h,fill=WHITE,width=4)
        self.create_arc(bx-4,t_top-4,bx+6,t_top+10,start=270,extent=90,
            outline=WHITE,width=2,style='arc')
        self.create_arc(bx-4,b_top+s_h-10,bx+6,b_top+s_h+4,start=180,extent=90,
            outline=WHITE,width=2,style='arc')

        # Staff lines
        for li in range(self.STAFF_LINES):
            self.create_line(self.MARG_L,t_top+li*self.LG,row_end,t_top+li*self.LG,
                fill=STAFF_LINE_COL,width=1)
            self.create_line(self.MARG_L,b_top+li*self.LG,row_end,b_top+li*self.LG,
                fill=STAFF_LINE_COL,width=1)

        self.create_line(self.MARG_L,t_top,self.MARG_L,b_top+s_h,fill=WHITE,width=1)
        self.create_text(self.MARG_L-62,t_top+self.LG*1.5,text='𝄞',fill=WHITE,font=('Arial',42),anchor='center')
        self.create_text(self.MARG_L-62,b_top+self.LG*0.8,text='𝄢',fill=WHITE,font=('Arial',28),anchor='center')

        kx=self.MARG_L+4
        if row_idx==0 and measures:
            kx=self._draw_key_sig(kx,t_top,b_top,score.key_sig)
            kx=self._draw_time_sig(kx,t_top,b_top,score.time_num,score.time_den)

        for mi,meas in enumerate(measures):
            abs_idx=self._find_abs_idx(meas)
            mx=self.MARG_L+mi*self.MEAS_W
            self._draw_measure(mx,t_top,b_top,meas,abs_idx)

        self.create_line(row_end,t_top,row_end,b_top+s_h,fill=WHITE,width=2)

    def _find_abs_idx(self,meas):
        for i,m in enumerate(self.score.measures):
            if m is meas: return i
        return -1

    def _draw_key_sig(self,x,t_top,b_top,key_name)->int:
        fifths=KEY_SIGS.get(key_name,0)
        if fifths==0: return x
        is_sharp=fifths>0; sym='♯' if is_sharp else '♭'
        slots_t=SHARP_TREBLE_SLOTS if is_sharp else FLAT_TREBLE_SLOTS
        slots_b=SHARP_BASS_SLOTS   if is_sharp else FLAT_BASS_SLOTS
        for i in range(abs(fifths)):
            ty=t_top+slots_t[i]*(self.LG/2)
            by=b_top+slots_b[i]*(self.LG/2)
            self.create_text(x+i*9+4,ty,text=sym,fill=GOLD,font=('Arial',11))
            self.create_text(x+i*9+4,by,text=sym,fill=GOLD,font=('Arial',11))
        return x+abs(fifths)*9+12

    def _draw_time_sig(self,x,t_top,b_top,num,den)->int:
        t_mid=t_top+(self.STAFF_LINES-1)*self.LG/2
        b_mid=b_top+(self.STAFF_LINES-1)*self.LG/2
        for mid in [t_mid,b_mid]:
            self.create_text(x+10,mid-self.LG*0.8,text=str(num),
                fill=WHITE,font=('Arial',16,'bold'),anchor='center')
            self.create_text(x+10,mid+self.LG*0.8,text=str(den),
                fill=WHITE,font=('Arial',16,'bold'),anchor='center')
        return x+28

    def _note_y(self,top_y,pitch,octave,clef='treble')->float:
        p=pitch.rstrip('#b')
        if p not in NOTE_STEPS: p='C'
        si=NOTE_STEPS.index(p)
        if clef=='treble': ref_s,ref_o=NOTE_STEPS.index('F'),5
        else:              ref_s,ref_o=NOTE_STEPS.index('A'),3
        ref_abs=ref_o*7+ref_s; note_abs=octave*7+si
        slots=ref_abs-note_abs
        return top_y+slots*(self.LG/2)

    def _draw_measure(self,mx,t_top,b_top,meas,abs_m_idx):
        s_h=(self.STAFF_LINES-1)*self.LG; ex=mx+self.MEAS_W
        self.create_line(ex,t_top,ex,t_top+s_h,fill=STAFF_BAR_COL,width=1)
        self.create_line(ex,b_top,ex,b_top+s_h,fill=STAFF_BAR_COL,width=1)
        self.create_line(ex,t_top,ex,b_top+s_h,fill=STAFF_BAR_COL,width=1)
        if abs_m_idx==self.sel_m:
            self.create_rectangle(mx+2,t_top-6,ex-2,b_top+s_h+6,
                outline=BLUE,width=2,dash=(3,2))
        self.create_text(mx+3,t_top-10,text=str(meas.number),fill=MUTED,font=('Arial',7),anchor='w')

        if meas.dynamic:
            self.create_text(mx+4,t_top-2,text=meas.dynamic,
                fill=ACCENT,font=('Times New Roman',10,'italic'),anchor='w')

        if not meas.notes:
            self._draw_whole_rest(mx+self.MEAS_W//2,t_top+self.LG,t_top)
            self._draw_whole_rest(mx+self.MEAS_W//2,b_top+self.LG,b_top)
            return

        for voice in [1,2]:
            vnotes=meas.voice_notes(voice)
            if vnotes: self._draw_voice(mx,t_top,vnotes,voice,abs_m_idx,meas,'treble')
        for voice in [3,4]:
            vnotes=meas.voice_notes(voice)
            if vnotes: self._draw_voice(mx,b_top,vnotes,voice,abs_m_idx,meas,'bass')
        vs=meas.all_voices()
        if not vs: self._draw_voice(mx,t_top,meas.notes,1,abs_m_idx,meas,'treble')
        if meas.repeat_start: self._draw_repeat_bar(mx,t_top,b_top,s_h,'start')
        if meas.repeat_end:   self._draw_repeat_bar(ex,t_top,b_top,s_h,'end')

    def _draw_voice(self,mx,top_y,notes,voice,abs_m_idx,meas,clef):
        s_h=(self.STAFF_LINES-1)*self.LG; n_notes=len(notes)
        spacing=max(16,(self.MEAS_W-24)//max(n_notes,1))
        stem_up=voice in (1,3)
        for ni,n in enumerate(notes):
            nx=mx+14+ni*spacing; n.x=nx
            sel=(abs_m_idx==self.sel_m and ni==self.sel_n and n.voice==voice)
            col=NOTE_SEL if sel else NOTE_COL
            if n.rest:
                n.y=top_y+self.LG; self._draw_rest_sym(nx,top_y+self.LG,n.duration); continue
            ny=self._note_y(top_y,n.pitch,n.octave,clef); n.y=ny
            self._ledger_lines(nx,ny,top_y,s_h)
            open_head=(n.duration>=2.0)
            rw,rh=self.NR,int(self.NR*0.65)
            if open_head:
                self.create_oval(nx-rw,ny-rh,nx+rw,ny+rh,outline=col,fill=DARK,width=2)
            else:
                self.create_oval(nx-rw,ny-rh,nx+rw,ny+rh,outline=col,fill=col)
            if n.duration<4.0:
                if stem_up:
                    sx=nx+rw-1
                    self.create_line(sx,ny,sx,ny-self.STEM_H,fill=col,width=1.5)
                    if n.duration<=0.5:
                        flags=max(1,int(round(math.log2(1/n.duration)))-1)
                        for fi in range(flags):
                            fy=ny-self.STEM_H+fi*6
                            self.create_line(sx,fy,sx+10,fy+8,fill=col,width=1.5)
                else:
                    sx=nx-rw+1
                    self.create_line(sx,ny,sx,ny+self.STEM_H,fill=col,width=1.5)
                    if n.duration<=0.5:
                        flags=max(1,int(round(math.log2(1/n.duration)))-1)
                        for fi in range(flags):
                            fy=ny+self.STEM_H-fi*6
                            self.create_line(sx,fy,sx+10,fy-8,fill=col,width=1.5)
            if n.dotted:
                self.create_oval(nx+rw+3,ny-2,nx+rw+7,ny+2,fill=col,outline=col)
            if '#' in n.pitch:
                self.create_text(nx-rw-7,ny,text='♯',fill=GOLD,font=('Arial',9))
            elif 'b' in n.pitch:
                self.create_text(nx-rw-7,ny,text='♭',fill=GOLD,font=('Arial',9))
            if n.lyric:
                ly=top_y+s_h+14
                self.create_text(nx,ly,text=n.lyric,fill=GREEN,font=('Georgia',8),anchor='n')
            if n.dynamic:
                self.create_text(nx,top_y-10,text=n.dynamic,
                    fill=ACCENT,font=('Times New Roman',9,'italic'),anchor='s')
            # Articulation marks
            if n.articulation=='staccato':
                self.create_oval(nx-2,ny-(rh+6),nx+2,ny-(rh+2),fill=col,outline=col)
            elif n.articulation=='accent':
                self.create_text(nx,ny-rh-8,text='>',fill=col,font=('Arial',9))
            elif n.articulation=='tenuto':
                self.create_line(nx-4,ny-rh-6,nx+4,ny-rh-6,fill=col,width=1.5)
            elif n.articulation=='fermata':
                self.create_text(nx,ny-rh-12,text='𝄐',fill=col,font=('Arial',14))

    def _ledger_lines(self,nx,ny,top_y,s_h):
        lg=self.LG
        if ny<top_y-1:
            ld=top_y-lg
            while ld>=ny-2:
                self.create_line(nx-8,ld,nx+8,ld,fill=LEDGER_COL,width=1); ld-=lg
        if ny>top_y+s_h+1:
            ld=top_y+s_h+lg
            while ld<=ny+2:
                self.create_line(nx-8,ld,nx+8,ld,fill=LEDGER_COL,width=1); ld+=lg

    def _draw_rest_sym(self,rx,ry,duration):
        ch={4.0:'𝄻',2.0:'𝄼',1.0:'𝄽',0.5:'𝄾',0.25:'𝄿'}.get(duration,'𝄽')
        self.create_text(rx,ry,text=ch,fill=MUTED,font=('Arial',15),anchor='center')

    def _draw_whole_rest(self,rx,ry,top_y):
        self.create_rectangle(rx-8,ry-3,rx+8,ry+1,fill=MUTED,outline='')

    def _draw_repeat_bar(self,x,t_top,b_top,s_h,which):
        if which=='start':
            self.create_line(x,t_top,x,b_top+s_h,fill=WHITE,width=1)
            self.create_line(x+3,t_top,x+3,b_top+s_h,fill=WHITE,width=3)
            self.create_oval(x+7,t_top+s_h//3-3,x+11,t_top+s_h//3+3,fill=WHITE)
            self.create_oval(x+7,t_top+2*s_h//3-3,x+11,t_top+2*s_h//3+3,fill=WHITE)
        else:
            self.create_oval(x-11,t_top+s_h//3-3,x-7,t_top+s_h//3+3,fill=WHITE)
            self.create_oval(x-11,t_top+2*s_h//3-3,x-7,t_top+2*s_h//3+3,fill=WHITE)
            self.create_line(x-3,t_top,x-3,b_top+s_h,fill=WHITE,width=3)
            self.create_line(x,t_top,x,b_top+s_h,fill=WHITE,width=1)

    def _find_measure(self,x,y):
        cw=self.winfo_width() or 900; mpr=self._mpr(cw)
        for i,meas in enumerate(self.score.measures):
            row=i//mpr; col=i%mpr
            mx=self.MARG_L+col*self.MEAS_W
            sy=self.MARG_T+row*(self._sys_h()+self.SYS_GAP)
            t_top=self._treble_top(sy); b_top=self._bass_top(sy)
            s_h=(self.STAFF_LINES-1)*self.LG
            in_t=mx<=x<=mx+self.MEAS_W and t_top-20<=y<=t_top+s_h+20
            in_b=mx<=x<=mx+self.MEAS_W and b_top-20<=y<=b_top+s_h+20
            if in_t or in_b:
                clef='treble' if in_t else 'bass'
                sy_=t_top if in_t else b_top
                return i,meas,mx,sy_,clef
        return -1,None,0,0,'treble'

    def _click(self,event):
        x,y=event.x,event.y
        if   self.tool=='select': self._do_select(x,y)
        elif self.tool=='note':   self._do_place(x,y,rest=False)
        elif self.tool=='rest':   self._do_place(x,y,rest=True)
        elif self.tool=='erase':  self._do_erase(x,y)
        elif self.tool=='lyric':  self._do_lyric(x,y)
        elif self.tool=='dynamic':self._do_dynamic(x,y)

    def _do_select(self,x,y):
        self.sel_m=-1; self.sel_n=-1
        mi,meas,mx,_,clef=self._find_measure(x,y)
        if meas:
            self.sel_m=mi; self.sel_n=-1
            for ni,n in enumerate(meas.notes):
                if abs(n.x-x)<14:
                    self.sel_n=ni
                    if self.on_select: self.on_select(mi,ni)
                    break
        self.redraw()

    def _do_place(self,x,y,rest=False):
        mi,meas,mx,sy_,clef=self._find_measure(x,y)
        if meas is None:
            self.score.add_measure()
            if self.on_change: self.on_change()
            self.redraw(); return
        if rest:
            n=MusNote(rest=True,duration=self.cur_dur,voice=self.cur_voice,dotted=self.cur_dotted)
        else:
            cw=self.winfo_width() or 900
            row=mi//self._mpr(cw)
            rsy=self.MARG_T+row*(self._sys_h()+self.SYS_GAP)
            clef2='bass' if self.cur_voice>=3 else 'treble'
            top_ref=self._bass_top(rsy) if clef2=='bass' else self._treble_top(rsy)
            p,o=self._y_to_note(y,top_ref,clef2)
            p=p+self.cur_acc
            n=MusNote(pitch=p,octave=o,duration=self.cur_dur,voice=self.cur_voice,dotted=self.cur_dotted)

        # Check available space for THIS voice only
        voice_beats=meas.beats_used_for_voice(self.cur_voice)
        avail=meas.beats_available
        if voice_beats+n.beats<=avail+0.01:
            meas.notes.append(n)
            if self.on_change: self.on_change()
        else:
            messagebox.showinfo("Measure Full",
                f"Voice {VOICE_NAMES.get(self.cur_voice,'?')} is full in measure {meas.number}.\n"
                "Each voice fills independently. Add a measure or choose another voice.")
        self.redraw()

    def _do_erase(self,x,y):
        mi,meas,mx,_,clef=self._find_measure(x,y)
        if not meas: return
        for ni,n in enumerate(meas.notes):
            if abs(n.x-x)<14:
                meas.notes.pop(ni)
                if self.on_change: self.on_change()
                self.redraw(); return

    def _do_lyric(self,x,y):
        mi,meas,mx,_,clef=self._find_measure(x,y)
        if not meas: return
        for n in meas.notes:
            if abs(n.x-x)<14:
                lyr=simpledialog.askstring("Lyric",f"Syllable for {n.pitch}{n.octave}:",
                    initialvalue=n.lyric,parent=self)
                if lyr is not None:
                    n.lyric=lyr
                    if self.on_change: self.on_change()
                    self.redraw()
                return

    def _do_dynamic(self,x,y):
        mi,meas,mx,_,clef=self._find_measure(x,y)
        if not meas: return
        # Apply to measure
        win=tk.Toplevel(self,bg=PANEL); win.title("Set Dynamic"); win.geometry("300x160")
        win.transient(self); win.grab_set()
        tk.Label(win,text="Select Dynamic:",bg=PANEL,fg=GOLD,font=('Arial',10,'bold')).pack(pady=8)
        dv=tk.StringVar(value=meas.dynamic or 'mf')
        f=tk.Frame(win,bg=PANEL); f.pack()
        for i,d in enumerate(DYNAMICS_LIST):
            tk.Radiobutton(f,text=d,variable=dv,value=d,bg=PANEL,fg=GOLD,
                selectcolor=DARK,font=('Times',9,'italic')).grid(row=i//6,column=i%6,padx=3)
        def apply():
            meas.dynamic=dv.get()
            if self.on_change: self.on_change()
            self.redraw(); win.destroy()
        tk.Button(win,text="Apply",bg=ACCENT,fg=WHITE,relief='flat',command=apply).pack(pady=8)

    def _context_menu(self,event):
        mi,meas,mx,_,clef=self._find_measure(event.x,event.y)
        if meas is None: return
        menu=tk.Menu(self,tearoff=0,bg=PANEL,fg=TEXT,activebackground=CARD)
        menu.add_command(label='Edit Measure Key/Time',
            command=lambda m=meas:self._edit_measure_key_time(m))
        menu.add_command(label='Set Dynamic…',
            command=lambda:self._do_dynamic(event.x,event.y))
        menu.add_separator()
        menu.add_command(label='Toggle Repeat Start',
            command=lambda m=meas:self._toggle(m,'repeat_start'))
        menu.add_command(label='Toggle Repeat End',
            command=lambda m=meas:self._toggle(m,'repeat_end'))
        menu.add_command(label='Toggle Double Bar',
            command=lambda m=meas:self._toggle(m,'double_bar'))
        menu.add_separator()
        menu.add_command(label='Reset to Score Key/Time',
            command=lambda m=meas:self._reset_measure_key_time(m))
        menu.tk_popup(event.x_root,event.y_root)

    def _toggle(self,meas,attr):
        setattr(meas,attr,not getattr(meas,attr))
        if self.on_change: self.on_change()
        self.redraw()

    def _edit_measure_key_time(self,meas):
        key=simpledialog.askstring('Key Signature','Key (e.g. C, G, Bb, F#):',
            initialvalue=meas.key_sig,parent=self)
        if key is None: return
        time=simpledialog.askstring('Time Signature','Time (e.g. 4/4, 3/8):',
            initialvalue=f'{meas.time_num}/{meas.time_den}',parent=self)
        if time is None: return
        try:
            num,den=[int(x) for x in time.split('/')]
            if num<=0 or den not in (1,2,4,8,16): raise ValueError
        except:
            messagebox.showerror('Invalid','Time must be num/den (1,2,4,8,16).'); return
        meas.key_sig=key.strip(); meas.time_num=num; meas.time_den=den
        if self.on_change: self.on_change()
        self.redraw()

    def _reset_measure_key_time(self,meas):
        meas.key_sig=self.score.key_sig
        meas.time_num=self.score.time_num; meas.time_den=self.score.time_den
        if self.on_change: self.on_change()
        self.redraw()

    def _y_to_note(self,y,top_y,clef):
        if clef=='treble': ref_s,ref_o=NOTE_STEPS.index('F'),5
        else:              ref_s,ref_o=NOTE_STEPS.index('A'),3
        ref_abs=ref_o*7+ref_s; slot=(y-top_y)/(self.LG/2)
        note_abs=ref_abs-round(slot); oct_=note_abs//7; si=note_abs%7
        if si<0: si+=7; oct_-=1
        return NOTE_STEPS[si%7],max(0,min(8,int(oct_)))

    def get_selected_note(self):
        if 0<=self.sel_m<len(self.score.measures):
            m=self.score.measures[self.sel_m]
            if 0<=self.sel_n<len(m.notes):
                return m.notes[self.sel_n]
        return None


# ═══════════════════════════════════════════════════════
#  TOOL PALETTE  (Tonic Solfa specific palettes)
# ═══════════════════════════════════════════════════════
class SolfaPalette(tk.Frame):
    """
    Comprehensive tool palette for tonic solfa notation.
    Includes: Duration, Accidentals, Voice, Dynamics, Articulation,
    Ornaments, Special Symbols, Smart Entry.
    """
    def __init__(self,master,on_tool_change=None,on_dur_change=None,
                 on_voice_change=None,on_dyn_apply=None,on_art_apply=None,**kwargs):
        super().__init__(master,bg=PANEL,**kwargs)
        self.on_tool_change=on_tool_change
        self.on_dur_change=on_dur_change
        self.on_voice_change=on_voice_change
        self.on_dyn_apply=on_dyn_apply
        self.on_art_apply=on_art_apply

        self.tool_var=tk.StringVar(value='select')
        self.dur_var=tk.StringVar(value='1.0')
        self.voice_var=tk.IntVar(value=1)
        self.acc_var=tk.StringVar(value='')
        self.dot_var=tk.BooleanVar(value=False)
        self.dyn_var=tk.StringVar(value='mf')
        self.art_var=tk.StringVar(value='')
        self.smart_entry_var=tk.BooleanVar(value=False)

        self._build()

    def _section(self,title):
        f=tk.Frame(self,bg=CARD,height=22); f.pack(fill='x',pady=(5,0))
        f.pack_propagate(False)
        tk.Label(f,text=title,bg=CARD,fg=GOLD,font=('Arial',7,'bold')).pack(side='left',padx=6,pady=3)

    def _build(self):
        # ── Tools ──────────────────────────────────
        self._section("  TOOLS")
        tf=tk.Frame(self,bg=PANEL); tf.pack(fill='x',padx=4,pady=2)
        tools=[('↖ Select','select'),('♩ Note','note'),('𝄽 Rest','rest'),
               ('✕ Erase','erase'),('T Lyric','lyric'),('𝆑 Dynamic','dynamic')]
        for i,(lbl,val) in enumerate(tools):
            rb=tk.Radiobutton(tf,text=lbl,variable=self.tool_var,value=val,
                indicatoron=0,bg=DARK,fg=TEXT,selectcolor=ACCENT,
                activebackground=CARD,font=('Arial',8),padx=5,pady=3,
                command=lambda v=val:self._emit_tool(v))
            rb.grid(row=i//3,column=i%3,padx=1,pady=1,sticky='ew')
        tf.columnconfigure(0,weight=1); tf.columnconfigure(1,weight=1); tf.columnconfigure(2,weight=1)

        # ── Smart Entry ────────────────────────────
        sf=tk.Frame(self,bg=PANEL); sf.pack(fill='x',padx=4,pady=2)
        tk.Checkbutton(sf,text="Smart Entry (keyboard)",variable=self.smart_entry_var,
            bg=PANEL,fg=GREEN,selectcolor=DARK,font=('Arial',8,'bold'),
            command=self._toggle_smart).pack(side='left',padx=4)

        # ── Duration ───────────────────────────────
        self._section("  DURATION")
        df=tk.Frame(self,bg=PANEL); df.pack(fill='x',padx=4,pady=2)
        durs=[('𝅝 Whole','4.0'),('𝅗𝅥 Half','2.0'),('♩ Qtr','1.0'),
              ('♪ 8th','0.5'),('𝅘𝅥𝅯 16th','0.25'),('32nd','0.125')]
        for i,(lbl,val) in enumerate(durs):
            rb=tk.Radiobutton(df,text=lbl,variable=self.dur_var,value=val,
                indicatoron=0,bg=DARK,fg=GOLD,selectcolor=ACCENT,
                activebackground=CARD,font=('Arial',8),padx=4,pady=3,
                command=lambda v=val:self._emit_dur(v))
            rb.grid(row=i//3,column=i%3,padx=1,pady=1,sticky='ew')
        df.columnconfigure(0,weight=1); df.columnconfigure(1,weight=1); df.columnconfigure(2,weight=1)

        dotf=tk.Frame(self,bg=PANEL); dotf.pack(fill='x',padx=4,pady=1)
        tk.Checkbutton(dotf,text="Dotted",variable=self.dot_var,
            bg=PANEL,fg=TEXT,selectcolor=DARK,font=('Arial',8)).pack(side='left')

        # ── Accidentals ────────────────────────────
        self._section("  ACCIDENTALS")
        acf=tk.Frame(self,bg=PANEL); acf.pack(fill='x',padx=4,pady=2)
        for lbl,val in [('♮ Natural',''),('♯ Sharp','#'),('♭ Flat','b'),
                         ('𝄪 Dbl♯','##'),('𝄫 Dbl♭','bb')]:
            tk.Radiobutton(acf,text=lbl,variable=self.acc_var,value=val,
                bg=PANEL,fg=GOLD,selectcolor=DARK,font=('Arial',9)).pack(side='left',padx=2)

        # ── Voice ──────────────────────────────────
        self._section("  VOICE  (SATB)")
        vf=tk.Frame(self,bg=PANEL); vf.pack(fill='x',padx=4,pady=2)
        for lbl,val,col in [('S Soprano',1,ACCENT),('A Alto',2,BLUE),
                             ('T Tenor',3,GREEN),('B Bass',4,GOLD)]:
            rb=tk.Radiobutton(vf,text=lbl,variable=self.voice_var,value=val,
                indicatoron=0,bg=DARK,fg=col,selectcolor=CARD,
                activebackground=PANEL,font=('Arial',9,'bold'),padx=6,pady=3,
                command=lambda v=val:self._emit_voice(v))
            rb.pack(side='left',padx=2,pady=2)

        # ── Octave ─────────────────────────────────
        self._section("  OCTAVE")
        of=tk.Frame(self,bg=PANEL); of.pack(fill='x',padx=4,pady=2)
        tk.Label(of,text="Oct:",bg=PANEL,fg=MUTED,font=('Arial',8)).pack(side='left')
        self.oct_var=tk.IntVar(value=4)
        tk.Spinbox(of,from_=1,to=8,textvariable=self.oct_var,
            bg=DARK,fg=WHITE,relief='flat',font=('Arial',9),width=4).pack(side='left',padx=4)
        tk.Label(of,text="  d=Do  d'=high Do  d,=low Do",
            bg=PANEL,fg=MUTED,font=('Arial',7)).pack(side='left')

        # ── Dynamics ───────────────────────────────
        self._section("  DYNAMICS  (click to apply to selection)")
        dynf=tk.Frame(self,bg=PANEL); dynf.pack(fill='x',padx=4,pady=2)
        row1=['pppp','ppp','pp','p','mp','mf','f','ff','fff','ffff']
        row2=['sf','sfz','sfp','fp','fz','rf','rfz','cresc.','dim.','']
        for ri,row in enumerate([row1,row2]):
            rf=tk.Frame(dynf,bg=PANEL); rf.pack(fill='x')
            for d in row:
                if not d: continue
                b=tk.Button(rf,text=d,bg=DARK,fg=GOLD,relief='flat',
                    font=('Times New Roman',9,'italic'),padx=4,pady=2,
                    command=lambda dv=d:self._apply_dyn(dv))
                b.pack(side='left',padx=1,pady=1)
                _tooltip(b,f"Apply {d} dynamic")

        # ── Articulations ──────────────────────────
        self._section("  ARTICULATION")
        artf=tk.Frame(self,bg=PANEL); artf.pack(fill='x',padx=4,pady=2)
        arts=[('· Staccato','staccato'),('> Accent','accent'),('— Tenuto','tenuto'),
              ('^ Marcato','marcato'),('𝄐 Fermata','fermata'),('⌒ Slur','slur'),
              ('~ Tie','tie'),('tr Trill','trill'),('∼ Mordent','mordent')]
        for i,(lbl,val) in enumerate(arts):
            b=tk.Button(artf,text=lbl,bg=DARK,fg=TEXT,relief='flat',
                font=('Arial',8),padx=3,pady=2,
                command=lambda v=val:self._apply_art(v))
            b.grid(row=i//3,column=i%3,padx=1,pady=1,sticky='ew')
        artf.columnconfigure(0,weight=1); artf.columnconfigure(1,weight=1); artf.columnconfigure(2,weight=1)

        # ── Special Solfa Symbols ──────────────────
        self._section("  SOLFA SYMBOLS")
        symf=tk.Frame(self,bg=PANEL); symf.pack(fill='x',padx=4,pady=2)
        syms=[("d Do",'d'),("r Re",'r'),("m Mi",'m'),("f Fa",'f'),
              ("s Sol",'s'),("l La",'l'),("t Ti",'t'),
              ("d' Hi-Do",'hi'),("d, Lo-Do",'lo'),("0 Rest",'0'),
              ("— Held",'—')]
        for i,(lbl,val) in enumerate(syms):
            b=tk.Button(symf,text=lbl,bg=CARD,fg=PAPER_INK if 'Do' not in lbl else ACCENT,
                relief='flat',font=('Times New Roman',9,'bold'),padx=3,pady=2,
                command=lambda v=val:self._insert_sym(v))
            b.grid(row=i//4,column=i%4,padx=1,pady=1,sticky='ew')
        for c in range(4): symf.columnconfigure(c,weight=1)

        # ── Repeat Signs ───────────────────────────
        self._section("  BARLINES & REPEATS")
        repf=tk.Frame(self,bg=PANEL); repf.pack(fill='x',padx=4,pady=2)
        self.repeat_callbacks={}
        for lbl,val in [('||: Repeat Start','repeat_start'),(':|  Repeat End','repeat_end'),
                         ('||  Double Bar','double_bar'),('Fine','fine'),('D.C.','dc'),('D.S.','ds')]:
            b=tk.Button(repf,text=lbl,bg=DARK,fg=TEXT,relief='flat',
                font=('Arial',8),padx=4,pady=2)
            b.pack(side='left',padx=2,pady=2)
            self.repeat_callbacks[val]=b

    def _emit_tool(self,v):
        if self.on_tool_change: self.on_tool_change(v)

    def _emit_dur(self,v):
        if self.on_dur_change: self.on_dur_change(float(v))

    def _emit_voice(self,v):
        if self.on_voice_change: self.on_voice_change(v)

    def _apply_dyn(self,d):
        if self.on_dyn_apply: self.on_dyn_apply(d)

    def _apply_art(self,a):
        if self.on_art_apply: self.on_art_apply(a)

    def _insert_sym(self,v):
        pass  # handled by main app

    def _toggle_smart(self):
        pass  # handled by main app

    def get_params(self):
        return {
            'tool':    self.tool_var.get(),
            'duration': float(self.dur_var.get()),
            'voice':   self.voice_var.get(),
            'accidental': self.acc_var.get(),
            'dotted':  self.dot_var.get(),
            'octave':  self.oct_var.get(),
            'dynamic': self.dyn_var.get(),
            'articulation': self.art_var.get(),
            'smart_entry': self.smart_entry_var.get(),
        }


# ═══════════════════════════════════════════════════════
#  NOTE EDITOR PANEL
# ═══════════════════════════════════════════════════════
class NoteEditorPanel(tk.Frame):
    def __init__(self,master,score:Score,on_change=None,**kwargs):
        super().__init__(master,bg=PANEL,**kwargs)
        self.score=score; self.on_change=on_change
        self.sel=None; self.sel_m=-1; self.sel_n=-1
        self._build()

    def _build(self):
        tk.Label(self,text="Note Editor",bg=PANEL,fg=GOLD,
            font=('Arial',12,'bold')).pack(pady=10)
        self.info=tk.Label(self,text="Select a note on the staff",
            bg=CARD,fg=MUTED,font=('Arial',10),relief='raised',bd=1,padx=10,pady=8)
        self.info.pack(fill='x',padx=10,pady=5)

        def row(lbl):
            f=tk.Frame(self,bg=PANEL); f.pack(fill='x',padx=10,pady=2)
            tk.Label(f,text=lbl,bg=PANEL,fg=MUTED,font=('Arial',8),width=11,anchor='w').pack(side='left')
            return f

        r=row("Pitch:")
        self._pitch=tk.StringVar(value='C')
        for p in ['C','D','E','F','G','A','B']:
            tk.Radiobutton(r,text=p,variable=self._pitch,value=p,
                bg=PANEL,fg=TEXT,selectcolor=ACCENT,font=('Arial',9),
                command=self._apply).pack(side='left',padx=1)

        r=row("Octave:")
        self._oct=tk.IntVar(value=4)
        tk.Scale(r,from_=1,to=8,orient='horizontal',variable=self._oct,
            bg=CARD,fg=TEXT,troughcolor=DARK,
            command=lambda v:self._apply()).pack(fill='x',expand=True)

        r=row("Duration:")
        r.pack(fill='x',padx=10,pady=2)
        self._dur=tk.StringVar(value='1.0')
        drow=tk.Frame(self,bg=PANEL); drow.pack(fill='x',padx=10,pady=1)
        for sym,val in [('𝅝 Whole','4.0'),('𝅗𝅥 Half','2.0'),('♩ Qtr','1.0'),
                         ('♪ 8th','0.5'),('𝅘𝅥𝅯 16th','0.25')]:
            tk.Radiobutton(drow,text=sym,variable=self._dur,value=val,
                bg=PANEL,fg=TEXT,selectcolor=ACCENT,font=('Arial',8),
                command=self._apply).pack(side='left',padx=1)

        r=row("Accidental:")
        self._acc=tk.StringVar(value='')
        for sym,val in [('♮',''),('♯','#'),('♭','b')]:
            tk.Radiobutton(r,text=sym,variable=self._acc,value=val,
                bg=PANEL,fg=GOLD,selectcolor=DARK,font=('Arial',11),
                command=self._apply).pack(side='left')

        r=row("Voice:")
        self._voice=tk.IntVar(value=1)
        for lbl,v,c in [('S',1,ACCENT),('A',2,BLUE),('T',3,GREEN),('B',4,GOLD)]:
            tk.Radiobutton(r,text=lbl,variable=self._voice,value=v,
                bg=PANEL,fg=c,selectcolor=DARK,font=('Arial',9,'bold'),
                command=self._apply).pack(side='left',padx=2)

        r=row("Dynamic:")
        self._dyn=tk.StringVar(value='')
        dynf=tk.Frame(self,bg=PANEL); dynf.pack(fill='x',padx=10,pady=1)
        for d in ['','pp','p','mp','mf','f','ff','sf','sfz']:
            tk.Radiobutton(dynf,text=d or '(none)',variable=self._dyn,value=d,
                bg=PANEL,fg=GOLD,selectcolor=DARK,font=('Times',8,'italic'),
                command=self._apply).pack(side='left',padx=2)

        r=row("Articulation:")
        self._art=tk.StringVar(value='')
        artf=tk.Frame(self,bg=PANEL); artf.pack(fill='x',padx=10,pady=1)
        for a in ['','staccato','accent','tenuto','marcato','fermata']:
            tk.Radiobutton(artf,text=a or '(none)',variable=self._art,value=a,
                bg=PANEL,fg=TEXT,selectcolor=DARK,font=('Arial',8),
                command=self._apply).pack(side='left',padx=2)

        checks=tk.Frame(self,bg=PANEL); checks.pack(fill='x',padx=10,pady=2)
        self._dot=tk.BooleanVar(); self._rest=tk.BooleanVar()
        self._tie=tk.BooleanVar(); self._slur=tk.BooleanVar()
        for txt,var in [("Dotted",self._dot),("Rest",self._rest),
                         ("Tied",self._tie),("Slur",self._slur)]:
            tk.Checkbutton(checks,text=txt,variable=var,bg=PANEL,fg=TEXT,
                selectcolor=DARK,font=('Arial',8),command=self._apply).pack(side='left',padx=4)

        r=row("Lyric:")
        self._lyric=tk.StringVar()
        e=tk.Entry(r,textvariable=self._lyric,bg=DARK,fg=WHITE,
            insertbackground=WHITE,relief='flat',font=('Arial',9))
        e.pack(side='left',fill='x',expand=True)
        e.bind('<Return>',lambda ev:self._apply())

        r=row("Fingering:")
        self._finger=tk.StringVar()
        tk.Entry(r,textvariable=self._finger,bg=DARK,fg=WHITE,
            insertbackground=WHITE,relief='flat',font=('Arial',9),width=6).pack(side='left')

        btn_f=tk.Frame(self,bg=PANEL); btn_f.pack(fill='x',padx=10,pady=8)
        tk.Button(btn_f,text="✓ Apply",bg=GREEN,fg=DARK,font=('Arial',9,'bold'),
            relief='flat',command=self._apply).pack(side='left',padx=4)
        tk.Button(btn_f,text="🗑 Delete",bg='#d9534f',fg=WHITE,font=('Arial',9,'bold'),
            relief='flat',command=self._delete).pack(side='left',padx=4)

        self._status=tk.Label(self,text="",bg=PANEL,fg=GREEN,font=('Arial',8),wraplength=220)
        self._status.pack(padx=10)

    def load_note(self,note,m_idx,n_idx):
        self.sel=note; self.sel_m=m_idx; self.sel_n=n_idx
        if note:
            self.info.config(
                text=f"{'Rest' if note.rest else note.pitch+str(note.octave)}"
                     f"  •  Measure {m_idx+1}, Note {n_idx+1}",fg=TEXT)
            self._pitch.set(note.pitch.rstrip('#b') or 'C')
            self._oct.set(note.octave)
            self._dur.set(str(note.duration))
            self._acc.set(note.accidental or '')
            self._voice.set(note.voice)
            self._dyn.set(note.dynamic or '')
            self._art.set(note.articulation or '')
            self._dot.set(note.dotted)
            self._rest.set(note.rest)
            self._tie.set(note.tied)
            self._slur.set('slur' in (note.special or '').lower())
            self._lyric.set(note.lyric or '')
            self._finger.set(note.fingering or '')
        else:
            self.info.config(text="No note selected",fg=MUTED)

    def _apply(self):
        if not self.sel: return
        n=self.sel
        n.pitch=self._pitch.get()+self._acc.get()
        n.octave=self._oct.get()
        try: n.duration=float(self._dur.get())
        except: pass
        n.accidental=self._acc.get()
        n.voice=self._voice.get()
        n.dynamic=self._dyn.get()
        n.articulation=self._art.get()
        n.dotted=self._dot.get()
        n.rest=self._rest.get()
        n.tied=self._tie.get()
        n.special='slur' if self._slur.get() else ''
        n.lyric=self._lyric.get()
        n.fingering=self._finger.get()
        self._status.config(text="✓ Applied")
        if self.on_change: self.on_change()

    def _delete(self):
        if not self.sel: return
        if 0<=self.sel_m<len(self.score.measures):
            m=self.score.measures[self.sel_m]
            if 0<=self.sel_n<len(m.notes):
                m.notes.pop(self.sel_n)
                self.sel=None
                self.info.config(text="Note deleted",fg=MUTED)
                if self.on_change: self.on_change()


# ═══════════════════════════════════════════════════════
#  SOLFA TEXT PANEL
# ═══════════════════════════════════════════════════════
class SolfaTextPanel(tk.Frame):
    def __init__(self,master,score:Score,on_change=None,**kwargs):
        super().__init__(master,bg=PANEL,**kwargs)
        self.score=score; self.on_change=on_change; self._build()

    def _build(self):
        bar=tk.Frame(self,bg=CARD); bar.pack(fill='x')
        tk.Label(bar,text="TONIC SOLFA TEXT VIEW",bg=CARD,fg=GOLD,
            font=('Arial',9,'bold')).pack(side='left',padx=10,pady=5)
        tk.Button(bar,text="⟳ Refresh",bg=ACCENT,fg=WHITE,relief='flat',
            font=('Arial',8),command=self.refresh_from_score).pack(side='right',padx=4,pady=4)
        self.txt=tk.Text(self,bg='#0d1b2a',fg=TEXT,insertbackground=WHITE,
            font=('Courier New',11),relief='flat',padx=12,pady=10,undo=True,wrap='none')
        sb_v=ttk.Scrollbar(self,orient='vertical',command=self.txt.yview)
        sb_h=ttk.Scrollbar(self,orient='horizontal',command=self.txt.xview)
        self.txt.config(yscrollcommand=sb_v.set,xscrollcommand=sb_h.set)
        sb_v.pack(side='right',fill='y'); sb_h.pack(side='bottom',fill='x')
        self.txt.pack(fill='both',expand=True)
        leg=tk.Frame(self,bg=PANEL); leg.pack(fill='x',pady=2)
        for lbl,col in [("d=Do","#e94560"),("r=Re","#f5a623"),("m=Mi","#00d4aa"),
                         ("f=Fa","#8892a4"),("s=Sol","#4fc3f7"),("l=La","#ce93d8"),
                         ("t=Ti","#ffb74d")]:
            tk.Label(leg,text=lbl,bg=col,fg=DARK,font=('Arial',8,'bold'),padx=4).pack(side='left',padx=1,pady=2)
        tk.Label(leg,text="  '=high oct   ,=low oct   —=held   0=rest   _=half   ==whole",
            bg=PANEL,fg=MUTED,font=('Arial',8)).pack(side='left',padx=8)

    def refresh_from_score(self):
        self.txt.delete('1.0','end')
        self.txt.insert('1.0',ConversionEngine.export_solfa_text(self.score))

    def set_score(self,score:Score):
        self.score=score; self.refresh_from_score()


# ═══════════════════════════════════════════════════════
#  REFERENCE PANEL
# ═══════════════════════════════════════════════════════
class ReferencePanel(tk.Canvas):
    def __init__(self,master,**kwargs):
        super().__init__(master,bg=DARK,bd=0,highlightthickness=0,**kwargs)
        self.bind('<Configure>',lambda e:self.after_idle(self._draw))

    def _draw(self):
        self.delete('all')
        cw=self.winfo_width() or 800; y=20
        self.create_text(cw//2,y,
            text="TONIC SOLFA REFERENCE CHART  —  Movable Do (SATB)",
            fill=GOLD,font=('Georgia',13,'bold'))
        y+=30
        syls=[('Do','d','C','#e94560'),('Re','r','D','#f5a623'),
              ('Mi','m','E','#00d4aa'),('Fa','f','F','#4fc3f7'),
              ('Sol','s','G','#ce93d8'),('La','l','A','#ffb74d'),
              ('Ti','t','B','#e94560')]
        cw2=(cw-40)//8; x0=20
        for i,(name,sym,nc,col) in enumerate(syls):
            x=x0+i*cw2
            self.create_rectangle(x+2,y+2,x+cw2-2,y+72,fill=col,outline=WHITE)
            self.create_text(x+cw2//2,y+16,text=name,fill=WHITE,font=('Georgia',13,'bold'))
            self.create_text(x+cw2//2,y+38,text=sym,fill=DARK,font=('Courier',22,'bold'))
            self.create_text(x+cw2//2,y+60,text=f"≈{nc} in C",fill=WHITE,font=('Arial',8))
        y+=86
        # Octave notation
        self.create_text(20,y,text="Octave notation (superscript/subscript):",
            fill=GOLD,font=('Arial',9,'bold'),anchor='w')
        y+=18
        oct_exs=[("d","Middle Do (oct 4)"),("d'","High Do (oct 5)"),
                  ("d''","Higher Do (oct 6)"),("d,","Low Do (oct 3)"),
                  ("d,,","Lower Do (oct 2)")]
        for sym,lbl in oct_exs:
            self.create_rectangle(20,y,120,y+32,fill=CARD,outline='')
            self.create_text(60,y+12,text=sym,fill=GOLD,font=('Courier New',14,'bold'))
            self.create_text(60,y+26,text=lbl,fill=MUTED,font=('Arial',7))
            y+=34
        y+=10
        # Duration notation
        self.create_text(20,y,text="Duration notation:",fill=GOLD,font=('Arial',9,'bold'),anchor='w')
        y+=18
        durs=[("d","Quarter"),("d_","Half (underline)"),("d==","Whole (2 underlines)"),
              ("d·","Eighth (dot above)"),("d:","Semiquaver"),("—","Held beat"),("0","Rest")]
        dx=20
        for sym,lbl in durs:
            self.create_rectangle(dx,y,dx+90,y+42,fill=CARD,outline='')
            self.create_text(dx+45,y+14,text=sym,fill=GOLD,font=('Courier',12,'bold'))
            self.create_text(dx+45,y+30,text=lbl,fill=MUTED,font=('Arial',7))
            dx+=94
            if dx>cw-100: dx=20; y+=44
        y+=50
        # Keys
        self.create_text(20,y,text="Keys (circle of fifths):",fill=GOLD,font=('Arial',9,'bold'),anchor='w')
        y+=18; kx=20
        for k in KEYS:
            self.create_rectangle(kx,y,kx+48,y+30,fill=DARK,outline=MUTED)
            self.create_text(kx+24,y+15,text=k,fill=TEXT,font=('Arial',9))
            kx+=50
        y+=40
        # Chromatic
        self.create_text(20,y,text="Chromatic syllables:",fill=GOLD,font=('Arial',9,'bold'),anchor='w')
        y+=18
        chrom_sharp=[('de','C#/Db'),('re','D#'),('fe','F#/Gb'),('se','G#/Ab'),('le','A#/Bb')]
        chrom_flat =[('ra','Db'),('ma','Eb'),('fe','Gb'),('la','Ab'),('ta','Bb')]
        self.create_text(20,y,text="Sharps: ",fill=BLUE,font=('Arial',8),anchor='w')
        x2=80
        for s,n in chrom_sharp:
            self.create_text(x2,y,text=f"{s}({n})",fill=BLUE,font=('Courier',9),anchor='w'); x2+=70
        y+=14
        self.create_text(20,y,text="Flats:  ",fill=PURPLE,font=('Arial',8),anchor='w')
        x2=80
        for s,n in chrom_flat:
            self.create_text(x2,y,text=f"{s}({n})",fill=PURPLE,font=('Courier',9),anchor='w'); x2+=70


# ═══════════════════════════════════════════════════════
#  SMART ENTRY ENGINE
# ═══════════════════════════════════════════════════════
class SmartEntry:
    """
    Keyboard-driven note entry.
    Keyboard mappings:
      d r m f s l t     → solfa notes in current key
      1-7               → also maps d r m f s l t
      Shift+d/r...      → lower octave
      Ctrl+d/r...       → upper octave
      0                 → rest
      Space             → advance beat (held note)
      Backspace         → delete last note
      [ ]               → previous/next measure
      q/w/e/r/t         → whole/half/quarter/eighth/16th (duration)
      . (period)        → toggle dot
      + / -             → octave up/down
      # / b             → sharp / flat
    """
    SOLFA_KEYS={'d':0,'r':2,'m':4,'f':5,'s':7,'l':9,'t':11}
    KEY_MAP={'d':'d','r':'r','m':'m','f':'f','s':'s','l':'l','t':'t',
             '1':'d','2':'r','3':'m','4':'f','5':'s','6':'l','7':'t'}
    DUR_MAP={'q':4.0,'w':2.0,'e':1.0,'a':0.5,'z':0.25}

    def __init__(self,score:Score,on_change=None):
        self.score=score; self.on_change=on_change
        self.active=False; self.cur_m=0; self.cur_v=1
        self.cur_dur=1.0; self.cur_oct=4; self.cur_dotted=False
        self.cur_acc=''; self.buffer=''

    def activate(self,voice,measure_idx):
        self.active=True; self.cur_v=voice; self.cur_m=measure_idx

    def deactivate(self):
        self.active=False; self.buffer=''

    def handle_key(self,event)->bool:
        """Returns True if key was consumed."""
        if not self.active: return False
        key=event.keysym.lower(); char=event.char

        # Duration shortcuts
        if key in self.DUR_MAP:
            self.cur_dur=self.DUR_MAP[key]; return True
        # Period = dotted
        if char=='.':
            self.cur_dotted=not self.cur_dotted; return True
        # Octave
        if key=='equal' or char=='+': self.cur_oct=min(8,self.cur_oct+1); return True
        if key=='minus' or char=='-': self.cur_oct=max(1,self.cur_oct-1); return True
        # Sharp/flat
        if char=='#': self.cur_acc='#'; return True
        if char=='b' and key!='b': self.cur_acc='b'; return True
        # Rest
        if char=='0':
            self._add_note(rest=True); self.cur_acc=''; return True
        # Backspace
        if key=='backspace':
            self._delete_last(); return True
        # Note entry
        if char in self.KEY_MAP or key in self.KEY_MAP:
            syl=self.KEY_MAP.get(char) or self.KEY_MAP.get(key)
            self._enter_solfa(syl); self.cur_acc=''; return True
        # Bracket measure nav
        if char=='[':
            self.cur_m=max(0,self.cur_m-1); return True
        if char==']':
            self.cur_m=min(len(self.score.measures)-1,self.cur_m+1); return True
        return False

    def _enter_solfa(self,syl):
        if self.cur_m>=len(self.score.measures): return
        m=self.score.measures[self.cur_m]
        pitch=self._solfa_to_pitch(syl,self.score.key_sig)
        if pitch is None: return
        p=pitch+self.cur_acc
        n=MusNote(pitch=p,octave=self.cur_oct,duration=self.cur_dur,
                  dotted=self.cur_dotted,voice=self.cur_v)
        avail=m.beats_available-m.beats_used_for_voice(self.cur_v)
        if n.beats<=avail+0.01:
            m.notes.append(n)
            if self.on_change: self.on_change()
        else:
            # Auto-advance to next measure
            if self.cur_m+1<len(self.score.measures):
                self.cur_m+=1
                m2=self.score.measures[self.cur_m]
                m2.notes.append(n)
                if self.on_change: self.on_change()

    def _add_note(self,rest=False):
        if self.cur_m>=len(self.score.measures): return
        m=self.score.measures[self.cur_m]
        n=MusNote(rest=True,duration=self.cur_dur,dotted=self.cur_dotted,voice=self.cur_v)
        avail=m.beats_available-m.beats_used_for_voice(self.cur_v)
        if n.beats<=avail+0.01:
            m.notes.append(n)
            if self.on_change: self.on_change()

    def _delete_last(self):
        if self.cur_m>=len(self.score.measures): return
        m=self.score.measures[self.cur_m]
        vnotes=[i for i,n in enumerate(m.notes) if n.voice==self.cur_v]
        if vnotes:
            m.notes.pop(vnotes[-1])
            if self.on_change: self.on_change()

    def _solfa_to_pitch(self,syl,key):
        kb=key.rstrip('#b')
        kc=NOTE_TO_CHROM.get(kb,0)
        if '#' in key and len(key)>1: kc=(kc+1)%12
        elif 'b' in key and len(key)>1: kc=(kc-1)%12
        sc=ConversionEngine.SOLFA_TO_CHROM.get(syl)
        if sc is None: return None
        midi_c=(kc+sc)%12
        return CHROM_TO_NOTE.get(midi_c,'C')


# ═══════════════════════════════════════════════════════
#  PRINT SETTINGS DIALOG
# ═══════════════════════════════════════════════════════
class TraditionalSolfaPrintSettingsDialog(tk.Toplevel):
    def __init__(self,master,canvas:TraditionalSolfaCanvas):
        super().__init__(master,bg=PANEL)
        self.title("Traditional Solfa Print Settings")
        self.geometry("400x260"); self.transient(master); self.grab_set()
        self.canvas=canvas
        tk.Label(self,text="Traditional Tonic Solfa — Print Layout",
            bg=PANEL,fg=GOLD,font=('Arial',11,'bold')).pack(pady=8)
        self.mpr=tk.IntVar(value=canvas.measures_per_row)
        self.rowgap=tk.IntVar(value=canvas.row_gap)
        self.scale=tk.DoubleVar(value=canvas.font_scale)
        self.fit=tk.BooleanVar(value=canvas.fit_to_width)
        self.barnum=tk.BooleanVar(value=canvas.show_bar_numbers)
        f=tk.Frame(self,bg=PANEL); f.pack(pady=4,padx=16,fill='x')
        rows=[("Measures per line:",self.mpr,1,16),("Row gap:",self.rowgap,8,80)]
        for ri,(lbl,var,lo,hi) in enumerate(rows):
            tk.Label(f,text=lbl,bg=PANEL,fg=TEXT,font=('Arial',9)).grid(row=ri,column=0,sticky='w')
            tk.Spinbox(f,from_=lo,to=hi,width=5,textvariable=var).grid(row=ri,column=1,sticky='w',padx=4)
        tk.Label(f,text="Font scale:",bg=PANEL,fg=TEXT,font=('Arial',9)).grid(row=2,column=0,sticky='w')
        tk.Spinbox(f,from_=0.6,to=2.0,increment=0.1,width=5,textvariable=self.scale).grid(row=2,column=1,sticky='w',padx=4)
        tk.Checkbutton(f,text='Fit to width',bg=PANEL,fg=TEXT,variable=self.fit).grid(row=3,column=0,columnspan=2,sticky='w')
        tk.Checkbutton(f,text='Show bar numbers',bg=PANEL,fg=TEXT,variable=self.barnum).grid(row=4,column=0,columnspan=2,sticky='w')
        b=tk.Frame(self,bg=PANEL); b.pack(pady=10)
        tk.Button(b,text="Apply",bg=ACCENT,fg=WHITE,relief='flat',width=10,command=self._apply).pack(side='left',padx=8)
        tk.Button(b,text="Close",bg=DARK,fg=WHITE,relief='flat',width=10,command=self.destroy).pack(side='left',padx=8)

    def _apply(self):
        self.canvas.set_render_options(
            measures_per_row=self.mpr.get(),row_gap=self.rowgap.get(),
            font_scale=self.scale.get(),fit_to_width=self.fit.get(),
            show_bar_numbers=self.barnum.get())
        self.canvas.redraw()


# ═══════════════════════════════════════════════════════
#  PROPERTIES PANEL
# ═══════════════════════════════════════════════════════
class PropertiesPanel(tk.Frame):
    def __init__(self,master,score:Score,on_change=None,**kwargs):
        super().__init__(master,bg=PANEL,width=220,**kwargs)
        self.score=score; self.on_change=on_change
        self.pack_propagate(False); self.vars={}
        self._build()

    def _sec(self,title):
        f=tk.Frame(self,bg=CARD,height=24); f.pack(fill='x',pady=(6,0))
        f.pack_propagate(False)
        tk.Label(f,text=title,bg=CARD,fg=GOLD,font=('Arial',8,'bold')).pack(side='left',padx=8,pady=3)

    def _field(self,label,attr,wtype='entry',opts=None):
        row=tk.Frame(self,bg=PANEL); row.pack(fill='x',padx=8,pady=2)
        tk.Label(row,text=label+':',bg=PANEL,fg=MUTED,font=('Arial',8),width=9,anchor='w').pack(side='left')
        if wtype=='entry':
            var=tk.StringVar(value=str(getattr(self.score,attr,'')))
            tk.Entry(row,textvariable=var,bg=DARK,fg=WHITE,insertbackground=WHITE,
                relief='flat',font=('Arial',9)).pack(side='left',fill='x',expand=True)
            var.trace_add('write',lambda *a,v=var,k=attr:self._upd(k,v.get()))
            self.vars[attr]=var
        elif wtype=='combo':
            cur=(f"{self.score.time_num}/{self.score.time_den}" if attr=='time_sig'
                 else str(getattr(self.score,attr,opts[0])))
            var=tk.StringVar(value=cur)
            cb=ttk.Combobox(row,textvariable=var,values=opts,font=('Arial',9),width=9,state='readonly')
            cb.pack(side='left')
            cb.bind('<<ComboboxSelected>>',lambda e,v=var,k=attr:self._upd(k,v.get()))
            self.vars[attr]=var
        elif wtype=='spin':
            lo,hi=opts
            var=tk.IntVar(value=int(getattr(self.score,attr,lo)))
            tk.Spinbox(row,from_=lo,to=hi,textvariable=var,bg=DARK,fg=WHITE,
                insertbackground=WHITE,relief='flat',font=('Arial',9),width=5).pack(side='left')
            var.trace_add('write',lambda *a,v=var,k=attr:self._upd_int(k,v))
            self.vars[attr]=var

    def _upd(self,attr,val):
        if attr=='time_sig':
            try:
                a,b=val.split('/')
                self.score.time_num=int(a); self.score.time_den=int(b)
                for m in self.score.measures: m.time_num=int(a); m.time_den=int(b)
            except: pass
        elif attr=='key_sig':
            self.score.key_sig=val
            for m in self.score.measures: m.key_sig=val
        elif hasattr(self.score,attr): setattr(self.score,attr,val)
        if self.on_change: self.on_change()

    def _upd_int(self,attr,var):
        try:
            setattr(self.score,attr,var.get())
            if self.on_change: self.on_change()
        except: pass

    def _build(self):
        self._sec("SCORE INFO")
        self._field("Title",'title')
        self._field("Composer",'composer')
        self._field("Lyricist",'lyricist')
        self._field("Key",'key_sig','combo',KEYS)
        self._field("Time",'time_sig','combo',TIME_SIGS)
        self._field("Tempo ♩",'tempo_bpm','spin',(20,400))
        self._field("Clef",'clef','combo',['treble','bass','alto'])
        self._sec("PLAYBACK")
        self._play_panel()

    def _play_panel(self):
        f=tk.Frame(self,bg=PANEL); f.pack(fill='x',padx=8,pady=4)
        tk.Button(f,text="▶ Play All",bg=GREEN,fg=DARK,relief='flat',
            font=('Arial',10,'bold'),command=self._play).pack(side='left',padx=2)
        tk.Button(f,text="⏹ Stop",bg=DARK,fg=TEXT,relief='flat',
            font=('Arial',10),command=self._stop).pack(side='left',padx=2)

    def _play(self):
        pass  # connected by main app

    def _stop(self):
        pass  # connected by main app

    def refresh(self,score:Score):
        self.score=score
        for k,v in self.vars.items():
            if k=='time_sig': v.set(f"{score.time_num}/{score.time_den}")
            elif hasattr(score,k): v.set(str(getattr(score,k)))


# ═══════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════
class TonicSolfaStudio(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME}  v{APP_VERSION}")
        self.geometry("1540x900"); self.minsize(1100,720)
        self.configure(bg=DARK)
        self.score=Score(title="Untitled Score")
        self.score.ensure_measures(8)
        self.filepath=None; self.modified=False
        self._hist=deque(maxlen=80); self._redo=deque(maxlen=80)
        self.settings=self._load_settings()
        self._snap()

        self.font_manager = FontStylesManager()
        self.lyrics_manager = LyricsManager()
        self.audio_config = AudioConfig(tempo_bpm=self.score.tempo_bpm)

        self.smart_entry=SmartEntry(self.score,on_change=self._on_change)
        self._setup_style()
        self._build_menu()
        self._build_toolbar()
        self._build_main()
        self._apply_settings()
        self._build_statusbar()
        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW",self._quit)
        self.after(150,self._initial_render)

    def _setup_style(self):
        s=ttk.Style(self); s.theme_use('clam')
        for n in ['TCombobox','TSpinbox']:
            s.configure(n,fieldbackground=DARK,background=DARK,foreground=TEXT,arrowcolor=GOLD)
        s.configure('TScrollbar',background=PANEL,troughcolor=DARK,arrowcolor=MUTED)
        s.configure('TNotebook',background=PANEL,tabmargins=0)
        s.configure('TNotebook.Tab',background=CARD,foreground=MUTED,padding=[10,4])
        s.map('TNotebook.Tab',background=[('selected',DARK)],foreground=[('selected',WHITE)])

    def _load_settings(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE,'r',encoding='utf-8') as f: return json.load(f)
        except: pass
        return {'trad_mpr':TraditionalSolfaCanvas.DEFAULT_MEASURES_PER_ROW,
                'trad_row_gap':TraditionalSolfaCanvas.ROW_GAP,
                'trad_font_scale':1.0,'trad_fit_to_width':True,'trad_bar_numbers':True}

    def _save_settings(self):
        try:
            data={'trad_mpr':self.trad_canvas.measures_per_row,
                  'trad_row_gap':self.trad_canvas.row_gap,
                  'trad_font_scale':self.trad_canvas.font_scale,
                  'trad_fit_to_width':self.trad_canvas.fit_to_width,
                  'trad_bar_numbers':self.trad_canvas.show_bar_numbers}
            with open(SETTINGS_FILE,'w',encoding='utf-8') as f: json.dump(data,f,indent=2)
        except: pass

    def _apply_settings(self):
        s=self.settings or {}
        if hasattr(self,'trad_canvas'):
            self.trad_canvas.set_render_options(
                measures_per_row=s.get('trad_mpr',TraditionalSolfaCanvas.DEFAULT_MEASURES_PER_ROW),
                row_gap=s.get('trad_row_gap',TraditionalSolfaCanvas.ROW_GAP),
                font_scale=s.get('trad_font_scale',1.0),
                fit_to_width=s.get('trad_fit_to_width',True),
                show_bar_numbers=s.get('trad_bar_numbers',True))

    # ── Menu ─────────────────────────────────────────
    def _build_menu(self):
        mb=tk.Menu(self,bg=PANEL,fg=TEXT,activebackground=CARD,activeforeground=WHITE,tearoff=False)
        fm=tk.Menu(mb,bg=PANEL,fg=TEXT,activebackground=CARD,activeforeground=WHITE,tearoff=False)
        fm.add_command(label="New Score",               command=self._new,        accelerator="Ctrl+N")
        fm.add_command(label="Open Project…",           command=self._open,       accelerator="Ctrl+O")
        fm.add_command(label="Save",                    command=self._save,       accelerator="Ctrl+S")
        fm.add_command(label="Save As…",                command=self._save_as)
        fm.add_separator()
        fm.add_command(label="Import MusicXML / MXL…", command=self._import_mxl)
        fm.add_command(label="Import MIDI (.mid)…",    command=self._import_midi)
        fm.add_command(label="Import WAV…",             command=self._import_wav)
        fm.add_command(label="Import Finale 2012/2014…",command=self._import_finale)
        fm.add_command(label="Import ABC…",             command=self._import_abc)
        fm.add_separator()
        fm.add_command(label="Export MusicXML…",        command=self._export_mxml)
        fm.add_command(label="Export MIDI (Harmony)…",  command=self._export_midi)
        fm.add_command(label="Export ABC…",             command=self._export_abc)
        fm.add_command(label="Export Tonic Solfa Text…",command=self._export_solfa_txt)
        fm.add_separator()
        fm.add_command(label="Print Traditional Solfa PDF…",command=self._print_trad_solfa,accelerator="Ctrl+P")
        fm.add_separator()
        fm.add_command(label="Exit",                    command=self._quit,       accelerator="Alt+F4")
        mb.add_cascade(label="File",menu=fm)

        em=tk.Menu(mb,bg=PANEL,fg=TEXT,activebackground=CARD,activeforeground=WHITE,tearoff=False)
        em.add_command(label="Undo",                command=self._undo,          accelerator="Ctrl+Z")
        em.add_command(label="Redo",                command=self._redo_cmd,      accelerator="Ctrl+Y")
        em.add_separator()
        em.add_command(label="Add Measure",         command=self._add_measure,   accelerator="Ctrl+M")
        em.add_command(label="Delete Last Measure", command=self._del_measure,   accelerator="Ctrl+Shift+M")
        em.add_command(label="Clear All Measures",  command=self._clear)
        em.add_separator()
        em.add_command(label="Score Properties…",   command=self._score_props,   accelerator="Ctrl+I")
        em.add_command(label="Add Lyrics…",         command=self._add_lyrics)
        em.add_command(label="Auto-Fill Rests",     command=self._autofill_rests)
        mb.add_cascade(label="Edit",menu=em)

        vm=tk.Menu(mb,bg=PANEL,fg=TEXT,activebackground=CARD,activeforeground=WHITE,tearoff=False)
        vm.add_command(label="Traditional Solfa View", command=lambda:self.nb.select(0), accelerator="Ctrl+1")
        vm.add_command(label="Staff Notation View",    command=lambda:self.nb.select(1), accelerator="Ctrl+2")
        vm.add_command(label="Solfa Text Editor",      command=lambda:self.nb.select(2), accelerator="Ctrl+3")
        vm.add_command(label="Note Editor",            command=lambda:self.nb.select(3), accelerator="Ctrl+4")
        vm.add_command(label="Solfa Reference Chart",  command=lambda:self.nb.select(4), accelerator="Ctrl+5")
        mb.add_cascade(label="View",menu=vm)

        tm=tk.Menu(mb,bg=PANEL,fg=TEXT,activebackground=CARD,activeforeground=WHITE,tearoff=False)
        tm.add_command(label="Convert Staff → Solfa",command=self._to_solfa)
        tm.add_command(label="Transpose…",           command=self._transpose,     accelerator="Ctrl+T")
        tm.add_command(label="Transpose Up Semitone",command=lambda:self._quick_transpose(1), accelerator="Ctrl+Up")
        tm.add_command(label="Transpose Down Semitone",command=lambda:self._quick_transpose(-1),accelerator="Ctrl+Down")
        rm_=tk.Menu(tm,bg=PANEL,fg=TEXT,tearoff=False)
        for lbl,val in [("||: Repeat Start","repeat_start"),(":|  Repeat End","repeat_end"),
                         ("||  Double Bar","double_bar")]:
            rm_.add_command(label=lbl,command=lambda v=val:self._add_repeat(v))
        tm.add_cascade(label="Repeat Signs",menu=rm_)
        tm.add_separator()
        tm.add_command(label="Library Status", command=self._lib_status)
        mb.add_cascade(label="Tools",menu=tm)

        pm=tk.Menu(mb,bg=PANEL,fg=TEXT,activebackground=CARD,activeforeground=WHITE,tearoff=False)
        pm.add_command(label="Play All Voices (Harmony)",command=self._play,accelerator="Space")
        pm.add_command(label="Stop",                     command=self._stop,accelerator="Escape")
        mb.add_cascade(label="Playback",menu=pm)

        hm=tk.Menu(mb,bg=PANEL,fg=TEXT,activebackground=CARD,activeforeground=WHITE,tearoff=False)
        hm.add_command(label="Quick Guide",        command=self._guide)
        hm.add_command(label="Keyboard Shortcuts", command=self._shortcuts)
        hm.add_separator()
        hm.add_command(label=f"About {APP_NAME}",  command=self._about)
        mb.add_cascade(label="Help",menu=hm)
        self.config(menu=mb)

    # ── Toolbar ──────────────────────────────────────
    def _build_toolbar(self):
        tb=tk.Frame(self,bg=CARD,height=48); tb.pack(fill='x')
        tb.pack_propagate(False)
        def btn(text,tip,cmd,bg=CARD,fg=TEXT):
            b=tk.Button(tb,text=text,bg=bg,fg=fg,relief='flat',font=('Arial',12),padx=6,
                activebackground=DARK,activeforeground=WHITE,command=cmd)
            b.pack(side='left',padx=1,pady=6); _tooltip(b,tip); return b

        btn("📄","New (Ctrl+N)",self._new)
        btn("📂","Open (Ctrl+O)",self._open)
        btn("💾","Save (Ctrl+S)",self._save)
        _sep(tb)
        btn("📥","Import MXL",self._import_mxl)
        btn("🎵","Import MIDI",self._import_midi)
        btn("🎼","Import Finale",self._import_finale)
        _sep(tb)
        # Tool selector
        self._tool_var=tk.StringVar(value='select')
        for sym,val,tip in [('↖','select','Select (Esc)'),('♩','note','Note (N)'),
                             ('𝄽','rest','Rest (R)'),('✕','erase','Erase (E)'),
                             ('T','lyric','Lyric (L)'),('𝆑','dynamic','Dynamic (D)')]:
            rb=tk.Radiobutton(tb,text=sym,variable=self._tool_var,value=val,
                indicatoron=0,bg=CARD,fg=GOLD,selectcolor=ACCENT,activebackground=DARK,
                font=('Arial',12),padx=6,pady=5,
                command=lambda v=val:self._set_tool(v))
            rb.pack(side='left',padx=1,pady=5); _tooltip(rb,tip)
        _sep(tb)
        # Duration
        tk.Label(tb,text="Dur:",bg=CARD,fg=MUTED,font=('Arial',8)).pack(side='left')
        self._tb_dur=tk.StringVar(value='Q')
        for sym,val,tip,key in [('W',4.0,'Whole (Q)','q'),('H',2.0,'Half (W)','w'),
                                  ('Q',1.0,'Quarter (E)','e'),('E',0.5,'Eighth (A)','a'),
                                  ('S',0.25,'16th (Z)','z')]:
            rb=tk.Radiobutton(tb,text=sym,variable=self._tb_dur,value=sym,
                indicatoron=0,bg=CARD,fg=GOLD,selectcolor=ACCENT,activebackground=DARK,
                font=('Arial',10,'bold'),padx=5,pady=5,
                command=lambda v=val,s=sym:self._set_dur(v,s))
            rb.pack(side='left',padx=1,pady=5); _tooltip(rb,tip)
        _sep(tb)
        # Accidentals
        self._tb_acc=tk.StringVar(value='')
        for sym,val,tip in [('♮','','Natural'),('♯','#','Sharp (#)'),('♭','b','Flat (b)')]:
            rb=tk.Radiobutton(tb,text=sym,variable=self._tb_acc,value=val,
                indicatoron=0,bg=CARD,fg=GOLD,selectcolor=ACCENT,activebackground=DARK,
                font=('Arial',12),padx=4,pady=5,
                command=lambda v=val:self._set_acc(v))
            rb.pack(side='left',padx=1,pady=5); _tooltip(rb,tip)
        _sep(tb)
        # Voice
        tk.Label(tb,text="Voice:",bg=CARD,fg=MUTED,font=('Arial',8)).pack(side='left')
        self._tb_voice=tk.IntVar(value=1)
        for lbl,v,c in [('S',1,ACCENT),('A',2,BLUE),('T',3,GREEN),('B',4,GOLD)]:
            rb=tk.Radiobutton(tb,text=lbl,variable=self._tb_voice,value=v,
                indicatoron=0,bg=CARD,fg=c,selectcolor=DARK,activebackground=DARK,
                font=('Arial',10,'bold'),padx=5,pady=5,
                command=lambda vv=v:self._set_voice(vv))
            rb.pack(side='left',padx=1,pady=5)
        _sep(tb)
        btn("▶","Play (Space)",self._play,bg=CARD)
        btn("⏹","Stop (Esc)",self._stop,bg=CARD)
        btn("🖨","Print Trad Solfa PDF (Ctrl+P)",self._print_trad_solfa,bg=CARD)
        _sep(tb)
        tk.Button(tb,text="Staff→Solfa",bg=ACCENT,fg=WHITE,relief='flat',
            font=('Arial',8,'bold'),command=self._to_solfa).pack(side='left',padx=3,pady=8)
        tk.Button(tb,text="+Measure",bg=GREEN,fg=DARK,relief='flat',
            font=('Arial',8,'bold'),command=self._add_measure).pack(side='left',padx=2,pady=8)
        # Smart Entry toggle
        self._smart_btn=tk.Button(tb,text="⌨ Smart Entry OFF",bg=DARK,fg=MUTED,
            relief='flat',font=('Arial',8,'bold'),command=self._toggle_smart_entry)
        self._smart_btn.pack(side='left',padx=3,pady=8)
        # Lib badges
        badges=[]
        if MIDIUTIL_OK:  badges.append("MIDI✓")
        if REPORTLAB_OK: badges.append("PDF✓")
        if PYGAME_OK:    badges.append("Audio✓")
        if MIDO_OK:      badges.append("MIDOin✓")
        if badges:
            tk.Label(tb,text="  ".join(badges),bg=CARD,fg=GREEN,font=('Arial',7)).pack(side='right',padx=10)

    def _set_tool(self,v):
        self._tool_var.set(v); self.staff_canvas.tool=v
        if hasattr(self,'palette'): self.palette.tool_var.set(v)

    def _set_dur(self,vf,vs):
        self._tb_dur.set(vs); self.staff_canvas.cur_dur=vf
        self.smart_entry.cur_dur=vf
        if hasattr(self,'palette'): self.palette.dur_var.set(str(vf))

    def _set_acc(self,v):
        self._tb_acc.set(v); self.staff_canvas.cur_acc=v
        self.smart_entry.cur_acc=v

    def _set_voice(self,v):
        self._tb_voice.set(v); self.staff_canvas.cur_voice=v
        self.smart_entry.cur_v=v
        if hasattr(self,'palette'): self.palette.voice_var.set(v)

    def _toggle_smart_entry(self):
        if self.smart_entry.active:
            self.smart_entry.deactivate()
            self._smart_btn.config(text="⌨ Smart Entry OFF",bg=DARK,fg=MUTED)
            self.status_var.set("Smart Entry: OFF")
        else:
            self.smart_entry.activate(self._tb_voice.get(),0)
            self._smart_btn.config(text="⌨ Smart Entry ON",bg=GREEN,fg=DARK)
            self.status_var.set("Smart Entry: ON — type d r m f s l t to enter notes, q/w/e/a/z for duration")

    # ── Main Layout ───────────────────────────────────
    def _build_main(self):
        paned=tk.PanedWindow(self,orient='horizontal',bg=DARK,sashrelief='flat',sashwidth=5)
        paned.pack(fill='both',expand=True)

        self.props_panel=PropertiesPanel(paned,self.score,on_change=self._on_change)
        self.props_panel._play=self._play  # wire up
        self.props_panel._stop=self._stop
        paned.add(self.props_panel,minsize=190,width=215)

        # Right-side tools dashboard
        self.tools_dashboard = tk.Frame(paned,bg=PANEL,width=220)
        self.tools_dashboard.pack_propagate(False)
        paned.add(self.tools_dashboard,minsize=180)

        tk.Label(self.tools_dashboard,text="🛠 Utility Dashboard",bg=PANEL,fg=GOLD,
            font=('Arial',11,'bold')).pack(pady=(12,8),padx=10,anchor='w')

        def dash_btn(label,cmd):
            tk.Button(self.tools_dashboard,text=label,bg=BLUE,fg=WHITE,relief='flat',
                font=('Arial',10),command=cmd).pack(fill='x',padx=10,pady=4)

        dash_btn('Font Style Manager', self._open_font_styles)
        dash_btn('Lyrics Manager', self._open_lyrics_manager)
        dash_btn('Import Finale', self._import_finale)
        dash_btn('Export Finale (MXL)', self._export_mxml)
        dash_btn('Play Audio (MIDI)', self._play)
        dash_btn('Render WAV', self._render_wav_from_score)

        # Center: tabs
        center=tk.Frame(paned,bg=DARK); paned.add(center,minsize=580)
        self.nb=ttk.Notebook(center); self.nb.pack(fill='both',expand=True)

        # Tab 0 – Traditional Tonic Solfa (PRIMARY — matches print)
        tf=tk.Frame(self.nb,bg=DARK); self.nb.add(tf,text="  📋 Traditional Solfa  ")
        ctrl=tk.Frame(tf,bg=CARD,height=28); ctrl.pack(fill='x'); ctrl.pack_propagate(False)
        tk.Label(ctrl,text="Traditional Tonic Solfa — SATB (Primary View & Print Output)",
            bg=CARD,fg=GOLD,font=('Arial',8,'bold')).pack(side='left',padx=10)
        tk.Button(ctrl,text="⟳ Refresh",bg=ACCENT,fg=WHITE,relief='flat',font=('Arial',8),
            command=lambda:self.trad_canvas.set_score(self.score)).pack(side='right',padx=6,pady=3)
        tk.Button(ctrl,text="⚙ Layout",bg=BLUE,fg=WHITE,relief='flat',font=('Arial',8),
            command=self._trad_print_settings).pack(side='right',padx=6,pady=3)
        tk.Button(ctrl,text="🖨 Print PDF",bg=GREEN,fg=DARK,relief='flat',font=('Arial',8,'bold'),
            command=self._print_trad_solfa).pack(side='right',padx=6,pady=3)

        opts=tk.Frame(tf,bg=CARD,height=28); opts.pack(fill='x')
        tk.Label(opts,text="bars/line",bg=CARD,fg=TEXT,font=('Arial',8)).pack(side='left',padx=6)
        self.trad_mpr=tk.IntVar(value=TraditionalSolfaCanvas.DEFAULT_MEASURES_PER_ROW)
        ttk.Spinbox(opts,from_=1,to=16,width=4,textvariable=self.trad_mpr,
            command=self._update_trad_layout).pack(side='left',padx=1)
        self.trad_fit=tk.BooleanVar(value=True)
        tk.Checkbutton(opts,text='Fit width',bg=CARD,fg=TEXT,selectcolor=CARD,
            variable=self.trad_fit,command=self._update_trad_layout).pack(side='left',padx=6)
        tk.Label(opts,text="row gap",bg=CARD,fg=TEXT,font=('Arial',8)).pack(side='left',padx=4)
        self.trad_rowgap=tk.IntVar(value=TraditionalSolfaCanvas.ROW_GAP)
        ttk.Spinbox(opts,from_=10,to=60,width=4,textvariable=self.trad_rowgap,
            command=self._update_trad_layout).pack(side='left',padx=1)
        tk.Label(opts,text="scale",bg=CARD,fg=TEXT,font=('Arial',8)).pack(side='left',padx=4)
        self.trad_scale=tk.DoubleVar(value=1.0)
        ttk.Spinbox(opts,from_=0.6,to=2.0,increment=0.1,width=4,textvariable=self.trad_scale,
            command=self._update_trad_layout).pack(side='left',padx=1)
        self.trad_barnum=tk.BooleanVar(value=True)
        tk.Checkbutton(opts,text='Bar #s',bg=CARD,fg=TEXT,selectcolor=CARD,
            variable=self.trad_barnum,command=self._update_trad_layout).pack(side='left',padx=6)

        vs=ttk.Scrollbar(tf,orient='vertical'); hs=ttk.Scrollbar(tf,orient='horizontal')
        self.trad_canvas=TraditionalSolfaCanvas(tf,self.score,xscrollcommand=hs.set,yscrollcommand=vs.set)
        vs.config(command=self.trad_canvas.yview); hs.config(command=self.trad_canvas.xview)
        vs.pack(side='right',fill='y'); hs.pack(side='bottom',fill='x')
        self.trad_canvas.pack(fill='both',expand=True)

        # Tab 1 – Staff Notation (editable)
        sf=tk.Frame(self.nb,bg=DARK); self.nb.add(sf,text="  🎼 Staff Notation  ")

        # Palette on left of staff
        pal_frame=tk.Frame(sf,bg=PANEL,width=280); pal_frame.pack(side='left',fill='y')
        pal_frame.pack_propagate(False)
        pal_scroll=tk.Frame(pal_frame,bg=PANEL)
        pal_scroll.pack(fill='both',expand=True)
        # Scrollable palette
        pal_canvas=tk.Canvas(pal_scroll,bg=PANEL,bd=0,highlightthickness=0)
        pal_vsb=ttk.Scrollbar(pal_scroll,orient='vertical',command=pal_canvas.yview)
        pal_canvas.configure(yscrollcommand=pal_vsb.set)
        pal_vsb.pack(side='right',fill='y'); pal_canvas.pack(side='left',fill='both',expand=True)
        pal_inner=tk.Frame(pal_canvas,bg=PANEL)
        pal_canvas.create_window((0,0),window=pal_inner,anchor='nw')
        pal_inner.bind('<Configure>',lambda e:pal_canvas.configure(scrollregion=pal_canvas.bbox('all')))

        self.palette=SolfaPalette(pal_inner,
            on_tool_change=self._set_tool,
            on_dur_change=lambda v:self._set_dur(v,{4.0:'W',2.0:'H',1.0:'Q',0.5:'E',0.25:'S'}.get(v,'Q')),
            on_voice_change=self._set_voice,
            on_dyn_apply=self._apply_dyn_to_selection,
            on_art_apply=self._apply_art_to_selection)
        self.palette.pack(fill='both',expand=True)

        # Wire repeat buttons
        for val,btn_widget in self.palette.repeat_callbacks.items():
            btn_widget.config(command=lambda v=val:self._add_repeat(v))

        # Smart entry indicator
        se_f=tk.Frame(pal_inner,bg=CARD,height=30); se_f.pack(fill='x',pady=4)
        se_f.pack_propagate(False)
        tk.Label(se_f,text="⌨ SMART ENTRY",bg=CARD,fg=GREEN,font=('Arial',8,'bold')).pack(side='left',padx=6)
        tk.Label(se_f,text="d r m f s l t → notes",bg=CARD,fg=MUTED,font=('Arial',7)).pack(side='left')

        vs2=ttk.Scrollbar(sf,orient='vertical'); hs2=ttk.Scrollbar(sf,orient='horizontal')
        self.staff_canvas=StaffCanvas(sf,self.score,on_change=self._on_change,
            on_select=self._on_note_sel,xscrollcommand=hs2.set,yscrollcommand=vs2.set)
        vs2.config(command=self.staff_canvas.yview); hs2.config(command=self.staff_canvas.xview)
        vs2.pack(side='right',fill='y'); hs2.pack(side='bottom',fill='x')
        self.staff_canvas.pack(fill='both',expand=True)

        # Tab 2 – Solfa Text
        stf=tk.Frame(self.nb,bg=PANEL); self.nb.add(stf,text="  🎵 Solfa Text  ")
        self.solfa_panel=SolfaTextPanel(stf,self.score,on_change=self._on_change)
        self.solfa_panel.pack(fill='both',expand=True)

        # Tab 3 – Note Editor
        nef=tk.Frame(self.nb,bg=PANEL); self.nb.add(nef,text="  ✏ Note Editor  ")
        self.note_editor=NoteEditorPanel(nef,self.score,on_change=self._on_change)
        self.note_editor.pack(fill='both',expand=True)

        # Tab 4 – Reference
        ref=tk.Frame(self.nb,bg=DARK); self.nb.add(ref,text="  📖 Solfa Reference  ")
        self.ref_panel=ReferencePanel(ref); self.ref_panel.pack(fill='both',expand=True)

        self.nb.bind('<<NotebookTabChanged>>',self._on_tab)

    def _build_statusbar(self):
        sb=tk.Frame(self,bg=CARD,height=26); sb.pack(fill='x',side='bottom')
        sb.pack_propagate(False)
        self.status_var=tk.StringVar(value=f"Ready  —  {APP_NAME} v{APP_VERSION}")
        self.info_var=tk.StringVar(value="")
        tk.Label(sb,textvariable=self.status_var,bg=CARD,fg=MUTED,font=('Arial',8),anchor='w').pack(side='left',padx=10)
        tk.Label(sb,textvariable=self.info_var,bg=CARD,fg=GREEN,font=('Arial',8)).pack(side='right',padx=10)
        miss=[l for l,ok in [("midiutil",MIDIUTIL_OK),("reportlab",REPORTLAB_OK),
                               ("pygame",PYGAME_OK),("mido",MIDO_OK)] if not ok]
        if miss:
            tk.Label(sb,text=f"⚠ pip install {' '.join(miss)}",bg=CARD,fg=GOLD,font=('Arial',8)).pack(side='right',padx=10)

    # ── Keyboard Shortcuts ────────────────────────────
    def _bind_shortcuts(self):
        self.bind('<Control-n>',lambda e:self._new())
        self.bind('<Control-o>',lambda e:self._open())
        self.bind('<Control-s>',lambda e:self._save())
        self.bind('<Control-z>',lambda e:self._undo())
        self.bind('<Control-y>',lambda e:self._redo_cmd())
        self.bind('<Control-m>',lambda e:self._add_measure())
        self.bind('<Control-M>',lambda e:self._del_measure())
        self.bind('<Control-p>',lambda e:self._print_trad_solfa())
        self.bind('<Control-t>',lambda e:self._transpose())
        self.bind('<Control-i>',lambda e:self._score_props())
        self.bind('<Control-Up>',   lambda e:self._quick_transpose(1))
        self.bind('<Control-Down>', lambda e:self._quick_transpose(-1))
        # View shortcuts
        self.bind('<Control-Key-1>',lambda e:self.nb.select(0))
        self.bind('<Control-Key-2>',lambda e:self.nb.select(1))
        self.bind('<Control-Key-3>',lambda e:self.nb.select(2))
        self.bind('<Control-Key-4>',lambda e:self.nb.select(3))
        self.bind('<Control-Key-5>',lambda e:self.nb.select(4))
        # Tool shortcuts
        self.bind('<Escape>',   lambda e:(self._set_tool('select'),self._stop()))
        self.bind('<n>',        lambda e:self._smart_or_tool('note'))
        self.bind('<r>',        lambda e:self._smart_or_tool('rest'))
        self.bind('<e>',        lambda e:self._smart_or_tool('erase'))
        self.bind('<l>',        lambda e:self._smart_or_tool('lyric'))
        self.bind('<d>',        lambda e:self._smart_or_tool('dynamic'))
        # Duration shortcuts (when smart entry OFF)
        self.bind('<q>',        lambda e:self._handle_key_or_dur(e,4.0,'W'))
        self.bind('<w>',        lambda e:self._handle_key_or_dur(e,2.0,'H'))
        self.bind('<a>',        lambda e:self._handle_key_or_dur(e,0.5,'E'))
        self.bind('<z>',        lambda e:self._handle_key_or_dur(e,0.25,'S'))
        # Playback
        self.bind('<space>',    lambda e:self._play())
        # Smart entry — forward all keys when active
        self.bind('<Key>',      self._route_key)
        # Octave via smart entry
        self.bind('<plus>',     lambda e:self._change_octave(1))
        self.bind('<minus>',    lambda e:self._change_octave(-1))

    def _smart_or_tool(self,tool):
        if not self.smart_entry.active:
            self._set_tool(tool)

    def _handle_key_or_dur(self,event,dur_val,sym):
        if self.smart_entry.active:
            self.smart_entry.handle_key(event)
        else:
            self._set_dur(dur_val,sym)

    def _route_key(self,event):
        if self.smart_entry.active:
            consumed=self.smart_entry.handle_key(event)
            if consumed:
                self._update_smart_display(); return 'break'

    def _update_smart_display(self):
        self.trad_canvas.set_score(self.score)
        self.staff_canvas.set_score(self.score)
        self._update_info()

    def _change_octave(self,delta):
        if self.smart_entry.active:
            self.smart_entry.cur_oct=max(1,min(8,self.smart_entry.cur_oct+delta))
            self.status_var.set(f"Smart Entry octave: {self.smart_entry.cur_oct}")

    # ── Render Helpers ────────────────────────────────
    def _initial_render(self):
        self.trad_canvas.set_score(self.score)
        self.staff_canvas.set_score(self.score)
        self.solfa_panel.set_score(self.score)
        self.props_panel.refresh(self.score)
        self.note_editor.score=self.score
        self._update_title(); self._update_info()
        self.status_var.set(f"Ready — {APP_NAME} v{APP_VERSION}. Ctrl+P = Print Tonic Solfa PDF")

    def _on_change(self):
        self.modified=True; self._update_title(); self._snap()
        self.trad_canvas.set_score(self.score)
        self.staff_canvas.set_score(self.score)
        self._update_info()

    def _trad_print_settings(self):
        TraditionalSolfaPrintSettingsDialog(self,self.trad_canvas)

    def _update_trad_layout(self):
        if not hasattr(self,'trad_canvas'): return
        self.trad_canvas.set_render_options(
            measures_per_row=self.trad_mpr.get(),
            row_gap=self.trad_rowgap.get(),
            font_scale=self.trad_scale.get(),
            fit_to_width=self.trad_fit.get(),
            show_bar_numbers=self.trad_barnum.get())
        self._save_settings()

    def _on_note_sel(self,m_idx,n_idx):
        if 0<=m_idx<len(self.score.measures):
            m=self.score.measures[m_idx]
            if 0<=n_idx<len(m.notes):
                self.note_editor.load_note(m.notes[n_idx],m_idx,n_idx)

    def _apply_dyn_to_selection(self,dyn):
        """Apply dynamic to selected note or current measure."""
        sn=self.staff_canvas.get_selected_note()
        if sn:
            sn.dynamic=dyn
            self._on_change()
            self.status_var.set(f"Applied dynamic '{dyn}' to note.")
        elif 0<=self.staff_canvas.sel_m<len(self.score.measures):
            m=self.score.measures[self.staff_canvas.sel_m]
            m.dynamic=dyn
            self._on_change()
            self.status_var.set(f"Applied dynamic '{dyn}' to measure {m.number}.")
        else:
            self.status_var.set("Select a note or measure first, then apply dynamic.")

    def _apply_art_to_selection(self,art):
        sn=self.staff_canvas.get_selected_note()
        if sn:
            sn.articulation=art; sn.special=art if art in ('slur','tie') else sn.special
            self._on_change()
            self.status_var.set(f"Applied articulation '{art}' to note.")
        else:
            self.status_var.set("Select a note first, then apply articulation.")

    def _on_tab(self,event):
        tab=self.nb.tab(self.nb.select(),'text')
        if 'Reference' in tab: self.ref_panel._draw()
        elif 'Trad'    in tab: self.trad_canvas.redraw()
        elif 'Staff'   in tab: self.staff_canvas.redraw()
        elif 'Text'    in tab: self.solfa_panel.refresh_from_score()
        self._update_info()

    def _update_title(self):
        mod=" *" if self.modified else ""
        path=f"  [{os.path.basename(self.filepath)}]" if self.filepath else ""
        self.title(f"{APP_NAME}  —  {self.score.title}{path}{mod}")

    def _update_info(self):
        s=self.score; vs=s.all_voices()
        n=sum(len(m.notes) for m in s.measures)
        self.info_var.set(
            f"Key: {s.key_sig}  |  {s.time_num}/{s.time_den}  |  ♩={s.tempo_bpm}  |  "
            f"{len(s.measures)} bar{'s' if len(s.measures)!=1 else ''}  |  "
            f"{n} note{'s' if n!=1 else ''}  |  "
            f"{', '.join(VOICE_NAMES.get(v,str(v)) for v in vs)}")

    # ── Undo/Redo ─────────────────────────────────────
    def _snap(self):
        try:
            self._hist.append(json.dumps(self.score.to_dict()))
            self._redo.clear()
        except: pass

    def _undo(self):
        if len(self._hist)>1:
            self._redo.append(self._hist.pop())
            self.score=Score.from_dict(json.loads(self._hist[-1]))
            self.smart_entry.score=self.score
            self._reload(); self.status_var.set("Undo")
        else: self.status_var.set("Nothing to undo")

    def _redo_cmd(self):
        if self._redo:
            snap=self._redo.pop(); self._hist.append(snap)
            self.score=Score.from_dict(json.loads(snap))
            self.smart_entry.score=self.score
            self._reload(); self.status_var.set("Redo")
        else: self.status_var.set("Nothing to redo")

    def _reload(self):
        self.trad_canvas.set_score(self.score)
        self.staff_canvas.set_score(self.score)
        self.solfa_panel.set_score(self.score)
        self.props_panel.refresh(self.score)
        self.note_editor.score=self.score
        self._update_title(); self._update_info()

    # ── File Operations ───────────────────────────────
    def _confirm(self)->bool:
        if self.modified:
            return messagebox.askyesno("Unsaved Changes","Discard changes and continue?",parent=self)
        return True

    def _new(self):
        if not self._confirm(): return
        self.score=Score(title="Untitled Score"); self.score.ensure_measures(8)
        self.smart_entry=SmartEntry(self.score,on_change=self._on_change)
        self.filepath=None; self.modified=False
        self._hist.clear(); self._redo.clear(); self._snap()
        self._initial_render(); self.status_var.set("New score created.")

    def _open(self):
        if not self._confirm(): return
        path=filedialog.askopenfilename(title="Open Project",
            filetypes=[("TSS Project","*.tss *.json"),("All Files","*.*")],parent=self)
        if not path: return
        try:
            with open(path,'r',encoding='utf-8') as f:
                self.score=Score.from_dict(json.load(f))
            self.smart_entry=SmartEntry(self.score,on_change=self._on_change)
            self.filepath=path; self.modified=False
            self._hist.clear(); self._redo.clear(); self._snap()
            self._initial_render(); self.status_var.set(f"Opened: {path}")
        except Exception as e:
            messagebox.showerror("Open Error",str(e),parent=self)

    def _save(self):
        if self.filepath: self._write(self.filepath)
        else: self._save_as()

    def _save_as(self):
        path=filedialog.asksaveasfilename(title="Save Project",defaultextension=".tss",
            filetypes=[("TSS Project","*.tss"),("JSON","*.json")],parent=self)
        if path: self._write(path)

    def _write(self,path):
        try:
            with open(path,'w',encoding='utf-8') as f:
                json.dump(self.score.to_dict(),f,indent=2,ensure_ascii=False)
            self.filepath=path; self.modified=False
            self._update_title(); self.status_var.set(f"Saved: {path}")
        except Exception as e:
            messagebox.showerror("Save Error",str(e),parent=self)

    # ── Import ────────────────────────────────────────
    def _load_file(self,path):
        ext=os.path.splitext(path)[1].lower()
        try:
            if ext in ('.tss','.json'):
                with open(path,'r',encoding='utf-8') as f: self.score=Score.from_dict(json.load(f))
            elif ext in ('.xml','.musicxml','.mxl'):
                self.score=ConversionEngine.import_mxl(path)
            elif ext in ('.mid','.midi'):
                self.score=ConversionEngine.import_midi(path)
            elif ext=='.wav':
                self.score=ConversionEngine.import_wav(path)
            elif ext in ('.musx','.mus','.enig','.enigma','.finale'):
                self.score=ConversionEngine.import_finale(path)
            elif ext=='.abc':
                self.score=ConversionEngine.import_abc(path)
            else:
                messagebox.showwarning("Unsupported",f"Format not supported: {ext}",parent=self); return
            self.smart_entry=SmartEntry(self.score,on_change=self._on_change)
            self.filepath=None; self.modified=True
            self._hist.clear(); self._redo.clear(); self._snap()
            self._initial_render()
            vs=self.score.all_voices()
            self.status_var.set(
                f"✓ Loaded: {os.path.basename(path)}  "
                f"({len(self.score.measures)} bars, "
                f"{', '.join(VOICE_NAMES.get(v,str(v)) for v in vs)})")
        except Exception as e:
            messagebox.showerror("Load Error",str(e),parent=self)

    def _import_mxl(self):
        if not self._confirm(): return
        path=filedialog.askopenfilename(title="Import MusicXML/MXL",
            filetypes=[("MusicXML/MXL","*.xml *.musicxml *.mxl"),("All","*.*")],parent=self)
        if path: self._load_file(path)

    def _import_midi(self):
        if not self._confirm(): return
        path=filedialog.askopenfilename(title="Import MIDI",
            filetypes=[("MIDI","*.mid *.midi"),("All","*.*")],parent=self)
        if path: self._load_file(path)

    def _import_wav(self):
        if not self._confirm(): return
        path=filedialog.askopenfilename(title="Import WAV",
            filetypes=[("WAV","*.wav"),("All","*.*")],parent=self)
        if path: self._load_file(path)

    def _import_finale(self):
        if not self._confirm(): return
        path=filedialog.askopenfilename(title="Import Finale 2012/2014",
            filetypes=[("Finale Files","*.musx *.mus *.enigma"),
                        ("All","*.*")],parent=self)
        if path: self._load_file(path)

    def _import_abc(self):
        if not self._confirm(): return
        path=filedialog.askopenfilename(title="Import ABC",
            filetypes=[("ABC","*.abc"),("All","*.*")],parent=self)
        if path: self._load_file(path)

    # ── Export ────────────────────────────────────────
    def _export_mxml(self):
        path=filedialog.asksaveasfilename(title="Export MusicXML",defaultextension=".xml",
            filetypes=[("MusicXML","*.xml"),("All","*.*")],parent=self)
        if not path: return
        try:
            with open(path,'w',encoding='utf-8') as f: f.write(ConversionEngine.export_musicxml(self.score))
            self.status_var.set(f"✓ MusicXML: {path}")
            messagebox.showinfo("Export",f"Saved:\n{path}",parent=self)
        except Exception as e: messagebox.showerror("Export Error",str(e),parent=self)

    def _export_midi(self):
        path=filedialog.asksaveasfilename(title="Export MIDI",defaultextension=".mid",
            filetypes=[("MIDI","*.mid"),("All","*.*")],parent=self)
        if not path: return
        try:
            with open(path,'wb') as f: f.write(ConversionEngine.export_midi_bytes_harmony(self.score))
            self.status_var.set(f"✓ MIDI: {path}")
            messagebox.showinfo("Export",f"Saved:\n{path}",parent=self)
        except Exception as e: messagebox.showerror("MIDI Error",str(e),parent=self)

    def _export_abc(self):
        path=filedialog.asksaveasfilename(title="Export ABC",defaultextension=".abc",
            filetypes=[("ABC","*.abc"),("All","*.*")],parent=self)
        if not path: return
        try:
            with open(path,'w',encoding='utf-8') as f: f.write(ConversionEngine.export_abc(self.score))
            self.status_var.set(f"✓ ABC: {path}")
        except Exception as e: messagebox.showerror("Export Error",str(e),parent=self)

    def _export_solfa_txt(self):
        path=filedialog.asksaveasfilename(title="Export Tonic Solfa Text",defaultextension=".txt",
            filetypes=[("Text","*.txt"),("All","*.*")],parent=self)
        if not path: return
        try:
            with open(path,'w',encoding='utf-8') as f: f.write(ConversionEngine.export_solfa_text(self.score))
            self.status_var.set(f"✓ Solfa text: {path}")
            messagebox.showinfo("Export",f"Saved:\n{path}",parent=self)
        except Exception as e: messagebox.showerror("Export Error",str(e),parent=self)

    def _print_trad_solfa(self):
        """Default print: Traditional Tonic Solfa (matches dashboard)."""
        path=filedialog.asksaveasfilename(title="Save Traditional Solfa PDF",
            defaultextension=".pdf",filetypes=[("PDF","*.pdf"),("All","*.*")],parent=self)
        if not path: return
        try:
            ConversionEngine.export_pdf_solfa_traditional(self.score,path)
            self.status_var.set(f"✓ Traditional Solfa PDF: {path}")
            messagebox.showinfo("Print",f"Traditional Tonic Solfa PDF saved:\n{path}",parent=self)
        except Exception as e: messagebox.showerror("Print Error",str(e),parent=self)

    # ── Edit ──────────────────────────────────────────
    def _add_measure(self):
        self.score.add_measure(); self._on_change()
        self.status_var.set(f"Added measure {len(self.score.measures)}")

    def _del_measure(self):
        if len(self.score.measures)>1:
            self.score.measures.pop(); self._on_change()
            self.status_var.set("Deleted last measure.")

    def _clear(self):
        if messagebox.askyesno("Clear All","Delete all measures?",parent=self):
            self.score.measures.clear(); self.score.ensure_measures(8)
            self._on_change(); self.status_var.set("Cleared.")

    def _score_props(self):
        win=tk.Toplevel(self,bg=PANEL); win.title("Score Properties")
        win.geometry("480x400"); win.transient(self); win.grab_set()
        fields=[("Title",'title'),("Composer",'composer'),
                ("Lyricist",'lyricist'),("Arranger",'arranger'),("Tempo",'tempo_bpm')]
        vs={}
        for i,(lbl,attr) in enumerate(fields):
            tk.Label(win,text=lbl+':',bg=PANEL,fg=MUTED,font=('Arial',9)).grid(row=i,column=0,padx=15,pady=6,sticky='e')
            var=tk.StringVar(value=str(getattr(self.score,attr,'')))
            tk.Entry(win,textvariable=var,bg=DARK,fg=WHITE,insertbackground=WHITE,
                relief='flat',font=('Arial',10),width=30).grid(row=i,column=1,padx=5,sticky='w')
            vs[attr]=var
        # Key/time
        row=len(fields)
        tk.Label(win,text="Key:",bg=PANEL,fg=MUTED,font=('Arial',9)).grid(row=row,column=0,padx=15,pady=6,sticky='e')
        kv=tk.StringVar(value=self.score.key_sig)
        ttk.Combobox(win,textvariable=kv,values=KEYS,width=8,state='readonly').grid(row=row,column=1,sticky='w')
        row+=1
        tk.Label(win,text="Time:",bg=PANEL,fg=MUTED,font=('Arial',9)).grid(row=row,column=0,padx=15,pady=6,sticky='e')
        tv=tk.StringVar(value=f"{self.score.time_num}/{self.score.time_den}")
        ttk.Combobox(win,textvariable=tv,values=TIME_SIGS,width=8,state='readonly').grid(row=row,column=1,sticky='w')
        row+=1
        tk.Label(win,text="Solfa Font:",bg=PANEL,fg=MUTED,font=('Arial',9)).grid(row=row,column=0,padx=15,pady=6,sticky='e')
        sfv=tk.StringVar(value=SOLFA_FONT_FAMILY)
        ttk.Combobox(win,textvariable=sfv,values=list(ENGRAVER_FONTS.keys()),width=12,state='readonly').grid(row=row,column=1,sticky='w')
        row+=1
        tk.Label(win,text="Lyric Font:",bg=PANEL,fg=MUTED,font=('Arial',9)).grid(row=row,column=0,padx=15,pady=6,sticky='e')
        lfv=tk.StringVar(value=LYRIC_FONT_FAMILY)
        ttk.Combobox(win,textvariable=lfv,values=list(ENGRAVER_FONTS.keys()),width=12,state='readonly').grid(row=row,column=1,sticky='w')
        def apply():
            global SOLFA_FONT_FAMILY, LYRIC_FONT_FAMILY
            for attr,var in vs.items():
                val=var.get()
                if attr=='tempo_bpm':
                    try: self.score.tempo_bpm=int(val)
                    except: pass
                else: setattr(self.score,attr,val)
            self.score.key_sig=kv.get()
            for m in self.score.measures: m.key_sig=kv.get()
            try:
                num,den=map(int,tv.get().split('/'))
                self.score.time_num=num; self.score.time_den=den
                for m in self.score.measures: m.time_num=num; m.time_den=den
            except: pass
            SOLFA_FONT_FAMILY = sfv.get()
            LYRIC_FONT_FAMILY = lfv.get()
            self._on_change(); self.props_panel.refresh(self.score); win.destroy()
        tk.Button(win,text="Apply",bg=ACCENT,fg=WHITE,relief='flat',
            command=apply).grid(row=row+1,column=1,pady=14,sticky='e',padx=5)
        tk.Button(win,text="Cancel",bg=DARK,fg=TEXT,relief='flat',
            command=win.destroy).grid(row=row+1,column=0,pady=14,sticky='w',padx=5)

    def _add_lyrics(self):
        win=tk.Toplevel(self,bg=PANEL); win.title("Add / Edit Lyrics")
        win.geometry("540,380"); win.geometry("540x380"); win.transient(self)
        tk.Label(win,text="Lyrics for Voice 1 (one word/syllable per note):",
            bg=PANEL,fg=GOLD,font=('Arial',9,'bold')).pack(pady=8,padx=10,anchor='w')
        existing=[n.lyric for m in self.score.measures for n in m.notes if n.voice==1 and not n.rest]
        txt=tk.Text(win,bg=DARK,fg=WHITE,insertbackground=WHITE,font=('Arial',10),relief='flat',height=12,padx=10)
        txt.pack(fill='both',expand=True,padx=10,pady=5)
        txt.insert('1.0','\n'.join(existing))
        def apply():
            words=txt.get('1.0','end').strip().replace('\n',' ').split()
            idx=0
            for m in self.score.measures:
                for n in m.notes:
                    if n.voice==1 and not n.rest:
                        n.lyric=words[idx] if idx<len(words) else ''; idx+=1
            self._on_change(); win.destroy()
        tk.Button(win,text="Apply Lyrics",bg=GREEN,fg=DARK,relief='flat',
            font=('Arial',9,'bold'),command=apply).pack(pady=8)

    def _autofill_rests(self):
        filled=0
        for m in self.score.measures:
            for voice in [1,2,3,4]:
                used=m.beats_used_for_voice(voice)
                avail=m.beats_available
                remaining=avail-used
                bu=4.0/m.time_den
                if remaining>=bu-0.01 and not m.voice_notes(voice):
                    while remaining>=bu-0.01:
                        m.notes.append(MusNote(rest=True,duration=bu,voice=voice))
                        remaining-=bu
                    filled+=1
        self._on_change(); self.status_var.set(f"Filled {filled} empty voice slots.")

    def _add_repeat(self,rtype):
        if not self.score.measures:
            messagebox.showwarning("Repeat","No measures.",parent=self); return
        m=self.score.measures[-1]
        if rtype=='repeat_start':   m.repeat_start=True
        elif rtype=='repeat_end':   m.repeat_end=True
        elif rtype=='double_bar':   m.double_bar=True
        self._on_change()

    # ── Tools ─────────────────────────────────────────
    def _to_solfa(self):
        self.solfa_panel.refresh_from_score()
        self.trad_canvas.set_score(self.score)
        self.nb.select(0); self.status_var.set("✓ Converted to tonic solfa — Traditional view updated.")

    def _transpose(self):
        win=tk.Toplevel(self,bg=PANEL); win.title("Transpose")
        win.geometry("340x220"); win.transient(self); win.grab_set()
        tk.Label(win,text="Transpose Score",bg=PANEL,fg=GOLD,font=('Arial',12,'bold')).pack(pady=10)
        r1=tk.Frame(win,bg=PANEL); r1.pack(pady=5)
        tk.Label(r1,text="Semitones:",bg=PANEL,fg=TEXT).pack(side='left',padx=5)
        sv=tk.IntVar(value=0)
        tk.Spinbox(r1,from_=-12,to=12,textvariable=sv,bg=DARK,fg=WHITE,width=5).pack(side='left')
        r2=tk.Frame(win,bg=PANEL); r2.pack(pady=5)
        tk.Label(r2,text="New Key:",bg=PANEL,fg=TEXT).pack(side='left',padx=5)
        kv=tk.StringVar(value=self.score.key_sig)
        ttk.Combobox(r2,textvariable=kv,values=KEYS,width=8,state='readonly').pack(side='left')
        def do_it():
            semis=sv.get()
            if semis:
                for m in self.score.measures:
                    for n in m.notes:
                        if not n.rest:
                            nm=n.midi_num+semis
                            n.pitch=CHROM_TO_NOTE.get(nm%12,'C')
                            n.octave=(nm//12)-1
            self.score.key_sig=kv.get()
            for m in self.score.measures: m.key_sig=kv.get()
            self._on_change(); self.status_var.set(f"Transposed {semis:+d} → {kv.get()}"); win.destroy()
        tk.Button(win,text="Transpose",bg=ACCENT,fg=WHITE,relief='flat',command=do_it).pack(pady=15)

    def _quick_transpose(self,semis):
        for m in self.score.measures:
            for n in m.notes:
                if not n.rest:
                    nm=n.midi_num+semis
                    n.pitch=CHROM_TO_NOTE.get(nm%12,'C')
                    n.octave=(nm//12)-1
        fifths=KEY_SIGS.get(self.score.key_sig,0)+semis
        self.score.key_sig=FIFTHS_TO_KEY.get(fifths%12,self.score.key_sig)
        for m in self.score.measures: m.key_sig=self.score.key_sig
        self._on_change()
        self.status_var.set(f"Transposed {semis:+d} semitone(s) → {self.score.key_sig}")

    # ── Playback ──────────────────────────────────────
    def _play(self):
        if not PYGAME_OK:
            messagebox.showinfo("Playback","Install pygame:\npip install pygame",parent=self); return
        try:
            mid=ConversionEngine.export_midi_bytes_harmony(self.score)
            pygame.mixer.music.load(io.BytesIO(mid))
            pygame.mixer.music.play()
            vs=self.score.all_voices()
            self.status_var.set(f"▶ Playing {len(vs)} voices: "
                                f"{', '.join(VOICE_NAMES.get(v,str(v)) for v in vs)}")
        except Exception as e:
            messagebox.showerror("Playback Error",str(e),parent=self)

    def _stop(self):
        if PYGAME_OK:
            try: pygame.mixer.music.stop()
            except: pass
        self.status_var.set("⏹ Stopped.")
        if self.smart_entry.active:
            pass  # keep smart entry active

    # ── Info Dialogs ──────────────────────────────────
    def _lib_status(self):
        messagebox.showinfo("Library Status",
            f"midiutil   : {'✓' if MIDIUTIL_OK  else '✗  pip install midiutil'}\n"
            f"reportlab  : {'✓' if REPORTLAB_OK else '✗  pip install reportlab'}\n"
            f"pygame     : {'✓' if PYGAME_OK    else '✗  pip install pygame'}\n"
            f"mido       : {'✓' if MIDO_OK      else '✗  pip install mido'}\n\n"
            "Core features work without libraries.\n"
            "midiutil→MIDI export  reportlab→PDF  pygame→Playback  mido→MIDI import",
            parent=self)

    def _open_font_styles(self):
        try:
            FontStylesDialog(self, self.font_manager)
        except Exception as e:
            messagebox.showerror("Font Style Manager", str(e), parent=self)

    def _open_lyrics_manager(self):
        try:
            win = tk.Toplevel(self)
            win.title("Lyrics Manager")
            win.geometry("760x560")
            LyricsEditorPanel(win, self.lyrics_manager).pack(fill='both', expand=True)
        except Exception as e:
            messagebox.showerror("Lyrics Manager", str(e), parent=self)

    def _render_wav_from_score(self):
        if not os.path.isdir(os.path.dirname(self.filepath or '')):
            default_dir = os.getcwd()
        else:
            default_dir = os.path.dirname(self.filepath)
        out_path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension='.wav',
            filetypes=[('WAV Audio', '*.wav')],
            initialdir=default_dir,
            title='Export Score as WAV'
        )
        if not out_path:
            return

        try:
            self.audio_config.tempo_bpm = self.score.tempo_bpm
            self.audio_config.instrument = Instrument.PIANO
            synth = AudioSynthesizer(self.audio_config)
            samples = synth.generate_from_score(self.score)
            WavFileWriter.write_wav(out_path, samples, self.audio_config)
            messagebox.showinfo('WAV Export', f'WAV saved to:\n{out_path}', parent=self)
        except Exception as e:
            messagebox.showerror('WAV Export Error', str(e), parent=self)

    def _guide(self):
        text="""TONIC SOLFA STUDIO v6.0 — Quick Guide
══════════════════════════════════════════════════

PRIMARY VIEW: Traditional Solfa (Tab 0)
  ∙ Matches historical SATB hymn-book layout (see reference images)
  ∙ Voice labels: Sop. Alto Ten. Bass with curly brace {
  ∙ Beats separated by ':' barlines '|' 
  ∙ '—' = held beat   ' = high octave   , = low octave
  ∙ d'=high Do (superscript)   d,=low Do (subscript)
  ∙ Underlines: _ = half note   == = whole note   · = eighth
  ∙ Bar numbers shown above each system
  ∙ Dynamic markings in red italic
  ∙ Ctrl+P → Print Traditional Solfa PDF (THIS is the default print)

STAFF NOTATION (Tab 1):
  ∙ Grand staff: SA treble + TB bass
  ∙ Editable: click with tool selected to add/erase notes
  ∙ LEFT PALETTE: full tool set (Duration, Voice, Dynamic, Articulation, etc.)
  ∙ Voice capacity is PER-VOICE — each SATB part fills independently
  ∙ Right-click measure for key/time/dynamic/repeat options

SMART ENTRY (keyboard-driven):
  ∙ Click "Smart Entry" button or keyboard shortcut to activate
  ∙ d r m f s l t → enter Do Re Mi Fa Sol La Ti
  ∙ 1-7 → same as d r m f s l t
  ∙ 0 → rest
  ∙ q=whole  w=half  e=quarter  a=eighth  z=16th
  ∙ .=dotted   +=octave up   -=octave down
  ∙ #=sharp   b=flat
  ∙ Backspace=delete last   [=prev measure   ]=next measure

DYNAMICS (now working):
  ∙ Select a note or measure, then click a dynamic button in palette
  ∙ Note dynamics: shown in red above note on staff, red italic in solfa
  ∙ Measure dynamics: shown at measure start
  ∙ All MIDI export respects dynamics

IMPORT FORMATS:
  ∙ MusicXML (.mxl, .xml) — full SATB via root XML
  ∙ MIDI (.mid) — auto-converts to SATB by channel (requires mido)
  ∙ WAV (.wav) — creates placeholder score (pitch detection needs aubio)
  ∙ Finale 2012/2014 (.musx, .mus) — embedded XML extracted
  ∙ ABC (.abc) — melody import

KEYBOARD SHORTCUTS:
  Ctrl+N  New         Ctrl+O  Open        Ctrl+S  Save
  Ctrl+P  Print PDF   Ctrl+Z  Undo        Ctrl+Y  Redo
  Ctrl+M  +Measure    Ctrl+T  Transpose   Ctrl+I  Score Props
  Ctrl+1-5  Switch tabs
  Ctrl+↑/↓  Quick transpose ±1 semitone
  Space   Play        Esc     Stop/Select
  n=Note tool  r=Rest  e=Erase  l=Lyric  d=Dynamic
  q=Whole  w=Half  E=Quarter  a=Eighth  z=16th (durations)
"""
        win=tk.Toplevel(self,bg=DARK); win.title("Quick Guide"); win.geometry("600x560")
        t=tk.Text(win,bg=DARK,fg=TEXT,font=('Courier New',10),relief='flat',padx=20,pady=20,wrap='word')
        t.pack(fill='both',expand=True)
        t.insert('1.0',text); t.config(state='disabled')

    def _shortcuts(self):
        messagebox.showinfo("Keyboard Shortcuts",
            "Ctrl+N  New Score\n"
            "Ctrl+O  Open Project\n"
            "Ctrl+S  Save\n"
            "Ctrl+P  Print Traditional Solfa PDF\n"
            "Ctrl+Z  Undo   Ctrl+Y  Redo\n"
            "Ctrl+M  Add Measure\n"
            "Ctrl+T  Transpose\n"
            "Ctrl+I  Score Properties\n"
            "Ctrl+1-5  Switch View Tabs\n"
            "Ctrl+↑/↓  Transpose ±1 Semitone\n"
            "Space  Play   Esc  Stop\n"
            "n=Note  r=Rest  e=Erase  l=Lyric  d=Dynamic\n"
            "q=Whole  w=Half  E=Quarter  a=Eighth  z=16th\n"
            "SMART ENTRY: d r m f s l t + # b + . + ± oct",parent=self)

    def _about(self):
        messagebox.showinfo(f"About {APP_NAME}",
            f"{APP_NAME}  v{APP_VERSION}\n\n"
            "Professional Music Notation & Tonic Solfa Software\n"
            "Staff Notation ↔ Traditional Tonic Solfa (SATB)\n\n"
            "v6.0 features:\n"
            "  ✅ Import: MusicXML, MIDI, WAV, Finale 2012/2014, ABC\n"
            "  ✅ Traditional Solfa as DEFAULT print (Ctrl+P)\n"
            "  ✅ Bar numbers on traditional solfa dashboard\n"
            "  ✅ SATB palette with all notation tools\n"
            "  ✅ Dynamics WORK — applied to notes AND measures\n"
            "  ✅ Dynamic affects MIDI velocity on export\n"
            "  ✅ Staff notation: voice-aware measure capacity\n"
            "  ✅ Smart Entry keyboard note input\n"
            "  ✅ d'=high Do (superscript)  d,=low Do (subscript)\n"
            "  ✅ Articulations: staccato, accent, tenuto, fermata…\n"
            "  ✅ Full keyboard shortcut coverage\n"
            "  ✅ Scrollable tool palette in staff view\n\n"
            "Formats: MusicXML, MIDI, WAV, PDF, ABC, TSS",parent=self)

    def _quit(self):
        if not self._confirm(): return
        self._save_settings()
        if PYGAME_OK:
            try: pygame.quit()
            except: pass
        self.destroy()


# ═══════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════
def _sep(parent):
    tk.Frame(parent,bg='#2a3a5a',width=1).pack(side='left',fill='y',padx=5,pady=6)

def _tooltip(widget,text:str):
    tip=None
    def show(e):
        nonlocal tip
        x=widget.winfo_rootx()+10; y=widget.winfo_rooty()+widget.winfo_height()+3
        tip=tk.Toplevel(widget); tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        tk.Label(tip,text=text,bg='#ffffcc',fg='#333333',
            relief='solid',font=('Arial',8),padx=4,pady=2).pack()
    def hide(e):
        nonlocal tip
        if tip:
            try: tip.destroy()
            except: pass
            tip=None
    widget.bind('<Enter>',show); widget.bind('<Leave>',hide)


# ═══════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════
def main():
    print("="*62)
    print(f"  {APP_NAME}  v{APP_VERSION}")
    print("="*62)
    print(f"  midiutil   : {'✓' if MIDIUTIL_OK  else '✗  pip install midiutil'}")
    print(f"  reportlab  : {'✓' if REPORTLAB_OK else '✗  pip install reportlab'}")
    print(f"  pygame     : {'✓' if PYGAME_OK    else '✗  pip install pygame'}")
    print(f"  mido       : {'✓' if MIDO_OK      else '✗  pip install mido'}")
    print("="*62)
    print()
    print("  v6.0 changes:")
    print("  • Import WAV, MIDI, Finale 2012/2014 files")
    print("  • Traditional Solfa is PRIMARY print (Ctrl+P)")
    print("  • Bar numbers on trad solfa dashboard")
    print("  • Full SATB palette (dynamics WORK, articulations)")
    print("  • Staff: voice-aware capacity (no false 'full' errors)")
    print("  • Smart Entry keyboard mode (d r m f s l t)")
    print("  • d'=high Do (superscript)  d,=low Do (subscript)")
    print("  • All keyboard shortcuts active")
    print()
    app=TonicSolfaStudio()
    app.mainloop()

if __name__=='__main__':
    main()
