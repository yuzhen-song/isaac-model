"""Publish this espresso revision only after its supervised run passes."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from revision_checks import ROOT, sha256, verified_run

REPOSITORY = 'yuzhen-song/isaac-model'


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def archive_revision(clone, proof):
    clone = clone.resolve()
    destination = clone / 'objects/espresso'
    if destination.is_symlink() or destination.resolve() != clone / 'objects/espresso':
        raise RuntimeError('Unexpected destination; refusing replacement')
    if not destination.resolve().is_relative_to(clone) or not (clone / '.git').is_dir():
        raise RuntimeError('Replacement requires a fresh repository working copy')
    # This is only the espresso directory in a fresh clone; Git history retains
    # the old revision. Do not mix old mesh/report files into the new revision.
    if destination.exists():
        shutil.rmtree(destination)
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    for item in manifest['files']:
        source = ROOT / item['file']
        target = destination / item['file']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    mapping = {
        'runtime_results/passive_scene_result.json': 'validation/passive_scene_result.json',
        'runtime_results/runtime_result.json': 'validation/runtime_result.json',
        'runtime_results/joint_motion.csv': 'validation/joint_motion.csv',
        'espresso_open_close_updated.json': 'validation/espresso_open_close_updated.json',
        'espresso_open_close_updated.csv': 'validation/espresso_open_close_updated.csv',
        'espresso_open_close_updated.mp4': 'media/espresso_open_close_updated.mp4',
        'passive_check.log': 'validation/logs/passive_check.log',
        'joint_check.log': 'validation/logs/joint_check.log',
        'record_video.log': 'validation/logs/record_video.log',
        'validation/run_success.json': 'validation/run_success.json',
    }
    for source, name in mapping.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / source, target)
    params = json.loads((ROOT / 'joint_parameters.json').read_text())
    dump(destination / 'validation/runtime_summary.json', {
        'source': 'supervised server run with package and output hashes',
        'source_STEP_sha256': params['source_STEP_sha256'],
        'passive_check_passed': True, 'joint_tracking_passed': True, 'recording_checks_passed': True,
        'completed_at_utc': proof['completed_at_utc'],
        'numeric_runtime_reports_archived': True, 'rerun_independently_on_another_host': False,
        'scope': proof['scope'],
    })
    # Keep the tested input manifest separate from generated runtime outputs so
    # teammates can rerun the supervisor from the cloned repository as well.
    shutil.copyfile(ROOT / 'manifest.json', destination / 'manifest.json')
    catalog_path = clone / 'objects/catalog.json'
    catalog = json.loads(catalog_path.read_text())
    item = next(item for item in catalog['objects'] if item['name'] == 'espresso')
    item.update({'total_mass_kg': params['mass_total_kg'],
                 'mass_provenance': 'latest STEP geometric estimate: PLA, 15% infill, settings from supplied 3MF',
                 'source_STEP_sha256': params['source_STEP_sha256'],
                 'revision': '20261105', 'validation_summary': 'validation/runtime_summary.json'})
    dump(catalog_path, catalog)
    root_readme = clone / 'README.md'
    text = root_readme.read_text(encoding='utf-8')
    text = text.replace('0° → 90° → 0°', '0° → −90° → 0°')
    lines = []
    for line in text.splitlines():
        if line.startswith('| Espresso machine |'):
            cells = line.split('|')
            cells[4] = ' PLA, 15% infill; **' + format(params['mass_total_kg'] * 1000, '.2f') + ' g** estimated total '
            line = '|'.join(cells)
        lines.append(line)
    text = '\n'.join(lines) + '\n'
    text = text.replace(
        '- Espresso masses come from the supplied per-part slicer screenshots. Microwave\n  masses are',
        '- Espresso masses are geometric estimates for the revised STEP, using the\n  supplied 3MF PLA/15% settings; see its `mass_estimate.json`. Microwave masses are')
    root_readme.write_text(text, encoding='utf-8')
    guide = clone / 'docs/ISAAC_LOADING.md'
    if guide.is_file():
        text = guide.read_text(encoding='utf-8')
        for old, new in [('0.55069 kg', format(params['mass_body_rigid_assembly_kg'], '.8f') + ' kg'),
                         ('0.00653 kg', format(params['mass_handle_kg'], '.8f') + ' kg')]:
            text = text.replace(old, new)
        guide.write_text(text, encoding='utf-8')
    integration = clone / 'validation/integration_static.json'
    if integration.is_file():
        report = json.loads(integration.read_text())
        report['objects']['espresso'] = json.loads((ROOT / 'docs/usd_static_validation.json').read_text())
        report['objects']['espresso']['runtime_evidence'] = 'objects/espresso/validation/run_success.json'
        dump(integration, report)


def run(command, cwd=None, capture=False):
    result = subprocess.run(command, cwd=cwd, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else None


def main():
    proof = verified_run()  # Gate before authentication, cloning, commits or push.
    for name in ('git', 'gh'):
        if shutil.which(name) is None:
            raise RuntimeError('Required command missing: ' + name)
    run(['gh', 'auth', 'status', '--hostname', 'github.com'])
    user = json.loads(run(['gh', 'api', 'user'], capture=True))
    clone = Path(tempfile.mkdtemp(prefix='isaac-espresso-revision-'))
    print('Working copy retained at: ' + str(clone), flush=True)
    git = ['git', '-c', 'credential.helper=', '-c', 'credential.helper=!gh auth git-credential']
    run(git + ['clone', '--depth', '1', '--branch', 'main', 'https://github.com/' + REPOSITORY + '.git', str(clone)])
    archive_revision(clone, proof)
    run(git + ['config', 'user.name', user.get('name') or user['login']], cwd=clone)
    run(git + ['config', 'user.email', str(user['id']) + '+' + user['login'] + '@users.noreply.github.com'], cwd=clone)
    run(git + ['add', '-A', '--', 'objects/espresso', 'objects/catalog.json', 'README.md',
               'docs/ISAAC_LOADING.md', 'validation/integration_static.json'], cwd=clone)
    run(git + ['add', '-f', 'objects/espresso/validation/logs'], cwd=clone)
    run(git + ['diff', '--cached', '--stat'], cwd=clone)
    run(git + ['commit', '-m', 'Update espresso geometry and archive successful server simulation'], cwd=clone)
    run(git + ['push', 'origin', 'HEAD:main'], cwd=clone)
    print('UPLOADED: https://github.com/' + REPOSITORY + '/tree/main/objects/espresso', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError, KeyError) as error:
        print('PUBLISH STOPPED: ' + str(error), file=sys.stderr)
        sys.exit(1)
