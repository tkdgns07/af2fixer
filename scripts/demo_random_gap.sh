#!/usr/bin/env bash
set -euo pipefail
# Requires: conda activate af2fixer

PDB_ID="${1:-1UBQ}"
CHAIN="${2:-A}"
FLANK="${3:-25}"

ROOT="runs/${PDB_ID}_${CHAIN}_demo"
mkdir -p "$ROOT" inputs

echo "[1] Download PDB ${PDB_ID}"
curl -sS "https://files.rcsb.org/download/${PDB_ID}.pdb" -o "inputs/${PDB_ID}.pdb"

echo "[2] Clean & renumber -> mmCIF"
python preprocessing/pdb_to_mmcif_and_renumber.py -i "inputs/${PDB_ID}.pdb" -o "${ROOT}/template_clean.cif" --drop-altloc

echo "[3] Extract FASTA from template"
python scripts/pdb_to_fasta.py -i "${ROOT}/template_clean.cif" -o "${ROOT}/full.fasta" --chains "${CHAIN}"

echo "[4] Pick random deletion range on ${CHAIN}"
eval $(python scripts/make_random_gap.py --input "${ROOT}/template_clean.cif" --chain "${CHAIN}")
echo " -> RANGE=${RANGE}, center site=${SITES}"

echo "[5] Mask template at RANGE"
python preprocessing/mask_template.py -i "${ROOT}/template_clean.cif" -o "${ROOT}/template_masked.cif" --ranges "${RANGE}"

echo "[6] Make window FASTA around center site (±${FLANK})"
python preprocessing/make_window_fasta.py -i "${ROOT}/full.fasta" -o "${ROOT}/windows.fasta" --sites "${SITES}" --flank "${FLANK}"

echo "[DONE] Inputs prepared in: ${ROOT}"
