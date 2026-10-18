"""Security routing: DIZA phones the on-duty security person with a short spoken briefing.

Two ways in, one briefing per call at most:
- the crisis agent and the language lines call `brief_security` for break-ins, theft, vandalism, threats or a
  suspicious person;
- any agent's `route_to_human` with the need `security` briefs security too (see `brief_after_routing`), so the
  inbound agent needs no extra tool.
A danger that is happening now still gets "call 911" first; the briefing is extra, never a replacement, and the
caller is never told that security is coming.

On duty = an available DIZA_RESPONDERS teammate whose skills include `security`. In drill mode any other available
teammate stands in; outside drill mode a building's security staff phone (DIZA_STAFF) is the fallback.
Env: RETELL_API_KEY, RETELL_FROM_NUMBER, RETELL_SECURITY_AGENT_ID (defaults to the agent in agents/retell.ids.json).
"""
import os, threading, time
from datetime import datetime
from fastapi import APIRouter, Depends
from .alerts import retell_post
from .building import TZ, building_for, tlog
from .main import DEMO, connect, event
from .retell_fns import last4, once, parse

router = APIRouter(prefix='/retell/fn')
SECURITY_AGENT_ID = 'agent_49bc7a7e9e4f23405a83ec5d07'  # security_brief in agents/retell.ids.json


def init_security():
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS security_briefs(call_id TEXT PRIMARY KEY,security_name TEXT,status TEXT,created REAL)')


def on_duty_security(c, call, exclude=()):
    """(name, phone, why) of the person to brief, or None. Never a police or 911 number."""
    rows = [r for r in c.execute("SELECT r.id,r.name,r.skills,p.phone FROM responders r JOIN responder_phones p ON p.responder_id=r.id "
                                 "WHERE r.status='available' ORDER BY r.id").fetchall() if r['id'] not in exclude]
    for r in rows:
        if 'security' in (r['skills'] or '').lower().split(','):
            return r['name'], r['phone'], 'on-duty security'
    if DEMO:
        return (f"{rows[0]['name']} (drill stand-in for security)", rows[0]['phone'], 'drill stand-in') if rows else None
    b = building_for(c, call)
    s = c.execute("SELECT name,phone FROM staff_vendors WHERE building_id=? AND role='security' AND phone!='' ORDER BY id LIMIT 1",
                  (b['id'],)).fetchone() if b else None
    return (s['name'], s['phone'], 'building security') if s else None


def briefing_text(args, call):
    when = 'happening now' if args.get('in_progress') else 'already happened'
    parts = [f"{args.get('incident') or 'A security report'} ({when})"]
    if args.get('location_text'):
        parts.append(f"Location: {args['location_text']}")
    if args.get('caller_quote'):
        parts.append(f"The caller said: \"{args['caller_quote']}\"")
    parts.append(f"Caller's number ends in {' '.join(last4(call) or '----')}")
    return '. '.join(p.rstrip('.') for p in parts)[:600] + '.'


def place_briefing(call, args, exclude=()):
    """Claim this call's one briefing, pick who is on duty and phone them. Returns the function's response."""
    with connect() as c:
        if c.execute('INSERT OR IGNORE INTO security_briefs VALUES(?,?,?,?)', (call['call_id'], '', 'claimed', time.time())).rowcount == 0:
            prior = c.execute('SELECT security_name,status FROM security_briefs WHERE call_id=?', (call['call_id'],)).fetchone()
            return {'status': prior['status'] if prior['status'] != 'claimed' else 'calling', 'security_name': prior['security_name']}
        who = on_duty_security(c, call, exclude)
        if not who:
            c.execute("UPDATE security_briefs SET status='no_security_on_duty' WHERE call_id=?", (call['call_id'],))
            event(c, call['call_id'], 'No security on duty to brief · callback offered')
            return {'status': 'no_security_on_duty', 'security_name': ''}
    name, phone, why = who
    short = name.split(' (')[0]
    stamp = datetime.now(TZ).strftime('%H:%M')
    try:  # outside the DB connection: a slow Retell API must not hold a SQLite lock
        placed = retell_post('/v2/create-phone-call', {
            'from_number': os.environ['RETELL_FROM_NUMBER'], 'to_number': phone,
            'override_agent_id': os.getenv('RETELL_SECURITY_AGENT_ID', SECURITY_AGENT_ID),
            'retell_llm_dynamic_variables': {
                'security_name': short, 'briefing': briefing_text(args, call),
                'in_progress': 'true' if args.get('in_progress') else 'false',
                'drill_prefix': 'This is a drill. ' if DEMO else ''},
            'metadata': {'purpose': 'security_brief', 'source_call_id': call['call_id']}})
    except Exception as e:  # Retell down or misconfigured: the caller still gets a person or a callback
        with connect() as c:
            c.execute("UPDATE security_briefs SET status='failed' WHERE call_id=?", (call['call_id'],))
            event(c, call['call_id'], f'Security briefing call to {name} failed ({type(e).__name__}), {stamp}')
        return {'status': 'failed', 'security_name': ''}
    with connect() as c:
        c.execute("UPDATE security_briefs SET status='calling',security_name=? WHERE call_id=?", (short, call['call_id']))
        event(c, call['call_id'], f"DIZA is calling {name} ({why}) with a security briefing, {stamp}")
        t = c.execute("SELECT code FROM tickets WHERE reporters LIKE ? ORDER BY created DESC LIMIT 1",
                      (f'%"{call["call_id"]}"%',)).fetchone()
        if t:
            tlog(c, t['code'], 'security', f'Security briefing call to {name}, {stamp}')
    return {'status': 'calling', 'security_name': short, 'briefing_call_id': placed.get('call_id', '')}


@router.post('/brief_security')
def brief_security(p=Depends(parse)):
    call, args = p
    return once('brief_security', call, args, lambda: place_briefing(call, args))


def brief_after_routing(call, args, routed):
    """route_to_human with the need 'security': brief security in the background (route_to_human must answer fast).
    Skipped when the person taking the warm transfer is security themselves: the whisper already briefs them."""
    if 'security' not in [n.lower() for n in args.get('needs') or []]:
        return
    with connect() as c:
        row = c.execute('SELECT r.id,r.skills FROM routings g JOIN responders r ON r.id=g.responder_id WHERE g.call_id=? '
                        'ORDER BY g.created DESC LIMIT 1', (call['call_id'],)).fetchone()
    if row and routed.get('oncall_number') and 'security' in (row['skills'] or '').lower().split(','):
        return
    brief = {'incident': args.get('summary') or 'Security matter', 'in_progress': args.get('severity') in ('P0', 'P1')}
    threading.Thread(target=place_briefing, args=(call, brief, (row['id'],) if row else ()), daemon=True).start()
