#!/usr/bin/env bash
# Download inputs into ./data (override with POPMAPS_DATA).
#   pipeline/fetch_data.sh US IN FR GB CN HK MO DE CA     Kontur population files by ISO-2 code
#   pipeline/fetch_data.sh --elections                    Texas 2026 Senate (county) + 2024 presidential (precinct)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; D="${POPMAPS_DATA:-$HERE/../data}"; mkdir -p "$D/kontur" "$D/bnd" "$D/election/nyt"
get(){ [ -s "$2" ] || { echo "-> $2"; curl -fSL --retry 3 -o "$2" "$1"; }; }
NE=https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson
for f in ne_10m_admin_0_countries ne_10m_admin_1_states_provinces ne_10m_lakes; do get "$NE/$f.geojson" "$D/bnd/$f.geojson"; done
get https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_state_5m.zip  "$D/bnd/cb_2023_us_state_5m.zip"
get https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_5m.zip "$D/bnd/cb_2023_us_county_5m.zip"
for c in "$@"; do
  if [ "$c" = "--elections" ]; then
    python "$HERE/fetch_tx_senate_2026.py" "$D/election/tx_senate_2026_county.csv"
    for x in geojson csv; do get "https://int.nyt.com/newsgraphics/elections/map-data/2024/national/TX-precincts-with-results.$x.gz" "$D/election/nyt/TX.$x.gz"
      [ -s "$D/election/nyt/TX.$x" ] || gunzip -kf "$D/election/nyt/TX.$x.gz"; done
    continue
  fi
  # Kontur Population 2023-11-01, one GeoPackage per country (same files as on data.humdata.org)
  [ -s "$D/kontur/$c.gpkg" ] || { echo "-> kontur $c"; curl -fSL --retry 3 "https://geodata-eu-central-1-kontur-public.s3.amazonaws.com/kontur_datasets/kontur_population_${c}_20231101.gpkg.gz" | gunzip > "$D/kontur/$c.gpkg"; }
done
