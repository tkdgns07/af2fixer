#!/usr/bin/env bash
set -euo pipefail

# ==========================
# Robust Conda activation
# ==========================
CONDA_BASE=""
if command -v conda >/dev/null 2>&1; then
  CONDA_BASE=$(conda info --base 2>/dev/null || true)
fi
if [[ -z "${CONDA_BASE}" ]]; then
  for c in "$HOME/miniconda3" "$HOME/anaconda3" "/opt/conda"; do
    if [[ -d "$c" && -f "$c/etc/profile.d/conda.sh" ]]; then
      CONDA_BASE="$c"; break
    fi
  done
fi
if [[ -z "${CONDA_BASE}" ]]; then
  echo "[ERROR] Could not locate conda. Install Miniconda/Anaconda first." >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$CONDA_BASE/etc/profile.d/conda.sh"

# ==========================
# Create env and install deps
# ==========================
ENV_NAME="af2pdb"
PY_VER="3.10"

if ! conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  conda create -y -n "$ENV_NAME" python="$PY_VER"
fi

conda activate "$ENV_NAME"

# Channels (need bioconda for hhsuite)
conda config --add channels conda-forge || true
conda config --add channels bioconda || true
conda config --set channel_priority strict

# Core deps
conda install -y \
  gemmi \
  biopython \
  numpy \
  pandas

# OpenMM (some platforms prefer conda-forge openmm)
conda install -y openmm

# HH-suite (hhblits, hhsearch)
conda install -y hhsuite

# Optional tools
# conda install -y mmseqs2
# pip install 'colabfold[alphafold]'

python - <<'PY'
import sys, platform
print("[OK] Python", sys.version)
print("[OK] Platform", platform.platform())
PY

echo "[DONE] Environment '$ENV_NAME' is ready."
