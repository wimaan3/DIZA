# Session context: la-3d

- **Session:** Codex with Zoe; Los Angeles community map.
- **Branch:** Map implementation merged from `3d-map`; deployment follow-up on `codex/deploy-city-3d`.
- **Scope:** User requested pulling main and making the map 3D, then clarified city-scale LA (Downtown / USC first, also west LA, with some care facilities), rather than a single senior residence.

## Files in this folder
| File | Contents |
| --- | --- |
| `src/main.jsx`, `src/styles.css` | Responsive city-map interface, region controls, accessible directory and selected-location panel |
| `src/CityMap.jsx` | MapLibre buildings, operator overlays, selected point, 2D/3D and offline outline |
| `src/data.js` | Verified facility directory, explicit synthetic events, coordinate and zone validation |
| `src/useOps.js` | Read-only existing `/api/ops` polling, auth, stale-data and timeout handling |
| `server.py` | Additive FastAPI mount at `/city-3d/`; original app mounted at `/` |
| `Dockerfile` | Optional combined build; does not change the active Railway configuration |
| `tests/` | Data-contract, wrapper/auth and browser interaction checks |
| `package.json`, `package-lock.json`, `vite.config.js`, `index.html`, `.gitignore` | Pinned dependencies, Vite setup and entry page |
| `README.md` | Run, review, deployment, limitations and source references |

## Decisions made
- Pulled `origin/main` (base `cfc6e82`) before implementation; work isolated under this session as required by AGENTS.md.
- MapLibre GL JS + OpenFreeMap extrusions reuse existing city data. No manual city reconstruction, Three.js models or paid map key needed for the first version.
- Downtown, USC / West Adams, Westwood and Santa Monica presets; LA overview supports wider context.
- Separate public facility markers from operational incidents. Demo incidents are visibly synthetic and not attributed to real facilities.
- Keep the existing backend API and its token guard. This client is read-only; it neither initiates Retell work nor sends SMS.
- Invalid coordinates are listed as unlocated; unknown severity remains unknown. Preserve coordinate conversion from backend `[lat, lon]` zone points to GeoJSON `[lon, lat]`.
- Same-origin token is memory-only. Authentication failures clear previous incident data; transient failures show a stale snapshot notice.
- Keep the implementation in our own session and provide an additive server instead of editing another team's dashboard. Code PR requires CS#2 review before merge.

## Key facts verified (with sources)
- Existing implementation has `/api/ops` with incident coordinates, effective severity and zones: `sessions/cs2-backend/mvp/backend/app/ops.py`. Original `/api/` bearer guard and lifespan are in `backend/app/main.py`.
- OpenFreeMap Liberty includes a `building-3d` extrusion layer on the `building` vector source layer using `render_height` / `render_min_height`. Confirmed by fetching its current style and rendering Downtown in Chrome. [Style](https://tiles.openfreemap.org/styles/liberty), [MapLibre example](https://maplibre.org/maplibre-gl-js/docs/examples/display-buildings-in-3d/), [OpenFreeMap quick start](https://openfreemap.org/quick_start/).
- Four public facility addresses verified on official operator sites; Census geocoder returned street-segment positions. Sources and returned coordinates are retained in `src/data.js` and linked in README.
- No LLM is used in this city-map client. User map interactions do not consume LLM tokens.

## Validation
- Production Vite build passed; MapLibre bundle produces a size advisory (approximately 285 KB gzip for the map main chunk, separate worker).
- Four Node data-contract tests passed.
- FastAPI wrapper/auth integration test passed with a temporary database and no Retell API key.
- Chrome browser smoke passed: rendered public 3D buildings, region switching, facility details, layers, offline outline, API authentication and stale snapshots, unlocated events, and mobile layout. No JavaScript runtime errors. Screenshots were visually inspected.

## Open questions
- Which care facilities should be in the team's final demo story and eventual verified directory?
- Whether CS#2 prefers the additive wrapper or integrating this map as a dashboard tab after review.

## Not done
- Map PR #38 is merged. Deployment follow-up changes the root Railway Dockerfile selection with the user's explicit authorization; configuration review and remote deployment verification remain pending.
- No photorealistic 3D city mesh, indoor layouts, resident/occupancy data, accessibility routing or facility capacity verification.
- No emergency-service transfer changes and no SMS work in this scope.
- Docker image build is not verified; both frontend code and the wrapper are tested locally.

## Deployment follow-up
- User explicitly approved changing `railway.json` to use `sessions/la-3d/Dockerfile` and redeploying. This authorizes the specific root configuration edit outside the session directory.
- Based on latest main `568a701`, preserving the team's subsequent demo changes.
- Only the Dockerfile selection changes: existing `/ops` health check, restart policy, `$PORT` startup, `/data/diza.sqlite3` database location and original backend remain in place.
- The previous deployment returned the original Operations HTML at `/city-3d/`; HTTP 200 alone is insufficient to verify activation.
- Config PR requires DS review per AGENTS.md. No direct main push or self-merge.

## Operations Live map integration
- **Branch:** `codex/ops-map-3d`.
- The user clarified that the 3D renderer must replace the existing Operations Live map shown in their screenshot, not be a separate primary experience. This explicitly authorizes the necessary edits in the existing dashboard folder.
- Replaced `dashboard/src/LiveMap.jsx` with MapLibre while keeping the existing props and mutation callbacks. Ops and Wall view now use 3D directly; no iframe, separate event store or second token login.
- Preserved severity markers, selected/flagged/GPS styling, linked-report rings, public places, unlocated list, draggable coordinates, zone drawing/saving/removal and offline outline. New incoming reports no longer force a world-scale fit; operators can choose All reports explicitly or jump to LA presets.
- Extracted presets, verified facility directory and building styling into `dashboard/src/city-map-data.js`, shared with the standalone explorer. Added `ops-map-3d.css`; added MapLibre and removed unused Leaflet dependency from the existing dashboard; split the map library into its own build chunk.
- Added Chinese/Spanish labels for new controls. Facility positions remain approximate address matches, not indoor or surveyed entrance data.
- `tests/ops_map_browser.py` tests the integrated `/ops` UI against an isolated local backend and temporary SQLite database, with Retell disabled. It checks selection, persisted dragging, pending placement, zone creation/deletion, 2D/3D, offline, facility layer, region navigation, mobile layout and Wall view.
- Both dashboard builds and shared-data tests pass. Integrated browser checks passed with no JavaScript errors; desktop and mobile screenshots inspected. Full Docker build remains unverified (daemon unavailable).
- CS#2 review and a subsequent deployment are required before this replacement appears online.
