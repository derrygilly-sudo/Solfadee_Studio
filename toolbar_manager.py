#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Toolbars and Palettes Manager for Tonic Solfa Studio
Implements Finale-style editing, staff, and special symbol toolbars.
"""

import tkinter as tk
from tkinter import ttk
from enum import Enum
from typing import Callable, Dict, Optional, List


# Theme colors
DARK   = "#1a1a2e"
PANEL  = "#16213e"
CARD   = "#0f3460"
ACCENT = "#e94560"
GOLD   = "#f5a623"
TEXT   = "#eaeaea"
MUTED  = "#8892a4"
GREEN  = "#00d4aa"
WHITE  = "#ffffff"


class Tool(Enum):
    """Available editing tools."""
    POINTER = "pointer"        # Selection
    NOTE = "note"              # Note entry
    REST = "rest"              # Rest entry
    ERASE = "erase"            # Eraser
    LYRIC = "lyric"            # Lyric entry
    DYNAMICS = "dynamics"      # Dynamics marks
    ARTICULATION = "articulation"  # Articulations (staccato, accent, etc.)
    TREMOLO = "tremolo"        # Tremolo marks
    SLUR = "slur"              # Slur drawing
    BEAM = "beam"              # Beam adjustments


class VoicePart(Enum):
    """SATB (4-part) voice assignments."""
    SOPRANO = 0                # Highest voice
    ALTO = 1                   # Second voice
    TENOR = 2                  # Third voice
    BASS = 3                   # Lowest voice


class DynamicMark(Enum):
    """Dynamic marking symbols."""
    PPPP = "pppp"  # Quadruple pianissimo
    PPP = "ppp"    # Triple p
    PP = "pp"      # Double p
    P = "p"        # Soft
    MP = "mp"      # Mezzo-piano
    MF = "mf"      # Mezzo-forte
    F = "f"        # Forte
    FF = "ff"      # Double forte
    FFF = "fff"    # Triple forte
    FFFF = "ffff"  # Quadruple forte
    SF = "sf"      # Subito forte
    SFZ = "sfz"    # Sforzando
    RF = "rf"      # Rinforzando
    RFZ = "rfz"    # Rinforzando


class ArticulationMark(Enum):
    """Articulation marking symbols."""
    STACCATO = "staccato"          # .
    STACCATISSIMO = "staccatissimo" # ▼
    TENUTO = "tenuto"              # -
    MARCATO = "marcato"            # ^
    ACCENT = "accent"              # >
    SFORZANDO = "sforzando"        # sfz
    OPEN = "open"                  # (string instrument)
    MUTED = "muted"                # (string instrument)
    TONGUED = "tongued"            # Brass
    FLUTTER = "flutter"            # (wind instrument)


class OrnamentMark(Enum):
    """Ornamentation symbols."""
    TRILL = "trill"                # tr
    TURN = "turn"                  # ⁀
    MORDENT = "mordent"            # ♩ 
    INV_MORDENT = "inv_mordent"    # ♪
    APPOGGIATURA = "appoggiatura"  # grace note
    ACCIACCATURA = "acciaccatura"  # quick grace note
    DIATONIC_TRILL = "diatonic_trill"  # tr with accidental


class EditingToolbar(tk.Frame):
    """Main editing toolbar with tools for note entry and manipulation."""

    def __init__(self, master, on_tool_change: Callable = None, **kwargs):
        super().__init__(master, bg=CARD, height=50, **kwargs)
        self.pack_propagate(False)
        self.on_tool_change = on_tool_change
        self.current_tool = Tool.NOTE
        self.tool_buttons: Dict[Tool, tk.Button] = {}
        
        self._build_toolbar()

    def _build_toolbar(self):
        """Build the main editing toolbar."""
        # Title
        title = tk.Label(self, text="EDITING TOOLS", bg=CARD, fg=GOLD,
                        font=('Arial', 9, 'bold'))
        title.pack(side='left', padx=10, pady=5)

        # Separator
        sep = tk.Frame(self, bg=MUTED, width=1)
        sep.pack(side='left', fill='y', padx=5)

        # Tool buttons
        tools = [
            (Tool.POINTER, "◀ Select", "Select/move notes"),
            (Tool.NOTE, "♩ Note", "Add notes to staff"),
            (Tool.REST, "𝄽 Rest", "Add rests"),
            (Tool.ERASE, "✕ Erase", "Delete notes/rests"),
            (Tool.LYRIC, "♪ Lyrics", "Add lyrics beneath notes"),
        ]

        for tool, label, tooltip in tools:
            btn = self._create_tool_button(tool, label, tooltip)
            self.tool_buttons[tool] = btn

        # Separator
        sep2 = tk.Frame(self, bg=MUTED, width=1)
        sep2.pack(side='left', fill='y', padx=5)

        # Advanced tools
        adv_tools = [
            (Tool.SLUR, "𝄐 Slur", "Draw slurs"),
            (Tool.BEAM, "⌢ Beam", "Adjust beaming"),
            (Tool.TREMOLO, "♈ Tremolo", "Add tremolo marks"),
        ]

        for tool, label, tooltip in adv_tools:
            btn = self._create_tool_button(tool, label, tooltip)
            self.tool_buttons[tool] = btn

        # Status label
        self.status = tk.Label(self, text="Tool: Note Entry", bg=CARD, fg=TEXT,
                              font=('Arial', 8))
        self.status.pack(side='right', padx=10)

        # Set initial active button
        self._set_tool(Tool.NOTE)

    def _create_tool_button(self, tool: Tool, label: str, tooltip: str) -> tk.Button:
        """Create a tool button with visual feedback."""
        def on_click():
            self._set_tool(tool)
            if self.on_tool_change:
                self.on_tool_change(tool)

        btn = tk.Button(
            self,
            text=label,
            bg=PANEL,
            fg=TEXT,
            activebackground=ACCENT,
            activeforeground=WHITE,
            relief='flat',
            font=('Arial', 8),
            command=on_click,
            padx=8,
            pady=4,
            cursor='hand2'
        )
        btn.pack(side='left', padx=2)
        
        # Tooltip
        btn.bind('<Enter>', lambda e: self._show_tooltip(e, tooltip))
        btn.bind('<Leave>', lambda e: self._hide_tooltip())
        
        return btn

    def _set_tool(self, tool: Tool):
        """Activate a tool and update visual feedback."""
        # Reset previous button
        if self.current_tool in self.tool_buttons:
            self.tool_buttons[self.current_tool].config(bg=PANEL)
        
        # Highlight new button
        self.current_tool = tool
        self.tool_buttons[tool].config(bg=ACCENT)
        self.status.config(text=f"Tool: {tool.value.title()}")

    def _show_tooltip(self, event, text: str):
        """Show tooltip on hover."""
        if not hasattr(self, 'tooltip') or self.tooltip is None:
            self.tooltip = tk.Toplevel(self)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{event.x_root}+{event.y_root+20}")
            
            label = tk.Label(self.tooltip, text=text, bg=GOLD, fg=DARK,
                           font=('Arial', 8), padx=5, pady=2)
            label.pack()

    def _hide_tooltip(self):
        """Hide tooltip."""
        if hasattr(self, 'tooltip') and self.tooltip:
            try:
                self.tooltip.destroy()
            except:
                pass
            self.tooltip = None

    def get_current_tool(self) -> Tool:
        """Get currently selected tool."""
        return self.current_tool


class StaffToolbar(tk.Frame):
    """Staff manipulation toolbar."""

    def __init__(self, master, on_action: Callable = None, **kwargs):
        super().__init__(master, bg=CARD, height=50, **kwargs)
        self.pack_propagate(False)
        self.on_action = on_action
        
        self._build_toolbar()

    def _build_toolbar(self):
        """Build staff toolbar."""
        title = tk.Label(self, text="STAFF TOOLS", bg=CARD, fg=GOLD,
                        font=('Arial', 9, 'bold'))
        title.pack(side='left', padx=10, pady=5)

        sep = tk.Frame(self, bg=MUTED, width=1)
        sep.pack(side='left', fill='y', padx=5)

        # Staff operations
        ops = [
            ("+ Staff", "Add staff", lambda: self._perform_action("add_staff")),
            ("- Staff", "Remove staff", lambda: self._perform_action("remove_staff")),
            ("Clef", "Change clef", lambda: self._perform_action("clef_dialog")),
            ("Key Sig", "Change key signature", lambda: self._perform_action("key_dialog")),
            ("Time Sig", "Change time signature", lambda: self._perform_action("time_dialog")),
            ("Beam", "Auto-beam notes", lambda: self._perform_action("auto_beam")),
            ("Stem", "Flip stem direction", lambda: self._perform_action("flip_stem")),
        ]

        for label, tooltip, cmd in ops:
            btn = tk.Button(
                self,
                text=label,
                bg=PANEL,
                fg=TEXT,
                activebackground=ACCENT,
                activeforeground=WHITE,
                relief='flat',
                font=('Arial', 8),
                command=cmd,
                padx=8,
                pady=4
            )
            btn.pack(side='left', padx=2)
            btn.bind('<Enter>', lambda e, t=tooltip: self._show_tooltip(e, t))
            btn.bind('<Leave>', lambda e: self._hide_tooltip())

    def _perform_action(self, action: str):
        """Perform toolbar action."""
        if self.on_action:
            self.on_action(action)

    def _show_tooltip(self, event, text: str):
        """Show tooltip."""
        if not hasattr(self, 'tooltip') or self.tooltip is None:
            self.tooltip = tk.Toplevel(self)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{event.x_root}+{event.y_root+20}")
            
            label = tk.Label(self.tooltip, text=text, bg=GOLD, fg=DARK,
                           font=('Arial', 8), padx=5, pady=2)
            label.pack()

    def _hide_tooltip(self):
        """Hide tooltip."""
        if hasattr(self, 'tooltip') and self.tooltip:
            try:
                self.tooltip.destroy()
            except:
                pass
            self.tooltip = None


class SpecialPalettePanel(tk.Frame):
    """Palette for special symbols: dynamics, articulations, ornaments."""

    def __init__(self, master, on_select: Callable = None, **kwargs):
        super().__init__(master, bg=PANEL, **kwargs)
        self.on_select = on_select
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        self._build_dynamics_palette()
        self._build_articulation_palette()
        self._build_note_symbols_palette()
        self._build_ornament_palette()

    def _build_dynamics_palette(self):
        """Build dynamics palette."""
        frame = tk.Frame(self.notebook, bg=PANEL)
        self.notebook.add(frame, text="Dynamics")
        
        canvas = tk.Canvas(frame, bg=PANEL, highlightthickness=0, height=200)
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=PANEL)
        
        scrollable.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Grid of dynamics
        row, col = 0, 0
        for mark in DynamicMark:
            btn = tk.Button(
                scrollable,
                text=mark.value.upper(),
                bg=CARD,
                fg=GOLD if mark in [DynamicMark.SF, DynamicMark.SFZ, DynamicMark.RF, DynamicMark.RFZ] else TEXT,
                font=('Arial', 9, 'bold'),
                relief='flat',
                padx=6,
                pady=4,
                command=lambda m=mark: self._on_select(m, "dynamic")
            )
            btn.grid(row=row, column=col, padx=2, pady=2)
            col += 1
            if col >= 4:
                col = 0
                row += 1
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def _build_articulation_palette(self):
        """Build articulation palette."""
        frame = tk.Frame(self.notebook, bg=PANEL)
        self.notebook.add(frame, text="Articulations")
        
        canvas = tk.Canvas(frame, bg=PANEL, highlightthickness=0, height=200)
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=PANEL)
        
        scrollable.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Grid of articulations
        articulation_symbols = [
            (ArticulationMark.STACCATO, "."),
            (ArticulationMark.TENUTO, "-"),
            (ArticulationMark.MARCATO, "^"),
            (ArticulationMark.ACCENT, ">"),
            (ArticulationMark.STACCATISSIMO, "▼"),
            (ArticulationMark.SFORZANDO, "sfz"),
            (ArticulationMark.OPEN, "○"),
            (ArticulationMark.MUTED, "◆"),
            (ArticulationMark.TONGUED, "✓"),
            (ArticulationMark.FLUTTER, "Fr"),
        ]
        
        row, col = 0, 0
        for mark, symbol in articulation_symbols:
            btn = tk.Button(
                scrollable,
                text=symbol,
                bg=CARD,
                fg=TEXT,
                font=('Arial', 10, 'bold'),
                relief='flat',
                padx=6,
                pady=4,
                command=lambda m=mark: self._on_select(m, "articulation")
            )
            btn.grid(row=row, column=col, padx=2, pady=2)
            col += 1
            if col >= 4:
                col = 0
                row += 1
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def _build_note_symbols_palette(self):
        """Build note duration symbols palette - for quick note entry."""
        frame = tk.Frame(self.notebook, bg=PANEL)
        self.notebook.add(frame, text="Note Durations")
        
        # Title
        title = tk.Label(frame, text="Note Durations (Click to Select)",
                        bg=PANEL, fg=GOLD, font=('Arial', 10, 'bold'))
        title.pack(pady=10)
        
        # Large buttons for each note duration
        btn_frame = tk.Frame(frame, bg=PANEL)
        btn_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Note symbols with their names and musical values
        note_durations = [
            ('𝅝', 'Semibreve', 'whole', 4.0, 'Full measure note (4 beats)'),
            ('𝅗𝅥', 'Minim', 'half', 2.0, 'Half note (2 beats)'),
            ('♩', 'Crotchet', 'quarter', 1.0, 'Quarter note (1 beat)'),
            ('♪', 'Quaver', 'eighth', 0.5, 'Eighth note (1/2 beat)'),
            ('𝅘𝅥𝅯', 'Semiquaver', '16th', 0.25, 'Sixteenth note (1/4 beat)'),
        ]
        
        for symbol, name, value, duration, description in note_durations:
            # Container for each note button
            note_container = tk.Frame(btn_frame, bg=CARD, relief='raised', bd=1)
            note_container.pack(fill='x', pady=5, padx=5)
            
            # Left: Symbol and name
            left = tk.Frame(note_container, bg=CARD)
            left.pack(side='left', fill='x', expand=True, padx=10, pady=8)
            
            symbol_label = tk.Label(left, text=symbol, bg=CARD, fg=WHITE,
                                   font=('Arial', 28, 'bold'))
            symbol_label.pack(side='left', padx=(0, 15))
            
            info = tk.Frame(left, bg=CARD)
            info.pack(side='left', fill='x')
            
            name_label = tk.Label(info, text=name, bg=CARD, fg=GOLD,
                                 font=('Arial', 12, 'bold'))
            name_label.pack(anchor='w')
            
            desc_label = tk.Label(info, text=description, bg=CARD, fg=MUTED,
                                 font=('Arial', 9))
            desc_label.pack(anchor='w')
            
            # Right: Select button
            select_btn = tk.Button(note_container, text="SELECT", bg=ACCENT, fg=WHITE,
                                  font=('Arial', 9, 'bold'), relief='flat',
                                  padx=15, pady=8,
                                  command=lambda v=value, n=name: self._on_note_duration_select(v, n))
            select_btn.pack(side='right', padx=10, pady=8)
            
            # Hover effect
            def on_enter(event, c=note_container):
                c.config(bg='#1a4d7d')
            def on_leave(event, c=note_container):
                c.config(bg=CARD)
            
            note_container.bind('<Enter>', on_enter)
            note_container.bind('<Leave>', on_leave)
            select_btn.bind('<Enter>', on_enter)
            select_btn.bind('<Leave>', on_leave)
    
    def _on_note_duration_select(self, duration: float, name: str):
        """Handle note duration selection."""
        if self.on_select:
            self.on_select({"duration": duration, "name": name}, "note_duration")

    def _build_ornament_palette(self):
        """Build ornament palette."""
        frame = tk.Frame(self.notebook, bg=PANEL)
        self.notebook.add(frame, text="Ornaments")
        
        canvas = tk.Canvas(frame, bg=PANEL, highlightthickness=0, height=200)
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=PANEL)
        
        scrollable.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Grid of ornaments
        ornament_symbols = [
            (OrnamentMark.TRILL, "tr"),
            (OrnamentMark.TURN, "⁀"),
            (OrnamentMark.MORDENT, "♩"),
            (OrnamentMark.INV_MORDENT, "♪"),
            (OrnamentMark.APPOGGIATURA, ""),
            (OrnamentMark.ACCIACCATURA, ""),
            (OrnamentMark.DIATONIC_TRILL, "tr~"),
        ]
        
        row, col = 0, 0
        for mark, symbol in ornament_symbols:
            btn = tk.Button(
                scrollable,
                text=symbol if symbol else mark.value.replace('_', ' ').title(),
                bg=CARD,
                fg=TEXT,
                font=('Arial', 9),
                relief='flat',
                padx=6,
                pady=4,
                command=lambda m=mark: self._on_select(m, "ornament")
            )
            btn.grid(row=row, column=col, padx=2, pady=2)
            col += 1
            if col >= 3:
                col = 0
                row += 1
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def _on_select(self, mark, category: str):
        """Handle palette symbol selection."""
        if self.on_select:
            self.on_select(mark, category)


class VoiceLayerPanel(tk.Frame):
    """Voice part layer selector (SATB) with layer controls."""

    def __init__(self, master, on_voice_change: Callable = None, **kwargs):
        super().__init__(master, bg=CARD, **kwargs)
        self.on_voice_change = on_voice_change
        self.current_voice = VoicePart.SOPRANO
        self.voice_buttons: Dict[VoicePart, tk.Button] = {}
        
        self._build_panel()

    def _build_panel(self):
        """Build voice layer panel."""
        # Title
        title = tk.Label(self, text="VOICE PARTS (SATB)", bg=CARD, fg=GOLD,
                        font=('Arial', 9, 'bold'))
        title.pack(side='top', padx=10, pady=5)

        # Voice buttons in a row
        frame = tk.Frame(self, bg=CARD)
        frame.pack(side='top', fill='x', padx=5, pady=5)

        voices = [
            (VoicePart.SOPRANO, "S", "Soprano", "#ff6b9d"),
            (VoicePart.ALTO, "A", "Alto", "#c06c84"),
            (VoicePart.TENOR, "T", "Tenor", "#6c567b"),
            (VoicePart.BASS, "B", "Bass", "#355c7d"),
        ]

        for voice, abbr, name, color in voices:
            btn = tk.Button(
                frame,
                text=f"{abbr}\n{name}",
                bg=color,
                fg=WHITE,
                activebackground=GOLD,
                activeforeground=DARK,
                relief='flat',
                font=('Arial', 8, 'bold'),
                padx=10,
                pady=8,
                command=lambda v=voice: self._select_voice(v),
                cursor='hand2'
            )
            btn.pack(side='left', padx=3)
            self.voice_buttons[voice] = btn

        # Voice info
        self.info_label = tk.Label(self, text="Active Voice: Soprano", bg=CARD, fg=TEXT,
                                  font=('Arial', 8))
        self.info_label.pack(side='top', padx=10, pady=5)

        # Layer visibility toggles
        frame2 = tk.Frame(self, bg=CARD)
        frame2.pack(side='top', fill='x', padx=5, pady=5)

        tk.Label(frame2, text="Show:", bg=CARD, fg=TEXT, font=('Arial', 7)).pack(side='left', padx=5)
        
        self.visibility_vars = {}
        for voice, abbr, _, _ in voices:
            var = tk.BooleanVar(value=True)
            self.visibility_vars[voice] = var
            chk = tk.Checkbutton(frame2, text=abbr, variable=var, bg=CARD, fg=TEXT,
                               selectcolor=ACCENT, font=('Arial', 7))
            chk.pack(side='left', padx=2)

        # Set initial active
        self._select_voice(VoicePart.SOPRANO)

    def _select_voice(self, voice: VoicePart):
        """Select active voice part."""
        # Reset previous button
        if self.current_voice in self.voice_buttons:
            btn = self.voice_buttons[self.current_voice]
            # Restore original color
            colors = {VoicePart.SOPRANO: "#ff6b9d", VoicePart.ALTO: "#c06c84",
                     VoicePart.TENOR: "#6c567b", VoicePart.BASS: "#355c7d"}
            btn.config(bg=colors[self.current_voice])

        # Highlight new voice
        self.current_voice = voice
        self.voice_buttons[voice].config(bg=ACCENT, fg=DARK)
        self.info_label.config(text=f"Active Voice: {voice.name.title()}")
        
        if self.on_voice_change:
            self.on_voice_change(voice)

    def get_current_voice(self) -> VoicePart:
        """Get current voice part."""
        return self.current_voice

    def get_visible_voices(self) -> List[VoicePart]:
        """Get list of visible voice parts."""
        return [v for v, var in self.visibility_vars.items() if var.get()]
