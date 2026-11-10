# Render the 5 legend swatches as flat tiles under the identical material, sun, sky and AgX settings as render.py,
# so each swatch shows exactly how a flat hexagon top of that density class appears in the map.
import bpy, numpy as np, math, sys, json
from mathutils import Vector
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from regions import WORK
MODE=sys.argv[1] if len(sys.argv)>1 else 'density'
OUT=f'{WORK}/legend_colors.json' if MODE=='density' else f'{WORK}/legend_colors_election.json'
stops=np.array([0.0,1.0,1.8,2.6,3.4,4.15]); cols=np.array([[215,38,40],[232,84,66],[250,246,240],[244,246,250],[70,135,225],[25,90,215]])/255.
bpy.ops.wm.read_factory_settings(use_empty=True); s=bpy.context.scene
for n,v in enumerate([0,1,2,3,4]):
    if MODE=='election':
        from regions import EL_STOPS, EL_COLS
        rgb=np.array([np.interp([-0.6,-0.3,0,0.3,0.6][n],EL_STOPS,np.array(EL_COLS)[:,k]/255.) for k in range(3)])
    else: rgb=np.array([np.interp(v,stops,cols[:,k]) for k in range(3)])
    rgb=rgb; lin=np.where(rgb<=0.04045,rgb/12.92,((rgb+0.055)/1.055)**2.4)
    bpy.ops.mesh.primitive_plane_add(size=1.0,location=(n*1.5,0,0)); ob=bpy.context.object
    m=bpy.data.materials.new(f'm{n}'); m.use_nodes=True; p=m.node_tree.nodes['Principled BSDF']
    p.inputs['Roughness'].default_value=0.55; p.inputs['Base Color'].default_value=(*lin,1); ob.data.materials.append(m)
sun=bpy.data.lights.new('sun','SUN'); sun.energy=6.0; sun.angle=math.radians(0.6); sun.color=(1.0,0.93,0.84)
so=bpy.data.objects.new('sun',sun); s.collection.objects.link(so)
from regions import SUN_EL, SUN_AZ; elev=math.radians(SUN_EL); az=math.radians(SUN_AZ)
so.rotation_euler=Vector((math.sin(az)*math.cos(elev),math.cos(az)*math.cos(elev),math.sin(elev))).to_track_quat('Z','Y').to_euler()
w=bpy.data.worlds.new('w'); s.world=w; w.use_nodes=True
w.node_tree.nodes['Background'].inputs['Color'].default_value=(0.55,0.65,0.85,1); w.node_tree.nodes['Background'].inputs['Strength'].default_value=0.35
cam=bpy.data.cameras.new('c'); cam.type='ORTHO'; cam.ortho_scale=7.5; co=bpy.data.objects.new('c',cam); s.collection.objects.link(co); s.camera=co
tilt=math.radians(50); co.location=(3.0,-10*math.sin(tilt),10*math.cos(tilt)); co.rotation_euler=(tilt,0,0)   # same view angle as the map
s.render.engine='CYCLES'; s.cycles.samples=64; s.cycles.use_denoising=True; s.cycles.max_bounces=4
s.render.resolution_x=750; s.render.resolution_y=150
s.view_settings.view_transform='AgX'; s.view_settings.look='AgX - Medium High Contrast'
s.render.filepath=f'{WORK}/legend_tiles.png'; bpy.ops.render.render(write_still=True)
from PIL import Image
a=np.asarray(Image.open(f'{WORK}/legend_tiles.png').convert('RGB')).astype(float)
res=[a[70:80,int((n*1.5-3.0+3.75)/7.5*750)-5:int((n*1.5-3.0+3.75)/7.5*750)+5].reshape(-1,3).mean(0).round().tolist() for n in range(5)]
json.dump(res,open(OUT,'w')); print(res)
