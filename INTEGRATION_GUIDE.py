"""
SOLFADEE STUDIO — INTEGRATION GUIDE
====================================
How to merge the two fix files into the original solfadee_studio_v5.py.

The two fix files are:
  solfadee_fixed_core.py   — Steps 1 & 2 (octave system + beat-map)
  solfadee_fixed_canvas.py — Steps 3 & 4 (alignment + new features)

────────────────────────────────────────────────────────────────
STEP 1 — OCTAVE SYSTEM FIX  (solfadee_fixed_core.py)
────────────────────────────────────────────────────────────────

REPLACE the existing get_home_octave() function:

  OLD (lines ~109-117 in original):
    def get_home_octave(key: str, voice: int) -> int:
        if voice in [1, 2]:  # soprano, alto
            return 4
        else:  # tenor, bass
            return 3

  NEW:
    def get_home_octave(key: str, voice: int) -> int:
        return 4   # always 4 — all voices share the same home note

RATIONALE:
  The specification (Document 2) states that all voices share the same
  home note — the tonic of the key in octave 4.  Returning octave 3
  for tenor/bass was incorrect because it shifted their displacement
  calculation, making C3 appear as 'd' (home) rather than 'd₁' (one
  below home).  Bass notes in octave 3 must show subscript ₁.

NO changes needed to MusNote.solfa() — the fix flows automatically
from correcting get_home_octave().


────────────────────────────────────────────────────────────────
STEP 2 — BEAT-MAP DOUBLING FIX  (solfadee_fixed_core.py)
────────────────────────────────────────────────────────────────

REPLACE MusNote.duration_underscores():

  OLD — returned strings starting with ':' (e.g. ':-', ':-:-')
  which collided with the ':' beat separator in _join_measure_slots.

  NEW (from solfadee_fixed_core.py):
    def duration_underscores(self) -> str:
        d = self.beats
        if d >= 1.0:  return ''      # multi-beat: shown by '—' hold tokens
        if d >= 0.75: return '.·'    # dotted eighth
        if d >= 0.5:  return '.'     # eighth
        if d >= 0.25: return ','     # sixteenth
        return ';'                   # 32nd

REPLACE _join_measure_slots() to use ' : ' (with spaces) as separator
so beat boundaries are visually distinct from any note-text content:

  OLD: f"{slots[0]} :{slots[1]}"     # no space before colon
  NEW: f"{slots[0]} : {slots[1]}"    # space both sides — unambiguous

REPLACE _note_display_symbol() to return '0' for rests instead of ''
so empty beat slots are never invisible.

ALSO in build_measure_string():
  • Change hold token from '-' to '—' (em dash) for print clarity.
  • Change empty beat from '' to '·' so slots are never blank.

FIX duplicate @dataclass decorator on Measure class:
  Remove the second @dataclass line immediately before class Measure:.


────────────────────────────────────────────────────────────────
STEP 3 — ALIGNMENT FIX  (solfadee_fixed_canvas.py)
────────────────────────────────────────────────────────────────

REPLACE the entire TraditionalSolfaCanvas class with the version
in solfadee_fixed_canvas.py.

Key differences:

  1. MEASURE WIDTH is now proportional:
       OLD: meas_w = self.measure_width   (flat 200 px constant)
       NEW: meas_w = meas.time_num * self.beat_width
     A 4/4 measure at beat_width=50 → 200 px.
     A 6/8 measure at beat_width=50 → 300 px.
     A 2/4 measure at beat_width=50 → 100 px.

  2. NOTE TOKENS are drawn at computed x-positions:
       OLD: one create_text call at x+6 with the full measure string
       NEW: for each note n at beat position pos:
              nx = x + (pos / beat_unit) * beat_width + 4
              create_text(nx, vy_mid, text=syllable, anchor='w')

  3. HOLD DASHES drawn at subsequent beat positions rather than
     inlined as text in a single string dump.

  4. BEAT SEPARATORS drawn as light dashed vertical lines
     (not the ':' colon character).

  5. TOTAL ROW WIDTH computed as sum of each measure's individual
     width so mixed time-signature rows are correct.

  6. TAG SYSTEM: all content items tagged 'content'; rulers tagged
     'ruler'.  redraw() deletes 'content' only, leaving rulers intact.


────────────────────────────────────────────────────────────────
STEP 4 — NEW FEATURES  (solfadee_fixed_canvas.py)
────────────────────────────────────────────────────────────────

ADD the three new classes before TraditionalSolfaCanvas:
  • FontTabPanel         (font + lyric-font selectors)
  • SolfaCanvasLayoutPanel  (bars/line, beat px, row gap, fit, bar #s)
  • CanvasRulerOverlay   (draggable screen-only rulers)

REPLACE the Solfa Canvas tab assembly code in
TonicSolfaStudio._build_main() with a call to build_trad_canvas_tab():

  OLD pattern in _build_main():
    tf = tk.Frame(self.nb, bg=DARK)
    self.nb.add(tf, text="  📋 Traditional Solfa  ")
    ... manual ctrl bar ...
    self.trad_canvas = TraditionalSolfaCanvas(tf, self.score, ...)

  NEW pattern:
    tf = tk.Frame(self.nb, bg=DARK)
    self.nb.add(tf, text="  📋 Traditional Solfa  ")
    result = build_trad_canvas_tab(
        tf, self.score,
        on_refresh=lambda: self.trad_canvas.set_score(self.score))
    self.trad_canvas   = result['canvas']
    self.layout_panel  = result['layout_panel']
    self.font_panel    = result['font_panel']

RULER USAGE:
  • "Add H Ruler" button → adds a draggable horizontal guide line
  • "Add V Ruler" button → adds a draggable vertical guide line
  • Drag the blue circle handle to reposition
  • Double-click handle to delete that ruler
  • "Clear Rulers" removes all rulers
  • Rulers are automatically hidden before PDF export via
    canvas.ruler.hide() / canvas.ruler.show()

FONT TAB USAGE:
  • Font family dropdown → updates canvas font_family
  • Size scale spinbox  → updates canvas font_scale
  • Lyric font dropdown → updates canvas lyric_font_family
  • "Apply" button      → calls set_render_options and redraws

LAYOUT PANEL USAGE:
  • Bars/line       → measures_per_row
  • Beat px         → beat_width (controls all measure widths)
  • Row gap         → vertical space between systems
  • Fit width       → auto-scale beat_width to fill canvas width
  • Bar #s          → show/hide bar numbers
  • ⟳ Refresh       → force redraw

────────────────────────────────────────────────────────────────
PDF EXPORT INTEGRATION (ruler hide/show)
────────────────────────────────────────────────────────────────

In ConversionEngine.export_pdf_solfa_traditional() or wherever PDF
export is triggered, bracket the export call with:

    self.trad_canvas.ruler.hide()
    try:
        ConversionEngine.export_pdf_solfa_traditional(self.score, path)
    finally:
        self.trad_canvas.ruler.show()

This ensures rulers never appear in the printed PDF.

────────────────────────────────────────────────────────────────
VERIFICATION CHECKLIST
────────────────────────────────────────────────────────────────

After integrating, verify:

  □ Bass note C3 in key C appears as d₁ (not d)
  □ Soprano C5 in key C appears as d'
  □ G major: G4 = d (no mark), G3 = d₁, G5 = d'
  □ A 4/4 half note followed by a quarter note shows:
        d' : — : m : s     (NOT d':- :-  or  d': -: m : s)
  □ An eighth note appears as  d.  (dot suffix, no colon prefix)
  □ A 4/4 measure is wider than a 2/4 measure in the same row
  □ Layout panel spinboxes immediately update the canvas
  □ Dragging a ruler handle moves the ruler; PDF shows no ruler
  □ Font dropdown changes the syllable font in the canvas
"""
