"""Standalone Isaac Sim 5.1 loading smoke check; not a robot task test."""
import argparse
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--object", choices=("microwave", "espresso", "espressomachine", "waffleiron", "mixer"), default="microwave")
parser.add_argument("--headless", action="store_true")
parser.add_argument("--seconds", type=float, default=3.)
args, unknown = parser.parse_known_args()
if not 0 < args.seconds < 3600:
    parser.error("--seconds must be positive and below 3600")

from isaacsim import SimulationApp
app = SimulationApp({"headless": args.headless, "anti_aliasing": 0})
try:
    import math
    import omni.usd
    from pxr import Gf, UsdGeom, UsdLux, UsdPhysics
    from isaacsim.core.api import SimulationContext
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.spawn_object import spawn_object

    omni.usd.get_context().new_stage()
    stage = omni.usd.get_context().get_stage()
    UsdGeom.SetStageMetersPerUnit(stage, 1.)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    physics = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
    physics.CreateGravityDirectionAttr(Gf.Vec3f(0, 0, -1))
    physics.CreateGravityMagnitudeAttr(9.81)
    table = UsdGeom.Cube.Define(stage, "/World/Table")
    table.CreateSizeAttr(1.)
    table.AddTranslateOp().Set(Gf.Vec3d(0, 0, -.051))
    table.AddScaleOp().Set(Gf.Vec3f(2, 2, .1))
    UsdPhysics.CollisionAPI.Apply(table.GetPrim())
    UsdLux.DomeLight.Define(stage, "/World/Light").CreateIntensityAttr(1500.)
    info = spawn_object(stage, args.object, "/World/Objects/Object")
    print(json.dumps(info, indent=2), flush=True)
    sim = SimulationContext(physics_dt=1/120, rendering_dt=1/60, stage_units_in_meters=1.)
    sim.initialize_physics()
    sim.play()
    for _ in range(math.ceil(args.seconds * 120)):
        sim.step(render=not args.headless)
    sim.stop()
    print("LOAD_SMOKE_CHECK_COMPLETED: " + args.object, flush=True)
finally:
    app.close()
