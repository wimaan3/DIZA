"""Assignments by phone: when a request is offered to a teammate who has a phone, DIZA calls them.

The call (agent `assignment_brief`) reads the request and asks "Can you take it?". A yes accepts it on the dashboard;
a no declines it, which offers it to their backup, who is called in turn. Only the number DIZA dialled can answer
for the assignment. While the phone rings, the offer stays open longer than the inbox's 30 s.
Nothing here dials 911 or anyone outside DIZA_RESPONDERS.
"""
import json, os, threading, time
from fastapi import APIRouter, Depends
from .main import DEMO, ROOT, backup_of, connect, event, offer
from .retell_fns import e164, once, parse
from .alerts import retell_post

router = APIRouter()
HOLD = int(os.getenv('ASSIGN_CALL_SECONDS', '120'))
URGENCY = {'P0': 'Life-threatening', 'P1': 'Urgent', 'P2': 'Needs a person soon', 'P3': 'Routine'}
LANG = {'en': 'English', 'es': 'Spanish', 'ko': 'Korean', 'zh': 'Chinese', 'vi': 'Vietnamese', 'ru': 'Russian', 'hy': 'Armenian', 'fa': 'Persian', 'tl': 'Tagalog'}


def init_assign():
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS assignment_calls(attempt_id TEXT PRIMARY KEY,request_id TEXT,responder_id TEXT,status TEXT,created REAL)')
        try: c.execute('ALTER TABLE assignment_calls ADD COLUMN phone TEXT')  # the number dialled: only it may answer
        except Exception: pass


def agent_id():
    if os.getenv('RETELL_ASSIGN_AGENT_ID'):
        return os.environ['RETELL_ASSIGN_AGENT_ID']
    try:
        return json.loads((ROOT.parents[2] / 'agents' / 'retell.ids.json').read_text()).get('assignment_brief', {}).get('agent_id', '')
    except Exception:
        return ''


def briefing(r):
    where = 'location not given yet' if (r['location'] or '').startswith('(') else r['location']
    lang = LANG.get(r['language'], r['language'] or 'English')
    return f"{URGENCY.get(r['severity'], 'A')} request: {r['category'].replace('_', ' ')} at {where}. {r['summary'][:200].rstrip('.')}. The caller speaks {lang}."


def start_call(qid, who):
    """Called by offer() inside its transaction: wait for the commit, then phone `who` in the background."""
    threading.Thread(target=_call_when_committed, args=(qid, who), daemon=True).start()


def _call_when_committed(qid, who):
    for _ in range(25):  # offer() commits right after it returns; wait for THIS person's offer (an older one may still be visible)
        with connect() as c:
            row = c.execute("SELECT a.id attempt,a.responder_id who FROM attempts a JOIN requests q ON q.id=a.request_id "
                            "WHERE a.request_id=? AND a.responder_id=? AND a.status='offered' AND q.status='offered' AND q.assignee=?",
                            (qid, who, who)).fetchone()
        if row:
            break
        time.sleep(0.2)
    else:
        return
    try:
        call_assignee(qid, row['attempt'], row['who'])
    except Exception as e:  # never let a phone problem break the dashboard's offer
        print('assignment call failed:', e, flush=True)


def call_assignee(qid, attempt, who):
    with connect() as c:
        person = c.execute('SELECT r.name,p.phone FROM responders r LEFT JOIN responder_phones p ON p.responder_id=r.id WHERE r.id=?', (who,)).fetchone()
        if not c.execute("INSERT OR IGNORE INTO assignment_calls(attempt_id,request_id,responder_id,status,created,phone) VALUES(?,?,?,?,?,?)",
                         (attempt, qid, who, 'claimed', time.time(), person['phone'] if person else None)).rowcount:
            return  # this offer was already called
        rep = c.execute('SELECT r.* FROM reports r JOIN requests q ON q.report_id=r.id WHERE q.id=?', (qid,)).fetchone()
        if not person or not person['phone']:
            return  # local placeholder teammates have no phone: the inbox is enough
        agent = agent_id()
        if not (os.getenv('RETELL_API_KEY') and os.getenv('RETELL_FROM_NUMBER') and agent):
            event(c, qid, f"Not calling {person['name']}: assignment calls aren't set up yet (push the assignment_brief agent)")
            return
        # A phone call takes longer than the inbox's acceptance window: keep the offer open while it rings.
        c.execute("UPDATE attempts SET expires=MAX(expires,?) WHERE id=?", (time.time() + HOLD, attempt))
    try:  # outside the DB connection: a slow Retell API must not hold a SQLite lock
        placed = retell_post('/v2/create-phone-call', {
            'from_number': os.environ['RETELL_FROM_NUMBER'], 'to_number': person['phone'], 'override_agent_id': agent,
            'retell_llm_dynamic_variables': {'responder_name': person['name'].split(' ')[0], 'briefing': briefing(rep), 'severity': rep['severity'],
                                             'assignment_id': qid, 'drill_prefix': 'This is a drill. ' if DEMO else ''},
            'metadata': {'purpose': 'assignment', 'request_id': qid}})
    except Exception as e:
        with connect() as c:
            c.execute("UPDATE assignment_calls SET status='failed' WHERE attempt_id=?", (attempt,))
            event(c, qid, f"Call to {person['name']} about this request failed ({type(e).__name__}); it's still in their inbox")
        return
    with connect() as c:
        c.execute("UPDATE assignment_calls SET status='calling' WHERE attempt_id=?", (attempt,))
        event(c, qid, f"DIZA is calling {person['name']} about this request" + (f" (call {placed.get('call_id', '')[-6:]})" if placed.get('call_id') else ''))


# --- Building tickets: assigning a ticket to staff phones them -------------------------------------------------
def start_ticket_call(code, staff_id):
    threading.Thread(target=_ticket_call, args=(code, staff_id), daemon=True).start()


def _ticket_call(code, staff_id):
    try:
        call_for_ticket(code, staff_id)
    except Exception as e:
        print('ticket call failed:', e, flush=True)


def stand_in(c):
    """Drill mode: demo vendors have no real phone, so an available teammate takes the call as their stand-in."""
    from .team import on_duty, profiles
    profs = profiles(c)
    for r in c.execute("SELECT r.id,r.name,p.phone FROM responders r JOIN responder_phones p ON p.responder_id=r.id WHERE r.status='available' ORDER BY r.id"):
        if on_duty(profs.get(r['id'], {}).get('hours')):
            return r
    return None


def call_for_ticket(code, staff_id):
    from .building import tlog
    with connect() as c:
        t = c.execute('SELECT t.*,b.name building FROM tickets t JOIN buildings b ON b.id=t.building_id WHERE t.code=?', (code,)).fetchone()
        s = c.execute('SELECT * FROM staff_vendors WHERE id=?', (staff_id,)).fetchone()
        if not t or not s:
            return
        phone, name, why = s['phone'], s['name'].split(' (')[0], ''
        if not phone and DEMO:
            mate = stand_in(c)
            if mate:
                phone, name, why = mate['phone'], mate['name'].split(' ')[0], f" (drill stand-in for {s['name']})"
        if not phone:
            tlog(c, code, 'call', f"{s['name']} has no phone on file (DIZA_STAFF): not called")
            return
        agent = agent_id()
        if not (os.getenv('RETELL_API_KEY') and os.getenv('RETELL_FROM_NUMBER') and agent):
            tlog(c, code, 'call', f"Not calling {s['name']}: assignment calls aren't set up yet")
            return
        key = f'{code}:{staff_id}:{int(time.time())}'
        c.execute('INSERT OR IGNORE INTO assignment_calls(attempt_id,request_id,responder_id,status,created,phone) VALUES(?,?,?,?,?,?)',
                  (key, code, staff_id, 'calling', time.time(), phone))
    where = t['unit'] if t['unit'].startswith('(') else f"unit {t['unit']}"
    brief = (f"{t['urgency'].capitalize()} ticket {' '.join(t['code'])}: {t['category'].replace('_', ' ')} in {where} at {t['building'].replace(' (demo)', '')}. "
             f"{(t['summary'] or '')[:160].rstrip('.')}.")
    try:
        retell_post('/v2/create-phone-call', {
            'from_number': os.environ['RETELL_FROM_NUMBER'], 'to_number': phone, 'override_agent_id': agent,
            'retell_llm_dynamic_variables': {'responder_name': name, 'briefing': brief, 'severity': 'P1' if t['urgency'] == 'emergency' else 'P2',
                                             'assignment_id': code, 'drill_prefix': 'This is a drill. ' if DEMO else ''},
            'metadata': {'purpose': 'ticket_assignment', 'ticket': code}})
    except Exception as e:
        with connect() as c:
            tlog(c, code, 'call', f"Call to {s['name']}{why} failed ({type(e).__name__})")
        return
    with connect() as c:
        tlog(c, code, 'call', f"DIZA is calling {name}{why} about this ticket")


def respond_ticket(c, code, decision, dialled):
    from .building import tlog
    row = c.execute("SELECT * FROM assignment_calls WHERE request_id=? ORDER BY created DESC LIMIT 1", (code,)).fetchone()
    t = c.execute('SELECT * FROM tickets WHERE code=?', (code,)).fetchone()
    if not row or not t or e164(row['phone'] or '') != e164(dialled):
        return {'ok': False, 'message': 'This ticket is no longer assigned to you.'}
    if t['assignee'] != row['responder_id'] or t['status'] == 'closed':
        return {'ok': False, 'message': 'This ticket was already handled.'}
    who = c.execute('SELECT name FROM staff_vendors WHERE id=?', (row['responder_id'],)).fetchone()['name']
    if decision == 'accept':
        c.execute("UPDATE tickets SET status='in_progress',updated=?,first_human_action_at=COALESCE(first_human_action_at,?) WHERE code=?", (time.time(), time.time(), code))
        tlog(c, code, 'status', f'{who} accepted by phone: in progress')
    else:
        c.execute("UPDATE tickets SET status='new',assignee=NULL,updated=? WHERE code=?", (time.time(), code))
        tlog(c, code, 'assign', f'{who} declined by phone: needs someone else')
    c.execute("UPDATE assignment_calls SET status=? WHERE attempt_id=?", ('accepted' if decision == 'accept' else 'declined', row['attempt_id']))
    return {'ok': True}


# --- Callbacks: the teammate gets a call with the caller's number ------------------------------------------------
def caller_number(call_id):
    """The caller's full number, fetched from Retell when needed. The dashboard keeps only the last 4 digits."""
    import urllib.request
    from .retell_fns import person_number
    req = urllib.request.Request(f'https://api.retellai.com/v2/get-call/{call_id}', headers={'Authorization': 'Bearer ' + os.environ['RETELL_API_KEY']})
    with urllib.request.urlopen(req, timeout=10) as r:
        return person_number(json.loads(r.read()))


def spoken_number(n):
    d = ''.join(ch for ch in n if ch.isdigit())[-10:]
    return f"{' '.join(d[:3])}, {' '.join(d[3:6])}, {' '.join(d[6:])}" if len(d) == 10 else ' '.join(d)


def start_callback(code, rid, who):
    threading.Thread(target=_callback, args=(code, rid, who), daemon=True).start()


def _callback(code, rid, who):
    try:
        call_for_callback(code, rid, who)
    except Exception as e:
        print('callback call failed:', e, flush=True)


def call_for_callback(code, rid, who):
    with connect() as c:
        r = c.execute('SELECT * FROM reports WHERE id=?', (rid,)).fetchone()
        person = c.execute('SELECT r.name,p.phone FROM responders r LEFT JOIN responder_phones p ON p.responder_id=r.id WHERE r.id=?', (who,)).fetchone()
        q = c.execute('SELECT id FROM requests WHERE report_id=?', (rid,)).fetchone()
        key = q['id'] if q else rid
        if not r or not person or not person['phone']:
            event(c, key, f"Callback {code}: {person['name'] if person else 'that teammate'} has no phone on file, so it stays queued")
            return
        agent = agent_id()
        if not (os.getenv('RETELL_API_KEY') and os.getenv('RETELL_FROM_NUMBER') and agent):
            event(c, key, f"Callback {code}: calls aren't set up yet, so it stays queued")
            return
    cid = r['dedupe'].split(':')[0]
    try:
        number = caller_number(cid)
    except Exception:
        number = ''
    if not number:
        with connect() as c:
            event(c, key, f"Callback {code}: the caller's number isn't available from Retell, so it stays queued")
        return
    where = 'location not given yet' if (r['location'] or '').startswith('(') else r['location']
    brief = (f"Please call back a caller about a {URGENCY.get(r['severity'], '').lower()} {r['category'].replace('_', ' ')} report at {where}. "
             f"Their number is {spoken_number(number)}. Again: {spoken_number(number)}.")
    with connect() as c:
        c.execute('INSERT OR IGNORE INTO assignment_calls(attempt_id,request_id,responder_id,status,created,phone) VALUES(?,?,?,?,?,?)',
                  (f'{code}:{who}', code, who, 'calling', time.time(), person['phone']))
    try:
        retell_post('/v2/create-phone-call', {
            'from_number': os.environ['RETELL_FROM_NUMBER'], 'to_number': person['phone'], 'override_agent_id': agent,
            'retell_llm_dynamic_variables': {'responder_name': person['name'].split(' ')[0], 'briefing': brief, 'severity': r['severity'],
                                             'assignment_id': code, 'drill_prefix': 'This is a drill. ' if DEMO else ''},
            'metadata': {'purpose': 'callback', 'case': code}})
    except Exception as e:
        with connect() as c:
            event(c, key, f"Callback {code}: call to {person['name']} failed ({type(e).__name__})")
        return
    with connect() as c:
        event(c, key, f"DIZA is calling {person['name']} with the caller's number for callback {code}")


@router.post('/retell/fn/respond_assignment')
def respond_assignment(p=Depends(parse)):
    call, args = p
    qid, decision = str(args.get('assignment_id') or ''), args.get('decision')

    def make():
        with connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if qid.startswith('T-') and decision in ('accept', 'decline'):  # a building ticket assigned to staff
                return respond_ticket(c, qid, decision, call.get('to_number', ''))
            if qid.startswith('D-') and decision in ('accept', 'decline'):  # a callback: the teammate calls the caller back
                row = c.execute('SELECT * FROM assignment_calls WHERE request_id=? ORDER BY created DESC LIMIT 1', (qid,)).fetchone()
                if not row or e164(row['phone'] or '') != e164(call.get('to_number', '')):
                    return {'ok': False, 'message': 'This callback is no longer assigned to you.'}
                who = c.execute('SELECT name FROM responders WHERE id=?', (row['responder_id'],)).fetchone()['name']
                c.execute('UPDATE cases SET status=?,updated=? WHERE code=?', ('in_progress' if decision == 'accept' else 'queued', time.time(), qid))
                event(c, qid, f"{who} {'is calling the caller back' if decision == 'accept' else 'declined the callback; it stays queued'}")
                return {'ok': True}
            q = c.execute('SELECT * FROM requests WHERE id=?', (qid,)).fetchone()
            if not q or decision not in ('accept', 'decline'):
                return {'ok': False, 'message': "I couldn't find that request; it's on the DIZA dashboard."}
            phone = c.execute('SELECT phone FROM responder_phones WHERE responder_id=?', (q['assignee'],)).fetchone() if q['assignee'] else None
            # Only the person DIZA called may answer for the assignment: the number we dialled must be the assignee's.
            if not phone or e164(phone['phone']) != e164(call.get('to_number', '')):
                return {'ok': False, 'message': 'This request is no longer assigned to you.'}
            a = c.execute("SELECT * FROM attempts WHERE request_id=? AND responder_id=? AND status='offered'", (qid, q['assignee'])).fetchone()
            if q['status'] != 'offered' or not a:
                return {'ok': False, 'message': 'This request was already handled.'}
            who = c.execute('SELECT name FROM responders WHERE id=?', (q['assignee'],)).fetchone()['name']
            accepted = decision == 'accept'
            c.execute('UPDATE attempts SET status=? WHERE id=?', ('accepted' if accepted else 'declined', a['id']))
            c.execute('UPDATE responders SET status=? WHERE id=?', ('busy' if accepted else 'available', q['assignee']))
            c.execute('UPDATE requests SET status=?,assignee=?,updated=? WHERE id=?', ('accepted' if accepted else 'new', q['assignee'] if accepted else None, time.time(), qid))
            c.execute("UPDATE assignment_calls SET status=? WHERE attempt_id=?", ('accepted' if accepted else 'declined', a['id']))
            event(c, qid, f'{who} accepted responsibility by phone' if accepted else f'{who} declined by phone · trying their backup')
            if not accepted:
                offer(c, qid, prefer=backup_of(c, q['assignee']))
        return {'ok': True}
    return once('respond_assignment', call, args, make)
