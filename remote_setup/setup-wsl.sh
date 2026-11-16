#!/usr/bin/env bash
# Step 3, run inside Ubuntu (WSL2) as the guest. Safe to run more than once.
#
#   bash setup-wsl.sh            # tools, Python environment, Quantum ESPRESSO (CPU), the repo
#   bash setup-wsl.sh --gpu-ml   # also PyTorch with CUDA for machine-learned potentials
#
# NOT TESTED on the target machine. It stops at the first error.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/dirac1974/failsmart-matengine}"
REPO_BRANCH="${REPO_BRANCH:-main}"
ENV_NAME="${ENV_NAME:-dft}"
GPU_ML=0
[[ "${1:-}" == "--gpu-ml" ]] && GPU_ML=1

say() { printf '\n==> %s\n' "$*"; }

say "System packages"
sudo apt-get update -y
sudo apt-get install -y build-essential git curl wget tmux htop rsync ca-certificates

say "GPU check"
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
else
  echo "WARNING: nvidia-smi does not work inside WSL."
  echo "         Update the NVIDIA driver on the Windows side. Do not install a Linux GPU driver here."
fi

say "Miniforge (conda)"
if [[ ! -d "$HOME/miniforge3" ]]; then
  curl -fsSL -o /tmp/miniforge.sh \
    "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
  bash /tmp/miniforge.sh -b -p "$HOME/miniforge3"
  rm -f /tmp/miniforge.sh
fi
# shellcheck disable=SC1091
source "$HOME/miniforge3/etc/profile.d/conda.sh"
grep -q 'miniforge3/etc/profile.d/conda.sh' "$HOME/.bashrc" 2>/dev/null \
  || echo 'source "$HOME/miniforge3/etc/profile.d/conda.sh"' >> "$HOME/.bashrc"

say "Environment '$ENV_NAME' with Python and Quantum ESPRESSO (CPU build from conda-forge)"
if ! conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  conda create -y -n "$ENV_NAME" -c conda-forge python=3.11 qe
fi
conda activate "$ENV_NAME"
command -v pw.x >/dev/null && echo "pw.x: $(command -v pw.x)"

say "Project code"
mkdir -p "$HOME/work"
if [[ ! -d "$HOME/work/failsmart-matengine/.git" ]]; then
  git clone --branch "$REPO_BRANCH" "$REPO_URL" "$HOME/work/failsmart-matengine"
else
  git -C "$HOME/work/failsmart-matengine" pull --ff-only || true
fi
pip install -q -e "$HOME/work/failsmart-matengine[dev]"

if [[ "$GPU_ML" -eq 1 ]]; then
  say "PyTorch with CUDA"
  pip install -q torch
  python - <<'PY'
import torch
print("torch", torch.__version__, "| CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
PY
fi

say "Machine summary"
echo "cores: $(nproc)   memory: $(free -g | awk '/^Mem:/{print $2}') GB   disk free: $(df -h "$HOME" | awk 'NR==2{print $4}')"

cat <<EOF

Done. Next:
  1. Check that detached jobs survive a disconnect:
       bash keepalive-test.sh start      (then log out completely, wait 5 minutes, log back in)
       bash keepalive-test.sh check
  2. Start work in tmux so it survives disconnects:
       tmux new -s run        (detach with Ctrl-b then d; come back with: tmux attach -t run)
       conda activate $ENV_NAME
EOF
