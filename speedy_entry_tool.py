#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Speedy Entry Tool for Tonic Solfa Studio
Enables fast note entry through keyboard shortcuts and pattern templates.
Allows experienced musicians to enter music quickly using familiar patterns.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
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


class DurationMode(Enum):
    """Duration shortcuts."""
    WHOLE = 4.0       # 1 key
    HALF = 2.0        # 2 key
    QUARTER = 1.0     # 4 key (default)
    EIGHTH = 0.5      # 8 key
    SIXTEENTH = 0.25  # 6 key
    THIRTYSECOND = 0.125  # 3 key


class ScaleTemplate:
    """Predefined scale and pattern templates for quick entry."""
    
    SCALES = {
        'C_Major': ['C', 'D', 'E', 'F', 'G', 'A', 'B'],
        'C_Minor': ['C', 'D', 'Eb', 'F', 'G', 'Ab', 'Bb'],
        'C_Major_Pentatonic': ['C', 'D', 'E', 'G', 'A'],
        'C_Minor_Pentatonic': ['C', 'Eb', 'F', 'G', 'Bb'],
        'G_Major': ['G', 'A', 'B', 'C', 'D', 'E', 'F#'],
        'D_Major': ['D', 'E', 'F#', 'G', 'A', 'B', 'C#'],
        'A_Major': ['A', 'B', 'C#', 'D', 'E', 'F#', 'G#'],
        'F_Major': ['F', 'G', 'A', 'Bb', 'C', 'D', 'E'],
        'Bb_Major': ['Bb', 'C', 'D', 'Eb', 'F', 'G', 'A'],
        'Eb_Major': ['Eb', 'F', 'G', 'Ab', 'Bb', 'C', 'D'],
    }
    
    ARPEGGIOS = {
        'C_Major': ['C', 'E', 'G'],
        'C_Minor': ['C', 'Eb', 'G'],
        'C_Diminished': ['C', 'Eb', 'Gb'],
        'C_Augmented': ['C', 'E', 'G#'],
        'F_Major': ['F', 'A', 'C'],
        'G_Major': ['G', 'B', 'D'],
    }
    
    RHYTHMS = {
        'Simple4': ['q', 'q', 'q', 'q'],  # 4 quarters
        'RhythmA': ['q', 'e', 'e', 'q'],
        'RhythmB': ['e', 'e', 'q', 'q'],
        'RhythmC': ['h', 'q', 'q'],
        'RhythmD': ['q', 'q', 'h'],
        'Triplet': ['et', 'et', 'et', 'q'],  # Eighth triplets
    }
    
    @classmethod
    def get_scale(cls, name: str) -> Optional[List[str]]:
        """Get a scale template."""
        return cls.SCALES.get(name)
    
    @classmethod
    def get_arpeggio(cls, name: str) -> Optional[List[str]]:
        """Get an arpeggio template."""
        return cls.ARPEGGIOS.get(name)
    
    @classmethod
    def get_rhythm(cls, name: str) -> Optional[List[str]]:
        """Get a rhythm template."""
        return cls.RHYTHMS.get(name)
    
    @classmethod
    def list_scales(cls) -> List[str]:
        """List all available scales."""
        return list(cls.SCALES.keys())
    
    @classmethod
    def list_arpeggios(cls) -> List[str]:
        """List all available arpeggios."""
        return list(cls.ARPEGGIOS.keys())
    
    @classmethod
    def list_rhythms(cls) -> List[str]:
        """List all available rhythms."""
        return list(cls.RHYTHMS.keys())


@dataclass
class ShortcutKey:
    """A keyboard shortcut mapping."""
    key: str                    # Key name (e.g., 'c', 'Control-n')
    action: str                 # Action name
    description: str            # Human-readable description
    callback: Optional[Callable] = None  # Function to call


class SpeedyEntryTool:
    """Manages fast music entry through keyboard shortcuts."""
    
    def __init__(self):
        self.shortcuts: Dict[str, ShortcutKey] = {}
        self.enabled = False
        self.current_duration = DurationMode.QUARTER
        self.current_octave = 4
        self.entry_counter = 0
        self.last_note = None
        self.callbacks = {}
        self._setup_default_shortcuts()
    
    def _setup_default_shortcuts(self):
        """Set up default keyboard shortcuts for note entry."""
        # Note pitches (C through B)
        notes = {
            'c': 'C', 'd': 'D', 'e': 'E', 'f': 'F',
            'g': 'G', 'a': 'A', 'b': 'B'
        }
        for key, pitch in notes.items():
            self.add_shortcut(ShortcutKey(
                key=key,
                action=f'note_{pitch}',
                description=f'Enter {pitch}'
            ))
        
        # Duration shortcuts (number row)
        durations = {
            '1': (DurationMode.WHOLE, 'Whole note'),
            '2': (DurationMode.HALF, 'Half note'),
            '4': (DurationMode.QUARTER, 'Quarter note'),
            '8': (DurationMode.EIGHTH, 'Eighth note'),
            '6': (DurationMode.SIXTEENTH, '16th note'),
            '3': (DurationMode.THIRTYSECOND, '32nd note'),
        }
        for key, (dur, desc) in durations.items():
            self.add_shortcut(ShortcutKey(
                key=key,
                action=f'duration_{dur.value}',
                description=desc
            ))
        
        # Rest
        self.add_shortcut(ShortcutKey(
            key='space',
            action='rest',
            description='Insert rest'
        ))
        
        # Octave controls
        self.add_shortcut(ShortcutKey(
            key='Up',
            action='octave_up',
            description='Raise octave'
        ))
        
        self.add_shortcut(ShortcutKey(
            key='Down',
            action='octave_down',
            description='Lower octave'
        ))
        
        # Special
        self.add_shortcut(ShortcutKey(
            key='period',
            action='dot_note',
            description='Dot note'
        ))
        
        self.add_shortcut(ShortcutKey(
            key='BackSpace',
            action='undo_last',
            description='Undo last note'
        ))
        
        self.add_shortcut(ShortcutKey(
            key='Control-z',
            action='undo',
            description='Undo'
        ))
        
        self.add_shortcut(ShortcutKey(
            key='Control-h',
            action='show_help',
            description='Show shortcuts'
        ))
    
    def add_shortcut(self, shortcut: ShortcutKey):
        """Add a shortcut."""
        self.shortcuts[shortcut.key] = shortcut
    
    def register_callback(self, action: str, callback: Callable):
        """Register a callback for an action."""
        self.callbacks[action] = callback
    
    def handle_key(self, key: str) -> bool:
        """Handle a key press. Returns True if handled."""
        if not self.enabled:
            return False
        
        shortcut = self.shortcuts.get(key)
        if not shortcut:
            return False
        
        # Execute the action
        return self._execute_action(shortcut.action)
    
    def _execute_action(self, action: str) -> bool:
        """Execute an action. Returns True if handled."""
        callback = self.callbacks.get(action)
        if callback:
            callback()
            return True
        
        # Built-in actions
        if action.startswith('note_'):
            pitch = action.replace('note_', '')
            self._on_note_entry(pitch)
            return True
        elif action.startswith('duration_'):
            dur_val = float(action.replace('duration_', ''))
            for d in DurationMode:
                if d.value == dur_val:
                    self.current_duration = d
                    break
            return True
        elif action == 'rest':
            self._on_rest_entry()
            return True
        elif action == 'octave_up':
            self.current_octave = min(8, self.current_octave + 1)
            return True
        elif action == 'octave_down':
            self.current_octave = max(1, self.current_octave - 1)
            return True
        elif action == 'dot_note':
            self._on_dot_note()
            return True
        elif action == 'undo_last':
            self._on_undo()
            return True
        
        return False
    
    def _on_note_entry(self, pitch: str):
        """Handle note entry."""
        # This would be called by the main app
        self.entry_counter += 1
        self.last_note = pitch
        # Callback to main app would happen here
    
    def _on_rest_entry(self):
        """Handle rest entry."""
        self.entry_counter += 1
    
    def _on_dot_note(self):
        """Handle dotting current note."""
        # Callback to main app would dot the last note
        pass
    
    def _on_undo(self):
        """Handle undo."""
        if self.entry_counter > 0:
            self.entry_counter -= 1
    
    def get_shortcuts_list(self) -> List[tuple]:
        """Get list of shortcuts for display."""
        return [(s.key, s.action, s.description) 
                for s in self.shortcuts.values()]
    
    def toggle_enabled(self):
        """Toggle speedy entry mode."""
        self.enabled = not self.enabled
        return self.enabled
    
    def reset_counters(self):
        """Reset input counters."""
        self.entry_counter = 0
        self.last_note = None


class SpeedyEntryPanel(tk.Frame):
    """GUI panel for speedy entry tool."""
    
    def __init__(self, parent, speedy_entry: SpeedyEntryTool, **kwargs):
        super().__init__(parent, bg=DARK, **kwargs)
        self.speedy_entry = speedy_entry
        self.enabled = False
        self._build_ui()
    
    def _build_ui(self):
        """Build the UI."""
        # Header
        header = tk.Frame(self, bg=PANEL, height=35)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        self.toggle_btn = tk.Button(
            header, text="🚀 Speedy Entry: OFF",
            bg=CARD, fg=TEXT, font=('Arial', 11, 'bold'),
            command=self._toggle_mode
        )
        self.toggle_btn.pack(side='left', padx=10, pady=5)
        
        tk.Label(header, text="Fast music input mode",
                 bg=PANEL, fg=MUTED, font=('Arial', 9)).pack(side='left', padx=10)
        
        # Main container
        main = tk.Frame(self, bg=DARK)
        main.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Info panel
        info = tk.LabelFrame(main, text="Quick Info", bg=CARD, fg=GOLD, font=('Arial', 10, 'bold'))
        info.pack(fill='x', pady=(0, 10))
        
        info_frame = tk.Frame(info, bg=CARD)
        info_frame.pack(fill='x', padx=10, pady=8)
        
        self.duration_label = tk.Label(info_frame, text="Duration: Quarter", bg=CARD, fg=TEXT)
        self.duration_label.pack(side='left', padx=10)
        
        self.octave_label = tk.Label(info_frame, text="Octave: 4", bg=CARD, fg=TEXT)
        self.octave_label.pack(side='left', padx=10)
        
        self.counter_label = tk.Label(info_frame, text="Notes: 0", bg=CARD, fg=GREEN, font=('Arial', 9, 'bold'))
        self.counter_label.pack(side='right', padx=10)
        
        # Pitch pad
        pitch_frame = tk.LabelFrame(main, text="Note Pad (A-G)", bg=CARD, fg=GOLD, font=('Arial', 10, 'bold'))
        pitch_frame.pack(fill='x', pady=10)
        
        pad_grid = tk.Frame(pitch_frame, bg=CARD)
        pad_grid.pack(padx=10, pady=10)
        
        pitches = [('C', 0), ('D', 1), ('E', 2), ('F', 3),
                   ('G', 4), ('A', 5), ('B', 6)]
        for pitch, col in pitches:
            btn = tk.Button(
                pad_grid, text=pitch, width=8, font=('Arial', 11, 'bold'),
                bg=ACCENT, fg=WHITE, relief='raised', bd=2
            )
            btn.grid(row=0, column=col, padx=2, pady=5)
        
        # Duration buttons
        dur_frame = tk.LabelFrame(main, text="Duration (1/2/4/8)", bg=CARD, fg=GOLD, font=('Arial', 10, 'bold'))
        dur_frame.pack(fill='x', pady=10)
        
        dur_grid = tk.Frame(dur_frame, bg=CARD)
        dur_grid.pack(padx=10, pady=10)
        
        durations = [('1', 'Whole', 0), ('2', 'Half', 1),
                     ('4', 'Quarter', 2), ('8', 'Eighth', 3)]
        for key, label, col in durations:
            btn = tk.Button(
                dur_grid, text=f"{key}\n{label}", width=10, height=3,
                font=('Arial', 9), bg=PANEL, fg=TEXT
            )
            btn.grid(row=0, column=col, padx=3, pady=5)
        
        # Pattern templates
        pattern_frame = tk.LabelFrame(main, text="Quick Patterns", bg=CARD, fg=GOLD, font=('Arial', 10, 'bold'))
        pattern_frame.pack(fill='x', pady=10)
        
        pattern_grid = tk.Frame(pattern_frame, bg=CARD)
        pattern_grid.pack(padx=10, pady=10, fill='x')
        
        scales = ScaleTemplate.list_scales()[:4]
        for i, scale in enumerate(scales):
            btn = tk.Button(
                pattern_grid, text=scale.replace('_', '\n'),
                font=('Arial', 9), bg=CARD, fg=GREEN,
                relief='flat', bd=1
            )
            btn.pack(side='left', padx=5, fill='both', expand=True)
        
        # Help text
        help_text = tk.Text(main, bg=CARD, fg=MUTED, height=8, font=('Courier', 9))
        help_text.pack(fill='both', expand=True, pady=10)
        help_text.insert('1.0', self._get_help_text())
        help_text.config(state='disabled')
    
    def _get_help_text(self) -> str:
        """Get help text for shortcuts."""
        return """KEYBOARD SHORTCUTS (when Speedy Entry is ON)

NOTES:  C D E F G A B               Enter pitch
DURATION: 1=Whole, 2=Half, 4=Quarter, 8=Eighth, 6=16th, 3=32nd
OCTAVE: ↑/↓ = Raise/Lower octave
SPECIAL: Space=Rest, .=Dot, Backspace=Undo, Ctrl+H=Help

EXAMPLE: Press "G" + "4" + "G" for G-quarter-G in current octave
Press "↑" then "E" to enter E in upper octave
"""
    
    def _toggle_mode(self):
        """Toggle speedy entry mode."""
        self.enabled = self.speedy_entry.toggle_enabled()
        mode_text = "ON" if self.enabled else "OFF"
        mode_color = GREEN if self.enabled else TEXT
        
        self.toggle_btn.configure(
            text=f"🚀 Speedy Entry: {mode_text}",
            fg=mode_color,
            activeforeground=mode_color
        )
    
    def update_info(self):
        """Update display info."""
        if hasattr(self.speedy_entry, 'current_duration'):
            dur_name = {
                DurationMode.WHOLE: 'Whole',
                DurationMode.HALF: 'Half',
                DurationMode.QUARTER: 'Quarter',
                DurationMode.EIGHTH: 'Eighth',
                DurationMode.SIXTEENTH: '16th',
                DurationMode.THIRTYSECOND: '32nd',
            }.get(self.speedy_entry.current_duration, 'Quarter')
            self.duration_label.configure(text=f"Duration: {dur_name}")
        
        self.octave_label.configure(text=f"Octave: {self.speedy_entry.current_octave}")
        self.counter_label.configure(text=f"Notes: {self.speedy_entry.entry_counter}")


class ShortcutsDialog(tk.Toplevel):
    """Dialog showing all available shortcuts."""
    
    def __init__(self, parent, speedy_entry: SpeedyEntryTool):
        super().__init__(parent)
        self.title("Keyboard Shortcuts")
        self.geometry("500x600")
        self.configure(bg=DARK)
        
        self.speedy_entry = speedy_entry
        self._build_ui()
    
    def _build_ui(self):
        """Build the UI."""
        # Header
        header = tk.Frame(self, bg=PANEL, height=40)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(
            header, text="Keyboard Shortcuts Reference",
            bg=PANEL, fg=GOLD, font=('Arial', 12, 'bold'), anchor='w', padx=15
        ).pack(side='left', fill='both', expand=True, pady=10)
        
        # Scrollable list
        main = tk.Frame(self, bg=DARK)
        main.pack(fill='both', expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(main, bg=DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=DARK)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add shortcuts
        for key, action, desc in self.speedy_entry.get_shortcuts_list():
            self._add_shortcut_row(scrollable_frame, key, action, desc)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Close button
        tk.Button(
            self, text="Close", bg=ACCENT, fg=WHITE,
            command=self.destroy
        ).pack(pady=10)
    
    def _add_shortcut_row(self, parent, key, action, desc):
        """Add a shortcut row to the dialog."""
        row = tk.Frame(parent, bg=CARD, relief='flat', bd=1)
        row.pack(fill='x', pady=3)
        
        tk.Label(row, text=key, bg=CARD, fg=GOLD, width=15, anchor='w',
                 font=('Courier', 10, 'bold')).pack(side='left', padx=5, pady=3)
        tk.Label(row, text=desc, bg=CARD, fg=TEXT, anchor='w',
                 font=('Arial', 9)).pack(side='left', padx=5, pady=3, fill='x', expand=True)


# Example usage
if __name__ == '__main__':
    root = tk.Tk()
    root.title("Speedy Entry Tool - Test")
    root.geometry("600x700")
    root.configure(bg=DARK)
    
    speedy = SpeedyEntryTool()
    panel = SpeedyEntryPanel(root, speedy)
    panel.pack(fill='both', expand=True)
    
    def show_shortcuts():
        dialog = ShortcutsDialog(root, speedy)
        root.wait_window(dialog)
    
    tk.Button(root, text="Show All Shortcuts", command=show_shortcuts,
              bg=ACCENT, fg=WHITE).pack(pady=10)
    
    root.mainloop()
