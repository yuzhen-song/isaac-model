"""Render the recorded Isaac hinge trajectory on the server without RTX."""
import csv
import math
import shutil
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT, FPS = 960, 640, 24

def unit(vector):
    return vector / np.linalg.norm(vector)

def geometry():
    # Same hinge-centred transforms as the USD scene, in millimetres.
    offsets = {"waff_bottom": (12.5,18.5,85.11), "waff_top": (12.5,12.5,85),
               "stick": (10,18.5,34.42206632), "lid": (10,27.97078405,37)}
    facet = np.dtype([("normal","<f4",3), ("vertices","<f4",(3,3)), ("flags","<u2")])
    parts = []
    for name, (cx,cy,cz) in offsets.items():
        raw = (ROOT/"source_cad"/(name+".STL")).read_bytes()
        count = int.from_bytes(raw[80:84],"little")
        if len(raw) != 84 + 50*count or not count:
            raise ValueError("Invalid binary STL: " + name)
        triangles = np.frombuffer(raw, facet, count=count, offset=84)["vertices"]
        points, indices = np.unique(triangles.reshape(-1,3),axis=0,return_inverse=True)
        x,y,z = points.T
        aligned = .001*np.column_stack((x-cx,cz-z,y-cy))
        parts.append((aligned, indices.reshape(-1,3), name=="waff_top"))
    return parts

def frame(parts, angle):
    a = math.radians(angle)
    rotation = np.array([[math.cos(a),0,-math.sin(a)], [0,1,0], [math.sin(a),0,math.cos(a)]])
    eye = unit(np.array([.65,-1,.6]))
    right = unit(np.cross([0,0,1],eye))
    up = np.cross(eye,right)
    lamp = unit(np.array([.25,-.45,1]))
    polygons, depths, colors = [], [], []
    for points, faces, moving in parts:
        v = points @ rotation.T if moving else points
        tri = v[faces]
        normals = np.cross(tri[:,1]-tri[:,0], tri[:,2]-tri[:,0])
        visible = (normals @ eye) > 0
        normals = normals[visible]
        normals /= np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-15)
        light = .55+.45*np.maximum(0,normals @ lamp)
        tint = [221,223,225] if moving else [159,177,188]
        colors.append((light[:,None]*tint).astype(np.uint8))
        centered = v - [.085,0,.074]
        screen = np.column_stack((WIDTH/2+2300*(centered @ right), HEIGHT/2-2300*(centered @ up)))
        polygons.append(screen[faces[visible]].round().astype(int))
        depths.append((tri[visible].mean(axis=1) @ eye))
    poly = np.concatenate(polygons)
    rgb = np.concatenate(colors)
    canvas = Image.new("RGB",(WIDTH,HEIGHT),(36,42,49))
    draw = ImageDraw.Draw(canvas)
    for i in np.argsort(np.concatenate(depths)):
        draw.polygon(poly[i].flatten().tolist(), fill=tuple(map(int,rgb[i])))
    draw.text((24,24), "Isaac Sim | recorded hinge motion     %.1f deg" % angle, fill="white")
    return canvas.tobytes()

def main():
    trace = ROOT/"motion.csv"
    if not trace.is_file():
        trace = ROOT/"validation/motion.csv"
    with trace.open() as f:
        rows = list(csv.DictReader(f))
    t = np.array([float(r["time_s"]) for r in rows])
    q = np.array([float(r["actual_open_deg"]) for r in rows])
    if len(t)<2 or not np.isfinite(q).all() or not (np.diff(t)>0).all() or max(q)<87 or abs(q[-1])>3:
        raise ValueError("Expected a complete measured open/close cycle")
    encoder = shutil.which("ffmpeg")
    if not encoder:
        import imageio_ffmpeg
        encoder = imageio_ffmpeg.get_ffmpeg_exe()
    out = ROOT/"waff_open_close.mp4"
    partial = ROOT/"waff_open_close.partial.mp4"
    parts = geometry()
    cmd = [encoder,"-hide_banner","-loglevel","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s","960x640","-r",str(FPS),"-i","-","-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart",str(partial)]
    cache = {}
    with subprocess.Popen(cmd,stdin=subprocess.PIPE) as proc:
        try:
            for tick in np.arange(t[0],t[-1]+1/FPS,1/FPS):
                angle = round(float(np.interp(tick,t,q)),1)
                if angle not in cache:
                    if len(cache)>=8:
                        cache.pop(next(iter(cache)))
                    cache[angle] = frame(parts, angle)
                proc.stdin.write(cache[angle])
        finally:
            proc.stdin.close()
        if proc.wait():
            raise RuntimeError("Video encoder failed")
    partial.replace(out)
    print(out)
if __name__ == "__main__":
    main()
