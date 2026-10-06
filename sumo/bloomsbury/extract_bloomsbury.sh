#!/usr/bin/env bash
# Reproducible extraction of the Bloomsbury (WC1) area from OpenStreetMap into a SUMO
# network -- a REAL London GRID topology (9 signalised junctions), a genuine contrast to
# the Euston A501 linear arterial, for the full-scale multi-topology study.
#
# Same lean-Overpass-QL + netconvert pipeline as euston/extract_corridor.ps1 (the public
# osmGet 504s; a GET of the lean QL returns in seconds). Verified on SUMO netconvert
# 1.26.0. Demand is randomTrips (synthetic magnitude on the REAL topology): the topology
# is real London; the demand volume is assumed (the same §8 caveat as the corridor --
# no Bloomsbury-specific hourly counts), so results here are descriptive pilots too.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SUMO="${SUMO_HOME:-/c/Program Files (x86)/Eclipse/Sumo}"
# Bloomsbury bounding box (S,W,N,E): Russell Square / Gower St / Southampton Row grid.
BBOX="51.5205,-0.1310,51.5270,-0.1180"

# 1. Fetch OSM (lean QL, GET; POST to the same endpoint returned an HTML error page).
curl -s --max-time 90 -G "https://overpass-api.de/api/interpreter" \
  --data-urlencode "data=[out:xml][timeout:120];(way[\"highway\"~\"^(primary|secondary|tertiary|residential|unclassified|living_street)\$\"]($BBOX););(._;>;);out body;" \
  -o "$HERE/bloomsbury.osm.xml"

# 2. netconvert -> signalised network (guess+join signals, drop simple ones, UTM proj).
"$SUMO/bin/netconvert" --osm-files "$HERE/bloomsbury.osm.xml" -o "$HERE/bloomsbury.net.xml" \
  --geometry.remove --roundabouts.guess --ramps.guess --junctions.join \
  --tls.guess-signals --tls.discard-simple --tls.join --no-turnarounds \
  --keep-edges.by-vclass passenger --proj.utm
# Expect ~9 traffic_light junctions (check the printed TLS count).

# 3. Demand: randomTrips (synthetic magnitude on the real topology), seed 42, ~1h.
python "$SUMO/tools/randomTrips.py" -n "$HERE/bloomsbury.net.xml" \
  -o "$HERE/_trips.xml" -r "$HERE/bloomsbury.rou.xml" \
  -b 0 -e 1200 -p 0.7 --fringe-factor 5 --seed 42 --validate \
  --min-distance 300 --vehicle-class passenger
echo "done: bloomsbury.net.xml + bloomsbury.rou.xml"
