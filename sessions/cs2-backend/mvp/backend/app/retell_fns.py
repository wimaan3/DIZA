"""Retell custom functions from 00_CONTRACTS.md, on the same SQLite store as main.py.

Every endpoint verifies X-Retell-Signature (via main.verified_body), reads Retell's default
{name, call, args} body, and is idempotent per call + arguments because Retell retries once.
Nothing here dials, texts or dispatches anyone: requests become cases a person must act on.
"""
import hashlib, json, os, random, re, time
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from . import resources
from .main import DEMO, ROOT, Report, app, connect, event, offer, save_report, verified_body

router = APIRouter(prefix='/retell/fn')
def forms_dir():
    return Path(os.getenv('FORMS_DIR', str(ROOT.parents[2] / 'agents' / 'forms')))
ETA = 'about 20 minutes'


def init_fns():
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS cases(code TEXT PRIMARY KEY,type TEXT,status TEXT,pool TEXT,call_id TEXT,caller_last4 TEXT,payload TEXT,created REAL,updated REAL);
        CREATE TABLE IF NOT EXISTS fn_results(key TEXT PRIMARY KEY,response TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS responder_phones(responder_id TEXT PRIMARY KEY,phone TEXT);
        CREATE TABLE IF NOT EXISTS routings(call_id TEXT,responder_id TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS consents(caller_hash TEXT PRIMARY KEY,do_not_call INTEGER DEFAULT 0,analytics INTEGER DEFAULT 1,feature INTEGER DEFAULT 0,updated REAL);
        CREATE TABLE IF NOT EXISTS kb_gaps(id INTEGER PRIMARY KEY AUTOINCREMENT,call_id TEXT,question TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS kb_items(id INTEGER PRIMARY KEY AUTOINCREMENT,question TEXT,answer TEXT,source TEXT,approved_by TEXT,created REAL);
        ''')
        # Real human-in-the-loop phones come from the environment only, never from git:
        # DIZA_RESPONDERS='[{"id":"imaan","name":"Imaan","phone":"+1...","skills":"evac_logistics,lang:en"}]'
        for r in json.loads(os.getenv('DIZA_RESPONDERS', '[]')):
            c.execute('INSERT OR REPLACE INTO responders VALUES(?,?,?,?)', (r['id'], r['name'], r.get('skills', 'general'), 'available'))
            c.execute('INSERT OR REPLACE INTO responder_phones VALUES(?,?)', (r['id'], r['phone']))


def release_call(call_id):
    if not call_id:
        return
    with connect() as c:
        for row in c.execute('SELECT responder_id FROM routings WHERE call_id=?', (call_id,)).fetchall():
            c.execute("UPDATE responders SET status='available' WHERE id=? AND status='busy'", (row['responder_id'],))
        c.execute('DELETE FROM routings WHERE call_id=?', (call_id,))


async def parse(req: Request):
    """Async dependency: read + verify the raw body. Handlers are plain functions, so FastAPI runs them in its
    thread pool and a slow geocode or SQLite lock never blocks the event loop for other live calls."""
    data = await verified_body(req)
    call = data.get('call') or {}
    if not call.get('call_id'):
        raise HTTPException(422, 'call.call_id required')
    return call, data.get('args') or {}


def once(name, call, args, make):
    """Run `make` once per (call, function, args); a Retell retry gets the stored answer."""
    key = hashlib.sha256(json.dumps([call['call_id'], name, args], sort_keys=True).encode()).hexdigest()
    with connect() as c:
        hit = c.execute('SELECT response FROM fn_results WHERE key=?', (key,)).fetchone()
    if hit:
        return json.loads(hit['response'])
    out = make()
    with connect() as c:
        c.execute('INSERT OR IGNORE INTO fn_results VALUES(?,?,?)', (key, json.dumps(out), time.time()))
    return out


def person_number(call):
    # On outbound calls (alerts, check-ins, welfare) from_number is our own line; the person is to_number.
    return (call.get('to_number') if call.get('direction') == 'outbound' else call.get('from_number')) or ''


def last4(call):
    return re.sub(r'\D', '', person_number(call))[-4:]


def caller_hash(call):
    return hashlib.sha256((person_number(call) or call['call_id']).encode()).hexdigest()


def new_case(call, type_, status, payload, pool='general_helper'):
    with connect() as c:
        for _ in range(50):
            code = f'D-{random.randint(100, 9999)}'
            if not c.execute('SELECT 1 FROM cases WHERE code=?', (code,)).fetchone():
                break
        now = time.time()
        c.execute('INSERT INTO cases VALUES(?,?,?,?,?,?,?,?,?)', (code, type_, status, pool, call['call_id'], last4(call), json.dumps(payload), now, now))
        event(c, code, f'{type_} case {code} created by phone agent · status {status} · no person has accepted it yet')
    return code


def simple(name, type_, status, pool, reply):
    def handler(p=Depends(parse)):
        call, args = p
        return once(name, call, args, lambda: reply(new_case(call, type_, status, args, pool), args))
    router.add_api_route(f'/{name}', handler, methods=['POST'], name=f'retell_{name}')


simple('create_request', 'request', 'new', 'general_helper',
       lambda code, a: {'code': code, 'pool': 'general_helper', 'eta_text': f'A person on our team will pick this up; expect a call in {ETA}.'})
simple('request_escort', 'escort', 'new', 'general_helper',
       lambda code, a: {'code': code, 'eta_text': 'An escort coordinator will call you to confirm.'})
simple('set_reminder', 'reminder', 'scheduled', 'general_helper',
       lambda code, a: {'code': code, 'scheduled_for': a.get('when', '')})
simple('book_appointment', 'appointment', 'pending_slot', 'general_helper',
       lambda code, a: {'code': code, 'slot': 'A coordinator will confirm a time from the ones you gave and call you back.'})
simple('schedule_callback', 'callback', 'queued', 'general_helper',
       lambda code, a: {'code': code, 'eta_text': ETA})
simple('enroll_checkin', 'checkin_enrollment', 'pending_consent', 'general_helper',
       lambda code, a: {'code': code, 'status': 'pending_consent'})
simple('register_volunteer', 'volunteer', 'pending_verification', 'general_helper',
       lambda code, a: {'code': code, 'status': 'pending_verification'})


@router.post('/notify_contact')
def notify_contact(p=Depends(parse)):
    call, args = p
    if args.get('consent') is not True:
        return {'code': '', 'status': 'consent_required'}
    # Queued for a person to send; this MVP has no outbound SMS.
    return once('notify_contact', call, args, lambda: {'code': new_case(call, 'notify_contact', 'queued', args), 'status': 'queued'})


@router.post('/flag_urgent')
def flag_urgent(p=Depends(parse)):
    call, args = p
    reason, keyword = args.get('reason', 'urgent'), args.get('keyword', '')

    def make():
        r = save_report(Report(idempotency_key=f"{call['call_id']}:p0:{reason}", location_text=f"(location not yet given · call {call['call_id'][-6:]})", hazard='other',
                               summary=f'P0 flagged by phone agent: {reason}', evidence=keyword[:2000], immediate_danger=True, source='retell'))
        with connect() as c:
            c.execute('BEGIN IMMEDIATE')
            q = c.execute('SELECT id FROM requests WHERE report_id=?', (r['id'],)).fetchone()
            if q:
                offer(c, q['id'])  # P0 → escalated to the supervisor, never offered to helpers
        if reason == 'self_harm':
            return {'instruction': 'Offer the 988 Suicide and Crisis Lifeline transfer now. If there is immediate danger, tell them to call 911. Never route to a volunteer.'}
        return {'instruction': 'Tell the caller to hang up and call 911 now. If they cannot, offer a person on our team. A supervisor has been alerted.'}
    return once('flag_urgent', call, args, make)


@router.post('/route_to_human')
def route_to_human(p=Depends(parse)):
    call, args = p
    needs = [n.lower() for n in args.get('needs') or []]
    lang = (args.get('language') or '').lower()
    wanted = set(needs) | ({f'lang:{lang}'} if lang else set())
    severity = args.get('severity', 'P2')

    def make():
        with connect() as c:
            c.execute('BEGIN IMMEDIATE')
            rows = c.execute("SELECT r.id,r.name,r.skills,p.phone FROM responders r JOIN responder_phones p ON p.responder_id=r.id WHERE r.status='available'").fetchall()
            best = None
            for r in rows:
                skills = set(r['skills'].lower().split(','))
                if severity in ('P0', 'P1') and 'volunteer' in skills:
                    continue  # never send urgent calls to unverified/general volunteers
                score = len(wanted & skills)
                if best is None or score > best[0]:
                    best = (score, r)
            if not best:
                event(c, call['call_id'], f'No responder with a phone available for {severity} call · callback offered')
                return {'oncall_number': '', 'responder_name': '', 'brief': '', 'match_reason': '', 'fallback': 'callback'}
            score, r = best
            c.execute("UPDATE responders SET status='busy' WHERE id=?", (r['id'],))
            c.execute('INSERT INTO routings VALUES(?,?,?)', (call['call_id'], r['id'], time.time()))
            matched = sorted(wanted & set(r['skills'].lower().split(',')))
            reason = 'you match ' + ', '.join(m.replace('lang:', 'language ') for m in matched) if matched else 'you were the first available person'
            event(c, call['call_id'], f"Warm transfer to {r['name']} ({severity}) · {reason}")
            return {'oncall_number': r['phone'], 'responder_name': r['name'], 'brief': (args.get('summary') or '')[:300], 'match_reason': reason}
    return once('route_to_human', call, args, make)


@router.post('/lookup_info')
def lookup_info(p=Depends(parse)):
    call, args = p
    question = (args.get('question') or '')[:500]
    with connect() as c:
        found = resources.lookup(c, question, args.get('location_text') or '', args.get('needs') or [], drill_mode=DEMO)
        if not found:
            c.execute('INSERT INTO kb_gaps(call_id,question,created) VALUES(?,?,?)', (call['call_id'], question, time.time()))
    # Unanswered questions are logged for a supervisor to answer once (POST /api/kb_items) for every later caller.
    return found or {'answer': '', 'gap_logged': True, 'resource_name': '', 'transfer_number': ''}


@router.post('/check_status')
def check_status(p=Depends(parse)):
    call, args = p
    code = (args.get('code') or '').upper().replace(' ', '')
    if code and not code.startswith('D-'):
        code = 'D-' + code.lstrip('D')
    with connect() as c:
        row = c.execute('SELECT * FROM cases WHERE code=?', (code,)).fetchone()
    if not row or (row['caller_last4'] and row['caller_last4'] != re.sub(r'\D', '', args.get('phone_last4') or '')):
        return {'status_text': "I couldn't find a request with that code and phone number."}
    words = {'new': 'received; a person on our team will pick it up soon', 'queued': 'queued for a callback', 'scheduled': 'scheduled',
             'pending_consent': 'waiting for the person to agree on their first call', 'pending_verification': 'waiting for a coordinator to verify you',
             'pending_slot': 'waiting for a coordinator to confirm a time', 'accepted': 'accepted by a person on our team', 'done': 'completed'}
    return {'status_text': f"Request {code} is {words.get(row['status'], row['status'])}."}


@router.post('/opt_out')
def opt_out(p=Depends(parse)):
    call, args = p
    scope = args.get('scope', 'calls')
    with connect() as c:
        c.execute('INSERT OR IGNORE INTO consents(caller_hash,updated) VALUES(?,?)', (caller_hash(call), time.time()))
        if scope in ('calls', 'all'):
            c.execute('UPDATE consents SET do_not_call=1,updated=? WHERE caller_hash=?', (time.time(), caller_hash(call)))
        if scope in ('analytics', 'all'):
            c.execute('UPDATE consents SET analytics=0,updated=? WHERE caller_hash=?', (time.time(), caller_hash(call)))
        event(c, call['call_id'], f'Caller opted out ({scope})' + (' · data deletion requested' if scope == 'all' else ''))
    return {'ok': True}


@router.post('/record_consent')
def record_consent(p=Depends(parse)):
    call, args = p
    with connect() as c:
        c.execute('INSERT OR IGNORE INTO consents(caller_hash,updated) VALUES(?,?)', (caller_hash(call), time.time()))
        if 'feature_consent' in args:
            c.execute('UPDATE consents SET feature=? WHERE caller_hash=?', (int(bool(args['feature_consent'])), caller_hash(call)))
        if 'analytics_consent' in args:
            c.execute('UPDATE consents SET analytics=? WHERE caller_hash=?', (int(bool(args['analytics_consent'])), caller_hash(call)))
    return {'ok': True}


@router.post('/send_link')
def send_link(p=Depends(parse)):
    # No SMS provider in this MVP; the agent tells the caller to use their code instead.
    return {'sent': False, 'spoken_short_url': ''}


# --- Forms loop (schemas in agents/forms/*.yaml) ---

def load_form(form_type):
    path = forms_dir() / f'{form_type}.yaml'
    if path.exists():
        import yaml
        return yaml.safe_load(path.read_text())
    return {'id': form_type, 'route_pool': 'general_helper', 'readback': '{details}', 'next_step_text': 'A person on our team will follow up.',
            'fields': [{'name': 'details', 'required': True, 'ask': 'Tell me what you need, in a sentence.'},
                       {'name': 'callback_phone', 'required': True, 'validate': 'phone', 'ask': "What's the best number to reach you?"}]}


def check_form(form, values):
    missing, invalid = [], []
    for f in form['fields']:
        v = str(values.get(f['name'], '')).strip()
        if not v:
            if f.get('required'):
                missing.append({'name': f['name'], 'ask': f.get('ask', f['name'])})
            continue
        rule = f.get('validate')
        if (rule == 'phone' and len(re.sub(r'\D', '', v)) < 10) or (rule == 'int' and not re.fullmatch(r'\d+', v)) \
                or (rule == 'enum' and v.lower() not in [str(x).lower() for x in f.get('choices', [])]):
            invalid.append({'name': f['name'], 'ask': f.get('ask', f['name']), 'expected': rule if rule != 'enum' else f.get('choices')})
    return missing, invalid


def readback(form, values):
    class Blank(dict):
        def __missing__(self, k): return 'not given'
    return form.get('readback', '').format_map(Blank({k: str(v) for k, v in values.items()}))


@router.post('/start_form')
def start_form(p=Depends(parse)):
    call, args = p

    def make():
        form = load_form(args.get('form_type', 'request'))
        values = {k: str(v) for k, v in (args.get('known_fields') or {}).items()}
        code = new_case(call, f"form:{form['id']}", 'draft', values, form.get('route_pool', 'general_helper'))
        missing, invalid = check_form(form, values)
        return {'case_code': code, 'next_fields': invalid + missing}
    return once('start_form', call, args, make)


@router.post('/fill_form')
def fill_form(p=Depends(parse)):
    call, args = p
    code = args.get('case_code', '')
    with connect() as c:
        row = c.execute('SELECT * FROM cases WHERE code=?', (code,)).fetchone()
        if not row or not row['type'].startswith('form:'):
            return {'missing': [], 'invalid': [{'name': 'case_code', 'ask': 'Restart the form with start_form.'}], 'complete': False, 'readback': ''}
        form = load_form(row['type'][5:])
        values = json.loads(row['payload'])
        values.update({k: str(v) for k, v in (args.get('fields') or {}).items()})
        c.execute('UPDATE cases SET payload=?,updated=? WHERE code=?', (json.dumps(values), time.time(), code))
    missing, invalid = check_form(form, values)
    done = not missing and not invalid
    return {'missing': missing, 'invalid': invalid, 'complete': done, 'readback': readback(form, values) if done else ''}


@router.post('/submit_form')
def submit_form(p=Depends(parse)):
    call, args = p
    code = args.get('case_code', '')
    with connect() as c:
        row = c.execute('SELECT * FROM cases WHERE code=?', (code,)).fetchone()
        if not row or not row['type'].startswith('form:'):
            return {'code': '', 'pool': '', 'status': 'not_found', 'next_step_text': "I couldn't find that form; let's start again."}
        form = load_form(row['type'][5:])
        missing, invalid = check_form(form, json.loads(row['payload']))
        if args.get('confirmed') is not True or missing or invalid:
            return {'code': code, 'pool': row['pool'], 'status': 'incomplete', 'next_step_text': 'Some details are still missing or need confirming.'}
        if row['status'] == 'draft':
            c.execute("UPDATE cases SET status='new',updated=? WHERE code=?", (time.time(), code))
            event(c, code, f"Form {form['id']} submitted by phone agent · waiting for a person in {row['pool']}")
    return {'code': code, 'pool': row['pool'], 'status': 'new', 'next_step_text': form.get('next_step_text', 'A person on our team will follow up.')}


# --- Supervisor: answer a logged question once; lookup_info then serves it to every caller ---

class KbItem(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    answer: str = Field(min_length=3, max_length=1000)
    source: str = Field(default='', max_length=300)
    approved_by: str = Field(min_length=1, max_length=100)
    gap_id: int | None = None


@app.post('/api/kb_items')
def approve_kb_item(item: KbItem):
    # Facts only: never caller-specific information (SYSTEM_SPEC 2.4). /api/* is behind OPS_API_TOKEN when set.
    with connect() as c:
        c.execute('INSERT INTO kb_items(question,answer,source,approved_by,created) VALUES(?,?,?,?,?)',
                  (item.question, item.answer, item.source, item.approved_by, time.time()))
        if item.gap_id is not None:
            c.execute('DELETE FROM kb_gaps WHERE id=?', (item.gap_id,))
    return {'ok': True}


@app.get('/api/kb')
def kb_state():
    with connect() as c:
        return {'gaps': [dict(r) for r in c.execute('SELECT id,question,created FROM kb_gaps ORDER BY created DESC LIMIT 100')],
                'items': [dict(r) for r in c.execute('SELECT * FROM kb_items ORDER BY created DESC')]}
