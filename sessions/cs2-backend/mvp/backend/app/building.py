"""Building mode: tenants call about problems, the AI files tickets, the manager ranks, assigns and closes them.

The AI only gathers. Plain rules here set urgency, merge duplicates and cross-reference related tickets, and the
reason for each is stored as text the dashboard shows. Nothing is ever auto-closed or hidden; a person decides.
Phones (after-hours line, staff, vendors) come from the environment only, never from git.
"""
import json, os, random, re, statistics, time
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .main import DEMO, app, connect, event
from .retell_fns import e164, last4, once, parse, responders_from_env

router = APIRouter()
TZ = ZoneInfo('America/Los_Angeles')
CATEGORIES = ('water_leak', 'no_heat', 'no_hot_water', 'electrical', 'gas_smell', 'lockout', 'pest', 'appliance', 'noise', 'security', 'other')
URGENCIES = ('emergency', 'urgent', 'routine')
STATUSES = ('new', 'assigned', 'in_progress', 'waiting_tenant', 'closed')
MERGE_WINDOW = 2 * 3600
XREF_WINDOW = 7 * 86400
# Age targets the dashboard turns red past (seconds).
TARGETS = {'emergency': 3600, 'urgent': 86400, 'routine': 7 * 86400}
# Civ. Code §1941.1 habitability items (stove/fridge added for 2026 leases); locks, noise and security are not on the list.
HABITABILITY = {'water_leak', 'no_heat', 'no_hot_water', 'electrical', 'gas_smell', 'pest', 'appliance'}
ETA_TEXT = "The manager will review it; you'll get updates by text."


# --- Rules (pure functions, unit-tested) ---

DANGER = re.compile(r"\b(gas|smell(s|ing)? (of )?gas|fire|flames?|smoke|smoking|burning|sparks?|sparking|someone (is )?hurt|injured|bleeding|"
                    r"unconscious|can'?t breathe|carbon monoxide|co alarm|fuego|humo|incendio|olor a gas|quemando)\b", re.I)
DANGER_CJK = ('불이', '불났', '화재', '연기', '가스', '火', '烟', '煤气', '着火', '燃气')  # no word boundaries in Korean/Chinese: substrings
NOT_DANGER = re.compile(r"\bsmoke (detector|alarm) (is )?(chirp|beep)\w*|\b(chirp|beep)\w* smoke (detector|alarm)", re.I)
ACTIVE_WATER = re.compile(r"\b(leak(s|ing)?|pour(s|ing)?|gush(es|ing)?|flood(s|ed|ing)?|spray(s|ing)?|burst|running|coming (in|through|down)|"
                          r"dripping (from|through)|water everywhere|goteando|inund\w*|fuga|saliendo)\b", re.I)
ACTIVE_WATER_CJK = ('누수', '물이 새', '물이 넘', '漏水', '在漏', '淹水')
# Only a clear sign the water has stopped or is minor lowers a leak below emergency.
INACTIVE_WATER = re.compile(r"\b(stopped|stain(ed|s)?|dried|old leak|used to|last (week|month)|faucet drips?|drippy faucet|slow drip)\b", re.I)


def danger_word(text):
    """The first fire/gas/injury word in the caller's words, or ''. A chirping smoke-detector battery is not danger."""
    t = NOT_DANGER.sub(' ', text or '')
    m = DANGER.search(t)
    return m.group(0) if m else next((w for w in DANGER_CJK if w in t), '')


ELECTRICAL_HAZARD = re.compile(r"\b(exposed wires?|outlet (is )?(hot|melting)|shock(ed)?|buzzing|breaker|no power|power out|outage)\b", re.I)


def cold_weather(now):
    # Heating season Oct 1 - Apr 30 (LA nights drop into the 40s-50s); DIZA_COLD_WEATHER=true|false overrides.
    env = os.getenv('DIZA_COLD_WEATHER', '').lower()
    if env in ('true', 'false'):
        return env == 'true'
    return datetime.fromtimestamp(now, TZ).month in (10, 11, 12, 1, 2, 3, 4)


def night(now):
    h = datetime.fromtimestamp(now, TZ).hour
    return h >= 20 or h < 7


def urgency(category, text='', now=None, hint=''):
    """(urgency, reason). Deterministic; an agent's hint can only raise it, never lower it."""
    now = now or time.time()
    text = text or ''
    word = danger_word(text)
    if category == 'gas_smell' or word:
        found = 'gas smell' if category == 'gas_smell' else f'caller said "{word}"'
        level, reason = 'emergency', f'Possible fire, gas or injury ({found}): tell the caller to call 911 first'
    elif category == 'water_leak' and (ACTIVE_WATER.search(text) or any(w in text for w in ACTIVE_WATER_CJK) or not INACTIVE_WATER.search(text)):
        level, reason = 'emergency', 'Water actively leaking (treated as active unless the caller says it stopped)'
    elif category == 'no_heat' and cold_weather(now):
        level, reason = 'urgent', 'No heat during heating season'
    elif category == 'no_hot_water':
        level, reason = 'urgent', 'No hot water'
    elif category == 'lockout' and night(now):
        level, reason = 'urgent', 'Locked out at night (8 PM - 7 AM)'
    elif category == 'electrical':
        level, reason = 'urgent', 'Electrical problem' + (f' ("{ELECTRICAL_HAZARD.search(text).group(0)}")' if ELECTRICAL_HAZARD.search(text) else '')
    else:
        level, reason = 'routine', 'Routine request'
    hint = (hint or '').lower()
    if hint in URGENCIES and URGENCIES.index(hint) < URGENCIES.index(level):
        level, reason = hint, f'{reason}; raised to {hint} by the phone agent'
    return level, reason


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


NOUN = {'water_leak': 'leak', 'no_heat': 'no-heat', 'no_hot_water': 'no-hot-water', 'electrical': 'electrical', 'gas_smell': 'gas-smell',
        'lockout': 'lockout', 'pest': 'pest', 'appliance': 'appliance', 'noise': 'noise', 'security': 'security', 'other': 'similar'}
CAUSE = {('water_leak', 'stack'): 'likely the same pipe', ('water_leak', 'unit'): 'likely the same fixture or pipe',
         ('water_leak', 'floor'): 'check for a shared pipe on this floor', ('no_heat', 'hvac_zone'): 'likely the same heating system',
         ('no_hot_water', 'hvac_zone'): 'likely the same water heater or boiler', ('no_hot_water', 'stack'): 'likely the same riser',
         ('electrical', 'floor'): 'possibly the same circuit or panel', ('electrical', 'stack'): 'possibly the same riser or panel',
         ('pest', 'stack'): 'likely spreading through shared walls', ('pest', 'floor'): 'likely spreading on this floor'}


# Which shared building element best explains a repeat problem: water follows the riser (stack), heat the HVAC zone,
# electrical the floor's panel. The same unit always comes first.
ORDER = {'electrical': ('floor', 'stack', 'hvac_zone'), 'no_heat': ('hvac_zone', 'stack', 'floor'),
         'pest': ('stack', 'floor', 'hvac_zone')}
DEFAULT_ORDER = ('stack', 'hvac_zone', 'floor')


def relation(a, b, category=''):
    """The strongest shared building element between two units (dicts with unit/stack/floor/hvac_zone), or None."""
    if a['unit'] == b['unit']:
        return 'unit'
    for key in ORDER.get(category, DEFAULT_ORDER):
        if a.get(key) not in (None, '') and a.get(key) == b.get(key):
            return key
    return None


def xref_reason(category, rel, unit, units):
    """Human-readable cross-reference text, e.g. '3rd leak report on stack B this week (4B, 5B, 6B): likely the same pipe'."""
    names = sorted(set(units), key=lambda u: (len(u), u))
    where = {'unit': f"in {unit['unit']}", 'stack': f"on stack {unit.get('stack')}", 'hvac_zone': f"in HVAC zone {unit.get('hvac_zone')}",
             'floor': f"on floor {unit.get('floor')}"}[rel]
    cause = CAUSE.get((category, rel), 'check for a shared cause')
    return f"{ordinal(len(units))} {NOUN.get(category, 'similar')} report {where} this week ({', '.join(names)}): {cause}"


def ca_clock(ticket, now=None):
    """Days since first notice for habitability problems, with Civ. Code §1942 (30 d) / §1942.4 (35 d) markers. Not legal advice."""
    if ticket['category'] not in HABITABILITY:
        return None
    end = ticket.get('closed_at') or now or time.time()
    days = int((end - ticket['created']) // 86400)
    if days >= 35:
        level, text = 'past_35', f'{days} days since first notice: past 35 days (Civ. Code §1942.4 if an inspector cited it)'
    elif days >= 30:
        level, text = 'past_30', f'{days} days since first notice: past the 30-day mark (Civ. Code §1942)'
    elif days >= 21:
        level, text = 'soon', f'{days} days since first notice: {30 - days} days to the 30-day mark (Civ. Code §1942)'
    else:
        level, text = 'ok', f'{days} day{"s" if days != 1 else ""} since first notice'
    return {'days': days, 'level': level, 'text': text + ('' if level == 'ok' else ' · a warning, not legal advice'), 'closed': bool(ticket.get('closed_at'))}


WORD_NUM = {'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10'}


def norm_unit(text):
    """'Unit 4-b', 'apt #4B', 'four B' -> '4B'."""
    t = (text or '').lower()
    t = re.sub(r'\b(' + '|'.join(WORD_NUM) + r')\b', lambda m: WORD_NUM[m.group(1)], t)
    t = re.sub(r'\b(unit|apartment|apt|suite|ste|room|rm|number|no)\b\.?', ' ', t)
    t = re.sub(r'[^a-z0-9]', '', t)
    return t.upper()


# --- Storage ---

def init_building():
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS buildings(id TEXT PRIMARY KEY,name TEXT,address TEXT,lat REAL,lon REAL,manager_name TEXT,after_hours_phone TEXT,line_number TEXT);
        CREATE TABLE IF NOT EXISTS units(building_id TEXT,unit TEXT,floor INTEGER,stack TEXT,hvac_zone TEXT,tenant_language TEXT,PRIMARY KEY(building_id,unit));
        CREATE TABLE IF NOT EXISTS staff_vendors(id TEXT PRIMARY KEY,building_id TEXT,name TEXT,role TEXT,phone TEXT,skills TEXT);
        CREATE TABLE IF NOT EXISTS tickets(code TEXT PRIMARY KEY,building_id TEXT,unit TEXT,unit_verified INTEGER,category TEXT,urgency TEXT,urgency_reason TEXT,
          summary TEXT,caller_quote TEXT,language TEXT,access_ok INTEGER,reporters TEXT,status TEXT,assignee TEXT,created REAL,updated REAL,
          first_human_action_at REAL,closed_at REAL,related TEXT,merged_into TEXT,tenant_notified_at REAL,source TEXT);
        CREATE TABLE IF NOT EXISTS ticket_events(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT,ts REAL,kind TEXT,actor TEXT,message TEXT);
        CREATE INDEX IF NOT EXISTS tickets_open ON tickets(building_id,category,created);
        ''')
        seed_building(c)
        # Phones only from the environment: DIZA_STAFF='{"maint":"+1...","security":"+1..."}', DIZA_BUILDING_AFTER_HOURS, DIZA_BUILDING_LINE.
        for sid, phone in json.loads(os.getenv('DIZA_STAFF', '{}') or '{}').items():
            c.execute('UPDATE staff_vendors SET phone=? WHERE id=?', (e164(phone), sid))
        if os.getenv('DIZA_BUILDING_AFTER_HOURS'):
            c.execute('UPDATE buildings SET after_hours_phone=? WHERE id=?', (e164(os.environ['DIZA_BUILDING_AFTER_HOURS']), DEMO_BUILDING))
        line = os.getenv('DIZA_BUILDING_LINE') or os.getenv('RETELL_FROM_NUMBER', '')
        if line:
            c.execute('UPDATE buildings SET line_number=? WHERE id=?', (e164(line), DEMO_BUILDING))


DEMO_BUILDING = 'bldg-demo'
# Fictional names; 555-01xx style numbers are never stored, phones stay blank until the environment fills them.
STAFF = [('mgr', 'Dana Okafor', 'manager', 'all'), ('maint', 'Luis Romero', 'maintenance', 'general,appliance,pest,lockout'),
         ('plumb', 'Westside Plumbing (demo vendor)', 'plumber', 'water_leak,no_hot_water'),
         ('elec', 'Brightline Electric (demo vendor)', 'electrician', 'electrical'), ('lock', 'QuickKey Locksmith (demo vendor)', 'locksmith', 'lockout'),
         ('hvac', 'CoolAir HVAC (demo vendor)', 'maintenance', 'no_heat,no_hot_water'), ('security', 'Night desk security (demo)', 'security', 'security,noise')]
LANGS = {'2A': 'es', '3C': 'ko', '1E': 'zh', '4D': 'es', '2F': 'vi', '3A': 'es'}


def seed_building(c):
    # One demo LA apartment building: 4 floors x stacks A-F = 24 units. Stacks share risers; HVAC zones split east/west.
    c.execute('INSERT OR IGNORE INTO buildings(id,name,address,lat,lon,manager_name) VALUES(?,?,?,?,?,?)',
              (DEMO_BUILDING, 'Larchmont Court Apartments (demo)', 'Koreatown, Los Angeles, CA (fictional demo building)', 34.0635, -118.3005, 'Dana Okafor'))
    if not c.execute('SELECT 1 FROM units WHERE building_id=?', (DEMO_BUILDING,)).fetchone():
        for floor in range(1, 5):
            for stack in 'ABCDEF':
                unit = f'{floor}{stack}'
                c.execute('INSERT INTO units VALUES(?,?,?,?,?,?)', (DEMO_BUILDING, unit, floor, stack, 'West' if stack in 'ABC' else 'East', LANGS.get(unit)))
    for sid, name, role, skills in STAFF:
        c.execute('INSERT OR IGNORE INTO staff_vendors(id,building_id,name,role,phone,skills) VALUES(?,?,?,?,?,?)', (sid, DEMO_BUILDING, name, role, '', skills))


def tlog(c, code, kind, message, actor='system', ts=None):
    c.execute('INSERT INTO ticket_events(code,ts,kind,actor,message) VALUES(?,?,?,?,?)', (code, ts or time.time(), kind, actor, message))


def building_for(c, call=None, hint=''):
    """The building from the number the tenant called, else a name hint, else the only/first building."""
    to = re.sub(r'\D', '', (call or {}).get('to_number') or '')[-10:]
    rows = c.execute('SELECT * FROM buildings').fetchall()
    for b in rows:
        if to and re.sub(r'\D', '', b['line_number'] or '')[-10:] == to:
            return b
    words = set(re.findall(r'[a-z]+', (hint or '').lower())) - {'the', 'apartments', 'building', 'court'}
    for b in rows:
        if words & set(re.findall(r'[a-z]+', b['name'].lower())):
            return b
    return rows[0] if rows else None


def find_unit(c, building_id, unit_text):
    u = norm_unit(unit_text)
    return c.execute('SELECT * FROM units WHERE building_id=? AND unit=?', (building_id, u)).fetchone() if u else None


def new_code(c):
    for _ in range(50):
        code = f'T-{random.randint(1000, 9999)}'
        if not c.execute('SELECT 1 FROM tickets WHERE code=?', (code,)).fetchone():
            return code
    raise HTTPException(500, 'Could not allocate a ticket code')


def category_of(text):
    t = (text or '').lower().strip().replace(' ', '_').replace('-', '_')
    if t in CATEGORIES:
        return t
    for cat, words in (('gas_smell', ('gas',)), ('no_hot_water', ('hot_water', 'hot water')), ('water_leak', ('leak', 'water', 'flood', 'drip')),
                       ('no_heat', ('heat', 'heater', 'cold')), ('electrical', ('electric', 'power', 'outlet', 'light')), ('lockout', ('lock', 'key')),
                       ('pest', ('pest', 'roach', 'mice', 'mouse', 'rat', 'bug', 'bed bug')), ('appliance', ('fridge', 'stove', 'oven', 'washer', 'dryer', 'dishwasher', 'appliance')),
                       ('noise', ('noise', 'loud', 'music', 'party')), ('security', ('security', 'break', 'stranger', 'door', 'theft', 'stolen'))):
        if any(w in t for w in words):
            return cat
    return 'other'


def file_ticket(c, building, unit_text, category, summary, quote='', language='en', access_ok=None, hint='', call_id='', caller_last4='', source='retell', now=None):
    """Create a ticket or merge into an open duplicate. Returns (ticket row, merged: bool). Caller holds the transaction."""
    now = now or time.time()
    category = category_of(category)
    unit = find_unit(c, building['id'], unit_text)
    unit_name = unit['unit'] if unit else (norm_unit(unit_text) or '(unit not given)')
    level, reason = urgency(category, f'{summary} {quote}', now, hint)
    reporter = {'call_id': call_id, 'last4': caller_last4, 'ts': now, 'quote': quote[:500], 'language': language}
    # Duplicate merge: same unit and category within 2 h, not closed → one ticket, reporters +1.
    dup = c.execute("SELECT * FROM tickets WHERE building_id=? AND unit=? AND category=? AND created>? AND status!='closed' AND merged_into IS NULL ORDER BY created LIMIT 1",
                    (building['id'], unit_name, category, now - MERGE_WINDOW)).fetchone()
    if dup:
        reporters = json.loads(dup['reporters'])
        if not any(r['call_id'] == call_id for r in reporters if call_id):
            reporters.append(reporter)
        up = URGENCIES.index(level) < URGENCIES.index(dup['urgency'])  # a duplicate can only raise urgency
        c.execute('UPDATE tickets SET reporters=?,urgency=?,urgency_reason=?,updated=? WHERE code=?',
                  (json.dumps(reporters), level if up else dup['urgency'], reason if up else dup['urgency_reason'], now, dup['code']))
        tlog(c, dup['code'], 'reporter', f"Another report from {('••' + caller_last4) if caller_last4 else 'a caller'} ({len(reporters)} reporters)"
             + (f': "{quote[:140]}"' if quote else '') + (f' · urgency raised to {level}' if up else ''), ts=now)
        return c.execute('SELECT * FROM tickets WHERE code=?', (dup['code'],)).fetchone(), True
    code = new_code(c)
    c.execute('INSERT INTO tickets VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
              (code, building['id'], unit_name, 1 if unit else 0, category, level, reason, summary[:1000], quote[:1000], language,
               None if access_ok is None else int(bool(access_ok)), json.dumps([reporter]), 'new', None, now, now, None, None, '[]', None, None, source))
    tlog(c, code, 'created', f"Ticket filed by {'phone agent' if source == 'retell' else source}: {NOUN.get(category, category)} in {unit_name} · {level} ({reason})", ts=now)
    if not unit:
        tlog(c, code, 'flag', f'Unit "{unit_text}" is not in the building records: confirm with the tenant', ts=now)
    if unit:
        cross_reference(c, building['id'], code, category, dict(unit), now)
    return c.execute('SELECT * FROM tickets WHERE code=?', (code,)).fetchone(), False


def cross_reference(c, building_id, code, category, unit, now):
    """Link to same-building, same-category tickets from the last 7 days that share a unit, stack, HVAC zone or floor."""
    rows = c.execute('SELECT t.code,t.related,u.unit,u.stack,u.floor,u.hvac_zone FROM tickets t JOIN units u ON u.building_id=t.building_id AND u.unit=t.unit '
                     'WHERE t.building_id=? AND t.category=? AND t.created>? AND t.code!=? AND t.merged_into IS NULL',
                     (building_id, category, now - XREF_WINDOW, code)).fetchall()
    by_rel = {}
    for r in rows:
        rel = relation(unit, dict(r), category)
        if rel:
            by_rel.setdefault(rel, []).append(r)
    if not by_rel:
        return None
    # Strongest element first: the same unit, then the riser/stack, then the HVAC zone, then the floor.
    rel = next(k for k in ('unit',) + ORDER.get(category, DEFAULT_ORDER) if k in by_rel)
    group = by_rel[rel]
    reason = xref_reason(category, rel, unit, [unit['unit']] + [r['unit'] for r in group])
    links = [{'code': r['code'], 'reason': reason, 'relation': rel} for r in group]
    # Weaker matches are still linked, with their own reason, so nothing related is silently left out.
    for other, rs in by_rel.items():
        if other != rel:
            text = xref_reason(category, other, unit, [unit['unit']] + [r['unit'] for r in rs])
            links += [{'code': r['code'], 'reason': text, 'relation': other} for r in rs if r['code'] not in {l['code'] for l in links}]
    c.execute('UPDATE tickets SET related=? WHERE code=?', (json.dumps(links), code))
    tlog(c, code, 'related', f"Linked to {', '.join(l['code'] for l in links)}: {reason} · a person decides; nothing is closed automatically", ts=now)
    for r in rows:
        link = next((l for l in links if l['code'] == r['code']), None)
        if not link:
            continue
        group_codes = {l['code'] for l in links if l['relation'] == link['relation']}
        # Older members of the same group get the updated count ("3rd leak report ...") on their existing links too.
        theirs = [{**x, 'reason': link['reason']} if x['code'] in group_codes and x.get('relation') == link['relation'] else x
                  for x in json.loads(r['related'] or '[]') if x['code'] != code] + [{'code': code, 'reason': link['reason'], 'relation': link['relation']}]
        c.execute('UPDATE tickets SET related=?,updated=? WHERE code=?', (json.dumps(theirs), now, r['code']))
        tlog(c, r['code'], 'related', f"New related ticket {code} ({unit['unit']}): {link['reason']}", ts=now)
    return reason


# --- Retell functions (contracts in sessions/dashboard-agent/SESSION_CONTEXT.md) ---

@router.post('/retell/fn/lookup_unit')
def lookup_unit(p=Depends(parse)):
    call, args = p
    with connect() as c:
        b = building_for(c, call, args.get('building_hint', ''))
        u = find_unit(c, b['id'], args.get('unit', '')) if b else None
    if not u:
        return {'ok': False, 'ask': 'Which unit number is on your door?'}
    return {'ok': True, 'building': b['name'], 'unit': u['unit'], 'floor': u['floor'], 'stack': u['stack']}


@router.post('/retell/fn/create_ticket')
def create_ticket(p=Depends(parse)):
    call, args = p

    def make():
        with connect() as c:
            c.execute('BEGIN IMMEDIATE')
            b = building_for(c, call, args.get('building_hint', ''))
            t, merged = file_ticket(c, b, args.get('unit', ''), args.get('category', 'other'), (args.get('summary') or args.get('category') or 'Tenant report')[:1000],
                                    args.get('caller_quote') or '', args.get('language') or 'en', args.get('access_ok'), args.get('urgency_hint', ''),
                                    call['call_id'], last4(call), 'retell')
            event(c, t['code'], f"Building ticket {t['code']} {'updated (duplicate report)' if merged else 'filed'} · {t['urgency']} · unit {t['unit']}")
        out = {'code': t['code'], 'urgency': t['urgency'], 'eta_text': ETA_TEXT}  # never a repair time
        if merged:
            out['merged_into'] = t['code']
        related = json.loads(t['related'] or '[]')
        if related:
            out['related_reason'] = related[0]['reason']
        if t['urgency'] == 'emergency' and t['category'] != 'water_leak':
            out['safety_text'] = 'If there is fire, smoke, a gas smell or someone is hurt, hang up and call 911 now, and leave the unit if it is safe to.'
        if not t['unit_verified']:
            out['ask'] = 'Which unit number is on your door?'
        return out
    return once('create_ticket', call, args, make)


STATUS_TEXT = {'new': 'received; the manager will review it soon', 'assigned': 'assigned to {who}', 'in_progress': 'being worked on',
               'waiting_tenant': 'waiting to hear back from you', 'closed': 'closed'}


@router.post('/retell/fn/ticket_status')
def ticket_status(p=Depends(parse)):
    call, args = p
    code = (args.get('code') or '').upper().replace(' ', '')
    if code and not code.startswith('T-'):
        code = 'T-' + code.lstrip('T').lstrip('-')
    digits = re.sub(r'\D', '', args.get('phone_last4') or '')[-4:]
    with connect() as c:
        t = c.execute('SELECT * FROM tickets WHERE code=?', (code,)).fetchone()
        who = c.execute('SELECT name,role FROM staff_vendors WHERE id=?', (t['assignee'],)).fetchone() if t and t['assignee'] else None
    if not t or not digits or digits not in {r.get('last4') for r in json.loads(t['reporters'])}:
        return {'status_text': "I couldn't find a ticket with that code and phone number."}
    if t['merged_into']:
        return {'status_text': f"Ticket {code} was combined with ticket {t['merged_into']}; ask me about that code for updates."}
    text = STATUS_TEXT.get(t['status'], t['status']).format(who=f"our {who['role']}" if who else 'a staff member')
    return {'status_text': f'Ticket {code} is {text}.'}


def police_lines():
    from . import resources
    return [r for r in resources.resources() if r.get('type') == 'police_nonemergency' and r.get('transfer_ok') and r.get('transfer_number')]


def drill_teammate(kind):
    # Drill mode: a teammate from DIZA_RESPONDERS stands in for the real line (a 'security'/'police' skill wins).
    team = responders_from_env()
    if not team:
        return None
    return next((r for r in team if kind.split('_')[0] in (r.get('skills') or '')), team[0])


def pick_police(location_text, building):
    """The allowlisted police non-emergency line whose `covers` list (cities, neighborhoods) appears in the location text."""
    text = ' '.join(x for x in ((location_text or ''), (building['address'] if building and not location_text else '')) if x).lower()
    lines = police_lines()
    best = None
    for r in lines:
        for area in r.get('covers') or [r.get('city', '')]:
            if area and re.search(rf'\b{re.escape(area.lower())}\b', text) and (best is None or len(area) > best[0]):
                best = (len(area), r)  # most specific area wins ("Venice" over "Los Angeles")
    return best[1] if best else None


@router.post('/retell/fn/local_contact')
def local_contact(p=Depends(parse)):
    call, args = p
    kind = args.get('kind', '')
    if kind not in ('security', 'police_nonemergency'):
        return {'name': '', 'transfer_number': ''}
    with connect() as c:
        b = c.execute('SELECT * FROM buildings WHERE id=?', (args['building_id'],)).fetchone() if args.get('building_id') else None
        if not b and not args.get('location_text'):
            b = building_for(c, call)
        real = None
        if kind == 'security' and b:
            s = c.execute("SELECT * FROM staff_vendors WHERE building_id=? AND role='security' ORDER BY id LIMIT 1", (b['id'],)).fetchone()
            real = {'name': s['name'], 'transfer_number': s['phone'] or ''} if s else None
        if not real or (kind == 'security' and not real['transfer_number']):
            police = pick_police(args.get('location_text', ''), b)
            if police:
                real = {'name': police['name'], 'transfer_number': police['transfer_number']}
        out = {'name': '', 'transfer_number': ''}
        if DEMO:
            mate = drill_teammate(kind)
            if mate:
                out = {'name': f"{mate['name']} (drill stand-in for {real['name'] if real else kind.replace('_', ' ')})", 'transfer_number': e164(mate['phone'])}
        elif real:
            out = real
        if out['name']:
            # Ticket trail: the redirect shows on this call's ticket (if any) and in the event log.
            t = c.execute("SELECT code FROM tickets WHERE reporters LIKE ? ORDER BY created DESC LIMIT 1", (f'%"{call["call_id"]}"%',)).fetchone()
            stamp = datetime.now(TZ).strftime('%H:%M')
            if t:
                tlog(c, t['code'], 'transfer', f"Caller offered a transfer to {out['name']}, {stamp}")
            event(c, call['call_id'], f"Local contact for {kind.replace('_', ' ')}: {out['name']}, {stamp}")
    return out


# --- Manager API (behind OPS_API_TOKEN when set) ---

def ticket_view(t, now, events):
    d = dict(t)
    d['reporters'] = json.loads(d['reporters'] or '[]')
    d['related'] = json.loads(d['related'] or '[]')
    d['timeline'] = events.get(t['code'], [])[-40:]
    d['ca_clock'] = ca_clock(d, now)
    d['target_s'] = TARGETS[d['urgency']]
    d['access_ok'] = None if d['access_ok'] is None else bool(d['access_ok'])
    return d


def insights(tickets, now):
    open_ = [t for t in tickets if t['status'] != 'closed' and not t['merged_into']]
    week = [t for t in tickets if t['created'] > now - 7 * 86400]
    waits = [t['first_human_action_at'] - t['created'] for t in tickets if t['first_human_action_at'] and t['created'] > now - 30 * 86400]
    repeats = {}
    for t in week:
        for l in t['related']:
            if l['relation'] in ('stack', 'hvac_zone', 'floor'):
                key = l['reason'].split(' this week')[0].split(' report ', 1)[-1]  # e.g. "on stack B"
                repeats.setdefault((NOUN.get(t['category'], t['category']), key), set()).update({t['code'], l['code']})
    langs = {}
    for t in week:
        for r in t['reporters']:
            langs[r.get('language') or 'en'] = langs.get(r.get('language') or 'en', 0) + 1
    return {'open_by_urgency': {u: sum(1 for t in open_ if t['urgency'] == u) for u in URGENCIES},
            'median_first_action_s': statistics.median(waits) if waits else None,
            'duplicates_merged_week': sum(max(0, len(t['reporters']) - 1) for t in week) + sum(1 for t in week if t['merged_into']),
            'top_repeats': sorted(({'problem': p, 'where': w, 'count': len(s)} for (p, w), s in repeats.items()), key=lambda x: -x['count'])[:5],
            'language_mix': dict(sorted(langs.items(), key=lambda kv: -kv[1]))}


@app.get('/api/building')
def building_state(building_id: str = ''):
    now = time.time()
    with connect() as c:
        b = c.execute('SELECT * FROM buildings WHERE id=?', (building_id,)).fetchone() if building_id else building_for(c)
        if not b:
            raise HTTPException(404, 'No building')
        # Open tickets of any age plus closed ones from the last 14 days, capped, so the 1.5 s poll stays small.
        rows = c.execute("SELECT * FROM tickets WHERE building_id=? AND (status!='closed' OR updated>?) ORDER BY created DESC LIMIT 300",
                         (b['id'], now - 14 * 86400)).fetchall()
        codes = [r['code'] for r in rows]
        events = {}
        for e in c.execute(f"SELECT * FROM ticket_events WHERE code IN ({','.join('?' * len(codes))}) ORDER BY ts", codes).fetchall() if codes else []:
            events.setdefault(e['code'], []).append(dict(e))
        tickets = [ticket_view(r, now, events) for r in rows]
        call_ids = list({r['call_id'] for t in tickets if t['status'] != 'closed' for r in t['reporters'] if r.get('call_id')})[:60]
        calls = [dict(r) for r in c.execute(f"SELECT * FROM calls WHERE call_id IN ({','.join('?' * len(call_ids))})", call_ids)] if call_ids else []
        public = dict(b)
        public['after_hours_last4'] = re.sub(r'\D', '', b['after_hours_phone'] or '')[-4:]
        public.pop('after_hours_phone', None)
        return {'demo': DEMO, 'now': now, 'building': public, 'buildings': [{'id': x['id'], 'name': x['name']} for x in c.execute('SELECT id,name FROM buildings')],
                'units': [dict(u) for u in c.execute('SELECT * FROM units WHERE building_id=? ORDER BY floor,stack,unit', (b['id'],))],
                'staff': [{**{k: s[k] for k in ('id', 'name', 'role', 'skills')}, 'has_phone': bool(s['phone'])} for s in c.execute('SELECT * FROM staff_vendors WHERE building_id=? ORDER BY role,name', (b['id'],))],
                'tickets': tickets, 'calls': calls, 'insights': insights(tickets, now), 'targets': TARGETS}


def touch(c, t, now, actor, kind, message):
    c.execute('UPDATE tickets SET updated=?,first_human_action_at=COALESCE(first_human_action_at,?) WHERE code=?', (now, now, t['code']))
    tlog(c, t['code'], kind, message, actor, now)


def get_ticket(c, code):
    t = c.execute('SELECT * FROM tickets WHERE code=?', (code,)).fetchone()
    if not t:
        raise HTTPException(404, 'Ticket not found')
    return t


class Assign(BaseModel):
    assignee: str = Field(min_length=1, max_length=60)
    actor: str = Field(default='manager', max_length=60)


@app.post('/api/tickets/{code}/assign')
def assign_ticket(code: str, a: Assign):
    now = time.time()
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        t = get_ticket(c, code)
        s = c.execute('SELECT * FROM staff_vendors WHERE id=?', (a.assignee,)).fetchone()
        if not s:
            raise HTTPException(400, 'Unknown staff member or vendor')
        c.execute("UPDATE tickets SET assignee=?,status=CASE WHEN status='new' THEN 'assigned' ELSE status END WHERE code=?", (s['id'], code))
        touch(c, t, now, a.actor, 'assign', f"Assigned to {s['name']} ({s['role']})")
    return {'ok': True}


class Status(BaseModel):
    status: str
    actor: str = Field(default='manager', max_length=60)


@app.post('/api/tickets/{code}/status')
def set_status(code: str, s: Status):
    if s.status not in STATUSES:
        raise HTTPException(400, 'Invalid status')
    now = time.time()
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        t = get_ticket(c, code)
        c.execute('UPDATE tickets SET status=?,closed_at=? WHERE code=?', (s.status, now if s.status == 'closed' else None, code))
        touch(c, t, now, s.actor, 'status', f"Status {t['status'].replace('_', ' ')} → {s.status.replace('_', ' ')}")
    return {'ok': True}


class Note(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    actor: str = Field(default='manager', max_length=60)


@app.post('/api/tickets/{code}/note')
def add_note(code: str, n: Note):
    with connect() as c:
        touch(c, get_ticket(c, code), time.time(), n.actor, 'note', n.text)
    return {'ok': True}


class Actor(BaseModel):
    text: str = Field(default='', max_length=1000)
    actor: str = Field(default='manager', max_length=60)


@app.post('/api/tickets/{code}/notified')
def tenant_notified(code: str, n: Actor | None = None):
    now = time.time()
    with connect() as c:
        t = get_ticket(c, code)
        c.execute('UPDATE tickets SET tenant_notified_at=? WHERE code=?', (now, code))
        touch(c, t, now, n.actor if n else 'manager', 'notified', 'Tenant notified' + (f': {n.text}' if n and n.text else ''))
    return {'ok': True}


class Merge(BaseModel):
    into: str
    actor: str = Field(default='manager', max_length=60)


@app.post('/api/tickets/{code}/merge')
def merge_ticket(code: str, m: Merge):
    # A person merges one ticket into another. The merged ticket stays visible (under its parent) and can be unmerged.
    if code == m.into:
        raise HTTPException(400, 'Cannot merge a ticket into itself')
    now = time.time()
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        t, parent = get_ticket(c, code), get_ticket(c, m.into)
        if parent['merged_into']:
            raise HTTPException(409, f"{m.into} is itself merged into {parent['merged_into']}")
        c.execute('UPDATE tickets SET merged_into=? WHERE code=?', (m.into, code))
        c.execute('UPDATE tickets SET merged_into=? WHERE merged_into=?', (m.into, code))  # keep chains one level deep
        touch(c, t, now, m.actor, 'merge', f'Merged into {m.into} by {m.actor}')
        touch(c, parent, now, m.actor, 'merge', f"{code} ({t['unit']}) merged into this ticket by {m.actor}")
    return {'ok': True}


@app.post('/api/tickets/{code}/unmerge')
def unmerge_ticket(code: str, n: Actor | None = None):
    now = time.time()
    actor = n.actor if n else 'manager'
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        t = get_ticket(c, code)
        if not t['merged_into']:
            raise HTTPException(409, 'Ticket is not merged')
        parent = get_ticket(c, t['merged_into'])
        c.execute('UPDATE tickets SET merged_into=NULL WHERE code=?', (code,))
        touch(c, t, now, actor, 'merge', f"Unmerged from {parent['code']} by {actor}")
        touch(c, parent, now, actor, 'merge', f'{code} unmerged by {actor}')
    return {'ok': True}


class Split(BaseModel):
    call_id: str
    actor: str = Field(default='manager', max_length=60)


@app.post('/api/tickets/{code}/split')
def split_reporter(code: str, s: Split):
    # Undo an automatic duplicate merge: one reporter becomes their own ticket (same unit and category).
    now = time.time()
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        t = get_ticket(c, code)
        reporters = json.loads(t['reporters'])
        mine = [r for r in reporters if r.get('call_id') == s.call_id]
        if not mine or len(reporters) < 2:
            raise HTTPException(409, 'That reporter is not on this ticket, or is its only reporter')
        new = new_code(c)
        r = mine[0]
        c.execute('INSERT INTO tickets SELECT ?,building_id,unit,unit_verified,category,urgency,urgency_reason,summary,?,?,access_ok,?,?,NULL,?,?,?,NULL,related,NULL,NULL,source FROM tickets WHERE code=?',
                  (new, r.get('quote', ''), r.get('language', 'en'), json.dumps(mine), 'new', r['ts'], now, now, code))
        c.execute('UPDATE tickets SET reporters=? WHERE code=?', (json.dumps([x for x in reporters if x.get('call_id') != s.call_id]), code))
        touch(c, t, now, s.actor, 'merge', f"Reporter ••{r.get('last4', '')} split out into {new} by {s.actor}")
        tlog(c, new, 'created', f'Split out of {code} by {s.actor}', s.actor, now)
    return {'code': new}


class UnitEdit(BaseModel):
    building_id: str = DEMO_BUILDING
    unit: str = Field(min_length=1, max_length=20)
    rename_to: str = Field(default='', max_length=20)
    floor: int | None = Field(default=None, ge=-5, le=200)
    stack: str | None = Field(default=None, max_length=20)
    hvac_zone: str | None = Field(default=None, max_length=40)
    tenant_language: str | None = Field(default=None, max_length=10)


@app.post('/api/units')
def edit_unit(u: UnitEdit):
    """Add a unit, or rename it / set its floor, stack and HVAC zone (edit mode on the building map)."""
    name = norm_unit(u.unit)
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        row = c.execute('SELECT * FROM units WHERE building_id=? AND unit=?', (u.building_id, name)).fetchone()
        if not row:
            c.execute('INSERT INTO units VALUES(?,?,?,?,?,?)', (u.building_id, name, u.floor if u.floor is not None else int(re.match(r'\d*', name).group(0) or 1),
                                                                 u.stack if u.stack is not None else re.sub(r'^\d+', '', name)[:1], u.hvac_zone or '', u.tenant_language))
        else:
            c.execute('UPDATE units SET floor=COALESCE(?,floor),stack=COALESCE(?,stack),hvac_zone=COALESCE(?,hvac_zone),tenant_language=COALESCE(?,tenant_language) WHERE building_id=? AND unit=?',
                      (u.floor, u.stack, u.hvac_zone, u.tenant_language, u.building_id, name))
        if u.rename_to and norm_unit(u.rename_to) != name:
            new = norm_unit(u.rename_to)
            if c.execute('SELECT 1 FROM units WHERE building_id=? AND unit=?', (u.building_id, new)).fetchone():
                raise HTTPException(409, f'Unit {new} already exists')
            c.execute('UPDATE units SET unit=? WHERE building_id=? AND unit=?', (new, u.building_id, name))
            for t in c.execute('SELECT code FROM tickets WHERE building_id=? AND unit=?', (u.building_id, name)).fetchall():
                c.execute('UPDATE tickets SET unit=? WHERE code=?', (new, t['code']))
                tlog(c, t['code'], 'unit', f'Unit renamed {name} → {new} by the manager', 'manager')
    return {'ok': True}


# --- Demo data ---

DEMO_TICKETS = [
    # (hours ago, unit, category, summary, quote, language, access_ok, last4)
    (50, '2B', 'water_leak', 'Water coming through the bathroom ceiling', 'There is water dripping from my bathroom ceiling, it started last night.', 'en', True, '0141'),
    (20, '3B', 'water_leak', 'Leak under the bathroom sink', 'Hay agua saliendo debajo del lavabo del baño.', 'es', True, '0177'),
    (0.4, '4B', 'water_leak', 'Water leaking from the ceiling above the tub', 'Water is pouring from the ceiling above my tub!', 'en', True, '0102'),
    (0.3, '4B', 'water_leak', 'Same leak, neighbor across the hall', 'My neighbor in 4B has water everywhere, it is coming into the hallway.', 'en', None, '0163'),
    (5, '3C', 'no_hot_water', 'No hot water since this morning', '아침부터 온수가 안 나와요.', 'ko', True, '0119'),
    (3, '1C', 'no_hot_water', 'Shower is cold', 'The shower only runs cold today.', 'en', False, '0188'),
    (30, '4D', 'pest', 'Cockroaches in the kitchen', 'Hay cucarachas en la cocina otra vez.', 'es', True, '0155'),
    (0.8, '2F', 'lockout', 'Locked out, key broke in the lock', 'Chìa khóa bị gãy trong ổ khóa, tôi không vào nhà được.', 'vi', None, '0124'),
    (2, '1E', 'appliance', 'Fridge not cooling', '冰箱不冷了，食物会坏。', 'zh', True, '0133'),
    (26, '3A', 'noise', 'Loud music late at night from upstairs', 'Música muy fuerte del piso de arriba después de medianoche.', 'es', None, '0146'),
    (24 * 33, '2D', 'no_heat', 'Wall heater does not turn on', 'My wall heater has not worked since last month.', 'en', True, '0112'),
    (24 * 3, '1A', 'other', 'Hallway light out on floor 1', 'The light by the mailboxes is out.', 'en', None, '0190'),
]


@app.post('/api/demo/seed')
def demo_seed(mode: str = 'building'):
    if not DEMO:
        raise HTTPException(403, 'Demo data is only available in drill mode')
    if mode != 'building':
        raise HTTPException(400, 'mode must be building or crisis')
    now = time.time()
    made = []
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        seed_building(c)
        b = c.execute('SELECT * FROM buildings WHERE id=?', (DEMO_BUILDING,)).fetchone()
        tag = f'demo-{int(now)}'
        for i, (hours, unit, cat, summary, quote, lang, access, l4) in sorted(enumerate(DEMO_TICKETS), key=lambda x: -x[1][0]):
            t, _ = file_ticket(c, b, unit, cat, summary, quote, lang, access, call_id=f'{tag}-{i}', caller_last4=l4, source='demo', now=now - hours * 3600)
            made.append((i, t['code']))
        made = [code for _, code in sorted(made)]
        # A little history so the queue shows real states: the oldest leak was assigned, the heater is waiting on parts.
        first, heater = made[0], made[10]
        c.execute("UPDATE tickets SET status='in_progress',assignee='plumb',first_human_action_at=? WHERE code=?", (now - 47 * 3600, first))
        tlog(c, first, 'assign', 'Assigned to Westside Plumbing (demo vendor) (plumber)', 'manager', now - 47 * 3600)
        c.execute("UPDATE tickets SET status='waiting_tenant',assignee='hvac',first_human_action_at=? WHERE code=?", (now - 24 * 31 * 3600, heater))
        tlog(c, heater, 'note', 'Part ordered; waiting for the tenant to confirm an entry time.', 'manager', now - 24 * 31 * 3600)
    return {'created': len(set(made)), 'codes': made, 'simulated': True}
