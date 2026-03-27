#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tonic Solfa Template Integration Module
Provides template image loading and staff configuration options
"""

import tkinter as tk
from tkinter import ttk
import os
from PIL import Image, ImageTk

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


class TemplateIntegrationPanel(tk.Frame):
    """Panel for displaying and selecting from template configurations."""
    
    def __init__(self, master, template_dir, on_template_select=None, **kwargs):
        super().__init__(master, bg=PANEL, **kwargs)
        self.template_dir = template_dir
        self.on_template_select = on_template_select
        self._build_ui()
    
    def _build_ui(self):
        """Build the template selection UI."""
        # Title
        title_frame = tk.Frame(self, bg=CARD)
        title_frame.pack(fill='x')
        tk.Label(title_frame, text="Staff Configuration Templates",
                bg=CARD, fg=GOLD, font=('Arial', 11, 'bold')).pack(padx=10, pady=8)
        
        # Try to load and display template image
        template_img_path = os.path.join(self.template_dir, 'images.jpg')
        if os.path.exists(template_img_path):
            try:
                img = Image.open(template_img_path)
                # Resize to fit panel
                max_width = 280
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                
                self.photo = ImageTk.PhotoImage(img)
                img_label = tk.Label(self, image=self.photo, bg=DARK, relief='sunken', bd=1)
                img_label.pack(pady=10, padx=10, fill='x')
                
                tk.Label(self, text="📊 Tonic Solfa Chart",
                        bg=CARD, fg=MUTED, font=('Arial', 8)).pack()
            except Exception as e:
                print(f"Could not display template image: {e}")
        
        # Staff type buttons
        style_frame = tk.Frame(self, bg=PANEL)
        style_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(style_frame, text="Select Staff Type:",
                bg=PANEL, fg=MUTED, font=('Arial', 9)).pack(anchor='w', pady=(0, 5))
        
        staff_types = [
            ("Single Staff", "single", "Solo/Melody"),
            ("Piano (2 Staves)", "piano", "Treble & Bass"),
            ("SATB (4 Staves)", "satb", "Choir/Harmony"),
        ]
        
        for label, value, desc in staff_types:
            btn_frame = tk.Frame(style_frame, bg=CARD, relief='raised', bd=1)
            btn_frame.pack(fill='x', pady=3)
            
            btn = tk.Button(btn_frame, text=f"{label}: {desc}",
                           bg=CARD, fg=TEXT, activebackground=ACCENT,
                           activeforeground=WHITE, relief='flat',
                           font=('Arial', 9),
                           command=lambda v=value: self._on_template_select(v))
            btn.pack(fill='x', padx=10, pady=8)
        
        # Description
        desc_frame = tk.Frame(self, bg=DARK, relief='sunken', bd=1)
        desc_frame.pack(fill='x', padx=10, pady=10)
        
        desc_text = (
            "• Single: Best for melody lines\n"
            "• Piano: Ideal for piano/keyboard\n"
            "• SATB: Perfect for vocal harmony"
        )
        tk.Label(desc_frame, text=desc_text,
                bg=DARK, fg=MUTED, font=('Arial', 8),
                justify='left').pack(anchor='w', padx=8, pady=8)
    
    def _on_template_select(self, template_type):
        """Handle template selection."""
        if self.on_template_select:
            self.on_template_select(template_type)


class TonicSolfaReferenceDisplay(tk.Toplevel):
    """Display window for Tonic Solfa reference with template image."""
    
    def __init__(self, parent, template_dir, **kwargs):
        super().__init__(parent, **kwargs)
        self.title("Tonic Solfa Reference")
        self.geometry("700x800")
        self.configure(bg=DARK)
        self.template_dir = template_dir
        
        self._build_display()
    
    def _build_display(self):
        """Build the reference display."""
        # Title
        tk.Label(self, text="Tonic Solfa Reference System",
                bg=DARK, fg=GOLD, font=('Georgia', 14, 'bold')).pack(pady=10)
        
        # Scrollable frame
        canvas_frame = tk.Frame(self, bg=DARK)
        canvas_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        canvas = tk.Canvas(canvas_frame, bg=DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical', command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=DARK)
        
        scrollable.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )
        
        canvas.create_window((0, 0), window=scrollable, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Load template image
        template_img_path = os.path.join(self.template_dir, 'images.jpg')
        if os.path.exists(template_img_path):
            try:
                img = Image.open(template_img_path)
                # Make it larger for display
                max_width = 650
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                
                self.photo = ImageTk.PhotoImage(img)
                img_label = tk.Label(scrollable, image=self.photo, bg=DARK)
                img_label.pack(pady=10)
            except Exception as e:
                tk.Label(scrollable, text=f"Could not load image: {e}",
                        bg=DARK, fg=TEXT).pack()
        
        # Description
        desc = tk.Label(scrollable, text=(
            "Official Tonic Solfa Notation Chart\n\n"
            "DO RE MI FA SOL LA TI\n"
            "d    r      m    f     s      l      t\n\n"
            "Use these syllables to annotate music in Tonic Solfa system.\n"
            "For each key, adjust the starting note accordingly."
        ), bg=DARK, fg=TEXT, font=('Arial', 10), justify='center')
        desc.pack(pady=20)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Close button
        tk.Button(self, text="Close", bg=ACCENT, fg=WHITE, relief='flat',
                 command=self.destroy).pack(pady=10)
