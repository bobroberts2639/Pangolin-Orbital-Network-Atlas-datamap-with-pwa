"""Assemble the satellite + ground-station master table for the Orbital Network Atlas.

Inputs (raw/):  CelesTrak OMM JSON groups (GitHub mirror satvisorcom/satvisor-data),
                satcat.csv (GitHub mirror 2048lr/celestrak-mirror),
                satnogs_stations.json (SatNOGS Network API, ODbL),
                starlink_pop.json (clarkzjw/starlink-geoip-data),
                starlink_gateways.json (geocoded from starlinkinsider list),
                curated_stations.py.
Outputs: master.csv (one row per entity) + features.npy (row-aligned numeric embedding).
"""
import csv, json, math, re, sys, collections
import numpy as np
sys.path.insert(0, '.')
from curated_stations import S as CURATED

MU = 398600.4418; RE = 6378.137

# group file -> constellation key, in assignment priority order
GROUPS = [
    ("starlink", "starlink"), ("oneweb", "oneweb"), ("kuiper", "kuiper"), ("qianfan", "qianfan"),
    ("hulianwang", "guowang"), ("iridium-NEXT", "iridium"), ("globalstar", "globalstar"),
    ("orbcomm", "orbcomm"), ("other-comm", "o3b"), ("tdrss", "tdrs"), ("ses", "ses"),
    ("intelsat", "intelsat"), ("eutelsat", "eutelsat"), ("telesat", "telesat"),
    ("x-comm", "other_leo"), ("geo", "geo"), ("satnogs", "smallsat"),
]
CONST = {  # key: (display, operator, primary links)
    "starlink": ("Starlink", "SpaceX", "Ku/Ka user & feeder, E-band gateways, optical ISL"),
    "oneweb": ("OneWeb", "Eutelsat OneWeb", "Ku user, Ka feeder"),
    "kuiper": ("Project Kuiper", "Amazon", "Ka user & feeder, optical ISL"),
    "qianfan": ("Qianfan (G60)", "SSST", "Ku/Ka"),
    "guowang": ("Guowang", "China SatNet", "Ku/Ka"),
    "iridium": ("Iridium NEXT", "Iridium", "L-band user, Ka feeder & crosslinks"),
    "globalstar": ("Globalstar", "Globalstar", "L/S user, C feeder (bent pipe)"),
    "orbcomm": ("Orbcomm", "Orbcomm", "VHF IoT/M2M"),
    "o3b": ("O3b / mPOWER", "SES", "Ka (MEO)"),
    "tdrs": ("TDRS relay", "NASA", "S/Ku/Ka space-to-space relay"),
    "ses": ("SES GEO", "SES", "C/Ku/Ka"),
    "intelsat": ("Intelsat GEO", "Intelsat", "C/Ku/Ka"),
    "eutelsat": ("Eutelsat GEO", "Eutelsat", "Ku/Ka"),
    "telesat": ("Telesat", "Telesat", "C/Ku/Ka"),
    "other_leo": ("Other comms LEO", "various", "various"),
    "geo": ("Other GEO (mixed use)", "various", "various"),
    "smallsat": ("SatNOGS-tracked smallsats", "various", "VHF/UHF/S amateur & science"),
}

def status_of(code):
    if code in ("+", "P", "B", "S", "X"): return "Operational"
    if code in ("-", "D"): return "Non-operational"
    return "Unknown"

# ---------------- satellites
satcat = {r["NORAD_CAT_ID"]: r for r in csv.DictReader(open("raw/satcat.csv"))}
seen, sats = set(), []
for fname, key in GROUPS:
    for o in json.load(open(f"raw/{fname}.json")):
        nid = o["NORAD_CAT_ID"]
        if nid in seen: continue
        if key == "tdrs" and not o["OBJECT_NAME"].startswith("TDRS"): continue
        seen.add(nid)
        sc = satcat.get(str(nid), {})
        n = o["MEAN_MOTION"]; a = (MU / (n * 2 * math.pi / 86400) ** 2) ** (1 / 3)
        e = o["ECCENTRICITY"]; alt = a - RE
        per, apo = a * (1 - e) - RE, a * (1 + e) - RE
        oc = "GEO" if 34000 < alt < 37500 and o["INCLINATION"] < 20 else \
             "LEO" if apo < 2000 else "MEO" if apo < 34000 else "HEO/GTO"
        ld = sc.get("LAUNCH_DATE") or ""
        disp, opname, links = CONST[key]
        owner = sc.get("OWNER", "")
        sats.append(dict(
            e=0, id=str(nid), name=o["OBJECT_NAME"], const=key, const_name=disp, operator=opname,
            owner=owner, launch=ld, year=int(ld[:4]) if ld else None, status=status_of(sc.get("OPS_STATUS_CODE", "")),
            orbit=oc, alt=round(alt, 1), perigee=round(per), apogee=round(apo), inc=o["INCLINATION"], ecc=e,
            raan=o["RA_OF_ASC_NODE"], argp=o["ARG_OF_PERICENTER"], ma=o["MEAN_ANOMALY"], n=n, epoch=o["EPOCH"],
            intl=o["OBJECT_ID"], links=links))
print("satellites", len(sats), collections.Counter(s["const"] for s in sats).most_common())

# shells: group LEO constellation sats by rounded inclination + altitude band
def shell(s):
    if s["orbit"] != "LEO": return f"{s['orbit']}"
    inc = s["inc"]; alt = s["alt"]
    if s["const"] == "starlink" and alt < 400: return "Orbit-raising / deorbiting"
    return f"{round(inc*2)/2:.1f}° · {int(round(alt/10)*10)} km"
for s in sats: s["shell"] = shell(s)

# ---------------- ground stations
stations = []
def st(**k):
    k.setdefault("e", 1); stations.append(k)

for g in json.load(open("starlink_gateways.json")):
    st(id=f"slgw-{len(stations)}", name=f"{g['name']}{', '+g['region'] if g['region'] else ''}",
       kind="Starlink gateway", network="SpaceX Starlink", operator="SpaceX", lat=g["lat"], lon=g["lon"],
       country=g["country"], status={"live": "Online", "construction": "Planned", "pending": "Planned"}.get(g["status"], "Unknown"),
       year=None, serves=["starlink"], bands="Ka/E feeder", precision="town (approx.)" if g["geo"] == "manual" else "town",
       obs=None, url="https://starlinkinsider.com/starlink-gateway-locations/")

for p in json.load(open("raw/starlink_pop.json")):
    if not p.get("show") or (p["lat"] == 0 and p["lon"] == 0): continue
    t = p.get("type", "pop")
    kind = "Starlink community gateway" if t == "community_gateway" else "Starlink PoP"
    note = re.sub("<[^>]+>", " ", p.get("note", "")).strip()
    st(id=f"slpop-{len(stations)}", name=(p["city"] or p["code"]) + (" PoP" if kind == "Starlink PoP" else " community gateway"),
       kind=kind, network="SpaceX Starlink", operator="SpaceX", lat=p["lat"], lon=p["lon"], country=p["country"],
       status="Online", year=None, serves=["starlink"] if kind != "Starlink PoP" else [], bands="terrestrial IP" if kind == "Starlink PoP" else "Ka",
       precision="site", obs=None, note=note[:160], url="https://pan.uvic.ca/~clarkzjw/starlink/")

KIND = {"gateway": "Constellation gateway", "ttc": "TT&C / downlink network", "deep": "Deep-space & relay", "teleport": "GEO teleport"}
for (name, op, net, lat, lon, cc, serves, prec, kind) in CURATED:
    st(id=f"cur-{len(stations)}", name=name, kind=KIND[kind], network=net, operator=op, lat=lat, lon=lon, country=cc,
       status="Online", year=None, serves=serves, bands="", precision=prec, obs=None, url="")

for s in json.load(open("raw/satnogs_stations.json")):
    if s["lat"] is None or s["lng"] is None: continue
    bands = sorted({a.get("band", "") for a in s.get("antenna") or [] if a.get("band")})
    st(id=f"sn-{s['id']}", name=s["name"], kind="SatNOGS station", network="SatNOGS (open)", operator=s.get("owner") or "",
       lat=s["lat"], lon=s["lng"], country="", status=s["status"] if s["status"] != "Testing" else "Testing",
       year=int(s["created"][:4]) if s.get("created") else None, serves=["smallsat"], bands="/".join(bands),
       precision="station", obs=s.get("observations"), url=f"https://network.satnogs.org/stations/{s['id']}/",
       min_h=s.get("min_horizon") or 0)
import os
BASE_ONLY = bool(os.environ.get("BASE_ONLY"))
# ---------------- FCC ICFS Form 312 Schedule B sites (exact coordinates, antennas, bands)
def _hav(a, b, c, d):
    a, b, c, d = map(math.radians, (a, b, c, d))
    return 2 * 6371 * math.asin(math.sqrt(math.sin((c - a) / 2) ** 2 + math.cos(a) * math.cos(c) * math.sin((d - b) / 2) ** 2))
FCC = json.load(open("fcc_sites.json"))
BANDNAME = {"SpaceX": "Ka · Q/V · E · W (feeder)", "Kuiper": "Ka (feeder)", "Northwood": "S · X · Ka", "RBC Signals": "UHF"}
ICFS = "https://fccprod.servicenowservices.com/icfs?id=ibfs_application_summary&number="
nmatch = nnew = 0
for f in ([] if BASE_ONLY else FCC["filings"]):
    fst = {"Pending Review": "Planned", "Closed": "Unknown"}.get(f["st"], "Unknown")
    extra = dict(fcc=f["f"], callsign=f["cs"], antennas=f"{f['ant'][1]} × {f['ant'][0]:g} m", elev_m=f["el"],
                 fcc_status=f["st"], bands=BANDNAME[f["op"]], precision="site (FCC filing)", url=ICFS + f["f"])
    if f["op"] == "SpaceX":
        town = f["a"].split(",")[0].strip().lower()   # match only the same town on the 2025 list, within 40 km
        cand = [x for x in stations if x["kind"] == "Starlink gateway" and x["name"].split(",")[0].strip().lower() == town
                and _hav(x["lat"], x["lon"], f["lat"], f["lon"]) < 40
                and x["status"] != "Online"]   # a new licence next to a live gateway is a second site
        if cand:  # same gateway already on the 2025 list: snap to the filed coordinates, keep its status
            x = min(cand, key=lambda x: _hav(x["lat"], x["lon"], f["lat"], f["lon"]))
            x.update(extra, lat=f["lat"], lon=f["lon"], name=x["name"] + " — " + f["n"]); nmatch += 1; continue
        new = dict(kind="Starlink gateway", network="SpaceX Starlink", operator="SpaceX", serves=["starlink"])
    elif f["op"] == "Kuiper":
        new = dict(kind="Constellation gateway", network="Amazon Kuiper", operator="Amazon (Kuiper Systems LLC)", serves=["kuiper"])
    else:
        new = dict(kind="TT&C / downlink network", network=f["op"] + " (ground station as a service)", operator=f["op"],
                   serves=["other_leo", "smallsat", "kuiper"] if f["op"] == "Northwood" else ["smallsat"])
        fst = "Online"   # modification of an existing licensed station
    st(id=f"fcc-{f['f']}", name=f"{f['n']} ({f['a']})", lat=f["lat"], lon=f["lon"], country="US", status=fst,
       year=int(f["f"][8:12]) if f["op"] in ("SpaceX", "Kuiper") else None, obs=None, **new, **extra)
    nnew += 1
print("FCC sites: matched", nmatch, "existing gateways, added", nnew)
# ---------------- FCC special temporary authorities (SES-STA), deduplicated to sites by sta_merge.py
STA = json.load(open("fcc_sta_sites.json"))
nm_ = ns_ = nn_ = 0
def _town(x): return re.split(r"[,(]", x)[0].strip().lower().replace(" gateway", "")
for e in ([] if BASE_ONLY else STA["sites"]):
    files = [f["f"] for f in e["filings"]]
    exact = e["precision"].startswith("site")
    best = None
    for x in stations:
        if x["kind"] in ("SatNOGS station", "Starlink PoP"): continue
        d = _hav(x["lat"], x["lon"], e["lat"], e["lon"])
        fam_e = e["applicant"].split()[0].lower().strip(",")
        same = fam_e in (x["operator"] + " " + x["network"]).lower() or (exact and str(x.get("precision", "")).startswith("site"))
        if d < 1.5 and same and (best is None or d < best[0]): best = (d, x)
    if best is None:   # same town, same network, within 40 km (2025 gateway list, curated teleports)
        for x in stations:
            if x["kind"] in ("SatNOGS station", "Starlink PoP") or x.get("fcc"): continue
            same_net = (x["kind"] == e["kind"] == "Starlink gateway") or (e["network"].split()[0].lower() in (x["network"] + " " + x["operator"]).lower())
            if same_net and _town(x["name"]) == _town(e["area"] or e["name"]) and _hav(x["lat"], x["lon"], e["lat"], e["lon"]) < 40:
                best = (0, x); break
    if best:
        x = best[1]; nm_ += 1
        x.setdefault("sta", []); x["sta"] += [f for f in files if f not in x["sta"]]
        if x["status"] in ("Planned", "Unknown"): x["status"] = "Online"; x["sta_note"] = "operating under temporary authority"
        if exact and not str(x.get("precision", "")).startswith("site"):
            x.update(lat=e["lat"], lon=e["lon"], precision="site (FCC STA filing)"); ns_ += 1
        if not x.get("antennas") and e["antennas"]: x["antennas"] = e["antennas"]
        if e["bands"] and (not x.get("bands") or x["bands"] in ("", "Ka/E feeder")): x["bands"] = e["bands"]
        continue
    par = next((p for p in e["parents"] if p.startswith("SES-LIC-")), "")
    yr = int((par or files[0])[8:12])
    st(id=f"sta-{files[0]}", name=e["name"] + (f" ({e['area']})" if e["area"] and e["area"] not in e["name"] and len(e["area"]) < 40 else ""),
       kind=e["kind"], network=e["network"], operator=e["applicant"], lat=e["lat"], lon=e["lon"], country="US",
       status="Online", sta_note="operating under temporary authority", year=yr, serves=e["serves"], bands=e["bands"],
       antennas=e["antennas"], precision=e["precision"], obs=None, sta=files, fcc=par,
       url="https://fccprod.servicenowservices.com/icfs?id=ibfs_application_summary&number=" + files[0])
    nn_ += 1
print("FCC STA sites: merged", nm_, "(snapped", ns_, ") added", nn_)
# 2025-list gateways placed at a town centre that now have an FCC-filed gateway in the same town: fold them in
drop = set()
for x in stations:
    if x["kind"] != "Starlink gateway" or str(x.get("precision", "")).startswith("site") or x.get("fcc") or x.get("sta"): continue
    for y in stations:
        if y is x or y["kind"] != "Starlink gateway" or not str(y.get("precision", "")).startswith("site"): continue
        if _town(y["name"].split("(")[-1]) == _town(x["name"]) or _town(y["name"]) == _town(x["name"]):
            if _hav(x["lat"], x["lon"], y["lat"], y["lon"]) < 40:
                if x["status"] == "Online": y["status"] = "Online"
                drop.add(id(x)); break
stations[:] = [x for x in stations if id(x) not in drop]
print("folded", len(drop), "town-level 2025 gateways into FCC-filed sites")
print("stations", len(stations), collections.Counter(x["kind"] for x in stations).most_common())

# ---------------- text + features for the similarity layout
rows = sats + stations
def text_of(r):
    if r["e"] == 0:
        return (f"{r['const_name']} satellite {r['name']} | {r['operator']} | {r['orbit']} {int(r['alt'])} km "
                f"incl {r['inc']:.1f} | shell {r['shell']} | launched {r['launch'][:7]} | {r['status']}")
    return (f"{r['kind']} {r['name']} | {r['network']} | {r['operator']} | {r['country']} | "
            f"lat {r['lat']:.0f} lon {r['lon']:.0f} | {r['status']} | bands {r['bands']}")
for r in rows: r["text"] = text_of(r)

consts = list(CONST); kinds = sorted({s["kind"] for s in stations}); orbits = ["LEO", "MEO", "GEO", "HEO/GTO"]
def oh(v, vocab, w=1.0):
    z = np.zeros(len(vocab)); z[vocab.index(v)] = w; return z
F = []
for r in rows:
    if r["e"] == 0:
        la = math.log10(max(r["alt"], 150)); y = (r["year"] or 2015)
        v = np.concatenate([[2.0, 0], [0, 0, 0],                              # entity + geo block (zeros)
            [ (la - 2.5) * 2.5, math.cos(math.radians(r["inc"])) * 1.2, math.sin(math.radians(r["inc"])) * 1.2,
              min(r["ecc"], .8) * 3, (y - 2015) / 9.0 ],
            oh(r["orbit"], orbits, 2.0), oh(r["const"], consts, 3.0), np.zeros(len(kinds)),
            [ {"Operational": 0, "Non-operational": .6, "Unknown": .3}[r["status"]] ]])
    else:
        la, lo = math.radians(r["lat"]), math.radians(r["lon"]); y = r["year"] or 2020
        v = np.concatenate([[0, 2.0], [math.cos(la)*math.cos(lo)*2.0, math.cos(la)*math.sin(lo)*2.0, math.sin(la)*2.0],
            [0, 0, 0, 0, (y - 2020) / 8.0],
            np.zeros(len(orbits)), np.zeros(len(consts)), oh(r["kind"], kinds, 3.0),
            [ {"Online": 0, "Testing": .3, "Planned": .4, "Offline": .6, "Unknown": .3}.get(r["status"], .3) ]])
    F.append(v)
F = np.array(F, dtype=np.float32)
F -= F.mean(axis=0)
F += np.random.default_rng(7).normal(0, 0.01, F.shape).astype(np.float32)  # break exact ties
np.save("features.npy", F)

cols = ["e", "id", "name", "text"]
with open("master.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(cols)
    for r in rows: w.writerow([r[c] for c in cols])
json.dump(rows, open("master.json", "w"))
if BASE_ONLY: json.dump([r["id"] for r in rows], open("layout_ids.json", "w"))
print("rows", len(rows), "features", F.shape)
