"""Texas 2026 U.S. Senate results by county, parsed from the Wikipedia article's county table.
Unofficial returns compiled from county reports; replace with the Secretary of State canvass when it is certified.
usage: python fetch_tx_senate_2026.py out.csv"""
import sys, io, urllib.request, pandas as pd
URL='https://en.wikipedia.org/w/index.php?title=2026_United_States_Senate_election_in_Texas&action=render'
html=urllib.request.urlopen(urllib.request.Request(URL,headers={'User-Agent':'prompted-population-maps'})).read().decode()
t=[t for t in pd.read_html(io.StringIO(html)) if len(t)>250 and t.astype(str).apply(lambda c:c.str.contains('Talarico')).any().any()][0]
t=t.iloc[:,:12]; t.columns=['county','d','dp','r','rp','l','lp','o','op','m','mp','tot']
num=lambda c: pd.to_numeric(t[c].astype(str).str.replace(',',''),errors='coerce')
for c in ['d','r','l','o','tot']: t[c]=num(c)
t=t[t.d.notna() & ~t.county.astype(str).str.contains('Total|County')]
assert len(t)==254, f'expected 254 counties, got {len(t)}'
assert (t.d+t.r+t.l+t.o==t.tot).all(), 'county columns do not add up'
t[['county','d','r','l','o','tot']].astype({'d':int,'r':int,'l':int,'o':int,'tot':int}).to_csv(sys.argv[1],index=False)
print(f"254 counties  D {t.d.sum():,.0f}  R {t.r.sum():,.0f}  total {t.tot.sum():,.0f} -> {sys.argv[1]}")
