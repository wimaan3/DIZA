"""Nearest-place and hotline lookup for the Retell `lookup_info` function.

Resources are real, verified places/hotlines in agents/resources/resources.yaml (RESOURCES_FILE).
Supervisor-approved answers (kb_items) win over resource matching. Geocoding: Census geocoder for
street addresses, OpenStreetMap Nominatim for landmarks/neighborhoods (cached, polite UA), with a
hard time budget so the agent's 5 s function timeout is never hit. Never claims a shelter is open.
"""
import json, math, os, re, threading, time, urllib.parse, urllib.request
from pathlib import Path
from .regions import code as country_code, region

GEOCODE_BUDGET_S = 3.0
UA = 'DIZA-hackathon-line/0.1 (USC student project; demo use)'
_geo_cache = {}
_res_cache = {'path': None, 'mtime': None, 'items': []}

STOP = set('a an the is are where what who how can i my me to for of in on at near nearest closest there any do does get find need help please'.split())
TYPE_WORDS = [
    ('shelter_site', ('shelter', 'evacuation center', 'place to stay', 'sleep tonight', 'stay tonight', 'albergue', 'refugio')),
    ('library_cooling_charging', ('cool', 'cooling', 'heat', 'hot', 'air conditioning', 'charge', 'charging', 'enfriamiento')),
    ('food', ('food', 'hungry', 'pantry', 'eat', 'meal', 'meals', 'groceries', 'comida')),
    ('hospital_er', ('emergency room', 'er', 'hospital')),
    ('health_center', ('doctor', 'clinic', 'health center', 'student health', 'nurse')),
    ('animal_shelter', ('pet', 'pets', 'dog', 'dogs', 'cat', 'cats', 'animal', 'animals', 'mascota')),
    ('public_safety', ('police', 'campus safety', 'dps', 'escort', 'security')),
    ('recovery_center', ('recovery', 'rebuild', 'fema', 'lost my home', 'lost my house', 'house burned', 'home burned', 'fire survivor', 'tenant', 'eaton fire')),
    ('relief_org', ('red cross',)),
]


def resources():
    path = Path(os.getenv('RESOURCES_FILE', str(Path(__file__).resolve().parents[5] / 'agents' / 'resources' / 'resources.yaml')))
    if not path.exists():
        return []
    mtime = path.stat().st_mtime
    if _res_cache['path'] != path or _res_cache['mtime'] != mtime:
        import yaml
        _res_cache.update(path=path, mtime=mtime, items=yaml.safe_load(path.read_text()).get('resources', []))
    return _res_cache['items']


def tokens(text):
    return {t for t in re.findall(r"[a-z0-9']+", (text or '').lower()) if t not in STOP}


def approved_answer(conn, question):
    q = tokens(question)
    best = None
    for row in conn.execute('SELECT * FROM kb_items').fetchall():
        k = tokens(row['question'])
        score = len(q & k) / max(len(k), 1)
        if score >= 0.6 and (best is None or score > best[0]):
            best = (score, row)
    return best[1] if best else None


_osm_lock = threading.Lock()
_osm_last = [0.0]


def _get_json(url, deadline):
    if 'nominatim' in url:  # OpenStreetMap's usage policy: at most one request per second, shared across threads
        with _osm_lock:
            time.sleep(max(0.0, 1.05 - (time.monotonic() - _osm_last[0])))
            _osm_last[0] = time.monotonic()
    timeout = max(0.3, deadline - time.monotonic())
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


STREET = re.compile(r"\b(st|street|ave|avenue|blvd|boulevard|dr|drive|rd|road|ln|lane|way|ct|court|pl|place|hwy|highway|fwy|freeway|pkwy|parkway|"
                    r"ter|terrace|cir|circle|calle|avenida)\b\.?|\d", re.I)
STATES = set("""al ak az ar ca co ct de fl ga hi id il in ia ks ky la me md ma mi mn ms mo mt ne nv nh nj nm ny nc nd oh ok or pa ri sc sd tn tx ut vt va wa wv wi wy
alabama alaska arizona arkansas california colorado connecticut delaware florida georgia hawaii idaho illinois indiana iowa kansas kentucky louisiana maine
maryland massachusetts michigan minnesota mississippi missouri montana nebraska nevada ohio oklahoma oregon pennsylvania tennessee texas utah vermont
virginia washington wisconsin wyoming usa us""".split()) | {'new york', 'new jersey', 'new mexico', 'new hampshire', 'north carolina', 'south carolina',
                                                        'north dakota', 'south dakota', 'rhode island', 'west virginia'}


def place_list(text):
    """Several separate places in one location answer ("Kansas City, Wichita, and Tulsa") -> each place, else [].
    Never splits an intersection or address ("Lake Ave and Altadena Dr", "123 Main St") or "City, State"."""
    parts = [p.strip(' .') for p in re.split(r'\s*(?:;|,|&|\band\b|\by\b|\bplus\b)\s*', text or '', flags=re.I) if p.strip(' .')]
    merged = []
    for p in parts:
        if merged and p.lower() in STATES:
            merged[-1] = f'{merged[-1]}, {p}'  # "Wichita, Kansas" stays one place
        else:
            merged.append(p)
    if len(merged) < 2 or any(STREET.search(p) for p in merged):
        return []
    return merged[:6]


GENERIC = set('unit apt apartment suite ste room floor fl building bldg house home near by the at in on of and a an my our st ave rd dr blvd '
              'church school park store shop market station hospital corner street road freeway highway mall bank restaurant hotel '
              'old new big little here there outside inside'.split())


def said_in(text, hit):
    """The match must contain a word the caller said. We add the service area to every query, so "unit 4C" otherwise
    matches a "County of Los Angeles" plant and lands a pin downtown; better no pin than a wrong one."""
    words = [w for w in re.findall(r'\w+', text.lower()) if w not in GENERIC and len(w) >= 2]
    place = ((hit.get('display_name') or '') + ' ' + (hit.get('name') or '')).lower()
    return bool(words) and any(w in place for w in words)


CROSS = re.compile(r'^\s*(?:near|at|on|by)?\s*(.+?)\s+(?:and|&|at|y|/)\s+(.+?)\s*(?:,\s*(.+?))?\s*$', re.I)


def _street_lines(street, place, deadline, box=None):
    """OSM segments of one street in a city or county (or inside a box), as lists of (lat, lon) points."""
    q = {'street': street, 'format': 'json', 'limit': 50, 'dedupe': 0, 'polygon_geojson': 1, 'countrycodes': country_code().lower()}
    if box:  # (south, west, north, east): only the part near the other street; plain text also finds "East Colorado Boulevard"
        q.pop('street'); q.update(q=street, viewbox=f'{box[1]},{box[2]},{box[3]},{box[0]}', bounded=1)
    else:
        q['county' if 'county' in place.lower() else 'city'] = place.split(',')[0].strip()
    lines = []
    for hit in _get_json('https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode(q), deadline) or []:
        g = hit.get('geojson') or {}
        parts = [g['coordinates']] if g.get('type') == 'LineString' else g.get('coordinates', []) if g.get('type') == 'MultiLineString' else []
        lines += [[(p[1], p[0]) for p in part] for part in parts]
    return lines


def _crossing(a_lines, b_lines):
    """Where two streets meet: a segment-segment intersection, else their closest points if under ~80 m."""
    best = None
    for la in a_lines:
        for lb in b_lines:
            for (p1, p2) in zip(la, la[1:]):
                for (q1, q2) in zip(lb, lb[1:]):
                    d = (p2[0] - p1[0]) * (q2[1] - q1[1]) - (p2[1] - p1[1]) * (q2[0] - q1[0])
                    if d:
                        t = ((q1[0] - p1[0]) * (q2[1] - q1[1]) - (q1[1] - p1[1]) * (q2[0] - q1[0])) / d
                        u = ((q1[0] - p1[0]) * (p2[1] - p1[1]) - (q1[1] - p1[1]) * (p2[0] - p1[0])) / d
                        if 0 <= t <= 1 and 0 <= u <= 1:
                            return (round(p1[0] + t * (p2[0] - p1[0]), 6), round(p1[1] + t * (p2[1] - p1[1]), 6))
            for p in la:
                for q in lb:
                    gap = math.hypot(p[0] - q[0], (p[1] - q[1]) * math.cos(math.radians(p[0]))) * 111_000
                    if gap < 80 and (best is None or gap < best[0]):
                        best = (gap, (round((p[0] + q[0]) / 2, 6), round((p[1] + q[1]) / 2, 6)))
    return best[1] if best else None


def _inside(point, place, deadline):
    """The corner must be in the city the caller named: "Los Angeles" street searches also return Downey's Western/6th."""
    d = _get_json('https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode(
        {'q': f"{place}, {region()['area']}", 'format': 'json', 'limit': 1, 'countrycodes': country_code().lower()}), deadline)
    if not d or 'boundingbox' not in d[0]:
        return False
    south, north, west, east = map(float, d[0]['boundingbox'])
    return south <= point[0] <= north and west <= point[1] <= east


def intersection(text, deadline):
    """'11th St and Broadway, Santa Monica' -> where those two streets cross. OSM search alone can't find corners:
    it returns a point somewhere on one of the streets (a live call landed blocks away near Lincoln Blvd)."""
    m = CROSS.match(text or '')
    # Only with a city or neighborhood: LA County has many "Western Ave and 6th St" corners (one is in Downey), so
    # guessing one would be a confident wrong pin. Without it, the street-level answer below stays.
    if not m or not m.group(3) or not (STREET.search(m.group(1)) or STREET.search(m.group(2))):
        return None
    place = m.group(3)
    try:
        a, b = _street_lines(m.group(1), place, deadline), _street_lines(m.group(2), place, deadline)
        hit = _crossing(a, b)
        if hit or not a or not b:
            return hit if hit and _inside(hit, place, deadline) else None
        # A city search can miss the right piece: long streets hit the 50-result cap, and "Colorado Blvd" misses
        # "East Colorado Boulevard". Look for each street again, by plain text, only around the other one.
        def box(lines):
            pts = [p for line in lines for p in line]
            return (min(p[0] for p in pts) - .003, min(p[1] for p in pts) - .003, max(p[0] for p in pts) + .003, max(p[1] for p in pts) + .003)
        for near, name, other in sorted(((a, m.group(2), b), (b, m.group(1), a)), key=lambda x: len(x[0])):
            if time.monotonic() > deadline:
                break
            hit = _crossing(near, _street_lines(name, place, deadline, box(near)) + other)
            if hit and _inside(hit, place, deadline):
                return hit
        return None
    except Exception:
        return None


def geocode(text, deadline):
    """(lat, lon) for an address, landmark or neighborhood (LA County first, then anywhere), or None."""
    # Callers say "near Venice Beach" or "by the USC Village": geocode the place, not the preposition.
    text = re.sub(r'^\s*(?:near|around|by|close to|next to|at|in|on)\s+(?:the\s+)?', '', (text or '').strip(), flags=re.I)
    if not text:
        return None
    if text in _geo_cache:
        return _geo_cache[text]
    corner = intersection(text, deadline)
    m = CROSS.match(text)
    if corner or (m and STREET.search(m.group(1)) and STREET.search(m.group(2))):
        # Two cross streets: the verified corner or no pin at all. A street-level guess lands blocks or cities away
        # (City Hall for "Western and 6th, Los Angeles"); the operator places it from the unlocated list instead.
        _geo_cache[text] = corner
        return corner
    area = region()['area']
    named = area.split(',')[0].lower() in text.lower() or (country_code() == 'US' and re.search(r'\b(ca|california)\b', text, re.I))
    q = text if named else f'{text}, {area}'
    attempts = []
    if re.match(r'^\s*\d+\s+\w', text) and country_code() == 'US':  # a US street address (the Census geocoder is US-only)
        attempts.append(('census', q))
    attempts.append(('osm', q))
    city = re.split(r'\b(?:and|&|y|at)\b|,', text)[-1].strip()  # "Lake and Woodbury, Altadena" -> "Altadena"
    if city and city.lower() != text.lower():
        attempts.append(('osm', f'{city}, {area}'))
    # Not in LA County ("Tulsa", "Wichita", "Madrid"): search everywhere, after the local tries so LA landmarks win.
    attempts.append(('osm_any', text))
    result, road = None, False
    for kind, query in attempts:
        if time.monotonic() > deadline:
            break
        try:
            if kind == 'census':
                d = _get_json('https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?' + urllib.parse.urlencode(
                    {'address': query, 'benchmark': 'Public_AR_Current', 'format': 'json'}), deadline)
                m = d['result']['addressMatches']
                if m:
                    result = (m[0]['coordinates']['y'], m[0]['coordinates']['x'])
            else:
                d = _get_json('https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode(
                    {'q': query, 'format': 'json', 'limit': 1, **({'countrycodes': country_code().lower()} if kind == 'osm' else {})}), deadline)
                if d and said_in(text, d[0]):
                    result = (float(d[0]['lat']), float(d[0]['lon']))
                    # A street called "Tulsa", or a building whose name only contains "Bakersfield": not the town the caller named.
                    hit_name = (d[0].get('name') or '').strip().lower()
                    road = d[0].get('class') == 'highway' or (d[0].get('class') not in ('place', 'boundary') and hit_name != text.strip().lower())
        except Exception:
            continue
        if result:
            break
    # The caller named a town ("Tulsa", "Bakersfield") and the local search found a street or a building instead: a town with exactly that name, anywhere, wins.
    if result and kind == 'osm' and road and not STREET.search(text) and time.monotonic() < deadline:
        try:
            d = _get_json('https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'q': text, 'format': 'json', 'limit': 1}), deadline)
            if d and d[0].get('class') in ('place', 'boundary') and (d[0].get('name') or '').strip().lower() == text.strip().lower():
                result = (float(d[0]['lat']), float(d[0]['lon']))
        except Exception:
            pass
    _geo_cache[text] = result
    return result


def miles(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def wanted_types(question, needs):
    q = (question or '').lower()
    types = {t for t, words in TYPE_WORDS if any(re.search(rf'\b{re.escape(w)}\b', q) for w in words)}
    needs = {n.lower() for n in needs or []}
    if 'pets' in needs and not types:
        types.add('animal_shelter')
    if {'large_animals', 'horse', 'horses', 'livestock'} & needs or re.search(r'horse|livestock', q):
        types.add('shelter_site')
    if 'oxygen_power' in needs and not types:
        types.add('library_cooling_charging')
    return types


def match_hotline(question):
    """Best hotline whose topic words appear (by stem) in the question; at least half of a topic must match."""
    words = tokens(question)
    best = None
    for r in resources():
        if r.get('type') != 'hotline':
            continue
        for topic in r.get('topics', []):
            parts = [w for w in tokens(topic) if len(w) > 2]
            hits = sum(1 for p in parts if any(w.startswith(p[:5]) for w in words))
            score = hits / max(len(parts), 1)
            if hits and score >= 0.5 and (best is None or score > best[0]):
                best = (score, r)
    return best[1] if best else None


def describe(r, dist=None):
    parts = []
    if r.get('type') == 'hospital_er':
        parts.append(f"If this is an emergency, call {region()['emergency_spoken']} instead of driving.")
    where = ', '.join(x for x in (r.get('address'), r.get('city')) if x)
    parts.append(f"{r['name']}" + (f", {where}" if where else '') + (f", about {dist:.1f} miles away" if dist is not None else '') + '.')
    if r.get('phone'):
        parts.append(f"Phone: {r['phone']}.")
    if r.get('hours'):
        parts.append(f"Hours: {r['hours'].split(';')[0]}.")
    if r.get('eligibility'):
        parts.append(f"For {r['eligibility']} only.")
    if r.get('status_note'):
        parts.append(r['status_note'])
    elif r.get('notes'):
        parts.append(r['notes'])
    return ' '.join(parts)


def lookup(conn, question, location_text='', needs=(), drill_mode=True):
    """Return the lookup_info response dict (00_CONTRACTS shape + resource_name / transfer_number)."""
    empty = {'answer': '', 'source': '', 'confidence': 0, 'resource_name': '', 'transfer_number': ''}
    item = approved_answer(conn, question)
    if item:
        return {**empty, 'answer': item['answer'], 'source': item['source'] or 'approved by supervisor', 'confidence': 0.9}

    def out(r, answer, confidence):
        allowed = r.get('transfer_ok') and r.get('transfer_number') and not drill_mode
        src = (r.get('source_urls') or [''])[0]
        return {'answer': answer, 'source': src, 'confidence': confidence, 'resource_name': r['name'],
                'transfer_number': r['transfer_number'] if allowed else ''}

    types = wanted_types(question, needs)
    if not types:
        hotline = match_hotline(question)
        return out(hotline, describe(hotline), 0.8) if hotline else None
    needs = {n.lower() for n in needs or []}
    large = bool({'large_animals', 'horse', 'horses', 'livestock'} & needs) or re.search(r'horse|livestock', question or '', re.I)
    wants_pets = 'pets' in needs or 'animal_shelter' in types
    order = [t for t, _ in TYPE_WORDS]
    pool = [r for r in resources() if r.get('type') in types
            and (not r.get('only_for') or (large and 'large_animals' in r['only_for']))]
    if not pool:
        return None
    here = geocode(location_text, time.monotonic() + GEOCODE_BUDGET_S)

    def rank(r):
        # 1) meets the pet need, 2) the kind of place asked for first, 3) distance (unknown coords last,
        #    except a site in the caller's own city), 4) file order.
        pet_miss = wants_pets and r.get('pets_allowed') is not True and r.get('type') != 'animal_shelter'
        if large and r.get('only_for'):
            pet_miss = False
        same_city = bool(location_text) and r.get('city', '').lower() in location_text.lower()
        dist = miles(here, (r['lat'], r['lon'])) if here and r.get('lat') is not None else None
        return (pet_miss, order.index(r['type']) if r['type'] in order else 99,
                0 if dist is not None or same_city else 1, 0 if same_city and dist is None else 1, dist or 0)

    best = min(pool, key=rank)
    dist = miles(here, (best['lat'], best['lon'])) if here and best.get('lat') is not None else None
    hint = '' if location_text else ' Tell me your cross streets for the closest option.'
    return out(best, describe(best, dist) + hint, 0.8 if dist is not None else 0.6)
