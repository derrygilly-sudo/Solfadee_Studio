"""
Tonic Solfa Canvas Renderer
============================
Renders a TonicSolfaScore onto a Tkinter Canvas widget using the
traditional tonic-solfa grid layout observed in the uploaded scores
(Monto Dwom & Wasɔr by O. A. McPRINCE).

Layout reference (from PDFs):
  ┌──────────────────────────────────────────────────────────┐
  │  TITLE          Doh is X      Time N/M    Composer        │
  ├──────────────────────────────────────────────────────────┤
  │  bar 1 │ bar 2 │ bar 3 │ bar 4 │ bar 5 │ bar 6          │
  │  [top]  [top]   [top]   [top]   [top]   [top]            │
  │  [bot]  [bot]   [bot]   [bot]   [bot]   [bot]            │
  ├──────────────────────────────────────────────────────────┤
  │  bar 7 │ bar 8 │ ...                                     │
  │  ...                                                     │
  ├──────────────────────────────────────────────────────────┤
  │  Lyrics / text underlay                                  │
  └──────────────────────────────────────────────────────────┘
"""

import tkinter as tk
from tkinter import font as tkfont
from typing import List, Optional, Tuple

from models import (
    TonicSolfaScore, VoicePart, Bar, SolfaNote, SolfaRest,
    Octave, Accidental, Dynamic, ArticulationMark, BarlineType
)


# ---------------------------------------------------------------------------
# Colour palette (matches the visual style of the printed scores)
# ---------------------------------------------------------------------------
PALETTE = {
    "bg":          "#FEFDF8",   # cream parchment background
    "staff_line":  "#2C2C2C",   # near-black rules
    "barline":     "#2C2C2C",
    "repeat_dot":  "#2C2C2C",
    "note_text":   "#1A1A1A",   # syllable text
    "lyric_text":  "#2C2C2C",   # lyric underlay
    "header_text": "#0A0A50",   # dark navy for headers
    "dynamic_text":"#8B0000",   # dark red for dynamics
    "slur_tie":    "#333333",
    "rehearsal":   "#005500",
    "first_end":   "#333333",
    "second_end":  "#333333",
    "selection":   "#C8E6FF",
}

# Column widths / row heights (pixels)
BARS_PER_ROW  = 6
BAR_W         = 130   # width of one bar column
BAR_H         = 70    # height per voice row (top+bottom together = 70)
VOICE_H       = 30    # half: top voice row
MARGIN_L      = 55    # left margin (for part names)
MARGIN_TOP    = 100   # header area height
ROW_GAP       = 18    # gap between system rows (for lyrics etc.)
LYRIC_H       = 18    # height of one lyric line
FONT_NOTE     = ("Times New Roman", 11, "bold")
FONT_LYRIC    = ("Times New Roman", 10)
FONT_HEADER   = ("Times New Roman", 13, "bold")
FONT_TITLE    = ("Times New Roman", 16, "bold")
FONT_DYNAMIC  = ("Times New Roman", 10, "italic")
FONT_SMALL    = ("Times New Roman", 9)


# ---------------------------------------------------------------------------
# Utility: octave rendering
# ---------------------------------------------------------------------------

def _octave_suffix(octave: Octave) -> str:
    if octave == Octave.LOW1:  return "₁"
    if octave == Octave.LOW2:  return "₂"
    if octave == Octave.HIGH1: return "¹"
    if octave == Octave.HIGH2: return "²"
    return ""


def _note_label(note: SolfaNote) -> str:
    """Return the displayable syllable string for a note."""
    syl = note.syllable
    if note.accidental == Accidental.SHARP:
        syl += "ⁱ"
    elif note.accidental in (Accidental.FLAT, Accidental.SE, Accidental.TA):
        syl += "ᵃ"
    elif note.accidental == Accidental.FE:
        syl = "fe"
    return syl + _octave_suffix(note.octave)


def _duration_to_marks(dur: float, dot: bool) -> str:
    """
    Return the tonic-solfa duration symbol(s).
    This matches the traditional per-beat underline pattern used in the original
    tonic canvas (and the `duration_underscores()` notation in MusNote).
    """
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


# ---------------------------------------------------------------------------
# Main Canvas Widget
# ---------------------------------------------------------------------------

class TonicSolfaCanvas(tk.Frame):
    """
    A scrollable Tkinter frame that renders a TonicSolfaScore in the
    traditional two-voice tonic-solfa grid format.
    """

    def __init__(self, master, score: TonicSolfaScore, app=None, **kwargs):
        super().__init__(master, **kwargs)
        self.score = score
        self.app = app
        self.measure_resize_factor = getattr(self.app, 'measure_resize_factor', 1.0) if self.app else 1.0
        self.beat_width = BAR_W  # Default beat width for spacing
        self.measure_width = BAR_W * BARS_PER_ROW  # Default measure width
        self._build_ui()
        self.render()

    def set_score(self, score: TonicSolfaScore):
        self.score = score
        self.render()

    def set_render_options(self, **kwargs):
        # Leverage optional resizing options similar to other canvas classes
        self.measure_resize_factor = kwargs.get('measure_resize_factor', self.measure_resize_factor)
        self.render()

    # ------------------------------------------------------------------ setup

    def _build_ui(self):
        self.configure(bg=PALETTE["bg"])

        # Scrollbars
        h_scroll = tk.Scrollbar(self, orient=tk.HORIZONTAL)
        v_scroll = tk.Scrollbar(self, orient=tk.VERTICAL)
        h_scroll.grid(row=1, column=0, sticky="ew")
        v_scroll.grid(row=0, column=1, sticky="ns")

        self.canvas = tk.Canvas(
            self, bg=PALETTE["bg"],
            xscrollcommand=h_scroll.set,
            yscrollcommand=v_scroll.set,
            highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        h_scroll.config(command=self.canvas.xview)
        v_scroll.config(command=self.canvas.yview)

        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>",   self._on_mousewheel)
        self.canvas.bind("<Button-5>",   self._on_mousewheel)

    def _on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1 * event.delta / 120), "units")

    # ------------------------------------------------------------------ render

    def render(self):
        """Clear and re-draw the entire score."""
        self.measure_resize_factor = getattr(self.app, 'measure_resize_factor', 1.0) if self.app else 1.0
        self.canvas.delete("all")
        score = self.score
        meta  = score.metadata

        total_width = MARGIN_L + BARS_PER_ROW * BAR_W + 40

        # Scaled dimensions
        bar_w = BAR_W * self.measure_resize_factor
        bar_h = BAR_H * self.measure_resize_factor
        voice_h = VOICE_H * self.measure_resize_factor
        row_gap = ROW_GAP * self.measure_resize_factor
        lyric_h = LYRIC_H * self.measure_resize_factor

        # ---- Header ---------------------------------------------------------
        cx = total_width // 2
        self.canvas.create_text(cx, 20, text=meta.title,
                                font=FONT_TITLE, fill=PALETTE["header_text"],
                                anchor="center")
        self.canvas.create_text(MARGIN_L, 42,
                                text=f"Doh is {meta.key_note}",
                                font=FONT_HEADER, fill=PALETTE["header_text"],
                                anchor="w")
        self.canvas.create_text(cx, 42,
                                text=f"Time {meta.time_numerator}/{meta.time_denominator}",
                                font=FONT_HEADER, fill=PALETTE["header_text"],
                                anchor="center")
        self.canvas.create_text(total_width - 10, 42,
                                text=meta.composer,
                                font=FONT_HEADER, fill=PALETTE["header_text"],
                                anchor="e")
        if meta.tempo_text:
            self.canvas.create_text(MARGIN_L, 62, text=meta.tempo_text,
                                    font=FONT_DYNAMIC, fill=PALETTE["dynamic_text"],
                                    anchor="w")
        if meta.dedication:
            self.canvas.create_text(cx, 62, text=meta.dedication,
                                    font=FONT_SMALL, fill=PALETTE["header_text"],
                                    anchor="center")
        if meta.date:
            self.canvas.create_text(total_width - 10, 62, text=meta.date,
                                    font=FONT_SMALL, fill=PALETTE["header_text"],
                                    anchor="e")
        if meta.location:
            self.canvas.create_text(total_width - 10, 78, text=meta.location,
                                    font=FONT_SMALL, fill=PALETTE["header_text"],
                                    anchor="e")

        # Beat pattern legend (Traditional tonic layout style)
        legend = (
            "Beat: 4.0=:-:-:-  3.0=:-:-  2.0=:-  1.5=:-.  "
            "1.0=:  0.75=.,  0.5=.  0.25=,"
        )
        self.canvas.create_text(MARGIN_L, 90, text=legend,
                                font=FONT_SMALL, fill=PALETTE["staff_line"],
                                anchor="w")

        # Horizontal rule under header
        self.canvas.create_line(MARGIN_L, MARGIN_TOP - 5,
                                total_width - 10, MARGIN_TOP - 5,
                                fill=PALETTE["staff_line"], width=1.5)

        # ---- System rows ----------------------------------------------------
        n_parts = len(score.parts)
        bar_count = score.bar_count

        # How many bars in total
        n_rows = (bar_count + BARS_PER_ROW - 1) // BARS_PER_ROW
        total_system_h = (bar_h * n_parts + row_gap + lyric_h * 2)

        y_cursor = MARGIN_TOP

        for row_idx in range(n_rows):
            bar_start = row_idx * BARS_PER_ROW
            bar_end   = min(bar_start + BARS_PER_ROW, bar_count)
            n_bars_this_row = bar_end - bar_start

            system_top = y_cursor

            # ---- Part labels (left margin) ----------------------------------
            for p_idx, part in enumerate(score.parts):
                py = system_top + p_idx * bar_h + bar_h // 2
                if row_idx == 0:
                    self.canvas.create_text(
                        MARGIN_L - 5, py,
                        text=part.name[:10],
                        font=FONT_SMALL, fill=PALETTE["header_text"],
                        anchor="e"
                    )

            # ---- Bar number row ---------------------------------------------
            for col, bar_abs_idx in enumerate(range(bar_start, bar_end)):
                bx = MARGIN_L + col * bar_w
                bar_num = bar_abs_idx + 1
                self.canvas.create_text(bx + 3, system_top - 2,
                                        text=str(bar_num),
                                        font=FONT_SMALL,
                                        fill=PALETTE["staff_line"],
                                        anchor="sw")

            # ---- Draw each part's row ---------------------------------------
            for p_idx, part in enumerate(score.parts):
                row_top = system_top + p_idx * bar_h

                # Horizontal staff lines (top & bottom of voice row)
                self.canvas.create_line(
                    MARGIN_L, row_top,
                    MARGIN_L + n_bars_this_row * bar_w, row_top,
                    fill=PALETTE["staff_line"], width=1
                )
                self.canvas.create_line(
                    MARGIN_L, row_top + bar_h,
                    MARGIN_L + n_bars_this_row * bar_w, row_top + bar_h,
                    fill=PALETTE["staff_line"], width=1
                )

                # Mid-line between top & bottom voices
                mid_y = row_top + bar_h // 2
                self.canvas.create_line(
                    MARGIN_L, mid_y,
                    MARGIN_L + n_bars_this_row * bar_w, mid_y,
                    fill=PALETTE["staff_line"], dash=(3, 4), width=1
                )

                # ---- Bars ---------------------------------------------------
                for col, bar_abs_idx in enumerate(range(bar_start, bar_end)):
                    bx = MARGIN_L + col * bar_w
                    bar = part.bars[bar_abs_idx] if bar_abs_idx < len(part.bars) else None

                    # Barlines
                    self._draw_barline(bx, row_top, bar_h,
                                       bar.barline_start if bar else BarlineType.SINGLE,
                                       left=True)
                    if col == n_bars_this_row - 1:
                        end_bl = bar.barline_end if bar else BarlineType.SINGLE
                        if bar_abs_idx == bar_count - 1:
                            end_bl = BarlineType.FINAL
                        self._draw_barline(bx + bar_w, row_top, bar_h,
                                           end_bl, left=False)

                    if bar is None:
                        continue

                    # Rehearsal / volta marks
                    if bar.rehearsal_mark:
                        self.canvas.create_text(
                            bx + 3, row_top - 12,
                            text=bar.rehearsal_mark, font=FONT_SMALL,
                            fill=PALETTE["rehearsal"], anchor="sw"
                        )
                    if bar.first_ending:
                        self._draw_volta(bx, row_top - 10, bar_w, "1.")
                    if bar.second_ending:
                        self._draw_volta(bx, row_top - 10, bar_w, "2.")

                    # Notes
                    self._draw_bar_notes(bar, bx, row_top, bar_w, bar_h, p_idx)

            # ---- Lyrics under system ----------------------------------------
            lyric_y = system_top + n_parts * bar_h + 4
            if score.lyrics:
                for v_idx, verse in enumerate(score.lyrics[:2]):  # first 2 verses
                    label = score.verse_labels[v_idx] if v_idx < len(score.verse_labels) else ""
                    if row_idx < len(verse):
                        text = verse[row_idx] if row_idx < len(verse) else ""
                    else:
                        text = ""
                    if label:
                        self.canvas.create_text(MARGIN_L, lyric_y + v_idx * lyric_h,
                                                text=f"{label}  {text}",
                                                font=FONT_LYRIC,
                                                fill=PALETTE["lyric_text"],
                                                anchor="nw")

            y_cursor = lyric_y + 2 * LYRIC_H + ROW_GAP

        # Update scroll region
        self.canvas.config(scrollregion=(0, 0, total_width, y_cursor + 20))

    # ------------------------------------------------------------------ note drawing

    def _draw_bar_notes(self, bar: Bar, bx: float, row_top: float,
                        bar_w: float, bar_h: float, part_idx: int):
        """Draw the notes for one bar in one part's row."""
        if not bar.voices:
            return

        # Two sub-rows: top voice (0) and bottom voice (1) if present
        voices = bar.voices
        n_voices = min(len(voices), 2)  # only 2 voices per part row

        for v_idx in range(n_voices):
            notes = voices[v_idx] if v_idx < len(voices) else []
            if not notes:
                continue

            sub_top = row_top + v_idx * (bar_h // 2)
            sub_h   = bar_h // 2
            cy      = sub_top + sub_h // 2

            # Distribute notes horizontally by fixed beat grid (correct bar alignment)
            n_items = len(notes)
            if n_items == 0:
                continue

            # Get time signature from score metadata
            beat_total = self.score.metadata.time_numerator * (4.0 / self.score.metadata.time_denominator)
            if beat_total <= 0: beat_total = 1.0
            start_x = bx + 6
            available_w = bar_w - 12

            # Beat separators for visual : markers
            for beat_idx in range(1, self.score.metadata.time_numerator):
                sep_x = bx + (beat_idx/beat_total) * available_w
                self.canvas.create_text(
                    sep_x, cy,
                    text=':', font=FONT_NOTE,
                    fill=PALETTE['staff_line'], anchor='n'
                )

            # Precompute note center positions on beat grid
            note_positions = []
            pos_beats = 0.0
            for item in notes:
                dur = getattr(item, 'actual_duration', getattr(item, 'duration', 1.0))
                center = start_x + (pos_beats / beat_total) * available_w + (dur / 2.0 / beat_total) * available_w
                note_positions.append((item, center, dur))
                pos_beats += dur

            prev_note_x = None
            prev_was_slur_start = False

            for i, (item, note_x, dur) in enumerate(note_positions):
                # Ensure note remains inside measure bounds
                note_x = max(bx + 4, min(bx + bar_w - 4, note_x))

                if isinstance(item, SolfaRest):
                    # Rest: draw a small dash
                    self.canvas.create_text(
                        note_x, cy, text="—",
                        font=FONT_NOTE, fill=PALETTE["staff_line"], anchor="center"
                    )
                elif isinstance(item, SolfaNote):
                    label = _note_label(item)
                    dur_marks = _duration_to_marks(item.duration, getattr(item, 'dot', getattr(item, 'dotted', False)))

                    # Draw syllable
                    self.canvas.create_text(
                        note_x, cy, text=label,
                        font=FONT_NOTE, fill=PALETTE["note_text"], anchor="center"
                    )

                    # Duration extension dashes
                    if dur_marks.strip():
                        self.canvas.create_text(
                            note_x + 12, cy, text=dur_marks.strip(),
                            font=FONT_NOTE, fill=PALETTE["staff_line"], anchor="w"
                        )

                    # Octave dots above/below (traditional solfa = dots)
                    if item.octave == Octave.HIGH1:
                        self.canvas.create_oval(
                            note_x - 1, cy - 11, note_x + 1, cy - 9,
                            fill=PALETTE["note_text"], outline=""
                        )
                    elif item.octave == Octave.LOW1:
                        self.canvas.create_oval(
                            note_x - 1, cy + 9, note_x + 1, cy + 11,
                            fill=PALETTE["note_text"], outline=""
                        )

                    # Tie / slur arc
                    if item.tied_forward and i < n_items - 1:
                        next_x = note_positions[i + 1][1]
                        self._draw_tie(note_x, cy, next_x, cy)

                    if prev_was_slur_start and prev_note_x is not None:
                        self._draw_slur(prev_note_x, cy, note_x, cy)

                    # Articulation
                    if item.articulation == ArticulationMark.STACCATO:
                        self.canvas.create_oval(note_x - 1, cy - 14,
                                                note_x + 1, cy - 12,
                                                fill=PALETTE["note_text"], outline="")
                    elif item.articulation == ArticulationMark.ACCENT:
                        self.canvas.create_text(note_x, cy - 14, text=">",
                                                font=FONT_SMALL,
                                                fill=PALETTE["note_text"])
                    elif item.articulation == ArticulationMark.TENUTO:
                        self.canvas.create_line(note_x - 4, cy - 14,
                                                note_x + 4, cy - 14,
                                                fill=PALETTE["note_text"], width=1.5)

                    # Dynamic
                    if item.dynamic:
                        self.canvas.create_text(
                            note_x, cy + sub_h - 4,
                            text=item.dynamic.value,
                            font=FONT_DYNAMIC, fill=PALETTE["dynamic_text"],
                            anchor="s"
                        )

                    # Lyric underlay
                    if item.lyric:
                        lyric = item.lyric
                        if item.lyric_hyphen:
                            lyric += "-"
                        if item.lyric_extender:
                            lyric += "__"
                        self.canvas.create_text(
                            note_x, sub_top + sub_h + 2,
                            text=lyric, font=FONT_LYRIC,
                            fill=PALETTE["lyric_text"], anchor="n"
                        )

                    prev_was_slur_start = item.slur_start
                else:
                    prev_was_slur_start = False

                prev_note_x = note_x

                if isinstance(item, SolfaRest):
                    # Rest: draw a small dash
                    self.canvas.create_text(
                        note_x, cy, text="—",
                        font=FONT_NOTE, fill=PALETTE["staff_line"], anchor="center"
                    )
                elif isinstance(item, SolfaNote):
                    label = _note_label(item)
                    dur_marks = _duration_to_marks(item.duration, getattr(item, 'dot', getattr(item, 'dotted', False)))

                    # Draw syllable
                    self.canvas.create_text(
                        note_x, cy, text=label,
                        font=FONT_NOTE, fill=PALETTE["note_text"], anchor="center"
                    )

                    # Duration extension dashes
                    if dur_marks.strip():
                        self.canvas.create_text(
                            note_x + 12, cy, text=dur_marks.strip(),
                            font=FONT_NOTE, fill=PALETTE["staff_line"], anchor="w"
                        )

                    # Octave dots above/below (traditional solfa = dots)
                    if item.octave == Octave.HIGH1:
                        self.canvas.create_oval(
                            note_x - 1, cy - 11, note_x + 1, cy - 9,
                            fill=PALETTE["note_text"], outline=""
                        )
                    elif item.octave == Octave.LOW1:
                        self.canvas.create_oval(
                            note_x - 1, cy + 9, note_x + 1, cy + 11,
                            fill=PALETTE["note_text"], outline=""
                        )

                    # Tie / slur arc
                    if item.tied_forward and i < n_items - 1:
                        next_x = x_cursor + cell_w + (available_w / n_items) / 2
                        self._draw_tie(note_x, cy, next_x, cy)

                    if prev_was_slur_start and prev_note_x is not None:
                        self._draw_slur(prev_note_x, cy, note_x, cy)

                    # Articulation
                    if item.articulation == ArticulationMark.STACCATO:
                        self.canvas.create_oval(note_x - 1, cy - 14,
                                                note_x + 1, cy - 12,
                                                fill=PALETTE["note_text"], outline="")
                    elif item.articulation == ArticulationMark.ACCENT:
                        self.canvas.create_text(note_x, cy - 14, text=">",
                                                font=FONT_SMALL,
                                                fill=PALETTE["note_text"])
                    elif item.articulation == ArticulationMark.TENUTO:
                        self.canvas.create_line(note_x - 4, cy - 14,
                                                note_x + 4, cy - 14,
                                                fill=PALETTE["note_text"], width=1.5)

                    # Dynamic
                    if item.dynamic:
                        self.canvas.create_text(
                            note_x, cy + sub_h - 4,
                            text=item.dynamic.value,
                            font=FONT_DYNAMIC, fill=PALETTE["dynamic_text"],
                            anchor="s"
                        )

                    # Lyric underlay
                    if item.lyric:
                        lyric = item.lyric
                        if item.lyric_hyphen:
                            lyric += "-"
                        if item.lyric_extender:
                            lyric += "__"
                        self.canvas.create_text(
                            note_x, sub_top + sub_h + 2,
                            text=lyric, font=FONT_LYRIC,
                            fill=PALETTE["lyric_text"], anchor="n"
                        )

                    prev_was_slur_start = item.slur_start
                else:
                    prev_was_slur_start = False

                prev_note_x = note_x
                x_cursor += cell_w

    # ------------------------------------------------------------------ decorations

    def _draw_barline(self, x: float, y: float, h: float,
                      bl_type: BarlineType, left: bool = True):
        """Draw a barline at horizontal position x."""
        c = self.canvas
        col = PALETTE["barline"]

        if bl_type == BarlineType.SINGLE:
            c.create_line(x, y, x, y + h, fill=col, width=1)

        elif bl_type == BarlineType.DOUBLE:
            c.create_line(x - 2, y, x - 2, y + h, fill=col, width=1)
            c.create_line(x,     y, x,     y + h, fill=col, width=1)

        elif bl_type == BarlineType.FINAL:
            c.create_line(x - 3, y, x - 3, y + h, fill=col, width=1)
            c.create_line(x,     y, x,     y + h, fill=col, width=3)

        elif bl_type == BarlineType.REPEAT_CLOSE:
            c.create_line(x - 3, y, x - 3, y + h, fill=col, width=1)
            c.create_line(x,     y, x,     y + h, fill=col, width=3)
            # Dots
            for dy in [h * 0.35, h * 0.65]:
                c.create_oval(x - 10, y + dy - 2, x - 6, y + dy + 2,
                              fill=col, outline="")

        elif bl_type == BarlineType.REPEAT_OPEN:
            c.create_line(x, y, x, y + h, fill=col, width=3)
            c.create_line(x + 3, y, x + 3, y + h, fill=col, width=1)
            for dy in [h * 0.35, h * 0.65]:
                c.create_oval(x + 6, y + dy - 2, x + 10, y + dy + 2,
                              fill=col, outline="")

        else:
            c.create_line(x, y, x, y + h, fill=col, width=1)

    def _draw_volta(self, bx: float, y: float, w: float, label: str):
        """Draw a first/second ending bracket."""
        c = self.canvas
        c.create_line(bx, y, bx + w, y, fill=PALETTE["first_end"], width=1)
        c.create_line(bx, y, bx, y + 8, fill=PALETTE["first_end"], width=1)
        c.create_text(bx + 4, y + 2, text=label, font=FONT_SMALL,
                      fill=PALETTE["first_end"], anchor="nw")

    def _draw_tie(self, x1: float, y: float, x2: float, _y2: float):
        """Draw a tie arc between two notes."""
        mid_x = (x1 + x2) / 2
        self.canvas.create_line(
            x1, y - 8, mid_x, y - 14, x2, y - 8,
            smooth=True, fill=PALETTE["slur_tie"], width=1.2
        )

    def _draw_slur(self, x1: float, y: float, x2: float, _y2: float):
        """Draw a slur arc under the notes."""
        mid_x = (x1 + x2) / 2
        self.canvas.create_line(
            x1, y + 8, mid_x, y + 14, x2, y + 8,
            smooth=True, fill=PALETTE["slur_tie"], width=1.2, dash=(4, 2)
        )

    def reload(self, score: TonicSolfaScore):
        """Replace the score and redraw."""
        self.score = score
        self.render()
