"""
PDF Exporter for Tonic Solfa Scores
=====================================
Converts a TonicSolfaScore into a professionally formatted PDF using
ReportLab, matching the visual style of the uploaded reference scores
(Monto Dwom & Wasɔr by O. A. McPRINCE).

Layout mirrors the Tkinter canvas exactly:
  • Header: title / Doh / Time / Composer / tempo / dedication / date
  • System rows of 6 bars, with bar numbers
  • Two-voice grid per part (top + bottom voice separated by dashed line)
  • Barlines, repeat signs, volta brackets, ties, slurs
  • Lyric underlay beneath each system
  • Multi-page support with automatic page breaks
"""

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

from models import (
    TonicSolfaScore, VoicePart, Bar, SolfaNote, SolfaRest,
    Octave, Accidental, Dynamic, ArticulationMark, BarlineType
)


# ---------------------------------------------------------------------------
# Colours (matching the canvas palette)
# ---------------------------------------------------------------------------
C_HEADER   = HexColor("#0A0A50")
C_STAFF    = HexColor("#2C2C2C")
C_NOTE     = HexColor("#1A1A1A")
C_LYRIC    = HexColor("#2C2C2C")
C_DYNAMIC  = HexColor("#8B0000")
C_BARLINE  = HexColor("#2C2C2C")
C_REPEAT   = HexColor("#2C2C2C")
C_REHEARSAL= HexColor("#005500")
C_VOLTA    = HexColor("#333333")
C_SLUR     = HexColor("#333333")


# ---------------------------------------------------------------------------
# Layout constants  (all in points;  1 mm ≈ 2.835 pt)
# ---------------------------------------------------------------------------
PAGE_W, PAGE_H  = landscape(A4)           # 841 x 595 pt
MARGIN_L        = 55.0
MARGIN_R        = 30.0
MARGIN_TOP      = 50.0
MARGIN_BOT      = 40.0
BARS_PER_ROW    = 6
BAR_W           = (PAGE_W - MARGIN_L - MARGIN_R) / BARS_PER_ROW  # ≈117 pt
BAR_H           = 52.0     # height per part row (both voices together)
VOICE_H         = BAR_H / 2
SYSTEM_GAP      = 28.0     # gap between consecutive system rows
LYRIC_H         = 11.0     # height per lyric line
HEADER_H        = 72.0     # total header block height

# Font sizes
FS_TITLE   = 16
FS_HEADER  = 11
FS_NOTE    = 10
FS_LYRIC   = 8.5
FS_DYNAMIC = 8
FS_SMALL   = 7.5
FS_BARNUM  = 7


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _octave_mark(octave: Octave) -> str:
    return {
        Octave.LOW2:  "2",
        Octave.LOW1:  "1",
        Octave.MID:   "",
        Octave.HIGH1: "1",
        Octave.HIGH2: "2",
    }.get(octave, "")


def _note_label(note: SolfaNote) -> str:
    syl = note.syllable
    if note.accidental == Accidental.SE:
        syl = "se"
    elif note.accidental == Accidental.FE:
        syl = "fe"
    elif note.accidental == Accidental.TA:
        syl = "ta"
    elif note.accidental == Accidental.SHARP:
        syl += "i"
    elif note.accidental == Accidental.FLAT:
        syl += "a"
    return syl


def _actual_dur(item) -> float:
    if hasattr(item, 'actual_duration'):
        return item.actual_duration
    return getattr(item, 'duration', 1.0)


# ---------------------------------------------------------------------------
# PDF Exporter class
# ---------------------------------------------------------------------------

class TonicSolfaPDFExporter:
    """
    Renders a TonicSolfaScore to a PDF file.

    Usage
    -----
    exporter = TonicSolfaPDFExporter(score)
    exporter.export("output.pdf")
    """

    def __init__(self, score: TonicSolfaScore,
                 orientation: str = "landscape",
                 bars_per_row: int = BARS_PER_ROW):
        self.score       = score
        self.bpr         = bars_per_row
        if orientation == "portrait":
            self.page_w, self.page_h = A4
        else:
            self.page_w, self.page_h = landscape(A4)
        self.bar_w = (self.page_w - MARGIN_L - MARGIN_R) / self.bpr
        self.c = None      # ReportLab canvas, set in export()

    # ------------------------------------------------------------------ public

    def export(self, filepath: str):
        """Generate the PDF at the given file path."""
        self.c = rl_canvas.Canvas(filepath,
                                   pagesize=(self.page_w, self.page_h))
        self.c.setTitle(self.score.metadata.title)
        self.c.setAuthor(self.score.metadata.composer)

        self._render_all_pages()
        self.c.save()
        print(f"[PDF] Saved → {filepath}")

    # ------------------------------------------------------------------ pages

    def _render_all_pages(self):
        score     = self.score
        meta      = score.metadata
        bar_count = score.bar_count
        n_parts   = len(score.parts)
        n_rows    = (bar_count + self.bpr - 1) // self.bpr

        # Calculate row height
        n_lyric_lines = min(len(score.lyrics), 2)
        row_h = (BAR_H * n_parts          # note rows
                 + n_lyric_lines * LYRIC_H  # lyrics
                 + SYSTEM_GAP)             # gap

        usable_h   = self.page_h - MARGIN_TOP - MARGIN_BOT
        rows_page1 = max(1, int((usable_h - HEADER_H) / row_h))
        rows_other = max(1, int(usable_h / row_h))

        page_num = 1
        row_idx  = 0

        while row_idx < n_rows:
            is_first = (page_num == 1)
            cap = rows_page1 if is_first else rows_other

            if is_first:
                self._draw_header(meta)
                y_cursor = self.page_h - MARGIN_TOP - HEADER_H
            else:
                y_cursor = self.page_h - MARGIN_TOP

            rows_this_page = min(cap, n_rows - row_idx)

            for _ in range(rows_this_page):
                if row_idx >= n_rows:
                    break
                y_cursor = self._draw_system_row(row_idx, y_cursor, n_parts)
                row_idx += 1

            # Page number footer
            self.c.setFont("Helvetica", 8)
            self.c.setFillColor(C_STAFF)
            self.c.drawCentredString(self.page_w / 2, 18,
                                     f"— {page_num} —")

            if row_idx < n_rows:
                self.c.showPage()
                page_num += 1

    # ------------------------------------------------------------------ header

    def _draw_header(self, meta):
        c       = self.c
        pw      = self.page_w
        cy_base = self.page_h - MARGIN_TOP

        # Title
        c.setFont("Helvetica-Bold", FS_TITLE)
        c.setFillColor(C_HEADER)
        c.drawCentredString(pw / 2, cy_base - 14, meta.title)

        # Doh / Time / Composer row
        c.setFont("Helvetica-Bold", FS_HEADER)
        c.drawString(MARGIN_L, cy_base - 30, f"Doh is {meta.key_note}")
        c.drawCentredString(pw / 2, cy_base - 30,
                             f"Time  {meta.time_numerator}/{meta.time_denominator}")
        c.drawRightString(pw - MARGIN_R, cy_base - 30, meta.composer)

        # Tempo / dedication row
        c.setFont("Helvetica-Oblique", FS_DYNAMIC)
        c.setFillColor(C_DYNAMIC)
        if meta.tempo_text:
            c.drawString(MARGIN_L, cy_base - 44, meta.tempo_text)
        c.setFillColor(C_HEADER)
        if meta.dedication:
            c.drawCentredString(pw / 2, cy_base - 44, meta.dedication)
        if meta.date or meta.location:
            c.setFont("Helvetica", FS_SMALL)
            info = "  |  ".join(filter(None, [meta.date, meta.location]))
            c.drawRightString(pw - MARGIN_R, cy_base - 44, info)

        # Horizontal rule
        c.setStrokeColor(C_STAFF)
        c.setLineWidth(1.0)
        c.line(MARGIN_L, cy_base - HEADER_H + 4,
               pw - MARGIN_R, cy_base - HEADER_H + 4)

    # ------------------------------------------------------------------ system row

    def _draw_system_row(self, row_idx: int, y_top: float, n_parts: int) -> float:
        """
        Draw one full system row (all parts, 6 bars) starting at y_top.
        Returns the y coordinate after this system (including lyrics).
        """
        score     = self.score
        bar_start = row_idx * self.bpr
        bar_end   = min(bar_start + self.bpr, score.bar_count)
        n_bars    = bar_end - bar_start

        total_row_w = n_bars * self.bar_w

        # ---- Part rows ------------------------------------------------------
        for p_idx, part in enumerate(score.parts):
            row_y = y_top - p_idx * BAR_H   # top-left y of this part row

            # Staff lines
            self._hline(MARGIN_L, row_y, total_row_w)            # top
            self._hline(MARGIN_L, row_y - BAR_H, total_row_w)    # bottom
            # Dashed midline
            self._hline(MARGIN_L, row_y - VOICE_H, total_row_w, dash=(2, 3))

            # Part label (first row only)
            if row_idx == 0:
                self.c.setFont("Helvetica", FS_SMALL)
                self.c.setFillColor(C_HEADER)
                self.c.drawRightString(MARGIN_L - 3,
                                       row_y - VOICE_H - FS_SMALL / 2,
                                       part.name[:12])

            # ---- Bars in this row ------------------------------------------
            for col, bar_abs in enumerate(range(bar_start, bar_end)):
                bx  = MARGIN_L + col * self.bar_w
                bar = part.bars[bar_abs] if bar_abs < len(part.bars) else None

                # Bar number
                if p_idx == 0:
                    self.c.setFont("Helvetica", FS_BARNUM)
                    self.c.setFillColor(C_STAFF)
                    self.c.drawString(bx + 1, row_y + 3, str(bar_abs + 1))

                # Barlines
                is_last_col = (col == n_bars - 1)
                is_last_bar = (bar_abs == score.bar_count - 1)
                self._draw_barline_pdf(bx, row_y, BAR_H,
                                       bar.barline_start if bar else BarlineType.SINGLE,
                                       left=True)
                if is_last_col:
                    end_bl = BarlineType.FINAL if is_last_bar else (
                        bar.barline_end if bar else BarlineType.SINGLE
                    )
                    self._draw_barline_pdf(bx + self.bar_w, row_y, BAR_H,
                                           end_bl, left=False)

                if bar is None:
                    continue

                # Volta brackets
                if bar.first_ending:
                    self._draw_volta_pdf(bx, row_y + 2, self.bar_w, "1.")
                if bar.second_ending:
                    self._draw_volta_pdf(bx, row_y + 2, self.bar_w, "2.")
                if bar.rehearsal_mark:
                    self.c.setFont("Helvetica-Bold", FS_SMALL)
                    self.c.setFillColor(C_REHEARSAL)
                    self.c.drawString(bx + 2, row_y + 8, bar.rehearsal_mark)

                # Notes
                self._draw_bar_notes_pdf(bar, bx, row_y, p_idx)

        # ---- Lyrics ---------------------------------------------------------
        lyric_y = y_top - n_parts * BAR_H - 3
        if score.lyrics:
            for v_idx, verse in enumerate(score.lyrics[:2]):
                label = (score.verse_labels[v_idx]
                         if v_idx < len(score.verse_labels) else "")
                if row_idx < len(verse):
                    text = verse[row_idx]
                else:
                    text = ""
                if text or label:
                    self.c.setFont("Helvetica" if v_idx else "Helvetica-Oblique",
                                   FS_LYRIC)
                    self.c.setFillColor(C_LYRIC)
                    full = f"{label}  {text}" if label else text
                    self.c.drawString(MARGIN_L, lyric_y - v_idx * LYRIC_H, full)

        return lyric_y - len(score.lyrics[:2]) * LYRIC_H - SYSTEM_GAP

    # ------------------------------------------------------------------ notes (PDF)

    def _draw_bar_notes_pdf(self, bar: Bar, bx: float, row_y: float, p_idx: int):
        """Render notes for one bar of one part."""
        if not bar.voices:
            return

        for v_idx, voice_notes in enumerate(bar.voices[:2]):
            if not voice_notes:
                continue

            sub_y = row_y - v_idx * VOICE_H       # top of this sub-row
            cy    = sub_y - VOICE_H / 2            # vertical centre

            total_dur = sum(_actual_dur(n) for n in voice_notes)
            if total_dur == 0:
                continue

            available_w = self.bar_w - 8
            x_cursor    = bx + 4
            prev_x      = None
            prev_slur   = False

            for i, item in enumerate(voice_notes):
                dur    = _actual_dur(item)
                cell_w = (dur / total_dur) * available_w
                note_x = x_cursor + cell_w / 2

                if isinstance(item, SolfaRest):
                    self.c.setFont("Helvetica", FS_NOTE)
                    self.c.setFillColor(C_STAFF)
                    self.c.drawCentredString(note_x, cy - 3, "—")

                elif isinstance(item, SolfaNote):
                    label = _note_label(item)

                    # Main syllable
                    self.c.setFont("Helvetica-Bold", FS_NOTE)
                    self.c.setFillColor(C_NOTE)
                    self.c.drawCentredString(note_x, cy - 4, label)

                    # Octave dots above/below
                    if item.octave == Octave.HIGH1:
                        self._dot(note_x, cy + 4)
                    elif item.octave == Octave.HIGH2:
                        self._dot(note_x - 2, cy + 4)
                        self._dot(note_x + 2, cy + 4)
                    elif item.octave == Octave.LOW1:
                        self._dot(note_x, cy - 14)
                    elif item.octave == Octave.LOW2:
                        self._dot(note_x - 2, cy - 14)
                        self._dot(note_x + 2, cy - 14)

                    # Duration extension dashes (each extra beat = one dash)
                    n_dashes = int(item.duration) - 1
                    for k in range(n_dashes):
                        dx = note_x + cell_w * (k + 1) / max(n_dashes + 1, 1)
                        self.c.setFont("Helvetica", FS_NOTE)
                        self.c.setFillColor(C_STAFF)
                        self.c.drawCentredString(dx, cy - 4, "—")

                    # Dot (dotted note)
                    if item.dot or item.double_dot:
                        self._dot(note_x + 8, cy - 2)
                    if item.double_dot:
                        self._dot(note_x + 12, cy - 2)

                    # Tie arc
                    if item.tied_forward and i < len(voice_notes) - 1:
                        next_dur = _actual_dur(voice_notes[i + 1])
                        next_x   = note_x + cell_w + (next_dur / total_dur) * available_w / 2
                        self._draw_tie_pdf(note_x, cy, next_x, cy, above=True)

                    # Slur
                    if prev_slur and prev_x is not None:
                        self._draw_slur_pdf(prev_x, cy, note_x, cy)

                    # Articulation
                    art = item.articulation
                    if art == ArticulationMark.STACCATO:
                        self._dot(note_x, cy + 6)
                    elif art == ArticulationMark.ACCENT:
                        self.c.setFont("Helvetica-Bold", FS_SMALL)
                        self.c.setFillColor(C_NOTE)
                        self.c.drawCentredString(note_x, cy + 6, ">")
                    elif art == ArticulationMark.TENUTO:
                        self.c.setStrokeColor(C_NOTE)
                        self.c.setLineWidth(1.2)
                        self.c.line(note_x - 3, cy + 7, note_x + 3, cy + 7)

                    # Dynamic
                    if item.dynamic:
                        self.c.setFont("Helvetica-Oblique", FS_DYNAMIC)
                        self.c.setFillColor(C_DYNAMIC)
                        self.c.drawCentredString(note_x, sub_y - VOICE_H + 1,
                                                  item.dynamic.value)

                    # Lyric underlay
                    if item.lyric:
                        lyric = item.lyric + ("-" if item.lyric_hyphen else "")
                        self.c.setFont("Helvetica", FS_LYRIC)
                        self.c.setFillColor(C_LYRIC)
                        self.c.drawCentredString(note_x,
                                                  sub_y - VOICE_H - LYRIC_H + 1,
                                                  lyric)

                    prev_slur = item.slur_start
                else:
                    prev_slur = False

                prev_x    = note_x
                x_cursor += cell_w

    # ------------------------------------------------------------------ helpers

    def _hline(self, x: float, y: float, w: float, dash=()):
        c = self.c
        c.setStrokeColor(C_STAFF)
        c.setLineWidth(0.6 if dash else 0.8)
        if dash:
            c.setDash(*dash)
        c.line(x, y, x + w, y)
        c.setDash()   # reset

    def _dot(self, x: float, y: float, r: float = 1.2):
        self.c.setFillColor(C_NOTE)
        self.c.circle(x, y, r, fill=1, stroke=0)

    def _draw_barline_pdf(self, x: float, y: float, h: float,
                          bl: BarlineType, left: bool):
        c   = self.c
        bot = y - h
        c.setStrokeColor(C_BARLINE)

        if bl == BarlineType.SINGLE:
            c.setLineWidth(0.7)
            c.line(x, y, x, bot)

        elif bl == BarlineType.DOUBLE:
            c.setLineWidth(0.7)
            c.line(x - 2, y, x - 2, bot)
            c.line(x,     y, x,     bot)

        elif bl == BarlineType.FINAL:
            c.setLineWidth(0.7)
            c.line(x - 3, y, x - 3, bot)
            c.setLineWidth(2.5)
            c.line(x,     y, x,     bot)

        elif bl == BarlineType.REPEAT_CLOSE:
            c.setLineWidth(0.7)
            c.line(x - 3, y, x - 3, bot)
            c.setLineWidth(2.5)
            c.line(x, y, x, bot)
            c.setFillColor(C_REPEAT)
            for dy in [h * 0.35, h * 0.65]:
                c.circle(x - 7, y - dy, 1.8, fill=1, stroke=0)

        elif bl == BarlineType.REPEAT_OPEN:
            c.setLineWidth(2.5)
            c.line(x, y, x, bot)
            c.setLineWidth(0.7)
            c.line(x + 3, y, x + 3, bot)
            c.setFillColor(C_REPEAT)
            for dy in [h * 0.35, h * 0.65]:
                c.circle(x + 7, y - dy, 1.8, fill=1, stroke=0)

        else:
            c.setLineWidth(0.7)
            c.line(x, y, x, bot)

    def _draw_volta_pdf(self, bx: float, y: float, w: float, label: str):
        c = self.c
        c.setStrokeColor(C_VOLTA)
        c.setLineWidth(0.7)
        c.line(bx, y, bx + w, y)
        c.line(bx, y, bx, y - 6)
        c.setFont("Helvetica", FS_SMALL)
        c.setFillColor(C_VOLTA)
        c.drawString(bx + 2, y - 8, label)

    def _draw_tie_pdf(self, x1: float, y: float, x2: float, _y2: float,
                      above: bool = True):
        """Draw a slur/tie arc between two note positions."""
        c      = self.c
        mid_x  = (x1 + x2) / 2
        bulge  = 8 if above else -8
        c.setStrokeColor(C_SLUR)
        c.setLineWidth(0.8)
        p = c.beginPath()
        p.moveTo(x1, y)
        p.curveTo(x1, y + bulge, x2, y + bulge, x2, y)
        c.drawPath(p, stroke=1, fill=0)

    def _draw_slur_pdf(self, x1: float, y: float, x2: float, _y2: float):
        """Draw a slur arc (below the notes)."""
        c      = self.c
        mid_x  = (x1 + x2) / 2
        c.setStrokeColor(C_SLUR)
        c.setLineWidth(0.8)
        c.setDash(4, 2)
        p = c.beginPath()
        p.moveTo(x1, y)
        p.curveTo(x1, y - 8, x2, y - 8, x2, y)
        c.drawPath(p, stroke=1, fill=0)
        c.setDash()
