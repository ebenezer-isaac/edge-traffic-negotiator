#!/usr/bin/env bash
# Reproducible extraction of the OLD STREET junction (EC1, "Silicon Roundabout" -> rebuilt
# signalised peninsula junction) from OpenStreetMap into a SUMO network -- a COMPLEX real
# multi-arm signalised junction, the hard-case contrast to the linear Euston A501 corridor and
# the Bloomsbury grid. Same lean-Overpass-QL + netconvert pipeline as extract_bloomsbury.sh.
#
# Demand is randomTrips (synthetic magnitude on the REAL topology): topology is real London, the
# volume is assumed (same §8 caveat) -- descriptive pilot until real DfT-hourly/TfL demand lands.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SUMO="${SUMO_HOME:-/c/Program Files (x86)/Eclipse/Sumo}"
# Old Street junction bounding box (S,W,N,E): the City Rd / Old St / East Rd / Old St crossroads
# and its approaches (~600 m box centred on ~51.5256,-0.0876).
BBOX="51.5228,-0.0925,51.5286,-0.0828"

# 1. Fetch OSM (lean QL, GET).
curl -s --max-time 90 -G "https://overpass-api.de/api/interpreter" \
  --data-urlencode "data=[out:xml][timeout:120];(way[\"highway\"~\"^(primary|secondary|tertiary|residential|unclassified|living_street|trunk)\$\"]($BBOX););(._;>;);out body;" \
  -o "$HERE/oldstreet.osm.xml"

# 2. netconvert -> signalised network. Larger join distance to collapse the former roundabout
#    island into a single controlled junction; guess+join signals; keep passenger roads.
"$SUMO/bin/netconvert" --osm-files "$HERE/oldstreet.osm.xml" -o "$HERE/oldstreet.net.xml" \
  --geometry.remove --roundabouts.guess --ramps.guess \
  --junctions.join --junctions.join-dist 40 \
  --tls.guess-signals --tls.discard-simple --tls.join --no-turnarounds \
  --keep-edges.by-vclass passenger --proj.utm

# 3. Demand: randomTrips (synthetic magnitude on the real topology), seed 42, ~1h.
python "$SUMO/tools/randomTrips.py" -n "$HERE/oldstreet.net.xml" \
  -o "$HERE/_trips.xml" -r "$HERE/oldstreet.rou.xml" \
  -b 0 -e 1200 -p 0.7 --fringe-factor 5 --seed 42 --validate \
  --min-distance 250 --vehicle-class passenger
echo "done: oldstreet.net.xml + oldstreet.rou.xml"
