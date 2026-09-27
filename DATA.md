# Orbital Network Atlas — data provenance, method and gaps

Built 2026-09-27. Companion to the Subsea Cable Atlas: same panel, filters, similarity map and
build-out timeline, with a live 3D globe as the primary view.

- `index.html` — the app shell; loads `data/orbital.json` and `data/borders.json` at startup.
- `assets/` — Earth textures (NASA Blue Marble / Black Marble derivatives, via the `three-globe`
  npm package examples) and a local `three.min.js` fallback (r160) used if the CDN is unreachable.
- `scripts/` — the full rebuild pipeline (see "Rebuilding").

Run locally: `python -m http.server 8000` in this folder, then open http://localhost:8000
(browsers block `fetch` on `file://`).

## Sources

| Layer | Source | Licence / terms | Vintage |
|---|---|---|---|
| 13,873 satellites — orbital elements (OMM) | CelesTrak GP groups via GitHub mirror `satvisorcom/satvisor-data` | CelesTrak public data | epochs up to 2026-09-27 00:06Z |
| Launch date, owner, ops status | CelesTrak SATCAT via GitHub mirror `2048lr/celestrak-mirror` | CelesTrak public data | refreshed 2026-09-27 04:46Z |
| 4,495 SatNOGS stations | SatNOGS Network API (`network.satnogs.org/api/stations`), saved by you | ODbL | 2026-09-27 |
| 198 Starlink gateways | starlinkinsider.com gateway list (compiled from FCC filings) | third-party compilation | 2025 page |
| 65 Starlink PoPs + 14 community gateways | `clarkzjw/starlink-geoip-data` `map/pop.json` (U. Victoria) | repo terms | current |
| 116 professional sites | Curated by hand: NASA DSN/SN/NEN, ESA ESTRACK, KSAT, SSC, AWS Ground Station, OneWeb SNPs, SES O3b, Iridium, Globalstar, major GEO teleports, China/ISRO/JAXA networks | — | see caveats |
| 29 FCC-filed sites (exact coordinates, antennas, bands) | FCC ICFS Form 312 Schedule B, read via the ICFS portal | US government public record | filings 2026-01-05 to 2026-09-01, read 2026-09-27 |
| Geocoding | GeoNames cities1000 (bundled in the `reverse_geocoder` PyPI package) | CC-BY 4.0 | — |
| Country borders | `johan/world.geo.json` | public domain | — |

**Constellations included:** Starlink (11,037), OneWeb (651), SatNOGS-tracked smallsats (606),
other GEO (421), Kuiper (391), Qianfan (238), Guowang (199), Iridium NEXT (80), Intelsat (55),
SES GEO (42), Globalstar (36), O3b/mPOWER (31), Eutelsat (29), other comms LEO (19), Telesat (16),
Orbcomm (14), TDRS (8). A satellite in several CelesTrak groups is assigned once, in that order.

## Propagation

Positions are computed in the browser every frame with a Kepler solver plus J2 secular drift of
node and perigee. To stay close to full SGP4 without running SGP4 for 14k objects per frame,
every LEO/MEO element set (12,864 of 13,873) was **re-epoched at build time**: SGP4 was run at
T0 = 2026-09-27 07:00Z and T0 + 24 h, and the mean anomaly and its rate were corrected so the
argument of latitude matches SGP4 at both instants. That folds drag and mean-motion recovery
into one linear term. Deep-space objects (period > 225 min, i.e. GEO/HEO) keep their published
mean elements with analytic J2 rates.

Checked against python-sgp4 on a 144-satellite sample at T0 + 3 h: **median 9.8 km, p90 25 km**.
The worst 1% (~12,000 km) are satellites still orbit-raising from recent launches, whose
along-track motion is not linear. Error grows the further the clock is from T0: roughly
50–120 km at T0 + 3 days for low Starlink shells. Rebuild to refresh.

Altitude above 2,000 km is drawn log-compressed so the GEO belt (35,786 km) sits at ~1.8 Earth
radii; tick "True-scale altitude" for real proportions.

## FCC filings (added 2026-09-27)

`data/fcc/fcc_filings_2026-07-31_to_09-18.csv` is the ICFS filing list you supplied, parsed and
tagged (500 filings). The 29 most relevant were opened in the ICFS portal and their Form 312
Schedule B read directly (`scripts/fcc_sites.json`): exact NAD-83 coordinates, site elevation,
antenna count and size, and every licensed band.

| Operator | Filings | What they are | Antennas per site |
|---|---|---|---|
| SpaceX | 20 new gateway licences (`SES-LIC`, filed 30 Jul–18 Aug 2026) | Starlink gateways, 19 pending, 1 closed | 40 × 1.999 m |
| Amazon Kuiper | 3 new gateway licences | Port St. Lucie FL, Twin Valley MN, Seminole TX | 6 × 2.4 m |
| Northwood Space | 5 modifications | Talkeetna AK, Bismarck ND, Loring ME, Brewster WA, Santa Paula CA | 12 × 2.4 m |
| RBC Signals | 1 modification | Winston-Salem NC (UHF) | 2 × 3.14 m |

SpaceX gateways file 11 bands: Ka (17.3–20.2 GHz down, 27.5–30 GHz up), Q/V (37.5–42 down,
47.2–52.4 up), E-band (71–76 down, 81–86 up) and W-band (92–114.25 GHz up).

Merging rules: a filing snaps an existing 2025-list gateway to the filed coordinates only when it
is the **same town** and that gateway was **not already live** (Elkton MD, Roberts WI). A new
licence in a town that already has a live gateway (Elbert CO, Lockport NY) is added as a second
site, because an `SES-LIC` is a new earth station. Everything else is added as a new site: 25 in
all. Pending licences show as **Planned** and draw no links. Northwood and RBC filings modify
licensed, operating stations, so those show as Online. The inspector shows the file number,
call sign and antennas, and links to the ICFS record. The "Only sites with FCC filings" filter
isolates them.

The 27 rows added after the similarity layout was computed are placed at the mean of their six
nearest neighbours in feature space; cluster labels are unchanged.

## Special temporary authorities (added 2026-09-27)

All 280 earth-station STAs (`SES-STA`) in the filing list were read from ICFS. An STA lets an
operator run a station before (or outside) its full licence, so it is the best public signal
of what is actually switched on right now.

| Outcome | Filings |
|---|---|
| Site taken from the STA's own Schedule B (exact coordinates) | 98 |
| Site taken from the filing description or the earlier STA it extends (town-level, geocoded) | 94 |
| Mobile, aircraft, ESIM, terminal or test-antenna STAs (no fixed site, skipped) | 17 |
| No location published anywhere in the chain (listed in `scripts/fcc_sta_sites.json`) | 71 |

These collapse to **161 distinct sites**: 78 Starlink gateways, 49 Viasat SANs (the ViaSat-3
ground network, 2.4 m Ka-band), 8 Intelsat teleports and 26 others (KSAT, SSC/USN, ATLAS, RBC
Signals, Parsons, AST SpaceMobile, Globalstar, Iridium and more). 48 merged into sites already
on the map, 16 of those snapping from town-level to exact coordinates; 113 are new.

What it changed:
- **Every SpaceX gateway application from the licence set also holds a 60-day STA**, so those
  sites now show as **Online (operating under temporary authority)**, not Planned.
- Two 2025-list gateways placed at town centres (Lockport NY, Elbert CO) turned out to be the
  same sites as filed gateways and were folded into them.
- GEO teleports now link only to their own operator's satellites (Viasat SANs to ViaSat and
  Inmarsat, Intelsat sites to Intelsat and Galaxy, and so on), and military GEO satellites are
  never drawn as teleport links. Ellenwood GA, for example, now links to Intelsat 40e, which is
  what its STA covers.

Caveats: Viasat's STA Schedule Bs are PDFs, so their SAN sites are town-level. One USN antenna
(USAK05) was filed at 64.30°N, 55 km from its sister antennas, and is treated as a typo.
Two new filters isolate these sites: "Only sites with FCC filings" and "Only sites under
temporary authority".

## Daily refresh, heatmap, trails, click-through (added 2026-09-27)

**Automated refresh.** A scheduled task runs every day at 04:48 Pacific. It reads the pipeline
published inside the artifact (`pipeline/`: scripts plus every input — FCC sites, SatNOGS
stations, the similarity layout and labels), re-downloads CelesTrak elements and SATCAT and the
Starlink PoP list from their GitHub mirrors, re-fits every orbit with SGP4 to the current hour,
and republishes only `data/orbital.json`. It refuses to publish if a download fails or the result
has fewer than 10,000 satellites or 4,000 stations. Newly launched satellites are placed on the
similarity map by nearest neighbours; labels stay fixed. The subtitle shows when orbits were last
refreshed. The refresh runs in the cloud, so this local folder copy does not update by itself;
`pipeline/refresh.py` runs here too (`pip install numpy sgp4`, then `python refresh.py`).

**Coverage heatmap** (toggle, or `h`). For every shown satellite, the ground circle where it is
above 25° elevation is added to a 2° grid, so each cell counts how many satellites a user there
could see right now. Filters apply, so Starlink-only shows Starlink coverage. Colour is a single
amber ramp stretched between the 5th and 99th percentile of covered cells; hovering the globe
reads the exact count. Military GEO satellites are excluded.

**Motion trails** (toggle, or `t`): three fading segments per satellite covering its last minute
of flight (GEO objects barely move and are skipped). **Ground track**: selecting a satellite
draws its sub-satellite path one orbit back (amber) and one forward (blue), capped at ±3 h, plus
its 25° visibility footprint.

**Click-through.** Clicking a satellite, on the globe or the similarity map, opens its CelesTrak
SATCAT record in a new tab and selects it. Ground sites open their FCC licence (else latest STA,
else their source page). Shift-click selects without opening. In the published artifact, some
viewers' browsers block tabs opened by script; the inspector's links always work.

## Globe readability

Country borders were brightened and their opacity now rises as you zoom out (0.38 → 0.7), and
land on the night side is lifted slightly above the ocean using the water mask, so continents
stay readable at full-globe distance.

## Link model (what the beams mean)

The beams are a **geometric visibility model, not observed traffic.** For each online ground site
and each system it serves, the app finds satellites above the site's elevation mask right now and
draws the highest ones:

| Site type | Mask | Links drawn |
|---|---|---|
| Starlink gateway / community gateway | 25° | up to 4 |
| Constellation gateway (OneWeb, O3b, Iridium, Globalstar) | 10° | up to 4 |
| GEO teleport | 10° | up to 2 |
| TT&C / deep-space | 10° | up to 2 |
| SatNOGS station | its own `min_horizon` (clamped 5–40°) | 1 |

Planned and offline sites draw no links. Starlink PoPs are terrestrial IP interconnects and draw
none. "Serves" for curated sites is an informed assignment (e.g. KSAT/SSC → OneWeb, Iridium,
O3b, Kuiper, other LEO); operators do not publish which satellites each antenna tracks.

The **Starlink laser mesh** is modelled too: each Starlink satellite above 400 km joins its two
nearest neighbours in the same shell (±1.2° inclination, ±25 km altitude) within 1,100 km.
Real optical-link topology is not public.

## Similarity map

Built with the datamap pipeline (UMAP + HDBSCAN, 3 label layers: 12 / 24 / 49 clusters, all
hand-labelled). Embeddings are **structured features, not text**: satellites by constellation,
orbit class, log altitude, inclination, eccentricity and launch year; ground sites by site type,
position on the globe and commissioning year. The displayed layout is a second, more spread UMAP
over the same features (min_dist 0.55); cluster membership and labels come from the first run
and label positions are each cluster's medoid in the displayed layout.

It reads the way you would expect: Starlink dominates by count and splits by shell and launch
year; the ground segment splits by region and site type.

## Known gaps

1. **Curated sites are town-level, several are "publicly reported" rather than confirmed**:
   OneWeb SNPs, O3b gateways, Globalstar gateways (a subset of ~25) and AWS Ground Station
   (published only by region). The `Location basis` field in the inspector says site / town /
   region for each.
2. **Starlink gateway list is from a 2025 compilation.** 81 of 198 towns were not in GeoNames
   cities1000 and were placed by hand at town level (`town (approx.)`). "Anchorage, Arkansas" in
   the source was treated as Anchorage, Alaska. Status labels (live / pending / construction) are
   the compiler's, not SpaceX's.
3. **No Kuiper or Chinese mega-constellation gateway list is public**; those constellations link
   only to multi-mission networks (KSAT, SSC, AWS, China ground segment) in this model.
4. **SatNOGS stations are mostly offline** (4,149 of 4,495). They are kept because they carry the
   network's growth history; filter by status to hide them.
5. **Undated ground sites** (393 commercial/government sites) have no commissioning year and
   stay visible through the timeline unless "Include undated" is unticked.
6. Earth-observation and science satellites are out of scope except the 606 SatNOGS-tracked
   smallsats, so TT&C networks show fewer links than they really carry.

## Verification

- Filter logic: the shipped predicate, run in Chromium against the payload, matches independent
  Python counts in 5 scenarios (all, Starlink only, ≤2020, no undated, GEO only).
- Propagation: see numbers above.
- Rendering: checked in headless Chromium (SwiftShader WebGL) at 1440×860 and 420×860.

## Rebuilding

```
python scripts/build_dataset.py        # master table + features (needs raw/ inputs)
python datamap_pipeline.py build ...   # layout + clusters (datamap skill)
python scripts/relayout.py             # spread display layout
python scripts/build_payload.py        # re-epoch with SGP4 and write data/orbital.json
```
Dependencies: `pip install sgp4 umap-learn hdbscan scikit-learn numpy pandas`.
