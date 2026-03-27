#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, '.')
from tonic_solfa_studio_v5 import Score, MusNote, ConversionEngine

out_dir = os.path.join(os.path.dirname(__file__), 'examples')
os.makedirs(out_dir, exist_ok=True)
path = os.path.join(out_dir, 'sample_export.pdf')

score = Score()
score.title = "Sample Export"
score.composer = "Export Bot"
score.key_sig = "C"
score.time_num = 4
score.time_den = 4
score.tempo_bpm = 100
score.ensure_measures(1)

m1 = score.measures[0]
m1.notes = [
    MusNote(pitch='C', octave=4, duration=1.0, voice=1, lyric='la'),
    MusNote(pitch='D', octave=4, duration=1.0, voice=1, lyric='sol'),
    MusNote(pitch='E', octave=4, duration=1.0, voice=1, lyric='fa'),
    MusNote(pitch='F', octave=4, duration=1.0, voice=1, lyric='mi'),
]

ConversionEngine.export_pdf_solfa_traditional(score, path)
print('Wrote', path)
print('Size:', os.path.getsize(path))
