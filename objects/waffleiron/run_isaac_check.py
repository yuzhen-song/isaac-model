"""Headless Isaac Sim 5.1 fixed-base opening and closing smoke test."""
from pathlib import Path
import csv
import json
import math
import traceback
import os
import sys
from isaacsim import SimulationApp

app = SimulationApp({"headless": True, "anti_aliasing": 0})
root = Path(__file__).resolve().parent

def run():
    import omni.usd
    import omni.physx
    import numpy as np
    from pxr import UsdPhysics
    from isaacsim.core.api import SimulationContext

    ctx = omni.usd.get_context()
    if not ctx.open_stage(str(root / "waff.usdc")):
        raise RuntimeError("Could not open waff.usdc")
    for _ in range(30):
        app.update()
    joint = ctx.get_stage().GetPrimAtPath("/Waff/Hinge")
    drive = UsdPhysics.DriveAPI.Apply(joint, "angular")
    drive.CreateTypeAttr("force")
    drive.CreateStiffnessAttr(1.5)
    drive.CreateDampingAttr(.08)
    drive.CreateMaxForceAttr(5.)
    target = drive.CreateTargetPositionAttr(0.)
    sim = SimulationContext(physics_dt=1/120, rendering_dt=1/60, stage_units_in_meters=1)
    sim.initialize_physics()
    sim.play()
    physx = omni.physx.get_physx_interface()
    rows, finals = [], []
    for goal in [0, 30, 60, 90, 60, 30, 0]:
        target.Set(float(-goal))
        for _ in range(360):
            sim.step(render=False)
            pose = physx.get_rigidbody_transformation("/Waff/Top")
            if not pose.get("ret_val"):
                raise RuntimeError("PhysX top pose unavailable")
            q = np.asarray(pose["rotation"])
            angle = (-math.degrees(2*math.atan2(q[1], q[3]))+180)%360-180
            drift = np.linalg.norm(np.asarray(pose["position"]) - [0, 0, .0185])
            off_axis = math.degrees(2*math.asin(min(1., np.linalg.norm(q[[0,2]]))))
            if not np.isfinite([*q, angle, drift]).all():
                raise RuntimeError("Non-finite PhysX pose")
            rows.append((len(rows)/120, goal, angle, drift, off_axis))
        finals.append(rows[-1])
        print(f"Target {goal} deg, measured {angle:.2f} deg", flush=True)
    sim.stop()
    passed = (all(abs(r[1]-r[2]) < 3 for r in finals)
              and max(r[3] for r in rows) < .0005 and max(r[4] for r in rows) < 1)
    with (root/"motion.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time_s", "target_open_deg","actual_open_deg","anchor_drift_m","off_axis_deg"])
        writer.writerows(rows)
    (root/"result.json").write_text(json.dumps({"passed":bool(passed), "final_open_deg":[r[2] for r in finals]}, indent=2))
    if not passed:
        raise RuntimeError("Tracking failed; inspect result.json and motion.csv")
    print("WAFF_PASS", flush=True)

try:
    (root/"result.json").write_text('{"passed":false,"status":"started"}')
    run()
except Exception:
    traceback.print_exc()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1)
else:
    app.close()
