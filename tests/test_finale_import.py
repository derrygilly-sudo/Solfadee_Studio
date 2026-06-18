import os
import zipfile
import tempfile
import xml.etree.ElementTree as ET
import pytest

from tonic_solfa_studio_v5 import ConversionEngine


def _make_simple_musicxml(path: str):
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Music</part-name></score-part></part-list>
  <part id="P1"><measure number="1"><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note></measure></part>
</score-partwise>'''
    with open(path, 'w', encoding='utf-8') as f:
        f.write(xml)


def test_import_finale_from_musx_zip(tmp_path, monkeypatch):
    # Create a .musx-like ZIP containing a MusicXML file
    musicxml = tmp_path / 'score.xml'
    _make_simple_musicxml(str(musicxml))
    musx = tmp_path / 'test.musx'
    with zipfile.ZipFile(str(musx), 'w') as z:
        z.write(str(musicxml), arcname='MusicXML/score.xml')

    s = ConversionEngine.import_finale(str(musx))
    assert s is not None
    assert hasattr(s, 'measures')
    assert any(len(m.notes) > 0 for m in s.measures)


def test_import_finale_binary_mus_shows_info(tmp_path, monkeypatch):
    # Binary .mus should be handled gracefully — patch messagebox to avoid modal
    import tkinter.messagebox as mb

    called = {'info': False}

    def fake_info(title, msg):
        called['info'] = True

    monkeypatch.setattr(mb, 'showinfo', fake_info)

    # Create a fake binary .mus file (not a ZIP)
    mus = tmp_path / 'fake.mus'
    mus.write_bytes(b"MUS_BINARY_HEADER\x00\x01\x02")

    s = ConversionEngine.import_finale(str(mus))
    assert s is not None
    assert called['info'] is True
    # ensure at least default measures exist
    assert len(s.measures) >= 1
