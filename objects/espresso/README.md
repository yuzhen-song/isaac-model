# Espresso machine — Isaac Sim model

An articulated model of a white PLA printed espresso-machine assembly.
Coordinates: metres, kilograms, Z up. Isaac Sim **5.1.0**, Python **3.11**.
Isaac Lab is not required. After cloning the repository, change into `objects/espresso` before running the commands below.

## Physics configuration

| Printed part | Slicer-estimated mass |
| --- | ---: |
| Body (`bottom`) | 0.54812 kg |
| Handle (`stick`), excluding brim | 0.00653 kg |
| Pin and cap together | 0.00257 kg |
| Total | 0.55722 kg |

The pin and cap are attached to the body, giving the Body rigid actor a mass of
**0.55069 kg**. The Handle rigid actor is **0.00653 kg**. Hardware is not counted twice.
Inertia and centre of mass approximate each CAD part with uniform effective density;
the true printed infill distribution was not reconstructed. White PLA appearance
does not determine the authored masses or contact friction.

- Main scene: `espresso_test.usda`; movable body supported by a tabletop.
- Hinge: `/World/Espresso/handle_hinge`, local Z axis, **no angular limits**.
- Body: `/World/Espresso/Body`; Handle: `/World/Espresso/Handle`.
- Passive hinge resistance: saturated viscous brake capped at **0.02 N·m**.
  Angular drive: stiffness=0, targetVelocity=0, damping=1 N·m·s/degree,
  maxForce=0.02 N·m. It is an approximation, not calibrated Coulomb/stiction friction.
- Contact: static friction=0.5, dynamic friction=0.4, restitution=0, all provisional.
- Dynamic mesh colliders use convex decomposition; inspect the cooked geometry in Isaac.
- Body–Handle contact is disabled for the ideal hinge/pin assembly; physical self-stops
  are not modeled. Contact with the tabletop and external robot objects is enabled.

## Install

Use an NVIDIA GPU and a driver compatible with Isaac Sim 5.1.
See https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/requirements.html .

```bash
conda create -n espresso-isaac51 python=3.11 -y
conda activate espresso-isaac51
python -m pip install --upgrade pip
python -m pip install --no-cache-dir -r requirements.txt --extra-index-url https://pypi.nvidia.com
```

If the Ubuntu container lacks the system graphics libraries, install as root
(or prepend sudo when required):

```bash
apt-get update
apt-get install -y libxt6 libglu1-mesa libvulkan1
```

Review and accept the NVIDIA licence when first prompted.

## Run

Open `espresso_test.usda` in Isaac Sim and press Play, or run a headless smoke check:

```bash
python run_passive_scene.py --headless --allow-root --seconds 10
```

The passive scene does not move the handle automatically. It preserves the movable
base, print masses, unlimited joint and passive brake.

For a scripted **0° → 90° → 0°** recording with these parameters preserved:

```bash
python -u record_espresso_motion.py --headless --allow-root
```

Outputs: `espresso_open_close_updated.mp4` (1280×720, 30 fps, 11 s) and matching
JSON/CSV reports. The script applies external motor torque and reaction torque to
the machine body. It is not a robot grasp demonstration. Check
`motion_checks_passed` in the JSON report; an MP4 alone does not prove tracking success.
The 90° target is a demonstration command, not a joint limit.

For isolated hinge tracking with a fixed body:

```bash
python run_isaac_check.py --headless --allow-root
```

This last test uses `espresso_fixed_base.usda` and replaces the brake with a test motor
in memory. It does not validate the dynamic base or hinge resistance and does not
modify the delivered scene files.

## Headless EGL workaround (only when NVIDIA GLX/Vulkan loading fails)

The source AutoDL machine required an EGL-based NVIDIA Vulkan ICD. This workaround
is machine-specific; standard desktop/server installations may not need it.

```bash
python - <<'PY'
import ctypes, json
from pathlib import Path
ctypes.CDLL('libEGL_nvidia.so.0')
candidates = [Path('/etc/vulkan/icd.d/nvidia_icd.json'),
              Path('/usr/share/vulkan/icd.d/nvidia_icd.json')]
source = next((p for p in candidates if p.is_file()), None)
if source is None:
    raise SystemExit('NVIDIA Vulkan ICD missing; check container GPU graphics support.')
data = json.loads(source.read_text())
data['ICD']['library_path'] = 'libEGL_nvidia.so.0'
Path('.runtime').mkdir(exist_ok=True)
Path('.runtime/nvidia_egl_icd.json').write_text(json.dumps(data, indent=2))
PY
export XDG_RUNTIME_DIR="/tmp/espresso-runtime-$(id -u)"
mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"
export VK_ICD_FILENAMES="$PWD/.runtime/nvidia_egl_icd.json"
python -u record_espresso_motion.py --headless --allow-root
```

## Files and validation scope

`joint_parameters.json` contains the full configuration and assumptions.
`meshes_sim_m/` contains Z-up meshes in metres; `meshes_assembly_mm/` contains
meshes in original CAD assembly coordinates (millimetres). `source_cad/` preserves
the original CAD files when included.

The provider's 10-second passive-scene log was reviewed: parameters passed the
script assertions, poses remained finite and stable, and execution completed.
Recorded motion quality, physical friction calibration, grasp success and sim-to-real
transfer are separate checks. `docs/usd_static_validation.json` documents the local
static checks only; its runtime-tested field is not a complete record of later runs.
Historical geometry previews show example poses, not angular limits.

## Demonstration video

[Download open/close video](media/espresso_open_close_updated.mp4)

