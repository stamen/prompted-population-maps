#!/usr/bin/env bash
# One command per map.   pipeline/make_map.sh <region> [preview|final]
#   preview: 800 px, 16 samples (~20 s)     final: 3600 px, 64 samples (6-15 min on 4 CPU cores)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; PY="${PYTHON:-python}"; K="$1"; MODE="${2:-preview}"
WORK="${POPMAPS_WORK:-$HERE/../work}"; OUT="${POPMAPS_OUT:-$HERE/../out}"; mkdir -p "$WORK" "$OUT"
if [ "$MODE" = final ]; then W=3600; S=64; DST="$OUT/$K.png"; else W=800; S=16; DST="$OUT/${K}_preview.png"; fi
"$PY" "$HERE/legend_render.py" >/dev/null; "$PY" "$HERE/legend_render.py" election >/dev/null   # swatches under the current sun
[ -s "$WORK/$K.npz" ] || "$PY" "$HERE/prep.py" "$K"
"$PY" "$HERE/render.py" "$K" $W $S "$WORK/${K}_${MODE}_raw.png" 2>&1 | grep -E "render [0-9]|Error|Traceback" || true
"$PY" "$HERE/annotate.py" "$K" "$WORK/${K}_${MODE}_raw.png" "$DST"
echo "wrote $DST"
