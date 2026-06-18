import pytest


def _has_usable_tk():
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.update()
        root.destroy()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _has_usable_tk(), reason="No usable Tk available for GUI tests")
def test_pro_canvas_edit_sync_keeps_manual_edits():
    from tonic_solfa_studio_v5 import TonicSolfaStudio, Measure, MusNote

    app = TonicSolfaStudio()
    app.withdraw()
    try:
        measure = Measure(number=1)
        measure.notes.append(MusNote('C', 4, duration=1.0, voice=1))
        app.score.measures = [measure]
        app._sync_solfa_canvas()

        edited_note = app.new_solfa_canvas.score.measures[0].notes[0]
        edited_note.syllable = 's'
        edited_note.beat_marker = ':-'
        edited_note.lyric = 'Edited'

        # Trigger a refresh that should preserve live edits
        app._refresh_solfa_canvas_pro_view(sync_from_main=False)

        refreshed_note = app.new_solfa_canvas.score.measures[0].notes[0]
        assert refreshed_note.syllable == 's'
        assert refreshed_note.beat_marker == ':-'
        assert refreshed_note.lyric == 'Edited'
    finally:
        try:
            app.destroy()
        except Exception:
            pass
