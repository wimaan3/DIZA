"""911 mode: rules rank the operator's queue, a second reader rescans what callers said for danger the AI missed,
and the dashboard shows how much load the line took off people. No AI here: every rule is plain and its reason is
shown on screen. Errors only push up: rules can raise a card, only a person (with a reason, logged) can lower one.
Nothing is ever hidden or deleted; low confidence means "verify".
"""
import json, re, statistics, time, uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .main import DEMO, ACTIVE_HAZARDS, Report, app, connect, event, kick_geocode, offer, save_report
from .retell_fns import once, parse
from .building import pick_police

router = APIRouter()
SEVERITIES = ('P0', 'P1', 'P2', 'P3')
BASE = {'P0': 100, 'P1': 70, 'P2': 40, 'P3': 10}
TARGET_S = {'P0': 60, 'P1': 300, 'P2': 900, 'P3': 3600}  # age timer turns red after this long without a person on it
FIELDS = ('location', 'callback', 'relationship', 'what', 'people', 'hazards', 'access_needs')
FIELD_LABEL = {'location': 'Location verified', 'callback': 'Callback number', 'relationship': 'On scene or third party', 'what': 'What is happening',
               'people': 'People involved', 'hazards': 'Hazards', 'access_needs': 'Access needs'}
QUESTION_SECONDS = 20  # estimate shown on screen: time an operator spends asking for one checklist item
PLACEHOLDER = '(location not yet given'

# --- Second reader -------------------------------------------------------------------------------------------
# (kind, implied severity, categories that already account for it, Latin/Cyrillic/Armenian/Persian regexes, CJK substrings)
# Matched against the caller's own words only (transcript lines not spoken by the agent, plus the quoted evidence).
LEXICON = [
    ('trapped', 'P0', None,
     [r"trapped", r"stuck (inside|upstairs|in (the|my|our) \w+)", r"can'?t get out", r"cannot get out", r"pinned",
      r"atrapad[oa]s?", r"no (puede|puedo|podemos|pueden) salir",
      r"mắc kẹt", r"bị kẹt", r"застрял\w*", r"заперт\w*", r"не (можем|может|могу) выйти",
      r"փակված", r"թակարդ\w*", r"گیر (افتاده|کرده)\w*", r"nakulong", r"naipit", r"na-?trap", r"hindi (makalabas|kami makalabas)"],
     ['갇혔', '갇혀', '못 나가', '被困', '困住', '出不去']),
    ('breathing', 'P0', {'medical'},
     [r"can'?t breathe", r"cannot breathe", r"not breathing", r"stopped breathing", r"choking",
      r"no (puede|puedo) respirar", r"no respira", r"không thở được", r"không thở", r"не дышит", r"не (может|могу) дышать", r"задыха\w*",
      r"չի շնչում", r"չեմ կարողանում շնչել", r"نفس نمی‌?کش\w*", r"نفسم بالا نمیاد", r"hindi (makahinga|humihinga)"],
     ['숨을 못', '숨을 안 쉬', '不能呼吸', '喘不过气', '没有呼吸']),
    ('unconscious', 'P0', {'medical'},
     [r"unconscious", r"passed out", r"unresponsive", r"won'?t wake up", r"not responding", r"inconsciente", r"desmayad[oa]", r"no responde",
      r"bất tỉnh", r"ngất", r"без сознания", r"потерял\w* сознание", r"ուշագնաց", r"անգիտակից", r"بیهوش", r"walang malay", r"nawalan ng malay"],
     ['의식이 없', '의식을 잃', '昏迷', '不省人事', '晕倒']),
    ('weapon', 'P0', {'safety_crime'},
     [r"guns?", r"shooting", r"shots? fired", r"knife", r"stabbed", r"weapon", r"pistola", r"arma", r"disparos?", r"cuchillo", r"apuñal\w+",
      r"súng", r"cầm dao", r"bị đâm", r"пистолет", r"оружие", r"стрельб\w*", r"нож\w*", r"զենք", r"ատրճանակ", r"դանակ", r"կրակոց",
      r"اسلحه", r"تفنگ", r"چاقو", r"تیراندازی", r"baril", r"binaril", r"kutsilyo", r"sinaksak"],
     ['총을', '총이', '총 들', '칼을', '칼이', '칼 들', '흉기', '有枪', '开枪', '拿枪', '枪声', '持刀', '拿刀', '有刀', '凶器']),
    ('fall', 'P1', {'medical'},
     [r"fell (down|over|in|on|and|off)", r"has fallen", r"took a fall", r"can'?t get up", r"cannot get up", r"se cay[óo]", r"no (se )?puede levantar(se)?",
      r"no puedo levantarme", r"bị ngã", r"té ngã", r"упал\w*", r"ընկել\w*", r"زمین خورد\w*", r"nahulog", r"natumba", r"nadapa"],
     ['넘어졌', '넘어지', '摔倒', '跌倒', '起不来']),
    ('bleeding', 'P1', {'medical'},
     [r"bleeding", r"blood everywhere", r"lots of blood", r"sangr\w+", r"chảy máu", r"кров\w+", r"արյուն\w*", r"خون‌?ریزی", r"خون میاد", r"dumudugo", r"duguan"],
     ['피가 많이', '피를 흘', '流血', '大出血']),
    ('injured', 'P1', {'medical'},
     [r"hurt", r"injured", r"broken (leg|arm|bone|hip)", r"burned", r"herid[oa]s?", r"lastimad[oa]s?", r"bị thương", r"ранен\w*", r"травм\w*",
      r"վիրավոր\w*", r"زخمی", r"مجروح", r"sugatan", r"nasugatan", r"nasaktan"],
     ['다쳤', '부상', '受伤']),
    ('fire', 'P1', {'fire', 'smoke'},
     [r"fire", r"flames?", r"on fire", r"burning", r"fuego", r"incendio", r"llamas", r"se quema\w*", r"cháy", r"hỏa hoạn", r"пожар\w*", r"горит", r"огонь",
      r"հրդեհ\w*", r"այրվում", r"آتش", r"آتیش", r"sunog", r"nasusunog"],
     ['불이', '불났', '화재', '着火', '火灾', '失火', '起火']),
    ('smoke', 'P1', {'fire', 'smoke'},
     [r"smoke", r"smoky", r"humo", r"khói", r"дым\w*", r"ծուխ", r"دود", r"usok"],
     ['연기', '烟雾', '冒烟', '浓烟']),
    ('flood', 'P1', {'flood'},
     [r"water (is )?rising", r"flooding", r"flooded", r"swept away", r"inund\w+", r"el agua (sube|está subiendo)", r"ngập", r"lũ", r"затоп\w*", r"наводн\w*",
      r"ջրհեղեղ", r"سیل", r"آب گرفت\w*", r"baha", r"binabaha"],
     ['침수', '물이 차', '淹水', '水淹', '洪水']),
]
# Speech-to-text sound-alikes: "he has a kite" is often "he has a knife"; "pulled a gone" is "pulled a gun".
SOUNDALIKE = [(re.compile(r"\b(has|had|got|holding|pulled( out)?|waving|with) (a|an|his|her) (kite|knight|nife)\b", re.I), 'knife'),
              (re.compile(r"\b(has|had|got|holding|pulled( out)?|waving) (a|an|his|her) (gone|gum|gunn)\b", re.I), 'gun')]
NEGATED = re.compile(r"\b(no one|nobody|noone|not|isn'?t|aren'?t|wasn'?t|no|nadie|ningún|ninguna|nunca)\b(\W+\w+){0,2}\W*$", re.I)
_COMPILED = [(k, sev, cats, re.compile(r"(?<!\w)(" + '|'.join(words) + r")(?!\w)", re.I), cjk) for k, sev, cats, words, cjk in LEXICON]
VULNERABLE = re.compile(r"\b(wheelchair|oxygen|walker|bedridden|bed-bound|dialysis|insulin|blind|deaf|pregnant|bab(y|ies)|infant|elderly|disabled|"
                        r"silla de ruedas|oxígeno|embarazada|bebé|휠체어|산소|轮椅|氧气|xe lăn|инвалидн\w+ коляск\w+)\b", re.I)


def caller_text(transcript, evidence=''):
    """The caller's own words: every transcript line not spoken by the agent, plus the quoted evidence."""
    lines = [l.split(':', 1)[1].strip() for l in (transcript or '').splitlines() if ':' in l and l.split(':', 1)[0].strip().lower() != 'agent']
    return '\n'.join(lines + ([evidence] if evidence else []))


def danger_hits(text):
    """Every danger mention in the caller's words, skipping plain negations ("no one is trapped")."""
    hits, seen = [], set()
    for kind, sev, cats, rx, cjk in _COMPILED:
        for m in rx.finditer(text or ''):
            if NEGATED.search(text[max(0, m.start() - 40):m.start()]):
                continue
            if kind not in seen:
                seen.add(kind); hits.append({'kind': kind, 'implied': sev, 'cats': cats, 'word': m.group(0), 'soundalike': False})
            break
        for w in cjk:
            if kind not in seen and w in (text or ''):
                seen.add(kind); hits.append({'kind': kind, 'implied': sev, 'cats': cats, 'word': w, 'soundalike': False})
    for rx, meant in SOUNDALIKE:
        m = rx.search(text or '')
        if m and 'weapon' not in seen:
            seen.add('weapon'); hits.append({'kind': 'weapon', 'implied': 'P0', 'cats': {'safety_crime'}, 'word': m.group(0), 'soundalike': meant})
    return hits


def second_reader(severity, category, hits):
    """Flag a card red when the caller's words disagree with the AI's category or severity."""
    flags = []
    for h in hits:
        worse = SEVERITIES.index(h['implied']) < SEVERITIES.index(severity)
        other_cat = h['cats'] is not None and category not in h['cats'] and severity != 'P0'
        if worse or other_cat:
            heard = f" (may be '{h['soundalike']}' misheard)" if h['soundalike'] else ''
            flags.append({'kind': h['kind'], 'word': h['word'], 'implied': h['implied'],
                          'message': f"Possible missed danger: caller said '{h['word']}'{heard}",
                          'why': f"AI filed {severity} {category.replace('_', ' ')}; '{h['kind']}' implies {h['implied']}" if worse else
                                 f"AI filed it as {category.replace('_', ' ')}; caller mentioned {h['kind']}"})
    return flags


# --- Ranking ------------------------------------------------------------------------------------------------
POINTS = {'fall': 25, 'trapped': 40, 'breathing': 35, 'unconscious': 35, 'weapon': 30, 'bleeding': 20, 'injured': 20, 'fire': 10, 'smoke': 5, 'flood': 10}
NUM_WORDS = {'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5}


def people_count(text):
    nums = [int(n) for n in re.findall(r'\b(\d{1,3})\s+(?:people|persons|of us|kids|children|adults|personas|niños)\b', text or '', re.I)]
    nums += [NUM_WORDS[w.lower()] for w in re.findall(r'\b(' + '|'.join(NUM_WORDS) + r')\s+(?:people|of us|kids|children|personas|niños)\b', text or '', re.I)]
    return max(nums) if nums else None


def rank(severity, hits, vulnerable, people, independent):
    """Score with every reason spelled out, e.g. 'trapped +40, wheelchair +10'. Higher is more urgent."""
    reasons = [(f'{severity} base', BASE[severity])]
    for h in hits:
        if h['kind'] in POINTS:
            reasons.append((h['kind'] + (' (possible)' if h['soundalike'] else ''), POINTS[h['kind']] // (2 if h['soundalike'] else 1)))
    for v in vulnerable[:2]:
        reasons.append((v.lower(), 10))
    if people and people >= 3:
        reasons.append((f'{people} people', 10))
    if independent > 1:
        reasons.append((f'{independent} independent callers', min(15, 5 * (independent - 1))))
    return sum(p for _, p in reasons), reasons


# --- Tables -------------------------------------------------------------------------------------------------
def init_ops():
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS incident_fields(call_id TEXT,field TEXT,value TEXT,updated REAL,PRIMARY KEY(call_id,field));
        CREATE TABLE IF NOT EXISTS zones(id TEXT PRIMARY KEY,name TEXT,kind TEXT,points TEXT,created REAL,created_by TEXT);
        ''')
        for col in ('reviewed_at REAL', 'reviewed_by TEXT', 'review_note TEXT', 'claimed_by TEXT'):
            try: c.execute(f'ALTER TABLE reports ADD COLUMN {col}')
            except Exception: pass
        # Retry recent reports that never got a pin (lookups used to be LA-only and couldn't split "Wichita and Tulsa").
        c.execute("UPDATE reports SET geo_tried=0 WHERE lat IS NULL AND geo_tried=1 AND created>? AND location NOT LIKE '(%'", (time.time() - 86400,))
        regeocode_once(c, 'regeocode-2026-10-18')


def regeocode_once(c, name):
    """One-time fix: re-look-up the last day's pins made by older geocoder rules ("Tulsa" St, a "Bakersfield" building)
    and split lists of places. Never touches caller GPS, operator-placed pins or demo data. Runs once per database."""
    c.execute('CREATE TABLE IF NOT EXISTS migrations(name TEXT PRIMARY KEY,ts REAL)')
    if c.execute('SELECT 1 FROM migrations WHERE name=?', (name,)).fetchone():
        return 0
    n = c.execute("UPDATE reports SET lat=NULL,lon=NULL,geo_tried=0 WHERE created>? AND gps_accuracy IS NULL AND location NOT LIKE '(%' "
                  "AND location NOT LIKE 'Placed by operator%' AND source!='demo' AND dedupe NOT LIKE '%#%'", (time.time() - 86400,)).rowcount
    c.execute('INSERT INTO migrations VALUES(?,?)', (name, time.time()))
    return n


def call_of(report):
    """Reports filed by a phone agent carry their call id in front of the dedupe key ('<call_id>:<hash>')."""
    return report['dedupe'].split(':')[0] if report['source'] in ('retell', 'demo') and ':' in (report['dedupe'] or '') else ''


def checklist(r, fields, caller_last4, text, hits, vulnerable, people):
    loc = r['location'] or ''
    if r['gps_accuracy'] is not None:
        location = ('ok', f"GPS from caller ±{round(r['gps_accuracy'])} m")
    elif loc.startswith('Placed by operator') or fields.get('location_verified'):
        location = ('ok', 'Placed by an operator')
    elif r['lat'] is not None:
        location = ('approx', f'Approximate (address lookup): {loc}')
    elif fields.get('location') or not loc.startswith(PLACEHOLDER):
        location = ('approx', fields.get('location') or loc)
    else:
        location = ('missing', '')
    hazard_words = [h['word'] for h in hits if h['kind'] in ('fire', 'smoke', 'flood', 'weapon')]
    items = {
        'location': location,
        'callback': ('ok', fields['callback']) if fields.get('callback') else ('ok', f'Caller ••{caller_last4}') if caller_last4 else ('missing', ''),
        'relationship': ('ok', fields['relationship'].replace('_', ' ')) if fields.get('relationship') else ('missing', ''),
        'what': ('ok', fields.get('what') or r['category'].replace('_', ' ')) if fields.get('what') or r['category'] not in ('other', 'info') else ('missing', ''),
        'people': ('ok', fields.get('people') or f'{people} people') if fields.get('people') or people else ('missing', ''),
        'hazards': ('ok', fields.get('hazards') or ', '.join(hazard_words) or r['category']) if fields.get('hazards') or hazard_words or r['category'] in ACTIVE_HAZARDS else ('missing', ''),
        'access_needs': ('ok', fields.get('access_needs') or ', '.join(vulnerable)) if fields.get('access_needs') or vulnerable else ('missing', ''),
    }
    return [{'key': k, 'label': FIELD_LABEL[k], 'state': items[k][0], 'value': items[k][1]} for k in FIELDS]


def missing_for(c, call_id):
    """What the agent still needs to ask, for update_incident's reply."""
    r = c.execute('SELECT * FROM reports WHERE substr(dedupe,1,?)=? ORDER BY created DESC LIMIT 1', (len(call_id) + 1, call_id + ':')).fetchone()
    fields = {x['field']: x['value'] for x in c.execute('SELECT field,value FROM incident_fields WHERE call_id=?', (call_id,))}
    if not r:
        return [f for f in FIELDS if f not in fields and f != 'callback']
    call = c.execute('SELECT caller_last4,transcript FROM calls WHERE call_id=?', (call_id,)).fetchone()
    text = caller_text(call['transcript'] if call else '', r['evidence'])
    hits = danger_hits(text)
    items = checklist(r, fields, call['caller_last4'] if call else '', text, hits, VULNERABLE.findall(text) and [m.group(0) for m in VULNERABLE.finditer(text)], people_count(text))
    return [i['key'] for i in items if i['state'] == 'missing']


# --- Phone agent: fill the card live ------------------------------------------------------------------------
@router.post('/retell/fn/update_incident')
def update_incident(p=Depends(parse)):
    call, args = p
    field, value = args.get('field', ''), str(args.get('value') or '').strip()[:500]

    def make():
        with connect() as c:
            if field not in FIELDS or not value:
                return {'ok': False, 'missing': missing_for(c, call['call_id'])}
            c.execute('INSERT INTO incident_fields VALUES(?,?,?,?) ON CONFLICT(call_id,field) DO UPDATE SET value=excluded.value,updated=excluded.updated',
                      (call['call_id'], field, value, time.time()))
            r = c.execute('SELECT * FROM reports WHERE substr(dedupe,1,?)=? ORDER BY created DESC LIMIT 1', (len(call['call_id']) + 1, call['call_id'] + ':')).fetchone()
            regeo = False
            if r and field == 'location' and (r['location'] or '').startswith(PLACEHOLDER):
                # A P0 flagged before the caller gave an address: the card gets the location (and a pin) as soon as they say it.
                c.execute('UPDATE reports SET location=?,lat=NULL,lon=NULL,geo_tried=0 WHERE id=?', (value, r['id']))
                regeo = True
            q = c.execute('SELECT id FROM requests WHERE report_id=?', (r['id'],)).fetchone() if r else None
            event(c, q['id'] if q else call['call_id'], f"Phone agent added {FIELD_LABEL[field].lower()}: {value[:120]}")
            out = {'ok': True, 'missing': missing_for(c, call['call_id'])}
        if regeo:
            kick_geocode(r['id'])
        return out
    return once('update_incident', call, args, make)


# --- Operator view ------------------------------------------------------------------------------------------
def build_incidents(c, now):
    reports = [dict(r) for r in c.execute('SELECT * FROM reports ORDER BY created DESC LIMIT 300')]
    call_ids = {call_of(r) for r in reports} - {''}
    marks = ','.join('?' * len(call_ids))
    calls = {x['call_id']: dict(x) for x in c.execute(f'SELECT call_id,caller_last4,transcript,status,started,agent FROM calls WHERE call_id IN ({marks})', tuple(call_ids))} if call_ids else {}
    fields = {}
    if call_ids:
        for x in c.execute(f'SELECT * FROM incident_fields WHERE call_id IN ({marks})', tuple(call_ids)):
            fields.setdefault(x['call_id'], {})[x['field']] = x['value']
    requests = {q['report_id']: dict(q) for q in c.execute('SELECT * FROM requests')}
    keys = {q['id'] for q in requests.values()} | {r['id'] for r in reports} | call_ids
    timeline = {}
    for e in c.execute('SELECT request_id,ts,message FROM events WHERE ts>? ORDER BY ts', (now - 2 * 86400,)):
        if e['request_id'] in keys:
            timeline.setdefault(e['request_id'], []).append({'ts': e['ts'], 'message': e['message']})
    callbacks = {}
    for x in c.execute("SELECT caller_last4,started,duration_s FROM calls WHERE direction='outbound' AND started>?", (now - 2 * 86400,)):
        if (x['duration_s'] or 0) >= 10:
            callbacks.setdefault(x['caller_last4'], []).append(x['started'])
    out = []
    for r in reports:
        cid = call_of(r)
        call = calls.get(cid, {})
        f = fields.get(cid, {})
        text = caller_text(call.get('transcript'), r['evidence'])
        hits = danger_hits(text)
        flags = second_reader(r['severity'], r['category'], hits)
        vulnerable = list(dict.fromkeys(m.group(0).lower() for m in VULNERABLE.finditer(text + ' ' + (f.get('access_needs') or ''))))
        people = people_count(text + ' ' + (f.get('people') or ''))
        reviewed = r['reviewed_at'] is not None
        effective = r['severity']
        if flags and not reviewed:  # the second reader can only push a card up, and a person's review settles it
            effective = min([r['severity']] + [x['implied'] for x in flags], key=SEVERITIES.index)
        q = requests.get(r['id'])
        events = sorted(timeline.get(q['id'] if q else '', []) + timeline.get(r['id'], []) + timeline.get(cid, []), key=lambda e: e['ts'])
        handled = r['claimed_by'] or (q and q['status'] in ('accepted', 'done')) or (r['severity'] == 'P3' and not flags)
        out.append({**{k: r[k] for k in ('id', 'cluster_id', 'location', 'category', 'summary', 'evidence', 'severity', 'reason', 'language', 'source', 'created',
                                         'lat', 'lon', 'gps_accuracy', 'reviewed_at', 'reviewed_by', 'review_note', 'claimed_by')},
                    'effective': effective, 'flags': flags, 'call_id': cid, 'caller_last4': call.get('caller_last4') or '', 'call_status': call.get('status') or '',
                    'agent': call.get('agent') or '', 'fields': f, 'vulnerable': vulnerable, 'people': people, 'hits': [h['word'] for h in hits],
                    'quotes': list(dict.fromkeys(l.strip() for l in text.splitlines() if l.strip()))[-4:], 'request': q, 'timeline': events[-30:],
                    'agency': (pick_police(r['location'], None) or {}).get('name', ''), 'handled': bool(handled),
                    'wait_s': (now - r['created']) if not handled else None, 'target_s': TARGET_S[effective],
                    'checklist': checklist(r, f, call.get('caller_last4') or '', text, hits, vulnerable, people),
                    'callback_answered': any(t > r['created'] for t in callbacks.get(call.get('caller_last4') or '-', []))})
    # Corroboration per incident (cluster): independent callers are distinct phone numbers, never just more rows.
    groups = {}
    for i in out:
        groups.setdefault(i['cluster_id'], []).append(i)
    for i in out:
        g = groups[i['cluster_id']]
        rel = [x['fields'].get('relationship', '') for x in g]
        i['corroboration'] = {'reports': len(g), 'independent_callers': len({x['caller_last4'] for x in g if x['caller_last4']}),
                              'on_scene': sum('scene' in v for v in rel), 'third_party': sum('third' in v for v in rel),
                              'gps': sum(x['gps_accuracy'] is not None for x in g), 'stated_address': sum(x['gps_accuracy'] is None and not x['location'].startswith(PLACEHOLDER) for x in g),
                              'callback_answered': any(x['callback_answered'] for x in g)}
        i['score'], i['score_reasons'] = rank(i['effective'], [h for h in danger_hits('\n'.join(i['quotes']))], i['vulnerable'], i['people'], i['corroboration']['independent_callers'])
    # P0 pinned on top, then score, then whoever has waited longest.
    out.sort(key=lambda i: (i['effective'] != 'P0', -i['score'], i['created']))
    return out


def load_metrics(c, incidents, now):
    """What the line took off people in the last 24 h, measured from stored calls and reports (estimates are labelled)."""
    since = now - 86400
    calls = [dict(x) for x in c.execute("SELECT call_id,direction,started,ended,duration_s,status FROM calls WHERE started>?", (since,))]
    inbound = [x for x in calls if x['direction'] != 'outbound']
    moved = {e['request_id'] for e in c.execute("SELECT request_id FROM events WHERE ts>? AND message LIKE 'Warm transfer to%'", (since,))}
    # Peak calls answered at once: nobody waited on hold for an operator during that minute.
    edges = sorted([(x['started'], 1) for x in inbound] + [(x['ended'] or (now if x['status'] == 'live' else x['started'] + (x['duration_s'] or 60)), -1) for x in inbound])
    peak = cur = 0
    for _, d in edges:
        cur += d; peak = max(peak, cur)
    recent = [i for i in incidents if i['created'] > since]
    ranked = [i['created'] - x['started'] for i in recent for x in calls if x['call_id'] == i['call_id'] and i['created'] >= x['started']]
    prefilled = sum(1 for i in recent for item in i['checklist'] if item['state'] != 'missing')
    cases = c.execute('SELECT COUNT(*) FROM cases WHERE created>?', (since,)).fetchone()[0]
    buckets = []
    for k in range(12):  # reports per 5 minutes over the last hour, split by severity
        lo = now - (12 - k) * 300
        row = {s: 0 for s in SEVERITIES}
        for i in recent:
            if lo <= i['created'] < lo + 300:
                row[i['effective']] += 1
        buckets.append({'start': lo, **row})
    return {'calls': len(inbound), 'ai_only': sum(1 for x in inbound if x['call_id'] not in moved), 'transferred': len(moved & {x['call_id'] for x in inbound}),
            'peak_concurrent': peak, 'reports': len(recent), 'incidents': len({i['cluster_id'] for i in recent}),
            'folded': len(recent) - len({i['cluster_id'] for i in recent}), 'prefilled': prefilled, 'question_seconds': QUESTION_SECONDS,
            'minutes_saved': round(prefilled * QUESTION_SECONDS / 60, 1), 'median_to_card_s': statistics.median(ranked) if ranked else None,
            'diverted': sum(1 for i in recent if i['severity'] == 'P3') + cases, 'flags': sum(1 for i in recent if i['flags'] and not i['reviewed_at']),
            'waiting_p0': sum(1 for i in recent if i['effective'] == 'P0' and not i['handled']), 'buckets': buckets,
            'categories': sorted(({'category': k, 'count': v} for k, v in _count(i['category'] for i in recent).items()), key=lambda x: -x['count'])[:8],
            'languages': sorted(({'language': k, 'count': v} for k, v in _count(i['language'] for i in recent).items()), key=lambda x: -x['count'])[:8]}


def _count(xs):
    out = {}
    for x in xs:
        out[x] = out.get(x, 0) + 1
    return out


@app.get('/api/ops')
def ops_state():
    now = time.time()
    with connect() as c:
        incidents = build_incidents(c, now)
        zones = [{**dict(z), 'points': json.loads(z['points'])} for z in c.execute('SELECT * FROM zones ORDER BY created')]
        return {'now': now, 'incidents': incidents, 'zones': zones, 'metrics': load_metrics(c, incidents, now)}


# --- Operator actions (behind OPS_API_TOKEN when set); every one is logged on the card's timeline ---
def effective_severity(c, r):
    """The severity the queue shows: the second reader can raise an unreviewed card; a person's review settles it."""
    if r['reviewed_at'] is not None:
        return r['severity']
    cid = call_of(dict(r))
    call = c.execute('SELECT transcript FROM calls WHERE call_id=?', (cid,)).fetchone() if cid else None
    flags = second_reader(r['severity'], r['category'], danger_hits(caller_text(call['transcript'] if call else '', r['evidence'])))
    return min([r['severity']] + [x['implied'] for x in flags], key=SEVERITIES.index)


def report_row(c, rid):
    r = c.execute('SELECT * FROM reports WHERE id=?', (rid,)).fetchone()
    if not r:
        raise HTTPException(404, 'Report not found')
    return r


def log(c, r, message):
    q = c.execute('SELECT id FROM requests WHERE report_id=?', (r['id'],)).fetchone()
    event(c, q['id'] if q else r['id'], message)


class Priority(BaseModel):
    severity: str = Field(pattern='^P[0-3]$')
    reason: str = Field(default='', max_length=300)
    by: str = Field(default='operator', max_length=100)


@app.post('/api/reports/{rid}/priority')
def set_priority(rid: str, p: Priority):
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        r = report_row(c, rid)
        shown = effective_severity(c, r)  # lowering is judged against what the operator sees, not the stored value
        lower = SEVERITIES.index(p.severity) > SEVERITIES.index(shown)
        if lower and len(p.reason.strip()) < 3:
            raise HTTPException(400, 'Lowering a priority needs a reason')
        c.execute('UPDATE reports SET severity=?,reason=?,reviewed_at=?,reviewed_by=?,review_note=? WHERE id=?',
                  (p.severity, f"Set to {p.severity} by {p.by}" + (f': {p.reason}' if p.reason else ''), time.time(), p.by, p.reason or None, rid))
        if p.severity != 'P3' and not c.execute('SELECT 1 FROM requests WHERE report_id=?', (rid,)).fetchone():
            c.execute('INSERT INTO requests VALUES(?,?,?,?,?,?)', (str(uuid.uuid4()), rid, 'new', None, time.time(), time.time()))
        log(c, r, f"{p.by} {'lowered' if lower else 'raised' if p.severity != shown else 'confirmed'} priority {shown} → {p.severity}" + (f': {p.reason}' if p.reason else ''))
    return {'ok': True}


class Review(BaseModel):
    reason: str = Field(min_length=3, max_length=300)
    by: str = Field(default='operator', max_length=100)


@app.post('/api/reports/{rid}/reviewed')
def mark_reviewed(rid: str, v: Review):
    with connect() as c:
        r = report_row(c, rid)
        c.execute('UPDATE reports SET reviewed_at=?,reviewed_by=?,review_note=? WHERE id=?', (time.time(), v.by, v.reason, rid))
        log(c, r, f'Reviewed by {v.by}: {v.reason}')
    return {'ok': True}


class Take(BaseModel):
    responder_id: str = Field(min_length=1, max_length=100)


@app.post('/api/reports/{rid}/take')
def take_call(rid: str, t: Take):
    """The operator claims the call: the next route_to_human on it returns them instead of the next free person."""
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        r = report_row(c, rid)
        who = c.execute('SELECT * FROM responders WHERE id=?', (t.responder_id,)).fetchone()
        if not who:
            raise HTTPException(404, 'Responder not found')
        cid = call_of(r)
        if cid:
            c.execute('DELETE FROM routings WHERE call_id=?', (cid,))
            c.execute('INSERT INTO routings VALUES(?,?,?)', (cid, who['id'], time.time()))
        c.execute("UPDATE responders SET status='busy' WHERE id=?", (who['id'],))
        c.execute('UPDATE reports SET claimed_by=? WHERE id=?', (who['id'], rid))
        log(c, r, f"{who['name']} took this call" + ('' if cid else ' (no live call attached)'))
    return {'ok': True}


class Merge(BaseModel):
    into: str = Field(min_length=1, max_length=100)


@app.post('/api/reports/{rid}/merge')
def merge_reports(rid: str, m: Merge):
    """Link a duplicate to another incident. Both reports stay listed; only the incident grouping changes."""
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        r, target = report_row(c, rid), report_row(c, m.into)
        c.execute('UPDATE reports SET cluster_id=? WHERE id=?', (target['cluster_id'], rid))
        log(c, r, f"Linked by an operator to the incident at {target['location']}")
    return {'ok': True}


@app.post('/api/reports/{rid}/unmerge')
def unmerge_report(rid: str):
    with connect() as c:
        r = report_row(c, rid)
        c.execute('UPDATE reports SET cluster_id=? WHERE id=?', (str(uuid.uuid4()), rid))
        log(c, r, 'Unlinked by an operator: now its own incident')
    return {'ok': True}


@app.post('/api/reports/{rid}/callback')
def queue_callback(rid: str):
    with connect() as c:
        r = report_row(c, rid)
        cid = call_of(r)
        last = c.execute('SELECT caller_last4 FROM calls WHERE call_id=?', (cid,)).fetchone() if cid else None
        code = f'D-{uuid.uuid4().int % 9000 + 1000}'
        now = time.time()
        c.execute('INSERT INTO cases VALUES(?,?,?,?,?,?,?,?,?)', (code, 'callback', 'queued', 'operator', cid, last['caller_last4'] if last else '',
                                                                  json.dumps({'report_id': rid}), now, now))
        log(c, r, f'Callback {code} queued by an operator')
    return {'ok': True, 'code': code}


class Zone(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: str = Field(default='note', pattern='^(evacuation_order|evacuation_warning|hazard|staging|note)$')
    points: list[list[float]] = Field(min_length=3, max_length=200)
    by: str = Field(default='operator', max_length=100)


@app.get('/api/zones')
def list_zones():
    with connect() as c:
        return {'zones': [{**dict(z), 'points': json.loads(z['points'])} for z in c.execute('SELECT * FROM zones ORDER BY created')]}


@app.post('/api/zones')
def add_zone(z: Zone):
    if any(len(p) != 2 or not (-90 <= p[0] <= 90 and -180 <= p[1] <= 180) for p in z.points):
        raise HTTPException(400, 'Each point is [lat, lon]')
    zid = str(uuid.uuid4())
    with connect() as c:
        c.execute('INSERT INTO zones VALUES(?,?,?,?,?,?)', (zid, z.name, z.kind, json.dumps(z.points), time.time(), z.by))
        event(c, zid, f"Zone drawn by {z.by}: {z.name} ({z.kind.replace('_', ' ')})")
    return {'ok': True, 'id': zid}


@app.post('/api/zones/{zid}/delete')
def delete_zone(zid: str):
    with connect() as c:
        z = c.execute('SELECT name FROM zones WHERE id=?', (zid,)).fetchone()
        if not z:
            raise HTTPException(404, 'Zone not found')
        c.execute('DELETE FROM zones WHERE id=?', (zid,))
        event(c, zid, f"Zone removed: {z['name']}")
    return {'ok': True}


# --- Demo (drill mode only): a freeway pile-up and elderly falls across LA, plus other kinds of calls. Fictional callers;
# real intersections, no real facilities named. Any kind of report works on the live line; this is only sample data.
# (minutes ago, location, lat, lon, category, danger flag, summary, caller's words, language, last4, relationship, gps ±m, transferred)
CRASH = '110 Fwy northbound at Exposition Blvd'
CRISIS = [
    (14, '1st St and Soto St, Boyle Heights', 34.0446, -118.2096, 'medical', False, 'Mother, 84, fell in the bathroom', "My mother is 84, she fell in the bathroom and she can't get up. She's breathing but in a lot of pain.", 'en', '0555', 'on_scene', None, False),
    (13, 'Hill St and College St, Chinatown', 34.0657, -118.2386, 'welfare_check', False, 'Grandfather may need a check', '我爷爷摔倒了，起不来。他一个人住。', 'zh', '0288', 'third_party', None, False),
    (12, CRASH, 34.0187, -118.2803, 'medical', False, 'Multi-car crash, people hurt', 'Big crash on the 110 at Exposition, at least four cars, people are hurt.', 'en', '0142', 'on_scene', None, False),
    (11, CRASH, 34.0190, -118.2800, 'medical', False, 'Crash on the 110, woman injured', 'Choque grande en la 110, hay una señora atrapada en su carro y está sangrando.', 'es', '0921', 'on_scene', None, False),
    (11, CRASH, 34.0184, -118.2806, 'medical', False, 'Crash seen from the freeway', 'My husband just called, he saw a crash on the 110 by USC, he says it looks bad.', 'en', '0377', 'third_party', None, False),
    (10, CRASH, 34.0189, -118.2798, 'medical', False, 'Many injured in freeway crash', '110번 고속도로에서 큰 사고가 났어요. 사람들이 다쳤어요.', 'ko', '0733', 'on_scene', None, False),
    (9, CRASH, 34.0186, -118.2801, 'medical', True, 'Driver stuck in car, smells gasoline', "I'm stuck in my car on the 110, the door won't open and I smell gasoline.", 'en', '0610', 'on_scene', 8, True),
    (8, 'Exposition Blvd and Figueroa St', None, None, 'infrastructure', False, 'Traffic backed up after the freeway crash', 'Traffic is stopped on Exposition, there was an accident up on the freeway.', 'en', '0964', 'third_party', None, False),
    (7, 'Fairfax Ave and Santa Monica Blvd', 34.0905, -118.3614, 'medical', False, 'Neighbor fell and is unconscious', 'Мой сосед упал и он без сознания.', 'ru', '0347', 'on_scene', None, False),
    (6, 'Adams Blvd and Normandie Ave, West Adams', 34.0330, -118.3003, 'medical', False, 'Grandmother fell in the kitchen', 'Mi abuela se cayó en la cocina y no se puede levantar.', 'es', '0802', 'on_scene', None, False),
    (5, 'Western Ave and 6th St, Koreatown', 34.0637, -118.3089, 'other', False, 'Grandmother needs help at home', '할머니가 넘어졌어요. 혼자 일어나지 못하세요.', 'ko', '0419', 'on_scene', None, False),
    (5, 'Crenshaw Blvd and Jefferson Blvd', 34.0255, -118.3354, 'power', False, 'Power out; neighbor on home oxygen', "The power's been out for an hour and my neighbor uses an oxygen machine.", 'en', '0517', 'third_party', None, False),
    (4, None, None, None, 'other', True, "P0 flagged by phone agent: father fell down the stairs", "My dad fell down the stairs and he's not responding.", 'en', '0111', 'on_scene', None, False),
    (3, 'Sunset Blvd and Vermont Ave', 34.0977, -118.2917, 'gas', False, 'Gas smell in apartment hallway', 'I smell gas in the hallway of my building. My neighbor is elderly and lives alone.', 'en', '0628', 'on_scene', None, False),
    (2, 'Wilshire Blvd and Westwood Blvd', 34.0590, -118.4440, 'info', False, 'Asked for a ride to dialysis', 'Can my mom get a ride to her dialysis appointment tomorrow?', 'en', '0195', 'on_scene', None, False),
    (1, 'Santa Monica', 34.0195, -118.4912, 'info', False, 'Asked for a cooling center for seniors', '¿Hay un centro de enfriamiento abierto para personas mayores en Santa Monica?', 'es', '0234', 'on_scene', None, False),
]
AGENT_LINE = {'en': 'DIZA here. What is happening and where are you?', 'es': 'Habla DIZA. ¿Qué está pasando y dónde está?', 'ko': 'DIZA입니다. 무슨 일이고 어디에 계세요?',
              'zh': '这里是 DIZA。发生了什么, 您在哪里?', 'vi': 'Đây là DIZA. Chuyện gì đang xảy ra và bạn ở đâu?', 'ru': 'Это DIZA. Что случилось и где вы?'}


def seed_crisis(c):
    now = time.time()
    tag = f'crisis-{int(now)}'
    mate = c.execute("SELECT name FROM responders ORDER BY id LIMIT 1").fetchone()
    made = []
    for i, (mins, loc, lat, lon, cat, danger, summary, quote, lang, l4, rel, gps, moved) in enumerate(CRISIS):
        cid = f'{tag}-{i}'
        started = now - mins * 60 - 50
        transcript = f"Agent: {AGENT_LINE.get(lang, AGENT_LINE['en'])}\nUser: {quote}"
        c.execute('INSERT OR REPLACE INTO calls(call_id,direction,agent,caller_last4,status,started,ended,duration_s,summary,updated,transcript) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                  (cid, 'inbound', 'inbound' if lang == 'en' else f'inbound_{lang}', l4, 'live' if mins <= 2 else 'ended', started,
                   None if mins <= 2 else started + 95, None if mins <= 2 else 95, summary, now, transcript))
        key = f'{cid}:p0:demo' if loc is None else f'{cid}:demo'
        made.append((key, mins, loc, lat, lon, cat, danger, summary, quote, lang, cid, rel, gps, moved))
    # save_report runs the real rules (severity, grouping, requests) outside this transaction's lock order, so commit first.
    c.commit()
    placed = []
    for key, mins, loc, lat, lon, cat, danger, summary, quote, lang, cid, rel, gps, moved in made:
        r = save_report(Report(idempotency_key=key, location_text=loc or f'{PLACEHOLDER} · call {cid[-6:]})', hazard=cat, summary=summary, evidence=quote,
                               language=lang, immediate_danger=danger, source='demo', needs_assistance=cat == 'medical'))
        placed.append((r['id'], mins, lat, lon, gps, cid, rel, moved))
    with connect() as c2:
        # Backdate only after every report is in, so the real 10-minute duplicate grouping sees them together.
        for rid, mins, lat, lon, gps, cid, rel, moved in placed:
            c2.execute('UPDATE reports SET created=?,lat=?,lon=?,gps_accuracy=?,geo_tried=1 WHERE id=?', (now - mins * 60, lat, lon, gps, rid))
            c2.execute('INSERT OR REPLACE INTO incident_fields VALUES(?,?,?,?)', (cid, 'relationship', rel, now))
            if moved and mate:
                event(c2, cid, f"Warm transfer to {mate['name']} (P0) · you match medical")
        c2.execute('INSERT INTO zones VALUES(?,?,?,?,?,?)', (str(uuid.uuid4()), 'Crash scene: 110 Fwy closed northbound at Exposition (demo)', 'hazard',
                                                             json.dumps([[34.0225, -118.2830], [34.0225, -118.2775], [34.0150, -118.2775], [34.0150, -118.2830]]), now, 'demo'))
        for x in range(4):  # questions answered from verified info, no operator involved
            c2.execute('INSERT OR REPLACE INTO calls(call_id,direction,agent,caller_last4,status,started,ended,duration_s,summary,updated) VALUES(?,?,?,?,?,?,?,?,?,?)',
                       (f'{tag}-info-{x}', 'inbound', 'inbound', f'02{x}{x}', 'ended', now - (20 - x * 3) * 60, now - (20 - x * 3) * 60 + 60, 60,
                        'Caller asked about road closures and senior services; answered from verified information.', now))
    return len(made)


app.include_router(router)
