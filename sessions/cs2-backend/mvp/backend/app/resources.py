"""Nearest-place and hotline lookup for the Retell `lookup_info` function.

Resources are real, verified places/hotlines in agents/resources/resources.yaml (RESOURCES_FILE).
Supervisor-approved answers (kb_items) win over resource matching. Geocoding: Census geocoder for
street addresses, OpenStreetMap Nominatim for landmarks/neighborhoods (cached, polite UA), with a
hard time budget so the agent's 5 s function timeout is never hit. Never claims a shelter is open.
"""
import json, math, os, re, time, urllib.parse, urllib.request
from pathlib import Path

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


def _get_json(url, deadline):
    timeout = max(0.3, deadline - time.monotonic())
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def geocode(text, deadline):
    """(lat, lon) for an address, landmark or neighborhood in LA County, or None."""
    text = (text or '').strip()
    if not text:
        return None
    if text in _geo_cache:
        return _geo_cache[text]
    q = text if re.search(r'\b(ca|california)\b', text, re.I) else f'{text}, Los Angeles County, CA'
    attempts = []
    if re.match(r'^\s*\d+\s+\w', text):  # looks like a street address
        attempts.append(('census', q))
    attempts.append(('osm', q))
    city = re.split(r'\b(?:and|&|y|at)\b|,', text)[-1].strip()  # "Lake and Woodbury, Altadena" -> "Altadena"
    if city and city.lower() != text.lower():
        attempts.append(('osm', f'{city}, Los Angeles County, CA'))
    result = None
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
                    {'q': query, 'format': 'json', 'limit': 1, 'countrycodes': 'us'}), deadline)
                if d:
                    result = (float(d[0]['lat']), float(d[0]['lon']))
        except Exception:
            continue
        if result:
            break
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
        parts.append('If this is an emergency, call 911 instead of driving.')
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
