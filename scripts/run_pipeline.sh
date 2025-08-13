#!/usr/bin/env bash
set -euo pipefail

# Example end-to-end pipeline glue. Adjust paths/params for your case.
# Requires conda env 'af2fixer' activated and necessary binaries installed.

# Inputs (edit me)
FULL_FASTA="inputs/full.fasta"
DELETION_SITES="50,105"
FLANK=25
TEMPLATE_PDB="inputs/input_template.pdb"
RANGES="A:100-130"
OUTROOT="runs/demo"

# 1) Preprocess template
python preprocessing/pdb_to_mmcif_and_renumber.py -i "$TEMPLATE_PDB" -o "$OUTROOT/template_clean.cif" --drop-altloc
python preprocessing/mask_template.py -i "$OUTROOT/template_clean.cif" -o "$OUTROOT/template_masked.cif" --ranges "$RANGES"

# 2) Windows FASTA
python preprocessing/make_window_fasta.py -i "$FULL_FASTA" -o "$OUTROOT/windows.fasta" --sites "$DELETION_SITES" --flank $FLANK

# 3) AF2 round-1 (no templates)
python colabfold/run_af2.py --fasta "$OUTROOT/windows.fasta" --out "$OUTROOT/af2_r1" --model-type alphafold2_ptm --recycles 3

# 4) HHsearch balancing
# (Set your DB locations: UNICLUST_DB and PDB_DB)
UNICLUST_DB="/path/to/uniclust30"    # e.g., uniclust30_2018_08/uniclust30_2018_08
PDB_DB="/path/to/pdb70"              # e.g., pdb70/pdb70
python balancing/run_hhsearch.py --fasta "$OUTROOT/windows.fasta" --db-uniref "$UNICLUST_DB" --db-pdb "$PDB_DB" --out "$OUTROOT/hhs"
python balancing/select_templates.py --hhr "$OUTROOT/hhs/pdb_hits.hhr" --top 5 --out "$OUTROOT/templates.json"

# 5) AF2 round-2 (with templates) - note: colabfold handles templates internally.
python colabfold/run_af2.py --fasta "$OUTROOT/windows.fasta" --out "$OUTROOT/af2_r2" --model-type alphafold2_ptm --recycles 3 --use-templates

# 6) Graft + minimize from best model (choose your rank file)
PRED_PDB=$(ls "$OUTROOT/af2_r2"/*rank_001*\.pdb | head -n1)
python postprocessing/graft_and_minimize.py --template "$OUTROOT/template_masked.cif" --pred "$PRED_PDB" --output "$OUTROOT/grafted_minimized.pdb" --map "A:100-130=1-31" --minimize --platform CPU

# 7) QC
python postprocessing/quality_check.py --pdb "$OUTROOT/grafted_minimized.pdb" --outdir "$OUTROOT/qc"

echo "[DONE] Pipeline completed -> $OUTROOT"
