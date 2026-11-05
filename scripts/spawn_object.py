"""Reference a delivered object into an existing stopped, metre/Z-up USD stage.

Import this after SimulationApp starts. No SimulationApp or new stage is created.
The returned paths are resolved for this instance, including remapped materials.
"""
import json
import math
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def spawn_object(stage, object_name, prim_path, position=(0., 0., 0.),
                 orientation_wxyz=(1., 0., 0., 0.)):
    from pxr import Gf, Sdf, UsdGeom, UsdPhysics

    if not math.isclose(UsdGeom.GetStageMetersPerUnit(stage), 1., rel_tol=1e-8):
        raise ValueError("Host stage must use metres; do not apply an extra 0.001 scale")
    if UsdGeom.GetStageUpAxis(stage) != UsdGeom.Tokens.z:
        raise ValueError("Host stage must be Z-up")
    path = Sdf.Path(prim_path)
    if not path.IsAbsolutePath() or not path.IsPrimPath() or path == Sdf.Path.absoluteRootPath:
        raise ValueError("prim_path must be an absolute non-root USD prim path")
    if stage.GetPrimAtPath(path):
        raise ValueError("Destination already exists; remove the old asset explicitly before replacement")
    for parent in path.GetParentPath().GetPrefixes():
        prim = stage.GetPrimAtPath(parent)
        if prim and prim.HasAPI(UsdPhysics.RigidBodyAPI):
            raise ValueError("Do not nest this assembly inside another rigid body")
    if len(position) != 3 or not all(math.isfinite(v) for v in position):
        raise ValueError("position must contain three finite metre values")
    if len(orientation_wxyz) != 4 or not all(math.isfinite(v) for v in orientation_wxyz):
        raise ValueError("orientation_wxyz must contain four finite values")
    if not math.isclose(sum(v * v for v in orientation_wxyz), 1., abs_tol=1e-6):
        raise ValueError("orientation_wxyz must be a unit quaternion in w,x,y,z order")
    catalog = json.loads((REPOSITORY_ROOT / "objects/catalog.json").read_text(encoding="utf-8"))
    matches = [item for item in catalog["objects"]
               if object_name in (item["name"], item.get("arctic_name"))]
    if len(matches) != 1:
        raise ValueError("Unknown object: " + object_name)
    item = matches[0]
    entry = item["integration"]
    asset = (REPOSITORY_ROOT / item["path"] / entry["asset_file"]).resolve()
    if not asset.is_file():
        raise FileNotFoundError(asset)
    root = UsdGeom.Xform.Define(stage, path)
    root.GetPrim().GetReferences().AddReference(asset.as_posix())
    if not stage.GetPrimAtPath(path.AppendPath(entry["body_relative_path"])):
        raise RuntimeError("Asset failed to compose: " + asset.as_posix())
    root.AddTranslateOp().Set(Gf.Vec3d(*position))
    root.AddOrientOp().Set(Gf.Quatf(orientation_wxyz[0], Gf.Vec3f(*orientation_wxyz[1:])))
    resolved = {"root": str(path), "asset_file": asset.as_posix(), "arctic_name": item["arctic_name"]}
    for key in ("body", "moving", "hinge"):
        resolved[key] = str(path.AppendPath(entry[key + "_relative_path"]))
    return resolved
