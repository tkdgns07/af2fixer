#!/usr/bin/env python
import argparse, shutil, subprocess, sys
from pathlib import Path

def need(cmd: str):
    if shutil.which(cmd) is None:
        print(f"[ERROR] Missing binary: {cmd}. Install hhsuite (hhblits/hhsearch).", file=sys.stderr)
        sys.exit(1)

def main():
    ap = argparse.ArgumentParser(description="Run HHblits -> HHsearch pipeline.")
    ap.add_argument('--fasta', required=True)
    ap.add_argument('--db-uniref', required=True, help='Path to uniclust30/UniRef db (HHblits)')
    ap.add_argument('--db-pdb', required=True, help='Path to pdb70/pdb100 HHsearch db (HHSuite)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--threads', type=int, default=4)
    args = ap.parse_args()

    need('hhblits'); need('hhsearch')

    outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
    a3m = outdir / "query.a3m"
    hhr = outdir / "pdb_hits.hhr"

    # HHblits to build MSA
    cmd1 = [
        "hhblits",
        "-i", args.fasta,
        "-oa3m", str(a3m),
        "-d", args.db_uniref,
        "-cpu", str(args.threads),
        "-n", "3"
    ]
    print("[RUN]", " ".join(cmd1)); subprocess.run(cmd1, check=True)

    # HHsearch against PDB db
    cmd2 = [
        "hhsearch",
        "-i", str(a3m),
        "-d", args.db_pdb,
        "-o", str(hhr),
        "-cpu", str(args.threads)
    ]
    print("[RUN]", " ".join(cmd2)); subprocess.run(cmd2, check=True)

    print(f"[OK] Wrote {hhr}")

if __name__ == '__main__':
    main()
