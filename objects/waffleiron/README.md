# waffleiron | Isaac Sim 5.1

Open waffleiron_test.usda for the fixed-base test. The object-only waffleiron_asset.usda entry releases the base for use in a host scene. The source STEP and STL files are included in source_cad/. Units are metres and kilograms, with Z up.

## PLA mass estimate

Total 225.276 g. The base including pin and cap weighs an estimated 114.038 g; the moving part is 111.239 g. The model uses 1.26 g/cm3 PLA, 15% sparse core, 0.87 mm wall, 0.2 mm layers and five top / three bottom layers. Waffle iron lid.3mf, Bambu project settings, extruder 1. Same profile assumed for mixer and waffle top. The calculation excludes supports, brim and purge. mass_estimate.json documents each part, print orientation, centre of mass and inertia. The mass properties are integrated over the estimated material distribution. Recompute the per-part estimates with Python 3.12, numpy, trimesh and manifold3d: python estimate_mass.py .

## Simulation and recording

Run python -u run_isaac_check.py in Isaac Sim Python. The joint opens about Y from zero to -90 degrees then returns to zero. The CAD-based hinge has internal collisions disabled; the limits are demonstration settings. Runtime output is result.json and motion.csv. Run python -u record_waffleiron_motion.py for the CPU-rendered replay of the measured motion. Archived results are under validation/ and media/.
