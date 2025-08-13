#!/usr/bin/env python
import argparse, random
import gemmi as gm

def polymer_resnums(struct, chain_id):
    resnums = []
    for res in struct[0][chain_id]:
        if res.is_polymer():
            resnums.append(res.seqid.num)
    return resnums

def main():
    ap = argparse.ArgumentParser(description="Pick a random contiguous deletion range on a chain.")
    ap.add_argument("--input", required=True, help="PDB/mmCIF (renumbered 권장)")
    ap.add_argument("--chain", default="A")
    ap.add_argument("--minlen", type=int, default=8)
    ap.add_argument("--maxlen", type=int, default=20)
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    st = gm.read_structure(args.input)
    resnums = polymer_resnums(st, args.chain)
    if len(resnums) == 0:
        raise SystemExit("No polymer residues on chain")

    L = random.randint(args.minlen, args.maxlen)
    start_min = resnums[0]
    start_max = resnums[-1] - L + 1
    if start_max < start_min:
        raise SystemExit("Chain too short for requested gap length")

    start = random.randint(start_min, start_max)
    end = start + L - 1
    center = (start + end)//2

    print(f"RANGE={args.chain}:{start}-{end}")
    print(f"SITES={center}")
    print(f"LENGTH={L}")

if __name__ == "__main__":
    main()
