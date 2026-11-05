#!/usr/bin/env bash
# Source this helper from an activated Isaac Sim Python environment.
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    echo 'Use: source scripts/enable_egl.sh' >&2
    exit 1
fi
_isaac_repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd) || return 1
if ! python - "$_isaac_repo_dir" <<'PY'
import ctypes
import json
import sys
from pathlib import Path

ctypes.CDLL('libEGL_nvidia.so.0')
candidates = [Path('/etc/vulkan/icd.d/nvidia_icd.json'),
              Path('/usr/share/vulkan/icd.d/nvidia_icd.json')]
source = next((p for p in candidates if p.is_file()), None)
if source is None:
    raise SystemExit('NVIDIA Vulkan ICD not found; check GPU graphics support in the container.')
data = json.loads(source.read_text())
data['ICD']['library_path'] = 'libEGL_nvidia.so.0'
output = Path(sys.argv[1]) / '.runtime' / 'nvidia_egl_icd.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(data, indent=2))
PY
then
    unset _isaac_repo_dir
    return 1
fi
export VK_ICD_FILENAMES="$_isaac_repo_dir/.runtime/nvidia_egl_icd.json"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/isaac-runtime-$(id -u)}"
mkdir -p -- "$XDG_RUNTIME_DIR" || return 1
chmod 700 -- "$XDG_RUNTIME_DIR" || return 1
printf 'NVIDIA EGL ICD: %s\nRuntime directory: %s\n' "$VK_ICD_FILENAMES" "$XDG_RUNTIME_DIR"
unset _isaac_repo_dir
