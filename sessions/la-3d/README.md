# DIZA · Los Angeles 3D

A city-scale view for community operations. Downtown, USC / West Adams, Westwood and Santa Monica presets sit over a pannable MapLibre map. OpenFreeMap supplies building footprints and mapped or estimated heights; this is not a photorealistic mesh or an indoor floor plan.

The initial explorer is available at `/city-3d/`. The Operations integration follow-up replaces the existing dashboard Live map at `/ops` and in Wall view, as explicitly requested by the user. It uses the same event state, selection and mutation callbacks; no separate login or iframe is introduced.

## What works

- Rotate/tilt/zoom the city, switch 3D / 2D, or zoom out to LA overview.
- Four public care locations with source links and approximate address positions.
- Three explicitly fictional events in Demo mode; never automatically substituted for backend data.
- Backend mode reads the existing same-origin `GET /api/ops` every five seconds, with incidents and read-only operator zones. Coordinates remain subject to backend/source accuracy. Events with no valid coordinates stay in the list without a fabricated pin.
- Memory-only operator token. A 401/403 clears the previous snapshot; network/server failures retain the previous snapshot with a visible stale-data notice. Only `/api/ops` receives the token.
- Layer toggles, search, location detail cards, keyboard controls, reduced-motion support and responsive layout.
- User-selectable offline outline reuses the repository's bundled Census geometry. No tile network is required after selecting it, but it has no 3D buildings. If WebGL is unavailable, the directory remains usable.

## Run locally

Node 22+ and Python with the existing backend requirements are sufficient. From the repo root:

```sh
cd sessions/la-3d
npm ci
npm run dev
```

Open <http://127.0.0.1:18783/city-3d/>. Demo mode needs no credentials. For backend events, run the existing backend on `127.0.0.1:8000`; Vite forwards `/api` there. The optional operator token is the backend's `OPS_API_TOKEN`, not a Retell key. The operations-dashboard link expects the combined server below; Vite alone only serves this map.

## Serve alongside the existing app

Build both dashboards, then run the additive server (from repo root):

```sh
npm --prefix sessions/cs2-backend/mvp/dashboard ci
npm --prefix sessions/cs2-backend/mvp/dashboard run build
npm --prefix sessions/la-3d ci
npm --prefix sessions/la-3d run build
python -m pip install -r sessions/cs2-backend/mvp/backend/requirements.txt
uvicorn server:app --app-dir sessions/la-3d --host 127.0.0.1 --port 8000
```

The new map is at `/city-3d/`; the original dashboard, API guard and Retell routes remain served by the existing app. The wrapper forwards startup/shutdown to the original app. Set `DIZA_DB` and other environment variables as for the existing backend. Running with a real Retell key enables the original backend's existing background work; this map does not initiate calls or messages.

An optional combined `Dockerfile` is included; build with repo-root context:

```sh
docker build -f sessions/la-3d/Dockerfile -t diza-city-3d .
```

The deployment follow-up sets the repository's `railway.json` Dockerfile path to `sessions/la-3d/Dockerfile`. After review and merge, Railway can build both dashboards using this image. Preserve the current environment and persistent `/data` volume. Confirm `/ops` and `/city-3d/` separately after deployment: the original SPA fallback can return HTTP 200 for an unimplemented map route. The image has not been built in this session; both frontend builds and the combined server were tested locally.

## Validation

```sh
npm --prefix sessions/la-3d test
npm --prefix sessions/la-3d run build
python -m pytest sessions/la-3d/tests/test_server.py -q
# With the Vite server running, and Playwright installed:
PLAYWRIGHT_CHANNEL=chrome python sessions/la-3d/tests/browser_smoke.py
```

The server test uses temporary SQLite storage and disables Retell synchronization. The browser test uses mocked backend responses, real public map tiles, and writes ignored screenshots to `.artifacts/`. It checks 3D loading, regional navigation, facility details, layers, offline mode, unauthorized responses, stale snapshots, missing coordinates and a 390px mobile viewport. `PLAYWRIGHT_CHANNEL` may be omitted when Playwright Chromium is installed.

## Data and attribution

Verified 2026-10-17. This is a curated demonstration directory, not an exhaustive list, an endorsement, or a list of emergency shelters. Facility availability and services must be checked with each operator.

| Facility | Public address | Address/service source |
| --- | --- | --- |
| Sakura Gardens of Los Angeles | 325 S Boyle Ave, Los Angeles, CA 90033 | [Official contact](https://sakuragardenslosangeles.com/contact-us/), [assisted living](https://sakuragardenslosangeles.com/living-options/assisted-living/) |
| St. John of God Retirement and Care Center | 2468 S St Andrews Pl, Los Angeles, CA 90018 | [Official campus site](https://stjog.org/) |
| Belmont Village Westwood | 10475 Wilshire Blvd, Los Angeles, CA 90024 | [Official location](https://www.belmontvillage.com/locations/westwood-los-angeles-california/) |
| Ivy Park at Santa Monica | 1312 15th St, Santa Monica, CA 90404 | [Official location](https://ivyliving.com/santamonica/), [assisted living](https://ivyliving.com/santamonica/assisted-living/) |

Coordinates are US Census `Public_AR_Current` address matches (street-segment interpolation), not surveyed entrances. Exact returned coordinates, source URLs and geocoder query URLs are retained in `src/data.js`. St. Andrews matched `SAINT ANDREWS` in the Census response. Ivy Park is the current name on the official facility site; older Sunrise search results were not used.

Map attribution is kept visible: OpenFreeMap / OpenMapTiles / OpenStreetMap. See [OpenFreeMap quick start](https://openfreemap.org/quick_start/) and [MapLibre 3D-building example](https://maplibre.org/maplibre-gl-js/docs/examples/display-buildings-in-3d/). No paid map API key is needed for this configured public tile source. Availability, coverage and provider terms remain external dependencies. The offline outline comes from `sessions/cs2-backend/mvp/dashboard/src/offline-la.json`; its provenance says Census TIGERweb. Its embedded fetch date is not independently verified here.

## Scope and follow-up

No automated police/911 routing, resident records, facility occupancy, hazard detection, SMS, indoor layouts, photogrammetry, or operational dispatch is added. The city layer does not use an LLM, so panning or rotating it consumes no model tokens. Network tile delivery and the existing app's services have their own costs.

The Operations replacement is in `sessions/cs2-backend/mvp/dashboard/src/LiveMap.jsx`. Both views share presets, facility sources and building styling from `city-map-data.js` in that dashboard. The Operations view preserves dragging report pins, placing unlocated reports and drawing/deleting zones through the original API callbacks. It defaults to a local 3D view; All reports explicitly frames distant reports. CS#2 review is required before merging the integration. A future facilities import can replace the four curated markers; real facility footprints and entrances should be verified before site-level use.
