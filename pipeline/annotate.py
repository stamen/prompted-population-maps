# usage: annotate.py <region> <raw.png> <out.png>
import numpy as np, sys, json, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from regions import R, WORK, SUN_EL, FONTS, SITE_URL
from pyproj import Transformer
key,RAW,OUT=sys.argv[1:4]; c=R[key]; meta=json.load(open(RAW.rsplit('.',1)[0]+'_meta.json'))
def ground_level(im):
    a=np.asarray(im).astype(np.float32); W_,H_=im.size; g=a[int(H_*0.01):int(H_*0.06),int(W_*0.85):int(W_*0.99)].max(2).ravel()
    return float(np.median(g[g>=np.median(g)]))
def grade(im,wp):
    a=np.asarray(im).astype(np.float32)/255
    a=np.clip(a/(wp/255),0,1); a=np.clip(a-0.10*np.sin(2*np.pi*a)/np.pi,0,1)**1.03
    l=a@np.array([0.2126,0.7152,0.0722],np.float32); sat=a.max(2)-a.min(2)
    f=np.where(sat<0.22,0.55,1.0-0.10*np.clip((sat-0.22)/0.4,0,1))
    a=np.clip(l[...,None]+(a-l[...,None])*f[...,None],0,1)*np.array([1.0,0.99,0.965],np.float32)
    im=Image.fromarray((np.clip(a,0,1)*255+0.5).astype(np.uint8))
    return im.filter(ImageFilter.UnsharpMask(radius=max(1,im.size[0]/1800),percent=55,threshold=2))
raw=Image.open(RAW).convert('RGB'); WP=ground_level(raw)*1.024; W,H=raw.size; U=0.75*min(W,H*0.857)
F=FONTS+'/'
fT=ImageFont.truetype(F+'InterDisplay-Bold.otf',int(U*0.040)); fS=ImageFont.truetype(F+'Inter-Regular.otf',int(U*0.0155))
fL=ImageFont.truetype(F+'Inter-Medium.otf',int(U*0.0135)); fLb=ImageFont.truetype(F+'Inter-SemiBold.otf',int(U*0.0140))
fC=ImageFont.truetype(F+'Inter-Regular.otf',int(U*0.0115)); fN=ImageFont.truetype(F+'Inter-Bold.otf',int(U*0.0185))
ink=(48,38,30); sub=(95,82,68); cream=(250,244,234)
mx,my=int(W*0.045),int(U*0.05)
if 'election' in c:
    # ---- election legend: 5 equal swatches on the two-party margin, plus the statewide result
    E=c['election']; import pandas as pd
    if E['level']=='county': er=pd.read_csv(E['csv']); T=dict(d=er.d.sum(),r=er.r.sum(),l=er.l.sum(),tot=er.tot.sum())
    else: er=pd.read_csv(E['geo'].replace('.geojson','.csv')); T=dict(d=er[E['dcol']].sum(),r=er[E['rcol']].sum(),l=0,tot=er[E['totcol']].sum())
    T=pd.Series(T)
    sw,gap,sh=int(U*0.05),int(U*0.004),int(U*0.024); yb=my+int(U*0.10)+sh
    d0=ImageDraw.Draw(raw)
    for n,col in enumerate(json.load(open(f'{WORK}/legend_colors_election.json'))):
        x=mx+n*(sw+gap); d0.rectangle([x,yb-sh,x+sw,yb],fill=tuple(int(q) for q in col))
    im=grade(raw,WP); dr=ImageDraw.Draw(im)
    dr.text((mx,my),f"{c['title']} Results",font=fT,fill=ink)
    dr.text((mx,my+int(U*0.055)),f"Color: {E['level']} two-party margin. Height: people per km² (linear), on 317,903 H3 hexagons.",font=fS,fill=sub)
    for n,lab in enumerate(['R+60','R+30','Even','D+30','D+60']):
        x=mx+n*(sw+gap); dr.rectangle([x,yb-sh,x+sw,yb],outline=(175,160,140),width=1)
        w=dr.textlength(lab,font=fL); dr.text((x+sw/2-w/2,yb+int(U*0.006)),lab,font=fL,fill=ink)
    lx2=mx+5*(sw+gap)+int(U*0.014); y=yb-sh-int(U*0.012)
    pc=lambda v:f"{v/T.tot*100:.1f}%"
    head=f"{E['dem']} {pc(T.d)}  ·  {E['rep']} {pc(T.r)}"+(f"  ·  {E['third']} {pc(T.l)}" if E.get('third') else f"  ·  others {pc(T.tot-T.d-T.r)}")
    for t,f,col in [(head,fLb,ink),
                    (f"{T.tot:,.0f} votes. Every hexagon takes its {E['level']}'s result,",fL,sub),
                    ("so tall spikes show where the votes were cast.",fL,sub)]:
        dr.text((lx2,y),t,font=f,fill=col); y+=int(f.size*1.45)
    legend_bottom=max(y,yb+int(U*0.03))
else:
    # ---- legend: a staircase of the 5 classes (one step per 10x), bottom-aligned on a baseline
    sw,gap=int(U*0.05),int(U*0.004); step=int(U*0.011); base_h=int(U*0.014)
    yb=my+int(U*0.10)+base_h+4*step                                       # baseline of the stairs
    d0=ImageDraw.Draw(raw)
    for n,col in enumerate(json.load(open(f'{WORK}/legend_colors.json'))):  # swatch colors rendered under the map lighting
        x=mx+n*(sw+gap); d0.rectangle([x,yb-(base_h+n*step),x+sw,yb],fill=tuple(int(q) for q in col))
    im=grade(raw,WP); dr=ImageDraw.Draw(im)
    dr.text((mx,my),f"{c['title']} Population Density",font=fT,fill=ink)
    agg='' if meta['res']==8 else ', summed from Kontur res-8'
    dr.text((mx,my+int(U*0.055)),f"{meta['cells']:,} H3 hexagons (~{meta['cell_km2']:.2f} km² each{agg}). Height is linear in people per km².",font=fS,fill=sub)
    for n,lab in enumerate(['≤1','10','100','1,000','10,000+']):
        x=mx+n*(sw+gap); dr.rectangle([x,yb-(base_h+n*step),x+sw,yb],outline=(175,160,140),width=1)
        w=dr.textlength(lab,font=fL); dr.text((x+sw/2-w/2,yb+int(U*0.006)),lab,font=fL,fill=ink)
    lx2=mx+5*(sw+gap)+int(U*0.014); top=yb-(base_h+4*step)
    # callout: what the stairs mean, and what the spike heights mean
    d=np.load(f'{WORK}/{key}.npz',allow_pickle=True); dens=d['pop']/d['area']; i=int(np.argmax(dens))
    lon0,lat0,pcx,pcy=d['proj']; tr=Transformer.from_crs(4326,f'+proj=laea +lat_0={lat0} +lon_0={lon0} +units=km',always_xy=True)
    mxk,myk=d['x'][i].mean(),d['y'][i].mean()
    cxy=[tuple(q) for q in d['city_xy']] if 'city_xy' in d.files else [(n_,*(np.array(tr.transform(lo,la))-[pcx,pcy])) for n_,lo,la in c['cities']]
    near=min(cxy,key=lambda q:np.hypot(q[1]-mxk,q[2]-myk))[0]
    lines=[('Each color step is 10× denser',fLb,ink),
           ('Darkest blue (10,000+ people/km²) is 10,000× denser than darkest red (≤1).',fL,sub),
           (f'Spike height is linear: the tallest, in {near}, is {dens[i]:,.0f} people/km².',fL,sub)]
    y=top-int(U*0.002)
    for t,f,col in lines: dr.text((lx2,y),t,font=f,fill=col); y+=int(f.size*1.45)
    legend_bottom=max(y,yb+int(U*0.03))
cr=(f"Results: {c['election']['source']}\n" if 'election' in c else "")+f"Data: Kontur Population (2023-11-01, CC BY 4.0) · {meta['pop']/1e6:,.1f} million people\nBoundary: {c['credit']} · Plan oblique view, {meta.get('projection','Lambert azimuthal equal-area')}\nRendered in Blender 5.2 Cycles (path-traced). Sun at {SUN_EL:g}° elevation from the west; all shadows are ray-traced from the geometry."
cr+=f"\nMaps and code: {SITE_URL}"
dr.multiline_text((mx,H-my-int(U*(0.091 if 'election' in c else 0.073))),cr,font=fC,fill=sub,spacing=int(U*0.004))
# ---- city labels: bold name on a soft cream pill sitting just above each city's skyline
taken=[(0,0,W,legend_bottom+int(U*0.01)),(0,H-my-int(U*0.11),W,H)]
def hit(b): return any(not(b[2]<t[0] or b[0]>t[2] or b[3]<t[1] or b[1]>t[3]) for t in taken)
ov=Image.new('RGBA',im.size,(0,0,0,0)); do=ImageDraw.Draw(ov); texts=[]
capH=fN.getbbox('H')[3]-fN.getbbox('H')[1]; padx,pady=fN.size*0.55,fN.size*0.42
for name,px,py in meta['labels']:
    l_,t_,r_,b_=fN.getbbox(name,anchor='ls'); w=r_-l_; bw,bh=w+2*padx,capH+2*pady
    for dx,dy in [(0,0),(0.55,0),(-0.55,0),(0,-1.1)]:
        x=px-bw/2+dx*bw; y=py-U*0.010-bh+dy*bh; b=(x-3,y-3,x+bw+3,y+bh+3)
        if not hit(b): break
    else: continue
    taken.append(b)
    do.rounded_rectangle([x+U*0.0012,y+U*0.0018,x+bw+U*0.0012,y+bh+U*0.0018],radius=bh/2,fill=(40,28,18,55))   # soft drop shadow
    do.rounded_rectangle([x,y,x+bw,y+bh],radius=bh/2,fill=(*cream,232),outline=(150,128,104,200),width=max(1,int(U/1400)))
    texts.append((x+bw/2-(l_+r_)/2,y+bh/2+capH/2,name))         # baseline so capitals sit centered; ink box centered horizontally
for name,px,py in meta.get('parts',[]):   # composite maps: small caption under each moved part
    w=dr.textlength(name,font=fL); dr.text((px-w/2,py+U*0.008),name,font=fL,fill=sub)
ov=ov.filter(ImageFilter.GaussianBlur(0)) ; im=Image.alpha_composite(im.convert('RGBA'),ov).convert('RGB'); dr=ImageDraw.Draw(im)
for x,y,name in texts: dr.text((x,y),name,font=fN,fill=ink,anchor='ls')
im.save(OUT,optimize=True)
