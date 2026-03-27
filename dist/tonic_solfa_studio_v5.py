#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════╗
║   TONIC SOLFA STUDIO  v5.0                               ║
║   Professional Music Notation & Tonic Solfa Software     ║
║   Staff Notation ↔ Traditional Tonic Solfa  (SATB)       ║
║   MusicXML · MIDI · PDF · ABC · TSS Project              ║
╚══════════════════════════════════════════════════════════╝

Install optional libs:
    pip install midiutil reportlab pygame pillow
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import json, os, math, copy, struct, io, zipfile
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

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
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.units import mm
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

# ═══════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════
APP_NAME    = "Tonic Solfa Studio Pro"
APP_VERSION = "5.0"

# Dark UI
DARK = "#1a1a2e"; PANEL = "#16213e"; CARD = "#0f3460"
ACCENT = "#e94560"; GOLD = "#f5a623"; TEXT = "#eaeaea"
MUTED = "#8892a4"; GREEN = "#00d4aa"; WHITE = "#ffffff"
BLUE  = "#4fc3f7"; PURPLE = "#ce93d8"

# Paper (traditional solfa print)
PAPER_BG    = "#f5f0e4"
PAPER_INK   = "#140e04"
PAPER_LINE  = "#9a8060"
PAPER_BAR   = "#2a1800"
PAPER_LYRIC = "#1a3060"
PAPER_DYN   = "#8b0000"
PAPER_HEAD  = "#3a0000"
PAPER_VOICE = "#3e2f1d"  # voice label color for traditional SATB style

# Staff colours (dark bg)
STAFF_LINE_COL = "#4a6a90"
STAFF_BAR_COL  = "#7090b0"
LEDGER_COL     = "#4a6a90"
NOTE_COL       = "#e8e8e8"
NOTE_SEL       = "#e94560"

# Music theory maps
NOTE_TO_CHROM = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
CHROM_TO_NOTE = {0:'C',1:'C#',2:'D',3:'Eb',4:'E',5:'F',
                 6:'F#',7:'G',8:'Ab',9:'A',10:'Bb',11:'B'}
CHROM_TO_SOLFA = {
    0:'d',1:'di',2:'r',3:'ri',4:'m',
    5:'f',6:'fi',7:'s',8:'si',9:'l',10:'li',11:'t'
}
SUBSCRIPT = str.maketrans('0123456789','₀₁₂₃₄₅₆₇₈₉')
KEY_SIGS = {
    'C':0,'G':1,'D':2,'A':3,'E':4,'B':5,'F#':6,
    'Gb':-6,'Db':-5,'Ab':-4,'Eb':-3,'Bb':-2,'F':-1
}
FIFTHS_TO_KEY = {v:k for k,v in KEY_SIGS.items()}
KEYS = ['C','G','D','A','E','B','F#','Gb','Db','Ab','Eb','Bb','F']
TIME_SIGS = ['2/4','3/4','4/4','6/8','9/8','12/8','2/2','3/8','5/4']
VOICE_NAMES  = {1:'Sop.',2:'Alto',3:'Ten.',4:'Bass'}
VOICE_NAMES_FULL = {1:'Soprano',2:'Alto',3:'Tenor',4:'Bass'}
NOTE_STEPS   = ['C','D','E','F','G','A','B']
DUR_TYPE_MAP = {'whole':4.0,'half':2.0,'quarter':1.0,'eighth':0.5,
                '16th':0.25,'32nd':0.125,'64th':0.0625,'breve':8.0}
# Treble clef: top line = F5  slots from top: F5 E5 D5 C5 B4 A4 G4 F4 E4
# Bass clef:   top line = A3  slots from top: A3 G3 F3 E3 D3 C3 B2 A2 G2
TREBLE_TOP = ('F', 5)   # pitch, octave of top line
BASS_TOP   = ('A', 3)   # pitch, octave of top line
SHARP_TREBLE_SLOTS = [4, 7, 3, 6, 2, 5, 1]   # staff slots for sharps (treble)
FLAT_TREBLE_SLOTS  = [6, 3, 7, 4, 8, 5, 9]   # staff slots for flats  (treble)
SHARP_BASS_SLOTS   = [6, 9, 5, 8, 4, 7, 3]
FLAT_BASS_SLOTS    = [8, 5, 9, 6, 10, 7, 11]

def _xml_escape(s: str) -> str:
    return (s.replace('&','&amp;').replace('<','&lt;')
             .replace('>','&gt;').replace('"','&quot;'))

# ═══════════════════════════════════════════════════════
#  DATA MODEL
# ═══════════════════════════════════════════════════════
@dataclass
class MusNote:
    pitch:      str   = 'C'
    octave:     int   = 4
    duration:   float = 1.0     # quarter-note beats
    dotted:     bool  = False
    rest:       bool  = False
    tied:       bool  = False
    lyric:      str   = ''
    dynamic:    str   = ''
    accidental: str   = ''
    voice:      int   = 1       # 1=S 2=A 3=T 4=B
    special:    str   = ''
    x:          float = field(default=0.0, repr=False)
    y:          float = field(default=0.0, repr=False)

    @property
    def beats(self) -> float:
        b = self.duration
        if self.dotted: b *= 1.5
        return b

    @property
    def midi_num(self) -> int:
        base = NOTE_TO_CHROM.get(self.pitch.rstrip('#b'), 0)
        if '#' in self.pitch: base += 1
        if 'b' in self.pitch: base -= 1
        return max(0, min(127, base + (self.octave + 1) * 12))

    def solfa(self, key: str = 'C') -> str:
        if self.rest: return '—'
        kb = key.rstrip('#b')
        kc = NOTE_TO_CHROM.get(kb, 0)
        if '#' in key and len(key) > 1: kc = (kc + 1) % 12
        elif 'b' in key and len(key) > 1: kc = (kc - 1) % 12
        nb = self.pitch.rstrip('#b')
        nc = NOTE_TO_CHROM.get(nb, 0)
        if '#' in self.pitch: nc = (nc + 1) % 12
        elif 'b' in self.pitch: nc = (nc - 1) % 12
        syl = CHROM_TO_SOLFA.get((nc - kc) % 12, 'd')
        ref = 3 if self.voice >= 3 else 4
        if self.octave < ref:
            syl += str(ref - self.octave).translate(SUBSCRIPT)
        elif self.octave > ref:
            syl += "'" * (self.octave - ref)
        return syl

    def to_dict(self) -> dict:
        return {'pitch':self.pitch,'octave':self.octave,'duration':self.duration,
                'dotted':self.dotted,'rest':self.rest,'tied':self.tied,
                'lyric':self.lyric,'dynamic':self.dynamic,
                'accidental':self.accidental,'voice':self.voice,'special':self.special}

    @classmethod
    def from_dict(cls, d: dict) -> 'MusNote':
        n = cls()
        for k, v in d.items():
            if hasattr(n, k) and k not in ('x','y'):
                setattr(n, k, v)
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

    @property
    def beats_available(self) -> float:
        return self.time_num * (4.0 / self.time_den)

    @property
    def beats_used(self) -> float:
        return sum(n.beats for n in self.notes)

    def voice_notes(self, voice: int) -> List[MusNote]:
        return [n for n in self.notes if n.voice == voice]

    def all_voices(self) -> List[int]:
        vs = {n.voice for n in self.notes}
        return sorted(vs) if vs else []

    def beat_grid(self, voice: int, key: str) -> List[str]:
        """One solfa symbol per beat position, '—' = held."""
        notes = self.voice_notes(voice)
        if not notes: return [''] * self.time_num
        beat_unit = 4.0 / self.time_den
        num_beats = self.time_num
        grid: List[str] = [''] * num_beats
        pos = 0.0
        for n in notes:
            bi = int(round(pos / beat_unit))
            if bi >= num_beats: break
            sym = n.solfa(key)
            if n.rest: sym = '—'
            grid[bi] = sym
            held = int(round(n.beats / beat_unit))
            for k in range(1, held):
                if bi + k < num_beats:
                    grid[bi + k] = '—'
            pos += n.beats
        return grid

    def to_dict(self) -> dict:
        return {'notes':[n.to_dict() for n in self.notes],
                'time_num':self.time_num,'time_den':self.time_den,
                'key_sig':self.key_sig,'clef':self.clef,
                'tempo_bpm':self.tempo_bpm,'repeat_start':self.repeat_start,
                'repeat_end':self.repeat_end,'double_bar':self.double_bar,
                'number':self.number,'dynamic':self.dynamic}

    @classmethod
    def from_dict(cls, d: dict) -> 'Measure':
        m = cls()
        m.notes = [MusNote.from_dict(nd) for nd in d.get('notes', [])]
        for k in ['time_num','time_den','key_sig','clef','tempo_bpm',
                  'repeat_start','repeat_end','double_bar','number','dynamic']:
            if k in d: setattr(m, k, d[k])
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
    clef:      str           = "treble"
    measures:  List[Measure] = field(default_factory=list)

    def all_voices(self) -> List[int]:
        vs: set = set()
        for m in self.measures:
            for n in m.notes: vs.add(n.voice)
        return sorted(vs) if vs else [1]

    def add_measure(self) -> Measure:
        m = Measure(time_num=self.time_num, time_den=self.time_den,
                    key_sig=self.key_sig, clef=self.clef,
                    number=len(self.measures)+1)
        self.measures.append(m)
        return m

    def ensure_measures(self, n: int = 4):
        while len(self.measures) < n: self.add_measure()

    def to_dict(self) -> dict:
        return {'title':self.title,'composer':self.composer,
                'lyricist':self.lyricist,'arranger':self.arranger,
                'key_sig':self.key_sig,'time_num':self.time_num,
                'time_den':self.time_den,'tempo_bpm':self.tempo_bpm,
                'clef':self.clef,'measures':[m.to_dict() for m in self.measures]}

    @classmethod
    def from_dict(cls, d: dict) -> 'Score':
        s = cls()
        for k in ['title','composer','lyricist','arranger','key_sig',
                  'time_num','time_den','tempo_bpm','clef']:
            if k in d: setattr(s, k, d[k])
        s.measures = [Measure.from_dict(md) for md in d.get('measures',[])]
        return s


# ═══════════════════════════════════════════════════════
#  CONVERSION ENGINE
# ═══════════════════════════════════════════════════════
class ConversionEngine:

    SOLFA_TO_CHROM = {
        'd':0,'di':1,'ra':1,'r':2,'ri':3,'me':3,'m':4,
        'f':5,'fi':6,'se':6,'s':7,'si':8,'le':8,'l':9,'li':10,'te':10,'t':11,
    }

    # ── MXL / MusicXML import ─────────────────────────
    @staticmethod
    def import_mxl(path: str) -> Score:
        ext = os.path.splitext(path)[1].lower()
        if ext == '.mxl':
            return ConversionEngine._import_mxl_zip(path)
        return ConversionEngine._parse_xml_file(path)

    @staticmethod
    def _import_mxl_zip(path: str) -> Score:
        """
        Import .mxl (ZIP). Strategy:
          1. Read container.xml → find root file (e.g. HYMN.musicxml)
          2. Root file has all 4 voices (V1-V4 / Staff 1-2)
          3. p1.musicxml has only V1+V2 — skip it
        """
        with zipfile.ZipFile(path, 'r') as z:
            names = z.namelist()
            # Find root file via container
            root_file = None
            if 'META-INF/container.xml' in names:
                try:
                    ct = ET.fromstring(
                        z.read('META-INF/container.xml').decode('utf-8', errors='replace'))
                    rf = (ct.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile')
                          or ct.find('.//rootfile'))
                    if rf is not None:
                        root_file = rf.get('full-path')
                except Exception:
                    pass
            # Fallback: first .musicxml that isn't p1 or META
            if root_file is None:
                for n in names:
                    if (n.endswith('.musicxml') or (n.endswith('.xml') and 'META' not in n)):
                        if not n.startswith('p') or not n[1:2].isdigit():
                            root_file = n
                            break
                if root_file is None:
                    for n in names:
                        if n.endswith('.musicxml') or (n.endswith('.xml') and 'META' not in n):
                            root_file = n
                            break
            if root_file and root_file in names:
                for enc in ['utf-8','utf-16','latin-1']:
                    try:
                        text = z.read(root_file).decode(enc, errors='replace').lstrip('\ufeff')
                        score = ConversionEngine._parse_xml_text(text)
                        # Accept if we got 3+ voices or has measures
                        vs = score.all_voices()
                        if len(vs) >= 2 or any(m.notes for m in score.measures):
                            return score
                    except Exception:
                        continue
            # Last resort: try each xml file
            for n in names:
                if (n.endswith('.xml') or n.endswith('.musicxml')) and 'META' not in n:
                    try:
                        text = z.read(n).decode('utf-8', errors='replace').lstrip('\ufeff')
                        score = ConversionEngine._parse_xml_text(text)
                        vs = score.all_voices()
                        if vs:
                            return score
                    except Exception:
                        continue
            raise ValueError("No parseable MusicXML found in MXL archive.")

    @staticmethod
    def _parse_xml_file(path: str) -> Score:
        for enc in ['utf-8','utf-16','latin-1','cp1252']:
            try:
                with open(path, 'rb') as f:
                    raw = f.read()
                text = raw.decode(enc, errors='replace').lstrip('\ufeff').replace('\x00','')
                return ConversionEngine._parse_xml_text(text)
            except ET.ParseError:
                continue
        raise ValueError("Could not parse MusicXML file.")

    @staticmethod
    def _parse_xml_text(xml_text: str) -> Score:
        score = Score()
        root = ET.fromstring(xml_text)

        # Metadata
        wt = root.find('.//work-title')
        mt = root.find('.//movement-title')
        if wt is not None and wt.text: score.title = wt.text.strip()
        elif mt is not None and mt.text: score.title = mt.text.strip()
        comp = root.find('.//creator[@type="composer"]')
        lyr  = root.find('.//creator[@type="lyricist"]')
        if comp is not None and comp.text: score.composer = comp.text.strip()
        if lyr  is not None and lyr.text:  score.lyricist = lyr.text.strip()

        cur_divs  = 1
        cur_key   = 'C'
        cur_tnum  = 4
        cur_tden  = 4
        cur_clef  = 'treble'
        cur_tempo = 100

        for mel in root.findall('.//measure'):
            m = Measure()
            # Attributes
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
                    sm = t_el.find('senza-misura')
                    if sm is None:
                        be = t_el.find('beats')
                        bt = t_el.find('beat-type')
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
                        cur_clef = ('treble' if sg=='G' else 'bass' if sg=='F' else 'alto')
            # Tempo
            for snd in mel.findall('.//sound'):
                t = snd.get('tempo')
                if t:
                    try: cur_tempo = int(float(t))
                    except: pass
            # Dynamic
            for dirn in mel.findall('direction'):
                dyn_el = dirn.find('.//dynamics')
                if dyn_el is not None:
                    for child in dyn_el:
                        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                        m.dynamic = tag; break
            # Barlines
            for bl in mel.findall('barline'):
                rep = bl.find('repeat')
                if rep is not None:
                    if rep.get('direction') == 'forward':  m.repeat_start = True
                    if rep.get('direction') == 'backward': m.repeat_end   = True

            m.time_num  = cur_tnum; m.time_den  = cur_tden
            m.key_sig   = cur_key;  m.clef      = cur_clef
            m.tempo_bpm = cur_tempo; m.number   = len(score.measures)+1

            # Notes
            for nel in mel.findall('note'):
                n = MusNote()
                # Voice
                v_el = nel.find('voice')
                if v_el is not None and v_el.text:
                    try: n.voice = int(v_el.text)
                    except: pass
                # Staff → voice bump (staff 2 voices get +2 if not already >2)
                st_el = nel.find('staff')
                if st_el is not None and st_el.text:
                    try:
                        st = int(st_el.text)
                        if st == 2 and n.voice <= 2:
                            n.voice = n.voice + 2
                    except: pass
                # Chord → skip (we don't handle chords, take melody note)
                if nel.find('chord') is not None:
                    continue
                # Rest
                if nel.find('rest') is not None:
                    n.rest = True
                else:
                    pe = nel.find('pitch')
                    if pe is not None:
                        step  = pe.findtext('step','C')
                        alter = pe.findtext('alter','0')
                        octs  = pe.findtext('octave','4')
                        try: n.octave = int(octs)
                        except: n.octave = 4
                        try:
                            alt = int(float(alter))
                            n.pitch = step + ('#' if alt>0 else 'b' if alt<0 else '')
                        except: n.pitch = step
                # Duration
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
                m.notes.append(n)

            if m.notes or m.tempo_bpm:
                score.measures.append(m)

        if not score.measures: score.ensure_measures(4)
        if score.measures:
            first = score.measures[0]
            score.key_sig   = first.key_sig
            score.time_num  = first.time_num
            score.time_den  = first.time_den
            score.tempo_bpm = first.tempo_bpm or 100
            score.clef      = first.clef
        return score

    @staticmethod
    def import_musx(path: str) -> Score:
        score = Score(title=os.path.splitext(os.path.basename(path))[0])
        try:
            with zipfile.ZipFile(path, 'r') as z:
                names = z.namelist()
                # Try embedded XML
                xml_files = [n for n in names if
                             (n.endswith('.xml') or n.endswith('.musicxml'))
                             and 'META' not in n and 'metadata' not in n.lower()]
                if xml_files:
                    try:
                        text = z.read(xml_files[0]).decode('utf-8', errors='replace')
                        s = ConversionEngine._parse_xml_text(text)
                        if s.measures and any(m.notes for m in s.measures):
                            s.title = score.title; return s
                    except Exception: pass
                # Metadata only
                if 'NotationMetadata.xml' in names:
                    meta = ET.fromstring(
                        z.read('NotationMetadata.xml').decode('utf-8', errors='replace'))
                    fi = meta.find('.//fileInfo') or meta.find('.//{*}fileInfo')
                    if fi is not None:
                        ks = fi.findtext('keySignature') or fi.findtext('{*}keySignature')
                        tp = fi.findtext('initialTempo') or fi.findtext('{*}initialTempo')
                        if ks and ks in KEYS: score.key_sig = ks
                        if tp:
                            try: score.tempo_bpm = int(float(tp))
                            except: pass
        except zipfile.BadZipFile: pass
        score.ensure_measures(4)
        return score

    @staticmethod
    def import_abc(path: str) -> Score:
        score = Score(title=os.path.basename(path))
        import re
        for enc in ['utf-8','latin-1','cp1252']:
            try:
                with open(path, encoding=enc) as f: content = f.read()
                break
            except (UnicodeDecodeError, FileNotFoundError): continue
        else:
            score.ensure_measures(4); return score
        for line in content.split('\n'):
            line = line.strip()
            if   line.startswith('T:'): score.title    = line[2:].strip()
            elif line.startswith('C:'): score.composer = line[2:].strip()
            elif line.startswith('K:'):
                k = line[2:].strip().split()[0]
                score.key_sig = k if k in KEYS else 'C'
            elif line.startswith('M:'):
                tp = line[2:].strip()
                if '/' in tp:
                    try:
                        a, b = tp.split('/'); score.time_num=int(a); score.time_den=int(b)
                    except: pass
            elif line.startswith('Q:'):
                mm = re.search(r'\d+', line[2:])
                if mm:
                    try: score.tempo_bpm = int(mm.group())
                    except: pass
        score.ensure_measures(4)
        return score

    # ── Export ────────────────────────────────────────
    @staticmethod
    def export_musicxml(score: Score) -> str:
        fifths = KEY_SIGS.get(score.key_sig, 0)
        xml = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN"',
            '  "http://www.musicxml.org/dtds/partwise.dtd">',
            '<score-partwise version="3.1">',
            f'  <work><work-title>{_xml_escape(score.title)}</work-title></work>',
            '  <identification>',
            f'    <creator type="composer">{_xml_escape(score.composer)}</creator>',
            '    <encoding><software>Tonic Solfa Studio v5</software></encoding>',
            '  </identification>',
            '  <part-list><score-part id="P1"><part-name>Music</part-name></score-part></part-list>',
            '  <part id="P1">',
        ]
        for mi, meas in enumerate(score.measures):
            xml.append(f'    <measure number="{mi+1}">')
            if mi == 0:
                xml += [
                    '      <attributes>',
                    '        <divisions>4</divisions>',
                    f'        <key><fifths>{fifths}</fifths><mode>major</mode></key>',
                    f'        <time><beats>{meas.time_num}</beats>'
                    f'<beat-type>{meas.time_den}</beat-type></time>',
                    f'        <staves>2</staves>',
                    '        <clef number="1"><sign>G</sign><line>2</line></clef>',
                    '        <clef number="2"><sign>F</sign><line>4</line></clef>',
                    '      </attributes>',
                    f'      <direction><direction-type><metronome>'
                    f'<beat-unit>quarter</beat-unit><per-minute>{score.tempo_bpm}</per-minute>'
                    f'</metronome></direction-type></direction>',
                ]
            if meas.repeat_start:
                xml.append('      <barline location="left"><repeat direction="forward"/></barline>')
            for n in meas.notes:
                dur_div = max(1, int(round(n.duration*4)))
                if n.dotted: dur_div = int(dur_div*1.5)
                type_str = {4:'whole',2:'half',1:'quarter',0.5:'eighth',
                            0.25:'16th',0.125:'32nd'}.get(n.duration,'quarter')
                staff_num = '2' if n.voice >= 3 else '1'
                xml.append('      <note>')
                if n.rest:
                    xml.append('        <rest/>')
                else:
                    step = n.pitch.rstrip('#b')
                    alter = 1 if '#' in n.pitch else (-1 if 'b' in n.pitch else 0)
                    xml.append('        <pitch>')
                    xml.append(f'          <step>{step}</step>')
                    if alter: xml.append(f'          <alter>{alter}</alter>')
                    xml.append(f'          <octave>{n.octave}</octave>')
                    xml.append('        </pitch>')
                xml += [
                    f'        <duration>{dur_div}</duration>',
                    f'        <voice>{n.voice}</voice>',
                    f'        <type>{type_str}</type>',
                    f'        <staff>{staff_num}</staff>',
                ]
                if n.dotted: xml.append('        <dot/>')
                if n.tied:   xml.append('        <tie type="start"/>')
                if n.lyric:
                    xml += ['        <lyric number="1"><syllabic>single</syllabic>',
                            f'          <text>{_xml_escape(n.lyric)}</text></lyric>']
                xml.append('      </note>')
            if meas.repeat_end:
                xml.append('      <barline location="right">'
                           '<bar-style>light-heavy</bar-style>'
                           '<repeat direction="backward"/></barline>')
            xml.append('    </measure>')
        xml += ['  </part>', '</score-partwise>']
        return '\n'.join(xml)

    @staticmethod
    def export_abc(score: Score) -> str:
        def d2a(b):
            return {4:'4',2:'2',1:'',0.5:'/2',0.25:'/4'}.get(b,'')
        lines = ['X:1',f'T:{score.title}',f'C:{score.composer}',
                 f'M:{score.time_num}/{score.time_den}','L:1/4',
                 f'Q:{score.tempo_bpm}',f'K:{score.key_sig}']
        abc = []
        for meas in score.measures:
            mn = []
            for n in meas.notes:
                if n.voice != 1: continue
                if n.rest: mn.append(f'z{d2a(n.duration)}'); continue
                p = n.pitch.rstrip('#b')
                acc = '^' if '#' in n.pitch else ('_' if 'b' in n.pitch else '')
                if n.octave <= 3: pn = acc+p.upper()+','*(4-n.octave)
                elif n.octave == 4: pn = acc+p.upper()
                elif n.octave == 5: pn = acc+p.lower()
                else: pn = acc+p.lower()+"'"*(n.octave-5)
                mn.append(pn+d2a(n.duration))
            abc.append(''.join(mn)+'|')
        lines.append(' '.join(abc))
        return '\n'.join(lines)

    @staticmethod
    def export_solfa_text(score: Score) -> str:
        voices = score.all_voices()
        vnames = {1:'Soprano/Melody',2:'Alto',3:'Tenor',4:'Bass'}
        lines = [
            '═'*66,
            f'  {score.title}',
            f'  Composer: {score.composer}',
            f'  Key: {score.key_sig}  Time: {score.time_num}/{score.time_den}'
            f'  Tempo: ♩={score.tempo_bpm}',
            '═'*66,
            'TONIC SOLFA NOTATION  (Movable Do — SATB)',
            '─'*66,
        ]
        for voice in voices:
            lines.append(f'\n  ── {vnames.get(voice,f"Voice {voice}")} ──')
            row, lyrs = [], []
            for mi, meas in enumerate(score.measures):
                grid = meas.beat_grid(voice, score.key_sig)
                cell = ' : '.join(s if s else '·' for s in grid)
                row.append(f'| {cell} ')
                lyr = ' '.join(n.lyric for n in meas.voice_notes(voice) if n.lyric)
                lyrs.append(f'| {lyr:<{len(cell)+1}}')
                if (mi+1) % 4 == 0:
                    lines.append('  '+''.join(row)+'|')
                    if any(l.strip('| ') for l in lyrs):
                        lines.append('  '+''.join(lyrs)+'|')
                    row, lyrs = [], []
                    lines.append('')
            if row:
                lines.append('  '+''.join(row)+'|')
                if any(l.strip('| ') for l in lyrs):
                    lines.append('  '+''.join(lyrs)+'|')
        lines += ['','─'*66,
                  "KEY: d=Do r=Re m=Mi f=Fa s=Sol l=La t=Ti",
                  "     '=upper oct  ₁=lower oct  —=held/rest  ·=silent"]
        return '\n'.join(lines)

    @staticmethod
    def export_midi_bytes_harmony(score: Score) -> bytes:
        """
        Export MIDI with all 4 voices on separate tracks/channels,
        playing simultaneously like a full SATB arrangement.
        Each voice starts at beat 0 and plays its own notes.
        """
        voices = score.all_voices()
        if not voices: voices = [1]

        if MIDIUTIL_OK:
            num_tracks = len(voices)
            midi = MIDIFile(num_tracks)
            # MIDI channels: 0=S 1=A 2=T 3=B
            # Programs: 0=Piano for all (or customize)
            voice_progs = {1:0, 2:0, 3:0, 4:32}  # 32=Acoustic Bass (opt.)
            voice_vols  = {1:80, 2:72, 3:75, 4:85}

            for ti, voice in enumerate(voices):
                channel = ti % 16
                midi.addTempo(ti, 0, score.tempo_bpm)
                midi.addProgramChange(ti, channel, 0,
                                      voice_progs.get(voice, 0))
                t = 0.0
                for meas in score.measures:
                    notes = meas.voice_notes(voice)
                    if not notes:
                        # Advance by measure length
                        t += meas.beats_available
                        continue
                    for n in notes:
                        if not n.rest:
                            midi.addNote(ti, channel, n.midi_num, t,
                                         n.beats, voice_vols.get(voice, 75))
                        t += n.beats
            buf = io.BytesIO()
            midi.writeFile(buf)
            return buf.getvalue()

        # Raw MIDI fallback — multi-track
        tpb      = 480
        tempo_us = int(60_000_000 / max(1, score.tempo_bpm))

        def var_len(v):
            r = bytearray()
            r.insert(0, v & 0x7F); v >>= 7
            while v:
                r.insert(0, (v & 0x7F)|0x80); v >>= 7
            return bytes(r)

        def make_track(voice, channel):
            ev = bytearray()
            ev += b'\x00\xff\x51\x03' + struct.pack('>I', tempo_us)[1:]
            nm = (VOICE_NAMES_FULL.get(voice,'Voice')).encode('ascii','replace')[:20]
            ev += b'\x00\xff\x03' + bytes([len(nm)]) + nm
            t_cursor = 0
            for meas in score.measures:
                notes = meas.voice_notes(voice)
                if not notes:
                    # silence for measure length
                    ticks = int(meas.beats_available * tpb)
                    ev += var_len(ticks) + bytes([0x90, 0, 0])
                    continue
                for n in notes:
                    ticks = int(n.beats * tpb)
                    if not n.rest:
                        mn = n.midi_num
                        ev += var_len(0) + bytes([0x90 | channel, mn, 80])
                        ev += var_len(ticks) + bytes([0x80 | channel, mn, 0])
                    else:
                        ev += var_len(ticks) + bytes([0x90 | channel, 0, 0])
            ev += b'\x00\xff\x2f\x00'
            return b'MTrk' + struct.pack('>I', len(ev)) + bytes(ev)

        tracks = []
        for ti, voice in enumerate(voices):
            tracks.append(make_track(voice, ti % 16))
        hdr = b'MThd' + struct.pack('>IHHH', 6, 1, len(tracks), tpb)
        return hdr + b''.join(tracks)

    @staticmethod
    def export_pdf_solfa(score: Score, path: str):
        """Export traditional tonic solfa to PDF."""
        if not REPORTLAB_OK:
            txt = path.replace('.pdf', '_solfa.txt')
            with open(txt, 'w', encoding='utf-8') as f:
                f.write(ConversionEngine.export_solfa_text(score))
            messagebox.showinfo("PDF",
                f"ReportLab not installed. Saved as text:\n{txt}\npip install reportlab")
            return
        w, h = A4
        c = rl_canvas.Canvas(path, pagesize=A4)
        # Title block
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(w/2, h-28*mm, score.title)
        c.setFont("Helvetica", 12)
        if score.composer:
            c.drawCentredString(w/2, h-38*mm, score.composer)
        c.setFont("Helvetica-Oblique", 10)
        c.drawCentredString(w/2, h-46*mm,
            f"KEY: {score.key_sig}  |  {score.time_num}/{score.time_den}  |  ♩={score.tempo_bpm}")
        c.setFont("Helvetica-Bold", 11)
        c.drawString(15*mm, h-56*mm, "TONIC SOLFA NOTATION  (Movable Do — SATB)")
        c.setFont("Courier", 9)
        solfa = ConversionEngine.export_solfa_text(score)
        y = h - 65*mm
        for line in solfa.split('\n'):
            if y < 18*mm:
                c.showPage(); y = h-18*mm; c.setFont("Courier", 9)
            c.drawString(12*mm, y, line[:105])
            y -= 4.2*mm
        c.save()

    @staticmethod
    def export_pdf_staff(score: Score, path: str):
        """Export staff notation summary to PDF."""
        if not REPORTLAB_OK:
            messagebox.showinfo("PDF", "pip install reportlab for PDF export.")
            return
        w, h = A4
        c = rl_canvas.Canvas(path, pagesize=A4)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(w/2, h-28*mm, score.title)
        c.setFont("Helvetica", 11)
        if score.composer:
            c.drawCentredString(w/2, h-38*mm, score.composer)
        c.setFont("Helvetica-Oblique", 10)
        c.drawCentredString(w/2, h-46*mm,
            f"KEY: {score.key_sig}  |  {score.time_num}/{score.time_den}  |  ♩={score.tempo_bpm}")
        # Staff reference grid
        c.setFont("Helvetica-Bold", 10)
        c.drawString(15*mm, h-56*mm, "STAFF NOTATION  (SATB — Voice Reference)")
        y_ref = h - 65*mm
        voices = score.all_voices() or [1,2,3,4]
        for voice in voices:
            if y_ref < 25*mm: break
            vname = VOICE_NAMES_FULL.get(voice, f'Voice {voice}')
            c.setFont("Helvetica-Bold", 9)
            c.drawString(15*mm, y_ref, f"{vname}:")
            c.setFont("Courier", 8)
            notes_str = []
            for meas in score.measures:
                vnotes = meas.voice_notes(voice)
                if not vnotes: notes_str.append('—')
                else:
                    notes_str.append(' '.join(
                        '—' if n.rest else f'{n.pitch}{n.octave}'
                        for n in vnotes))
            row = '  |  '.join(notes_str)[:140]
            c.drawString(30*mm, y_ref - 5*mm, row)
            y_ref -= 16*mm
        c.save()


# ═══════════════════════════════════════════════════════
#  TRADITIONAL TONIC SOLFA CANVAS
#  Style matches historical SATB hymn book publications
# ═══════════════════════════════════════════════════════
class TraditionalSolfaCanvas(tk.Canvas):
    MARGIN_L  = 16
    MARGIN_T  = 16
    KEY_W     = 72    # width of key/time column
    LABEL_W   = 46    # width of voice label
    BEAT_W    = 32    # pixels per beat
    VOICE_H   = 28    # height per voice row
    LYRIC_H   = 20    # height of lyric row
    ROW_GAP   = 18    # gap between systems
    BRACE_W   = 8

    F_TITLE  = ('Times New Roman', 16, 'bold')
    F_SUB    = ('Times New Roman', 10)
    F_KEY    = ('Times New Roman', 11, 'bold')
    F_VOICE  = ('Times New Roman', 10, 'bold')
    F_SYL    = ('Times New Roman', 13, 'bold')
    F_SEP    = ('Times New Roman', 10)
    F_LYRIC  = ('Times New Roman', 9)
    F_DYN    = ('Times New Roman', 10, 'italic')
    F_MNUM   = ('Times New Roman', 7)

    def __init__(self, master, score: Score, **kwargs):
        super().__init__(master, bg=PAPER_BG, bd=0, highlightthickness=0, **kwargs)
        self.score = score
        self.bind('<Configure>', lambda e: self.after_idle(self.redraw))

    def set_score(self, score: Score):
        self.score = score; self.redraw()

    def redraw(self):
        self.delete('all')
        if not self.score or not self.score.measures:
            w = self.winfo_width() or 800
            self.create_text(w//2, 120,
                text="No music loaded — import a file or add notes",
                fill=PAPER_LINE, font=('Times New Roman',13), anchor='center')
            return
        self._draw_page()

    def _draw_page(self):
        s = self.score
        cw = self.winfo_width() or 900
        y = self.MARGIN_T

        # Title
        y += 12
        self.create_text(cw//2, y, text=s.title.upper(),
                         fill=PAPER_HEAD, font=self.F_TITLE, anchor='n')
        y += 24
        if s.composer:
            self.create_text(cw//2, y, text=s.composer,
                             fill=PAPER_INK, font=self.F_SUB, anchor='n')
            y += 16
        if s.lyricist:
            self.create_text(cw//2, y, text=s.lyricist,
                             fill=PAPER_INK, font=self.F_SUB, anchor='n')
            y += 14
        y += 8
        # Rule
        self.create_line(self.MARGIN_L, y, cw - self.MARGIN_L, y,
                         fill=PAPER_LINE, width=1)
        y += 8

        # Detect all voices — ensure we always show SATB if data available
        all_vs = s.all_voices()
        # If only 1-2 voices in data, still show them (don't pad fake voices)

        beat_num = s.time_num
        meas_w   = beat_num * self.BEAT_W + 4
        avail_w  = cw - self.MARGIN_L - self.KEY_W - self.LABEL_W - self.BRACE_W - 16
        mpr      = max(1, avail_w // meas_w)
        has_lyr  = any(n.lyric for mm in s.measures for n in mm.notes)

        rows = math.ceil(len(s.measures) / mpr)
        for row in range(rows):
            row_meas = s.measures[row*mpr:(row+1)*mpr]
            y = self._draw_system(y, row_meas, all_vs, s, row==0, has_lyr, cw)
            y += self.ROW_GAP

        self.configure(scrollregion=(0, 0, cw, y + 20))

    def _draw_system(self, y0, measures, voices, score, first_row, has_lyr, cw):
        # Split into upper (SA) and lower (TB) groups
        upper = [v for v in voices if v <= 2]
        lower = [v for v in voices if v > 2]
        groups = []
        if upper: groups.append(upper)
        if lower: groups.append(lower)
        if not groups: groups = [[1]]

        x_key   = self.MARGIN_L
        x_label = x_key + self.KEY_W
        x_music = x_label + self.LABEL_W + self.BRACE_W

        beat_num = score.time_num
        meas_w   = beat_num * self.BEAT_W + 4
        total_w  = len(measures) * meas_w
        x_end    = x_music + total_w
        y = y0

        for gi, group in enumerate(groups):
            gh = len(group) * self.VOICE_H

            # KEY / TIME display (left column)
            ky = y + gh//2
            key_txt  = f"KEY {score.key_sig}."
            time_txt = f"{score.time_num}/{score.time_den}"
            self.create_text(x_key + self.KEY_W - 4, ky - 8,
                             text=key_txt, fill=PAPER_INK,
                             font=self.F_KEY, anchor='e')
            self.create_text(x_key + self.KEY_W - 4, ky + 8,
                             text=time_txt, fill=PAPER_INK,
                             font=self.F_KEY, anchor='e')
            if gi == 0 and measures and measures[0].dynamic:
                self.create_text(x_key, y - 6, text=measures[0].dynamic,
                                 fill=PAPER_DYN, font=self.F_DYN, anchor='w')

            # Brace [ left of group
            bx = x_label + self.LABEL_W
            self.create_line(bx, y, bx, y+gh, fill=PAPER_BAR, width=3)
            self.create_line(bx, y, bx+self.BRACE_W, y, fill=PAPER_BAR, width=2)
            self.create_line(bx, y+gh, bx+self.BRACE_W, y+gh, fill=PAPER_BAR, width=2)

            # Top rule of group
            self.create_line(x_music, y, x_end, y, fill=PAPER_LINE, width=1)

            # Voice rows
            for vi, voice in enumerate(group):
                vy     = y + vi * self.VOICE_H
                vy_mid = vy + self.VOICE_H // 2

                # Voice label
                lbl = VOICE_NAMES.get(voice, f'V{voice}')
                self.create_text(x_label + self.LABEL_W - 4, vy_mid,
                                 text=lbl, fill=PAPER_VOICE,
                                 font=self.F_VOICE, anchor='e')
                # Row bottom line
                self.create_line(x_music, vy+self.VOICE_H, x_end, vy+self.VOICE_H,
                                 fill=PAPER_LINE, width=1)
                # Opening barline
                self.create_line(x_music, vy, x_music, vy+self.VOICE_H,
                                 fill=PAPER_BAR, width=1)
                # Measures
                mx = x_music
                for mi, meas in enumerate(measures):
                    self._draw_measure_row(mx, vy, meas, voice, score.key_sig)
                    mx += meas_w

            # Closing bold barline
            self.create_line(x_end, y, x_end, y+gh, fill=PAPER_BAR, width=2)

            y += gh

            # Lyrics row below upper group
            if gi == 0 and has_lyr and upper:
                mx = x_music
                for meas in measures:
                    self._draw_lyrics_row(mx, y+3, meas, upper, meas_w)
                    mx += meas_w
                y += self.LYRIC_H

            if gi < len(groups)-1: y += 6

        return y

    def _draw_measure_row(self, x, vy, meas, voice, key):
        beat_num = meas.time_num
        vy_mid   = vy + self.VOICE_H // 2
        bw       = self.BEAT_W
        grid     = meas.beat_grid(voice, key)

        for bi, sym in enumerate(grid):
            bx     = x + bi * bw
            bx_mid = bx + bw // 2 + (2 if bi > 0 else 0)

            # Beat separator colon (not before first beat)
            if bi > 0:
                self.create_text(bx, vy_mid, text=':',
                                 fill=PAPER_LINE, font=self.F_SEP, anchor='center')

            if sym == '—':
                self.create_text(bx_mid, vy_mid, text='—',
                                 fill=PAPER_LINE, font=self.F_SEP, anchor='center')
            elif sym:
                self.create_text(bx_mid, vy_mid, text=sym,
                                 fill=PAPER_INK, font=self.F_SYL, anchor='center')

        # Barline
        self.create_line(x+beat_num*bw+4, vy, x+beat_num*bw+4, vy+self.VOICE_H,
                         fill=PAPER_BAR, width=1)

    def _draw_lyrics_row(self, x, ly, meas, group, meas_w):
        for voice in group:
            notes = meas.voice_notes(voice) or meas.notes
            beat_unit = 4.0 / meas.time_den
            bw = self.BEAT_W
            pos = 0.0
            for n in notes:
                if n.lyric:
                    bi = min(meas.time_num-1, int(round(pos/beat_unit)))
                    bx = x + bi*bw + bw//2
                    self.create_text(bx, ly+self.LYRIC_H//2,
                                     text=n.lyric, fill=PAPER_LYRIC,
                                     font=self.F_LYRIC, anchor='center')
                pos += n.beats
            break


# ═══════════════════════════════════════════════════════
#  STAFF NOTATION CANVAS
#  Grand staff SATB: SA treble + TB bass (hymn-book style)
# ═══════════════════════════════════════════════════════
class StaffCanvas(tk.Canvas):
    """
    SATB grand staff notation panel.
    Treble staff (top): Soprano (stems up) + Alto (stems down)
    Bass staff (bottom): Tenor (stems up) + Bass (stems down)
    Style matches the hymn-book staff image reference.
    """
    LG      = 10     # line gap (pixels between staff lines)
    MARG_L  = 100    # left margin
    MARG_T  = 90     # top margin
    MARG_R  = 30
    MEAS_W  = 190    # measure width
    SYS_GAP = 80     # gap between systems
    NR      = 5      # notehead radius
    STEM_H  = 32     # stem length (pixels)
    STAFF_LINES = 5

    def __init__(self, master, score: Score, on_change=None, on_select=None, **kwargs):
        super().__init__(master, bg=DARK, bd=0, highlightthickness=0, **kwargs)
        self.score     = score
        self.on_change = on_change
        self.on_select = on_select
        self.tool      = 'select'
        self.cur_dur   = 1.0
        self.cur_voice = 1
        self.cur_acc   = ''
        self.sel_m     = -1
        self.sel_n     = -1
        self.bind('<Button-1>', self._click)
        self.bind('<Configure>', lambda e: self.after_idle(self.redraw))

    def set_score(self, s: Score):
        self.score = s; self.redraw()

    def redraw(self):
        self.delete('all')
        if not self.score: return
        cw = self.winfo_width() or 900
        self._draw_score(cw)

    # ── Layout helpers ───────────────────────────────
    def _mpr(self, cw):
        return max(1, (cw - self.MARG_L - self.MARG_R) // self.MEAS_W)

    def _sys_h(self):
        """Height from treble-top to bass-bottom."""
        # treble 5 lines + gap of 8 lg + bass 5 lines
        return (self.STAFF_LINES-1)*self.LG + 8*self.LG + (self.STAFF_LINES-1)*self.LG

    def _treble_top(self, sy): return sy
    def _bass_top(self, sy):   return sy + (self.STAFF_LINES-1)*self.LG + 8*self.LG

    def _draw_score(self, cw):
        s = self.score
        mpr  = self._mpr(cw)
        rows = math.ceil(max(1, len(s.measures)) / mpr)
        sy   = self.MARG_T

        # Title
        self.create_text(cw//2, 18, text=s.title,
                         fill=WHITE, font=('Georgia',14,'bold'), anchor='n')
        self.create_text(cw//2, 38, text=s.composer,
                         fill=MUTED, font=('Georgia',10), anchor='n')

        for row in range(rows):
            rm = s.measures[row*mpr:(row+1)*mpr]
            if not rm: break
            self._draw_system(sy, rm, s, row, cw)
            sy += self._sys_h() + self.SYS_GAP

        self.configure(scrollregion=(0, 0, cw, sy+40))

    def _draw_system(self, sy, measures, score, row_idx, cw):
        t_top = self._treble_top(sy)
        b_top = self._bass_top(sy)
        s_h   = (self.STAFF_LINES-1)*self.LG
        row_end = self.MARG_L + len(measures)*self.MEAS_W

        # ── System bracket ────────────────────────
        bx = self.MARG_L - 14
        self.create_line(bx, t_top, bx, b_top+s_h, fill=WHITE, width=4)
        # Hook top
        self.create_arc(bx-4, t_top-4, bx+6, t_top+10,
                        start=270, extent=90, outline=WHITE, width=2, style='arc')
        # Hook bottom
        self.create_arc(bx-4, b_top+s_h-10, bx+6, b_top+s_h+4,
                        start=180, extent=90, outline=WHITE, width=2, style='arc')

        # ── Draw the two staves ───────────────────
        for li in range(self.STAFF_LINES):
            # Treble
            self.create_line(self.MARG_L, t_top+li*self.LG,
                             row_end, t_top+li*self.LG,
                             fill=STAFF_LINE_COL, width=1)
            # Bass
            self.create_line(self.MARG_L, b_top+li*self.LG,
                             row_end, b_top+li*self.LG,
                             fill=STAFF_LINE_COL, width=1)

        # System opening barline (through both staves)
        self.create_line(self.MARG_L, t_top, self.MARG_L, b_top+s_h,
                         fill=WHITE, width=1)

        # ── Clef symbols ──────────────────────────
        # Treble clef
        self.create_text(self.MARG_L - 60, t_top + self.LG*1.5,
                         text='𝄞', fill=WHITE, font=('Arial',42), anchor='center')
        # Bass clef
        self.create_text(self.MARG_L - 60, b_top + self.LG*0.8,
                         text='𝄢', fill=WHITE, font=('Arial',28), anchor='center')

        # ── Key + Time sig (first row only) ──────
        kx = self.MARG_L + 4
        if row_idx == 0 and measures:
            kx = self._draw_key_sig(kx, t_top, b_top, score.key_sig)
            kx = self._draw_time_sig(kx, t_top, b_top, score.time_num, score.time_den)

        # ── Measures ──────────────────────────────
        for mi, meas in enumerate(measures):
            abs_idx = self._find_abs_idx(meas)
            mx = self.MARG_L + mi * self.MEAS_W
            self._draw_measure(mx, t_top, b_top, meas, abs_idx)

        # System closing barline
        self.create_line(row_end, t_top, row_end, b_top+s_h,
                         fill=WHITE, width=2)

    def _find_abs_idx(self, meas):
        for i, m in enumerate(self.score.measures):
            if m is meas: return i
        return -1

    def _draw_key_sig(self, x, t_top, b_top, key_name) -> int:
        fifths = KEY_SIGS.get(key_name, 0)
        if fifths == 0: return x
        is_sharp = fifths > 0
        sym      = '♯' if is_sharp else '♭'
        slots_t  = SHARP_TREBLE_SLOTS if is_sharp else FLAT_TREBLE_SLOTS
        slots_b  = SHARP_BASS_SLOTS   if is_sharp else FLAT_BASS_SLOTS
        for i in range(abs(fifths)):
            slot_t = slots_t[i]
            slot_b = slots_b[i]
            ty = t_top + slot_t * (self.LG/2)
            by = b_top + slot_b * (self.LG/2)
            self.create_text(x+i*9+4, ty, text=sym, fill=GOLD, font=('Arial',11))
            self.create_text(x+i*9+4, by, text=sym, fill=GOLD, font=('Arial',11))
        return x + abs(fifths)*9 + 12

    def _draw_time_sig(self, x, t_top, b_top, num, den) -> int:
        t_mid = t_top + (self.STAFF_LINES-1)*self.LG/2
        b_mid = b_top + (self.STAFF_LINES-1)*self.LG/2
        for mid in [t_mid, b_mid]:
            self.create_text(x+10, mid-self.LG*0.8, text=str(num),
                             fill=WHITE, font=('Arial',16,'bold'), anchor='center')
            self.create_text(x+10, mid+self.LG*0.8, text=str(den),
                             fill=WHITE, font=('Arial',16,'bold'), anchor='center')
        return x + 28

    def _note_y(self, top_y, pitch, octave, clef='treble') -> float:
        """Y pixel position for a note on a staff."""
        p = pitch.rstrip('#b')
        if p not in NOTE_STEPS: p = 'C'
        si = NOTE_STEPS.index(p)
        if clef == 'treble':
            ref_s, ref_o = NOTE_STEPS.index('F'), 5  # top line = F5
        else:
            ref_s, ref_o = NOTE_STEPS.index('A'), 3  # top line = A3
        ref_abs  = ref_o * 7 + ref_s
        note_abs = octave * 7 + si
        slots    = ref_abs - note_abs          # positive = lower
        return top_y + slots * (self.LG / 2)

    def _draw_measure(self, mx, t_top, b_top, meas, abs_m_idx):
        s_h  = (self.STAFF_LINES-1)*self.LG
        ex   = mx + self.MEAS_W
        # Barlines
        self.create_line(ex, t_top, ex, t_top+s_h, fill=STAFF_BAR_COL, width=1)
        self.create_line(ex, b_top, ex, b_top+s_h, fill=STAFF_BAR_COL, width=1)
        # Connecting barline
        self.create_line(ex, t_top, ex, b_top+s_h, fill=STAFF_BAR_COL, width=1)
        # Measure number
        self.create_text(mx+3, t_top-10, text=str(meas.number),
                         fill=MUTED, font=('Arial',7), anchor='w')
        if not meas.notes:
            self._draw_whole_rest(mx+self.MEAS_W//2, t_top+self.LG, t_top)
            self._draw_whole_rest(mx+self.MEAS_W//2, b_top+self.LG, b_top)
            return

        # Draw treble voices (S=1, A=2)
        for voice in [1, 2]:
            vnotes = meas.voice_notes(voice)
            if vnotes:
                self._draw_voice(mx, t_top, vnotes, voice, abs_m_idx,
                                 meas, clef='treble')
        # Draw bass voices (T=3, B=4)
        for voice in [3, 4]:
            vnotes = meas.voice_notes(voice)
            if vnotes:
                self._draw_voice(mx, b_top, vnotes, voice, abs_m_idx,
                                 meas, clef='bass')
        # Single-voice fallback
        vs = meas.all_voices()
        if not vs:
            self._draw_voice(mx, t_top, meas.notes, 1, abs_m_idx, meas, 'treble')

        # Repeat barlines
        if meas.repeat_start:
            self._draw_repeat_bar(mx, t_top, b_top, s_h, 'start')
        if meas.repeat_end:
            self._draw_repeat_bar(ex, t_top, b_top, s_h, 'end')

    def _draw_voice(self, mx, top_y, notes, voice, abs_m_idx, meas, clef):
        s_h     = (self.STAFF_LINES-1)*self.LG
        n_notes = len(notes)
        spacing = (self.MEAS_W - 20) / max(n_notes, 1)
        stem_up = voice in (1, 3)

        for ni, n in enumerate(notes):
            nx  = mx + 14 + ni * spacing
            n.x = nx
            sel = (abs_m_idx == self.sel_m and ni == self.sel_n
                   and n.voice == voice)
            col = NOTE_SEL if sel else NOTE_COL

            if n.rest:
                n.y = top_y + self.LG
                self._draw_rest_sym(nx, top_y+self.LG, n.duration)
                continue

            ny  = self._note_y(top_y, n.pitch, n.octave, clef)
            n.y = ny

            # Ledger lines
            self._ledger_lines(nx, ny, top_y, s_h)

            # Notehead — open for half/whole, filled for quarter/shorter
            open_head = (n.duration >= 2.0)
            rx, ry = nx, ny
            rw, rh = self.NR, int(self.NR*0.65)
            if open_head:
                self.create_oval(rx-rw, ry-rh, rx+rw, ry+rh,
                                 outline=col, fill=DARK, width=2)
            else:
                self.create_oval(rx-rw, ry-rh, rx+rw, ry+rh,
                                 outline=col, fill=col)
            # Whole note — no stem
            if n.duration < 4.0:
                if stem_up:
                    sx = nx + rw - 1
                    self.create_line(sx, ny, sx, ny - self.STEM_H,
                                     fill=col, width=1.5)
                    if n.duration <= 0.5:
                        flags = max(1, int(round(math.log2(1/n.duration))) - 1)
                        for fi in range(flags):
                            fy = ny - self.STEM_H + fi*6
                            self.create_line(sx, fy, sx+10, fy+8, fill=col, width=1.5)
                else:
                    sx = nx - rw + 1
                    self.create_line(sx, ny, sx, ny + self.STEM_H,
                                     fill=col, width=1.5)
                    if n.duration <= 0.5:
                        flags = max(1, int(round(math.log2(1/n.duration))) - 1)
                        for fi in range(flags):
                            fy = ny + self.STEM_H - fi*6
                            self.create_line(sx, fy, sx+10, fy-8, fill=col, width=1.5)
            # Dot
            if n.dotted:
                self.create_oval(nx+rw+3, ny-2, nx+rw+7, ny+2,
                                 fill=col, outline=col)
            # Accidental
            if '#' in n.pitch:
                self.create_text(nx-rw-7, ny, text='♯',
                                 fill=GOLD, font=('Arial',9))
            elif 'b' in n.pitch:
                self.create_text(nx-rw-7, ny, text='♭',
                                 fill=GOLD, font=('Arial',9))
            # Lyric below staff
            if n.lyric:
                ly = top_y + s_h + 14
                self.create_text(nx, ly, text=n.lyric,
                                 fill=GREEN, font=('Georgia',8), anchor='n')

    def _ledger_lines(self, nx, ny, top_y, s_h):
        lg = self.LG
        # Above staff
        if ny < top_y - 1:
            ld = top_y - lg
            while ld >= ny - 2:
                self.create_line(nx-8, ld, nx+8, ld, fill=LEDGER_COL, width=1)
                ld -= lg
        # Below staff
        if ny > top_y + s_h + 1:
            ld = top_y + s_h + lg
            while ld <= ny + 2:
                self.create_line(nx-8, ld, nx+8, ld, fill=LEDGER_COL, width=1)
                ld += lg

    def _draw_rest_sym(self, rx, ry, duration):
        ch = {4.0:'𝄻',2.0:'𝄼',1.0:'𝄽',0.5:'𝄾',0.25:'𝄿'}.get(duration,'𝄽')
        self.create_text(rx, ry, text=ch, fill=MUTED,
                         font=('Arial',15), anchor='center')

    def _draw_whole_rest(self, rx, ry, top_y):
        """Whole measure rest rectangle."""
        self.create_rectangle(rx-8, ry-3, rx+8, ry+1,
                              fill=MUTED, outline='')

    def _draw_repeat_bar(self, x, t_top, b_top, s_h, which):
        if which == 'start':
            self.create_line(x, t_top, x, b_top+s_h, fill=WHITE, width=1)
            self.create_line(x+3, t_top, x+3, b_top+s_h, fill=WHITE, width=3)
            self.create_oval(x+7, t_top+s_h//3-3, x+11, t_top+s_h//3+3, fill=WHITE)
            self.create_oval(x+7, t_top+2*s_h//3-3, x+11, t_top+2*s_h//3+3, fill=WHITE)
        else:
            self.create_oval(x-11, t_top+s_h//3-3, x-7, t_top+s_h//3+3, fill=WHITE)
            self.create_oval(x-11, t_top+2*s_h//3-3, x-7, t_top+2*s_h//3+3, fill=WHITE)
            self.create_line(x-3, t_top, x-3, b_top+s_h, fill=WHITE, width=3)
            self.create_line(x, t_top, x, b_top+s_h, fill=WHITE, width=1)

    # ── Interaction ──────────────────────────────────
    def _find_measure(self, x, y):
        cw  = self.winfo_width() or 900
        mpr = self._mpr(cw)
        for i, meas in enumerate(self.score.measures):
            row = i // mpr; col = i % mpr
            mx  = self.MARG_L + col * self.MEAS_W
            sy  = self.MARG_T + row * (self._sys_h() + self.SYS_GAP)
            t_top = self._treble_top(sy); b_top = self._bass_top(sy)
            s_h   = (self.STAFF_LINES-1)*self.LG
            in_t  = mx <= x <= mx+self.MEAS_W and t_top-20 <= y <= t_top+s_h+20
            in_b  = mx <= x <= mx+self.MEAS_W and b_top-20 <= y <= b_top+s_h+20
            if in_t or in_b:
                clef = 'treble' if in_t else 'bass'
                sy_   = t_top if in_t else b_top
                return i, meas, mx, sy_
        return -1, None, 0, 0

    def _click(self, event):
        x, y = event.x, event.y
        if   self.tool == 'select': self._do_select(x, y)
        elif self.tool == 'note':   self._do_place(x, y, rest=False)
        elif self.tool == 'rest':   self._do_place(x, y, rest=True)
        elif self.tool == 'erase':  self._do_erase(x, y)
        elif self.tool == 'lyric':  self._do_lyric(x, y)

    def _do_select(self, x, y):
        self.sel_m = -1; self.sel_n = -1
        mi, meas, mx, _ = self._find_measure(x, y)
        if meas:
            for ni, n in enumerate(meas.notes):
                if abs(n.x - x) < 14:
                    self.sel_m = mi; self.sel_n = ni
                    if self.on_select: self.on_select(mi, ni)
                    break
        self.redraw()

    def _do_place(self, x, y, rest=False):
        mi, meas, mx, sy_ = self._find_measure(x, y)
        if meas is None:
            self.score.add_measure()
            if self.on_change: self.on_change()
            self.redraw(); return
        if rest:
            n = MusNote(rest=True, duration=self.cur_dur, voice=self.cur_voice)
        else:
            cw = self.winfo_width() or 900
            row = mi // self._mpr(cw)
            rsy = self.MARG_T + row*(self._sys_h()+self.SYS_GAP)
            clef = 'bass' if self.cur_voice >= 3 else 'treble'
            top_ref = self._bass_top(rsy) if clef=='bass' else self._treble_top(rsy)
            p, o = self._y_to_note(y, top_ref, clef)
            p = p + self.cur_acc
            n = MusNote(pitch=p, octave=o, duration=self.cur_dur, voice=self.cur_voice)
        if meas.beats_used + n.beats <= meas.beats_available + 0.01:
            meas.notes.append(n)
            if self.on_change: self.on_change()
        else:
            messagebox.showinfo("Measure Full",
                "Measure is full. Add a new measure first.")
        self.redraw()

    def _do_erase(self, x, y):
        mi, meas, mx, _ = self._find_measure(x, y)
        if not meas: return
        for ni, n in enumerate(meas.notes):
            if abs(n.x - x) < 14:
                meas.notes.pop(ni)
                if self.on_change: self.on_change()
                self.redraw(); return

    def _do_lyric(self, x, y):
        mi, meas, mx, _ = self._find_measure(x, y)
        if not meas: return
        for n in meas.notes:
            if abs(n.x - x) < 14:
                lyr = simpledialog.askstring(
                    "Lyric", f"Syllable for {n.pitch}{n.octave}:",
                    initialvalue=n.lyric, parent=self)
                if lyr is not None:
                    n.lyric = lyr
                    if self.on_change: self.on_change()
                    self.redraw()
                return

    def _y_to_note(self, y, top_y, clef):
        if clef == 'treble': ref_s, ref_o = NOTE_STEPS.index('F'), 5
        else:                 ref_s, ref_o = NOTE_STEPS.index('A'), 3
        ref_abs  = ref_o*7 + ref_s
        slot     = (y - top_y) / (self.LG/2)
        note_abs = ref_abs - round(slot)
        oct_     = note_abs // 7
        si       = note_abs % 7
        if si < 0: si += 7; oct_ -= 1
        return NOTE_STEPS[si % 7], max(0, min(8, int(oct_)))

    def get_selected_note(self):
        if 0 <= self.sel_m < len(self.score.measures):
            m = self.score.measures[self.sel_m]
            if 0 <= self.sel_n < len(m.notes):
                return m.notes[self.sel_n]
        return None


# ═══════════════════════════════════════════════════════
#  PROPERTIES PANEL
# ═══════════════════════════════════════════════════════
class PropertiesPanel(tk.Frame):
    def __init__(self, master, score: Score, on_change=None, **kwargs):
        super().__init__(master, bg=PANEL, width=230, **kwargs)
        self.score = score; self.on_change = on_change
        self.pack_propagate(False); self.vars = {}
        self._build()

    def _sec(self, title):
        f = tk.Frame(self, bg=CARD, height=26); f.pack(fill='x', pady=(8,0))
        f.pack_propagate(False)
        tk.Label(f, text=title, bg=CARD, fg=GOLD,
                 font=('Arial',8,'bold')).pack(side='left', padx=8, pady=4)

    def _field(self, label, attr, wtype='entry', opts=None):
        row = tk.Frame(self, bg=PANEL); row.pack(fill='x', padx=8, pady=2)
        tk.Label(row, text=label+':', bg=PANEL, fg=MUTED,
                 font=('Arial',8), width=9, anchor='w').pack(side='left')
        if wtype == 'entry':
            var = tk.StringVar(value=str(getattr(self.score, attr, '')))
            tk.Entry(row, textvariable=var, bg=DARK, fg=WHITE,
                     insertbackground=WHITE, relief='flat', font=('Arial',9)
                     ).pack(side='left', fill='x', expand=True)
            var.trace_add('write', lambda *a, v=var, k=attr: self._upd(k, v.get()))
            self.vars[attr] = var
        elif wtype == 'combo':
            cur = (f"{self.score.time_num}/{self.score.time_den}"
                   if attr=='time_sig' else str(getattr(self.score, attr, opts[0])))
            var = tk.StringVar(value=cur)
            cb = ttk.Combobox(row, textvariable=var, values=opts,
                              font=('Arial',9), width=9, state='readonly')
            cb.pack(side='left')
            cb.bind('<<ComboboxSelected>>', lambda e, v=var, k=attr: self._upd(k, v.get()))
            self.vars[attr] = var
        elif wtype == 'spin':
            lo, hi = opts
            var = tk.IntVar(value=int(getattr(self.score, attr, lo)))
            tk.Spinbox(row, from_=lo, to=hi, textvariable=var,
                       bg=DARK, fg=WHITE, insertbackground=WHITE,
                       relief='flat', font=('Arial',9), width=5).pack(side='left')
            var.trace_add('write', lambda *a, v=var, k=attr: self._upd_int(k, v))
            self.vars[attr] = var

    def _upd(self, attr, val):
        if attr == 'time_sig':
            try:
                a, b = val.split('/')
                self.score.time_num=int(a); self.score.time_den=int(b)
                for m in self.score.measures: m.time_num=int(a); m.time_den=int(b)
            except: pass
        elif attr == 'key_sig':
            self.score.key_sig = val
            for m in self.score.measures: m.key_sig = val
        elif hasattr(self.score, attr): setattr(self.score, attr, val)
        if self.on_change: self.on_change()

    def _upd_int(self, attr, var):
        try:
            setattr(self.score, attr, var.get())
            if self.on_change: self.on_change()
        except: pass

    def _build(self):
        self._sec("SCORE PROPERTIES")
        self._field("Title",   'title')
        self._field("Composer",'composer')
        self._field("Lyricist",'lyricist')
        self._field("Key",     'key_sig',   'combo', KEYS)
        self._field("Time",    'time_sig',  'combo', TIME_SIGS)
        self._field("Tempo ♩", 'tempo_bpm', 'spin',  (20, 400))
        self._field("Clef",    'clef',      'combo', ['treble','bass','alto'])
        self._sec("NOTE INPUT")
        self._note_tools()
        self._sec("DYNAMICS")
        self._dyn_panel()
        self._sec("PLAYBACK")
        self._play_panel()

    def _note_tools(self):
        df = tk.Frame(self, bg=PANEL); df.pack(fill='x', padx=8, pady=3)
        tk.Label(df, text="Duration:", bg=PANEL, fg=MUTED, font=('Arial',8)).pack(anchor='w')
        bf = tk.Frame(df, bg=PANEL); bf.pack(fill='x')
        self._dur_btns = {}
        for sym, val, tip in [('W',4.0,'Whole'),('H',2.0,'Half'),('Q',1.0,'Quarter'),
                               ('E',0.5,'Eighth'),('S',0.25,'16th')]:
            b = tk.Button(bf, text=sym, width=3, bg=DARK, fg=TEXT, relief='flat',
                          font=('Arial',9,'bold'),
                          command=lambda v=val: self._set_dur(v))
            b.pack(side='left', padx=1)
            _tooltip(b, tip)
            self._dur_btns[val] = b
        self._set_dur(1.0)

        af = tk.Frame(self, bg=PANEL); af.pack(fill='x', padx=8, pady=2)
        tk.Label(af, text="Accidental:", bg=PANEL, fg=MUTED, font=('Arial',8)).pack(side='left')
        self._acc_var = tk.StringVar(value='')
        for sym, val in [('♮',''),('♯','#'),('♭','b')]:
            tk.Radiobutton(af, text=sym, variable=self._acc_var, value=val,
                           bg=PANEL, fg=GOLD, selectcolor=DARK,
                           font=('Arial',11)).pack(side='left')

        of = tk.Frame(self, bg=PANEL); of.pack(fill='x', padx=8, pady=2)
        tk.Label(of, text="Octave:", bg=PANEL, fg=MUTED, font=('Arial',8)).pack(side='left')
        self._oct_var = tk.IntVar(value=4)
        tk.Spinbox(of, from_=1, to=8, textvariable=self._oct_var,
                   bg=DARK, fg=WHITE, relief='flat', font=('Arial',9), width=4
                   ).pack(side='left', padx=4)

        vf = tk.Frame(self, bg=PANEL); vf.pack(fill='x', padx=8, pady=3)
        tk.Label(vf, text="Voice:", bg=PANEL, fg=MUTED, font=('Arial',8)).pack(anchor='w')
        vbf = tk.Frame(vf, bg=PANEL); vbf.pack(fill='x')
        self._voice_var = tk.IntVar(value=1)
        for lbl, val, col in [('S',1,ACCENT),('A',2,BLUE),('T',3,GREEN),('B',4,GOLD)]:
            tk.Radiobutton(vbf, text=lbl, variable=self._voice_var, value=val,
                           bg=PANEL, fg=col, selectcolor=DARK,
                           font=('Arial',9,'bold')).pack(side='left', padx=3)

        self._dot_var = tk.BooleanVar()
        tk.Checkbutton(self, text="Dotted note", variable=self._dot_var,
                       bg=PANEL, fg=TEXT, selectcolor=DARK,
                       font=('Arial',8)).pack(anchor='w', padx=8)

    def _set_dur(self, val):
        for v, b in self._dur_btns.items():
            b.config(bg=ACCENT if v==val else DARK,
                     fg=WHITE if v==val else TEXT)
        self._cur_dur = val

    def _dyn_panel(self):
        dyns = ['pp','p','mp','mf','f','ff','sf','sfz']
        f = tk.Frame(self, bg=PANEL); f.pack(fill='x', padx=8, pady=3)
        self._dyn_var = tk.StringVar(value='mf')
        for i, d in enumerate(dyns):
            tk.Radiobutton(f, text=d, variable=self._dyn_var, value=d,
                           bg=PANEL, fg=GOLD, selectcolor=DARK,
                           font=('Times',9,'italic')).grid(row=i//4, column=i%4, padx=2, pady=1)

    def _play_panel(self):
        f = tk.Frame(self, bg=PANEL); f.pack(fill='x', padx=8, pady=4)
        tk.Button(f, text="▶ Play All", bg=GREEN, fg=DARK, relief='flat',
                  font=('Arial',10,'bold'), command=self._play).pack(side='left', padx=2)
        tk.Button(f, text="⏹ Stop", bg=DARK, fg=TEXT, relief='flat',
                  font=('Arial',10), command=self._stop).pack(side='left', padx=2)

    def _play(self):
        if not PYGAME_OK:
            messagebox.showinfo("Playback","Install pygame:\npip install pygame"); return
        try:
            mid = ConversionEngine.export_midi_bytes_harmony(self.score)
            pygame.mixer.music.load(io.BytesIO(mid))
            pygame.mixer.music.play()
        except Exception as e:
            messagebox.showerror("Playback Error", str(e))

    def _stop(self):
        if PYGAME_OK:
            try: pygame.mixer.music.stop()
            except: pass

    def refresh(self, score: Score):
        self.score = score
        mapping = {'title':'title','composer':'composer','key_sig':'key_sig',
                   'time_sig':f"{score.time_num}/{score.time_den}",
                   'tempo_bpm':'tempo_bpm'}
        for k, v in self.vars.items():
            if k == 'time_sig':
                v.set(f"{score.time_num}/{score.time_den}")
            elif hasattr(score, k):
                v.set(str(getattr(score, k)))

    def get_params(self):
        return {
            'duration':  getattr(self, '_cur_dur', 1.0),
            'accidental': self._acc_var.get(),
            'octave':    self._oct_var.get(),
            'voice':     self._voice_var.get(),
            'dotted':    self._dot_var.get(),
        }


# ═══════════════════════════════════════════════════════
#  NOTE EDITOR PANEL
# ═══════════════════════════════════════════════════════
class NoteEditorPanel(tk.Frame):
    def __init__(self, master, score: Score, on_change=None, **kwargs):
        super().__init__(master, bg=PANEL, **kwargs)
        self.score = score; self.on_change = on_change
        self.sel = None; self.sel_m = -1; self.sel_n = -1
        self._build()

    def _build(self):
        tk.Label(self, text="Note Editor", bg=PANEL, fg=GOLD,
                 font=('Arial',12,'bold')).pack(pady=10)
        self.info = tk.Label(self, text="Select a note on the staff",
                              bg=CARD, fg=MUTED, font=('Arial',10),
                              relief='raised', bd=1, padx=10, pady=8)
        self.info.pack(fill='x', padx=10, pady=5)

        def row(lbl):
            f = tk.Frame(self, bg=PANEL); f.pack(fill='x', padx=10, pady=2)
            tk.Label(f, text=lbl, bg=PANEL, fg=MUTED,
                     font=('Arial',8), width=10, anchor='w').pack(side='left')
            return f

        r = row("Pitch:")
        self._pitch = tk.StringVar(value='C')
        for p in ['C','D','E','F','G','A','B']:
            tk.Radiobutton(r, text=p, variable=self._pitch, value=p,
                           bg=PANEL, fg=TEXT, selectcolor=ACCENT,
                           font=('Arial',9), command=self._apply).pack(side='left', padx=1)

        r = row("Octave:")
        self._oct = tk.IntVar(value=4)
        tk.Scale(r, from_=1, to=8, orient='horizontal', variable=self._oct,
                 bg=CARD, fg=TEXT, troughcolor=DARK,
                 command=lambda v: self._apply()).pack(fill='x', expand=True)

        r = row("Duration:")
        r.pack(fill='x', padx=10, pady=2)
        self._dur = tk.StringVar(value='1.0')
        for sym, val in [('𝅝 Whole','4.0'),('𝅗𝅥 Half','2.0'),
                          ('♩ Quarter','1.0'),('♪ Eighth','0.5'),('𝅘𝅥𝅯 16th','0.25')]:
            tk.Radiobutton(self, text=sym, variable=self._dur, value=val,
                           bg=PANEL, fg=TEXT, selectcolor=ACCENT,
                           font=('Arial',8), command=self._apply).pack(anchor='w', padx=10, pady=1)

        r = row("Accidental:")
        self._acc = tk.StringVar(value='')
        for sym, val in [('♮',''),('♯','#'),('♭','b')]:
            tk.Radiobutton(r, text=sym, variable=self._acc, value=val,
                           bg=PANEL, fg=GOLD, selectcolor=DARK,
                           font=('Arial',11), command=self._apply).pack(side='left')

        r = row("Voice:")
        self._voice = tk.IntVar(value=1)
        for lbl, v, c in [('S',1,ACCENT),('A',2,BLUE),('T',3,GREEN),('B',4,GOLD)]:
            tk.Radiobutton(r, text=lbl, variable=self._voice, value=v,
                           bg=PANEL, fg=c, selectcolor=DARK,
                           font=('Arial',9,'bold'), command=self._apply).pack(side='left', padx=2)

        self._dot  = tk.BooleanVar()
        self._rest = tk.BooleanVar()
        tk.Checkbutton(self, text="Dotted", variable=self._dot,
                       bg=PANEL, fg=TEXT, selectcolor=DARK, command=self._apply).pack(anchor='w', padx=10)
        tk.Checkbutton(self, text="Rest (no pitch)", variable=self._rest,
                       bg=PANEL, fg=TEXT, selectcolor=DARK, command=self._apply).pack(anchor='w', padx=10)

        r = row("Lyric:")
        self._lyric = tk.StringVar()
        e = tk.Entry(r, textvariable=self._lyric, bg=DARK, fg=WHITE,
                     insertbackground=WHITE, relief='flat', font=('Arial',9))
        e.pack(side='left', fill='x', expand=True)
        e.bind('<Return>', lambda ev: self._apply())

        tk.Button(self, text="🗑  Delete Note", bg='#d9534f', fg=WHITE,
                  font=('Arial',9,'bold'), relief='flat',
                  command=self._delete).pack(fill='x', padx=10, pady=10)
        self._status = tk.Label(self, text="", bg=PANEL, fg=GREEN,
                                font=('Arial',8), wraplength=220)
        self._status.pack(padx=10)

    def load_note(self, note, m_idx, n_idx):
        self.sel = note; self.sel_m = m_idx; self.sel_n = n_idx
        if note:
            self.info.config(
                text=f"{'Rest' if note.rest else note.pitch+str(note.octave)}"
                     f"  •  Measure {m_idx+1}, Note {n_idx+1}", fg=TEXT)
            self._pitch.set(note.pitch.rstrip('#b') or 'C')
            self._oct.set(note.octave)
            self._dur.set(str(note.duration))
            self._acc.set(note.accidental or '')
            self._voice.set(note.voice)
            self._dot.set(note.dotted)
            self._rest.set(note.rest)
            self._lyric.set(note.lyric or '')
        else:
            self.info.config(text="No note selected", fg=MUTED)

    def _apply(self):
        if not self.sel: return
        n = self.sel
        n.pitch = self._pitch.get() + self._acc.get()
        n.octave = self._oct.get()
        try: n.duration = float(self._dur.get())
        except: pass
        n.accidental = self._acc.get()
        n.voice   = self._voice.get()
        n.dotted  = self._dot.get()
        n.rest    = self._rest.get()
        n.lyric   = self._lyric.get()
        self._status.config(text="✓ Applied")
        if self.on_change: self.on_change()

    def _delete(self):
        if not self.sel: return
        if 0 <= self.sel_m < len(self.score.measures):
            m = self.score.measures[self.sel_m]
            if 0 <= self.sel_n < len(m.notes):
                m.notes.pop(self.sel_n)
                self.sel = None
                self.info.config(text="Note deleted", fg=MUTED)
                if self.on_change: self.on_change()


# ═══════════════════════════════════════════════════════
#  SOLFA TEXT PANEL
# ═══════════════════════════════════════════════════════
class SolfaTextPanel(tk.Frame):
    def __init__(self, master, score: Score, on_change=None, **kwargs):
        super().__init__(master, bg=PANEL, **kwargs)
        self.score = score; self.on_change = on_change
        self._build()

    def _build(self):
        bar = tk.Frame(self, bg=CARD); bar.pack(fill='x')
        tk.Label(bar, text="TONIC SOLFA TEXT VIEW",
                 bg=CARD, fg=GOLD, font=('Arial',9,'bold')).pack(side='left', padx=10, pady=5)
        tk.Button(bar, text="⟳ Refresh from Score", bg=ACCENT, fg=WHITE,
                  relief='flat', font=('Arial',8),
                  command=self.refresh_from_score).pack(side='right', padx=4, pady=4)
        self.txt = tk.Text(
            self, bg='#0d1b2a', fg=TEXT, insertbackground=WHITE,
            font=('Courier New',11), relief='flat', padx=12, pady=10,
            undo=True, wrap='none')
        sb_v = ttk.Scrollbar(self, orient='vertical', command=self.txt.yview)
        sb_h = ttk.Scrollbar(self, orient='horizontal', command=self.txt.xview)
        self.txt.config(yscrollcommand=sb_v.set, xscrollcommand=sb_h.set)
        sb_v.pack(side='right', fill='y')
        sb_h.pack(side='bottom', fill='x')
        self.txt.pack(fill='both', expand=True)
        leg = tk.Frame(self, bg=PANEL); leg.pack(fill='x', pady=2)
        for lbl, col in [("d=Do","#e94560"),("r=Re","#f5a623"),("m=Mi","#00d4aa"),
                          ("f=Fa","#8892a4"),("s=Sol","#4fc3f7"),("l=La","#ce93d8"),
                          ("t=Ti","#ffb74d")]:
            tk.Label(leg, text=lbl, bg=col, fg=DARK,
                     font=('Arial',8,'bold'), padx=4).pack(side='left', padx=1, pady=2)
        tk.Label(leg, text="  '=upper oct   ₁=lower oct   —=held   :=beat",
                 bg=PANEL, fg=MUTED, font=('Arial',8)).pack(side='left', padx=8)

    def refresh_from_score(self):
        self.txt.delete('1.0','end')
        self.txt.insert('1.0', ConversionEngine.export_solfa_text(self.score))

    def set_score(self, score: Score):
        self.score = score; self.refresh_from_score()


# ═══════════════════════════════════════════════════════
#  SUMMARY PANEL
# ═══════════════════════════════════════════════════════
class SummaryPanel(tk.Frame):
    def __init__(self, master, score: Score, **kwargs):
        super().__init__(master, bg=DARK, **kwargs)
        self.score = score; self._build()

    def _build(self):
        self.txt = tk.Text(self, bg='#0d1b2a', fg=TEXT,
                           font=('Courier New',10), relief='flat',
                           padx=15, pady=15, wrap='word', state='disabled')
        sb = ttk.Scrollbar(self, command=self.txt.yview)
        self.txt.config(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        self.txt.pack(fill='both', expand=True)

    def refresh(self, score: Score):
        self.score = score
        self.txt.config(state='normal')
        self.txt.delete('1.0','end')
        s = score
        vs = s.all_voices()
        tn = sum(len(m.notes) for m in s.measures)
        hdr = (f"\n  ╔══════════════════════════════════════════╗\n"
               f"  ║  {s.title:<40} ║\n"
               f"  ║  Composer : {s.composer:<28} ║\n"
               f"  ║  Key: {s.key_sig:<6}  {s.time_num}/{s.time_den}  ♩={s.tempo_bpm:<4} BPM   ║\n"
               f"  ╚══════════════════════════════════════════╝\n\n"
               f"  Measures: {len(s.measures)}   Notes: {tn}   "
               f"Voices: {', '.join(VOICE_NAMES.get(v,str(v)) for v in vs)}\n\n")
        self.txt.insert('end', hdr)
        self.txt.insert('end', '─'*50+'\n  TONIC SOLFA:\n'+'─'*50+'\n')
        self.txt.insert('end', ConversionEngine.export_solfa_text(s)+'\n\n')
        self.txt.insert('end', '─'*50+'\n  ABC:\n'+'─'*50+'\n')
        self.txt.insert('end', ConversionEngine.export_abc(s)+'\n')
        self.txt.config(state='disabled')


# ═══════════════════════════════════════════════════════
#  REFERENCE CANVAS
# ═══════════════════════════════════════════════════════
class ReferencePanel(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg=DARK, bd=0, highlightthickness=0, **kwargs)
        self.bind('<Configure>', lambda e: self.after_idle(self._draw))

    def _draw(self):
        self.delete('all')
        cw = self.winfo_width() or 800
        y = 20
        self.create_text(cw//2, y,
                         text="TONIC SOLFA REFERENCE CHART  —  Movable Do (SATB)",
                         fill=GOLD, font=('Georgia',13,'bold'))
        y += 30
        syls = [('Do','d','C','#e94560'),('Re','r','D','#f5a623'),
                ('Mi','m','E','#00d4aa'),('Fa','f','F','#4fc3f7'),
                ('Sol','s','G','#ce93d8'),('La','l','A','#ffb74d'),
                ('Ti','t','B','#e94560')]
        cw2 = (cw-40)//8; x0 = 20
        for i,(name,sym,nc,col) in enumerate(syls):
            x = x0+i*cw2
            self.create_rectangle(x+2, y+2, x+cw2-2, y+72, fill=col, outline=WHITE)
            self.create_text(x+cw2//2, y+16,  text=name, fill=WHITE, font=('Georgia',13,'bold'))
            self.create_text(x+cw2//2, y+38,  text=sym,  fill=DARK,  font=('Courier',22,'bold'))
            self.create_text(x+cw2//2, y+60,  text=f"≈{nc} in C", fill=WHITE, font=('Arial',8))
        y += 86
        self.create_text(20, y, text="Octave notation:",
                         fill=GOLD, font=('Arial',9,'bold'), anchor='w')
        y += 18
        self.create_text(20, y, anchor='w', fill=TEXT, font=('Courier',10),
                         text="  d₁ = one oct below   d = middle   d' = one oct above   d'' = two oct above")
        y += 18
        self.create_text(20, y, anchor='w', fill=MUTED, font=('Courier',9),
                         text="  Soprano/Alto: reference = octave 4  │  Tenor/Bass: reference = octave 3")
        y += 28
        self.create_text(20, y, text="Duration notation:",
                         fill=GOLD, font=('Arial',9,'bold'), anchor='w')
        y += 18
        durs = [("d","Quarter ♩"),("d — ","Half 𝅗𝅥"),("d — — —","Whole 𝅝"),
                (".d","Eighth ♪"),("·d","Dotted"),("—","Held/Rest")]
        dx = 20
        for sym, lbl in durs:
            self.create_rectangle(dx, y, dx+90, y+42, fill=CARD, outline='')
            self.create_text(dx+45, y+14, text=sym, fill=GOLD, font=('Courier',12,'bold'))
            self.create_text(dx+45, y+30, text=lbl, fill=MUTED, font=('Arial',7))
            dx += 94
        y += 56
        self.create_text(20, y, text="Keys (circle of fifths):",
                         fill=GOLD, font=('Arial',9,'bold'), anchor='w')
        y += 18
        kx = 20
        for k in KEYS:
            self.create_rectangle(kx, y, kx+48, y+30, fill=DARK, outline=MUTED)
            self.create_text(kx+24, y+15, text=k, fill=TEXT, font=('Arial',9))
            kx += 50


# ═══════════════════════════════════════════════════════
#  PRINT CHOICE DIALOG
# ═══════════════════════════════════════════════════════
class PrintChoiceDialog(tk.Toplevel):
    """Ask user what to print: Tonic Solfa or Staff Notation."""
    def __init__(self, master, score: Score):
        super().__init__(master, bg=PANEL)
        self.title("Print / Export PDF")
        self.geometry("380x220")
        self.transient(master); self.grab_set()
        self.result = None; self.score = score

        tk.Label(self, text="What would you like to print?",
                 bg=PANEL, fg=GOLD, font=('Arial',12,'bold')).pack(pady=16)

        bf = tk.Frame(self, bg=PANEL); bf.pack(pady=10)
        tk.Button(bf, text="📋  Traditional Tonic Solfa",
                  bg=ACCENT, fg=WHITE, relief='flat',
                  font=('Arial',10,'bold'), padx=16, pady=10,
                  command=self._solfa).pack(side='left', padx=8)
        tk.Button(bf, text="🎼  Staff Notation",
                  bg=BLUE, fg=DARK, relief='flat',
                  font=('Arial',10,'bold'), padx=16, pady=10,
                  command=self._staff).pack(side='left', padx=8)

        tk.Button(self, text="Cancel", bg=DARK, fg=TEXT, relief='flat',
                  font=('Arial',9), command=self.destroy).pack(pady=8)

    def _solfa(self): self.result = 'solfa'; self._export()
    def _staff(self): self.result = 'staff'; self._export()

    def _export(self):
        path = filedialog.asksaveasfilename(
            title="Save PDF", defaultextension=".pdf",
            filetypes=[("PDF","*.pdf"),("All","*.*")],
            parent=self)
        if not path:
            return
        try:
            if self.result == 'solfa':
                ConversionEngine.export_pdf_solfa(self.score, path)
            else:
                ConversionEngine.export_pdf_staff(self.score, path)
            messagebox.showinfo("Print", f"Saved:\n{path}", parent=self)
        except Exception as e:
            messagebox.showerror("Print Error", str(e), parent=self)
        self.destroy()


# ═══════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════
class TonicSolfaStudio(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME}  v{APP_VERSION}")
        self.geometry("1460x880"); self.minsize(1020,700)
        self.configure(bg=DARK)
        self.score    = Score(title="Untitled Score")
        self.score.ensure_measures(8)
        self.filepath = None; self.modified = False
        self._hist = deque(maxlen=60); self._redo = deque(maxlen=60)
        self._snap()
        self._setup_style()
        self._build_menu()
        self._build_toolbar()
        self._build_main()
        self._build_statusbar()
        self.protocol("WM_DELETE_WINDOW", self._quit)
        self.after(130, self._initial_render)

    def _setup_style(self):
        s = ttk.Style(self); s.theme_use('clam')
        for n in ['TCombobox','TSpinbox']:
            s.configure(n, fieldbackground=DARK, background=DARK,
                        foreground=TEXT, arrowcolor=GOLD)
        s.configure('TScrollbar', background=PANEL, troughcolor=DARK, arrowcolor=MUTED)
        s.configure('TNotebook', background=PANEL, tabmargins=0)
        s.configure('TNotebook.Tab', background=CARD, foreground=MUTED, padding=[12,5])
        s.map('TNotebook.Tab',
              background=[('selected',DARK)], foreground=[('selected',WHITE)])

    # ── Menu ─────────────────────────────────────────
    def _build_menu(self):
        mb = tk.Menu(self, bg=PANEL, fg=TEXT, activebackground=CARD,
                     activeforeground=WHITE, tearoff=False)

        fm = tk.Menu(mb, bg=PANEL, fg=TEXT, activebackground=CARD,
                     activeforeground=WHITE, tearoff=False)
        fm.add_command(label="New Score",               command=self._new,          accelerator="Ctrl+N")
        fm.add_command(label="Open Project…",           command=self._open,         accelerator="Ctrl+O")
        fm.add_command(label="Save",                    command=self._save,         accelerator="Ctrl+S")
        fm.add_command(label="Save As…",                command=self._save_as)
        fm.add_separator()
        fm.add_command(label="Import MusicXML / MXL…", command=self._import_mxl)
        fm.add_command(label="Import Finale (.musx)…", command=self._import_musx)
        fm.add_command(label="Import ABC…",             command=self._import_abc)
        fm.add_separator()
        fm.add_command(label="Load Template…",          command=self._load_template)
        fm.add_command(label="Save as Template…",       command=self._save_template)
        fm.add_separator()
        fm.add_command(label="Export MusicXML…",        command=self._export_mxml)
        fm.add_command(label="Export MIDI (Harmony)…",  command=self._export_midi)
        fm.add_command(label="Export PDF…",             command=self._print_dialog)
        fm.add_command(label="Export ABC…",             command=self._export_abc)
        fm.add_command(label="Export Tonic Solfa Text…",command=self._export_solfa_txt)
        fm.add_separator()
        fm.add_command(label="Print…",                  command=self._print_dialog,  accelerator="Ctrl+P")
        fm.add_separator()
        fm.add_command(label="Exit",                    command=self._quit,          accelerator="Alt+F4")
        mb.add_cascade(label="File", menu=fm)

        em = tk.Menu(mb, bg=PANEL, fg=TEXT, activebackground=CARD,
                     activeforeground=WHITE, tearoff=False)
        em.add_command(label="Undo",                command=self._undo,         accelerator="Ctrl+Z")
        em.add_command(label="Redo",                command=self._redo_cmd,     accelerator="Ctrl+Y")
        em.add_separator()
        em.add_command(label="Add Measure",         command=self._add_measure,  accelerator="Ctrl+M")
        em.add_command(label="Delete Last Measure", command=self._del_measure)
        em.add_command(label="Clear All Measures",  command=self._clear)
        em.add_separator()
        em.add_command(label="Score Properties…",   command=self._score_props)
        em.add_command(label="Add Lyrics…",         command=self._add_lyrics)
        em.add_command(label="Auto-Fill Rests…",    command=self._autofill_rests)
        mb.add_cascade(label="Edit", menu=em)

        vm = tk.Menu(mb, bg=PANEL, fg=TEXT, activebackground=CARD,
                     activeforeground=WHITE, tearoff=False)
        vm.add_command(label="Traditional Solfa View",  command=lambda: self.nb.select(0))
        vm.add_command(label="Staff Notation View",     command=lambda: self.nb.select(1))
        vm.add_command(label="Solfa Text Editor",       command=lambda: self.nb.select(2))
        vm.add_command(label="Note Editor",             command=lambda: self.nb.select(3))
        vm.add_command(label="Score Summary",           command=lambda: self.nb.select(4))
        vm.add_command(label="Solfa Reference Chart",   command=lambda: self.nb.select(5))
        mb.add_cascade(label="View", menu=vm)

        tm = tk.Menu(mb, bg=PANEL, fg=TEXT, activebackground=CARD,
                     activeforeground=WHITE, tearoff=False)
        tm.add_command(label="Convert Staff → Solfa",  command=self._to_solfa)
        tm.add_command(label="Transpose…",             command=self._transpose)
        rm = tk.Menu(tm, bg=PANEL, fg=TEXT, activebackground=CARD,
                     activeforeground=WHITE, tearoff=False)
        for lbl, val in [("Repeat Start ||:","repeat_start"),("Repeat End :|","repeat_end"),
                          ("Double Bar ||","double_bar")]:
            rm.add_command(label=lbl, command=lambda v=val: self._add_repeat(v))
        tm.add_cascade(label="Repeat Signs", menu=rm)
        tm.add_separator()
        tm.add_command(label="Library Status",          command=self._lib_status)
        mb.add_cascade(label="Tools", menu=tm)

        pm = tk.Menu(mb, bg=PANEL, fg=TEXT, activebackground=CARD,
                     activeforeground=WHITE, tearoff=False)
        pm.add_command(label="Play All Voices (Harmony)", command=self._play, accelerator="Space")
        pm.add_command(label="Stop",                      command=self._stop, accelerator="Escape")
        mb.add_cascade(label="Playback", menu=pm)

        hm = tk.Menu(mb, bg=PANEL, fg=TEXT, activebackground=CARD,
                     activeforeground=WHITE, tearoff=False)
        hm.add_command(label="Quick Guide",         command=self._guide)
        hm.add_command(label="Keyboard Shortcuts",  command=self._shortcuts)
        hm.add_separator()
        hm.add_command(label=f"About {APP_NAME}",   command=self._about)
        mb.add_cascade(label="Help", menu=hm)

        self.config(menu=mb)
        self.bind('<Control-n>', lambda e: self._new())
        self.bind('<Control-o>', lambda e: self._open())
        self.bind('<Control-s>', lambda e: self._save())
        self.bind('<Control-z>', lambda e: self._undo())
        self.bind('<Control-y>', lambda e: self._redo_cmd())
        self.bind('<Control-m>', lambda e: self._add_measure())
        self.bind('<Control-p>', lambda e: self._print_dialog())
        self.bind('<space>',     lambda e: self._play())
        self.bind('<Escape>',    lambda e: self._stop())

    # ── Toolbar ──────────────────────────────────────
    def _build_toolbar(self):
        tb = tk.Frame(self, bg=CARD, height=46); tb.pack(fill='x')
        tb.pack_propagate(False)

        def btn(text, tip, cmd, bg=CARD):
            b = tk.Button(tb, text=text, bg=bg, fg=TEXT, relief='flat',
                          font=('Arial',12), padx=6,
                          activebackground=DARK, activeforeground=WHITE, command=cmd)
            b.pack(side='left', padx=1, pady=6)
            _tooltip(b, tip); return b

        btn("📄","New",  self._new)
        btn("📂","Open", self._open)
        btn("💾","Save", self._save)
        _sep(tb)
        btn("📥","Import MXL",  self._import_mxl)
        btn("🎼","Import MUSX", self._import_musx)
        _sep(tb)

        self._tool_var = tk.StringVar(value='select')
        self._tool_btns = {}
        for sym, val, tip in [('↖','select','Select'),('♩','note','Note'),
                               ('𝄽','rest','Rest'),  ('✕','erase','Erase'),
                               ('T','lyric','Lyric')]:
            rb = tk.Radiobutton(tb, text=sym, variable=self._tool_var, value=val,
                                indicatoron=0, bg=CARD, fg=GOLD,
                                selectcolor=ACCENT, activebackground=DARK,
                                font=('Arial',12), padx=6, pady=5,
                                command=lambda v=val: self._set_tool(v))
            rb.pack(side='left', padx=1, pady=5)
            _tooltip(rb, tip); self._tool_btns[val] = rb
        _sep(tb)

        tk.Label(tb, text="Dur:", bg=CARD, fg=MUTED, font=('Arial',8)).pack(side='left')
        self._tb_dur = tk.StringVar(value='Q')
        self._tb_dur_btns = {}
        for sym, val, tip in [('W',4.0,'Whole'),('H',2.0,'Half'),('Q',1.0,'Quarter'),
                               ('E',0.5,'Eighth'),('S',0.25,'16th')]:
            rb = tk.Radiobutton(tb, text=sym, variable=self._tb_dur, value=sym,
                                indicatoron=0, bg=CARD, fg=GOLD,
                                selectcolor=ACCENT, activebackground=DARK,
                                font=('Arial',10,'bold'), padx=5, pady=5,
                                command=lambda v=val, s=sym: self._set_dur(v, s))
            rb.pack(side='left', padx=1, pady=5)
            _tooltip(rb, tip); self._tb_dur_btns[sym] = rb
        _sep(tb)

        self._tb_acc = tk.StringVar(value='')
        for sym, val, tip in [('♮','','Natural'),('♯','#','Sharp'),('♭','b','Flat')]:
            rb = tk.Radiobutton(tb, text=sym, variable=self._tb_acc, value=val,
                                indicatoron=0, bg=CARD, fg=GOLD,
                                selectcolor=ACCENT, activebackground=DARK,
                                font=('Arial',12), padx=4, pady=5,
                                command=lambda v=val: self._set_acc(v))
            rb.pack(side='left', padx=1, pady=5)
            _tooltip(rb, tip)
        _sep(tb)

        tk.Label(tb, text="Voice:", bg=CARD, fg=MUTED, font=('Arial',8)).pack(side='left')
        self._tb_voice = tk.IntVar(value=1)
        for lbl, v, c in [('S',1,ACCENT),('A',2,BLUE),('T',3,GREEN),('B',4,GOLD)]:
            rb = tk.Radiobutton(tb, text=lbl, variable=self._tb_voice, value=v,
                                indicatoron=0, bg=CARD, fg=c,
                                selectcolor=DARK, activebackground=DARK,
                                font=('Arial',10,'bold'), padx=5, pady=5,
                                command=lambda vv=v: self._set_voice(vv))
            rb.pack(side='left', padx=1, pady=5)
        _sep(tb)

        btn("▶","Play All", self._play, bg=CARD)
        btn("⏹","Stop",     self._stop, bg=CARD)
        btn("🖨","Print",    self._print_dialog, bg=CARD)
        _sep(tb)
        tk.Button(tb, text="Staff→Solfa", bg=ACCENT, fg=WHITE, relief='flat',
                  font=('Arial',8,'bold'),
                  command=self._to_solfa).pack(side='left', padx=3, pady=8)
        tk.Button(tb, text="+Measure", bg=GREEN, fg=DARK, relief='flat',
                  font=('Arial',8,'bold'),
                  command=self._add_measure).pack(side='left', padx=2, pady=8)
        badges = []
        if MIDIUTIL_OK:  badges.append("MIDI✓")
        if REPORTLAB_OK: badges.append("PDF✓")
        if PYGAME_OK:    badges.append("Audio✓")
        if badges:
            tk.Label(tb, text="  ".join(badges), bg=CARD, fg=GREEN,
                     font=('Arial',7)).pack(side='right', padx=10)

    def _set_tool(self, v):
        self._tool_var.set(v); self.staff_canvas.tool = v

    def _set_dur(self, vf, vs):
        self._tb_dur.set(vs)
        self.staff_canvas.cur_dur = vf
        if hasattr(self, 'props_panel'): self.props_panel._set_dur(vf)

    def _set_acc(self, v):
        self._tb_acc.set(v); self.staff_canvas.cur_acc = v

    def _set_voice(self, v):
        self._tb_voice.set(v); self.staff_canvas.cur_voice = v

    # ── Main layout ──────────────────────────────────
    def _build_main(self):
        paned = tk.PanedWindow(self, orient='horizontal', bg=DARK,
                               sashrelief='flat', sashwidth=5)
        paned.pack(fill='both', expand=True)

        self.props_panel = PropertiesPanel(paned, self.score, on_change=self._on_change)
        paned.add(self.props_panel, minsize=200, width=235)

        center = tk.Frame(paned, bg=DARK); paned.add(center, minsize=600)
        self.nb = ttk.Notebook(center); self.nb.pack(fill='both', expand=True)

        # Tab 0 – Traditional Tonic Solfa
        tf = tk.Frame(self.nb, bg=DARK); self.nb.add(tf, text="  📋 Traditional Solfa  ")
        ctrl = tk.Frame(tf, bg=CARD, height=30); ctrl.pack(fill='x'); ctrl.pack_propagate(False)
        tk.Label(ctrl, text="Traditional Tonic Solfa  (SATB · historical printed format)",
                 bg=CARD, fg=GOLD, font=('Arial',8,'bold')).pack(side='left', padx=10)
        tk.Button(ctrl, text="⟳ Refresh", bg=ACCENT, fg=WHITE, relief='flat',
                  font=('Arial',8), command=lambda: self.trad_canvas.set_score(self.score)
                  ).pack(side='right', padx=6, pady=3)
        vs = ttk.Scrollbar(tf, orient='vertical')
        hs = ttk.Scrollbar(tf, orient='horizontal')
        self.trad_canvas = TraditionalSolfaCanvas(
            tf, self.score, xscrollcommand=hs.set, yscrollcommand=vs.set)
        vs.config(command=self.trad_canvas.yview)
        hs.config(command=self.trad_canvas.xview)
        vs.pack(side='right', fill='y'); hs.pack(side='bottom', fill='x')
        self.trad_canvas.pack(fill='both', expand=True)

        # Tab 1 – Staff Notation
        sf = tk.Frame(self.nb, bg=DARK); self.nb.add(sf, text="  🎼 Staff Notation  ")
        vs2 = ttk.Scrollbar(sf, orient='vertical')
        hs2 = ttk.Scrollbar(sf, orient='horizontal')
        self.staff_canvas = StaffCanvas(
            sf, self.score, on_change=self._on_change,
            on_select=self._on_note_sel,
            xscrollcommand=hs2.set, yscrollcommand=vs2.set)
        vs2.config(command=self.staff_canvas.yview)
        hs2.config(command=self.staff_canvas.xview)
        vs2.pack(side='right', fill='y'); hs2.pack(side='bottom', fill='x')
        self.staff_canvas.pack(fill='both', expand=True)

        # Tab 2 – Solfa Text
        stf = tk.Frame(self.nb, bg=PANEL); self.nb.add(stf, text="  🎵 Solfa Text  ")
        self.solfa_panel = SolfaTextPanel(stf, self.score, on_change=self._on_change)
        self.solfa_panel.pack(fill='both', expand=True)

        # Tab 3 – Note Editor
        nef = tk.Frame(self.nb, bg=PANEL); self.nb.add(nef, text="  ✏ Note Editor  ")
        self.note_editor = NoteEditorPanel(nef, self.score, on_change=self._on_change)
        self.note_editor.pack(fill='both', expand=True)

        # Tab 4 – Summary
        smf = tk.Frame(self.nb, bg=DARK); self.nb.add(smf, text="  📊 Score Summary  ")
        self.summary = SummaryPanel(smf, self.score)
        self.summary.pack(fill='both', expand=True)

        # Tab 5 – Reference
        ref = tk.Frame(self.nb, bg=DARK); self.nb.add(ref, text="  📖 Solfa Reference  ")
        self.ref_panel = ReferencePanel(ref)
        self.ref_panel.pack(fill='both', expand=True)

        self.nb.bind('<<NotebookTabChanged>>', self._on_tab)

    def _build_statusbar(self):
        sb = tk.Frame(self, bg=CARD, height=26); sb.pack(fill='x', side='bottom')
        sb.pack_propagate(False)
        self.status_var = tk.StringVar(value=f"Ready  —  {APP_NAME} v{APP_VERSION}")
        self.info_var   = tk.StringVar(value="")
        tk.Label(sb, textvariable=self.status_var, bg=CARD, fg=MUTED,
                 font=('Arial',8), anchor='w').pack(side='left', padx=10)
        tk.Label(sb, textvariable=self.info_var, bg=CARD, fg=GREEN,
                 font=('Arial',8)).pack(side='right', padx=10)
        miss = [l for l, ok in [("midiutil",MIDIUTIL_OK),
                                  ("reportlab",REPORTLAB_OK),("pygame",PYGAME_OK)] if not ok]
        if miss:
            tk.Label(sb, text=f"⚠ pip install {' '.join(miss)}",
                     bg=CARD, fg=GOLD, font=('Arial',8)).pack(side='right', padx=10)

    # ── Rendering helpers ─────────────────────────────
    def _initial_render(self):
        self._auto_detect()
        self.trad_canvas.set_score(self.score)
        self.staff_canvas.set_score(self.score)
        self.solfa_panel.set_score(self.score)
        self.props_panel.refresh(self.score)
        self.note_editor.score = self.score
        self.summary.refresh(self.score)
        self._update_title(); self._update_info()

    def _auto_detect(self):
        if not self.score.measures: return
        vs = self.score.all_voices()
        n  = sum(len(m.notes) for m in self.score.measures)
        self.status_var.set(
            f"Loaded: {self.score.title}  |  {len(self.score.measures)} bars  "
            f"{n} notes  Voices: {', '.join(VOICE_NAMES.get(v,str(v)) for v in vs)}  "
            f"Key: {self.score.key_sig}  {self.score.time_num}/{self.score.time_den}")

    def _on_change(self):
        self.modified = True; self._update_title(); self._snap()
        self.trad_canvas.set_score(self.score)
        self.staff_canvas.set_score(self.score)
        self.props_panel.refresh(self.score)
        self._update_info()
        tab = self.nb.tab(self.nb.select(),'text')
        if 'Summary' in tab: self.summary.refresh(self.score)

    def _on_note_sel(self, m_idx, n_idx):
        if 0 <= m_idx < len(self.score.measures):
            m = self.score.measures[m_idx]
            if 0 <= n_idx < len(m.notes):
                self.note_editor.load_note(m.notes[n_idx], m_idx, n_idx)

    def _on_tab(self, event):
        tab = self.nb.tab(self.nb.select(),'text')
        if 'Summary'     in tab: self.summary.refresh(self.score)
        elif 'Reference' in tab: self.ref_panel._draw()
        elif 'Trad'      in tab: self.trad_canvas.redraw()
        elif 'Staff'     in tab: self.staff_canvas.redraw()
        self._update_info()

    def _update_title(self):
        mod  = " *" if self.modified else ""
        path = f"  [{os.path.basename(self.filepath)}]" if self.filepath else ""
        self.title(f"{APP_NAME}  —  {self.score.title}{path}{mod}")

    def _update_info(self):
        s  = self.score; vs = s.all_voices()
        n  = sum(len(m.notes) for m in s.measures)
        self.info_var.set(
            f"Key: {s.key_sig}  |  {s.time_num}/{s.time_den}  |  ♩={s.tempo_bpm}  |  "
            f"{len(s.measures)} bar{'s' if len(s.measures)!=1 else ''}  |  "
            f"{n} note{'s' if n!=1 else ''}  |  "
            f"{', '.join(VOICE_NAMES.get(v,str(v)) for v in vs)}")

    # ── Undo / Redo ───────────────────────────────────
    def _snap(self):
        try:
            self._hist.append(json.dumps(self.score.to_dict()))
            self._redo.clear()
        except Exception: pass

    def _undo(self):
        if len(self._hist) > 1:
            self._redo.append(self._hist.pop())
            self.score = Score.from_dict(json.loads(self._hist[-1]))
            self._reload(); self.status_var.set("Undo")
        else: self.status_var.set("Nothing to undo")

    def _redo_cmd(self):
        if self._redo:
            snap = self._redo.pop()
            self._hist.append(snap)
            self.score = Score.from_dict(json.loads(snap))
            self._reload(); self.status_var.set("Redo")
        else: self.status_var.set("Nothing to redo")

    def _reload(self):
        self.trad_canvas.set_score(self.score)
        self.staff_canvas.set_score(self.score)
        self.solfa_panel.set_score(self.score)
        self.props_panel.refresh(self.score)
        self.note_editor.score = self.score
        self._update_title(); self._update_info()

    # ── File operations ───────────────────────────────
    def _confirm(self) -> bool:
        if self.modified:
            return messagebox.askyesno("Unsaved Changes",
                "You have unsaved changes. Discard and continue?", parent=self)
        return True

    def _new(self):
        if not self._confirm(): return
        self.score = Score(title="Untitled Score"); self.score.ensure_measures(8)
        self.filepath = None; self.modified = False
        self._hist.clear(); self._redo.clear(); self._snap()
        self._initial_render(); self.status_var.set("New score created.")

    def _open(self):
        if not self._confirm(): return
        path = filedialog.askopenfilename(
            title="Open Project",
            filetypes=[("TSS Project","*.tss *.json"),("All Files","*.*")], parent=self)
        if not path: return
        try:
            with open(path,'r',encoding='utf-8') as f:
                self.score = Score.from_dict(json.load(f))
            self.filepath = path; self.modified = False
            self._hist.clear(); self._redo.clear(); self._snap()
            self._initial_render(); self.status_var.set(f"Opened: {path}")
        except Exception as e:
            messagebox.showerror("Open Error", str(e), parent=self)

    def _save(self):
        if self.filepath: self._write(self.filepath)
        else: self._save_as()

    def _save_as(self):
        path = filedialog.asksaveasfilename(
            title="Save Project", defaultextension=".tss",
            filetypes=[("TSS Project","*.tss"),("JSON","*.json")], parent=self)
        if path: self._write(path)

    def _write(self, path):
        try:
            with open(path,'w',encoding='utf-8') as f:
                json.dump(self.score.to_dict(), f, indent=2, ensure_ascii=False)
            self.filepath = path; self.modified = False
            self._update_title(); self.status_var.set(f"Saved: {path}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e), parent=self)

    def _save_template(self):
        safe = ''.join(c for c in self.score.title if c.isalnum() or c in ' _-').strip()
        path = filedialog.asksaveasfilename(
            title="Save as Template", defaultextension=".tss",
            initialfile=f"{safe or 'template'}.tss",
            filetypes=[("TSS Template","*.tss"),("JSON","*.json")], parent=self)
        if path: self._write(path)

    def _load_template(self):
        if not self._confirm(): return
        path = filedialog.askopenfilename(
            title="Load Template",
            filetypes=[
                ("All Supported","*.tss *.json *.xml *.musicxml *.mxl *.musx *.abc"),
                ("TSS Project","*.tss *.json"),
                ("MusicXML/MXL","*.xml *.musicxml *.mxl"),
                ("Finale MUSX","*.musx"),
                ("ABC","*.abc"),
                ("All Files","*.*"),
            ], parent=self)
        if not path: return
        self._load_file(path, as_template=True)

    def _load_file(self, path, as_template=False):
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext in ('.tss','.json'):
                with open(path,'r',encoding='utf-8') as f:
                    self.score = Score.from_dict(json.load(f))
            elif ext in ('.xml','.musicxml','.mxl'):
                self.score = ConversionEngine.import_mxl(path)
            elif ext == '.musx':
                self.score = ConversionEngine.import_musx(path)
            elif ext == '.abc':
                self.score = ConversionEngine.import_abc(path)
            else:
                messagebox.showwarning("Unsupported",
                    f"Format not supported: {ext}", parent=self); return
            if as_template: self.filepath = None
            self.modified = False
            self._hist.clear(); self._redo.clear(); self._snap()
            self._initial_render()
            self.status_var.set(f"✓ Loaded: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Load Error", str(e), parent=self)

    # ── Import ────────────────────────────────────────
    def _import_mxl(self):
        if not self._confirm(): return
        path = filedialog.askopenfilename(
            title="Import MusicXML / MXL",
            filetypes=[("MusicXML/MXL","*.xml *.musicxml *.mxl"),("All","*.*")], parent=self)
        if not path: return
        try:
            self.score = ConversionEngine.import_mxl(path)
            self.filepath = None; self.modified = True
            self._hist.clear(); self._redo.clear(); self._snap()
            self._initial_render()
            vs = self.score.all_voices()
            self.status_var.set(
                f"✓ Imported: {os.path.basename(path)}  "
                f"({len(self.score.measures)} bars, "
                f"{', '.join(VOICE_NAMES.get(v,str(v)) for v in vs)})")
        except Exception as e:
            messagebox.showerror("Import Error", str(e), parent=self)

    def _import_musx(self):
        if not self._confirm(): return
        path = filedialog.askopenfilename(
            title="Import Finale MUSX",
            filetypes=[("Finale MUSX","*.musx"),("All","*.*")], parent=self)
        if not path: return
        try:
            self.score = ConversionEngine.import_musx(path)
            self.filepath = None; self.modified = True
            self._hist.clear(); self._redo.clear(); self._snap()
            self._initial_render()
            notes = sum(len(m.notes) for m in self.score.measures)
            if notes == 0:
                messagebox.showinfo("MUSX Import",
                    "Metadata loaded (title, key, tempo).\n\n"
                    "For full note data: open in Finale → File → Export → MusicXML,\n"
                    "then import the .xml file here.", parent=self)
            self.status_var.set(f"✓ MUSX: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("MUSX Error", str(e), parent=self)

    def _import_abc(self):
        if not self._confirm(): return
        path = filedialog.askopenfilename(
            title="Import ABC", filetypes=[("ABC","*.abc"),("All","*.*")], parent=self)
        if not path: return
        try:
            self.score = ConversionEngine.import_abc(path)
            self.filepath = None; self.modified = True
            self._hist.clear(); self._redo.clear(); self._snap()
            self._initial_render()
            self.status_var.set(f"✓ ABC: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("ABC Error", str(e), parent=self)

    # ── Export ────────────────────────────────────────
    def _export_mxml(self):
        path = filedialog.asksaveasfilename(
            title="Export MusicXML", defaultextension=".xml",
            filetypes=[("MusicXML","*.xml"),("All","*.*")], parent=self)
        if not path: return
        try:
            with open(path,'w',encoding='utf-8') as f:
                f.write(ConversionEngine.export_musicxml(self.score))
            self.status_var.set(f"✓ MusicXML: {path}")
            messagebox.showinfo("Export", f"MusicXML saved:\n{path}", parent=self)
        except Exception as e:
            messagebox.showerror("Export Error", str(e), parent=self)

    def _export_midi(self):
        path = filedialog.asksaveasfilename(
            title="Export MIDI (Harmony)", defaultextension=".mid",
            filetypes=[("MIDI","*.mid"),("All","*.*")], parent=self)
        if not path: return
        try:
            with open(path,'wb') as f:
                f.write(ConversionEngine.export_midi_bytes_harmony(self.score))
            self.status_var.set(f"✓ MIDI: {path}")
            messagebox.showinfo("Export", f"MIDI saved:\n{path}", parent=self)
        except Exception as e:
            messagebox.showerror("MIDI Error", str(e), parent=self)

    def _export_abc(self):
        path = filedialog.asksaveasfilename(
            title="Export ABC", defaultextension=".abc",
            filetypes=[("ABC","*.abc"),("All","*.*")], parent=self)
        if not path: return
        try:
            with open(path,'w',encoding='utf-8') as f:
                f.write(ConversionEngine.export_abc(self.score))
            self.status_var.set(f"✓ ABC: {path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e), parent=self)

    def _export_solfa_txt(self):
        path = filedialog.asksaveasfilename(
            title="Export Tonic Solfa Text", defaultextension=".txt",
            filetypes=[("Text","*.txt"),("All","*.*")], parent=self)
        if not path: return
        try:
            with open(path,'w',encoding='utf-8') as f:
                f.write(ConversionEngine.export_solfa_text(self.score))
            self.status_var.set(f"✓ Solfa text: {path}")
            messagebox.showinfo("Export", f"Saved:\n{path}", parent=self)
        except Exception as e:
            messagebox.showerror("Export Error", str(e), parent=self)

    def _print_dialog(self):
        """Show print choice dialog (Solfa vs Staff) then save PDF."""
        PrintChoiceDialog(self, self.score)

    # ── Edit operations ───────────────────────────────
    def _add_measure(self):
        self.score.add_measure(); self._on_change()
        self.status_var.set(f"Added measure {len(self.score.measures)}")

    def _del_measure(self):
        if len(self.score.measures) > 1:
            self.score.measures.pop(); self._on_change()
            self.status_var.set("Deleted last measure.")

    def _clear(self):
        if messagebox.askyesno("Clear All","Delete all measures?", parent=self):
            self.score.measures.clear(); self.score.ensure_measures(8)
            self._on_change(); self.status_var.set("Cleared.")

    def _score_props(self):
        win = tk.Toplevel(self, bg=PANEL); win.title("Score Properties")
        win.geometry("420x320"); win.transient(self); win.grab_set()
        fields = [("Title",'title'),("Composer",'composer'),
                  ("Lyricist",'lyricist'),("Arranger",'arranger')]
        vs = {}
        for i,(lbl,attr) in enumerate(fields):
            tk.Label(win,text=lbl+':',bg=PANEL,fg=MUTED,font=('Arial',9)
                     ).grid(row=i,column=0,padx=15,pady=8,sticky='e')
            var = tk.StringVar(value=getattr(self.score,attr,''))
            tk.Entry(win,textvariable=var,bg=DARK,fg=WHITE,insertbackground=WHITE,
                     relief='flat',font=('Arial',10),width=32
                     ).grid(row=i,column=1,padx=5)
            vs[attr] = var
        def apply():
            for attr, var in vs.items(): setattr(self.score, attr, var.get())
            self._on_change(); win.destroy()
        tk.Button(win,text="Apply",bg=ACCENT,fg=WHITE,relief='flat',
                  command=apply).grid(row=len(fields),column=1,pady=15,sticky='e',padx=5)
        tk.Button(win,text="Cancel",bg=DARK,fg=TEXT,relief='flat',
                  command=win.destroy).grid(row=len(fields),column=0,pady=15)

    def _add_lyrics(self):
        win = tk.Toplevel(self, bg=PANEL); win.title("Add / Edit Lyrics")
        win.geometry("520x360"); win.transient(self)
        tk.Label(win, text="Enter lyrics — one word/syllable per note (Voice 1 only):",
                 bg=PANEL, fg=GOLD, font=('Arial',9,'bold')).pack(pady=8, padx=10, anchor='w')
        existing = [n.lyric for m in self.score.measures
                    for n in m.notes if n.voice==1 and not n.rest]
        txt = tk.Text(win, bg=DARK, fg=WHITE, insertbackground=WHITE,
                      font=('Arial',10), relief='flat', height=12, padx=10)
        txt.pack(fill='both', expand=True, padx=10, pady=5)
        txt.insert('1.0', '\n'.join(existing))
        def apply():
            words = txt.get('1.0','end').strip().replace('\n',' ').split()
            idx = 0
            for m in self.score.measures:
                for n in m.notes:
                    if n.voice==1 and not n.rest:
                        n.lyric = words[idx] if idx < len(words) else ''
                        idx += 1
            self._on_change(); win.destroy()
        tk.Button(win,text="Apply Lyrics",bg=GREEN,fg=DARK,relief='flat',
                  font=('Arial',9,'bold'),command=apply).pack(pady=8)

    def _autofill_rests(self):
        filled = 0
        for m in self.score.measures:
            if not m.notes:
                bu = 4.0 / m.time_den; beats = m.beats_available
                while beats >= bu-0.01:
                    m.notes.append(MusNote(rest=True, duration=bu)); beats -= bu
                filled += 1
        self._on_change(); self.status_var.set(f"Filled {filled} empty measures.")

    def _add_repeat(self, rtype):
        if not self.score.measures:
            messagebox.showwarning("Repeat","No measures.", parent=self); return
        m = self.score.measures[-1]
        if rtype=='repeat_start': m.repeat_start=True
        elif rtype=='repeat_end': m.repeat_end=True
        elif rtype=='double_bar': m.double_bar=True
        self._on_change()

    # ── Tools ─────────────────────────────────────────
    def _to_solfa(self):
        self.solfa_panel.refresh_from_score()
        self.trad_canvas.set_score(self.score)
        self.nb.select(2); self.status_var.set("✓ Converted to tonic solfa.")

    def _transpose(self):
        win = tk.Toplevel(self, bg=PANEL); win.title("Transpose")
        win.geometry("320x200"); win.transient(self); win.grab_set()
        tk.Label(win,text="Transpose Score",bg=PANEL,fg=GOLD,
                 font=('Arial',12,'bold')).pack(pady=10)
        r1 = tk.Frame(win,bg=PANEL); r1.pack(pady=5)
        tk.Label(r1,text="Semitones:",bg=PANEL,fg=TEXT).pack(side='left',padx=5)
        sv = tk.IntVar(value=0)
        tk.Spinbox(r1,from_=-12,to=12,textvariable=sv,bg=DARK,fg=WHITE,width=5).pack(side='left')
        r2 = tk.Frame(win,bg=PANEL); r2.pack(pady=5)
        tk.Label(r2,text="New Key:",bg=PANEL,fg=TEXT).pack(side='left',padx=5)
        kv = tk.StringVar(value=self.score.key_sig)
        ttk.Combobox(r2,textvariable=kv,values=KEYS,width=8,state='readonly').pack(side='left')
        def do_it():
            semis = sv.get()
            if semis:
                for m in self.score.measures:
                    for n in m.notes:
                        if not n.rest:
                            nm = n.midi_num + semis
                            n.pitch  = CHROM_TO_NOTE.get(nm % 12,'C')
                            n.octave = (nm // 12) - 1
            self.score.key_sig = kv.get()
            for m in self.score.measures: m.key_sig = kv.get()
            self._on_change()
            self.status_var.set(f"Transposed {semis:+d} → {kv.get()}")
            win.destroy()
        tk.Button(win,text="Transpose",bg=ACCENT,fg=WHITE,relief='flat',
                  command=do_it).pack(pady=15)

    # ── Playback ──────────────────────────────────────
    def _play(self):
        if not PYGAME_OK:
            messagebox.showinfo("Playback","Install pygame:\npip install pygame",parent=self); return
        try:
            mid = ConversionEngine.export_midi_bytes_harmony(self.score)
            pygame.mixer.music.load(io.BytesIO(mid))
            pygame.mixer.music.play()
            vs = self.score.all_voices()
            self.status_var.set(f"▶ Playing {len(vs)} voices: "
                                f"{', '.join(VOICE_NAMES.get(v,str(v)) for v in vs)}")
        except Exception as e:
            messagebox.showerror("Playback Error", str(e), parent=self)

    def _stop(self):
        if PYGAME_OK:
            try: pygame.mixer.music.stop()
            except: pass
        self.status_var.set("⏹ Stopped.")

    # ── Info dialogs ──────────────────────────────────
    def _lib_status(self):
        messagebox.showinfo("Library Status",
            f"midiutil   : {'✓' if MIDIUTIL_OK  else '✗  pip install midiutil'}\n"
            f"reportlab  : {'✓' if REPORTLAB_OK else '✗  pip install reportlab'}\n"
            f"pygame     : {'✓' if PYGAME_OK    else '✗  pip install pygame'}\n\n"
            "Core features work without any libraries.\n"
            "midiutil→MIDI  reportlab→PDF  pygame→Playback",
            parent=self)

    def _guide(self):
        text = """TONIC SOLFA STUDIO v5.0 — Quick Guide
══════════════════════════════════════════

TRADITIONAL SOLFA VIEW (Tab 0):
  Renders all 4 SATB voices in traditional grid format.
  Voice labels: Sop. Alto Ten. Bass
  Beats separated by ':', barlines by '|'
  '—' = held beat   ' = upper octave   ₁ = lower octave

STAFF NOTATION VIEW (Tab 1):
  Grand staff: SA on treble, TB on bass
  Soprano (S) stems up, Alto (A) stems down
  Tenor (T) stems up, Bass (B) stems down
  Key sig and time sig drawn on both staves

NOTE INPUT:
  Select tool in toolbar → ↖ Select  ♩ Note  𝄽 Rest  ✕ Erase  T Lyric
  Duration: W H Q E S (Whole Half Quarter Eighth 16th)
  Voice: S A T B

IMPORTING FILES:
  MusicXML (.mxl, .xml) — all 4 SATB voices via root XML
  Finale MUSX (.musx)   — metadata + embedded XML if available
  ABC (.abc)            — melody import

PLAYBACK:
  'Play All' plays ALL voices in harmony simultaneously
  Separate MIDI tracks: one per voice (S/A/T/B)
  Uses midiutil for highest quality; raw MIDI fallback otherwise

PRINT / PDF:
  File > Print or toolbar 🖨 shows choice dialog:
  → Traditional Tonic Solfa PDF (all voices, grid format)
  → Staff Notation PDF (voice reference table)

KEYBOARD SHORTCUTS:
  Ctrl+N  New    Ctrl+O  Open    Ctrl+S  Save    Ctrl+P  Print
  Ctrl+Z  Undo   Ctrl+Y  Redo    Ctrl+M  Add Measure
  Space   Play   Escape  Stop
"""
        win = tk.Toplevel(self, bg=DARK); win.title("Quick Guide"); win.geometry("560,520")
        win.geometry("560x520")
        t = tk.Text(win, bg=DARK, fg=TEXT, font=('Courier New',10),
                    relief='flat', padx=20, pady=20, wrap='word')
        t.pack(fill='both', expand=True)
        t.insert('1.0', text); t.config(state='disabled')

    def _shortcuts(self):
        messagebox.showinfo("Keyboard Shortcuts",
            "Ctrl+N  New Score\n"
            "Ctrl+O  Open Project\n"
            "Ctrl+S  Save\n"
            "Ctrl+P  Print / Export PDF\n"
            "Ctrl+Z  Undo\n"
            "Ctrl+Y  Redo\n"
            "Ctrl+M  Add Measure\n"
            "Space   Play All Voices\n"
            "Escape  Stop", parent=self)

    def _about(self):
        messagebox.showinfo(f"About {APP_NAME}",
            f"{APP_NAME}  v{APP_VERSION}\n\n"
            "Professional Music Notation & Tonic Solfa Software\n"
            "Staff Notation ↔ Traditional Tonic Solfa (SATB)\n\n"
            "v5.0 fixes:\n"
            "  ✅ SATB 4-voice display (Sop Alto Ten Bass)\n"
            "  ✅ MXL import reads root XML (all 4 voices)\n"
            "  ✅ Harmony playback — all voices simultaneously\n"
            "  ✅ Multi-track MIDI export (1 track per voice)\n"
            "  ✅ Print dialog — choose Solfa or Staff PDF\n"
            "  ✅ Grand staff: SA treble + TB bass with bracket\n"
            "  ✅ Proper undo/redo with separate redo stack\n"
            "  ✅ Key sig drawn on both treble and bass staves\n\n"
            "Formats: MusicXML, MIDI, PDF, ABC, TSS project",
            parent=self)

    def _quit(self):
        if not self._confirm(): return
        if PYGAME_OK:
            try: pygame.quit()
            except: pass
        self.destroy()


# ═══════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════
def _sep(parent):
    tk.Frame(parent, bg='#2a3a5a', width=1).pack(side='left', fill='y', padx=5, pady=6)

def _tooltip(widget, text: str):
    tip = None
    def show(e):
        nonlocal tip
        x = widget.winfo_rootx()+10; y = widget.winfo_rooty()+widget.winfo_height()+3
        tip = tk.Toplevel(widget); tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        tk.Label(tip, text=text, bg='#ffffcc', fg='#333333',
                 relief='solid', font=('Arial',8), padx=4, pady=2).pack()
    def hide(e):
        nonlocal tip
        if tip:
            try: tip.destroy()
            except: pass
            tip = None
    widget.bind('<Enter>', show); widget.bind('<Leave>', hide)


# ═══════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════
def main():
    print("="*58)
    print(f"  {APP_NAME}  v{APP_VERSION}")
    print("="*58)
    print(f"  midiutil   : {'✓' if MIDIUTIL_OK  else '✗  pip install midiutil'}")
    print(f"  reportlab  : {'✓' if REPORTLAB_OK else '✗  pip install reportlab'}")
    print(f"  pygame     : {'✓' if PYGAME_OK    else '✗  pip install pygame'}")
    print("="*58)
    print()
    print("  v5.0 changes:")
    print("  • SATB 4-voice display (all voices in trad solfa)")
    print("  • MXL import uses root XML (correct 4-voice data)")
    print("  • Harmony playback — all voices simultaneously")
    print("  • Print dialog — choose Solfa or Staff PDF")
    print("  • Grand staff: SA treble + TB bass with bracket")
    print()
    app = TonicSolfaStudio()
    app.mainloop()

if __name__ == '__main__':
    main()
