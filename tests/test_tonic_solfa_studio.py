import os
import tempfile
import unittest
from unittest.mock import patch
import tkinter as tk

from tonic_solfa_studio_v5 import (
    Score, Measure, MusNote,
    ConversionEngine, TraditionalSolfaCanvas, StaffCanvas,
    build_measure_string
)
from solfa_canvas_pro import SolfaScore, render_pdf
from canvas_renderer import _duration_to_marks
from audio_engine import AudioConfig, AudioSynthesizer, WavFileWriter
from lyrics_manager import LyricsManager, LyricSection, LyricSyllable
from speedy_entry_tool import SpeedyEntryTool


class TestTonicSolfaStudio(unittest.TestCase):
    def test_score_basics(self):
        score = Score(title="Test", composer="Tester")
        m = Measure()
        m.notes.append(MusNote('C', 4, duration=1.0))
        m.notes.append(MusNote('D', 4, duration=1.0))
        m.notes.append(MusNote('E', 4, duration=0.5))
        score.measures = [m]

        self.assertEqual(score.title, 'Test')
        self.assertEqual(score.composer, 'Tester')
        self.assertEqual(len(score.measures), 1)

    def test_musnote_primitives(self):
        n = MusNote('C', 4, duration=1.0)
        self.assertEqual(n.solfa(), 'd')
        self.assertEqual(n.midi_num, 60)  # Middle C

    def test_conversion_engine_parse_xml_text(self):
        xml_text = '''<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <work><work-title>Test</work-title></work>
  <identification><creator type="composer">Tester</creator></identification>
  <part-list><score-part id="P1"><part-name>Music</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
    </measure>
  </part>
</score-partwise>'''
        score = ConversionEngine._parse_xml_text(xml_text)
        self.assertEqual(score.title, 'Test')
        self.assertEqual(score.composer, 'Tester')
        self.assertEqual(len(score.measures), 1)
        self.assertEqual(score.measures[0].notes[0].pitch, 'C')

    def test_musnote_solfa(self):
        n = MusNote('C', 4, duration=1.0)
        self.assertEqual(n.solfa(), 'd')
        self.assertEqual(n.solfa(key='G'), 'f')

        n_low = MusNote('C', 3, duration=1.0)
        self.assertEqual(n_low.solfa(), 'd,')

        n_lower = MusNote('C', 2, duration=1.0)
        self.assertEqual(n_lower.solfa(), 'd,,')

        n_high = MusNote('C', 5, duration=1.0)
        self.assertEqual(n_high.solfa(), "d'")

        n_higher = MusNote('C', 6, duration=1.0)
        self.assertEqual(n_higher.solfa(), "d''")

        n_g_key = MusNote('G', 5, duration=1.0)
        self.assertEqual(n_g_key.solfa(key='G'), "d'")

    def test_duration_to_marks_beat_pattern(self):
        self.assertEqual(_duration_to_marks(4.0, False), ':-:-:-')
        self.assertEqual(_duration_to_marks(3.0, False), ':-:-')
        self.assertEqual(_duration_to_marks(2.0, False), ':-')
        self.assertEqual(_duration_to_marks(1.5, False), ':-.')
        self.assertEqual(_duration_to_marks(1.0, False), ':')
        self.assertEqual(_duration_to_marks(0.75, False), '.,')
        self.assertEqual(_duration_to_marks(0.5, False), '.')
        self.assertEqual(_duration_to_marks(0.25, False), ',')
        self.assertEqual(_duration_to_marks(1.0, True), ':-.')  # dotted

    def test_build_measure_string_longform(self):
        notes = [MusNote('C', 4, duration=1.0), MusNote('D', 4, duration=1.0)]
        self.assertEqual(build_measure_string(notes, 'C', 2, 4), 'd :r')

        notes2 = [MusNote('E', 4, duration=1.0, dotted=True), MusNote('E', 4, duration=0.5)]
        self.assertEqual(build_measure_string(notes2, 'C', 2, 4), 'm :- .m')

        notes3 = [MusNote('G', 4, duration=2.0), MusNote('A', 4, duration=2.0)]
        self.assertEqual(build_measure_string(notes3, 'C', 4, 4), "s :- | l :-")

    def test_build_measure_string_tie_carry(self):
        notes = [MusNote('C', 4, duration=1.0, tied=True), MusNote('D', 4, duration=1.0)]
        # carry_hold should be accepted and preserve note allocation when first note starts at measure beginning
        self.assertEqual(build_measure_string(notes, 'C', 2, 4, carry_hold=True), 'd :r')

    def test_audio_engine_output(self):
        config = AudioConfig(sample_rate=22050, instrument=AudioConfig().instrument, tempo_bpm=120)
        synth = AudioSynthesizer(config)

        samples = synth.generate_note(60, 0.1)
        self.assertTrue(len(samples) > 0)
        self.assertTrue(all(-1.0 <= v <= 1.0 for v in samples))

        wav_bytes = WavFileWriter.write_wav_bytes(samples, config)
        self.assertTrue(wav_bytes.startswith(b'RIFF'))
        self.assertIn(b'WAVE', wav_bytes)

    def test_lyrics_manager(self):
        lm = LyricsManager()
        lm.add_verse(LyricSection.VERSE, 1, ['Hello', 'World'])
        self.assertEqual(lm.get_verse(LyricSection.VERSE, 1).lines, ['Hello', 'World'])
        lm.add_syllable(LyricSyllable(text='Hello', section=LyricSection.VERSE, verse_num=1, note_num=1))
        self.assertEqual(len(lm.syllables), 1)

    def test_speedy_entry_toggle(self):
        speedy = SpeedyEntryTool()
        self.assertFalse(speedy.enabled)
        self.assertTrue(speedy.toggle_enabled())
        self.assertTrue(speedy.enabled)
        self.assertTrue(speedy.handle_key('c'))
        self.assertTrue(speedy.handle_key('4'))

    def test_traditional_solfa_canvas_draw_empty_score(self):
        root = tk.Tk(); root.withdraw()
        try:
            score = Score(title='Empty', composer='N/A')
            canvas = TraditionalSolfaCanvas(root, score, width=800, height=600)
            canvas.pack()
            canvas.update_idletasks()
            canvas.redraw()
            self.assertTrue(canvas.find_all(), 'Canvas should have text/polylines for empty score')
        finally:
            root.destroy()

    def test_traditional_solfa_canvas_draw_sample_score(self):
        root = tk.Tk(); root.withdraw()
        try:
            score = Score(title='Sample', composer='Tester')
            m = Measure()
            m.notes.append(MusNote('C', 4, duration=1.0, voice=1, lyric='Do'))
            m.notes.append(MusNote('E', 4, duration=1.0, voice=2, lyric='Mi'))
            score.measures = [m]
            canvas = TraditionalSolfaCanvas(root, score, width=1000, height=600)
            canvas.pack()
            canvas.update_idletasks()
            canvas.redraw()
            self.assertTrue(canvas.find_all(), 'Canvas should draw stuff for a sample score')
        finally:
            root.destroy()

    def test_staff_canvas_measure_key_time_reset(self):
        root = tk.Tk(); root.withdraw()
        try:
            score = Score(key_sig='C', time_num=4, time_den=4)
            m = Measure(key_sig='G', time_num=3, time_den=8)
            score.measures = [m]
            canvas = StaffCanvas(root, score, width=800, height=600)
            canvas.pack(); canvas.update_idletasks()
            canvas._reset_measure_key_time(m)
            self.assertEqual(m.key_sig, 'C')
            self.assertEqual(m.time_num, 4)
            self.assertEqual(m.time_den, 4)
        finally:
            root.destroy()

    @patch('tonic_solfa_studio_v5.simpledialog.askstring')
    def test_staff_canvas_measure_key_time_edit(self, mock_askstring):
        mock_askstring.side_effect = ['F', '5/4']
        root = tk.Tk(); root.withdraw()
        try:
            score = Score(key_sig='C', time_num=4, time_den=4)
            m = Measure(key_sig='G', time_num=3, time_den=8)
            score.measures = [m]
            canvas = StaffCanvas(root, score, width=800, height=600)
            canvas.pack(); canvas.update_idletasks()
            canvas._edit_measure_key_time(m)
            self.assertEqual(m.key_sig, 'F')
            self.assertEqual(m.time_num, 5)
            self.assertEqual(m.time_den, 4)
        finally:
            root.destroy()

    def test_measure_resize_affects_traditional_and_solfa_canvases(self):
        """Integration test: Verify measure resize from panel affects both Traditional and Solfa canvases."""
        from tonic_solfa_studio_v5 import TonicSolfaStudio
        app = TonicSolfaStudio()
        app.withdraw()
        
        try:
            # Record initial beat widths
            initial_trad_beat_w = app.trad_canvas.beat_width
            initial_solfa_beat_w = app.new_solfa_canvas.beat_width
            self.assertGreater(initial_trad_beat_w, 0)
            self.assertGreater(initial_solfa_beat_w, 0)
            
            # Set different measure resize values via props panel
            app.props_panel.measure_w_var.set(250)
            app.props_panel.beat_w_var.set(50)
            app.props_panel.auto_fit_measure_var.set(False)
            
            # Apply measure resize from panel
            app._apply_measure_resize_from_panel()
            
            # Verify traditional canvas updated to 50
            self.assertEqual(app.trad_canvas.beat_width, 50)
            self.assertEqual(app.trad_canvas.measure_width, 250)
            
            # Verify solfa canvas also updated to 50 (both react to panel)
            self.assertEqual(app.new_solfa_canvas.beat_width, 50)
            self.assertEqual(app.new_solfa_canvas.measure_width, 250)
            
            # Change again to verify both update
            app.props_panel.beat_w_var.set(60)
            app.props_panel.measure_w_var.set(300)
            app._apply_measure_resize_from_panel()
            
            self.assertEqual(app.trad_canvas.beat_width, 60)
            self.assertEqual(app.trad_canvas.measure_width, 300)
            self.assertEqual(app.new_solfa_canvas.beat_width, 60)
            self.assertEqual(app.new_solfa_canvas.measure_width, 300)
            
        finally:
            app.destroy()

    def test_solfa_pro_style_changes_are_reflected_in_output(self):
        from tonic_solfa_studio_v5 import TonicSolfaStudio
        app = TonicSolfaStudio()
        app.withdraw()

        try:
            measure = Measure(number=1)
            measure.notes.append(MusNote('C', 4, duration=1.0, voice=1))
            measure.notes.append(MusNote(rest=True, duration=1.0, voice=1))
            app.score.measures = [measure]

            app.solfa_style_var.set('Curwen')
            curwen = app._build_solfa_score_from_main()
            self.assertEqual(curwen.measures[0].notes[0].beat_marker, '-')
            self.assertEqual(curwen.measures[0].notes[1].syllable, '0')

            app.solfa_style_var.set('Continental')
            continental = app._build_solfa_score_from_main()
            self.assertEqual(continental.measures[0].notes[0].beat_marker, '·')
            self.assertEqual(continental.measures[0].notes[1].syllable, 'r')
        finally:
            app.destroy()

    def test_solfa_pro_pdf_export_uses_live_settings(self):
        score = SolfaScore(title='PDF Style Check', solfa_style='Continental')
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'style_check.pdf')
            render_pdf(score, path, measures_per_row=3, font_size=12.0, row_height=120)
            self.assertTrue(os.path.exists(path))
            self.assertGreater(os.path.getsize(path), 0)


if __name__ == '__main__':
    unittest.main()
