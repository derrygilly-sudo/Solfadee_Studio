#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Font Styles Manager for Tonic Solfa Studio
Handles multiple font styles, sizes, and formatting options for professional output.
"""

import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional

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

class FontWeight(Enum):
    """Font weight options."""
    LIGHT = 300
    NORMAL = 400
    BOLD = 700
    EXTRA_BOLD = 900

class TextAlignment(Enum):
    """Text alignment options."""
    LEFT = 'left'
    CENTER = 'center'
    RIGHT = 'right'

@dataclass
class FontStyle:
    """Complete font style definition."""
    name: str              # Style name (e.g., "Title", "Composer", "Lyric")
    family: str            # Font family (Arial, Georgia, Courier, Times New Roman, etc.)
    size: int              # Point size (8-72)
    weight: str            # normal, bold, italic, bold italic
    color: str             # Hex color (#RRGGBB)
    alignment: str         # left, center, right
    spacing: float         # Letter spacing multiplier (0.8 - 1.5)
    line_height: float     # Line height multiplier (0.9 - 1.5)
    kerning: bool          # Enable kerning
    underline: bool        # Underline text
    strikethrough: bool    # Strikethrough text
    
    def to_tkinter_font_spec(self) -> Tuple[str, int, str]:
        """Convert to Tkinter font specification tuple."""
        weight_map = {
            'normal': '',
            'bold': 'bold',
            'italic': 'italic',
            'bold italic': 'bold italic'
        }
        tkinter_weight = weight_map.get(self.weight, '')
        return (self.family, self.size, tkinter_weight)
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            'name': self.name,
            'family': self.family,
            'size': self.size,
            'weight': self.weight,
            'color': self.color,
            'alignment': self.alignment,
            'spacing': self.spacing,
            'line_height': self.line_height,
            'kerning': self.kerning,
            'underline': self.underline,
            'strikethrough': self.strikethrough
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FontStyle':
        """Deserialize from dictionary."""
        return cls(**data)
    
    @classmethod
    def default_title(cls) -> 'FontStyle':
        """Default style for score title."""
        return cls(
            name="Title",
            family="Georgia",
            size=20,
            weight="bold",
            color=WHITE,
            alignment="center",
            spacing=1.0,
            line_height=1.2,
            kerning=True,
            underline=False,
            strikethrough=False
        )
    
    @classmethod
    def default_composer(cls) -> 'FontStyle':
        """Default style for composer."""
        return cls(
            name="Composer",
            family="Georgia",
            size=12,
            weight="italic",
            color=MUTED,
            alignment="center",
            spacing=1.0,
            line_height=1.1,
            kerning=True,
            underline=False,
            strikethrough=False
        )
    
    @classmethod
    def default_lyric(cls) -> 'FontStyle':
        """Default style for lyrics."""
        return cls(
            name="Lyric",
            family="Arial",
            size=10,
            weight="normal",
            color=TEXT,
            alignment="left",
            spacing=1.0,
            line_height=1.3,
            kerning=False,
            underline=False,
            strikethrough=False
        )
    
    @classmethod
    def default_dynamic(cls) -> 'FontStyle':
        """Default style for dynamics (pp, ff, etc.)."""
        return cls(
            name="Dynamic",
            family="Georgia",
            size=11,
            weight="italic",
            color=GOLD,
            alignment="center",
            spacing=1.0,
            line_height=1.0,
            kerning=True,
            underline=False,
            strikethrough=False
        )
    
    @classmethod
    def default_annotation(cls) -> 'FontStyle':
        """Default style for annotations."""
        return cls(
            name="Annotation",
            family="Arial",
            size=9,
            weight="normal",
            color=GREEN,
            alignment="left",
            spacing=0.9,
            line_height=1.0,
            kerning=False,
            underline=False,
            strikethrough=False
        )


class FontStylePreset:
    """Font style presets for quick access."""
    
    PRESETS = {
        'classical': {
            'title': FontStyle.default_title(),
            'composer': FontStyle.default_composer(),
            'lyric': FontStyle(
                name="Lyric",
                family="Garamond",
                size=11,
                weight="normal",
                color=TEXT,
                alignment="center",
                spacing=1.0,
                line_height=1.4,
                kerning=True,
                underline=False,
                strikethrough=False
            ),
            'dynamic': FontStyle.default_dynamic(),
            'annotation': FontStyle.default_annotation()
        },
        'modern': {
            'title': FontStyle(
                name="Title",
                family="Arial",
                size=18,
                weight="bold",
                color=WHITE,
                alignment="left",
                spacing=1.05,
                line_height=1.2,
                kerning=True,
                underline=False,
                strikethrough=False
            ),
            'composer': FontStyle(
                name="Composer",
                family="Arial",
                size=11,
                weight="normal",
                color=MUTED,
                alignment="left",
                spacing=1.0,
                line_height=1.1,
                kerning=False,
                underline=False,
                strikethrough=False
            ),
            'lyric': FontStyle.default_lyric(),
            'dynamic': FontStyle.default_dynamic(),
            'annotation': FontStyle.default_annotation()
        },
        'minimal': {
            'title': FontStyle(
                name="Title",
                family="Courier",
                size=14,
                weight="bold",
                color=GOLD,
                alignment="left",
                spacing=1.0,
                line_height=1.1,
                kerning=False,
                underline=False,
                strikethrough=False
            ),
            'composer': FontStyle(
                name="Composer",
                family="Courier",
                size=10,
                weight="normal",
                color=TEXT,
                alignment="left",
                spacing=1.0,
                line_height=1.0,
                kerning=False,
                underline=False,
                strikethrough=False
            ),
            'lyric': FontStyle(
                name="Lyric",
                family="Courier",
                size=9,
                weight="normal",
                color=TEXT,
                alignment="left",
                spacing=1.0,
                line_height=1.2,
                kerning=False,
                underline=False,
                strikethrough=False
            ),
            'dynamic': FontStyle(
                name="Dynamic",
                family="Courier",
                size=9,
                weight="bold",
                color=ACCENT,
                alignment="center",
                spacing=1.0,
                line_height=1.0,
                kerning=False,
                underline=False,
                strikethrough=False
            ),
            'annotation': FontStyle(
                name="Annotation",
                family="Courier",
                size=8,
                weight="normal",
                color=MUTED,
                alignment="left",
                spacing=0.9,
                line_height=1.0,
                kerning=False,
                underline=False,
                strikethrough=False
            )
        }
    }
    
    @classmethod
    def get_preset(cls, name: str) -> Optional[dict]:
        """Get a preset by name."""
        return cls.PRESETS.get(name)
    
    @classmethod
    def list_presets(cls) -> List[str]:
        """List all available preset names."""
        return list(cls.PRESETS.keys())


class FontStylesManager:
    """Manager for font styles in the application."""
    
    def __init__(self, parent_widget=None):
        self.parent = parent_widget
        self.styles: Dict[str, FontStyle] = {
            'title': FontStyle.default_title(),
            'composer': FontStyle.default_composer(),
            'lyric': FontStyle.default_lyric(),
            'dynamic': FontStyle.default_dynamic(),
            'annotation': FontStyle.default_annotation()
        }
        self.custom_styles: Dict[str, FontStyle] = {}
        self.observers = []
    
    def register_observer(self, callback):
        """Register a callback for style changes."""
        self.observers.append(callback)
    
    def notify_observers(self):
        """Notify all observers of style changes."""
        for callback in self.observers:
            callback()
    
    def get_style(self, key: str) -> Optional[FontStyle]:
        """Get a style by key."""
        return self.styles.get(key) or self.custom_styles.get(key)
    
    def set_style(self, key: str, style: FontStyle):
        """Set a style."""
        self.styles[key] = style
        self.notify_observers()
    
    def add_custom_style(self, key: str, style: FontStyle):
        """Add a custom style."""
        self.custom_styles[key] = style
        self.notify_observers()
    
    def apply_preset(self, preset_name: str):
        """Apply a preset theme."""
        preset = FontStylePreset.get_preset(preset_name)
        if preset:
            self.styles.update(preset)
            self.notify_observers()
            return True
        return False
    
    def to_dict(self) -> dict:
        """Serialize all styles to dictionary."""
        return {
            'styles': {k: v.to_dict() for k, v in self.styles.items()},
            'custom_styles': {k: v.to_dict() for k, v in self.custom_styles.items()}
        }
    
    def from_dict(self, data: dict):
        """Load styles from dictionary."""
        for k, v in data.get('styles', {}).items():
            self.styles[k] = FontStyle.from_dict(v)
        for k, v in data.get('custom_styles', {}).items():
            self.custom_styles[k] = FontStyle.from_dict(v)
        self.notify_observers()


class FontStylesDialog(tk.Toplevel):
    """Dialog window for managing font styles."""
    
    def __init__(self, parent, font_manager: FontStylesManager):
        super().__init__(parent)
        self.title("Font Styles Manager")
        self.geometry("700x600")
        self.configure(bg=DARK)
        self.resizable(False, False)
        
        self.font_manager = font_manager
        self.current_style_key = None
        self.current_style = None
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the UI."""
        # Header
        header = tk.Frame(self, bg=PANEL, height=40)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(
            header, text="Font Styles Manager",
            bg=PANEL, fg=GOLD, font=('Arial', 14, 'bold'),
            anchor='w', padx=15
        ).pack(side='left', fill='both', expand=True)
        
        # Main container
        main = tk.Frame(self, bg=DARK)
        main.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Left panel: Style list
        left = tk.Frame(main, bg=PANEL, width=250)
        left.pack(side='left', fill='both', padx=(0, 10))
        left.pack_propagate(False)
        
        tk.Label(left, text="Available Styles", bg=PANEL, fg=GOLD,
                 font=('Arial', 10, 'bold')).pack(anchor='w', padx=10, pady=8)
        
        self.style_listbox = tk.Listbox(
            left, bg=CARD, fg=TEXT, font=('Arial', 10),
            highlightthickness=0, bd=0, activestyle='none'
        )
        self.style_listbox.pack(fill='both', expand=True, padx=8, pady=8)
        self.style_listbox.bind('<<ListboxSelect>>', self._on_style_select)
        
        # Populate listbox
        for key in self.font_manager.styles.keys():
            self.style_listbox.insert('end', key.upper())
        for key in self.font_manager.custom_styles.keys():
            self.style_listbox.insert('end', f"[CUSTOM] {key.upper()}")
        
        # Right panel: Style editor
        right = tk.Frame(main, bg=DARK)
        right.pack(side='left', fill='both', expand=True)
        
        tk.Label(right, text="Style Editor", bg=DARK, fg=GOLD,
                 font=('Arial', 10, 'bold')).pack(anchor='w', pady=(0, 10))
        
        # Editor frame
        editor = tk.Frame(right, bg=CARD, relief='flat', bd=1)
        editor.pack(fill='both', expand=True)
        editor.pack_propagate(False)
        
        # Font family
        tk.Label(editor, text="Font Family:", bg=CARD, fg=TEXT, anchor='w').pack(fill='x', padx=10, pady=(10, 0))
        self.family_var = tk.StringVar()
        family_combo = ttk.Combobox(
            editor, textvariable=self.family_var,
            values=['Arial', 'Georgia', 'Courier', 'Times New Roman', 'Helvetica', 'Verdana'],
            state='readonly', width=30
        )
        family_combo.pack(fill='x', padx=10, pady=(0, 8))
        
        # Font size
        tk.Label(editor, text="Size (pt):", bg=CARD, fg=TEXT, anchor='w').pack(fill='x', padx=10, pady=(0, 0))
        size_frame = tk.Frame(editor, bg=CARD)
        size_frame.pack(fill='x', padx=10, pady=(0, 8))
        self.size_var = tk.StringVar()
        self.size_scale = tk.Scale(
            size_frame, variable=self.size_var, from_=8, to=72,
            bg=PANEL, fg=GOLD, highlightthickness=0, orient='h'
        )
        self.size_scale.pack(side='left', fill='x', expand=True)
        tk.Label(size_frame, textvariable=self.size_var, bg=CARD, fg=GOLD, width=3).pack(side='left', padx=5)
        
        # Weight
        tk.Label(editor, text="Style:", bg=CARD, fg=TEXT, anchor='w').pack(fill='x', padx=10, pady=(0, 0))
        weight_frame = tk.Frame(editor, bg=CARD)
        weight_frame.pack(fill='x', padx=10, pady=(0, 8))
        self.weight_var = tk.StringVar()
        for w in ['normal', 'bold', 'italic', 'bold italic']:
            tk.Radiobutton(
                weight_frame, text=w, variable=self.weight_var, value=w,
                bg=CARD, fg=TEXT, activebackground=PANEL
            ).pack(side='left')
        
        # Color picker
        tk.Label(editor, text="Color:", bg=CARD, fg=TEXT, anchor='w').pack(fill='x', padx=10, pady=(0, 0))
        color_frame = tk.Frame(editor, bg=CARD)
        color_frame.pack(fill='x', padx=10, pady=(0, 8))
        self.color_canvas = tk.Canvas(
            color_frame, bg=CARD, width=50, height=30, highlightthickness=0, bd=1
        )
        self.color_canvas.pack(side='left')
        self.color_canvas.bind('<Button-1>', self._on_color_pick)
        tk.Button(
            color_frame, text="Pick Color", bg=ACCENT, fg=WHITE,
            command=self._on_color_pick
        ).pack(side='left', padx=8)
        
        # Alignment
        tk.Label(editor, text="Alignment:", bg=CARD, fg=TEXT, anchor='w').pack(fill='x', padx=10, pady=(0, 0))
        align_frame = tk.Frame(editor, bg=CARD)
        align_frame.pack(fill='x', padx=10, pady=(0, 8))
        self.alignment_var = tk.StringVar()
        for a in ['left', 'center', 'right']:
            tk.Radiobutton(
                align_frame, text=a.capitalize(), variable=self.alignment_var, value=a,
                bg=CARD, fg=TEXT, activebackground=PANEL
            ).pack(side='left')
        
        # Spacing
        tk.Label(editor, text="Letter Spacing:", bg=CARD, fg=TEXT, anchor='w').pack(fill='x', padx=10, pady=(0, 0))
        spacing_frame = tk.Frame(editor, bg=CARD)
        spacing_frame.pack(fill='x', padx=10, pady=(0, 8))
        self.spacing_var = tk.StringVar()
        self.spacing_scale = tk.Scale(
            spacing_frame, variable=self.spacing_var, from_=80, to_=150,
            bg=PANEL, fg=GOLD, highlightthickness=0, orient='h'
        )
        self.spacing_scale.pack(side='left', fill='x', expand=True)
        tk.Label(spacing_frame, text="%", bg=CARD, fg=GOLD).pack(side='left', padx=5)
        
        # Checkboxes
        checks_frame = tk.Frame(editor, bg=CARD)
        checks_frame.pack(fill='x', padx=10, pady=(0, 10))
        self.underline_var = tk.BooleanVar()
        self.strikethrough_var = tk.BooleanVar()
        tk.Checkbutton(
            checks_frame, text="Underline", variable=self.underline_var,
            bg=CARD, fg=TEXT, activebackground=PANEL
        ).pack(side='left')
        tk.Checkbutton(
            checks_frame, text="Strikethrough", variable=self.strikethrough_var,
            bg=CARD, fg=TEXT, activebackground=PANEL
        ).pack(side='left', padx=10)
        
        # Preview
        preview_frame = tk.LabelFrame(right, text="Preview", bg=CARD, fg=GOLD)
        preview_frame.pack(fill='x', pady=10)
        self.preview_label = tk.Label(
            preview_frame, text="The Quick Brown Fox",
            bg=DARK, fg=TEXT, font=('Arial', 12),
            padx=10, pady=10, wraplength=300
        )
        self.preview_label.pack(fill='both', expand=True)
        
        # Buttons
        button_frame = tk.Frame(self, bg=DARK)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Button(
            button_frame, text="Apply", bg=ACCENT, fg=WHITE,
            command=self._on_apply
        ).pack(side='left', padx=5)
        
        tk.Button(
            button_frame, text="Reset", bg=CARD, fg=TEXT,
            command=self._on_reset
        ).pack(side='left', padx=5)
        
        tk.Button(
            button_frame, text="Close", bg=PANEL, fg=TEXT,
            command=self.destroy
        ).pack(side='right', padx=5)
    
    def _on_style_select(self, event):
        """Handle style selection."""
        selection = self.style_listbox.curselection()
        if not selection:
            return
        
        style_name = self.style_listbox.get(selection[0])
        if '[CUSTOM]' in style_name:
            key = style_name.replace('[CUSTOM] ', '').lower()
            self.current_style = self.font_manager.custom_styles.get(key)
        else:
            key = style_name.lower()
            self.current_style = self.font_manager.styles.get(key)
        
        self.current_style_key = key
        self._load_style_to_editor()
    
    def _load_style_to_editor(self):
        """Load current style into editor."""
        if not self.current_style:
            return
        
        self.family_var.set(self.current_style.family)
        self.size_var.set(str(self.current_style.size))
        self.weight_var.set(self.current_style.weight)
        self.alignment_var.set(self.current_style.alignment)
        self.spacing_var.set(str(int(self.current_style.spacing * 100)))
        self.underline_var.set(self.current_style.underline)
        self.strikethrough_var.set(self.current_style.strikethrough)
        
        # Update color canvas
        self.color_canvas.configure(bg=self.current_style.color)
        
        self._update_preview()
    
    def _on_color_pick(self, event=None):
        """Handle color picker."""
        color = colorchooser.askcolor(
            self.current_style.color if self.current_style else WHITE,
            title="Choose Color"
        )
        if color[1]:
            self.color_canvas.configure(bg=color[1])
            if self.current_style:
                self.current_style.color = color[1]
            self._update_preview()
    
    def _update_preview(self):
        """Update preview label."""
        if not self.current_style:
            return
        
        family = self.family_var.get()
        size = int(self.size_var.get())
        weight = self.weight_var.get()
        color = self.color_canvas.cget('bg')
        
        weight_map = {
            'bold': 'bold',
            'italic': 'italic',
            'bold italic': ('bold', 'italic'),
            'normal': ''
        }
        font_spec = (family, size, weight_map.get(weight, ''))
        
        self.preview_label.configure(font=font_spec, fg=color)
    
    def _on_apply(self):
        """Apply changes to current style."""
        if not self.current_style:
            messagebox.showwarning("No Style", "Please select a style first.")
            return
        
        self.current_style.family = self.family_var.get()
        self.current_style.size = int(self.size_var.get())
        self.current_style.weight = self.weight_var.get()
        self.current_style.alignment = self.alignment_var.get()
        self.current_style.spacing = float(self.spacing_var.get()) / 100.0
        self.current_style.underline = self.underline_var.get()
        self.current_style.strikethrough = self.strikethrough_var.get()
        self.current_style.color = self.color_canvas.cget('bg')
        
        self.font_manager.notify_observers()
        messagebox.showinfo("Success", f"Style '{self.current_style_key}' updated!")
    
    def _on_reset(self):
        """Reset current style to default."""
        if not self.current_style:
            return
        
        if messagebox.askyesno("Confirm", "Reset this style to default?"):
            if self.current_style_key == 'title':
                self.current_style = FontStyle.default_title()
            elif self.current_style_key == 'composer':
                self.current_style = FontStyle.default_composer()
            elif self.current_style_key == 'lyric':
                self.current_style = FontStyle.default_lyric()
            elif self.current_style_key == 'dynamic':
                self.current_style = FontStyle.default_dynamic()
            elif self.current_style_key == 'annotation':
                self.current_style = FontStyle.default_annotation()
            
            self._load_style_to_editor()
            self.font_manager.notify_observers()


# Example usage
if __name__ == '__main__':
    root = tk.Tk()
    root.title("Font Styles Manager - Test")
    root.geometry("400x300")
    root.configure(bg=DARK)
    
    manager = FontStylesManager(root)
    
    def open_dialog():
        dialog = FontStylesDialog(root, manager)
        root.wait_window(dialog)
    
    tk.Button(root, text="Open Font Styles Manager", command=open_dialog,
              bg=ACCENT, fg=WHITE, font=('Arial', 12)).pack(pady=20)
    
    tk.Label(root, text="Font Styles Manager Module\nv1.0",
             bg=DARK, fg=GOLD, font=('Arial', 12)).pack(pady=20)
    
    root.mainloop()
