<#
.SYNOPSIS
  Reproducible extraction of the Euston Road (A501) corridor from OpenStreetMap
  into a SUMO network with traffic lights preserved, suitable for TraCI control.

.DESCRIPTION
  Scripted netconvert pipeline (no GUI wizard). Three stages:
    1. Fetch OSM via Overpass QL (lean: highway ways + nodes only).
    2. netconvert -> full bbox network (diagnostic / over-extracted).
    3. netconvert -> spine network (geo-boundary clipped to the A501 corridor).
  The spine network (euston_spine.net.xml) is the dissertation target:
  the ~3-4 signalised junctions along the real Euston Road A501 stretch
  (Great Portland St -> Euston station front -> King's Cross).

  VERIFIED against Eclipse SUMO netconvert 1.26.0 on Windows.
  Every flag below appears in `netconvert --help`.

.NOTES
  SUMO_HOME must point at the SUMO install. Default below matches this machine.
  After running, CHECK the printed TLS count on euston_spine.net.xml: the target
  is ~3-4 traffic_light junctions. If the spine is empty or has too few/many,
  widen/narrow $GeoPoly (below) and re-run stage 3b only.
#>

$ErrorActionPreference = 'Stop'

# --- Config -----------------------------------------------------------------
$Sumo      = if ($env:SUMO_HOME) { $env:SUMO_HOME } else { 'C:\Program Files (x86)\Eclipse\Sumo' }
$Netconvert = Join-Path $Sumo 'bin\netconvert.exe'
$Here      = Split-Path -Parent $MyInvocation.MyCommand.Path

# Corridor bounding box (geo): west,south,east,north
# Euston Road A501 runs ~E-W across central London. Corridor from Great Portland
# St (~51.5232,-0.1445) east to King's Cross / York Way (~51.5302,-0.1228),
# buffered ~200 m N-S. The signalised stretch (Great Portland St, Gower St,
# Euston station front / Gordon St, Upper Woburn Pl / Eversholt St, King's Cross).
$BBox = '-0.1470,51.5215,-0.1205,51.5320'   # W,S,E,N  (QL below uses S,W,N,E)

$OsmFile      = Join-Path $Here 'euston_corridor.osm.xml'
$QueryFile    = Join-Path $Here 'query_ql.txt'
$NetFull      = Join-Path $Here 'euston_corridor.net.xml'
$NetArterial  = Join-Path $Here 'euston_arterial.net.xml'
$NetSpine     = Join-Path $Here 'euston_spine.net.xml'

# Arterial road types kept for the corridor (drops residential side streets +
# their spurious signals). Verified type names = "highway.<osm_value>".
$KeepTypes = 'highway.trunk,highway.primary,highway.secondary,highway.trunk_link,highway.primary_link,highway.secondary_link'

# Corridor polygon (lon lat pairs) tracing the A501 Euston Road spine, rising
# gently from the SW (Great Portland St) to the NE (King's Cross), with a ~250 m
# buffer. Used by --keep-edges.in-geo-boundary to clip the rectangle to the spine.
$GeoPoly = '-0.1450,51.5218 -0.1215,51.5288 -0.1215,51.5318 -0.1450,51.5248'

# --- Stage 1: OSM fetch -----------------------------------------------------
# We use Overpass QL directly via curl. The bundled osmGet.py emits the legacy
# Overpass XML query with a 240 s server timeout + huge element-limit, which
# 504'd on every public mirror tried (overpass-api.de, kumi.systems,
# private.coffee). The lean QL query below returns in seconds.
if (-not (Test-Path $OsmFile) -or (Get-Item $OsmFile).Length -lt 100000) {
    $ql = @'
[out:xml][timeout:180];
(
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link)$"](51.5215,-0.1470,51.5320,-0.1205);
);
(._;>;);
out body;
'@
    Set-Content -Path $QueryFile -Value $ql -NoNewline -Encoding utf8
    Write-Host "Fetching OSM from Overpass..."
    # NB: a "Mozilla/..." UA gets 406 Not Acceptable from overpass-api.de; a
    # plain UA + urlencoded `data=` param is the compatible form.
    & curl.exe -s -m 200 -A 'curl/8 EdgeNegotiator' `
        --data-urlencode "data@$QueryFile" `
        'https://overpass-api.de/api/interpreter' -o $OsmFile
    if ((Get-Item $OsmFile).Length -lt 100000) {
        Write-Host "primary mirror too small; retrying overpass.kumi.systems..."
        & curl.exe -s -m 200 -A 'curl/8 EdgeNegotiator' `
            --data-urlencode "data@$QueryFile" `
            'https://overpass.kumi.systems/api/interpreter' -o $OsmFile
    }
    if ((Get-Item $OsmFile).Length -lt 100000) { throw "OSM fetch failed / too small on both mirrors." }
}
Write-Host ("OSM file: {0:N0} bytes" -f (Get-Item $OsmFile).Length)

# --- Common netconvert flags (verified vs netconvert 1.26.0 --help) ---------
$Common = @(
    '--proj.utm'                                   # metric projection for TraCI
    '--geometry.remove'                            # -R: collapse geometry-only nodes
    '--roundabouts.guess'                          # detect roundabouts
    '--ramps.guess'; 'false'                       # corridor has no motorway ramps
    '--junctions.join'                             # merge dual-carriageway split nodes
    '--junctions.join-dist'; '30'
    '--tls.guess-signals'                          # turn OSM signal nodes into TL junctions
    '--tls.discard-simple'                         # drop trivial 1-2 link "signals"
    '--tls.join'                                   # cluster adjacent TL nodes into one program
    '--tls.join-dist'; '40'
    '--tls.default-type'; 'actuated'               # actuated programs (replace per-junction later)
    '--keep-edges.by-vclass'; 'passenger'          # car-drivable network
    '--no-turnarounds'; 'true'                     # avoid U-turn artefacts at TLS
    '--default.spreadtype'; 'center'               # symmetric lane geometry
)

# --- Stage 2: full bbox network (diagnostic) --------------------------------
Write-Host "Building full bbox network (diagnostic)..."
& $Netconvert --osm-files $OsmFile --output-file $NetFull `
    @Common `
    --remove-edges.by-vclass 'rail,rail_urban,rail_electric,tram,subway,pedestrian,bicycle,ship'

# --- Stage 3a: arterial-only (drops residential signals) --------------------
Write-Host "Building arterial network..."
& $Netconvert --osm-files $OsmFile --output-file $NetArterial `
    @Common `
    --keep-edges.by-type $KeepTypes `
    --remove-edges.isolated

# --- Stage 3b: spine network (geo-clipped) = DISSERTATION TARGET ------------
Write-Host "Building spine (corridor-clipped) network..."
& $Netconvert --osm-files $OsmFile --output-file $NetSpine `
    @Common `
    --keep-edges.by-type $KeepTypes `
    --keep-edges.in-geo-boundary $GeoPoly `
    --remove-edges.isolated

Write-Host "`nDone. TLS counts:"
$py = Join-Path $Here '..\..\.venv\Scripts\python.exe'
foreach ($net in @($NetFull, $NetArterial, $NetSpine)) {
    & $py -c "import sumolib,sys; n=sumolib.net.readNet(sys.argv[1]); t=[x for x in n.getNodes() if x.getType()=='traffic_light']; print('  %-40s TLS=%d junctions=%d edges=%d' % (sys.argv[1].split('\\')[-1], len(t), len(n.getNodes()), len([e for e in n.getEdges() if e.getFunction()!='internal'])))" $net
}
