#!/usr/bin/env python
import argparse, sys
from typing import List, Tuple
import gemmi as gm

def parse_ranges(ranges_str: str) -> List[Tuple[str, int, int]]:
    out = []
    for token in ranges_str.split(','):
        token = token.strip()
        if not token: continue
        chain, span = token.split(':')
        a, b = span.split('-')
        out.append((chain, int(a), int(b)))
    return out

def in_any_range(chain_id: str, resnum: int, ranges: List[Tuple[str, int, int]]) -> bool:
    for cid, a, b in ranges:
        if chain_id == cid and a <= resnum <= b:
            return True
    return False

def mask(struct: gm.Structure, ranges: List[Tuple[str, int, int]]):
    for model in struct:
        for chain in list(model):
            for residue in list(chain):
                if residue.is_polymer():
                    rn = residue.seqid.num
                    if in_any_range(chain.name, rn, ranges):
                        chain.remove_residue(residue)
    struct.remove_empty_chains()

def main():
    ap = argparse.ArgumentParser(description="Remove residue ranges from template mmCIF.")
    ap.add_argument('-i', '--input', required=True)
    ap.add_argument('-o', '--output', required=True)
    ap.add_argument('--ranges', required=True, help='Comma-separated ranges like A:45-60,B:10-20')
    args = ap.parse_args()

    try:
        struct = gm.read_structure(args.input)
    except Exception as e:
        print(f"[ERROR] read_structure: {e}", file=sys.stderr)
        sys.exit(1)

    ranges = parse_ranges(args.ranges)
    mask(struct, ranges)

    doc = struct.make_mmcif_document()
    with open(args.output, 'w') as f:
        f.write(doc.as_string())
    print(f"[OK] Wrote masked template -> {args.output}")

if __name__ == '__main__':
    main()
