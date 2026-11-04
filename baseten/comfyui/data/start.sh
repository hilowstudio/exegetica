#!/bin/sh
# Starts ComfyUI on Baseten. Model files are mounted read-only at /models/minimax-h3 (config.yaml).
set -e

nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader || true
python3 -c "import sys, torch; ok = torch.cuda.is_available(); print('torch', torch.__version__, 'cuda', torch.version.cuda, 'gpu', ok, flush=True); sys.exit(0 if ok else 1)" || {
  echo "PyTorch cannot reach the GPU. CUDA 13 needs NVIDIA driver r580 or newer. Switch config.yaml to the cu128 build and the fp8 model files."
  exit 1
}

mkdir -p /tmp/comfy/input /tmp/comfy/output /tmp/comfy/temp /tmp/comfy/user
cd /app/ComfyUI
exec python3 main.py --listen 0.0.0.0 --port 8188 \
  --extra-model-paths-config /app/data/extra_model_paths.yaml \
  --input-directory /tmp/comfy/input --output-directory /tmp/comfy/output \
  --temp-directory /tmp/comfy/temp --user-directory /tmp/comfy/user \
  --disable-auto-launch --offline --disable-metadata --use-ck-attention
