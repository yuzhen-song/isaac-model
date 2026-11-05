"""Run the delivered dynamic scene without replacing its passive hinge brake."""
import argparse
import json
import math
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--headless', action='store_true')
parser.add_argument('--seconds', type=float, default=10.)
args, unknown = parser.parse_known_args()
if not math.isfinite(args.seconds) or args.seconds <= 0:
    parser.error('--seconds must be positive and finite')

from isaacsim import SimulationApp
app = SimulationApp({'headless': args.headless, 'anti_aliasing': 0})
try:
    import numpy as np
    import omni.usd
    import omni.physx
    from pxr import UsdPhysics
    from isaacsim.core.api import SimulationContext

    root = Path(__file__).resolve().parent
    assert omni.usd.get_context().open_stage(str(root / 'microwave_test.usda'))
    for _ in range(30):
        app.update()
    stage = omni.usd.get_context().get_stage()
    params = json.loads((root / 'joint_parameters.json').read_text(encoding='utf-8'))
    body_path = '/World/Microwave/Body'
    handle_path = '/World/Microwave/Door'
    joint = UsdPhysics.RevoluteJoint.Get(stage, '/World/Microwave/door_hinge')
    assert joint.GetLowerLimitAttr().Get() == -math.inf
    assert joint.GetUpperLimitAttr().Get() == math.inf
    assert not UsdPhysics.RigidBodyAPI(stage.GetPrimAtPath(body_path)).GetKinematicEnabledAttr().Get()
    for path, mass in [(body_path, params['mass_body_rigid_assembly_kg']),
                       (handle_path, params['mass_door_kg'])]:
        assert math.isclose(UsdPhysics.MassAPI(stage.GetPrimAtPath(path)).GetMassAttr().Get(), mass, rel_tol=1e-6)
    brake = UsdPhysics.DriveAPI(joint.GetPrim(), 'angular')
    assert brake.GetStiffnessAttr().Get() == 0
    assert brake.GetTargetVelocityAttr().Get() == 0
    assert math.isclose(brake.GetMaxForceAttr().Get(), .02, rel_tol=1e-6)
    print('Dynamic scene: PLA/15%-infill estimated masses, unlimited rotation, passive 0.02 Nm brake cap. No motion command is applied.', flush=True)
    sim = SimulationContext(physics_dt=1/120, rendering_dt=1/60, stage_units_in_meters=1)
    sim.initialize_physics()
    sim.play()
    interface = omni.physx.get_physx_interface()
    samples = []
    for step in range(math.ceil(args.seconds * 120)):
        sim.step(render=not args.headless)
        if step % 120 == 0 or step == math.ceil(args.seconds * 120) - 1:
            row = {'time_s': (step + 1) / 120}
            for name, path in [('body', body_path), ('handle', handle_path)]:
                pose = interface.get_rigidbody_transformation(path)
                if not pose.get('ret_val', False):
                    raise RuntimeError(f'PhysX did not return a valid pose for {path}')
                position = np.array(pose['position'], dtype=float)
                rotation = np.array(pose['rotation'], dtype=float)
                if not (np.isfinite(position).all() and np.isfinite(rotation).all()):
                    raise RuntimeError(f'Non-finite state at {path}')
                row[name] = {'position_m': position.tolist(), 'quaternion_xyzw': rotation.tolist()}
                if not -.05 < position[2] < .5:
                    raise RuntimeError(f'Body fell through table or left expected scene: {path}: {position}')
            samples.append(row)
            print(json.dumps(row), flush=True)
    output = root / 'runtime_results'
    output.mkdir(exist_ok=True)
    report = {'finite_supported_poses_observed': True, 'samples': samples,
              'scope': 'passive dynamic-scene smoke check only; no grasp, friction calibration or robot task validation'}
    (output / 'passive_scene_result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    sim.stop()
finally:
    app.close()
