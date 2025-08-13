import argparse, subprocess, sys, os
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

def run(cmd, env=None):
    print("[RUN]", " ".join(cmd))
    subprocess.run(cmd, check=True, env=env)

def find_rank1_pdb(outdir: Path):
    cands = sorted(outdir.glob("*rank_001*.pdb"))
    return cands[0] if cands else None

def cmd_demo(args):
    script = BASE / "scripts" / "demo_random_gap.sh"
    run(["bash", str(script), args.pdb_id, args.chain, str(args.flank)])

def cmd_prep(args):
    run(["python", str(BASE/"preprocessing"/"pdb_to_mmcif_and_renumber.py"),
         "-i", args.template, "-o", f"{args.out}/template_clean.cif", "--drop-altloc"])
    run(["python", str(BASE/"preprocessing"/"mask_template.py"),
         "-i", f"{args.out}/template_clean.cif", "-o", f"{args.out}/template_masked.cif", "--ranges", args.ranges])
    run(["python", str(BASE/"scripts"/"pdb_to_fasta.py"),
         "-i", f"{args.out}/template_clean.cif", "-o", f"{args.out}/full.fasta", "--chains", args.chain])
    run(["python", str(BASE/"preprocessing"/"make_window_fasta.py"),
         "-i", f"{args.out}/full.fasta", "-o", f"{args.out}/windows.fasta",
         "--sites", args.sites, "--flank", str(args.flank)])

def cmd_hhsearch(args):
    run(["python", str(BASE/"balancing"/"run_hhsearch.py"),
         "--fasta", args.fasta, "--db-uniref", args.db_uniref, "--db-pdb", args.db_pdb,
         "--out", args.out, "--threads", str(args.threads)])
    run(["python", str(BASE/"balancing"/"select_templates.py"),
         "--hhr", f"{args.out}/pdb_hits.hhr", "--top", str(args.top), "--out", f"{args.out}/templates.json"])

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

# === ALL-IN-ONE (CUDA-friendly) ===
def cmd_all(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # CUDA env hints for sub-processes (optional)
    env = os.environ.copy()
    if args.cuda_devices is not None:
        env["CUDA_VISIBLE_DEVICES"] = args.cuda_devices
    # OpenMM platform preference (still also passed via CLI)
    env["OPENMM_DEFAULT_PLATFORM"] = args.platform

    # 1) Preprocess
    clean = out / "template_clean.cif"
    masked = out / "template_masked.cif"
    full_fa = out / "full.fasta"
    win_fa = out / "windows.fasta"

    run(["python", str(BASE/"preprocessing"/"pdb_to_mmcif_and_renumber.py"),
         "-i", args.template, "-o", str(clean), "--drop-altloc"], env=env)

    run(["python", str(BASE/"preprocessing"/"mask_template.py"),
         "-i", str(clean), "-o", str(masked), "--ranges", args.ranges], env=env)

    run(["python", str(BASE/"scripts"/"pdb_to_fasta.py"),
         "-i", str(clean), "-o", str(full_fa), "--chains", args.chain], env=env)

    # sites auto if absent
    sites = args.sites
    if not sites:
        span = args.ranges.split(',')[0].split(':')[1]
        a, b = [int(x) for x in span.split('-')]
        sites = str((a + b)//2)

    run(["python", str(BASE/"preprocessing"/"make_window_fasta.py"),
         "-i", str(full_fa), "-o", str(win_fa),
         "--sites", sites, "--flank", str(args.flank)], env=env)

    # 2) AF2 Round 1 (no templates)
    r1 = out / "af2_r1"
    cmd = ["python", str(BASE/"colabfold"/"run_af2.py"),
           "--fasta", str(win_fa), "--out", str(r1),
           "--model-type", args.model_type, "--recycles", str(args.recycles),
           "--num-models", str(args.num_models)]
    if args.gpu_relax: cmd.append("--gpu-relax")
    run(cmd, env=env)

    # 3) (optional) HHsearch balancing
    if args.balance:
        hhs = out / "hhs"
        run(["python", str(BASE/"balancing"/"run_hhsearch.py"),
             "--fasta", str(win_fa),
             "--db-uniref", args.db_uniref, "--db-pdb", args.db_pdb,
             "--out", str(hhs), "--threads", str(args.threads)], env=env)
        run(["python", str(BASE/"balancing"/"select_templates.py"),
             "--hhr", str(hhs/"pdb_hits.hhr"),
             "--top", str(args.top_templates),
             "--out", str(hhs/"templates.json")], env=env)

    # 4) AF2 Round 2 (with templates if balance)
    r2 = out / "af2_r2"
    cmd = ["python", str(BASE/"colabfold"/"run_af2.py"),
           "--fasta", str(win_fa), "--out", str(r2),
           "--model-type", args.model_type, "--recycles", str(args.recycles),
           "--num-models", str(args.num_models)]
    if args.balance:
        cmd.append("--use-templates")
    if args.gpu_relax:
        cmd.append("--gpu-relax")
    run(cmd, env=env)

    # 5) (optional) blend, then graft+minimize on CUDA
    pred = find_rank1_pdb(r2)
    if pred is None:
        print("[ERROR] r2 rank_001 PDB not found.", file=sys.stderr)
        sys.exit(3)

    template_for_graft = str(masked)
    if args.blend_alpha is not None:
        blend_out = out / "blended.pdb"
        ranges_simple = ",".join([r.split('=')[0] if '=' in r else r for r in args.ranges.split(',')])
        run(["python", str(BASE/"postprocessing"/"blend_with_template.py"),
             "--template", template_for_graft, "--pred", str(pred),
             "--out", str(blend_out), "--ranges", ranges_simple, "--alpha", str(args.blend_alpha)], env=env)
        template_for_graft = str(blend_out)

    # compute mapping automatically for first range
    span = args.ranges.split(',')[0].split(':')[1]
    a, b = [int(x) for x in span.split('-')]
    N = b - a + 1
    mapping = f"{args.chain}:{a}-{b}=1-{N}"

    run(["python", str(BASE/"postprocessing"/"graft_and_minimize.py"),
         "--template", template_for_graft, "--pred", str(pred),
         "--output", str(out/"grafted_minimized.pdb"),
         "--map", mapping, "--minimize", "--platform", args.platform], env=env)

    # 6) QC
    run(["python", str(BASE/"postprocessing"/"quality_check.py"),
         "--pdb", str(out/"grafted_minimized.pdb"),
         "--outdir", str(out/"qc")], env=env)

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
    s.add_argument("--ranges", required=True, help="e.g. A:100-120[,B:..-..]")
    s.add_argument("--sites", required=False, help="e.g. 110[, ...] (omit => auto center)")
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

    # ALL-IN-ONE (local files; CUDA-friendly)
    a = sub.add_parser("all", help="One-click pipeline with local files (no downloads)")
    a.add_argument("--template", required=True, help="Local template PDB/mmCIF")
    a.add_argument("--chain", required=True, help="e.g., A")
    a.add_argument("--ranges", required=True, help='Repair region(s), e.g., "A:100-130"[, ...]')
    a.add_argument("--sites", required=False, help="Window centers (omit => auto center)")
    a.add_argument("--flank", type=int, default=25, help="Window flank length (default 25)")
    a.add_argument("--out", required=True, help="Output root directory")

    a.add_argument("--balance", action="store_true", help="Enable HHsearch balancing")
    a.add_argument("--db-uniref", default=None, help="Uniclust30 prefix path")
    a.add_argument("--db-pdb", default=None, help="pdb70 prefix path")
    a.add_argument("--threads", type=int, default=4)
    a.add_argument("--top-templates", type=int, default=5)

    a.add_argument("--model-type", default="alphafold2_ptm")
    a.add_argument("--recycles", type=int, default=3)
    a.add_argument("--num-models", type=int, default=5)

    a.add_argument("--blend-alpha", type=float, default=None, help="Blend weight (optional)")
    a.add_argument("--platform", default="CUDA", help="OpenMM platform (CUDA/CPU/etc)")
    a.add_argument("--gpu-relax", action="store_true", help="Use GPU relax in ColabFold if available")
    a.add_argument("--cuda-devices", default=None, help="Set CUDA_VISIBLE_DEVICES (e.g., '0', '0,1')")
    a.set_defaults(func=cmd_all)

    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
