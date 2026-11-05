# ARCTIC Object Models for Isaac Sim

3D models, physical parameters and ready-to-open Isaac Sim scenes for ARCTIC-related objects.

**For teammates: [how to install and load the models in Isaac Sim](docs/ISAAC_LOADING.md).**
The guide covers the environment, GUI loading and Python loading. White PLA
appearance, masses, collision geometry and unlimited hinges are already configured.

## Available objects

| Object | Assets and configuration | Main scene | Mass source | Demonstration |
| --- | --- | --- | --- | --- |
| Espresso machine | [objects/espresso](objects/espresso/) | [espresso_test.usda](objects/espresso/espresso_test.usda) | Slicer estimates; **557.22 g** total | [0° → 90° → 0° video](objects/espresso/media/espresso_open_close_updated.mp4); [tracking report](objects/espresso/validation/espresso_open_close_updated.json) |
| Microwave | [objects/microwave](objects/microwave/) | [microwave_test.usda](objects/microwave/microwave_test.usda) | PLA, **15% infill** plus provisional shell settings; **523.55 g** estimated total | [0° → −90° → 0° video](objects/microwave/media/microwave_open_close.mp4); [validation summary](objects/microwave/validation/runtime_summary.json) |

Both scenes use metres, kilograms and a Z-up world, with a movable body and an
unlimited revolute hinge. The individual object README and `joint_parameters.json`
are the authoritative configuration references. New objects follow the same layout.

## Environment

- Isaac Sim **5.1.0**, Python **3.11** and a compatible NVIDIA GPU/driver.
- Isaac Lab is not required for the supplied object checks or recordings.
- Review the NVIDIA licence at first startup.

```bash
git clone https://github.com/yuzhen-song/isaac-model.git
cd isaac-model

conda create -n arctic-isaac51 python=3.11 -y
conda activate arctic-isaac51
python -m pip install --upgrade pip
python -m pip install --no-cache-dir -r requirements.txt --extra-index-url https://pypi.nvidia.com
```

If the Ubuntu container lacks the system graphics libraries, install them as root
(or use sudo):

```bash
apt-get update
apt-get install -y libxt6 libglu1-mesa libvulkan1
```

See the [official Isaac Sim 5.1 requirements](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/requirements.html)
for driver and platform compatibility.

## Load into an existing robot scene

| ARCTIC name | Object-only entrypoint |
| --- | --- |
| `espressomachine` | [`objects/espresso/espresso_asset.usda`](objects/espresso/espresso_asset.usda) |
| `microwave` | [`objects/microwave/microwave_asset.usda`](objects/microwave/microwave_asset.usda) |

Use these entries when replacing the simulation asset. They keep geometry,
materials, masses and the unlimited joint while disabling the demo table,
physics scene, camera and light. Keep the complete object directory because the
entries reference neighbouring files. Scale is **1**, in metres, kilograms, Z up.

Run a standalone loading example from the repository root:

```bash
python examples/load_object.py --object microwave --headless --allow-root
```

To add an object to an existing stage, call `scripts.spawn_object.spawn_object`
after starting `SimulationApp`; see the [loading guide](docs/ISAAC_LOADING.md)
for a complete snippet and returned body/joint paths. New entrypoints have OpenUSD
static validation; the new loading example still needs a runtime check in the target environment.

## Run the original validation scene

Open an object's main USDA in Isaac Sim and press Play. For a terminal check,
change into that object's directory first:

```bash
cd objects/microwave
python run_passive_scene.py --headless --allow-root --seconds 10
python run_isaac_check.py --headless --allow-root
python -u record_microwave_motion.py --headless --allow-root
```

For the espresso machine, use `objects/espresso` and `record_espresso_motion.py`.
The `--allow-root` flag is included for root-run containers.

| Script / asset | Purpose |
| --- | --- |
| Main `*_test.usda` | Movable object supported by the scene's tabletop; original passive hinge brake retained. |
| `run_passive_scene.py` | Ten-second passive smoke check; does not turn the handle or door. |
| `run_isaac_check.py` | Fixed-base hinge tracking check. Temporarily replaces the brake with a motor in memory. |
| `record_*_motion.py` | Eleven-second torque-driven recording; keeps the dynamic body, configured masses and passive brake. |
| `media/` | Archived demonstration video. New recordings are produced in the object's directory. |
| `validation/` | Archived reports and their provenance. |

Recording outputs are an MP4, JSON and CSV. Check `motion_checks_passed` in a
recording's JSON report; these are scripted motor demonstrations rather than
robot-grasp trials. Example angle targets are commands, not joint limits.

## Headless EGL configuration

The original AutoDL environment required NVIDIA EGL as the Vulkan ICD entrypoint.
If your machine has the same GLX/Vulkan loading problem, from the repository root:

```bash
source scripts/enable_egl.sh
cd objects/microwave
python -u record_microwave_motion.py --headless --allow-root
```

The helper creates a local `.runtime/nvidia_egl_icd.json`, sets `VK_ICD_FILENAMES`
and prepares `XDG_RUNTIME_DIR`. It does not change system ICD files or install a
driver. Standard working graphics environments can use their default configuration.

## Physics assumptions and validation

- Espresso masses come from the supplied per-part slicer screenshots. Microwave
  masses are a geometric estimate using 1.24 g/cm³ PLA, 15% sparse infill,
  0.8 mm walls and 0.6 mm top/bottom thickness; see its `mass_estimate.json`.
- Pins and caps belong to their fixed body rigid actor and are not counted twice.
  Inertias use each CAD part's uniform effective density; actual infill lattices
  are not explicitly modeled.
- Hinge resistance is a provisional saturated viscous brake capped at **0.02 N·m**,
  not measured breakaway friction. External contact uses provisional coefficients.
- Hinges have no angular limits. Body-to-moving-part contacts are disabled for the
  ideal pin/hinge assembly, so internal contact and mechanical self-stops are not
  represented. Tabletop and external robot contact remain enabled.
- Dynamic mesh collision uses convex decomposition. Inspect cooked colliders when
  adding robot contacts or changing the scene.
- Espresso tracking JSON is archived and reports a pass. The microwave operator
  reports successful checks/recording, and its archived video has 330 frames at
  30 fps, 1280×720, lasting 11 seconds. Microwave numeric runtime reports have not
  yet been archived; its summary identifies this distinction.
- `docs/usd_static_validation.json` records build-time static checks. Its original
  runtime-tested field predates later server runs; consult `validation/` for
  current runtime evidence. Physical friction calibration and real robot trials
  remain separate work.

## Archiving the microwave server run

To also publish the exact assets, scripts and JSON/CSV reports used on the original
server, run this in that server's terminal after testing has finished:

```bash
curl -fL https://raw.githubusercontent.com/yuzhen-song/isaac-model/main/scripts/publish_microwave_runtime.py -o /tmp/publish_microwave_runtime.py
python /tmp/publish_microwave_runtime.py --source /root/autodl-tmp/microwave_updated/Microwave_Isaac_Handoff
```

Requires an authenticated GitHub CLI (`gh`) with write access to this repository.
The helper uses a fresh working copy, archives reports and any of the three known
test logs, records source hashes, updates documentation and pushes to `main`.
It records reported failures as failures; it does not rerun Isaac Sim. Use
`--dry-run` to inspect the file mapping without connecting or writing.

## Adding more objects

See [CONTRIBUTING.md](CONTRIBUTING.md). Keep object-specific CAD, meshes, USD scenes,
parameters, demonstrations and evidence together under `objects/<object_name>/`.

Original CAD assembly coordinates are in millimetres in `meshes_assembly_mm/`;
`meshes_sim_m/` contains transformed Z-up meshes in metres. Preserve the transforms
and zero pose documented by each object rather than mixing those coordinate systems.
