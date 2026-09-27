"""Pack master.json + datamap layout/clusters + labels into atlas/data/orbital.json (columnar)."""
import json, glob, math, datetime as dt, numpy as np, collections
from refit import refit
RAW={}
for g in ["starlink","oneweb","kuiper","qianfan","hulianwang","iridium-NEXT","globalstar","orbcomm","other-comm","tdrss","ses","intelsat","eutelsat","telesat","x-comm","geo","satnogs"]:
    for o in json.load(open(f"raw/{g}.json")): RAW.setdefault(str(o["NORAD_CAT_ID"]),o)
T0=round(dt.datetime.now(dt.timezone.utc).timestamp()/3600)*3600
MU=398600.4418; REk=6378.137; J2=1.08262668e-3
nfit=0

R = json.load(open("master.json"))
import os
if os.path.exists("layout.json"):   # portable copy used by the scheduled refresh
    L0 = np.array(json.load(open("layout.json")), dtype=np.float32)
else:
    L0 = np.load(glob.glob("dm_work/cache/layout_*.npz")[0])["coords"]          # layout of the base build
BASE_IDS = json.load(open("layout_ids.json"))                                  # row ids of that build, in order
pos = {rid: i for i, rid in enumerate(BASE_IDS)}
F = np.load("features.npy")
have = [i for i, r in enumerate(R) if r["id"] in pos]
L = np.zeros((len(R), 2), dtype=L0.dtype)
for i in have: L[i] = L0[pos[R[i]["id"]]]
# rows added since (FCC sites): mean of the 6 nearest neighbours in feature space + small deterministic offset
base = F[have]; rng = np.random.default_rng(11); nnew = 0
for i, r in enumerate(R):
    if r["id"] in pos: continue
    nn = np.argsort(np.linalg.norm(base - F[i], axis=1))[:6]
    L[i] = L[np.array(have)[nn]].mean(0) + rng.normal(0, 0.12, 2); nnew += 1
print("placed", nnew, "new rows by feature-space KNN")
if os.path.exists("clusters.json"):
    C = {k: np.array(v) for k, v in json.load(open("clusters.json")).items()}
else:
    C = np.load(glob.glob("dm_work/cache/clusters_*.npz")[0])
LAB = json.load(open("labels.json"))

sats = [(i, r) for i, r in enumerate(R) if r["e"] == 0]
stns = [(i, r) for i, r in enumerate(R) if r["e"] == 1]

CONST = ["starlink", "oneweb", "kuiper", "qianfan", "guowang", "iridium", "globalstar", "orbcomm", "o3b",
         "tdrs", "ses", "intelsat", "eutelsat", "telesat", "other_leo", "geo", "smallsat"]
CNAME = {r["const"]: r["const_name"] for _, r in sats}
COP = {r["const"]: r["operator"] for _, r in sats}
CLINK = {r["const"]: r["links"] for _, r in sats}
ORB = ["LEO", "MEO", "GEO", "HEO/GTO"]
SST = ["Operational", "Non-operational", "Unknown"]
KINDS = ["Starlink gateway", "Starlink community gateway", "Starlink PoP", "Constellation gateway",
         "GEO teleport", "TT&C / downlink network", "Deep-space & relay", "SatNOGS station"]
GST = ["Online", "Testing", "Planned", "Offline", "Unknown"]

def ep(s):
    return round(dt.datetime.fromisoformat(s).replace(tzinfo=dt.timezone.utc).timestamp(), 1)

S = collections.defaultdict(list)
for i, r in sats:
    S["id"].append(int(r["id"])); S["name"].append(r["name"]); S["c"].append(CONST.index(r["const"]))
    S["st"].append(SST.index(r["status"])); S["o"].append(ORB.index(r["orbit"])); S["y"].append(r["year"])
    S["ld"].append(r["launch"]); S["alt"].append(round(r["alt"])); S["pe"].append(r["perigee"]); S["ap"].append(r["apogee"])
    S["inc"].append(round(r["inc"], 4)); S["n"].append(round(r["n"], 8))
    o = RAW[r["id"]]; per = 1440 / r["n"]; ok = False
    if per < 225:
        el, ok = refit(o, T0)
        # reject fits whose effective mean motion strays >2% from the published one (bad drift unwrap)
        if ok and abs(el[8] - 2*math.pi*r["n"]/86400) > 0.02 * 2*math.pi*r["n"]/86400: ok = False
    if ok:
        globals()["nfit"] += 1; epoch = T0
    else:  # deep-space or failed refit: mean elements + analytic J2 secular rates from the OMM epoch
        n = r["n"]*2*math.pi/86400; a = (MU/n/n)**(1/3); e = r["ecc"]; inc = math.radians(r["inc"]); p = a*(1-e*e); k = 1.5*n*J2*(REk/p)**2
        el = [a, e, inc, math.radians(r["raan"]), -k*math.cos(inc), math.radians(r["argp"]), 0.5*k*(5*math.cos(inc)**2-1), math.radians(r["ma"]), n]
        epoch = ep(r["epoch"])
    S["el"].append([round(el[0], 3), round(el[1], 7), round(el[2], 6), round(el[3] % (2*math.pi), 6), float("%.6e" % el[4]),
                    round(el[5] % (2*math.pi), 6), float("%.6e" % el[6]), round(el[7] % (2*math.pi), 6), float("%.9e" % el[8])])
    S["ep"].append(epoch); S["own"].append(r["owner"]); S["intl"].append(r["intl"]); S["sh"].append(r["shell"])
    S["xy"].append([round(float(L[i][0]), 2), round(float(L[i][1]), 2)])

G = collections.defaultdict(list)
for i, r in stns:
    G["name"].append(r["name"]); G["k"].append(KINDS.index(r["kind"])); G["net"].append(r["network"])
    G["op"].append(r["operator"]); G["lat"].append(round(r["lat"], 4)); G["lon"].append(round(r["lon"], 4))
    G["cc"].append(r["country"]); G["st"].append(GST.index(r["status"]) if r["status"] in GST else 4)
    G["y"].append(r["year"]); G["sv"].append([CONST.index(s) for s in r["serves"]]); G["b"].append(r["bands"])
    G["pr"].append(r["precision"]); G["obs"].append(r["obs"]); G["u"].append(r.get("url", ""))
    G["mh"].append(r.get("min_h", 0)); G["note"].append(r.get("note", ""))
    G["fcc"].append(r.get("fcc", "")); G["cs"].append(r.get("callsign", "")); G["ant"].append(r.get("antennas", ""))
    G["sta"].append(r.get("sta", []))
    G["xy"].append([round(float(L[i][0]), 2), round(float(L[i][1]), 2)])

layers = []
for li in range(3):
    lab = C[f"layer_{li}"]; d = {}; Lc = L0
    for cid in sorted(set(lab) - {-1}):
        idx = np.where(lab == cid)[0]; c = Lc[idx].mean(0)
        med = idx[np.argmin(np.linalg.norm(Lc[idx] - c, axis=1))]
        name = LAB[f"layer_{li}"][str(int(cid))]
        if name in d: name += " "  # keep keys unique
        d[name] = {"x": round(float(L0[med][0]), 2), "y": round(float(L0[med][1]), 2), "n": int(len(idx))}
    layers.append(d)

out = {
    "title": "Orbital Network Atlas",
    "built": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%MZ"), "t0": T0,
    "elements_as_of": max(r["epoch"] for _, r in sats)[:16] + "Z",
    "const": [{"k": k, "name": CNAME[k], "op": COP[k], "links": CLINK[k]} for k in CONST],
    "orbits": ORB, "sat_status": SST, "kinds": KINDS, "gs_status": GST,
    "sats": S, "stations": G, "label_layers": layers,
}
s = json.dumps(out, separators=(",", ":"))
open(os.environ.get("OUT", "out/orbital.json"), "w").write(s)
print("refit to T0", nfit, "of", len(S["id"]), "T0", T0)
print("sats", len(S["id"]), "stations", len(G["name"]), "bytes", len(s))
