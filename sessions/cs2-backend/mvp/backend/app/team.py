"""Who on the team gets a call: skills, languages, the area they cover, their hours and their backup.

One DIZA_RESPONDERS entry (every field but id, name and phone is optional; old entries keep working):
  {"id":"min","name":"Min","phone":"+13105550103",
   "skills":["medical","security"], "languages":["ko","en"],
   "areas":["Koreatown","Mid-City"], "home":[34.06,-118.30], "radius_km":8,
   "hours":"Mon-Fri 08:00-20:00; Sat 10:00-16:00", "backup":"sam", "note":"EMT"}

Rules, every reason spoken or shown: only people on duty with a phone; volunteers never get P0/P1; language +3,
each needed skill +2, covers the caller's area +2. A transfer that didn't connect goes to that person's backup.
"""
import json, math, re, time
from datetime import datetime
from zoneinfo import ZoneInfo
from .regions import region

# The agents ask for "evac_logistics", the dashboard offers to "logistics": the same people.
SYNONYMS = {'evac_logistics': 'logistics', 'logistics': 'evac_logistics', 'emt': 'medical', 'nurse': 'medical', 'medic': 'medical',
            'counselor': 'mental_health', 'police': 'security', 'guard': 'security'}
LANG_NAME = {'en': 'English', 'es': 'Spanish', 'ko': 'Korean', 'zh': 'Chinese', 'vi': 'Vietnamese', 'ru': 'Russian', 'hy': 'Armenian',
             'fa': 'Persian', 'tl': 'Tagalog', 'ja': 'Japanese', 'fr': 'French', 'ar': 'Arabic'}
DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']


def _list(v):
    return [x.strip() for x in (v.split(',') if isinstance(v, str) else v or []) if str(x).strip()]


def normalize(r):
    """A DIZA_RESPONDERS entry -> (skills string, profile dict). Languages become lang: tags; synonyms are added."""
    tags = [s.lower() for s in _list(r.get('skills', 'general'))] + [s.lower() for s in _list(r.get('roles'))]
    tags += [f"lang:{l.lower().removeprefix('lang:')}" for l in _list(r.get('languages'))]
    tags += [SYNONYMS[t] for t in tags if t in SYNONYMS]
    skills = ','.join(dict.fromkeys(tags)) or 'general'
    home = r.get('home') if isinstance(r.get('home'), list) and len(r['home']) == 2 else None
    return skills, {'areas': _list(r.get('areas')), 'home': home, 'radius_km': float(r.get('radius_km') or 10) if home else None,
                    'hours': str(r.get('hours') or '').strip(), 'backup': str(r.get('backup') or '').strip(), 'note': str(r.get('note') or '')[:200]}


def init_team(c, team):
    c.execute('CREATE TABLE IF NOT EXISTS responder_profiles(responder_id TEXT PRIMARY KEY,profile TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS routing_tries(call_id TEXT,responder_id TEXT,outcome TEXT,ts REAL)')
    ids = {r['id'] for r in team}
    for r in team:
        _, profile = normalize(r)
        if profile['backup'] and profile['backup'] not in ids:
            print(f"DIZA_RESPONDERS: {r['id']}'s backup '{profile['backup']}' is not on the team; ignored", flush=True)
            profile['backup'] = ''
        if profile['hours'] and parse_hours(profile['hours']) is None:
            print(f"DIZA_RESPONDERS: {r['id']}'s hours '{profile['hours']}' not understood (use e.g. 'Mon-Fri 08:00-20:00'); treated as always on", flush=True)
            profile['hours'] = ''
        c.execute('INSERT OR REPLACE INTO responder_profiles VALUES(?,?)', (r['id'], json.dumps(profile)))


def profiles(c):
    try:
        return {r['responder_id']: json.loads(r['profile']) for r in c.execute('SELECT * FROM responder_profiles')}
    except Exception:
        return {}


# --- Hours ----------------------------------------------------------------------------------------------------
def parse_hours(text):
    """'Mon-Fri 08:00-20:00; Sat 10:00-16:00' or '18:00-06:00' -> [(days, start_min, end_min)], or None if unreadable."""
    out = []
    for part in [p.strip() for p in re.split(r'[;\n]', text or '') if p.strip()]:
        m = re.fullmatch(r'(?:([A-Za-z]{3})(?:\s*-\s*([A-Za-z]{3}))?\s+)?(\d{1,2}):?(\d{2})\s*-\s*(\d{1,2}):?(\d{2})', part)
        if not m:
            return None
        d1, d2, h1, m1, h2, m2 = m.groups()
        if d1 and d1.lower() not in DAYS or d2 and d2.lower() not in DAYS:
            return None
        if d1:
            a, b = DAYS.index(d1.lower()), DAYS.index((d2 or d1).lower())
            days = {(a + k) % 7 for k in range((b - a) % 7 + 1)}
        else:
            days = set(range(7))
        out.append((days, int(h1) * 60 + int(m1), int(h2) * 60 + int(m2)))
    return out


def on_duty(hours, now=None):
    """True when no hours are set, or now falls in a shift (overnight shifts count from their start day)."""
    spans = parse_hours(hours) if hours else None
    if not spans:
        return True
    t = datetime.fromtimestamp(now or time.time(), ZoneInfo(region()['tz']))
    day, minute = t.weekday(), t.hour * 60 + t.minute
    for days, start, end in spans:
        if start <= end and day in days and start <= minute < end:
            return True
        if start > end and ((day in days and minute >= start) or ((day - 1) % 7 in days and minute < end)):
            return True
    return False


# --- Area -----------------------------------------------------------------------------------------------------
def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    return 6371 * 2 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))


def area_match(profile, location_text, point):
    """'covers Altadena' or '2 km away' when this person covers where the caller is, else ''."""
    text = (location_text or '').lower()
    for a in profile.get('areas') or []:
        if a and re.search(rf'\b{re.escape(a.lower())}\b', text):
            return f'covers {a}'
    if point and profile.get('home'):
        d = km(point, profile['home'])
        if d <= (profile.get('radius_km') or 10):
            return f'{d:.0f} km away' if d >= 1 else 'nearby'
    return ''


def caller_place(c, call_id):
    """Where this call's caller is: the latest report filed on the call (location text and pin)."""
    r = c.execute('SELECT location,lat,lon FROM reports WHERE substr(dedupe,1,?)=? ORDER BY created DESC LIMIT 1',
                  (len(call_id) + 1, call_id + ':')).fetchone() if call_id else None
    if not r or (r['location'] or '').startswith('('):
        return '', None
    return r['location'], ((r['lat'], r['lon']) if r['lat'] is not None else None)


# --- Picking --------------------------------------------------------------------------------------------------
def pick(c, wanted, severity='P2', location_text='', point=None, exclude=(), prefer='', now=None):
    """Best available, on-duty person with a phone for these needs. Returns (row, reason) or (None, why_not)."""
    profs = profiles(c)
    rows = c.execute("SELECT r.id,r.name,r.skills,p.phone FROM responders r JOIN responder_phones p ON p.responder_id=r.id "
                     "WHERE r.status='available' ORDER BY r.id").fetchall()
    best, off = None, 0
    for r in rows:
        if r['id'] in exclude:
            continue
        skills = set((r['skills'] or '').lower().split(','))
        if severity in ('P0', 'P1') and 'volunteer' in skills:
            continue  # never send urgent calls to unverified/general volunteers
        prof = profs.get(r['id'], {})
        if not on_duty(prof.get('hours'), now):
            off += 1
            continue
        langs = sorted(w for w in wanted & skills if w.startswith('lang:'))
        needs = sorted(w for w in wanted & skills if not w.startswith('lang:'))
        where = area_match(prof, location_text, point)
        score = 3 * len(langs) + 2 * len(needs) + (2 if where else 0) + (100 if prefer and r['id'] == prefer else 0)
        why = [f"speaks {LANG_NAME.get(l[5:], l[5:])}" for l in langs] + [n.replace('_', ' ') for n in needs] + ([where] if where else [])
        if best is None or score > best[0]:
            best = (score, r, why)
    if not best:
        return None, f'{off} teammate{"s" if off != 1 else ""} off duty' if off else 'nobody available'
    score, r, why = best
    if prefer and r['id'] == prefer:
        why = ['backup'] + why
    return r, ', '.join(why) or 'first available'
