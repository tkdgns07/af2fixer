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
ENV_NAME="af2fixer"
PY_VER="3.10"

# Create env if missing
if ! conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  conda create -y -n "$ENV_NAME" "python=${PY_VER}"
fi
conda activate "$ENV_NAME"

# --------------------------
# Channels & solver (reset)
# --------------------------
# 채널 순서와 solver를 고정해 재현성/충돌 방지
conda config --remove-key channels 2>/dev/null || true
conda config --add channels conda-forge
conda config --add channels bioconda
conda config --add channels defaults
conda config --set channel_priority strict
conda config --set solver libmamba || true

# --------------------------
# Core deps from conda-forge
# --------------------------
# 과학 라이브러리는 conda-forge에서 명시 설치(버전 호환 확보)
conda install -y -c conda-forge \
  "biopython>=1.81" \
  gemmi \
  openmm \
  numpy \
  pandas

# --------------------------
# Bio tools from bioconda
# --------------------------
# HHsuite는 bioconda 최신 빌드를 사용
conda install -y -c bioconda hhsuite

# (선택) mmseqs2 등을 쓰려면 아래 주석 해제
# conda install -y -c bioconda mmseqs2

# --------------------------
# Sanity check
# --------------------------
python - <<'PY'
import sys, platform
import importlib
mods = ["Bio", "gemmi", "numpy", "pandas"]
print("[OK] Python", sys.version.split()[0])
print("[OK] Platform", platform.platform())
for m in mods:
    importlib.import_module(m)
    print(f"[OK] import {m}")
try:
    import openmm
    print("[OK] openmm", openmm.__version__)
except Exception as e:
    print("[WARN] openmm import failed:", e)
PY

echo "[DONE] Environment '${ENV_NAME}' is ready."
