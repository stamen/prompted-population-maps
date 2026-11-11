"""Rebuild docs/index.html (the GitHub Pages site) from docs/template.html, the finished maps in out/,
the per-region data in work/, docs/history.json, docs/cost_log.json and the pipeline source files.
usage: python docs/build_site.py"""
import json, html, os, sys
import numpy as np
from PIL import Image
D=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(D); sys.path.insert(0,os.path.join(ROOT,'pipeline'))
from regions import R, WORK, OUT
REPO='https://github.com/stamen/prompted-population-maps/blob/main/'
DENSITY=['texas','new_york','ontario','uk','france','germany','india','china']
ELECTION=['texas_senate','texas_pres2024']
REAL7=['usa','russia','japan','mexico','brazil','australia','egypt']   # the seven first made with vibes
def export(k):
    src=os.path.join(OUT,f'{k}.png')
    if not os.path.exists(src): print('missing',src); return None
    im=Image.open(src).convert('RGB'); W,H=im.size
    full=f'{D}/full/{k}.jpg'; web=f'{D}/img/{k}.jpg'
    if not os.path.exists(full) or os.path.getmtime(full)<os.path.getmtime(src):
        im.save(full,quality=88,optimize=True,progressive=True)
        im.resize((1600,round(1600*H/W)),Image.LANCZOS).save(web,quality=84,optimize=True,progressive=True)
    d=np.load(f'{WORK}/{k}.npz',allow_pickle=True)
    return dict(w=1600,h=round(1600*H/W),cells=len(d['pop']),pop=float(d['pop'].sum()),res=int(d['res']),km2=float(np.median(d['area'])))
def fig(k,i,extra=''):
    ps=f"{i['pop']/1e9:.2f} billion" if i['pop']>1e9 else f"{i['pop']/1e6:.1f} million"
    name=R[k]['title']+(' Results' if 'election' in R[k] else '')
    return (f'    <figure><a class="plate" href="full/{k}.jpg" target="_blank" rel="noopener"><img src="img/{k}.jpg" alt="{html.escape(name)}, raytraced 3D hexagon map" width="{i["w"]}" height="{i["h"]}" loading="lazy"></a>\n'
            f'      <figcaption><b>{html.escape(name)}</b><span class="num">{extra or ps+f" · {i["cells"]:,} cells · res {i["res"]} (~{i["km2"]:.2f} km²)"}</span></figcaption></figure>\n')
t=open(f'{D}/template.html').read()
g=''.join(fig(k,i) for k in DENSITY if (i:=export(k)))
r7=''.join(fig(k,i) for k in REAL7 if (i:=export(k)))
e=''.join(fig(k,i,extra=('county results' if R[k]['election']['level']=='county' else 'precinct results')+f" · {i['cells']:,} cells") for k in ELECTION if (i:=export(k)))
tl=''
for s in json.load(open(f'{D}/history.json')):
    im=Image.open(f"{D}/img/history/{s['img']}"); w,h=im.size
    tl+=(f'    <article class="step"><a class="plate" href="img/history/{s["img"]}" target="_blank" rel="noopener"><img src="img/history/{s["img"]}" alt="Texas map: {html.escape(s["title"].lower())}" width="{w}" height="{h}" loading="lazy"></a>\n'
         f'      <div class="stack"><h3>{html.escape(s["title"])}</h3><p class="ask">“{html.escape(s["ask"])}”</p><p>{html.escape(s["what"])}</p></div></article>\n')
C=json.load(open(f'{D}/cost_log.json'))
rows=''.join(f'<tr{" class=sum" if r.get("sum") else ""}><td>{html.escape(r["phase"])}</td><td class="r">{r["share"]}</td></tr>' for r in C['phases'])
m=C['measured']
meas=''.join(f'<tr><td>{html.escape(a)}</td><td class="r">{b}</td></tr>' for a,b in [('Output tokens (written by the model, including reasoning)',f"{m['output_tokens']:,}"),('Input tokens, not cached',f"{m['input_tokens']:,}"),('Cache writes',f"{m['cache_write_tokens']:,}"),('Cache reads (the conversation re-read on every step)',f"{m['cache_read_tokens']:,}"),('API cost at list price',f"${m['cost_usd']:.2f}")])
code=''
for f,dsc in [('AGENTS.md','instructions for coding agents'),('pipeline/regions.py','one entry per map'),('pipeline/prep.py','clip, aggregate, project, join elections'),('pipeline/render.py','build scene and path-trace'),('pipeline/annotate.py','grade, title, legend, labels'),('pipeline/legend_render.py','render the swatch colors'),('pipeline/make_map.sh','one command per map'),('pipeline/fetch_data.sh','download inputs'),('pipeline/fetch_tx_senate_2026.py','2026 Senate county results')]:
    src=html.escape(open(os.path.join(ROOT,f)).read())
    code+=f'  <details><summary>{f}<span>{dsc} · <a href="{REPO}{f}" target="_blank" rel="noopener">on GitHub</a></span></summary><div class="codebox"><button class="copy" type="button">Copy</button><pre>{src}</pre></div></details>\n'
for a,b in [('<!--GALLERY-->',g),('<!--ELECTION-->',e),('<!--REAL7-->',r7),('<!--TIMELINE-->',tl),('<!--COST-->',rows),('<!--MEASURED-->',meas),('<!--MEASURED_AT-->',html.escape(m['as_of'])),('<!--CODE-->',code)]: t=t.replace(a,b)
open(f'{D}/index.html','w').write(t); print('wrote docs/index.html',len(t),'bytes')
