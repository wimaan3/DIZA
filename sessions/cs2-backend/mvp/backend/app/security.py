"""Security routing: DIZA phones the on-duty security person with a short spoken briefing.

The phone agent calls `brief_security` for break-ins, theft, vandalism, threats or a suspicious person. A danger that
is happening now still gets "call 911" first; the briefing is extra, never a replacement, and the caller is never told
that security is coming.

On duty = an available DIZA_RESPONDERS teammate whose skills include `security`. Outside drill mode, a building's
security staff phone (DIZA_STAFF) is the fallback. In drill mode only teammates are ever called.
Env: RETELL_API_KEY, RETELL_FROM_NUMBER, RETELL_SECURITY_AGENT_ID (defaults to the agent in agents/retell.ids.json).
"""
import os
from datetime import datetime
from fastapi import APIRouter, Depends
from .alerts import retell_post
from .building import TZ, building_for, drill_teammate, tlog
from .main import DEMO, connect, event
from .retell_fns import e164, last4, once, parse

router = APIRouter(prefix='/retell/fn')
SECURITY_AGENT_ID = 'agent_49bc7a7e9e4f23405a83ec5d07'  # security_brief in agents/retell.ids.json


def on_duty_security(c, call):
    """(name, phone, why) of the person to brief, or None. Never a police or 911 number."""
    rows = c.execute("SELECT r.name,r.skills,p.phone FROM responders r JOIN responder_phones p ON p.responder_id=r.id "
                     "WHERE r.status='available' ORDER BY r.id").fetchall()
    for r in rows:
        if 'security' in (r['skills'] or '').lower().split(','):
            return r['name'], r['phone'], 'on-duty security'
    if DEMO:
        mate = drill_teammate('security')
        return (f"{mate['name']} (drill stand-in for security)", e164(mate['phone']), 'drill stand-in') if mate else None
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


@router.post('/brief_security')
def brief_security(p=Depends(parse)):
    call, args = p

    def make():
        with connect() as c:
            who = on_duty_security(c, call)
            if not who:
                event(c, call['call_id'], 'No security on duty to brief · callback offered')
                return {'status': 'no_security_on_duty', 'security_name': ''}
            name, phone, why = who
            brief = briefing_text(args, call)
            stamp = datetime.now(TZ).strftime('%H:%M')
            try:
                placed = retell_post('/v2/create-phone-call', {
                    'from_number': os.environ['RETELL_FROM_NUMBER'], 'to_number': phone,
                    'override_agent_id': os.getenv('RETELL_SECURITY_AGENT_ID', SECURITY_AGENT_ID),
                    'retell_llm_dynamic_variables': {
                        'security_name': name.split(' (')[0], 'briefing': brief,
                        'in_progress': 'true' if args.get('in_progress') else 'false',
                        'drill_prefix': 'This is a drill. ' if DEMO else ''},
                    'metadata': {'purpose': 'security_brief', 'source_call_id': call['call_id']}})
            except Exception as e:  # Retell down or misconfigured: the caller still gets a person or a callback
                event(c, call['call_id'], f'Security briefing call to {name} failed ({type(e).__name__}), {stamp}')
                return {'status': 'failed', 'security_name': ''}
            event(c, call['call_id'], f"DIZA is calling {name} ({why}) with a security briefing, {stamp}")
            t = c.execute("SELECT code FROM tickets WHERE reporters LIKE ? ORDER BY created DESC LIMIT 1",
                          (f'%"{call["call_id"]}"%',)).fetchone()
            if t:
                tlog(c, t['code'], 'security', f'Security briefing call to {name}, {stamp}')
            return {'status': 'calling', 'security_name': name.split(' (')[0], 'briefing_call_id': placed.get('call_id', '')}
    return once('brief_security', call, args, make)
