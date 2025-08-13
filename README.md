# af2fixer

AF2 loop-fixer pipeline with HHsearch balancing. Now with a single CLI: `af2fixer`.

## 0) Environment
```bash
bash env_setup/install_env.sh
conda activate af2fixer
```

## 1) Install CLI (editable)
```bash
pip install -e .
# Now you have the command: af2fixer
```

## 2) Quick demo (downloads PDB, random gap, prepares inputs)
```bash
af2fixer demo 1UBQ --chain A --flank 25
```

## 3) HHsearch balancing (requires local DBs)
```bash
af2fixer hhsearch \
  --fasta runs/1UBQ_A_demo/windows.fasta \
  --db-uniref /data/hhsuite_dbs/uniclust30_2018_08/uniclust30_2018_08 \
  --db-pdb    /data/hhsuite_dbs/pdb70/pdb70 \
  --out runs/1UBQ_A_demo/hhs --threads 8 --top 5
```

## 4) Run ColabFold
```bash
af2fixer af2 --fasta runs/1UBQ_A_demo/windows.fasta --out runs/1UBQ_A_demo/af2_r1 \
  --model-type alphafold2_ptm --recycles 3
# (with templates)
af2fixer af2 --fasta runs/1UBQ_A_demo/windows.fasta --out runs/1UBQ_A_demo/af2_r2 \
  --model-type alphafold2_ptm --recycles 3 --use-templates
```

## 5) Graft + minimize
```bash
PRED=$(ls runs/1UBQ_A_demo/af2_r2/*rank_001*.pdb | head -n1)
python postprocessing/graft_and_minimize.py \
  --template runs/1UBQ_A_demo/template_masked.cif \
  --pred "$PRED" \
  --output runs/1UBQ_A_demo/grafted_minimized.pdb \
  --map "A:100-130=1-31" --minimize --platform CPU
```

## 6) QC
```bash
af2fixer qc --pdb runs/1UBQ_A_demo/grafted_minimized.pdb --outdir runs/1UBQ_A_demo/qc
```

See `scripts/demo_random_gap.sh` for a fully worked preprocessing example.
