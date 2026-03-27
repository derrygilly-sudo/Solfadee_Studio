#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inject Finale support methods into tonic_solfa_studio.py
"""

import os

def inject_finale_support():
    filepath = 'tonic_solfa_studio.py'
    
    # Read the file
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find insertion point
    marker = '# ── Edit ops ─────────────────────────────────────────'
    insert_pos = content.find(marker)
    
    if insert_pos == -1:
        print('ERROR: Could not find insertion point')
        return False
    
    # Finale support methods code
    finale_code = '''# ── Finale Notation File Support ──────────────────────
    def _import_finale(self):
        """Import Finale notation files (.mus or MusicXML format)."""
        path = filedialog.askopenfilename(
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
            
            if ext == '.mus':
                resp = messagebox.askyesno(
                    "Finale .mus Import",
                    "Finale .mus files are proprietary format.\\n\\n"
                    "Please export from Finale as MusicXML and import that.\\n\\n"
                    "Select a MusicXML file?"
                )
                if resp:
                    self._import_musicxml()
                return
            
            if ext in ['.xml', '.musicxml', '.mxl']:
                self.score = ConversionEngine.musicxml_to_score(path)
                self.modified = True
                self._initial_render()
                self.status_var.set(f"Imported Finale Notation: {os.path.basename(path)}")
                messagebox.showinfo("Finale Import Success",
                    f"Successfully imported Finale notation!\\n{os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import: {str(e)}")
            self.score = Score(title=f"Finale Import - {os.path.basename(path)}")
            self.score.ensure_measures(4)
            self._initial_render()

    def _export_finale(self):
        """Export score in Finale-compatible MusicXML format."""
        path = filedialog.asksaveasfilename(
            title="Export as Finale-Compatible Format",
            defaultextension=".xml",
            filetypes=[
                ("MusicXML (Finale Compatible)", "*.xml"),
                ("MusicXML", "*.musicxml"),
            ]
        )
        if not path:
            return
        
        try:
            xml = ConversionEngine.score_to_musicxml(self.score)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(xml)
            self.status_var.set(f"Exported Finale format: {os.path.basename(path)}")
            messagebox.showinfo("Export Success",
                f"Score exported for Finale!\\n{os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {str(e)}")

    '''
    
    # Insert the code
    new_content = content[:insert_pos] + finale_code + '\n    ' + content[insert_pos:]
    
    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print('✓ SUCCESS: Finale support methods injected!')
    return True

if __name__ == '__main__':
    os.chdir(r'c:\Users\HP\Documents\TONIC SOLFA SOFTWARE')
    inject_finale_support()
