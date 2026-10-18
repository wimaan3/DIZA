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
        if not c.execute("INSERT OR IGNORE INTO assignment_calls VALUES(?,?,?,?,?)", (attempt, qid, who, 'claimed', time.time())).rowcount:
            return  # this offer was already called
        person = c.execute('SELECT r.name,p.phone FROM responders r LEFT JOIN responder_phones p ON p.responder_id=r.id WHERE r.id=?', (who,)).fetchone()
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


@router.post('/retell/fn/respond_assignment')
def respond_assignment(p=Depends(parse)):
    call, args = p
    qid, decision = str(args.get('assignment_id') or ''), args.get('decision')

    def make():
        with connect() as c:
            c.execute('BEGIN IMMEDIATE')
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
