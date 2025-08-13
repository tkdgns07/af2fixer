#!/usr/bin/env python
import argparse, sys
import gemmi as gm

def drop_altlocs(struct: gm.Structure, keep=("", "A")):
    for model in struct:
        for chain in model:
            for residue in chain:
                atoms_to_keep = []
                for atom in residue:
                    if atom.altloc in keep:
                        atom.altloc = ""
                        atoms_to_keep.append(atom)
                residue.clear()
                for a in atoms_to_keep:
                    residue.add_atom(a)

def renumber_residues(struct: gm.Structure, start_at: int = 1):
    for model in struct:
        for chain in model:
            n = start_at
            for residue in chain:
                if residue.is_polymer():
                    residue.seqid.icode = ""
                    residue.seqid.num = n
                    n += 1

def write_mmcif(struct: gm.Structure, out_path: str):
    doc = struct.make_mmcif_document()
    with open(out_path, 'w') as f:
        f.write(doc.as_string())

def main():
    ap = argparse.ArgumentParser(description="PDB/mmCIF -> clean mmCIF with per-chain renumbering")
    ap.add_argument('-i', '--input', required=True)
    ap.add_argument('-o', '--output', required=True)
    ap.add_argument('--drop-altloc', action='store_true')
    ap.add_argument('--start', type=int, default=1)
    args = ap.parse_args()

    try:
        struct = gm.read_structure(args.input)
    except Exception as e:
        print(f"[ERROR] Failed to read structure: {e}", file=sys.stderr)
        sys.exit(1)

    struct.remove_empty_chains()
    struct.remove_ligands_and_waters()

    if args.drop_altloc:
        drop_altlocs(struct)

    renumber_residues(struct, start_at=args.start)

    try:
        write_mmcif(struct, args.output)
    except Exception as e:
        print(f"[ERROR] Failed to write mmCIF: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[OK] Wrote renumbered mmCIF -> {args.output}")

if __name__ == '__main__':
    main()
