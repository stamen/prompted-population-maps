# One entry per map. cities: (name, lon, lat) in label-priority order.
import os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA=os.environ.get('POPMAPS_DATA',os.path.join(ROOT,'data'))    # downloads (fetch_data.sh)
WORK=os.environ.get('POPMAPS_WORK',os.path.join(ROOT,'work'))    # intermediates + raw renders
OUT=os.environ.get('POPMAPS_OUT',os.path.join(ROOT,'out'))       # finished maps
FONTS=os.path.join(ROOT,'fonts')
os.makedirs(WORK,exist_ok=True); os.makedirs(OUT,exist_ok=True)
NE0=f'{DATA}/bnd/ne_10m_admin_0_countries.geojson'; NE1=f'{DATA}/bnd/ne_10m_admin_1_states_provinces.geojson'
LAKES=f'{DATA}/bnd/ne_10m_lakes.geojson'
CENSUS=f'zip://{DATA}/bnd/cb_2023_us_state_5m.zip'
K=f'{DATA}/kontur/'
SITE_URL='stamen.github.io/prompted-population-maps'   # printed in every map's credits
SUN_EL=15.0; SUN_AZ=282.0     # sun elevation above the horizon and azimuth (degrees); lower = longer shadows
# election ramp on two-party margin (D-R)/(D+R): -0.6 = R+60 ... +0.6 = D+60
EL_STOPS=[-0.6,-0.3,-0.1,0.0,0.1,0.3,0.6]
EL_COLS=[[165,15,30],[214,48,44],[240,160,145],[246,240,232],[150,185,235],[45,110,210],[15,50,160]]
R={
 'texas':dict(title='Texas',kontur=['US'],bnd=('census','TX'),national=False,credit='US Census Bureau cartographic boundary 2023',
   cities=[('Houston',-95.37,29.76),('Dallas',-96.80,32.78),('Fort Worth',-97.33,32.75),('San Antonio',-98.49,29.42),('Austin',-97.74,30.27),('El Paso',-106.44,31.76),('McAllen',-98.23,26.20),('Laredo',-99.51,27.51),('Corpus Christi',-97.40,27.80),('Lubbock',-101.86,33.58),('Amarillo',-101.83,35.22),('Midland',-102.08,32.00)]),
 'texas_senate':dict(title='Texas 2026 U.S. Senate',election=dict(level='county',dem='Talarico (D)',rep='Paxton (R)',third='Brown (L)',csv=f'{DATA}/election/tx_senate_2026_county.csv',counties=f'zip://{DATA}/bnd/cb_2023_us_county_5m.zip',statefp='48',
     source='Unofficial county returns compiled on Wikipedia (retrieved 10 Nov 2026), spot-checked against Decision Desk HQ and Dallas Morning News reporting'),kontur=['US'],bnd=('census','TX'),national=False,credit='US Census Bureau cartographic boundary 2023',
   cities=[('Houston',-95.37,29.76),('Dallas',-96.80,32.78),('Fort Worth',-97.33,32.75),('San Antonio',-98.49,29.42),('Austin',-97.74,30.27),('El Paso',-106.44,31.76),('McAllen',-98.23,26.20),('Laredo',-99.51,27.51),('Corpus Christi',-97.40,27.80),('Lubbock',-101.86,33.58),('Amarillo',-101.83,35.22),('Midland',-102.08,32.00)]),
 'texas_pres2024':dict(title='Texas 2024 Presidential',election=dict(level='precinct',dem='Harris (D)',rep='Trump (R)',third=None,
     geo=f'{DATA}/election/nyt/TX.geojson',dcol='votes_dem',rcol='votes_rep',totcol='votes_total',
     source='The New York Times, 2024 presidential precinct results (official precinct boundaries). Used under the NYT non-commercial data agreement'),kontur=['US'],bnd=('census','TX'),national=False,credit='US Census Bureau cartographic boundary 2023',
   cities=[('Houston',-95.37,29.76),('Dallas',-96.80,32.78),('Fort Worth',-97.33,32.75),('San Antonio',-98.49,29.42),('Austin',-97.74,30.27),('El Paso',-106.44,31.76),('McAllen',-98.23,26.20),('Laredo',-99.51,27.51),('Corpus Christi',-97.40,27.80),('Lubbock',-101.86,33.58),('Amarillo',-101.83,35.22),('Midland',-102.08,32.00)]),
 'new_york':dict(title='New York State',kontur=['US'],bnd=('census','NY'),national=False,
   credit='US Census Bureau cartographic boundary 2023',
   cities=[('New York City',-74.00,40.71),('Buffalo',-78.88,42.89),('Rochester',-77.61,43.16),('Syracuse',-76.15,43.05),('Albany',-73.76,42.65),('Binghamton',-75.91,42.10),('Utica',-75.23,43.10),('Ithaca',-76.50,42.44),('Plattsburgh',-73.45,44.70)]),
 'india':dict(title='India',kontur=['IN'],bnd=('ne0',['India']),national=True,credit='Natural Earth 1:10m (de facto boundaries)',
   cities=[('Mumbai',72.88,19.08),('Delhi',77.21,28.61),('Kolkata',88.36,22.57),('Chennai',80.27,13.08),('Bengaluru',77.59,12.97),('Hyderabad',78.49,17.39),('Ahmedabad',72.57,23.02),('Pune',73.86,18.52),('Jaipur',75.79,26.91),('Lucknow',80.95,26.85),('Patna',85.14,25.59),('Guwahati',91.74,26.14),('Srinagar',74.80,34.08),('Kochi',76.27,9.93)]),
 'france':dict(title='France',kontur=['FR'],bnd=('ne0',['France']),national=True,bbox=(-6,41,10,52),credit='Natural Earth 1:10m (metropolitan France)',
   cities=[('Paris',2.35,48.86),('Lyon',4.84,45.76),('Marseille',5.37,43.30),('Toulouse',1.44,43.60),('Nice',7.26,43.70),('Lille',3.06,50.63),('Bordeaux',-0.58,44.84),('Nantes',-1.55,47.22),('Strasbourg',7.75,48.58),('Rennes',-1.68,48.11),('Montpellier',3.88,43.61),('Ajaccio',8.74,41.93)]),
 'uk':dict(title='United Kingdom',kontur=['GB'],bnd=('ne0',['United Kingdom']),national=True,credit='Natural Earth 1:10m',
   cities=[('London',-0.13,51.51),('Birmingham',-1.90,52.49),('Manchester',-2.24,53.48),('Glasgow',-4.25,55.86),('Edinburgh',-3.19,55.95),('Liverpool',-2.98,53.41),('Leeds',-1.55,53.80),('Newcastle',-1.61,54.97),('Bristol',-2.59,51.45),('Belfast',-5.93,54.60),('Cardiff',-3.18,51.48),('Sheffield',-1.47,53.38),('Aberdeen',-2.10,57.15),('Plymouth',-4.14,50.38)]),
 'china':dict(title='China',kontur=['CN','HK','MO'],bnd=('ne0',['China','Hong Kong S.A.R.','Macao S.A.R']),national=True,
   credit='Natural Earth 1:10m (de facto boundaries; includes Hong Kong & Macau)',
   cities=[('Shanghai',121.47,31.23),('Beijing',116.40,39.90),('Guangzhou',113.26,23.13),('Shenzhen',114.06,22.54),('Chongqing',106.55,29.56),('Chengdu',104.07,30.57),('Wuhan',114.31,30.59),("Xi'an",108.94,34.34),('Tianjin',117.20,39.13),('Harbin',126.53,45.80),('Hong Kong',114.17,22.32),('Kunming',102.83,24.88),('Shenyang',123.43,41.80),('Ürümqi',87.62,43.83),('Lhasa',91.13,29.65),('Lanzhou',103.83,36.06)]),
 'ontario':dict(title='Ontario',kontur=['CA'],bnd=('ne1','Ontario'),national=False,lakes=True,credit='Natural Earth 1:10m (lakes removed)',
   cities=[('Toronto',-79.38,43.65),('Ottawa',-75.70,45.42),('Hamilton',-79.87,43.26),('London',-81.25,42.98),('Windsor',-83.03,42.31),('Kitchener',-80.49,43.45),('Sudbury',-80.99,46.49),('Thunder Bay',-89.25,48.38),('Kingston',-76.48,44.23),('Sault Ste. Marie',-84.33,46.52),('Timmins',-81.33,48.48),('Moosonee',-80.65,51.27)]),
 'germany':dict(title='Germany',kontur=['DE'],bnd=('ne0',['Germany']),national=True,credit='Natural Earth 1:10m',
   cities=[('Berlin',13.40,52.52),('Hamburg',9.99,53.55),('Munich',11.58,48.14),('Cologne',6.96,50.94),('Frankfurt',8.68,50.11),('Stuttgart',9.18,48.78),('Düsseldorf',6.77,51.23),('Leipzig',12.37,51.34),('Dresden',13.74,51.05),('Hanover',9.73,52.37),('Nuremberg',11.08,49.45),('Bremen',8.80,53.08),('Dortmund',7.47,51.51)]),
 # ---- the seven countries first made "with vibes" (see the site), now from real data
 'usa':dict(title='United States (contiguous)',kontur=['US'],bnd=('ne0',['United States of America']),national=True,res=6,lakes=True,bbox=(-125,24,-66.5,49.5),credit='Natural Earth 1:10m (contiguous 48 states, lakes removed)',
   cities=[('New York',-74.0,40.7),('Los Angeles',-118.24,34.05),('Chicago',-87.63,41.88),('Houston',-95.37,29.76),('Dallas',-96.8,32.78),('Miami',-80.19,25.77),('Atlanta',-84.39,33.75),('Seattle',-122.33,47.61),('Denver',-104.99,39.74),('Phoenix',-112.07,33.45),('San Francisco',-122.42,37.77),('Minneapolis',-93.27,44.98)]),
 'russia':dict(title='Russia',kontur=['RU'],bnd=('ne0',['Russia']),national=True,bbox=(19,41,180,82),credit='Natural Earth 1:10m (de facto boundaries; Chukotka east of 180° omitted)',
   cities=[('Moscow',37.62,55.75),('St Petersburg',30.32,59.94),('Novosibirsk',82.92,55.03),('Yekaterinburg',60.6,56.84),('Kazan',49.11,55.79),('Rostov-on-Don',39.7,47.23),('Krasnoyarsk',92.87,56.01),('Omsk',73.37,54.99),('Irkutsk',104.3,52.29),('Vladivostok',131.89,43.12),('Khabarovsk',135.07,48.48),('Yakutsk',129.73,62.03)]),
 'japan':dict(title='Japan',kontur=['JP'],bnd=('ne0',['Japan']),national=True,bbox=(122,24,146.5,46),credit='Natural Earth 1:10m (remote Pacific islands omitted)',
   cities=[('Tokyo',139.69,35.69),('Osaka',135.5,34.69),('Nagoya',136.91,35.18),('Fukuoka',130.4,33.59),('Sapporo',141.35,43.06),('Sendai',140.87,38.27),('Hiroshima',132.46,34.39),('Niigata',139.04,37.92),('Kagoshima',130.56,31.6),('Naha',127.68,26.21),('Kanazawa',136.65,36.56),('Kochi',133.53,33.56)]),
 'mexico':dict(title='Mexico',kontur=['MX'],bnd=('ne0',['Mexico']),national=True,top=0.32,bbox=(-117.5,14,-86,33),credit='Natural Earth 1:10m (remote Pacific islands omitted)',
   cities=[('Mexico City',-99.13,19.43),('Guadalajara',-103.35,20.67),('Monterrey',-100.31,25.69),('Puebla',-98.2,19.04),('Tijuana',-117.04,32.51),('León',-101.68,21.12),('Juárez',-106.42,31.69),('Mérida',-89.62,20.97),('Chihuahua',-106.09,28.63),('Culiacán',-107.39,24.8),('Acapulco',-99.82,16.86),('Cancún',-86.85,21.16)]),
 'brazil':dict(title='Brazil',kontur=['BR'],bnd=('ne0',['Brazil']),national=True,bbox=(-74.5,-34,-34,5.5),credit='Natural Earth 1:10m (Atlantic islands omitted)',
   cities=[('São Paulo',-46.63,-23.55),('Rio de Janeiro',-43.2,-22.9),('Belo Horizonte',-43.94,-19.92),('Brasília',-47.88,-15.79),('Salvador',-38.5,-12.97),('Fortaleza',-38.54,-3.72),('Recife',-34.88,-8.05),('Porto Alegre',-51.23,-30.03),('Curitiba',-49.27,-25.43),('Manaus',-60.02,-3.12),('Belém',-48.5,-1.46),('Goiânia',-49.25,-16.68)]),
 'australia':dict(title='Australia',kontur=['AU'],bnd=('ne0',['Australia']),national=True,bbox=(112,-44,154,-9),credit='Natural Earth 1:10m (external territories omitted)',
   cities=[('Sydney',151.21,-33.87),('Melbourne',144.96,-37.81),('Brisbane',153.03,-27.47),('Perth',115.86,-31.95),('Adelaide',138.6,-34.93),('Canberra',149.13,-35.28),('Hobart',147.33,-42.88),('Darwin',130.84,-12.46),('Townsville',146.82,-19.26),('Cairns',145.77,-16.92),('Alice Springs',133.88,-23.7),('Newcastle',151.78,-32.93)]),
 'egypt':dict(title='Egypt',kontur=['EG'],bnd=('ne0',['Egypt']),national=True,top=0.55,credit='Natural Earth 1:10m (de facto boundaries)',
   cities=[('Cairo',31.24,30.04),('Alexandria',29.92,31.2),('Port Said',32.3,31.26),('Suez',32.55,29.97),('Mansoura',31.38,31.04),('Tanta',31.0,30.79),('Asyut',31.18,27.18),('Luxor',32.64,25.69),('Aswan',32.9,24.09),('Hurghada',33.81,27.26),('Siwa',25.52,29.2),('Marsa Matruh',27.24,31.35)]),
}
