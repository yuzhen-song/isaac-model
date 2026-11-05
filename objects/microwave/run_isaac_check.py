"""Run with Isaac Sim 5.1's Python; this is a joint motion test, not a grasp test."""
import argparse,csv,json,math,sys
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--headless',action='store_true')
args,unknown=parser.parse_known_args()
from isaacsim import SimulationApp
app=SimulationApp({'headless':args.headless, 'anti_aliasing':0})
try:
    import numpy as np
    import omni.usd,omni.physx
    from pxr import UsdPhysics,UsdGeom,Gf
    from isaacsim.core.api import SimulationContext
    root=Path(__file__).resolve().parent
    assert omni.usd.get_context().open_stage(str(root/'microwave_fixed_base.usda'))
    for _ in range(30):app.update()
    stage=omni.usd.get_context().get_stage()
    joint=UsdPhysics.RevoluteJoint.Get(stage,'/World/Microwave/door_hinge')
    drive=UsdPhysics.DriveAPI.Apply(joint.GetPrim(),'angular')
    drive.CreateTypeAttr('force');drive.CreateStiffnessAttr(1.0);drive.CreateDampingAttr(.05);drive.CreateMaxForceAttr(.1);drive.CreateTargetPositionAttr(0.0)
    # In memory ONLY, this motor replaces the passive brake for isolated joint testing.
    # This check does not validate hinge resistance, base stability, or grasp success.
    sim=SimulationContext(physics_dt=1/120,rendering_dt=1/60,stage_units_in_meters=1)
    sim.initialize_physics();sim.play()
    px=omni.physx.get_physx_interface()
    expected=np.array(json.loads((root/'joint_parameters.json').read_text())['origin_xyz'])
    rows=[];targets=[0,30,0,-30,-60,-90,-120,-90,-60,-30,0]
    for target in targets:
        drive.GetTargetPositionAttr().Set(float(target))
        for step in range(360):
            sim.step(render=not args.headless)
            pose=px.get_rigidbody_transformation('/World/Microwave/Door')
            if not pose.get('ret_val',False):raise RuntimeError('PhysX handle pose unavailable; do not treat the stage loading as a pass.')
            position=np.array(pose['position'],float);q=np.array(pose['rotation'],float)
            assert np.isfinite(position).all() and np.isfinite(q).all(),'Non-finite rigid body state'
            angle=math.degrees(2*math.atan2(q[2],q[3]));angle=(angle+180)%360-180
            off_axis=math.degrees(2*math.asin(min(1.,float(np.linalg.norm(q[:2])))))
            rows.append({'target_deg':target,'step':step,'actual_deg':angle,'anchor_error_m':float(np.linalg.norm(position-expected)),'off_axis_deg':off_axis})
        print('target=',target,'actual=',rows[-1]['actual_deg'],'anchor_error_m=',rows[-1]['anchor_error_m'],flush=True)
    finals=[rows[(i+1)*360-1] for i in range(len(targets))]
    checks={'target_error_under_3deg':all(abs(r['target_deg']-r['actual_deg'])<3 for r in finals),'anchor_error_under_0p5mm':max(r['anchor_error_m'] for r in rows)<.0005,'off_axis_under_1deg':max(r['off_axis_deg'] for r in rows)<1,'unlimited_joint_authored':math.isinf(joint.GetLowerLimitAttr().Get()) and joint.GetLowerLimitAttr().Get()<0 and math.isinf(joint.GetUpperLimitAttr().Get()) and joint.GetUpperLimitAttr().Get()>0, 'crossed_old_lower_limit':min(r['actual_deg'] for r in finals)<-20, 'reached_open_minus_120deg':min(r['actual_deg'] for r in finals)<-110}
    output=root/'runtime_results';output.mkdir(exist_ok=True)
    with (output/'joint_motion.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    report={'passed':all(checks.values()),'checks':checks,'finals':finals,'scope':'fixed-base motor test replaces the passive brake IN MEMORY; no validation of friction, dynamic base stability, robot grasp, or sim2real'}
    (output/'runtime_result.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)
    sim.stop()
    if not report['passed']:raise RuntimeError('Joint validation failed; see runtime_results.')
finally:
    app.close()
