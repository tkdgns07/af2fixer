import argparse, subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

def run(cmd):
    print("[RUN]", " ".join(cmd))
    subprocess.run(cmd, check=True)

def cmd_demo(args):
    script = BASE / "scripts" / "demo_random_gap.sh"
    run(["bash", str(script), args.pdb_id, args.chain, str(args.flank)])

def cmd_prep(args):
    run(["python", str(BASE/"preprocessing"/"pdb_to_mmcif_and_renumber.py"),
         "-i", args.template, "-o", args.out+"/template_clean.cif", "--drop-altloc"])
    run(["python", str(BASE/"preprocessing"/"mask_template.py"),
         "-i", args.out+"/template_clean.cif", "-o", args.out+"/template_masked.cif", "--ranges", args.ranges])
    run(["python", str(BASE/"scripts"/"pdb_to_fasta.py"),
         "-i", args.out+"/template_clean.cif", "-o", args.out+"/full.fasta", "--chains", args.chain])
    run(["python", str(BASE/"preprocessing"/"make_window_fasta.py"),
         "-i", args.out+"/full.fasta", "-o", args.out+"/windows.fasta",
         "--sites", args.sites, "--flank", str(args.flank)])

def cmd_hhsearch(args):
    run(["python", str(BASE/"balancing"/"run_hhsearch.py"),
         "--fasta", args.fasta, "--db-uniref", args.db_uniref, "--db-pdb", args.db_pdb,
         "--out", args.out, "--threads", str(args.threads)])
    run(["python", str(BASE/"balancing"/"select_templates.py"),
         "--hhr", args.out+"/pdb_hits.hhr", "--top", str(args.top), "--out", args.out+"/templates.json"])

def cmd_af2(args):
    cmd = ["python", str(BASE/"colabfold"/"run_af2.py"),
           "--fasta", args.fasta, "--out", args.out, "--model-type", args.model_type,
           "--recycles", str(args.recycles), "--num-models", str(args.num_models)]
    if args.use_templates: cmd.append("--use-templates")
    if args.gpu_relax: cmd.append("--gpu-relax")
    run(cmd)

def cmd_graft(args):
    cmd = ["python", str(BASE/"postprocessing"/"graft_and_minimize.py"),
           "--template", args.template, "--pred", args.pred, "--output", args.out, "--map", args.map]
    if args.minimize: cmd.append("--minimize")
    cmd += ["--platform", args.platform]
    run(cmd)

def cmd_qc(args):
    cmd = ["python", str(BASE/"postprocessing"/"quality_check.py"),
           "--pdb", args.pdb, "--outdir", args.outdir]
    if args.pae: cmd += ["--pae", args.pae]
    run(cmd)

def main():
    p = argparse.ArgumentParser(prog="af2fixer", description="AF2 fixer pipeline CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("demo", help="Quick demo: download PDB, make random gap, prepare inputs")
    s.add_argument("pdb_id")
    s.add_argument("--chain", default="A")
    s.add_argument("--flank", type=int, default=25)
    s.set_defaults(func=cmd_demo)

    s = sub.add_parser("prep", help="Preprocess template & make window FASTA")
    s.add_argument("--template", required=True)
    s.add_argument("--chain", required=True)
    s.add_argument("--ranges", required=True, help="e.g. A:100-120")
    s.add_argument("--sites", required=True, help="e.g. 110")
    s.add_argument("--flank", type=int, default=25)
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_prep)

    s = sub.add_parser("hhsearch", help="Run HHblits->HHsearch and select templates")
    s.add_argument("--fasta", required=True)
    s.add_argument("--db-uniref", required=True)
    s.add_argument("--db-pdb", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--threads", type=int, default=4)
    s.add_argument("--top", type=int, default=5)
    s.set_defaults(func=cmd_hhsearch)

    s = sub.add_parser("af2", help="Run ColabFold")
    s.add_argument("--fasta", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--model-type", default="alphafold2_ptm")
    s.add_argument("--recycles", type=int, default=3)
    s.add_argument("--num-models", type=int, default=5)
    s.add_argument("--use-templates", action="store_true")
    s.add_argument("--gpu-relax", action="store_true")
    s.set_defaults(func=cmd_af2)

    s = sub.add_parser("graft", help="Graft predicted loop into template (optionally minimize)")
    s.add_argument("--template", required=True)
    s.add_argument("--pred", required=True)
    s.add_argument("--map", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--minimize", action="store_true")
    s.add_argument("--platform", default="CPU")
    s.set_defaults(func=cmd_graft)

    s = sub.add_parser("qc", help="Quality check")
    s.add_argument("--pdb", required=True)
    s.add_argument("--pae", default=None)
    s.add_argument("--outdir", required=True)
    s.set_defaults(func=cmd_qc)

    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
