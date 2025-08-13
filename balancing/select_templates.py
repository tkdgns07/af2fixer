#!/usr/bin/env python
import argparse, re, sys, json
from pathlib import Path

def parse_hhr(path: str, top: int):
    hits = []
    # crude HHR parser: look for lines starting with "No " and following "Probab", "E-value", "PDB", "Aligned_cols"
    pat = re.compile(r'^\s*No\s+(\d+)\s+')
    current = None
    with open(path, 'r') as f:
        for line in f:
            if line.startswith("No "):
                m = pat.match(line)
                if m:
                    if current: hits.append(current)
                    current = {"rank": int(m.group(1)), "raw": line.strip()}
            elif current and line.strip().startswith("Probab="):
                # example: Probab=99.4  E-value=1.7e-31  Score=218.12  Aligned_cols=276  ...
                current["probab"] = line.strip()
            elif current and line.strip().startswith("Template"):
                # Template  1XYZ_A  <desc...>
                toks = line.strip().split()
                if len(toks) >= 2:
                    current["template"] = toks[1]
        if current: hits.append(current)
    hits.sort(key=lambda x: x["rank"])
    return hits[:top]

def main():
    ap = argparse.ArgumentParser(description="Select top-N HHsearch templates and emit a JSON list.")
    ap.add_argument('--hhr', required=True)
    ap.add_argument('--top', type=int, default=5)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    hits = parse_hhr(args.hhr, args.top)
    out = {"templates": hits}
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"[OK] Wrote template list -> {args.out}")

if __name__ == '__main__':
    main()
