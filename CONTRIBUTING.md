# Adding or updating an object

Use `objects/<object_name>/` for every object. Root files describe the collection;
object files describe one model and its assumptions.

| Path | Contents |
| --- | --- |
| `README.md` | Source files, units, axis/zero pose, mass provenance, assumptions, commands and validation state. |
| `source_cad/` | Original CAD assembly, parts and neutral STEP export when available. |
| `meshes_assembly_mm/` | Separate meshes in original CAD assembly coordinates, millimetres. |
| `meshes_sim_m/` | Separate simulation meshes, metres, Z up. |
| `*_test.usda` | Main dynamic scene, including masses, inertia, colliders and joints. |
| `*_fixed_base.usda` | Optional isolated hinge-test overlay. |
| `joint_parameters.json` | Machine-readable physics and coordinate configuration. |
| `mass_estimate.json` | Geometric estimation assumptions, when mass is not supplied by a slicer or measurement. |
| `run_passive_scene.py` | Passive startup and support check. |
| `run_isaac_check.py` | Motor-driven isolated joint check. |
| `record_*_motion.py` | Reproducible physical demonstration recording. |
| `media/` | Small final demonstration videos; use release assets for large recordings. |
| `docs/` | Build-time geometric and static USD validation. |
| `validation/` | Archived runtime JSON/CSV and a summary identifying what was actually checked. |

Add a row to the root README and an entry to `objects/catalog.json`. Use object-local
paths in scene sublayers and resolve assets relative to the script/scene file so
the object directory remains movable.

When changing mass, update inertia consistently. Record whether mass was measured,
provided by a slicer, or geometrically estimated. Preserve the exact infill, wall,
top/bottom and print-orientation assumptions for an estimate.

Distinguish static checks, passive checks, isolated motor tracking, torque-driven
recording, robot contact and real-world success. Store numeric reports in
`validation/` instead of treating a video or an old static flag as complete evidence.
Keep existing source attribution with the relevant object.

Do not commit Python environments, caches, authentication files, raw startup logs
or incomplete recordings. Put final evidence in `media/` and `validation/`; runtime
outputs written next to a script are ignored by the repository rules.
