import sys, numpy as np, pandas as pd, pyogrio, h3, geopandas as gpd, shapely, time
from shapely.ops import unary_union
from pyproj import Transformer
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from regions import *
key=sys.argv[1]; c=R[key]; t=time.time()
b=c['bnd']
if b[0]=='census': g=gpd.read_file(CENSUS); g=g[g.STUSPS==b[1]].to_crs(4326).geometry
elif b[0]=='ne0': g=gpd.read_file(NE0); g=g[g.ADMIN.isin(b[1])].geometry
else: g=gpd.read_file(NE1); g=g[(g['name']==b[1])&(g.admin=='Canada')].geometry
geom=unary_union(list(g))
if 'bbox' in c: geom=geom.intersection(shapely.box(*c['bbox']))
if c.get('lakes'):   # cut out the Great Lakes and inland lakes so the land mass follows the real shoreline
    lk=gpd.read_file(LAKES); lk=lk[lk.intersects(geom)].geometry; land=geom.difference(unary_union(list(lk))).buffer(0)
else: land=geom
df=pd.concat([pyogrio.read_dataframe(K+f+'.gpkg',read_geometry=False,columns=['h3','population']) for f in c['kontur']])
lon0,lat0=(geom.bounds[0]+geom.bounds[2])/2,(geom.bounds[1]+geom.bounds[3])/2
tr=Transformer.from_crs(4326,f'+proj=laea +lat_0={lat0} +lon_0={lon0} +units=km',always_xy=True)
gp=shapely.ops.transform(lambda x,y:tr.transform(x,y),geom)
gl=shapely.ops.transform(lambda x,y:tr.transform(x,y),land)
S=max(gp.bounds[2]-gp.bounds[0],gp.bounds[3]-gp.bounds[1])
res=8 if S<=2000 else 7
cells=df.h3.values; pop=df.population.values.astype(float)
if res<8:   # sum Kontur res-8 populations into their res-7 parents (real totals, coarser cells)
    par=np.array([h3.cell_to_parent(x,res) for x in cells]); s=pd.Series(pop).groupby(par).sum(); cells=s.index.values; pop=s.values
ll=np.array([h3.cell_to_latlng(x) for x in cells])
clip=gp.buffer(3.0) if c['national'] else gp    # national files contain only that country: small buffer keeps coastal cells
X,Y=tr.transform(ll[:,1],ll[:,0]); keep=shapely.contains_xy(clip,X,Y)
cells,pop=cells[keep],pop[keep]
def bnd6(x):
    v=h3.cell_to_boundary(x)
    if len(v)>6:   # icosahedron-edge cells carry extra near-collinear 'distortion' vertices: keep the 6 sharpest corners
        a=np.array(v); d1=a-np.roll(a,1,0); d2=np.roll(a,-1,0)-a
        ang=np.abs(np.arctan2(d1[:,0]*d2[:,1]-d1[:,1]*d2[:,0],(d1*d2).sum(1)))
        v=tuple(map(tuple,a[np.sort(np.argsort(-ang)[:6])]))
    return v if len(v)==6 else v+(v[-1],)*(6-len(v))
verts=np.array([bnd6(x) for x in cells]); vx,vy=tr.transform(verts[...,1],verts[...,0])
area=np.array([h3.cell_area(x,'km^2') for x in cells])
cx,cy=(gp.bounds[0]+gp.bounds[2])/2,(gp.bounds[1]+gp.bounds[3])/2
parts=[p for p in (gl.geoms if gl.geom_type=='MultiPolygon' else [gl]) if p.area>max(20,S*S*2e-5)]
polys=np.empty(len(parts),object); polys[:]=[np.array(p.simplify(S/4000).exterior.coords)-[cx,cy] for p in parts]
extra={}
if 'election' in c:
    E=c['election']
    if E['level']=='county':   # county table joined to Census county polygons by name
        er=pd.read_csv(E['csv']); er['m']=(er.d-er.r)/(er.d+er.r)
        co=gpd.read_file(E['counties']); co=co[co.STATEFP==E['statefp']].merge(er,left_on='NAME',right_on='county').to_crs(4326)
    else:                      # precinct polygons that already carry vote counts
        co=gpd.read_file(E['geo']).to_crs(4326); co['m']=(co[E['dcol']]-co[E['rcol']])/(co[E['dcol']]+co[E['rcol']]).clip(lower=1)
        co['geometry']=co.geometry.buffer(0)
    lat_,lon_=np.array([h3.cell_to_latlng(x) for x in cells]).T
    pts=gpd.GeoDataFrame(geometry=gpd.points_from_xy(lon_,lat_),crs=4326)
    j=gpd.sjoin_nearest(pts.to_crs(3083),co[['m','geometry']].to_crs(3083),how='left').groupby(level=0).first()   # nearest handles edge cells
    # county-colored slab: triangulate each county (holes/islands kept) and keep its outline rings for walls
    ct,ctm,cr,crm=[],[],[],[]
    for g_,m_ in zip(co.geometry,co.m):
        gq=shapely.ops.transform(lambda x,y:tr.transform(x,y),g_)
        for p_ in (gq.geoms if gq.geom_type=='MultiPolygon' else [gq]):
            q=p_.simplify(S/4000 if E['level']=='county' else S/25000)   # precincts are tiny in cities: simplify gently
            if q.is_empty or q.area<0.0005: continue
            if not q.is_valid: q=q.buffer(0)
            if q.geom_type!='Polygon': continue
            for t_ in shapely.constrained_delaunay_triangles(q).geoms: ct.append(np.array(t_.exterior.coords)[:3]-[cx,cy]); ctm.append(m_)
            for r_ in [q.exterior,*q.interiors]: cr.append(np.array(r_.coords)-[cx,cy]); crm.append(m_)
    extra['ctris']=np.array(ct); extra['ctm']=np.array(ctm); rr=np.empty(len(cr),object); rr[:]=cr; extra['crings']=rr; extra['crm']=np.array(crm)
    print('county slab triangles',len(ct))
    extra['margin']=j['m'].values; print('cells per county ok; margin range',np.nanmin(extra['margin']).round(3),np.nanmax(extra['margin']).round(3))
if c.get('lakes'):   # triangulate the slab with holes (inland lakes), plus every ring for the side walls
    tris=[];rings=[]
    for p in parts:
        q=p.simplify(S/4000)
        for t_ in shapely.constrained_delaunay_triangles(q).geoms: tris.append(np.array(t_.exterior.coords)[:3]-[cx,cy])
        rings+= [np.array(q.exterior.coords)-[cx,cy]]+[np.array(r.coords)-[cx,cy] for r in q.interiors]
    rr=np.empty(len(rings),object); rr[:]=rings; extra=dict(tris=np.array(tris),rings=rr)
    print('slab triangles',len(tris),'rings',len(rings))
np.savez(f'{WORK}/{key}.npz',**extra,x=vx-cx,y=vy-cy,pop=pop,area=area,polys=polys,proj=np.array([lon0,lat0,cx,cy]),
         bounds=np.array(gp.bounds)-[cx,cy,cx,cy],res=res)
print(f'{key}: res{res} cells={len(cells)} pop={pop.sum():,.0f} extent={S:.0f}km polys={len(parts)} maxdens={np.max(pop/area):,.0f} {time.time()-t:.0f}s')
