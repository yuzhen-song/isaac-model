"""Geometric layer integration for the supplied mixer and waffle iron STLs.
Run with Python, numpy, trimesh and manifold3d. Input paths are package-local.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

DENSITY = 1.26  # g/cm3, PLA extruder 1 in lid.3mf
HEIGHT = 0.2
WALL = 0.42 + 0.45
BOTTOM, TOP = 3, 5
INFILL = 0.15
Y_UP = [[1,0,0],[0,0,-1],[0,1,0]]
Z_DOWN = [[1,0,0],[0,-1,0],[0,0,-1]]

def planar_moments(section):
    # Signed polygon integrals of 1,x,y,x^2,xy,y^2, including holes.
    out = np.zeros(6)
    for loop in section.to_polygons():
        x,y = loop.T
        u,v = np.roll(loop,-1,axis=0).T
        cross = x*v-u*y
        out += [cross.sum()/2, ((x+u)*cross).sum()/6, ((y+v)*cross).sum()/6,
                ((x*x+x*u+u*u)*cross).sum()/12,
                ((2*x*y+x*v+u*y+2*u*v)*cross).sum()/24,
                ((y*y+y*v+v*v)*cross).sum()/12]
    return out

def estimate(path,rotation):
    mesh=trimesh.load(path,force="mesh")
    if not mesh.is_volume:
        raise ValueError(f"Expected a closed outward-oriented mesh: {path}")
    solid=mf.Manifold(mf.Mesh(np.asarray(mesh.vertices @ rotation.T,dtype=np.float32),
                              np.asarray(mesh.faces,dtype=np.uint32)))
    if solid.status()!=mf.Error.NoError:
        raise ValueError(f"{path}: {solid.status()}")
    low,high=np.asarray(solid.bounding_box())[[2,5]]
    count=math.ceil((high-low)/HEIGHT)
    dz=np.minimum(HEIGHT,high-low-np.arange(count)*HEIGHT)
    centers=low+np.arange(count)*HEIGHT+dz/2
    sections=[solid.slice(z) for z in centers]
    total=core_volume=plastic=0.
    first=np.zeros(3)
    second=np.zeros((3,3))
    for i,(section,z,h) in enumerate(zip(sections,centers,dz)):
        full=planar_moments(section)
        core=mf.CrossSection()
        if BOTTOM<=i<count-TOP:
            core=section.offset(-WALL,mf.JoinType.Miter)
            for j in range(i-BOTTOM,i+TOP+1):
                if j!=i:
                    core=core ^ sections[j]
                if core.is_empty():
                    break
        inner=planar_moments(core)
        a,x,y,xx,xy,yy=full-(1-INFILL)*inner
        total+=h*full[0]
        core_volume+=h*inner[0]
        plastic+=h*a
        first+=h*np.array([x,y,a*z])
        second+=h*np.array([[xx,xy,x*z],[xy,yy,y*z],[x*z,y*z,a*(z*z+h*h/12)]])
    correction=mesh.volume/total
    if not .97<correction<1.03:
        raise ValueError(f"Unexpected integrated volume correction {correction}")
    center=first/plastic
    covariance=rotation.T @ (second/plastic-np.outer(center,center)) @ rotation
    pla=plastic*correction
    return dict(stl_volume_mm3=mesh.volume,shell_volume_mm3=(total-core_volume)*correction,
                core_volume_mm3=core_volume*correction,pla_volume_mm3=pla,
                mass_g=pla*DENSITY/1000,source_center_mm=(rotation.T @ center).tolist(),
                source_covariance_mm2=covariance.tolist(),layer_volume_normalization=correction,
                print_rotation=rotation.tolist(),layers=count,
                stl_sha256=hashlib.sha256(path.read_bytes()).hexdigest())

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("folder",type=Path)
    args=parser.parse_args()
    d=args.folder
    parts={}
    for f in sorted((d/"source_cad").glob("*.STL")):
        rotation=np.eye(3)
        if f.stem in ("waff_bottom","waff_top"):
            rotation=np.array(Y_UP,dtype=float)
        elif f.stem=="stick":
            rotation=np.array(Z_DOWN,dtype=float)
        parts[f.stem]=estimate(f,rotation)
        print(f.stem,round(parts[f.stem]["mass_g"],3),flush=True)
    data=dict(profile_source="Waffle iron lid.3mf, Bambu project settings, extruder 1. Same profile assumed for mixer and waffle top.",
              orientation="Waffle base +Y, pin -Z and cap +Z from 3MF. Waffle top assumed +Y; mixer parts assumed STL +Z.",
              method="Closed STL volumes, layer cross sections, solid walls and skins, 15% core; integrate first and second moments of printed material. Scaled to the signed solid mesh volume.",
              exclusions=["supports","brim","purge","toolpath overlaps","variable width","bridges"],density_g_cm3=DENSITY,
              infill_fraction=INFILL,wall_mm=WALL,layer_height_mm=HEIGHT,top_layers=TOP,bottom_layers=BOTTOM,
              parts=parts,total_mass_g=sum(x["mass_g"] for x in parts.values()))
    (d/"recalculated_parts.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
if __name__=="__main__":
    main()
