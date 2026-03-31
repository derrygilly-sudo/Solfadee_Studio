#!/usr/bin/env python3
"""
combine_studio.py
─────────────────
Run ONCE to produce solfadee_studio.py from:
  • solfadee_studio_header.py  (the patched import block)
  • solfadee_v5.py             (YOUR original document — renamed/copied here)

Usage:
    python3 combine_studio.py tonic_solfa_studio.py

Output:
    solfadee_studio.py   ← optional integrated/export build
"""
import sys, os, ast

def main():
    if len(sys.argv) < 2:
        # Try auto-detect
        candidates = [f for f in os.listdir('.') if f.endswith('.py')
                      and 'solfa' in f.lower() and 'studio' not in f.lower()
                      and 'canvas' not in f.lower() and 'fixes' not in f.lower()
                      and 'bridge' not in f.lower() and 'engine' not in f.lower()
                      and 'exporter' not in f.lower() and 'renderer' not in f.lower()
                      and 'manager' not in f.lower() and 'style' not in f.lower()
                      and 'combine' not in f.lower()]
        if candidates:
            original = candidates[0]
            print(f"Auto-detected original file: {original}")
        else:
            print("Usage: python3 combine_studio.py <original_solfadee_v5.py>")
            sys.exit(1)
    else:
        original = sys.argv[1]

    header_file = "solfadee_studio_header.py"
    output_file = "solfadee_studio.py"

    if not os.path.exists(original):
        fallback_candidates = [
            "tonic_solfa_studio.py",
            "tonic_solfa_studio_v5.py",
            "solfadee_studio_v5.py",
        ]
        if original == "solfadee_v5.py":
            for candidate in fallback_candidates:
                if os.path.exists(candidate):
                    print(f"WARNING: {original} not found. Using {candidate} instead.")
                    original = candidate
                    break

    if not os.path.exists(original):
        print(f"ERROR: {original} not found.")
        sys.exit(1)
    if not os.path.exists(header_file):
        print(f"ERROR: {header_file} not found. Must be in same folder.")
        sys.exit(1)

    with open(header_file, encoding="utf-8") as f:
        header = f.read().rstrip("\n") + "\n\n"

    with open(original, encoding="utf-8") as f:
        original_text = f.read()

    # ── Find the body cut-point ────────────────────────────────────────────
    # Search for "OPTIONAL LIBRARIES" section — everything from there onward
    # is preserved verbatim.
    CUT_MARKERS = [
        "OPTIONAL LIBRARIES",
        "try:\n    from midiutil",
        "try:\n    from reportlab",
    ]
    cut_idx = -1
    for marker in CUT_MARKERS:
        idx = original_text.find(marker)
        if idx != -1:
            # Walk back to start of preceding comment block (the ═══ line)
            block_start = original_text.rfind("\n#", 0, idx)
            if block_start != -1:
                cut_idx = block_start + 1   # skip the leading newline
            else:
                cut_idx = idx
            break

    if cut_idx == -1:
        print("WARNING: Could not find OPTIONAL LIBRARIES marker.")
        print("         Falling back to cutting after the 'from solfadee_fixes' import line.")
        for line_end_marker in [
            "from solfadee_fixes import",
            "from tonic_solfa_style_engine import",
            "from score_bridge import",
        ]:
            idx = original_text.find(line_end_marker)
            if idx != -1:
                nl = original_text.find("\n", idx)
                cut_idx = nl + 1
                break

    if cut_idx == -1:
        print("ERROR: Could not find any cut-point. Please check the original file.")
        sys.exit(1)

    body = original_text[cut_idx:]

    # ── Combine ────────────────────────────────────────────────────────────
    combined = header + body

    # ── Validate ───────────────────────────────────────────────────────────
    try:
        ast.parse(combined)
        syntax_ok = True
    except SyntaxError as e:
        print(f"WARNING: Combined file has syntax error: {e}")
        syntax_ok = False

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(combined)

    status = "✓ Syntax OK" if syntax_ok else "⚠ Syntax warning (see above)"
    print(f"\n{status}")
    print(f"✓ Written: {output_file}  ({combined.count(chr(10))} lines)")
    print()
    print("Run your app:")
    print(f"  python3 {output_file}")
    print()
    if not syntax_ok:
        print("If syntax error persists, open solfadee_studio.py in VS Code")
        print("and check the line number reported above.")

if __name__ == "__main__":
    main()
