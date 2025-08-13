#!/usr/bin/env python
import argparse, json
from pathlib import Path
import numpy as np
from Bio.PDB import PDBParser

def read_plddt(pdb_path: str):
    parser = PDBParser(QUIET=True)
    struct = parser.get_structure('m', pdb_path)
    out = []
    for model in struct:
        for chain in model:
            for res in chain:
                if res.id[0] != ' ':
                    continue
                bs = [atom.get_bfactor() for atom in res.get_atoms()]
                if bs:
                    out.append((chain.id, res.id[1], float(np.mean(bs))))
    return out

def count_clashes(pdb_path: str, cutoff: float = 2.1) -> int:
    parser = PDBParser(QUIET=True)
    struct = parser.get_structure('m', pdb_path)
    atoms = [a for a in struct.get_atoms() if a.element != 'H']
    coords = np.array([a.coord for a in atoms], dtype=float)
    n = len(atoms)
    if n == 0: return 0
    diffs = coords[:, None, :] - coords[None, :, :]
    d2 = np.sum(diffs * diffs, axis=2)
    iu = np.triu_indices(n, k=1)
    dists = np.sqrt(d2[iu])
    clashes = 0
    for (i, j), d in zip(zip(iu[0], iu[1]), dists):
        if d < cutoff:
            r_i = atoms[i].get_parent(); r_j = atoms[j].get_parent()
            if r_i == r_j: continue
            clashes += 1
    return clashes

def write_report(outdir: Path, plddt_stats, pae_stats, clashes):
    outdir.mkdir(parents=True, exist_ok=True)
    arr = np.array([x[2] for x in plddt_stats], dtype=float)
    lines = []
    lines.append("=== Quality Report ===")
    lines.append(f"pLDDT: mean={arr.mean():.2f}, median={np.median(arr):.2f}, min={arr.min():.2f}, max={arr.max():.2f}")
    if pae_stats is not None:
        lines.append(f"PAE:   mean={float(np.mean(pae_stats)):.2f} (lower is better)")
    lines.append(f"Clashes (heavy atom, <2.1Å, inter-residue): {clashes}")
    (outdir / 'report.txt').write_text('\n'.join(lines) + '\n')
    with open(outdir / 'plddt_per_residue.csv', 'w') as f:
        f.write('chain,resnum,plddt\n')
        for ch, rn, v in plddt_stats:
            f.write(f"{ch},{rn},{v:.2f}\n")
    if pae_stats is not None:
        np.savetxt(outdir / 'pae_mean.txt', np.array([np.mean(pae_stats)]), fmt='%.3f')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pdb', required=True)
    ap.add_argument('--pae', default=None)
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()
    plddt_stats = read_plddt(args.pdb)
    pae_stats = None
    if args.pae and Path(args.pae).exists():
        with open(args.pae) as f:
            pae = json.load(f)
        if isinstance(pae, dict) and 'pae' in pae:
            pae_stats = np.array(pae['pae'], dtype=float)
        elif isinstance(pae, list):
            pae_stats = np.array(pae, dtype=float)
    clashes = count_clashes(args.pdb)
    write_report(Path(args.outdir), plddt_stats, pae_stats, clashes)
    print(f"[OK] Wrote QC report to {args.outdir}")

if __name__ == '__main__':
    main()
