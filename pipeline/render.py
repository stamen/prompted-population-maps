# usage: render.py <region> <width_px> <spp> <out.png>   (height is derived from the region's plan-oblique frame)
import bpy, bmesh, numpy as np, math, sys, time, json
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from regions import R, WORK
key,WPX,SPP,OUT=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),sys.argv[4]
d=np.load(f'{WORK}/{key}.npz',allow_pickle=True); c=R[key]
X,Y=d['x'],d['y']; dens=d['pop']/d['area']; n=len(dens)
x0,y0,x1,y1=d['bounds']; S=max(x1-x0,y1-y0)          # all dimensions scale from the Texas design (S=1250 km)
HMAX=0.224*S; h=0.0002*S+dens/dens.max()*HMAX; SLAB=0.0024*S
# colour: same absolute log-density ramp as Texas, so maps are comparable
ld=np.log10(np.clip(dens,1,None)); stops=np.array([0.0,1.0,1.8,2.6,3.4,4.15])
cols=np.array([[215,38,40],[232,84,66],[250,246,240],[244,246,250],[70,135,225],[25,90,215]])/255.
rgb=np.stack([np.interp(ld,stops,cols[:,k]) for k in range(3)],1)
if 'margin' in d.files:   # colour = county two-party margin (D-R)/(D+R): red Republican, blue Democratic
    from regions import EL_STOPS, EL_COLS
    ec=np.array(EL_COLS)/255.; rgb=np.stack([np.interp(d['margin'],EL_STOPS,ec[:,k]) for k in range(3)],1)
lin=np.where(rgb<=0.04045,rgb/12.92,((rgb+0.055)/1.055)**2.4)
V=np.stack([np.concatenate([X,X],1),np.concatenate([Y,Y],1),np.concatenate([np.repeat(h[:,None],6,1),np.zeros((n,6))],1)],-1).reshape(-1,3)
base=(np.arange(n)*12)[:,None]; top=base+np.arange(6)[None,:]
sides=np.stack([np.stack([base[:,0]+a,base[:,0]+6+a,base[:,0]+6+(a+1)%6,base[:,0]+(a+1)%6],1) for a in range(6)],1)
loops=np.concatenate([top,sides.reshape(n,24)],1).reshape(-1); sizes=np.tile([6,4,4,4,4,4,4],n); starts=np.concatenate([[0],np.cumsum(sizes)[:-1]])
bpy.ops.wm.read_factory_settings(use_empty=True); s=bpy.context.scene
me=bpy.data.meshes.new('hex'); me.vertices.add(len(V)); me.vertices.foreach_set('co',V.astype(np.float32).ravel())
me.loops.add(len(loops)); me.loops.foreach_set('vertex_index',loops.astype(np.int32))
me.polygons.add(len(sizes)); me.polygons.foreach_set('loop_start',starts.astype(np.int32)); me.polygons.foreach_set('loop_total',sizes.astype(np.int32))
me.update(calc_edges=True); me.validate()
at=me.attributes.new('col','FLOAT_COLOR','FACE'); at.data.foreach_set('color',np.repeat(np.concatenate([lin,np.ones((n,1))],1),7,0).astype(np.float32).ravel())
ob=bpy.data.objects.new('hex',me); s.collection.objects.link(ob); bpy.context.view_layer.objects.active=ob; ob.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode='OBJECT')
def mat(name,color=None,attr=None,rough=0.55):
    m=bpy.data.materials.new(name); m.use_nodes=True; p=m.node_tree.nodes['Principled BSDF']; p.inputs['Roughness'].default_value=rough
    if attr: a=m.node_tree.nodes.new('ShaderNodeAttribute'); a.attribute_name=attr; m.node_tree.links.new(a.outputs['Color'],p.inputs['Base Color'])
    else: p.inputs['Base Color'].default_value=(*color,1)
    return m
ob.data.materials.append(mat('hexm',attr='col'))
slabm=mat('slab',(0.30,0.27,0.24) if 'margin' in d.files else (0.680,0.019,0.021),rough=0.8)      # uninhabited: neutral for election maps, lowest red class for density
def elcol(m):   # election ramp in linear RGB
    from regions import EL_STOPS, EL_COLS
    ec=np.array(EL_COLS)/255.; r=np.stack([np.interp(m,EL_STOPS,ec[:,k]) for k in range(3)],-1)
    return np.where(r<=0.04045,r/12.92,((r+0.055)/1.055)**2.4)
if 'ctris' in d.files:   # election maps: slab built from county polygons, each in its county's result colour
    T=d['ctris']; nt=len(T); C=elcol(d['ctm'])
    vt=[np.dstack([T,np.zeros((nt,3,1))]).reshape(-1,3),np.dstack([T,np.full((nt,3,1),-SLAB)]).reshape(-1,3)]
    ft=[(3*i,3*i+1,3*i+2) for i in range(nt)]+[(3*(nt+i)+2,3*(nt+i)+1,3*(nt+i)) for i in range(nt)]; fc=list(C)+list(C)
    o_=2*3*nt
    for Rg,m_ in zip(d['crings'],elcol(d['crm'])):
        k_=len(Rg)-1; vt.append(np.vstack([np.c_[Rg[:-1],np.zeros(k_)],np.c_[Rg[:-1],np.full(k_,-SLAB)]]))
        ft+=[(o_+i,o_+(i+1)%k_,o_+k_+(i+1)%k_,o_+k_+i) for i in range(k_)]; fc+=[m_]*k_; o_+=2*k_
    sm=bpy.data.meshes.new('cslab'); sm.from_pydata(np.vstack(vt).tolist(),[],ft); sm.update()
    a_=sm.attributes.new('col','FLOAT_COLOR','FACE'); a_.data.foreach_set('color',np.c_[np.array(fc),np.ones(len(fc))].astype(np.float32).ravel())
    so_=bpy.data.objects.new('cslab',sm); s.collection.objects.link(so_); sm.materials.append(mat('cslabm',attr='col',rough=0.8))
    bpy.context.view_layer.objects.active=so_; bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode='OBJECT')
elif 'tris' in d.files:   # hole-aware slab (lakes cut out): triangulated top/bottom + walls on every ring
    T=d['tris']; nt=len(T); vt=np.concatenate([np.dstack([T,np.zeros((nt,3,1))]),np.dstack([T,np.full((nt,3,1),-SLAB)])]).reshape(-1,3)
    ft=[(3*i,3*i+1,3*i+2) for i in range(nt)]+[(3*(nt+i)+2,3*(nt+i)+1,3*(nt+i)) for i in range(nt)]
    for Rg in d['rings']:
        o_=len(vt); m_=len(Rg)-1; ring=np.vstack([np.c_[Rg[:-1],np.zeros(m_)],np.c_[Rg[:-1],np.full(m_,-SLAB)]]); vt=np.vstack([vt,ring])
        ft+=[(o_+i,o_+(i+1)%m_,o_+m_+(i+1)%m_,o_+m_+i) for i in range(m_)]
    sm=bpy.data.meshes.new('slab'); sm.from_pydata(vt.tolist(),[],ft); sm.update(); sm.validate()
    so_=bpy.data.objects.new('slab',sm); s.collection.objects.link(so_); sm.materials.append(slabm)
    bpy.context.view_layer.objects.active=so_; bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=1e-4); bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode='OBJECT')
for k,P in enumerate([] if ('tris' in d.files or 'ctris' in d.files) else d['polys']):
    sm=bpy.data.meshes.new(f's{k}'); bm=bmesh.new(); vs=[bm.verts.new((px,py,0.0)) for px,py in P[:-1]]
    try: f=bm.faces.new(vs)
    except Exception: bm.free(); continue
    r=bmesh.ops.extrude_face_region(bm,geom=[f]); bmesh.ops.translate(bm,verts=[e for e in r['geom'] if isinstance(e,bmesh.types.BMVert)],vec=(0,0,-SLAB))
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces); bm.to_mesh(sm); bm.free()
    so_=bpy.data.objects.new(f's{k}',sm); s.collection.objects.link(so_); sm.materials.append(slabm)
bpy.ops.mesh.primitive_plane_add(size=6*S,location=(0,0,-SLAB)); bpy.context.object.data.materials.append(mat('ground',(0.92,0.72,0.50),rough=0.9))
sun=bpy.data.lights.new('sun','SUN'); sun.energy=6.0; sun.angle=math.radians(0.6); sun.color=(1.0,0.93,0.84)
so=bpy.data.objects.new('sun',sun); s.collection.objects.link(so); from regions import SUN_EL, SUN_AZ; el,az=math.radians(SUN_EL),math.radians(SUN_AZ)
so.rotation_euler=Vector((math.sin(az)*math.cos(el),math.cos(az)*math.cos(el),math.sin(el))).to_track_quat('Z','Y').to_euler()
w=bpy.data.worlds.new('w'); s.world=w; w.use_nodes=True
w.node_tree.nodes['Background'].inputs['Color'].default_value=(0.55,0.65,0.85,1); w.node_tree.nodes['Background'].inputs['Strength'].default_value=0.35
# ---- plan-oblique frame: margins for shadows (east), title (top) and credits (bottom)
fx0,fx1,fy0,fy1=x0-0.03*S,x1+0.13*S,y0-0.12*S,y1+0.22*S
FW,FH=fx1-fx0,fy1-fy0; HPX=int(round(WPX*FH/FW))
if HPX>int(WPX*1.4): WPX=int(round(WPX*1.4*FW/FH)); HPX=int(round(WPX*FH/FW))   # cap very tall frames
tilt=math.radians(50); D=4*S
cam=bpy.data.cameras.new('cam'); cam.type='ORTHO'; cam.ortho_scale=FW; cam.sensor_fit='HORIZONTAL'; cam.clip_end=20*S
co=bpy.data.objects.new('cam',cam); s.collection.objects.link(co); s.camera=co
co.location=((fx0+fx1)/2,(fy0+fy1)/2-D*math.sin(tilt),D*math.cos(tilt)); co.rotation_euler=(tilt,0,0)
s.render.resolution_x=WPX; s.render.resolution_y=HPX; s.render.resolution_percentage=100
s.render.pixel_aspect_x=1/math.cos(tilt); s.render.pixel_aspect_y=1.0; bpy.context.view_layer.update()
# ---- label anchors: each city's visible skyline (25th-tallest cell within ~1.6% of extent)
from pyproj import Transformer
lon0,lat0,pcx,pcy=d['proj']; tr=Transformer.from_crs(4326,f'+proj=laea +lat_0={lat0} +lon_0={lon0} +units=km',always_xy=True)
CX,CY=X.mean(1),Y.mean(1); lab=[]; rad=max(12,0.016*S)
for name,lon,lat in c['cities']:
    ex,ey=tr.transform(lon,lat); ex-=pcx; ey-=pcy
    m=np.where((CX-ex)**2+(CY-ey)**2<rad**2)[0]
    if len(m)==0: print('no cells near',name); continue
    sky=np.sort(h[m])[-min(25,len(m))]; j=m[np.argmin(np.abs(h[m]-sky))]
    v=world_to_camera_view(s,co,Vector((CX[j],CY[j],h[j]))); lab.append((name,v.x*WPX,(1-v.y)*HPX))
meta=dict(labels=lab,cells=int(n),res=int(d['res']),cell_km2=float(np.median(d['area'])),pop=float(d['pop'].sum()))
json.dump(meta,open(OUT.rsplit('.',1)[0]+'_meta.json','w'))
s.render.engine='CYCLES'; s.cycles.device='CPU'; s.cycles.samples=SPP; s.cycles.use_denoising=True; s.cycles.max_bounces=4
s.view_settings.view_transform='AgX'; s.view_settings.look='AgX - Medium High Contrast'
s.render.image_settings.file_format='PNG'; s.render.filepath=OUT
t=time.time(); bpy.ops.render.render(write_still=True); print(f'{key} {WPX}x{HPX} render {time.time()-t:.0f}s faces {len(me.polygons)}')
