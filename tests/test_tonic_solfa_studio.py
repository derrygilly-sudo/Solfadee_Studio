import os
import tempfile
import unittest
from unittest.mock import patch
import tkinter as tk

from tonic_solfa_studio_v5 import (
    Score, Measure, MusNote,
    ConversionEngine, TraditionalSolfaCanvas, StaffCanvas
)
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
        self.assertEqual(n_low.solfa(), 'd1')

        n_high = MusNote('C', 5, duration=1.0)
        self.assertEqual(n_high.solfa(), "d'")

        n_g_key = MusNote('G', 5, duration=1.0)
        self.assertEqual(n_g_key.solfa(key='G'), "d'")

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


if __name__ == '__main__':
    unittest.main()
