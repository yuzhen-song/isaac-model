"""Checks shared by the run supervisor and the post-success publisher."""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUTS = (
    'runtime_results/passive_scene_result.json', 'runtime_results/runtime_result.json',
    'runtime_results/joint_motion.csv', 'espresso_open_close_updated.json',
    'espresso_open_close_updated.csv', 'espresso_open_close_updated.mp4',
    'passive_check.log', 'joint_check.log', 'record_video.log',
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def input_hashes():
    manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
    result = {}
    for item in manifest['files']:
        path = ROOT / item['file']
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT) or not path.is_file():
            raise RuntimeError('Missing/unsafe input: ' + item['file'])
        actual = sha256(path)
        if actual != item['sha256']:
            raise RuntimeError('Input differs from this revision package: ' + item['file'])
        result[item['file']] = actual
    return result


def runtime_checks():
    for name in OUTPUTS:
        if not (ROOT / name).is_file() or (ROOT / name).stat().st_size == 0:
            raise RuntimeError('Missing runtime output: ' + name)
    passive = json.loads((ROOT / OUTPUTS[0]).read_text())
    joint = json.loads((ROOT / OUTPUTS[1]).read_text())
    recording = json.loads((ROOT / 'espresso_open_close_updated.json').read_text())
    if passive.get('finite_supported_poses_observed') is not True or not passive.get('samples'):
        raise RuntimeError('Passive scene check did not pass')
    for report, flag in ((joint, 'passed'), (recording, 'motion_checks_passed')):
        checks = report.get('checks')
        if report.get(flag) is not True or not isinstance(checks, dict) or not checks or not all(v is True for v in checks.values()):
            raise RuntimeError('Joint or recording check did not pass')
    if recording.get('frames') != 330 or recording.get('fps') != 30 or recording.get('duration_s') != 11:
        raise RuntimeError('Unexpected recording duration or frame count')
    with (ROOT / 'espresso_open_close_updated.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1320 or not all(math.isfinite(float(row[key])) for row in rows for key in ('time_s', 'target_deg', 'actual_deg')):
        raise RuntimeError('Recording CSV is incomplete or non-finite')
    return {'passive': True, 'joint': True, 'recording': True,
            'outputs': {name: sha256(ROOT / name) for name in OUTPUTS}}


def verified_run():
    proof = json.loads((ROOT / 'validation/run_success.json').read_text(encoding='utf-8'))
    if proof.get('passed') is not True:
        raise RuntimeError('No successful supervised run exists')
    if proof.get('inputs') != input_hashes():
        raise RuntimeError('Package inputs changed after successful testing')
    checks = runtime_checks()
    if proof.get('outputs') != checks['outputs']:
        raise RuntimeError('Runtime outputs changed after successful testing')
    return proof
