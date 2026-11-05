"""Record a physical open/close demo using the updated Espresso USD scene.

Run in Isaac Sim 5.1's Python, alongside espresso_test.usda and
joint_parameters.json. The passive hinge brake, print masses, and unlimited
joint remain unchanged. An external test torque turns the handle and applies
the equal-and-opposite reaction to the dynamic machine body.

This is a scripted actuation demonstration, not a robot grasp demonstration.
"""
import argparse
import csv
import json
import math
from pathlib import Path


def reference(t, amplitude):
    """Radians and radians/sec: hold, quintic open, hold, close, hold (11 s)."""
    if t <= 1.:
        return 0., 0.
    if t < 5.:
        u = (t - 1.) / 4.
        return amplitude * (10*u**3 - 15*u**4 + 6*u**5), amplitude * (30*u**2 - 60*u**3 + 30*u**4) / 4.
    if t <= 6.:
        return amplitude, 0.
    if t < 10.:
        u = (t - 6.) / 4.
        return amplitude * (1. - 10*u**3 + 15*u**4 - 6*u**5), -amplitude * (30*u**2 - 60*u**3 + 30*u**4) / 4.
    return 0., 0.


def quat_mul(a, b):
    x, y, z, w = a
    X, Y, Z, W = b
    return (w*X + x*W + y*Z - z*Y, w*Y - x*Z + y*W + z*X,
            w*Z + x*Y - y*X + z*W, w*W - x*X - y*Y - z*Z)


def axis_and_angle(q_body, q_handle):
    relative = quat_mul((-q_body[0], -q_body[1], -q_body[2], q_body[3]), q_handle)
    angle = 2. * math.atan2(relative[2], relative[3])
    angle = (angle + math.pi) % (2. * math.pi) - math.pi
    rotated = quat_mul(quat_mul(q_body, (0., 0., 1., 0.)),
                       (-q_body[0], -q_body[1], -q_body[2], q_body[3]))
    return rotated[:3], angle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--angle', type=float, default=-90., help='Demo target, not a joint limit')
    parser.add_argument('--output', default='espresso_open_close_updated.mp4')
    args, unknown = parser.parse_known_args()
    if not math.isfinite(args.angle):
        parser.error('--angle must be finite')
    root = Path(__file__).resolve().parent
    for name in ['espresso_test.usda', 'joint_parameters.json']:
        if not (root / name).is_file():
            parser.error(f'Place this script in the NEW scene directory; missing: {root / name}')
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.stem + '.partial.mp4')

    from isaacsim import SimulationApp
    app = SimulationApp({'headless': args.headless, 'anti_aliasing': 0,
                         'width': 1280, 'height': 720})
    writer = None
    rgb = None
    render_product = None
    sim = None
    rows = []
    count = 0
    complete = False
    try:
        import numpy as np
        import imageio.v2 as imageio
        import carb
        import omni.usd
        import omni.replicator.core as rep
        from omni.isaac.dynamic_control import _dynamic_control
        from pxr import UsdPhysics
        from isaacsim.core.api import SimulationContext

        assert omni.usd.get_context().open_stage(str(root / 'espresso_test.usda'))
        for _ in range(30):
            app.update()
        stage = omni.usd.get_context().get_stage()
        params = json.loads((root / 'joint_parameters.json').read_text(encoding='utf-8'))
        body_path = '/World/Espresso/Body'
        handle_path = '/World/Espresso/Handle'
        joint = UsdPhysics.RevoluteJoint.Get(stage, '/World/Espresso/handle_hinge')
        brake = UsdPhysics.DriveAPI(joint.GetPrim(), 'angular')
        assert joint.GetLowerLimitAttr().Get() == -math.inf
        assert joint.GetUpperLimitAttr().Get() == math.inf
        assert not UsdPhysics.RigidBodyAPI(stage.GetPrimAtPath(body_path)).GetKinematicEnabledAttr().Get()
        assert brake.GetStiffnessAttr().Get() == 0
        assert brake.GetTargetVelocityAttr().Get() == 0
        assert math.isclose(brake.GetMaxForceAttr().Get(), .02, rel_tol=1e-6)
        for path, mass in [(body_path, params['mass_body_rigid_assembly_kg']),
                           (handle_path, params['mass_handle_kg'])]:
            assert math.isclose(UsdPhysics.MassAPI(stage.GetPrimAtPath(path)).GetMassAttr().Get(), mass, rel_tol=1e-6)
        assert stage.GetPrimAtPath('/World/Camera').IsValid()
        print('Scene checks passed: print masses; dynamic base; unlimited hinge; 0.02 Nm brake cap preserved.', flush=True)
        print(f'Recording 0 -> {args.angle:g} -> 0 degrees, 1280x720, 30 fps. External test torque, no robot.', flush=True)

        rep.orchestrator.set_capture_on_play(False)
        render_product = rep.create.render_product('/World/Camera', (1280, 720))
        rgb = rep.AnnotatorRegistry.get_annotator('rgb')
        rgb.attach([render_product])
        sim = SimulationContext(physics_dt=1/120, rendering_dt=1/30, stage_units_in_meters=1)
        sim.initialize_physics()
        sim.play()
        for _ in range(60):
            sim.step(render=False)
        dc = _dynamic_control.acquire_dynamic_control_interface()
        body_handle = dc.get_rigid_body(body_path)
        hand_handle = dc.get_rigid_body(handle_path)
        if body_handle == _dynamic_control.INVALID_HANDLE or hand_handle == _dynamic_control.INVALID_HANDLE:
            raise RuntimeError('PhysX rigid-body handle unavailable; cannot apply physical torque')
        # Warm up rendering without advancing physics time.
        for _ in range(8):
            rep.orchestrator.step(delta_time=0., pause_timeline=False, rt_subframes=2)

        def state():
            body_pose = dc.get_rigid_body_pose(body_handle)
            hand_pose = dc.get_rigid_body_pose(hand_handle)
            qb = tuple(float(body_pose.r[i]) for i in range(4))
            qh = tuple(float(hand_pose.r[i]) for i in range(4))
            axis, wrapped = axis_and_angle(qb, qh)
            wb = dc.get_rigid_body_angular_velocity(body_handle)
            wh = dc.get_rigid_body_angular_velocity(hand_handle)
            velocity = sum(axis[i] * (float(wh[i]) - float(wb[i])) for i in range(3))
            position = [float(body_pose.p[i]) for i in range(3)]
            if not all(math.isfinite(v) for v in (*qb, *qh, *axis, wrapped, velocity, *position)):
                raise RuntimeError('Non-finite PhysX state')
            if not -.05 < position[2] < .5:
                raise RuntimeError('Dynamic body fell through the table or left the scene')
            return axis, wrapped, velocity, position

        _, last_wrapped, _, initial_body_position = state()
        accumulated = last_wrapped
        writer = imageio.get_writer(str(partial), fps=30, codec='libx264',
                                   pixelformat='yuv420p', macro_block_size=1,
                                   ffmpeg_params=['-crf', '18'])
        amplitude = math.radians(args.angle)
        frame_stats = []
        max_body_shift = 0.
        for step in range(1320):
            t = (step + 1) / 120.
            target, target_velocity = reference(t, amplitude)
            axis, wrapped, velocity, body_position = state()
            accumulated += (wrapped - last_wrapped + math.pi) % (2. * math.pi) - math.pi
            last_wrapped = wrapped
            error = target - accumulated
            # Smooth friction compensation plus PD feedback. The existing USD
            # brake stays enabled; no pose/velocity teleport or drive replacement.
            torque = .12 * error + .006 * (target_velocity - velocity)
            torque += .02 * math.tanh((target_velocity + 5. * error) / .01)
            torque = max(-.06, min(.06, torque))
            vector = carb.Float3(*(torque * v for v in axis))
            reaction = carb.Float3(*(-torque * v for v in axis))
            dc.wake_up_rigid_body(hand_handle)
            dc.wake_up_rigid_body(body_handle)
            if not dc.apply_body_torque(hand_handle, vector, True):
                raise RuntimeError('PhysX rejected handle torque')
            if not dc.apply_body_torque(body_handle, reaction, True):
                raise RuntimeError('PhysX rejected body reaction torque')
            sim.step(render=False)
            _, wrapped_after, _, position_after = state()
            actual_after = accumulated + (wrapped_after - last_wrapped + math.pi) % (2. * math.pi) - math.pi
            shift = math.dist(initial_body_position, position_after)
            max_body_shift = max(max_body_shift, shift)
            rows.append({'time_s': t, 'target_deg': math.degrees(target),
                         'actual_deg': math.degrees(actual_after),
                         'applied_motor_torque_Nm': torque, 'body_shift_m': shift})
            if (step + 1) % 4 == 0:
                rep.orchestrator.step(delta_time=0., pause_timeline=False, rt_subframes=2)
                frame = np.asarray(rgb.get_data())
                if frame.ndim != 3 or frame.shape[:2] != (720, 1280) or frame.shape[2] < 3:
                    raise RuntimeError(f'Invalid camera RGB frame: {frame.shape}')
                frame = np.ascontiguousarray(frame[:, :, :3], dtype=np.uint8)
                if count % 30 == 0:
                    frame_stats.append(float(frame.std()))
                    print(f't={t:4.1f}s target={math.degrees(target):6.2f} actual={math.degrees(actual_after):6.2f} deg | frame {count + 1}/330', flush=True)
                writer.append_data(frame)
                count += 1
        if count != 330 or not frame_stats or max(frame_stats) < 1.:
            raise RuntimeError('Video frames are incomplete or appear blank')
        writer.close()
        writer = None
        partial.replace(output)
        opened = [r for r in rows if 5.5 <= r['time_s'] <= 6.]
        closed = [r for r in rows if 10.5 <= r['time_s'] <= 11.]
        checks = {
            'open_hold_error_under_3deg': max(abs(r['actual_deg'] - args.angle) for r in opened) < 3.,
            'closed_hold_error_under_3deg': max(abs(r['actual_deg']) for r in closed) < 3.,
            'video_330_nonempty_frames': count == 330,
            'unlimited_hinge_and_original_brake_preserved': True,
        }
        report = {'motion_checks_passed': all(checks.values()), 'checks': checks,
                  'video': str(output), 'fps': 30, 'frames': count, 'duration_s': 11.,
                  'max_body_shift_m': max_body_shift,
                  'scope': 'external motor torque demonstration; dynamic base and passive brake preserved; no robot grasp or calibrated friction verification'}
        output.with_suffix('.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        with output.with_suffix('.csv').open('w', newline='', encoding='utf-8') as stream:
            csv_writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            csv_writer.writeheader()
            csv_writer.writerows(rows)
        complete = True
        print(f'Video saved: {output}', flush=True)
        print(json.dumps(report, indent=2), flush=True)
        if not report['motion_checks_passed']:
            raise RuntimeError('Video was saved, but motion tracking checks failed; send the JSON/CSV report')
    finally:
        if writer is not None:
            writer.close()
        if not complete and count:
            print(f'Recording incomplete; partial file: {partial} ({count} frames)', flush=True)
        if sim is not None:
            sim.stop()
        if rgb is not None:
            rgb.detach()
        if render_product is not None:
            render_product.destroy()
        app.close()


if __name__ == '__main__':
    main()
