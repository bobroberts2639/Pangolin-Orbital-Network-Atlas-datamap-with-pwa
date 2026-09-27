"""Orbital Network Atlas — scheduled refresh.

Re-downloads the public orbital data (CelesTrak GP elements + SATCAT via GitHub mirrors,
Starlink PoPs), rebuilds the master table, re-epochs every orbit with SGP4 to *now*, and writes
data/orbital.json. Satellites launched since the similarity layout was computed are placed
by feature-space nearest neighbours; cluster labels are unchanged.

Run from a folder containing the files published under pipeline/ in the atlas artifact:
    python refresh.py            ->  out/orbital.json
Needs: numpy, sgp4  (pip install numpy sgp4)
"""
import json, os, subprocess, sys, urllib.request, datetime as dt
os.makedirs("raw", exist_ok=True); os.makedirs("out", exist_ok=True)
SV = "https://raw.githubusercontent.com/satvisorcom/satvisor-data/master/celestrak/json/"
GROUPS = ["starlink", "oneweb", "kuiper", "qianfan", "hulianwang", "iridium-NEXT", "globalstar", "orbcomm", "other-comm",
          "tdrss", "ses", "intelsat", "eutelsat", "telesat", "x-comm", "geo", "satnogs"]
def get(url, path, min_bytes=1000):
    for attempt in range(3):
        try:
            data = urllib.request.urlopen(url, timeout=90).read()
            if len(data) >= min_bytes:
                open(path, "wb").write(data); return len(data)
        except Exception as e:
            err = e
    raise SystemExit(f"download failed: {url} ({err if 'err' in dir() else 'too small'})")
n = 0
for g in GROUPS: n += get(SV + g + ".json", f"raw/{g}.json", 50)
n += get("https://raw.githubusercontent.com/2048lr/celestrak-mirror/main/satcat/satcat.csv", "raw/satcat.csv", 1_000_000)
n += get("https://raw.githubusercontent.com/clarkzjw/starlink-geoip-data/master/map/pop.json", "raw/starlink_pop.json", 1000)
if not os.path.exists("raw/satnogs_stations.json"):
    import shutil; shutil.copy("satnogs_stations.json", "raw/satnogs_stations.json")
print(f"downloaded {n/1e6:.1f} MB")
env = dict(os.environ, OUT="out/orbital.json")
for step in ("build_dataset.py", "build_payload.py"):
    r = subprocess.run([sys.executable, step], env=env, capture_output=True, text=True)
    print(r.stdout[-1500:]); 
    if r.returncode: print(r.stderr[-3000:]); raise SystemExit(f"{step} failed")
d = json.load(open("out/orbital.json"))
ns, ng = len(d["sats"]["id"]), len(d["stations"]["name"])
assert ns > 10000 and ng > 4000, (ns, ng)   # sanity: never publish a gutted payload
print(json.dumps({"ok": True, "sats": ns, "stations": ng, "elements_as_of": d["elements_as_of"],
                  "built": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")}))
