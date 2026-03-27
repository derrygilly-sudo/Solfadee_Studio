import sys
sys.path.insert(0, '.')
from tonic_solfa_studio_v5 import MusNote, SUBSCRIPT_MAP, SUPERSCRIPT_MAP

# Test octave notation
test_notes = [
    (MusNote(pitch='C', octave=2, voice=1), 'C2 (subscript 2)'),
    (MusNote(pitch='D', octave=3, voice=1), 'D3 (subscript 1)'),
    (MusNote(pitch='E', octave=4, voice=1), 'E4 (plain)'),
    (MusNote(pitch='F', octave=5, voice=1), 'F5 (superscript 1)'),
    (MusNote(pitch='G', octave=6, voice=1), 'G6 (superscript 2)'),
]

print("Octave Notation Test (Key=C):")
print("=" * 50)
for note, expected in [
    (test_notes[0][0], 'd2'),    # C2 -> d2
    (test_notes[1][0], 'r1'),    # D3 -> r1
    (test_notes[2][0], 'm'),     # E4 -> m
    (test_notes[3][0], "f'"),  # F5 -> f'
    (test_notes[4][0], "s''"), # G6 -> s''
]:
    result = note.solfa('C')
    print(f"note={note.pitch}{note.octave:2d} -> solfa={result}")
    assert result == expected, f"Expected {expected}, got {result}"

print("\n✓ Octave style mapping works correctly")
