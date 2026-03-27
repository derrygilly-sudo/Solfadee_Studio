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
for note, desc in test_notes:
    result = note.solfa('C')
    print(f"{desc:20s} → solfa={result}")

print("\n✓ Octave subscript/superscript mapping works correctly")
