# Espresso — updated STEP revision 20261105

Isaac Sim 5.1.0 / Python 3.11. Metres, kilograms, Z up. White PLA appearance.
Source: the current espressonmachine.STEP; every simulation mesh was regenerated
from that STEP. The supplied stick.STL is an older geometry and was not used.

## Mass and physics

| Part | Estimated mass |
| --- | ---: |
| Body | 544.52 g |
| Handle | 11.68 g |
| Pin | 1.43 g |
| Cap | 0.83 g |
| Total | 558.47 g |

Mass is a geometric estimate using the supplied 3MF settings: PLA density
1.26 g/cm3, 15% infill, 2 walls (0.87 mm approximate total
line width), 0.2 mm layers, 5 top layers and 3 bottom layers. Current STEP part
local Z is assumed to be the print direction. Supports, brim, purge and exact
toolpath effects are excluded. These are not the old model's slicer weights.
See mass_estimate.json and print_settings.json for provenance and assumptions.

Pin/cap masses are included in Body (0.546783623 kg);
Handle is 0.011684005 kg. Inertias use per-part uniform effective density.
The base is movable, supported by a table. The +Z revolute joint has no angle
limits. A zero-velocity saturated brake remains capped at 0.02 Nm. Contact
coefficients are provisional (0.5 static, 0.4 dynamic, restitution 0).
Parent/child contact is disabled for the ideal hinge; external contact remains enabled.

## Load and run

- espresso_test.usda: complete scene, open and press Play.
- espresso_asset.usda: object-only entrypoint for an existing scene; keep this
  whole directory together, since the entrypoint references espresso_test.usda.
- espresso_fixed_base.usda: isolated fixed-base motor check only.
- /World/Espresso/Body, /World/Espresso/Handle, /World/Espresso/handle_hinge:
  paths in the complete scene. The asset entrypoint remaps them under /Asset/Espresso.

```bash
python run_checks_and_record.py
```

This runs passive, isolated-joint and dynamic recording checks in sequence.
It uses the active Isaac Python environment, saves logs, JSON/CSV and
espresso_open_close_updated.mp4 (11 seconds, 30 fps, 1280x720).
The handle is driven by external test torque; its equal reaction is applied
to Body. The demonstration angle is a command, not a joint limit.
Only a fully successful run creates validation/run_success.json.

After reviewing a successful video, publish the validated revision:

```bash
python publish_revision.py
```

Publishing requires authenticated gh/git with repository write access. It
refuses missing/failed results or changed input files, updates only the espresso
object and relevant documentation/catalog entries, and never force-pushes.
The original static report remains build-time evidence; current server results
are archived under validation/ after publishing.

Default recording direction: 0 -> -90 -> 0 degrees. This is a motion command, not a joint limit.
