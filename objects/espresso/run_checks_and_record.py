"""Run the updated scene checks and recording; publishing is a separate step."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from revision_checks import ROOT, OUTPUTS, input_hashes, runtime_checks


def main():
    proof_path = ROOT / 'validation/run_success.json'
    proof_path.unlink(missing_ok=True)
    inputs = input_hashes()
    for name in OUTPUTS:
        if not name.endswith('.mp4'):
            (ROOT / name).unlink(missing_ok=True)
    environment = dict(os.environ)
    environment.setdefault('XDG_RUNTIME_DIR', '/tmp/isaac-runtime')
    runtime = Path(environment['XDG_RUNTIME_DIR'])
    runtime.mkdir(parents=True, exist_ok=True)
    runtime.chmod(0o700)
    existing_icd = Path('/root/autodl-tmp/nvidia_egl_icd.json')
    if not environment.get('VK_ICD_FILENAMES') and existing_icd.is_file():
        environment['VK_ICD_FILENAMES'] = str(existing_icd)
    commands = (
        ('run_passive_scene.py', ['--seconds', '10'], 'passive_check.log'),
        ('run_isaac_check.py', [], 'joint_check.log'),
        ('record_espresso_motion.py', [], 'record_video.log'),
    )
    started = datetime.now(timezone.utc).isoformat()
    for script, options, log in commands:
        command = [sys.executable, '-u', str(ROOT / script), '--headless', '--allow-root'] + options
        print('\nRUNNING: ' + script, flush=True)
        with (ROOT / log).open('w', encoding='utf-8') as stream:
            process = subprocess.Popen(command, cwd=ROOT, env=environment,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, encoding='utf-8', errors='replace', bufsize=1)
            for line in process.stdout:
                print(line, end='', flush=True)
                stream.write(line)
                stream.flush()
            status = process.wait()
        if status:
            raise RuntimeError(script + ' failed; see ' + log + '. GitHub was not changed.')
    checks = runtime_checks()
    if inputs != input_hashes():
        raise RuntimeError('Scene/script inputs changed while testing')
    params = json.loads((ROOT / 'joint_parameters.json').read_text())
    proof_path.parent.mkdir(exist_ok=True)
    proof_path.write_text(json.dumps({
        'passed': True, 'started_at_utc': started,
        'completed_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_STEP_sha256': params['source_STEP_sha256'], 'python': sys.version,
        'inputs': inputs, 'outputs': checks['outputs'],
        'scope': 'passive smoke check, isolated motor tracking, dynamic external-torque video; no robot task',
    }, indent=2) + '\n', encoding='utf-8')
    print('\nALL_CHECKS_PASSED', flush=True)
    print('VIDEO: ' + str(ROOT / 'espresso_open_close_updated.mp4'), flush=True)
    print('After reviewing the video, publish with: python publish_revision.py', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        print('STOPPED: ' + str(error), file=sys.stderr)
        sys.exit(1)
