"""
Tonic Solfa Notation Models
============================
Data structures representing every element found in traditional
tonic-solfa scores (as seen in Monto Dwom & Wasɔr by O. A. McPRINCE).
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from enum import Enum


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Octave(Enum):
    """Octave displacement relative to the default (middle) octave."""
    LOW2   = -2   # double subscript  e.g. d2 below
    LOW1   = -1   # subscript 1      e.g. d1 (written as d₁ / d1 in ASCII)
    MID    =  0   # no mark
    HIGH1  =  1   # superscript 1    e.g. d¹
    HIGH2  =  2   # superscript 2


class Duration(Enum):
    """Standard durations expressed as fractions of a beat."""
    DOUBLE_WHOLE = 8.0
    WHOLE        = 4.0
    HALF         = 2.0
    QUARTER      = 1.0
    EIGHTH       = 0.5
    SIXTEENTH    = 0.25
    THIRTY_SECOND = 0.125


class Dynamic(Enum):
    """Dynamic markings."""
    PPP = "ppp"
    PP  = "pp"
    P   = "p"
    MP  = "mp"
    MF  = "mf"
    F   = "f"
    FF  = "ff"
    FFF = "fff"
    SF  = "sf"
    SFZ = "sfz"
    FP  = "fp"


class Accidental(Enum):
    """Chromatic alterations used in tonic-solfa (e.g. 'fe', 'ta', 'se')."""
    NATURAL  = ""
    SHARP    = "i"    # raised  → suffix 'i' (di, ri, fi, si, li)
    FLAT     = "a"    # lowered → suffix 'a' (ra, ma, se/sa, la, ta)
    # Tonic-solfa specific names
    SE       = "se"   # flattened 's'  (≈ Ab)
    FE       = "fe"   # sharpened 'f'  (≈ F#)
    TA       = "ta"   # flattened 't'  (≈ Bb)


class ArticulationMark(Enum):
    """Articulation / expression marks."""
    NONE        = ""
    STACCATO    = "."
    ACCENT      = ">"
    TENUTO      = "-"
    MARCATO     = "^"
    FERMATA     = "U"


class BarlineType(Enum):
    SINGLE      = "|"
    DOUBLE      = "||"
    FINAL       = "|."
    REPEAT_OPEN  = "|:"
    REPEAT_CLOSE = ":|"
    DOUBLE_REPEAT = ":|:"


# ---------------------------------------------------------------------------
# Core note / rest / beat structures
# ---------------------------------------------------------------------------

@dataclass
class SolfaNote:
    """
    A single tonic-solfa pitch syllable with all its decorations.

    Syllable conventions
    --------------------
    d  r  m  f  s  l  t   – the seven degrees
    Subscript  1 (octave LOW1)  written  d1 r1 m1 …
    Superscript 1 (octave HIGH1) written d' r' m' … (or d^ in ASCII)
    Accidentals: se, fe, ta, ra, ma, la, di, ri, fi, si, li
    """
    syllable:     str              # 'd', 'r', 'm', 'f', 's', 'l', 't'
    octave:       Octave           = Octave.MID
    accidental:   Accidental       = Accidental.NATURAL
    duration:     float            = 1.0   # in beats (quarter note = 1.0)
    dot:          bool             = False  # dotted note → ×1.5
    double_dot:   bool             = False  # double-dotted → ×1.75
    tied_forward: bool             = False  # ~ connects to next note
    slur_start:   bool             = False
    slur_end:     bool             = False
    articulation: ArticulationMark = ArticulationMark.NONE
    dynamic:      Optional[Dynamic] = None
    lyric:        str              = ""    # syllable of text under note
    lyric_hyphen: bool             = False # lyric continues (-)
    lyric_extender: bool           = False # lyric extender line ___

    @property
    def actual_duration(self) -> float:
        """Duration after applying dot(s)."""
        d = self.duration
        if self.double_dot:
            return d * 1.75
        if self.dot:
            return d * 1.5
        return d

    @property
    def display_name(self) -> str:
        """Human-readable pitch name including accidental & octave."""
        base = self.syllable
        if self.accidental != Accidental.NATURAL:
            base += self.accidental.value
        if self.octave == Octave.LOW1:
            base += "₁"
        elif self.octave == Octave.LOW2:
            base += "₂"
        elif self.octave == Octave.HIGH1:
            base += "¹"
        elif self.octave == Octave.HIGH2:
            base += "²"
        return base

    def __repr__(self):
        return f"SolfaNote({self.display_name}, dur={self.actual_duration})"


@dataclass
class SolfaRest:
    """A silence/rest of a given duration."""
    duration:  float = 1.0
    dot:       bool  = False
    double_dot: bool = False

    @property
    def actual_duration(self) -> float:
        d = self.duration
        if self.double_dot:
            return d * 1.75
        if self.dot:
            return d * 1.5
        return d

    def __repr__(self):
        return f"SolfaRest(dur={self.actual_duration})"


# A beat-cell can hold one or more notes (for simultaneous parts on one beat)
BeatItem = SolfaNote | SolfaRest


@dataclass
class Beat:
    """
    One rhythmic position in a bar.
    voices[0] = top voice, voices[1] = bottom voice (SATB layout uses 4).
    """
    items: List[BeatItem] = field(default_factory=list)

    def add(self, item: BeatItem):
        self.items.append(item)


# ---------------------------------------------------------------------------
# Bar / Measure
# ---------------------------------------------------------------------------

@dataclass
class Bar:
    """
    One measure in the score.

    In tonic-solfa layout each bar is a visual column.
    The colons ':' and pipes '|' delimit beats within a bar.
    """
    number:       int
    beats:        List[Beat]            = field(default_factory=list)
    barline_end:  BarlineType           = BarlineType.SINGLE
    barline_start: BarlineType          = BarlineType.SINGLE
    rehearsal_mark: Optional[str]       = None   # e.g. "A", "1.", "2."
    tempo_mark:   Optional[str]         = None   # e.g. "Andante", ♩=80
    dynamic_mark: Optional[Dynamic]     = None
    dynamic_hairpin_cresc:  bool        = False
    dynamic_hairpin_decresc: bool       = False
    double_bar:   bool                  = False
    repeat_open:  bool                  = False
    repeat_close: bool                  = False
    first_ending: bool                  = False
    second_ending: bool                 = False
    voices: List[List[BeatItem]]        = field(default_factory=list)

    @property
    def beat_count(self) -> int:
        return len(self.beats)


# ---------------------------------------------------------------------------
# Voice / Part
# ---------------------------------------------------------------------------

@dataclass
class VoicePart:
    """
    One voice part (Soprano, Alto, Tenor, Bass or a single-line melody).
    Holds an ordered list of bars.
    """
    name:  str          # e.g. "Soprano", "Alto", "Melody"
    clef:  str = "treble"
    bars:  List[Bar] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Score metadata
# ---------------------------------------------------------------------------

@dataclass
class ScoreMetadata:
    title:          str   = "Untitled"
    composer:       str   = ""
    arranger:       str   = ""
    key_note:       str   = "C"   # The 'Doh' note, e.g. "G", "C"
    time_numerator: int   = 4
    time_denominator: int = 4
    tempo_bpm:      int   = 80
    tempo_text:     str   = ""    # e.g. "Andante", "With victorious expressiveness"
    date:           str   = ""
    dedication:     str   = ""    # e.g. "To Ebenezer Methodist Choir"
    language:       str   = ""    # e.g. "Twi / Akan", "English"
    location:       str   = ""    # e.g. "Asante Mampong"


# ---------------------------------------------------------------------------
# Full Score
# ---------------------------------------------------------------------------

@dataclass
class TonicSolfaScore:
    """
    Top-level container for a complete tonic-solfa score.
    Multiple VoiceParts make up an SATB or other ensemble arrangement.
    """
    metadata: ScoreMetadata             = field(default_factory=ScoreMetadata)
    parts:    List[VoicePart]           = field(default_factory=list)
    lyrics:   List[List[str]]           = field(default_factory=list)  # verse lines
    verse_labels: List[str]             = field(default_factory=list)  # "1.", "2."

    def add_part(self, part: VoicePart):
        self.parts.append(part)

    @property
    def bar_count(self) -> int:
        if not self.parts:
            return 0
        return max(len(p.bars) for p in self.parts)
