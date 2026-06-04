# Lambeth Corridor Extraction & Demand Calibration

**Corridor:** Brixton -> Elephant & Castle (A23 Brixton Rd -> A3 Kennington Park Rd / Newington Butts), London Boroughs of Lambeth & Southwark.

**Status of this document:** Lead with what was *actually run and verified* on this machine vs. what is *documented-only*. Anything I could not execute is tagged **UNVERIFIED — needs manual run**.

**Environment actually used (verified):**
- Eclipse SUMO **1.26.0** at `C:\Program Files (x86)\Eclipse\Sumo` (NB: brief said 1.27; the *bin* is 1.26.0, the bundled `sumolib`/`tools` report 1.27.0 — harmless mismatch).
- venv `e:/assignments/edge-traffic-negotiator/03-implementation/edge-negotiator/.venv` — has `sumolib`, `traci`, `pandas`, `numpy`; I added **`pyproj` 3.7.2** (needed for lon/lat -> net-XY snapping; standard SUMO dep). `scipy` and `rtree` are **absent** (see caveats).
- All files live under `.../edge-negotiator/sumo/lambeth/`. Nothing under `src/` or `tests/` was touched.

---

## TL;DR — what I built and verified

| Artefact | Status |
|---|---|
| `lambeth_corridor.osm.xml` (1.84 MB OSM) | **fetched & verified** (Overpass QL) |
| `lambeth_corridor.net.xml` (full bbox, diagnostic) | **built** — 60 TLS junctions (over-extracted) |
| `lambeth_arterial.net.xml` (arterials only) | **built** — 31 TLS junctions |
| `lambeth_spine.net.xml` (**dissertation target**, geo-clipped) | **built** — **9 TLS junctions**, 88 junctions, 130 edges, runs clean on light demand (0 teleports) |
| `extract_corridor.ps1` | reproducible 3-stage netconvert pipeline |
| `aadf.zip` (19.5 MB DfT AADF, all GB) | **downloaded & verified live** |
| `aadf_to_edgedata.py` | AADF -> SUMO edgeData; **ran**, snapped **12 corridor count points** onto spine edges (snap 0-51 m) |
| `aadf_counts.edgedata.xml` | 12 calibrated edge-count anchors |
| routeSampler calibration | **ran** — **GEH<5 at 100 % of 12 count locations** |

**Biggest risk (be honest with the user):** the *demand-intensity / TLS-timing* calibration, **not** the geometry. The network geometry is sound (light demand = 0 teleports). But the raw AADF-anchored peak demand (PEAK_FRACTION=0.085 over a 1 h burst with all-pairs random base routing) **gridlocks** the corridor: a full-peak SUMO run produced **490 teleports (259 jam)** with only 4285/7908 vehicles inserted. This is the expected "raw calibration too hot" state and is fixable (lower peak fraction / spread the profile / fix actuated TLS programs / proper OD instead of random routing), but it is the work that stands between "net builds" and "dissertation-ready". See the DoD checklist (section 3).

---

## 1. OSM -> SUMO network (reproducible, scripted)

### 1.1 Bounding box / OSM query

Corridor bbox (geo, W,S,E,N): **`-0.1190, 51.4600, -0.0930, 51.4980`** — Brixton (~51.4626,-0.1145) to Elephant & Castle (~51.4946,-0.0997) with buffer.

**OSM fetch — I did NOT use `osmGet.py`.** The bundled `osmGet.py` emits the *legacy Overpass XML* query (`<osm-script timeout="240" element-limit="1073741824">`). Every public mirror I tried returned **504 Gateway Timeout** on it (`overpass-api.de`, `overpass.kumi.systems`, `overpass.private.coffee`). Switching to a **lean modern Overpass QL** query (highway ways + their nodes only, no relation recursion) returned **HTTP 200, 1.84 MB in seconds**. Query (`query_ql.txt`):

```overpassql
[out:xml][timeout:180];
(
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link)$"](51.4600,-0.1190,51.4980,-0.0930);
);
(._;>;);
out body;
```
(Note Overpass bbox order is **S,W,N,E**.) Fetch command actually run:
```powershell
curl.exe -s -m 200 -H 'User-Agent: Mozilla/5.0 (EdgeNegotiator dissertation)' `
  --data-binary '@query_ql.txt' `
  'https://overpass-api.de/api/interpreter' -o lambeth_corridor.osm.xml
```

### 1.2 netconvert pipeline (flags VERIFIED against `netconvert 1.26.0 --help`)

Every flag below was grep-confirmed present in `--help`. **Correction to the brief:** the OSM input flag is **`--osm-files`** (hyphen), not `--osm.files`.

Common flags (all three stages):
| Flag | Purpose | Verified |
|---|---|---|
| `--osm-files <f>` | OSM input | yes |
| `--output-file <f>` | net output (`-o`) | yes |
| `--proj.utm` | metric UTM projection (needed for TraCI + geo snapping) | yes |
| `--geometry.remove` (`-R`) | collapse geometry-only nodes | yes |
| `--roundabouts.guess` | detect roundabouts | yes |
| `--ramps.guess false` | corridor has no motorway ramps (brief: "ramps off") | yes |
| `--junctions.join` + `--junctions.join-dist 30` | merge split dual-carriageway nodes | yes |
| `--tls.guess-signals` | turn OSM `traffic_signals` nodes into controlled TL junctions | yes |
| `--tls.discard-simple` | drop trivial 1-2-link "signals" (kills phantom crossings) | yes |
| `--tls.join` + `--tls.join-dist 40` | cluster adjacent TL nodes into ONE program | yes |
| `--tls.default-type actuated` | actuated default programs | yes |
| `--keep-edges.by-vclass passenger` | car-drivable network | yes |
| `--no-turnarounds true` | avoid U-turn artefacts | yes |
| `--default.spreadtype center` | symmetric lane geometry | yes |

Stage-specific:
- **Full bbox (diagnostic):** add `--remove-edges.by-vclass "rail,rail_urban,rail_electric,tram,subway,pedestrian,bicycle,ship"`.
- **Arterial:** add `--keep-edges.by-type "highway.trunk,highway.primary,highway.secondary,highway.trunk_link,highway.primary_link,highway.secondary_link"` + `--remove-edges.isolated`.
- **Spine (TARGET):** arterial flags **plus** `--keep-edges.in-geo-boundary "-0.1175,51.4615 -0.1095,51.4615 -0.0955,51.4955 -0.1035,51.4955"` — a ~250 m buffered polygon tracing the A23/A3 spine. This is what clips the wide rectangle down to the single corridor.

Run it all with: `pwsh -File sumo/lambeth/extract_corridor.ps1`

### 1.3 Results (actually measured with sumolib)

| Network | TLS junctions | Total junctions | Edges | Note |
|---|---|---|---|---|
| `lambeth_corridor.net.xml` (full bbox) | **60** | 1382 | 3055 | over-extracted: captures all parallel routes + side-street signals |
| `lambeth_arterial.net.xml` | **31** | 254 | 444 | drops residential; still spans parallel A-roads (A202/A203/A215) |
| `lambeth_spine.net.xml` | **9** | 88 | 130 | **geo-clipped to the Brixton->E&C axis (3.86 km N-S). In the target ~10-13 band.** |

The 9 spine TLS junctions correspond to real signals along Brixton Rd / Kennington Park Rd / Newington (several are `cluster_...` = SUMO-joined multi-node intersections, which is correct). Two have only 2 incoming edges (likely signalised pedestrian crossings) — review whether to keep or convert.

**To land squarely in 10-13:** widen the polygon slightly toward E&C / nudge `--tls.join-dist`, or hand-pick which of the 31 arterial TLS to include via `--keep-edges.input-file`. The spine geometry **ran clean** in SUMO on a 100-vehicle smoke test (0 teleports, avg wait 5 s), so it is structurally connected end-to-end.

---

## 2. Demand calibration — DfT AADF -> routes

### 2.1 Data source (VERIFIED live)

**DfT Road Traffic Statistics — AADF by count point.**
- Portal: https://roadtraffic.dft.gov.uk and downloads page https://roadtraffic.dft.gov.uk/downloads
- Dataset (data.gov.uk): https://www.data.gov.uk/dataset/208c0e7b-353f-4e2d-8b7a-1a7118467acc/gb-road-traffic-counts
- **Direct count-point CSV (verified, HTTP 200, 19.5 MB):**
  `https://storage.googleapis.com/dft-statistics/road-traffic/downloads/data-gov-uk/dft_traffic_counts_aadf.zip`
- Local-authority aggregate: `.../local_authority_traffic.csv`; regional: `.../region_traffic_by_vehicle_type.csv`

**AADF CSV columns (read directly from the real file, 34 cols):**
`count_point_id, year, region_id, region_name, region_ons_code, local_authority_id, local_authority_name, local_authority_code, road_name, road_category, road_type, start_junction_road_name, end_junction_road_name, easting, northing, latitude, longitude, link_length_km, link_length_miles, estimation_method, estimation_method_detailed, pedal_cycles, two_wheeled_motor_vehicles, cars_and_taxis, buses_and_coaches, LGVs, HGVs_2_rigid_axle, HGVs_3_rigid_axle, HGVs_4_or_more_rigid_axle, HGVs_3_or_4_articulated_axle, HGVs_5_articulated_axle, HGVs_6_articulated_axle, all_HGVs, all_motor_vehicles`

`all_motor_vehicles` = the AADF total (both directions). AADF is a **24 h, both-direction average**.

**Corridor coverage is excellent (verified):** 57 count points fall in the bbox; the spine has dense **2025** coverage with junction names matching the network, e.g. A23 Brixton Rd cp 36269 (AADF 20072), 6266 (18322), 18461 (17984); A3 cp 36109 (28713), 28507 (17228); E&C A3 cp 46107 (34065), A201 cp 46783 (28404).

### 2.2 AADF -> hourly peak -> edge counts (method, RAN)

`aadf_to_edgedata.py` does:
1. Filter AADF to the corridor bbox, **latest year per count point**.
2. **Snap** each count point (`latitude`/`longitude` -> net XY via `net.convertLonLat2XY`, pyproj) to nearest `passenger`-allowed edge within 60 m.
3. Convert: `per_direction_peak = AADF * PEAK_FRACTION / 2` veh/h. **PEAK_FRACTION default 0.085** = assumed ~8.5 % of daily flow in the peak hour (the "assumed peak profile" the brief calls for — *this is a modelling assumption, tune per scenario; a defensible refinement is to use DfT/TfL time-of-day profiles*).
4. Write a SUMO **edgeData** `<meandata>` file with `entered="<veh/h>"` per edge.

Ran: snapped **12** corridor count points onto spine edges (snap distances mostly 0-9 m, worst 51 m on a minor road) -> `aadf_counts.edgedata.xml`.

### 2.3 routeSampler calibration (RAN, GEH<5 at 100 %)

```powershell
# 1. candidate route pool (random base demand to sample FROM)
python "$env:SUMO_HOME\tools\randomTrips.py" -n lambeth_spine.net.xml `
  -r candidate.rou.xml -b 0 -e 3600 --insertion-rate 3000 --fringe-factor 30 --validate --seed 1

# 2. sample candidates to match AADF edge counts
python "$env:SUMO_HOME\tools\routeSampler.py" -r candidate.rou.xml `
  -d aadf_counts.edgedata.xml -o calibrated.rou.xml `
  --edgedata-attribute entered --geh-ok 5 -v
```
Result actually obtained: *"Wrote 7908 routes (263 distinct) achieving total count 8930 (100.00%) at 12 locations. **GEH<5.0 for 100.00%**."* GEH<5 is the standard traffic-engineering acceptance threshold — so the calibration *fit* is excellent.

> **`--optimize full` is documented in the brief but UNVERIFIED here:** routeSampler aborts with *"Cannot use optimization (scipy not installed)"*. Greedy sampling (above) already hit GEH<5; if you want the LP refinement, `pip install scipy` into the venv first.

---

## 3. Definition of Done — Lambeth net is dissertation-ready

- [ ] **TLS count matches reality (~10-13).** Currently **9** on the spine net (verified). Widen the geo-boundary polygon toward E&C and/or hand-select arterial junctions to reach 10-13. Cross-check the count against TfL/OSM on the ground.
- [ ] **TLS programs are sane.** Default `actuated` programs are placeholders. Inspect each junction in `netedit`; fix any TL that "does not control any links" (one such warning seen: TL `3386113653`). Verify phase counts match the SLM action space (the brief's `{"phase": N}`).
- [ ] **Connectivity / no dead corridor.** Verified: 15 entry + 14 exit fringe edges; 100-veh smoke test = 0 teleports. Re-check after any polygon change (`--remove-edges.isolated` + a smoke run).
- [ ] **Demand calibrated to AADF.** Method verified end-to-end (GEH<5 at all 12 anchors). Anchors use latest-year AADF on the spine. Re-snap after the net is frozen (edge IDs change when geometry changes).
- [ ] **Runs without teleports/gridlock at the target demand.** **NOT YET MET.** Full-peak calibrated run gave **490 teleports / 4285 of 7908 inserted**. Required work: (a) reduce/realistic-ify the peak profile (PEAK_FRACTION, spread over multiple `<interval>`s instead of one 1 h burst); (b) use proper OD/turn-ratio demand rather than all-pairs random base routing; (c) tune TLS green splits; (d) raise `--time-to-teleport` only as a diagnostic, not a fix. Target: teleports ~0 and >95 % of loaded vehicles inserted within the analysis window.
- [ ] **Determinism for the sweep.** Fix `--seed` in randomTrips and routeSampler; archive `aadf.zip` (so the AADF snapshot is reproducible — DfT updates the file).
- [ ] **Geo integrity.** Built with `--proj.utm`; confirm TraCI coordinates and the SLM/MaxPressure detectors read the right lanes.

---

## 4. File inventory (`sumo/lambeth/`)

| File | What it is |
|---|---|
| `extract_corridor.ps1` | reproducible 3-stage OSM->net pipeline (run this) |
| `query_ql.txt` | the working Overpass QL query |
| `lambeth_corridor.osm.xml` | raw OSM (1.84 MB) |
| `lambeth_corridor.net.xml` | full-bbox net (diagnostic, 60 TLS) |
| `lambeth_arterial.net.xml` | arterials-only net (31 TLS) |
| `lambeth_spine.net.xml` | **corridor target net (9 TLS)** |
| `smoke.rou.xml` | 100-veh smoke demand (0-teleport sanity check) |
| `aadf.zip` | DfT AADF snapshot (19.5 MB) — archive for reproducibility |
| `aadf_to_edgedata.py` | AADF -> SUMO edgeData snapper |
| `aadf_counts.edgedata.xml` | 12 AADF edge-count anchors for routeSampler |

## 5. Caveats / UNVERIFIED items
- **routeSampler `--optimize full`**: UNVERIFIED — needs `scipy` in venv.
- **`rtree` absent**: sumolib falls back to brute-force neighbor search (works, just slower). Optional `pip install rtree`.
- **PEAK_FRACTION=0.085** and **all-pairs random base routing** are modelling assumptions, not calibrated facts — these are the primary cause of the gridlock and the main thing to refine.
- **SUMO bin is 1.26.0**, not 1.27 as the brief states (tools report 1.27.0).
