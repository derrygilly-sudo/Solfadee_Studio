#!/usr/bin/env python3
import os, sys
from pathlib import Path
from PIL import Image, ImageChops
import fitz

base = Path(__file__).parent
examples = base / 'examples'
templates = base / 'templates'
out_renders = examples / 'renders'
out_diffs = examples / 'diffs'
for p in (out_renders, out_diffs): p.mkdir(exist_ok=True)

# Render all PDFs in examples/ to PNG (first page only)
pdfs = sorted(examples.glob('*.pdf'))
rendered = {}
for pdf in pdfs:
    try:
        doc = fitz.open(str(pdf))
        page = doc.load_page(0)
        mat = fitz.Matrix(2,2)  # render at 2x
        pix = page.get_pixmap(matrix=mat, alpha=False)
        out_png = out_renders / (pdf.stem + '.png')
        pix.save(str(out_png))
        rendered[pdf.stem] = out_png
        print('Rendered', pdf.name, '->', out_png.name)
    except Exception as e:
        print('Render failed for', pdf.name, type(e).__name__, e)

# Attempt to find matching template image for each rendered PDF by stem matching
img_exts = ['.png','.jpg','.jpeg','.webp']
for stem, png in rendered.items():
    # derive candidate template names
    name = stem
    if name.startswith('reg_'):
        cand = name[4:]
    elif name.startswith('sample'):
        cand = 'sample'
    else:
        cand = name
    # try exact match (case-insensitive)
    found = None
    for t in templates.iterdir():
        if t.is_file() and t.suffix.lower() in img_exts:
            if t.stem.lower() == cand.lower():
                found = t; break
    if not found:
        # relax: look for any image whose stem appears in cand or vice versa
        for t in templates.iterdir():
            if t.is_file() and t.suffix.lower() in img_exts:
                if t.stem.lower() in cand.lower() or cand.lower() in t.stem.lower():
                    found = t; break
    if not found:
        print('No template image match for', stem)
        continue
    # open both and resize to same size
    a = Image.open(png).convert('RGBA')
    b = Image.open(found).convert('RGBA')
    # Resize template to match render (maintain aspect ratio by fit within)
    if b.size != a.size:
        b = b.resize(a.size, Image.LANCZOS)
    diff = ImageChops.difference(a, b)
    bbox = diff.getbbox()
    out_diff = out_diffs / (stem + '_diff.png')
    diff.save(out_diff)
    print('Diff for', stem, 'saved to', out_diff.name, 'bbox:', bbox)

print('\nDone. Rendered images:', len(rendered))
print('Renders in', out_renders)
print('Diffs in', out_diffs)
