#!/usr/bin/env python
import argparse
import gemmi as gm
aa3_to1 = gm.util.one_letter_codes

def seq_from_chain(chain):
    s = []
    for res in chain:
        if res.is_polymer() and res.name in aa3_to1:
            s.append(aa3_to1[res.name])
    return "".join(s)

def main():
    ap = argparse.ArgumentParser(description="Extract FASTA from PDB/mmCIF.")
    ap.add_argument("-i", "--input", required=True)
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--chains", default=None, help="Comma-separated chain IDs (default: all)")
    args = ap.parse_args()

    st = gm.read_structure(args.input)
    st.remove_empty_chains()
    chains_sel = None if not args.chains else set(x.strip() for x in args.chains.split(","))

    with open(args.output, "w") as f:
        for ch in st[0]:
            if chains_sel and ch.name not in chains_sel:
                continue
            seq = seq_from_chain(ch)
            if not seq:
                continue
            f.write(f">{ch.name}\n")
            for i in range(0, len(seq), 80):
                f.write(seq[i:i+80] + "\n")

if __name__ == "__main__":
    main()
