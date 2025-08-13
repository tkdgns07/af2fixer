#!/usr/bin/env python
import argparse, shutil, subprocess, sys
from pathlib import Path

def check_binary(cmd: str):
    if shutil.which(cmd) is None:
        print(f"[ERROR] '{cmd}' not found in PATH. Install ColabFold (pip).", file=sys.stderr)
        sys.exit(1)

def main():
    ap = argparse.ArgumentParser(description="Thin wrapper for colabfold_batch.")
    ap.add_argument('--fasta', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--model-type', default='alphafold2_ptm')
    ap.add_argument('--recycles', type=int, default=3)
    ap.add_argument('--use-templates', action='store_true')
    ap.add_argument('--gpu-relax', action='store_true')
    ap.add_argument('--num-models', type=int, default=5)
    args = ap.parse_args()

    check_binary('colabfold_batch')
    outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)

    cmd = [
        'colabfold_batch',
        '--model-type', args.model_type,
        '--num-recycle', str(args.recycles),
        '--num-models', str(args.num_models)
    ]
    if args.use_templates:
        cmd += ['--use-templates']
    if args.gpu_relax:
        cmd += ['--use-gpu-relax']

    cmd += [args.fasta, str(outdir)]
    print('[RUN]', ' '.join(cmd))
    subprocess.run(cmd, check=True)
    print(f"[OK] ColabFold outputs in: {outdir}")

if __name__ == '__main__':
    main()
