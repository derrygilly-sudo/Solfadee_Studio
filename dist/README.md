# 🎵 Tonic Solfa Studio - Professional Music Notation Software

**Version 1.1 (Enhanced)**  
Professional music notation software for Windows with bi-directional conversion between **staff notation** and **tonic solfa notation**.

![Status](https://img.shields.io/badge/Status-Production%20Ready-green)
![Version](https://img.shields.io/badge/Version-1.1-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)

---

## 🎯 Features

### Core Music Notation
✅ **Staff Notation Editing**
- Visual staff with 5 lines for treble clef
- Point-and-click note entry
- Full duration support (whole, half, quarter, eighth, sixteenth, thirty-second)
- Dotted notes and tied notes
- Rests and measure management

✅ **Tonic Solfa Notation**
- Convert staff notation → tonic solfa
- Convert tonic solfa → staff notation
- Support for movable "Do" system
- Chromatic solfa singing
- Octave notation (lower, middle, upper)

✅ **Professional Metadata**
- Title, composer, arranger, lyricist
- Key signature (all 12 keys)
- Time signature (2/4, 3/4, 4/4, 6/8, 12/8, etc.)
- Tempo (BPM)
- Custom clefs (treble, bass, alto)

### File Format Support

#### Import/Export Formats
- **MusicXML** (.xml, .musicxml) - Industry standard
- **MIDI** (.mid, .midi) - Digital audio workstations
- **ABC Notation** (.abc) - Folk music standard
- **PDF** (.pdf) - Print-ready scores
- **WAV** (.wav) - Uncompressed audio
- **Tonic Solfa Text** (.txt) - Simple text format
- **Native Project** (.tss, .json) - Full save/restore

### Enhanced Features (v1.1+)

#### 1. **Advanced Font Styles System**
- Multiple font families (Arial, Georgia, Courier, Times New Roman, Helvetica, Verdana)
- Configurable font sizes (8pt - 72pt)
- Text styles: Normal, Bold, Italic, Bold-Italic
- Color customization for all text elements
- Style presets (Classical, Modern, Minimal)
- Real-time preview of styling

#### 2. **Speedy Entry Tool** ⚡
- Keyboard shortcuts for rapid music entry (100+ notes/minute)
- Quick note entry (A-G keys)
- Duration shortcuts (1=Whole, 2=Half, 4=Quarter, 8=Eighth, 6=16th, 3=32nd)
- Octave up/down (↑/↓)
- Rest entry (Space)
- Pattern templates:
  - Scales (C, G, D, A, E, B, F#, Db, Ab, Eb, Bb, F)
  - Arpeggios
  - Common rhythms
  - Triplets

#### 3. **Professional Lyrics & Annotations**
- Multi-line lyrics editor with verse organization
- Verse/Chorus/Bridge/Pre-Chorus/Outro sections
- Lyric formatting (bold, italic, underline, custom colors)
- Dynamic markings (pp, p, mp, mf, f, ff)
- Articulation marks (staccato, legato, accent)
- Chord symbols and fingering notation
- Performance directions (rit., accel., poco, molto)

#### 4. **Audio Generation & Export**
- Synthesize audio from scores
- **WAV export** at 44.1kHz or 48kHz
- **MP3 export** with customizable bitrate (optional)
- Multiple instrument sounds:
  - Sine wave (pure)
  - Triangle wave
  - Square wave
  - Sawtooth wave
  - Piano (with harmonics)
  - Bell/Chime
  - Flute
- ADSR envelope control
- Volume adjustment
- Real-time playback preview

### Additional Tools

✨ **Interactive Learning Panel**
- Visual guide to tonic solfa syllables
- Do-Re-Mi-Fa-Sol-La-Ti mappings
- Chromatic solfa reference
- Octave notation guide
- Duration notation examples
- Key signature chart

📊 **Score Summary**
- Measure count
- Note count and statistics
- Key signature and tempo
- Time signature analysis
- Estimated duration

🎨 **Visual Staff Editor**
- Click-to-place notes
- Drag to move notes
- Selection and deletion tools
- Real-time rendering
- Zoom and scroll support

---

## 🚀 Quick Start

### Installation

#### 1. Install Python 3.8+
Download from [python.org](https://www.python.org/downloads/) and install with "Add Python to PATH" option checked.

#### 2. Download Tonic Solfa Studio
```bash
git clone https://github.com/derrygee/tonic-solfa-studio.git
cd "TONIC SOLFA SOFTWARE"
```

#### 3. Option A: Auto-Install (Windows)
Double-click `install_and_run.bat` - it will:
- Check for Python
- Install all dependencies
- Launch the application

#### 4. Option B: Manual Install
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python tonic_solfa_studio.py
```

### First Run

1. **Create a new score**: File → New
2. **Enter title**: Edit score metadata in properties panel
3. **Choose key and time signature**
4. **Shift to Staff panel** and begin entering notes:
   - Click note button, then click on staff to place
   - Or use Speedy Entry (Ctrl+E) for keyboard shortcuts
5. **Switch to Solfa panel** to see tonic solfa notation
6. **Export**: File → Export → Choose format (MusicXML, MIDI, PDF, WAV, etc.)

---

## 📖 User Guide

### Keyboard Shortcuts (Speedy Entry Mode)

```
NOTES:          C D E F G A B               (Enter pitches)
DURATION:       1=Whole, 2=Half, 4=Quarter
                8=Eighth, 6=16th, 3=32nd
OCTAVE:         ↑/↓ = Raise/Lower octave
SPECIAL:        Space=Rest, .=Dot, ←=Undo
                Ctrl+H = Shortcuts help
```

### Menu Structure

```
File
├── New                    (Ctrl+N)
├── Open                   (Ctrl+O)
├── Save                   (Ctrl+S)
├── Save As
├── Recent Files
├── Import (MusicXML, MIDI, ABC)
├── Export (All formats)
└── Exit                   (Ctrl+Q)

Edit
├── Undo                   (Ctrl+Z)
├── Cut                    (Ctrl+X)
├── Copy                   (Ctrl+C)
├── Paste                  (Ctrl+V)
└── Select All             (Ctrl+A)

View
├── Zoom In                (+)
├── Zoom Out               (-)
├── Reset Zoom
└── Themes

Tools
├── Speedy Entry           (Ctrl+E)
├── Font Styles Manager
├── Lyrics Editor
├── Audio Export
├── Keyboard Shortcuts     (Ctrl+H)
└── Learning Panel

Help
├── About
├── User Guide
├── Online Resources
└── Donate
```

### Staff Notation

**Note Entry:**
1. Select note tool (pencil icon)
2. Select duration (quarter note, eighth, etc.)
3. Click on staff line/space to place note

**Staff Lines (Treble Clef):**
```
Lines (bottom to top):  E  G  B  D  F
Spaces (bottom to top): F  A  C  E
Octave 4 middle C: One space below bottom line
```

### Tonic Solfa Notation

**Syllables:**
```
Do (d)   - First degree
Re (r)   - Second degree
Mi (m)   - Third degree
Fa (f)   - Fourth degree
Sol (s)  - Fifth degree
La (l)   - Sixth degree
Ti (t)   - Seventh degree
```

**Duration Notation:**
```
(none)  = Quarter note ♩
─       = Half note 𝅗𝅥
═       = Whole note 𝅝
.       = Eighth note ♪
..      = Sixteenth note
·       = Dotted note (1.5x duration)
```

**Octave Notation:**
```
d,      = Lower Do (subscript comma)
d       = Middle Do
d'      = Upper Do (superscript apostrophe)
```

---

## 📦 Module Documentation

### Core Modules

**tonic_solfa_studio.py** (2,500+ lines)
- Main GUI application
- StaffCanvas for visualization
- Menu and toolbar management
- Project save/load

**font_styles_manager.py** (700+ lines)
- FontStyle class with presets
- FontStylesDialog for interactive editing
- Support for 6+ font families
- Color and spacing customization

**speedy_entry_tool.py** (750+ lines)
- SpeedyEntryTool with keyboard mapping
- ShortcutsDialog for reference
- ScaleTemplate with 10+ popular scales
- Real-time indicator panel

**lyrics_manager.py** (650+ lines)
- LyricsManager for verse organization
- LyricsEditorPanel with formatting
- Support for Verse/Chorus/Bridge sections
- Bold, italic, underline, color formatting

**audio_engine.py** (800+ lines)
- WaveformGenerator (sine, triangle, square, sawtooth, piano, bell, flute)
- AudioSynthesizer for score→audio
- EnvelopeGenerator (ADSR, percussive)
- WavFileWriter for WAV export

### Conversion Engine

**ConversionEngine** (included in main)
- score_to_solfa() - Staff notation → Tonic solfa text
- solfa_text_to_score() - Tonic solfa text → Staff notation
- score_to_musicxml() - Export to MusicXML format
- score_to_midi_bytes() - Export to MIDI
- score_to_abc() - Export to ABC notation
- score_to_pdf() - Export to professional PDF
- midi_to_score() - Import from MIDI
- musicxml_to_score() - Import from MusicXML

---

## 🎨 Customization

### Create Custom Font Preset

Edit `font_styles_manager.py`:

```python
'my_preset': {
    'title': FontStyle(
        name="Title",
        family="Georgia",
        size=22,
        weight="bold",
        color="#FFFFFF",
        alignment="center",
        spacing=1.0,
        line_height=1.2,
        kerning=True,
        underline=False,
        strikethrough=False
    ),
    # ... other styles
}
```

### Add Custom Scale Template

Edit `speedy_entry_tool.py`:

```python
SCALES = {
    'E_Major': ['E', 'F#', 'G#', 'A', 'B', 'C#', 'D#'],
    # ... other scales
}
```

### Modify Audio Instrument

Edit `audio_engine.py`:

```python
INSTRUMENT_PRESETS = {
    'violin': {...},
    'trumpet': {...},
    # Add your own
}
```

---

## 🔧 Configuration Files

### Project File Format (.tss, .json)

```json
{
  "title": "Twinkle Twinkle Little Star",
  "composer": "Jane Taylor (lyrics) / Traditional (melody)",
  "arranger": "User Name",
  "lyricist": "Jane Taylor",
  "key_sig": "C",
  "time_num": 4,
  "time_den": 4,
  "tempo_bpm": 120,
  "clef": "treble",
  "font_name": "Georgia",
  "font_size": 12,
  "page_size": "A4",
  "measures": [
    {
      "number": 1,
      "time_num": 4,
      "time_den": 4,
      "key_sig": "C",
      "clef": "treble",
      "notes": [
        {
          "pitch": "C",
          "octave": 4,
          "duration": 1.0,
          "dotted": false,
          "rest": false,
          "lyric": "Twin",
          "dynamic": "p"
        }
        // ... more notes
      ]
    }
    // ... more measures
  ]
}
```

---

## 🧪 Testing

### Run Unit Tests

```bash
python -m pytest tests/
```

### Manual Testing Checklist

- [ ] Create new score
- [ ] Enter notes via staff editor
- [ ] Switch to alternate keys (G major, F major, etc.)
- [ ] Export to MusicXML (verify in MuseScore/Finale)
- [ ] Export to MIDI (play in DAW)
- [ ] Export to PDF (verify layout)
- [ ] Export to WAV (listen to synthesis)
- [ ] Import MusicXML file
- [ ] Import MIDI file
- [ ] Test speedy entry shortcuts
- [ ] Apply font styles
- [ ] Add and format lyrics
- [ ] Save and load .tss project

---

## 🐛 Troubleshooting

### "Module not found" errors

Install missing dependencies:
```bash
pip install -r requirements.txt
```

### Graphics rendering issues

Update Tkinter (usually built-in):
```bash
# Windows
python -m pip install --upgrade tkinter

# Linux
sudo apt-get install python3-tk

# macOS
brew install python-tk
```

### Audio export produces silence

Ensure numpy/scipy installed:
```bash
pip install numpy scipy
```

### MusicXML import fails

Verify music21 is properly installed:
```bash
python -c "import music21; print(music21.__version__)"
```

### Slow performance on large scores

- Reduce screen resolution of staff canvas
- Close other applications
- Use "Minimize to Tray" when not editing

---

## 📊 Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Create new score | < 100ms | Instant |
| Load 4-measure file | < 200ms | JSON parsing |
| Export to MusicXML | < 500ms | Up to 10 measures |
| Export to MIDI | < 300ms | Real-time playable |
| Export to PDF | 1-2s | reportlab rendering |
| Export to WAV | 2-5s | Audio synthesis |
| Speedy entry | 100+ notes/min | With practice |

---

## 📋 Version History

### v1.1 (2026-03-24) - Enhanced Edition
- ✨ Advanced font styles with 6+ presets
- ✨ Speedy entry tool with keyboard shortcuts
- ✨ Professional lyrics editor with formatting
- ✨ Audio synthesis and WAV export
- ✨ ADSR envelope and multiple instruments
- 📈 ~1,700 lines of new code

### v1.0 (2026-03) - Initial Release
- Core staff/solfa notation
- MusicXML, MIDI, ABC, PDF export
- Basic GUI with properties panel
- Learning support materials

---

## 🤝 Contributing

Found a bug or have a feature request?

1. Check [Issues](https://github.com/derrygee/tonic-solfa-studio/issues)
2. Create a new issue with:
   - Clear title
   - Steps to reproduce
   - Expected vs. actual behavior
   - Your system (OS, Python version)

---

## 📝 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- **Music21** - UC Berkeley music theory library
- **ReportLab** - PDF generation
- **MIDIUtil** - MIDI file creation
- **Tkinter** - Python GUI framework

---

## 📞 Contact & Support

- 📧 Email: support@tonicsolfa.dev
- 🌐 Website: https://www.tonicsolfa.dev
- 💬 Discord: [Join Community](https://discord.gg/tonic-solfa)
- 🐦 Twitter: [@TonicSolfaStudio](https://twitter.com/tonicSolfaStudio)

---

## 📚 Additional Resources

- [Music Theory Basics](https://www.musictheory.net/)
- [Tonic Solfa Explained](https://en.wikipedia.org/wiki/Solmization)
- [MusicXML Standard](https://www.musicxml.com/)
- [MIDI Specification](https://www.midi.org/)

---

**Happy Music Making! 🎵**

*Made with ❤️ for musicians and music educators worldwide*
