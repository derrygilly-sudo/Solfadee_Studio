#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Lyrics Manager for Tonic Solfa Studio
Provides professional lyrics editing, formatting, and organization features.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

# Color palette
DARK   = "#1a1a2e"
PANEL  = "#16213e"
CARD   = "#0f3460"
ACCENT = "#e94560"
GOLD   = "#f5a623"
TEXT   = "#eaeaea"
MUTED  = "#8892a4"
GREEN  = "#00d4aa"
WHITE  = "#ffffff"


class LyricSection(Enum):
    """Lyric section types."""
    VERSE = "Verse"
    CHORUS = "Chorus"
    BRIDGE = "Bridge"
    PRE_CHORUS = "Pre-Chorus"
    OUTRO = "Outro"
    INTRO = "Intro"


@dataclass
class LyricSyllable:
    """A single syllable with optional formatting."""
    text: str              # The syllable text
    section: LyricSection  # Section it belongs to
    verse_num: int         # Verse/section number
    note_num: int          # Associated note number
    bold: bool = False
    italic: bool = False
    color: str = TEXT
    
    def to_dict(self) -> dict:
        return {
            'text': self.text,
            'section': self.section.name,
            'verse_num': self.verse_num,
            'note_num': self.note_num,
            'bold': self.bold,
            'italic': self.italic,
            'color': self.color
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> 'LyricSyllable':
        return cls(
            text=d['text'],
            section=LyricSection[d.get('section', 'VERSE')],
            verse_num=d.get('verse_num', 1),
            note_num=d.get('note_num', 0),
            bold=d.get('bold', False),
            italic=d.get('italic', False),
            color=d.get('color', TEXT)
        )


@dataclass
class LyricVerse:
    """A complete verse/section with multiple lines."""
    section_type: LyricSection
    section_num: int
    lines: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'section_type': self.section_type.name,
            'section_num': self.section_num,
            'lines': self.lines
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> 'LyricVerse':
        return cls(
            section_type=LyricSection[d['section_type']],
            section_num=d.get('section_num', 1),
            lines=d.get('lines', [])
        )


class LyricsManager:
    """Manages lyrics for a score."""
    
    def __init__(self):
        self.verses: Dict[str, LyricVerse] = {}  # key = "Verse1", "Chorus1", etc.
        self.syllables: List[LyricSyllable] = []
        self.current_verse = None
        self.observers = []
    
    def register_observer(self, callback):
        """Register callback for changes."""
        self.observers.append(callback)
    
    def notify_observers(self):
        """Notify observers of changes."""
        for callback in self.observers:
            callback()
    
    def add_verse(self, section: LyricSection, num: int, lines: List[str]):
        """Add a verse."""
        key = f"{section.name}{num}"
        self.verses[key] = LyricVerse(section, num, lines)
        self.notify_observers()
    
    def get_verse(self, section: LyricSection, num: int) -> Optional[LyricVerse]:
        """Get a verse."""
        key = f"{section.name}{num}"
        return self.verses.get(key)
    
    def get_all_verses(self) -> List[LyricVerse]:
        """Get all verses in order."""
        return list(self.verses.values())
    
    def remove_verse(self, section: LyricSection, num: int):
        """Remove a verse."""
        key = f"{section.name}{num}"
        if key in self.verses:
            del self.verses[key]
            self.notify_observers()
    
    def add_syllable(self, syllable: LyricSyllable):
        """Add a syllable."""
        self.syllables.append(syllable)
        self.notify_observers()
    
    def to_dict(self) -> dict:
        """Serialize."""
        return {
            'verses': {k: v.to_dict() for k, v in self.verses.items()},
            'syllables': [s.to_dict() for s in self.syllables]
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> 'LyricsManager':
        """Deserialize."""
        manager = cls()
        for k, v in d.get('verses', {}).items():
            verse = LyricVerse.from_dict(v)
            manager.verses[k] = verse
        for s in d.get('syllables', []):
            manager.syllables.append(LyricSyllable.from_dict(s))
        return manager


class LyricsEditorPanel(tk.Frame):
    """Edit lyrics with formatting and organization."""
    
    def __init__(self, parent, lyrics_manager: LyricsManager, **kwargs):
        super().__init__(parent, bg=DARK, **kwargs)
        self.lyrics_manager = lyrics_manager
        self.lyrics_manager.register_observer(self.on_content_changed)
        
        self.current_section = LyricSection.VERSE
        self.current_verse_num = 1
        self.selected_text = ""
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the UI."""
        # Header
        header = tk.Frame(self, bg=PANEL, height=40)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header, text="📝 Lyrics Editor", bg=PANEL, fg=GOLD,
                 font=('Arial', 12, 'bold'), anchor='w', padx=15).pack(side='left', fill='both', expand=True)
        
        # Controls
        controls = tk.Frame(self, bg=CARD)
        controls.pack(fill='x', padx=10, pady=8)
        
        tk.Label(controls, text="Section:", bg=CARD, fg=TEXT).pack(side='left', padx=5)
        section_var = tk.StringVar(value="Verse")
        section_combo = ttk.Combobox(
            controls, textvariable=section_var,
            values=[s.value for s in LyricSection],
            state='readonly', width=12
        )
        section_combo.pack(side='left', padx=5)
        section_combo.bind('<<ComboboxSelected>>', 
                          lambda e: self._on_section_change(section_var.get()))
        self.section_var = section_var
        
        tk.Label(controls, text="Number:", bg=CARD, fg=TEXT).pack(side='left', padx=5)
        verse_num_var = tk.StringVar(value="1")
        verse_num_spin = ttk.Spinbox(
            controls, textvariable=verse_num_var,
            from_=1, to=10, width=4
        )
        verse_num_spin.pack(side='left', padx=5)
        verse_num_spin.bind('<KeyRelease>',
                           lambda e: self._on_verse_change(verse_num_var.get()))
        self.verse_num_var = verse_num_var
        
        tk.Button(controls, text="New Verse", bg=ACCENT, fg=WHITE,
                 command=self._on_new_verse).pack(side='left', padx=5)
        
        # Main editor area
        editor_container = tk.Frame(self, bg=DARK)
        editor_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Text editor with toolbar
        editor_toolbar = tk.Frame(editor_container, bg=CARD)
        editor_toolbar.pack(fill='x', pady=(0, 5))
        
        tk.Button(editor_toolbar, text="B", font=('Arial', 9, 'bold'),
                 width=3, bg=PANEL, fg=TEXT,
                 command=self._toggle_bold).pack(side='left', padx=2)
        tk.Button(editor_toolbar, text="I", font=('Arial', 9, 'italic'),
                 width=3, bg=PANEL, fg=TEXT,
                 command=self._toggle_italic).pack(side='left', padx=2)
        tk.Button(editor_toolbar, text="U", font=('Arial', 9, 'underline'),
                 width=3, bg=PANEL, fg=TEXT,
                 command=self._toggle_underline).pack(side='left', padx=2)
        
        ttk.Separator(editor_toolbar, orient='vertical').pack(side='left', padx=5, fill='y')
        
        tk.Button(editor_toolbar, text="🎨 Color", bg=PANEL, fg=TEXT,
                 command=self._pick_color).pack(side='left', padx=2)
        
        ttk.Separator(editor_toolbar, orient='vertical').pack(side='left', padx=5, fill='y')
        
        tk.Button(editor_toolbar, text="Clear Format", bg=CARD, fg=MUTED,
                 command=self._clear_formatting).pack(side='left', padx=2)
        
        # Text area
        self.text_area = tk.Text(
            editor_container, bg=CARD, fg=TEXT, font=('Georgia', 11),
            height=12, wrap='word', undo=True,
            insertbackground=GOLD
        )
        self.text_area.pack(fill='both', expand=True)
        self.text_area.bind('<<Change>>', self._on_text_change)
        
        # Bottom section info
        bottom = tk.Frame(self, bg=PANEL)
        bottom.pack(fill='x', padx=10, pady=5)
        
        self.info_label = tk.Label(bottom, text="", bg=PANEL, fg=MUTED, font=('Arial', 8))
        self.info_label.pack(anchor='w')
        
        # List of verses
        list_frame = tk.LabelFrame(self, text="Verses", bg=CARD, fg=GOLD)
        list_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        self.verse_listbox = tk.Listbox(
            list_frame, bg=CARD, fg=TEXT, font=('Arial', 9),
            height=4, highlightthickness=0, bd=0
        )
        self.verse_listbox.pack(fill='x', padx=8, pady=8)
        self.verse_listbox.bind('<<ListboxSelect>>', self._on_verse_select)
        
        # Buttons
        button_frame = tk.Frame(self, bg=DARK)
        button_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        tk.Button(button_frame, text="Save Verse", bg=ACCENT, fg=WHITE,
                 command=self._save_verse).pack(side='left', padx=5)
        tk.Button(button_frame, text="Delete Verse", bg=CARD, fg=MUTED,
                 command=self._delete_verse).pack(side='left', padx=5)
        tk.Button(button_frame, text="Import Lyrics", bg=PANEL, fg=TEXT,
                 command=self._import_lyrics).pack(side='left', padx=5)
        tk.Button(button_frame, text="Export Lyrics", bg=PANEL, fg=TEXT,
                 command=self._export_lyrics).pack(side='right', padx=5)
    
    def _on_section_change(self, section_name: str):
        """Handle section change."""
        for s in LyricSection:
            if s.value == section_name:
                self.current_section = s
                break
        self._load_verse()
    
    def _on_verse_change(self, num_str: str):
        """Handle verse number change."""
        try:
            self.current_verse_num = int(num_str)
            self._load_verse()
        except ValueError:
            pass
    
    def _load_verse(self):
        """Load current verse into editor."""
        verse = self.lyrics_manager.get_verse(self.current_section, self.current_verse_num)
        self.text_area.delete('1.0', 'end')
        if verse:
            text = '\n'.join(verse.lines)
            self.text_area.insert('1.0', text)
        self._update_verse_list()
    
    def _on_new_verse(self):
        """Create new verse."""
        self.lyrics_manager.add_verse(
            self.current_section,
            self.current_verse_num,
            ["Line 1\nLine 2\nLine 3"]
        )
        self._load_verse()
    
    def _save_verse(self):
        """Save current verse."""
        text = self.text_area.get('1.0', 'end').strip()
        lines = text.split('\n')
        self.lyrics_manager.add_verse(
            self.current_section,
            self.current_verse_num,
            lines
        )
        messagebox.showinfo("Success", "Verse saved!")
    
    def _delete_verse(self):
        """Delete current verse."""
        if messagebox.askyesno("Confirm", "Delete this verse?"):
            self.lyrics_manager.remove_verse(
                self.current_section,
                self.current_verse_num
            )
            self.text_area.delete('1.0', 'end')
            self._update_verse_list()
    
    def _toggle_bold(self):
        """Toggle bold formatting on selection."""
        try:
            sel = self.text_area.tag_ranges('sel')
            if sel:
                self.text_area.tag_add('bold', sel[0], sel[1])
                self.text_area.tag_configure('bold', font=('Georgia', 11, 'bold'))
        except:
            pass
    
    def _toggle_italic(self):
        """Toggle italic formatting."""
        try:
            sel = self.text_area.tag_ranges('sel')
            if sel:
                self.text_area.tag_add('italic', sel[0], sel[1])
                self.text_area.tag_configure('italic', font=('Georgia', 11, 'italic'))
        except:
            pass
    
    def _toggle_underline(self):
        """Toggle underline."""
        try:
            sel = self.text_area.tag_ranges('sel')
            if sel:
                self.text_area.tag_add('underline', sel[0], sel[1])
                self.text_area.tag_configure('underline', underline=True)
        except:
            pass
    
    def _pick_color(self):
        """Pick text color."""
        try:
            from tkinter import colorchooser
            color = colorchooser.askcolor(color=TEXT)[1]
            if color:
                sel = self.text_area.tag_ranges('sel')
                if sel:
                    tag_name = f'color_{color}'
                    self.text_area.tag_add(tag_name, sel[0], sel[1])
                    self.text_area.tag_configure(tag_name, foreground=color)
        except:
            messagebox.showerror("Error", "Could not pick color")
    
    def _clear_formatting(self):
        """Clear all formatting."""
        try:
            sel = self.text_area.tag_ranges('sel')
            if sel:
                for tag in self.text_area.tag_names():
                    self.text_area.tag_remove(tag, sel[0], sel[1])
        except:
            pass
    
    def _update_verse_list(self):
        """Update verse listbox."""
        self.verse_listbox.delete(0, 'end')
        for verse in self.lyrics_manager.get_all_verses():
            label = f"{verse.section_type.value} {verse.section_num}"
            self.verse_listbox.insert('end', label)
    
    def _on_verse_select(self, event):
        """Handle verse selection from listbox."""
        selection = self.verse_listbox.curselection()
        if selection:
            verses = self.lyrics_manager.get_all_verses()
            verse = verses[selection[0]]
            self.current_section = verse.section_type
            self.current_verse_num = verse.section_num
            self.section_var.set(verse.section_type.value)
            self.verse_num_var.set(str(verse.section_num))
            self._load_verse()
    
    def _on_text_change(self, event=None):
        """Text changed."""
        word_count = len(self.text_area.get('1.0', 'end').split())
        self.info_label.config(text=f"Words: {word_count}")
    
    def _import_lyrics(self):
        """Import lyrics from file."""
        messagebox.showinfo("Import", "Not yet implemented")
    
    def _export_lyrics(self):
        """Export lyrics to file."""
        messagebox.showinfo("Export", "Not yet implemented")
    
    def on_content_changed(self):
        """Called when lyrics change."""
        self._update_verse_list()


# Example usage
if __name__ == '__main__':
    root = tk.Tk()
    root.title("Lyrics Manager - Test")
    root.geometry("700x800")
    root.configure(bg=DARK)
    
    manager = LyricsManager()
    panel = LyricsEditorPanel(root, manager)
    panel.pack(fill='both', expand=True, padx=10, pady=10)
    
    root.mainloop()
