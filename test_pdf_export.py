#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from tonic_solfa_studio_v5 import Score, Measure, MusNote, ConversionEngine, REPORTLAB_OK
import tempfile
import os

print(f"ReportLab Available: {REPORTLAB_OK}")

# Create a simple test score
score = Score()
score.title = "Test Hymn"
score.composer = "Test Composer"
score.key_sig = "C"
score.time_num = 4
score.time_den = 4
score.tempo_bpm = 120

# Ensure measures exist
score.ensure_measures(1)

# Add some notes
m1 = score.measures[0]
m1.notes = [
    MusNote(pitch='C', octave=4, duration=1.0, voice=1, lyric="Test"),
    MusNote(pitch='D', octave=4, duration=1.0, voice=1),
    MusNote(pitch='E', octave=4, duration=1.0, voice=1),
    MusNote(pitch='F', octave=4, duration=1.0, voice=1),
]

# Try to export to PDF
with tempfile.TemporaryDirectory() as tmpdir:
    pdf_path = os.path.join(tmpdir, "test.pdf")
    try:
        ConversionEngine.export_pdf_solfa_traditional(score, pdf_path)
        if os.path.exists(pdf_path):
            print(f"✓ PDF exported successfully to {pdf_path}")
            print(f"  File size: {os.path.getsize(pdf_path)} bytes")
        else:
            print(f"✗ PDF file was not created")
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
