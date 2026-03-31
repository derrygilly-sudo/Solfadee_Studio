"""
Score Bridge Converter
=======================
Converts SolfaDee Studio's native Score/MusNote/Measure model
into the TonicSolfaScore/SolfaNote/Bar model used by
canvas_renderer.py and pdf_exporter.py.

This means ANY score imported via MusicXML, MIDI, ABC or Finale
can be rendered on the new canvas and exported via the new PDF engine.

Usage
-----
    from score_bridge import bridge_score_to_solfa
    from canvas_renderer import TonicSolfaCanvas
    from pdf_exporter import TonicSolfaPDFExporter

    tsc = bridge_score_to_solfa(your_score)          # convert
    canvas = TonicSolfaCanvas(parent_frame, tsc)      # render
    TonicSolfaPDFExporter(tsc).export("out.pdf")      # PDF
"""

from models import (
    TonicSolfaScore, ScoreMetadata, VoicePart, Bar,
    SolfaNote, SolfaRest,
    Octave, Accidental, Dynamic, ArticulationMark, BarlineType
)


# ── Voice number → part name ────────────────────────────────────────────────
_VOICE_NAMES = {1: "Soprano", 2: "Alto", 3: "Tenor", 4: "Bass"}

# ── Duration (beats) → nearest standard value ───────────────────────────────
_STD_DURS = [4.0, 3.0, 2.0, 1.5, 1.0, 0.75, 0.5, 0.375, 0.25, 0.125, 0.0625]


def _nearest_dur(beats: float):
    """
    Return (duration_base, dotted) closest to the given beat value.
    dot=True means duration_base * 1.5 ≈ beats.
    """
    if beats <= 0:
        return 0.25, False
    best = min(_STD_DURS, key=lambda d: abs(d - beats))
    # Check if a dotted version of a shorter duration is closer
    dot_candidates = [(d, True) for d in [4.0, 2.0, 1.0, 0.5, 0.25, 0.125]
                      if abs(d * 1.5 - beats) < abs(best - beats)]
    if dot_candidates:
        d, dotted = min(dot_candidates, key=lambda x: abs(x[0] * 1.5 - beats))
        return d, True
    return best, False


# ── Octave integer → Octave enum ────────────────────────────────────────────
def _octave_enum(octave_int: int, home: int = 4) -> Octave:
    diff = octave_int - home
    if diff <= -2: return Octave.LOW2
    if diff == -1: return Octave.LOW1
    if diff == 0:  return Octave.MID
    if diff == 1:  return Octave.HIGH1
    return Octave.HIGH2


# ── Accidental string → Accidental enum ─────────────────────────────────────
def _accidental_enum(pitch: str, acc_str: str) -> Accidental:
    """
    Derive accidental from pitch string ('#', 'b') or explicit acc field.
    Tonic-solfa specific names (se, fe, ta) are derived from the syllable.
    """
    combined = (pitch or "") + (acc_str or "")
    if "#"  in combined: return Accidental.SHARP
    if "b"  in combined: return Accidental.FLAT
    return Accidental.NATURAL


# ── Dynamic string → Dynamic enum ───────────────────────────────────────────
_DYN_MAP = {
    "pppp": Dynamic.PPP, "ppp": Dynamic.PPP, "pp": Dynamic.PP,
    "p":    Dynamic.P,   "mp":  Dynamic.MP,  "mf": Dynamic.MF,
    "f":    Dynamic.F,   "ff":  Dynamic.FF,  "fff": Dynamic.FFF,
    "ffff": Dynamic.FFF, "sf":  Dynamic.SF,  "sfz": Dynamic.SFZ,
    "sfp":  Dynamic.FP,  "fp":  Dynamic.FP,  "fz":  Dynamic.SF,
    "rf":   Dynamic.SF,  "rfz": Dynamic.SFZ,
}


def _dynamic_enum(dyn_str: str) -> "Dynamic | None":
    return _DYN_MAP.get((dyn_str or "").strip().lower())


# ── Articulation string → ArticulationMark enum ─────────────────────────────
_ART_MAP = {
    "staccato": ArticulationMark.STACCATO,
    "accent":   ArticulationMark.ACCENT,
    "tenuto":   ArticulationMark.TENUTO,
    "marcato":  ArticulationMark.MARCATO,
    "fermata":  ArticulationMark.FERMATA,
}


def _art_enum(art_str: str) -> ArticulationMark:
    return _ART_MAP.get((art_str or "").strip().lower(), ArticulationMark.NONE)


# ── BarlineType from Measure flags ──────────────────────────────────────────
def _barline_end(measure) -> BarlineType:
    if getattr(measure, "repeat_end",   False): return BarlineType.REPEAT_CLOSE
    if getattr(measure, "double_bar",   False): return BarlineType.DOUBLE
    return BarlineType.SINGLE


def _barline_start(measure) -> BarlineType:
    if getattr(measure, "repeat_start", False): return BarlineType.REPEAT_OPEN
    return BarlineType.SINGLE


# ── Convert one MusNote → SolfaNote ─────────────────────────────────────────
def _convert_note(mus_note, key: str, home_octave: int) -> "SolfaNote | SolfaRest":
    """
    Convert a single MusNote from the native model into a SolfaNote
    (or SolfaRest) for the new canvas/PDF model.
    """
    beats = getattr(mus_note, "beats", mus_note.duration)

    # Rest
    if getattr(mus_note, "rest", False):
        dur, dot = _nearest_dur(beats)
        return SolfaRest(duration=dur, dot=dot)

    # Syllable — use the existing solfa() method on MusNote
    try:
        full_sym = mus_note.solfa_syllable(key)  # e.g. 'd', 'r', 'se', 'fe'
    except Exception:
        full_sym = "d"

    # Separate base syllable from chromatic suffix
    # Chromatic syllables: de re fe se le  (sharp-type)
    #                      ra ma la ta     (flat-type)
    CHROMATIC_SHARP = {"de", "re", "fe", "se", "le"}
    CHROMATIC_FLAT  = {"ra", "ma", "la", "ta"}
    CHROM_SOLFA_MAP = {
        "de": ("d", Accidental.SHARP),
        "re": ("r", Accidental.SHARP),
        "fe": ("f", Accidental.FE),
        "se": ("s", Accidental.SE),
        "le": ("l", Accidental.SHARP),
        "ra": ("r", Accidental.FLAT),
        "ma": ("m", Accidental.FLAT),
        "la": ("l", Accidental.FLAT),
        "ta": ("t", Accidental.TA),
    }

    if full_sym in CHROM_SOLFA_MAP:
        syllable, accidental = CHROM_SOLFA_MAP[full_sym]
    else:
        syllable   = full_sym[:1] if full_sym else "d"
        accidental = _accidental_enum(
            getattr(mus_note, "pitch", ""),
            getattr(mus_note, "accidental", "")
        )

    # Octave
    oct_int  = getattr(mus_note, "octave", 4)
    octave   = _octave_enum(oct_int, home_octave)

    # Duration
    dur, dot = _nearest_dur(beats)

    # Build SolfaNote
    return SolfaNote(
        syllable     = syllable,
        octave       = octave,
        accidental   = accidental,
        duration     = dur,
        dot          = dot,
        tied_forward = getattr(mus_note, "tied",        False),
        slur_start   = getattr(mus_note, "slur_start",  False),
        slur_end     = getattr(mus_note, "slur_stop",   False),
        articulation = _art_enum(getattr(mus_note, "articulation", "")),
        dynamic      = _dynamic_enum(getattr(mus_note, "dynamic", "")),
        lyric        = getattr(mus_note, "lyric",       ""),
        lyric_hyphen = "-" in getattr(mus_note, "lyric", ""),
    )


# ── Convert one Measure → Bar ────────────────────────────────────────────────
def _convert_measure(measure, voice_list: list) -> Bar:
    """
    Convert a native Measure into a Bar.
    Each voice becomes one entry in bar.voices (list of note lists).
    """
    bar = Bar(
        number        = getattr(measure, "number", 1),
        barline_start = _barline_start(measure),
        barline_end   = _barline_end(measure),
        rehearsal_mark= getattr(measure, "rehearsal", None) or None,
        dynamic_mark  = _dynamic_enum(getattr(measure, "dynamic", "")),
        repeat_open   = getattr(measure, "repeat_start", False),
        repeat_close  = getattr(measure, "repeat_end",   False),
        double_bar    = getattr(measure, "double_bar",   False),
    )

    key = getattr(measure, "key_sig", "C")

    for voice in voice_list:
        # Home octave: treble voices (1,2) → 4, bass voices (3,4) → 3
        home_oct = 4 if voice <= 2 else 3

        raw_notes = [n for n in measure.notes if getattr(n, "voice", 1) == voice]

        converted = []
        for mn in raw_notes:
            converted.append(_convert_note(mn, key, home_oct))

        bar.voices.append(converted)

    return bar


# ── Main bridge function ─────────────────────────────────────────────────────
def bridge_score_to_solfa(score) -> TonicSolfaScore:
    """
    Convert a SolfaDee Studio Score object into a TonicSolfaScore
    suitable for TonicSolfaCanvas and TonicSolfaPDFExporter.

    Parameters
    ----------
    score : Score
        A native SolfaDee Studio Score instance (from the main app's
        data model — Score, Measure, MusNote).

    Returns
    -------
    TonicSolfaScore
        Ready to pass to TonicSolfaCanvas or TonicSolfaPDFExporter.
    """
    # ── Metadata ────────────────────────────────────────────────────────────
    meta = ScoreMetadata(
        title           = getattr(score, "title",     "Untitled"),
        composer        = getattr(score, "composer",  ""),
        arranger        = getattr(score, "arranger",  ""),
        key_note        = getattr(score, "key_sig",   "C"),
        time_numerator  = getattr(score, "time_num",  4),
        time_denominator= getattr(score, "time_den",  4),
        tempo_bpm       = getattr(score, "tempo_bpm", 80),
        tempo_text      = "",
    )

    tsc = TonicSolfaScore(metadata=meta)

    # ── Voices present in this score ────────────────────────────────────────
    all_voices = score.all_voices() if hasattr(score, "all_voices") else [1]
    if not all_voices:
        all_voices = [1]

    # ── Build one VoicePart per SATB voice ──────────────────────────────────
    # We keep all voices together in one "part" with multiple voice lanes,
    # matching the traditional SATB grid (two rows: SA top, TB bottom).
    # Alternatively build separate VoiceParts per voice — both work.
    # Here we use one VoicePart per voice for maximum flexibility.

    # Group: upper voices (S, A = 1, 2) and lower (T, B = 3, 4)
    upper = [v for v in all_voices if v <= 2]
    lower = [v for v in all_voices if v >  2]
    groups = []
    if upper: groups.append(("SA", upper))
    if lower: groups.append(("TB", lower))
    if not groups:
        groups = [("Voice 1", [1])]

    for group_name, voice_list in groups:
        part = VoicePart(name=group_name)

        for measure in score.measures:
            bar = _convert_measure(measure, voice_list)
            part.bars.append(bar)

        tsc.add_part(part)

    # ── Lyrics (collect from voice 1, grouped by system row) ────────────────
    # Pull all lyrics from voice 1 across measures into verse lines
    all_lyrics = []
    for measure in score.measures:
        v1_notes = [n for n in measure.notes
                    if getattr(n, "voice", 1) == 1 and not getattr(n, "rest", False)]
        line = " ".join(n.lyric for n in v1_notes if getattr(n, "lyric", ""))
        if line:
            all_lyrics.append(line)

    if all_lyrics:
        tsc.lyrics      = [all_lyrics]
        tsc.verse_labels = ["Lyrics"]

    return tsc
