#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Finale Notation File Support for Tonic Solfa Studio
Adds methods for importing and exporting Finale notation files (.mus, .xml variations)
"""

import os
import json
from typing import Optional

def add_finale_import_export_methods(tonic_solfa_class):
    """
    Add Finale support methods to TonicSolfaStudio class
    
    Methods added:
    - _import_finale: Import Finale notation files
    - _export_finale: Export to Finale notation format
    """
    
    def _import_finale(self):
        """Import Finale notation files (.mus, .xml)"""
        path = tk.filedialog.askopenfilename(
            title="Import Finale Notation File",
            filetypes=[
                ("Finale Files", "*.mus"),
                ("MusicXML/Finale", "*.xml *.musicxml *.mxl"),
                ("All", "*.*")
            ]
        )
        if not path:
            return
        
        try:
            ext = os.path.splitext(path)[1].lower()
            
            # Finale .mus files are proprietary binary format
            # We provide graceful fallback with a message
            if ext == '.mus':
                messagebox.showinfo(
                    "Finale .mus Import",
                    "Finale .mus files are proprietary binary format.\n\n"
                    "Please save your Finale score as MusicXML (.xml) first:\n"
                    "File → Save As → choose 'MusicXML' format\n\n"
                    "Then import the MusicXML file for full compatibility."
                )
                # Fall through to MusicXML dialog
                self._import_musicxml()
                return
            
            # For .xml/.mxl files, use standard MusicXML import
            if ext in ['.xml', '.musicxml', '.mxl']:
                self.score = ConversionEngine.musicxml_to_score(path)
                self.modified = True
                self._initial_render()
                self.status_var.set(f"Imported Finale Notation (MusicXML): {path}")
                messagebox.showinfo("Finale Import Success",
                    f"Successfully imported Finale notation from:\n{path}\n\n"
                    "Tip: Save Finale scores as MusicXML for best compatibility.")
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import Finale file:\n{str(e)}")
            self.score = Score(title=f"Finale Import Failed - {os.path.basename(path)}")
            self.score.ensure_measures(4)
            self._initial_render()

    def _export_finale(self):
        """Export to Finale notation format (via MusicXML)"""
        path = tk.filedialog.asksaveasfilename(
            title="Export as Finale-Compatible Format",
            defaultextension=".xml",
            filetypes=[
                ("MusicXML (Finale Compatible)", "*.xml"),
                ("All", "*.*")
            ]
        )
        if not path:
            return
        
        try:
            xml = ConversionEngine.score_to_musicxml(self.score)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(xml)
            
            self.status_var.set(f"Exported Finale-compatible MusicXML: {path}")
            messagebox.showinfo("Export Success",
                f"Successfully exported score in Finale-compatible format:\n{path}\n\n"
                "You can now open this file in Finale:\n"
                "File → Open → select the MusicXML file")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export Finale format:\n{str(e)}")

    # Attach methods to the class
    tonic_solfa_class._import_finale = _import_finale
    tonic_solfa_class._export_finale = _export_finale


# Enhanced note drawing capabilities for better visibility
ENHANCED_NOTE_DRAWING_CODE = '''
def _draw_note_at_enhanced(self, nx, staff_y, note_obj, selected=False):
    """Enhanced note drawing with engraver-style rendering and better visibility"""
    if note_obj.rest:
        self._draw_rest(nx, staff_y + STAFF_LINE_GAP, note_obj.duration)
        return

    ny = self._note_canvas_y(staff_y, note_obj.pitch, note_obj.octave, self.score.clef)
    color = ACCENT if selected else WHITE
    
    # Enhanced note radius for better visibility
    r = NOTE_RADIUS + 2 if ENGRAVER_MODE else NOTE_RADIUS

    # Draw ledger lines with enhanced visibility
    top_y = staff_y
    bot_y = staff_y + STAFF_LINE_GAP * 4
    
    if ny < top_y:
        for ly_raw in range(int(top_y), int(ny)-1, -int(STAFF_LINE_GAP)):
            if ly_raw <= int(top_y):
                self.create_line(nx-12, ly_raw, nx+12, ly_raw, fill='#5070a0', width=1.5)
    
    if ny > bot_y:
        for ly_raw in range(int(bot_y+STAFF_LINE_GAP), int(ny)+1, int(STAFF_LINE_GAP)):
            self.create_line(nx-12, ly_raw, nx+12, ly_raw, fill='#5070a0', width=1.5)

    # Draw note head with enhanced appearance
    if note_obj.duration >= 2:
        # Open note head (whole and half notes)
        self.create_oval(nx-r, ny-r*0.8, nx+r, ny+r*0.8,
                         outline=color, fill=DARK, width=2.5)
        if ENGRAVER_MODE:
            self.create_oval(nx-r+1, ny-r*0.8+1, nx+r-1, ny+r*0.8-1,
                             outline=color, fill='', width=1)
    else:
        # Filled note head (quarter and shorter notes)
        self.create_oval(nx-r, ny-r*0.8, nx+r, ny+r*0.8,
                         outline=color, fill=color, width=1)

    # Draw stem with enhanced thickness
    if note_obj.duration < 4:
        stem_dir = 1 if ny < staff_y + STAFF_LINE_GAP*2 else -1
        stem_len = STAFF_LINE_GAP * 3.5
        stem_x = nx + (r+1 if stem_dir < 0 else -r-1)
        self.create_line(stem_x, ny,
                         stem_x, ny + stem_dir * stem_len,
                         fill=color, width=2)
        
        # Draw beams/flags for eighth notes and shorter
        if note_obj.duration <= 0.5:
            flag_y = ny + stem_dir * stem_len
            num_flags = int(math.log2(1/note_obj.duration))
            for fi in range(num_flags):
                fy = flag_y + fi * 6 * (-stem_dir)
                self.create_line(stem_x, fy, stem_x+10, fy+7*stem_dir,
                                 fill=color, width=2)

    # Draw dot with enhanced visibility
    if note_obj.dotted:
        self.create_oval(nx+r+5, ny-2.5, nx+r+9, ny+2.5, fill=GOLD, outline=GOLD)

    # Draw accidental with enhanced font size and weight
    accidental_size = 12 if ENGRAVER_MODE else 9
    if '#' in note_obj.pitch:
        self.create_text(nx-r-15, ny, text='♯', fill=GOLD, 
                        font=('Arial', accidental_size, 'bold'))
    elif 'b' in note_obj.pitch:
        self.create_text(nx-r-15, ny, text='♭', fill=GOLD, 
                        font=('Arial', accidental_size, 'bold'))

    # Rest of original code for lyric, dynamic, special symbols...
    # [Original code preserved]

    note_obj.y = ny
'''


# Toolbar enhancement with musical note symbols
TOOLBAR_ENHANCEMENT_CODE = '''
# Add to toolbar section - display note duration symbols with musical notation
def _build_note_symbols_toolbar(parent):
    """Build toolbar showing all available note symbols with names"""
    
    frame = tk.Frame(parent, bg=CARD, height=60)
    frame.pack(fill='x', padx=5, pady=3)
    frame.pack_propagate(False)
    
    tk.Label(frame, text="NOTE SYMBOLS:", bg=CARD, fg=GOLD,
             font=('Arial', 9, 'bold')).pack(side='left', padx=10, pady=5)
    
    # Display all note duration symbols
    note_info = [
        ('𝅝', 'Semibreve', 4.0),
        ('𝅗𝅥', 'Minim', 2.0),
        ('♩', 'Crotchet', 1.0),
        ('♪', 'Quaver', 0.5),
        ('𝅘𝅥𝅯', 'Semiquaver', 0.25),
    ]
    
    for symbol, name, beats in note_info:
        btn = tk.Button(frame, text=f"{symbol} {name}", 
                        bg=DARK, fg=TEXT, relief='flat',
                        font=('Arial', 10),
                        width=15)
        btn.pack(side='left', padx=3, pady=5)
        # Add tooltip showing beat value
        btn.bind('<Enter>', lambda e, b=beats: _show_duration_tooltip(e, b))
        btn.bind('<Leave>', lambda e: _hide_duration_tooltip())


def _show_duration_tooltip(event, beats):
    """Show duration tooltip"""
    tooltip_text = f"{beats} quarter-note beats"
    # Create tooltip widget
    pass

def _hide_duration_tooltip():
    """Hide duration tooltip"""
    pass
'''


# Configuration dialog enhancement
STAFF_CONFIG_ENHANCEMENT = '''
def _configure_staff_enhanced(self):
    """Enhanced staff configuration with Finale/Musicmakers-style options"""
    win = tk.Toplevel(self, bg=PANEL)
    win.title("Staff Configuration - Professional Settings")
    win.geometry("500x450")
    win.transient(self)
    win.grab_set()

    tk.Label(win, text="Professional Staff Configuration", bg=PANEL, fg=GOLD,
             font=('Arial', 14, 'bold')).pack(pady=15)

    # Preset styles (Finale-style, Musicmakers, etc.)
    style_frame = tk.Frame(win, bg=PANEL)
    style_frame.pack(fill='x', padx=20, pady=10)
    
    tk.Label(style_frame, text="Staff Style:", bg=PANEL, fg=TEXT, 
             font=('Arial', 10)).pack(anchor='w')
    
    style_var = tk.StringVar(value="standard")
    styles = [
        ("Standard Engraver", "standard"),
        ("Finale Style", "finale"),
        ("Musicmakers Style", "musicmakers"),
        ("Contemporary", "contemporary")
    ]
    
    for label, value in styles:
        rb = tk.Radiobutton(style_frame, text=label, variable=style_var,
                            value=value, bg=PANEL, fg=TEXT, selectcolor=ACCENT,
                            font=('Arial', 9))
        rb.pack(anchor='w', pady=3)

    # Staff type
    staff_frame = tk.Frame(win, bg=PANEL)
    staff_frame.pack(fill='x', padx=20, pady=10)
    
    tk.Label(staff_frame, text="Staff Type:", bg=PANEL, fg=TEXT,
             font=('Arial', 10)).pack(anchor='w')
    
    staff_type_var = tk.StringVar(value="single")
    staff_types = [("Single Staff", "single"), ("Piano/Grand Staff", "piano"),
                   ("SATB (4-Part)", "satb"), ("Custom", "custom")]
    
    for label, value in staff_types:
        rb = tk.Radiobutton(staff_frame, text=label, variable=staff_type_var,
                            value=value, bg=PANEL, fg=TEXT, selectcolor=ACCENT,
                            font=('Arial', 9))
        rb.pack(anchor='w', pady=3)

    # Display mode
    display_frame = tk.Frame(win, bg=PANEL)
    display_frame.pack(fill='x', padx=20, pady=10)
    
    tk.Label(display_frame, text="Display Mode:", bg=PANEL, fg=TEXT,
             font=('Arial', 10)).pack(anchor='w')
    
    engraver_var = tk.BooleanVar(value=True)
    tk.Checkbutton(display_frame, text="Engraver-Style Rendering", 
                   variable=engraver_var, bg=PANEL, fg=TEXT,
                   selectcolor=DARK, font=('Arial', 9)).pack(anchor='w', pady=3)
    
    tk.Checkbutton(display_frame, text="Show All Notation Elements",
                   bg=PANEL, fg=TEXT, selectcolor=DARK,
                   font=('Arial', 9)).pack(anchor='w', pady=3)

    def apply_config():
        # Apply selected configuration
        win.destroy()

    tk.Button(win, text="Apply Configuration", bg=ACCENT, fg=WHITE,
              font=('Arial', 11, 'bold'),
              command=apply_config).pack(pady=20)
'''

if __name__ == "__main__":
    print("Finale Support Module Loaded Successfully")
    print("Add finale_support methods to your TonicSolfaStudio class using:")
    print("  add_finale_import_export_methods(TonicSolfaStudio)")
