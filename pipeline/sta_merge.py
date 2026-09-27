"""Turn raw ICFS STA pulls into deduplicated ground sites (scripts/fcc_sta_sites.json)."""
import json, re, collections, csv
raw = json.load(open("sta_raw.json"))["rows"]
chase = {}
DESCS = {d["f"]: d["descs"] for d in json.load(open("sta_descs.json"))}
from geo_us import geocode
status = {r["file_number"]: r["status"] for r in csv.DictReader(open("fcc_filings_2026-07-31_to_09-18.csv"))}

def band(lo, hi):
    f = (lo + hi) / 2 / 1000  # GHz
    for name, a, b in [("UHF", 0, 1), ("L", 1, 2), ("S", 2, 4), ("C", 4, 8), ("X", 8, 12), ("Ku", 12, 17.1),
                       ("Ka", 17.1, 31.5), ("Q/V", 31.5, 60), ("E", 60, 90), ("W", 90, 120)]:
        if a <= f < b: return name
    return "?"
def bands(s):
    out = []
    for tok in s.split():
        m = re.match(r"([\d.]+)-([\d.]+)([TR])", tok)
        if m:
            lo, hi = float(m[1]), float(m[2])
            if lo > 200000: lo, hi = lo / 1000, hi / 1000   # kHz entries
            out.append(band(lo, hi))
    order = ["UHF", "L", "S", "C", "X", "Ku", "Ka", "Q/V", "E", "W"]
    return " · ".join(b for b in order if b in out)

NET = {  # applicant -> (network, kind, serves)
 "SpaceX Services, Inc.": ("SpaceX Starlink", "Starlink gateway", ["starlink"]),
 "Viasat, Inc.": ("Viasat", "GEO teleport", ["geo"]), "ISAT US Inc.": ("Viasat/Inmarsat", "GEO teleport", ["geo"]),
 "Intelsat License LLC": ("Intelsat", "GEO teleport", ["geo"]), "SES Networks Lux, S.a.r.l.": ("SES O3b", "Constellation gateway", ["o3b"]),
 "DIRECTV Enterprises, LLC": ("DIRECTV", "GEO teleport", ["geo"]), "Calian Pacific Teleports Ltd.": ("Calian", "GEO teleport", ["geo"]),
 "Globalstar Licensee LLC": ("Globalstar", "Constellation gateway", ["globalstar"]),
 "Iridium Satellite LLC": ("Iridium", "Constellation gateway", ["iridium"]), "Iridium Constellation LLC": ("Iridium", "Constellation gateway", ["iridium"]),
 "AST & Science, LLC": ("AST SpaceMobile", "Constellation gateway", ["other_leo"]), "Kuiper Systems LLC": ("Amazon Kuiper", "Constellation gateway", ["kuiper"]),
}
GSaaS = ["other_leo", "smallsat"]
def net_of(app):
    if app in NET: return NET[app]
    return (app.replace(", LLC", "").replace(" LLC", "").replace(", Inc.", "").replace(" Inc.", ""), "TT&C / downlink network", GSaaS)
MOBILE = re.compile(r"ESIM|ESAA|aboard aircraft|terminal|blanket|CONUS|temporary-fixed|Ragno|Starway|Lesa Blade|HiSky|Intellian|Ball 9x9|NB-IoT|MES STA|800 MHz Testing", re.I)

sites = {}
skipped = collections.Counter(); nos = []
for r in raw:
    ss = r["sites"] or chase.get(r["f"], {}).get("sites", [])
    via = r["ref"] or chase.get(r["f"], {}).get("via", "")
    if MOBILE.search(r["desc"]): skipped["mobile / terminal / test"] += 1; continue
    precision = "site (FCC Schedule B)"
    if not ss:
        txt = " ## ".join([r["desc"]] + [d.split(" :: ", 1)[-1] for d in DESCS.get(r["f"], [])])
        hit = None
        for m in re.finditer(r"([A-Z][A-Za-z.'-]+(?: [A-Z][A-Za-z.'-]+){0,2}),? ([A-Z]{2})\b", txt):
            town, st = m[1], m[2]
            town = re.sub(r"^(?:for|use|to|in|Extension|STA|Ext) ", "", town).strip()
            g = geocode(town, st)
            if g: hit = (town, st, g); break
        if not hit:
            for kw, st2 in [("Deadhorse", "AK"), ("Utqiagvik", "AK"), ("Maui", "HI"), ("Las Cruces", "NM"), ("Tempe", "AZ"),
                            ("Chandler", "AZ"), ("Fairbanks", "AK"), ("Wasilla", "AK"), ("Clifton", "TX"), ("Haleiwa", "HI"),
                            ("Tafuna", "AS"), ("Winston", "NC"), ("Santa Paula", "CA"), ("Lanham", "MD"), ("Homestead", "FL"), ("Eagle Mountain", "UT")]:
                if kw.lower() in txt.lower():
                    g = geocode("Winston-Salem" if kw == "Winston" else kw, st2)
                    if g: hit = (kw if kw != "Winston" else "Winston-Salem", st2, g); break
        if not hit: nos.append(r); continue
        town, st, g = hit
        ss = [[f"{town}, {st}", town, f"{town}, {st}", g[0], g[1], 0, "", ""]]
        m = re.search(r"([\d.]+) ?m\b", txt); 
        if m: ss[0][6] = m[1]; ss[0][5] = 1
        if "Ka band" in txt or "SAN" in txt: ss[0][7] = "27500-30000T 17700-20200R"
        precision = "town (from FCC filing description)"
    net, kind, serves = net_of(r["app"])
    for s in ss:
        n, city, area, lat, lon, q, diam, b = s
        if abs(lat) < 1e-6 and abs(lon) < 1e-6: continue
        if n == "USAK05": continue   # filed latitude 64.30 is 55 km south of USAK01/04; treated as a filing typo
        key = (round(lat, 3), round(lon, 3))
        if r["app"] == "Viasat, Inc." and "SAN" in (r["desc"] + " ".join(DESCS.get(r["f"], []))):
            net, kind = "Viasat SAN (ViaSat-3 gateways)", "GEO teleport"
        nm = str(n).replace('The "', '"').strip()
        if not nm or nm.isdigit() or nm.upper() == nm and len(nm) <= 3 and kind == "Starlink gateway":
            nm = f"{(city or area).strip().title()} Gateway"
        e = sites.setdefault(key, dict(name=nm, area=area or city, lat=lat, lon=lon, applicant=r["app"],
             network=net, kind=kind, serves=serves, antennas=(f"{q} × {diam} m" if diam else (f"{q} antennas" if q else "")), bands=bands(b), precision=precision,
             filings=[], parents=[]))
        e["filings"].append(dict(f=r["f"], desc=r["desc"][:140], status=status.get(r["f"], "")))
        if via and via not in e["parents"]: e["parents"].append(via)
out = sorted(sites.values(), key=lambda e: (e["network"], e["area"]))
json.dump(dict(_source="FCC ICFS: SES-STA filings listed 2026-07-31..09-18; sites from each STA's Schedule B or, when it has none, from the licence/STA it extends. Read 2026-09-27.",
               sites=out, no_location=[dict(f=r["f"], applicant=r["app"], desc=r["desc"][:140]) for r in nos],
               skipped=dict(skipped)), open("fcc_sta_sites.json", "w"), indent=1)
print("sites", len(out), collections.Counter(e["network"] for e in out).most_common())
print("no location", len(nos), "skipped", dict(skipped))
