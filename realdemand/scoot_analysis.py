import csv, json, os, statistics as st
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "tfl", "scoot", "1453-2627 Scoot Data.csv")
rows = []
bad = 0
with open(SRC, newline="", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        try:
            rows.append((r["ScootDetectorId"].strip(), r["Date"], int(r["Hour"]),
                         int(r["VehicleCount"].replace(",", "").strip())))
        except Exception as e:
            bad += 1; print("BAD ROW", r, e)
print(f"rows={len(rows)} unparseable={bad}")
dates = sorted({r[1] for r in rows}); print("dates", dates)
dets = sorted({r[0] for r in rows}); print("detectors", len(dets))
cnt = defaultdict(int); cell = {}
for d, dt, h, v in rows:
    cnt[(d, dt, h)] += 1; cell[(d, dt, h)] = cell.get((d, dt, h), 0) + v
dups = [k for k, c in cnt.items() if c > 1]
missing = [(d, dt, h) for d in dets for dt in dates for h in range(24) if (d, dt, h) not in cell]
print(f"duplicate (det,date,hour) keys={len(dups)}  missing cells={len(missing)} of {len(dets)*len(dates)*24}")
if missing:
    md = defaultdict(int)
    for d, dt, h in missing: md[d] += 1
    print("missing by detector:", dict(md))
junc = lambda d: d.split("/")[0] + "/" + d.split("/")[1][:3]
J = defaultdict(list)
for d in dets: J[junc(d)].append(d)
print("\n=== 1. JUNCTIONS ===")
for j in sorted(J): print(f"{j}: {len(J[j])} detectors")
det_day = {d: {dt: sum(cell.get((d, dt, h), 0) for h in range(24)) for dt in dates} for d in dets}
det_mean = {d: sum(det_day[d].values()) / len(dates) for d in dets}
zero = [d for d in dets if all(v == 0 for v in det_day[d].values())]
print("\nall-zero detectors:", zero)
zh = defaultdict(int)
for (d, dt, h), v in cell.items():
    if v == 0: zh[d] += 1
print("zero-count hours per detector (>0):", {d: n for d, n in sorted(zh.items())})
out = {}
cvf = lambda x: (st.pstdev(x) / st.mean(x) if st.mean(x) else float("nan"))
print("\n=== 2. DAILY TOTALS & CV (sample-sd CV also shown) ===")
for j in sorted(J):
    tot = {dt: sum(det_day[d][dt] for d in J[j]) for dt in dates}
    v = list(tot.values()); cvs = st.stdev(v) / st.mean(v) if st.mean(v) else float("nan")
    print(f"{j}: " + "  ".join(f"{dt}={tot[dt]:>7}" for dt in dates) + f"  mean={st.mean(v):.0f}  CV(pop)={cvf(v)*100:.2f}%  CV(sample)={cvs*100:.2f}%")
    hourly = [sum(cell.get((d, dt, h), 0) for d in J[j] for dt in dates) / len(dates) for h in range(24)]
    s = sum(hourly); share = [x / s if s else 0 for x in hourly]
    am = max(range(6, 11), key=lambda h: hourly[h]); pm = max(range(15, 20), key=lambda h: hourly[h])
    bh = max(range(24), key=lambda h: hourly[h])
    ranked = sorted(J[j], key=lambda d: -det_mean[d])
    out[j] = dict(n_detectors=len(J[j]), detectors=J[j], daily_totals=tot, cv_pop=cvf(v), cv_sample=cvs,
        hourly_profile_mean_vph=hourly, hourly_share=share,
        peak_hours=dict(am_peak_hour=am, am_vph=hourly[am], pm_peak_hour=pm, pm_vph=hourly[pm], busiest_hour=bh, busiest_vph=hourly[bh]),
        top_detectors=[(d, det_mean[d]) for d in ranked[:5]], low_detectors=[(d, det_mean[d]) for d in ranked[-3:]],
        all_detector_mean_daily={d: det_mean[d] for d in ranked},
        per_detector_day={d: det_day[d] for d in ranked})
print("\n=== 3. HOURLY PROFILE (mean veh/h over 3 days, junction total) and share % ===")
for j in sorted(J):
    o = out[j]; p = o["peak_hours"]
    print(f"\n{j}  AM peak(06-10) h{p['am_peak_hour']:02d}={p['am_vph']:.0f}  PM peak(15-19) h{p['pm_peak_hour']:02d}={p['pm_vph']:.0f}  busiest h{p['busiest_hour']:02d}={p['busiest_vph']:.0f} veh/h")
    print("  h:    " + " ".join(f"{h:>5}" for h in range(24)))
    print("  vph:  " + " ".join(f"{x:>5.0f}" for x in o["hourly_profile_mean_vph"]))
    print("  %:    " + " ".join(f"{x*100:>5.1f}" for x in o["hourly_share"]))
print("\n=== 4. TOP / LOW DETECTORS (mean daily count) ===")
for j in sorted(J):
    o = out[j]
    print(f"{j}: TOP " + ", ".join(f"{d}={v:.0f}" for d, v in o["top_detectors"]))
    print(f"      LOW " + ", ".join(f"{d}={v:.0f}" for d, v in o["low_detectors"]))
print("\n=== junction summary ranked by mean daily volume ===")
for j in sorted(J, key=lambda j: -st.mean(out[j]["daily_totals"].values())):
    print(f"{j}  mean daily={st.mean(out[j]['daily_totals'].values()):.0f}  dets={len(J[j])}  busiest vph={out[j]['peak_hours']['busiest_vph']:.0f}")
json.dump(dict(dates=dates, anomalies=dict(all_zero_detectors=zero, missing_cells=len(missing), dup_keys=len(dups),
    zero_hours_per_detector=dict(zh)), junctions=out), open(os.path.join(HERE, "scoot_summary.json"), "w"), indent=1)
