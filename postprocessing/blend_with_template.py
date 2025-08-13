#!/usr/bin/env python
import argparse
from typing import List, Tuple
import gemmi as gm

def parse_map(map_str: str) -> List[Tuple[str, int, int]]:
    out = []
    for token in map_str.split(','):
        token = token.strip()
        if not token: continue
        chain, span = token.split(':')
        a, b = [int(x) for x in span.split('-')]
        out.append((chain, a, b))
    return out

def blend_coords(template: gm.Structure, pred: gm.Structure, ranges, alpha: float):
    t_model, p_model = template[0], pred[0]
    pred_residues = []
    for ch in p_model:
        for res in ch:
            if res.is_polymer(): pred_residues.append(res)
    for chain_name, a, b in ranges:
        t_chain = t_model[chain_name]
        for i, t_resnum in enumerate(range(a, b+1), start=1):
            p_idx = i
            if not (1 <= p_idx <= len(pred_residues)): break
            p_res = pred_residues[p_idx-1]
            t_res = None
            for r in t_chain:
                if r.is_polymer() and r.seqid.num == t_resnum:
                    t_res = r; break
            if t_res is None: continue
            p_atoms = {a.name.strip(): a for a in p_res}
            for t_atom in t_res:
                nm = t_atom.name.strip()
                if nm in p_atoms:
                    tp = t_atom.pos; pp = p_atoms[nm].pos
                    t_atom.pos = gm.Position(
                        (1-alpha)*tp.x + alpha*pp.x,
                        (1-alpha)*tp.y + alpha*pp.y,
                        (1-alpha)*tp.z + alpha*pp.z,
                    )

def main():
    ap = argparse.ArgumentParser(description="Blend coordinates of template and predicted structures in given ranges.")
    ap.add_argument('--template', required=True, help='Template PDB/mmCIF')
    ap.add_argument('--pred', required=True, help='Predicted PDB')
    ap.add_argument('--out', required=True, help='Output blended PDB')
    ap.add_argument('--ranges', required=True, help='e.g., A:100-130[,B:50-60]')
    ap.add_argument('--alpha', type=float, default=0.3, help='Weight of predicted coords (0..1)')
    args = ap.parse_args()

    t = gm.read_structure(args.template)
    p = gm.read_structure(args.pred)
    ranges = parse_map(args.ranges)
    blend_coords(t, p, ranges, args.alpha)
    with gm.PdbWriter(args.out) as w:
        w.write_structure(t)
    print(f"[OK] Wrote blended PDB -> {args.out}")

if __name__ == '__main__':
    main()
