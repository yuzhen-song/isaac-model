# Waffle iron

Open **waffleiron_test.usda** for the tested fixed-base setup. The original four CAD parts are in source_cad/. The pin and cap belong to the base. The upper shell opens around the Y axis. The scene uses metres, kilograms and Z up. Joint travel is −90° to 0°; the report expresses opening as a positive angle. Base and top masses (0.50 kg and 0.35 kg) are provisional demo values. The internal contact pair is disabled.

For integration, reference **waffleiron_asset.usda** or use the repository loader with the name **waffleiron**. The integration entry releases the world fixation and excludes the test light and physics scene. Runtime evidence applies to the fixed-base scene.

From this directory, using the Isaac Sim 5.1 Python environment:

    python -u run_isaac_check.py
    python -u record_waffleiron_motion.py

The checker drives the hinge in memory and writes result.json and motion.csv. The recorder uses NumPy, Pillow and ffmpeg (or imageio-ffmpeg) to replay the measured trajectory on the source meshes. It uses validation/motion.csv when no new local trace exists. The published MP4 is in media/ and the server check and trajectory are in validation/.
