# Composite regions: several separate places (e.g. the US with Alaska, Hawaii, and the territories) drawn at ONE scale.
# Each part gets its own Lambert azimuthal equal-area projection (so its shape is right), then is moved, never resized,
# into a layout next to the main part. Called by prep.py when a region has `parts`. Writes work/<region>.npz.
import sys, os, time, numpy as np, pandas as pd, pyogrio, h3, geopandas as gpd, shapely, shapely.ops, shapely.affinity
from shapely.ops import unary_union
from pyproj import Transformer
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from regions import *
key=sys.argv[1]; c=R[key]; t=time.time(); res=c['res']; GAP=c.get('gap',250.0)
ne=gpd.read_file(NE0); lakes=unary_union(list(gpd.read_file(LAKES).geometry)) if c.get('lakes') else None
def part_geom(P):
    g=unary_union(list(ne[ne.ADMIN.isin(P['ne'])].geometry)); pieces=[]
    for bx in P['bbox']:
        q=g.intersection(shapely.box(*bx))
        if bx[0]>0 and P.get('west_of_180'): q=shapely.affinity.translate(q,xoff=-360)   # Aleutians past 180°: bring to -180..
        pieces.append(q)
    return unary_union(pieces).buffer(0)
# population: all Kontur files, summed to the target resolution once
df=pd.concat([pyogrio.read_dataframe(K+f+'.gpkg',read_geometry=False,columns=['h3','population']) for f in c['kontur']])
cells=df.h3.values; pop=df.population.values.astype(float)
if res<8:
    par=np.array([h3.cell_to_parent(x,res) for x in cells]); s_=pd.Series(pop).groupby(par).sum(); cells=s_.index.values; pop=s_.values
ll=np.array([h3.cell_to_latlng(x) for x in cells]); LAT,LON=ll[:,0],ll[:,1]
def bnd6(x):
    v=h3.cell_to_boundary(x)
    if len(v)>6:
        a=np.array(v); d1=a-np.roll(a,1,0); d2=np.roll(a,-1,0)-a
        v=tuple(map(tuple,a[np.sort(np.argsort(-np.abs(np.arctan2(d1[:,0]*d2[:,1]-d1[:,1]*d2[:,0],(d1*d2).sum(1))))[:6])]))
    return v if len(v)==6 else v+(v[-1],)*(6-len(v))
P_out=[]; used=np.zeros(len(cells),bool)
for P in c['parts']:
    g=part_geom(P); land=g.difference(lakes).buffer(0) if lakes is not None else g
    lon0,lat0=g.centroid.x,g.centroid.y
    tr=Transformer.from_crs(4326,f'+proj=laea +lat_0={lat0} +lon_0={lon0} +units=km',always_xy=True)
    f=lambda x,y:tr.transform(x,y)
    gp=shapely.ops.transform(f,g); gl=shapely.ops.transform(f,land)
    lon=np.where((LON>0)&P.get('west_of_180',False),LON-360,LON)
    X,Y=tr.transform(lon,LAT); keep=~used&shapely.contains_xy(gp.buffer(3.0),X,Y); used|=keep
    idx=np.where(keep)[0]
    verts=np.array([bnd6(x) for x in cells[idx]]); vlon=verts[...,1]
    if P.get('west_of_180'): vlon=np.where(vlon>0,vlon-360,vlon)
    vx,vy=tr.transform(vlon,verts[...,0])
    P_out.append(dict(P=P,tr=tr,gp=gp,gl=gl,idx=idx,vx=vx,vy=vy))
    print(f"  {P['name']}: {len(idx)} cells, {pop[idx].sum():,.0f} people")
# layout: the main part stays put; the others are moved (not scaled) to rules relative to placed parts
main=P_out[0]; B={main['P']['name']:main['gp'].bounds}; off={main['P']['name']:(0.0,0.0)}
for o in P_out[1:]:
    x0,y0,x1,y1=o['gp'].bounds; w,h_=x1-x0,y1-y0; L=o['P']['place']; ref=B[L['ref']]
    tx={'left_of':ref[0]-GAP-x1,'right_of':ref[2]+GAP-x0,'align_left':ref[0]-x0,'align_right':ref[2]-x1}[L['x']]+L.get('dx',0)
    ty={'below':ref[1]-GAP-y1,'above':ref[3]+GAP-y0,'align_top':ref[3]-y1,'align_bottom':ref[1]-y0,'center':(ref[1]+ref[3])/2-(y0+y1)/2}[L['y']]+L.get('dy',0)
    off[o['P']['name']]=(tx,ty); B[o['P']['name']]=(x0+tx,y0+ty,x1+tx,y1+ty)
allb=np.array(list(B.values())); bx0,by0,bx1,by1=allb[:,0].min(),allb[:,1].min(),allb[:,2].max(),allb[:,3].max()
cx,cy=(bx0+bx1)/2,(by0+by1)/2; S=max(bx1-bx0,by1-by0)
VX,VY,POP,AREA,tris,rings,city_xy,part_xy=[],[],[],[],[],[],[],[]
for o in P_out:
    tx,ty=off[o['P']['name']]; tx-=cx; ty-=cy
    VX.append(o['vx']+tx); VY.append(o['vy']+ty); POP.append(pop[o['idx']]); AREA.append([h3.cell_area(x,'km^2') for x in cells[o['idx']]])
    for p in (o['gl'].geoms if o['gl'].geom_type=='MultiPolygon' else [o['gl']]):
        q=p.simplify(min(S/4000,max(0.2,p.length/400)))
        if q.is_empty or q.area<0.5: continue
        if not q.is_valid: q=q.buffer(0)
        if q.geom_type!='Polygon': continue
        for t_ in shapely.constrained_delaunay_triangles(q).geoms: tris.append(np.array(t_.exterior.coords)[:3]+[tx,ty])
        rings+=[np.array(q.exterior.coords)+[tx,ty]]+[np.array(r.coords)+[tx,ty] for r in q.interiors]
    for name,lon,lat in o['P'].get('cities',[]):
        ex,ey=o['tr'].transform(lon-360 if (lon>0 and o['P'].get('west_of_180')) else lon,lat); city_xy.append((name,ex+tx,ey+ty))
    if o is not main:
        x0,y0,x1,y1=o['gp'].bounds; part_xy.append((o['P']['name'],(x0+x1)/2+tx,y0+ty))
x=np.concatenate(VX); y=np.concatenate(VY); popv=np.concatenate(POP); area=np.concatenate(AREA)
rr=np.empty(len(rings),object); rr[:]=rings; cxy=np.empty(len(city_xy),object); cxy[:]=city_xy; pxy=np.empty(len(part_xy),object); pxy[:]=part_xy
polys=np.empty(0,object)
np.savez(f'{WORK}/{key}.npz',x=x,y=y,pop=popv,area=area,polys=polys,tris=np.array(tris),rings=rr,city_xy=cxy,part_xy=pxy,
         proj=np.array([0,0,0,0]),bounds=np.array([bx0-cx,by0-cy,bx1-cx,by1-cy]),res=res)
print(f'{key}: composite res{res} cells={len(popv)} pop={popv.sum():,.0f} extent={S:.0f}km parts={len(P_out)} maxdens={np.max(popv/area):,.0f} {time.time()-t:.0f}s')
