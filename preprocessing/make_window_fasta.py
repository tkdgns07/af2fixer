#!/usr/bin/env python
import argparse
from typing import List
from Bio import SeqIO

def extract_windows(seq: str, sites: List[int], flank: int):
    out = []
    n = len(seq)
    for pos in sites:
        start = max(1, pos - flank)
        end = min(n, pos + flank)
        window = seq[start-1:end]
        out.append((pos, start, end, window))
    return out

def main():
    ap = argparse.ArgumentParser(description="Create ±flank windows around deletion sites from a full FASTA.")
    ap.add_argument('-i', '--input', required=True)
    ap.add_argument('-o', '--output', required=True)
    ap.add_argument('--sites', required=True, help='Comma separated 1-based positions, e.g., 45,120')
    ap.add_argument('--flank', type=int, default=25)
    args = ap.parse_args()

    from Bio import SeqIO
    records = list(SeqIO.parse(args.input, 'fasta'))
    if len(records) != 1:
        raise SystemExit('[ERROR] Expect single-sequence FASTA')

    seq = str(records[0].seq).replace('\n', '').strip()
    sites = [int(x) for x in args.sites.split(',') if x.strip()]
    windows = extract_windows(seq, sites, args.flank)

    with open(args.output, 'w') as f:
        for pos, s, e, w in windows:
            f.write(f">win_pos{pos}_range{s}-{e}\n")
            for i in range(0, len(w), 80):
                f.write(w[i:i+80] + "\n")

    print(f"[OK] Wrote {len(windows)} windows -> {args.output}")

if __name__ == '__main__':
    main()
