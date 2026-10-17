"""Approved alerts → automated Retell calls, with per-person outcomes.

Flow: a supervisor drafts an alert (zone, exact text per language, official source) → a named person
approves it (the dashboard button) → we start one Retell batch call to opted-in contacts using the
`alert` agent → call webhooks update each recipient (reached / voicemail / no answer / needs help /
safe / opted out) → the console shows the tally → "retry unreached" redials no-answers.
The AI never decides to alert or what to say (never-automate rule); nothing here posts public alerts.
Env: RETELL_API_KEY, RETELL_FROM_NUMBER, RETELL_ALERT_AGENT_ID, ALERT_CONTACTS_FILE or ALERT_CONTACTS_CSV (opted-in CSV:
name,phone,language[,opted_out], never committed), ALLOW_LIVE_ALERTS=true to permit mode=live.
"""
import csv, hashlib, json, os, re, secrets, time, urllib.request
from fastapi import HTTPException
from pydantic import BaseModel, Field
from .main import app, connect, event

DRILL_PREFIX = {'en': 'This is a drill for a USC student project.', 'es': 'Esto es un simulacro de un proyecto estudiantil de USC.'}
LOCALES = {'ko': 'ko-KR', 'zh': 'zh-CN', 'hy': 'hy-AM', 'tl': 'fil-PH'}
# Don't redial these: retrying wastes calls and makes the number look like spam.
DO_NOT_RETRY = {'invalid_destination', 'marked_as_spam', 'network_blocked', 'user_declined', 'telephony_provider_permission_denied'}
FINAL = ('needs_help', 'safe', 'opted_out', 'failed')


def init_alerts():
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS alerts(id TEXT PRIMARY KEY,mode TEXT,zone_name TEXT,source TEXT,messages TEXT,status TEXT,
          approved_by TEXT,approved_at REAL,batch_ids TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS alert_recipients(alert_id TEXT,recipient TEXT PRIMARY KEY,name TEXT,phone TEXT,language TEXT,
          status TEXT,attempts INTEGER,updated REAL);
        ''')


def retell_post(path, body):
    req = urllib.request.Request('https://api.retellai.com' + path, data=json.dumps(body).encode(), method='POST',
                                 headers={'Authorization': 'Bearer ' + os.environ['RETELL_API_KEY'], 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read() or b'{}')


def contacts():
    # Opted-in contacts: a CSV file path, or the CSV text itself (handy on hosts like Railway).
    path, inline = os.getenv('ALERT_CONTACTS_FILE', ''), os.getenv('ALERT_CONTACTS_CSV', '')
    if inline:
        import io
        source = io.StringIO(inline.replace('\\n', '\n'))
    elif path and os.path.exists(path):
        source = open(path, newline='')
    else:
        raise HTTPException(503, 'ALERT_CONTACTS_FILE or ALERT_CONTACTS_CSV (opted-in contacts) is not configured')
    with connect() as c:  # anyone who said "stop calling" on any call is never called again
        blocked = {r['caller_hash'] for r in c.execute('SELECT caller_hash FROM consents WHERE do_not_call=1')}
    out = []
    for row in csv.DictReader(source):
        phone = re.sub(r'[^\d+]', '', row.get('phone', ''))
        if hashlib.sha256(phone.encode()).hexdigest() in blocked:
            continue
        if re.fullmatch(r'\+1\d{10}', phone) and (row.get('opted_out') or '').strip().lower() not in ('1', 'true', 'yes'):
            out.append({'name': (row.get('name') or '').strip(), 'phone': phone, 'language': (row.get('language') or 'en').strip().lower()})
    return out


class AlertDraft(BaseModel):
    mode: str = Field(pattern='^(drill|live)$')
    zone_name: str = Field(min_length=2, max_length=120)
    source: str = Field(min_length=3, max_length=200)  # the official source callers can verify
    messages: dict[str, dict[str, str]]                 # {"en": {"message": "...", "action": "..."}, "es": {...}}


class Approval(BaseModel):
    approved_by: str = Field(min_length=2, max_length=100)


@app.post('/api/alerts')
def draft_alert(d: AlertDraft):
    if 'en' not in d.messages or not d.messages['en'].get('message'):
        raise HTTPException(422, 'messages.en.message is required')
    alert_id = f"alert-{time.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(2)}"
    with connect() as c:
        c.execute('INSERT INTO alerts VALUES(?,?,?,?,?,?,?,?,?,?)', (alert_id, d.mode, d.zone_name, d.source, json.dumps(d.messages),
                                                                     'draft', None, None, '[]', time.time()))
        event(c, alert_id, f'Alert drafted for {d.zone_name} ({d.mode}) · waiting for a person to approve the exact text')
    return {'id': alert_id, 'status': 'draft'}


def build_tasks(alert, recipients):
    messages = json.loads(alert['messages'])
    tasks = []
    for r in recipients:
        lang = r['language'] if r['language'] in messages else 'en'
        text = messages[lang]
        msg = text['message'].strip()
        if alert['mode'] == 'drill':
            msg = f"{DRILL_PREFIX.get(lang, DRILL_PREFIX['en'])} {msg}"
        task = {'to_number': r['phone'], 'override_agent_id': os.environ['RETELL_ALERT_AGENT_ID'],
                'override_agent_version': os.getenv('RETELL_ALERT_AGENT_VERSION', 'latest_published'),  # 'latest' includes drafts
                'retell_llm_dynamic_variables': {'caller_name': (r['name'].split(' ')[0] if r['name'] else 'there'), 'language': lang,
                    'zone_name': alert['zone_name'], 'alert_message': msg, 'alert_action': text.get('action', '').strip(),
                    'alert_source': alert['source'], 'alert_id': alert['id'], 'drill_mode': str(alert['mode'] == 'drill').lower()},
                'metadata': {'alert_id': alert['id'], 'recipient': r['recipient']}}
        if lang in LOCALES:
            task['agent_override'] = {'agent': {'language': LOCALES[lang]}}
        tasks.append(task)
    return tasks


def send_batch(alert, recipients, label):
    for key in ('RETELL_API_KEY', 'RETELL_FROM_NUMBER', 'RETELL_ALERT_AGENT_ID'):
        if not os.getenv(key):
            raise HTTPException(503, f'{key} is not configured')
    body = {'name': f"{alert['id']} {label}", 'from_number': os.environ['RETELL_FROM_NUMBER'],
            'tasks': build_tasks(alert, recipients), 'reserved_concurrency': 8}  # inbound keeps answering
    if alert['mode'] == 'drill':  # non-emergency calls: 8 AM-9 PM local (TCPA); live emergency alerts are exempt
        body['call_time_window'] = {'windows': [{'start': 480, 'end': 1260}], 'timezone': 'America/Los_Angeles'}
    return retell_post('/create-batch-call', body).get('batch_call_id', '')


@app.post('/api/alerts/{alert_id}/approve')
def approve_and_send(alert_id: str, a: Approval):
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        alert = c.execute('SELECT * FROM alerts WHERE id=?', (alert_id,)).fetchone()
        if not alert:
            raise HTTPException(404, 'Alert not found')
        if alert['status'] != 'draft':
            raise HTTPException(409, f"Alert is already {alert['status']}")
        if alert['mode'] == 'live' and os.getenv('ALLOW_LIVE_ALERTS', '').lower() != 'true':
            raise HTTPException(403, 'Live alerts are disabled (ALLOW_LIVE_ALERTS). Relay only official orders.')
        people = [{**p, 'recipient': secrets.token_hex(6)} for p in contacts()]
        c.execute("UPDATE alerts SET status='approved',approved_by=?,approved_at=? WHERE id=?", (a.approved_by, time.time(), alert_id))
        for p in people:
            c.execute('INSERT INTO alert_recipients VALUES(?,?,?,?,?,?,?,?)', (alert_id, p['recipient'], p['name'], p['phone'],
                                                                               p['language'], 'calling', 1, time.time()))
        alert = dict(c.execute('SELECT * FROM alerts WHERE id=?', (alert_id,)).fetchone())
    try:
        batch = send_batch(alert, people, 'initial')
    except Exception as e:
        with connect() as c:  # nothing is calling: put the alert back to draft so it can be fixed and re-approved
            c.execute("UPDATE alerts SET status='draft',approved_by=NULL,approved_at=NULL WHERE id=?", (alert_id,))
            c.execute('DELETE FROM alert_recipients WHERE alert_id=?', (alert_id,))
            event(c, alert_id, f'Alert send failed, back to draft: {str(e)[:120]}')
        raise HTTPException(502, f'Retell batch call failed; alert is back to draft: {str(e)[:200]}')
    with connect() as c:
        c.execute("UPDATE alerts SET status='sent',batch_ids=? WHERE id=?", (json.dumps([batch]), alert_id))
        event(c, alert_id, f"Alert approved by {a.approved_by} · calling {len(people)} opted-in people (batch {batch})")
    return {'id': alert_id, 'status': 'sent', 'calls': len(people), 'batch_call_id': batch}


@app.post('/api/alerts/{alert_id}/retry')
def retry_unreached(alert_id: str):
    with connect() as c:
        alert = c.execute('SELECT * FROM alerts WHERE id=?', (alert_id,)).fetchone()
        if not alert or alert['status'] != 'sent':
            raise HTTPException(409, 'Only sent alerts can be retried')
        people = [dict(r) for r in c.execute("SELECT * FROM alert_recipients WHERE alert_id=? AND status='no_answer' AND attempts<3", (alert_id,))]
        if not people:
            return {'id': alert_id, 'calls': 0}
        for p in people:
            c.execute("UPDATE alert_recipients SET status='calling',attempts=attempts+1,updated=? WHERE recipient=?", (time.time(), p['recipient']))
    batch = send_batch(dict(alert), people, f'retry')
    with connect() as c:
        ids = json.loads(alert['batch_ids']) + [batch]
        c.execute('UPDATE alerts SET batch_ids=? WHERE id=?', (json.dumps(ids), alert_id))
        event(c, alert_id, f'Retrying {len(people)} people who did not answer (batch {batch})')
    return {'id': alert_id, 'calls': len(people), 'batch_call_id': batch}


@app.get('/api/alerts')
def list_alerts():
    with connect() as c:
        out = []
        for a in c.execute('SELECT id,mode,zone_name,status,approved_by,approved_at,created FROM alerts ORDER BY created DESC LIMIT 50'):
            tally = {r['status']: r['n'] for r in c.execute('SELECT status,COUNT(*) n FROM alert_recipients WHERE alert_id=? GROUP BY status', (a['id'],))}
            out.append({**dict(a), 'tally': tally, 'total': sum(tally.values())})
        return {'alerts': out}


def on_alert_call_event(data):
    """Update a recipient from Retell call webhooks (metadata carries alert_id + recipient)."""
    call = data.get('call') or {}
    meta = call.get('metadata') or {}
    if not meta.get('alert_id') or not meta.get('recipient'):
        return
    ev, status = data.get('event'), None
    if ev == 'call_ended':
        reason = call.get('disconnection_reason') or ''
        if reason == 'voicemail_reached':
            status = 'voicemail'
        elif reason in DO_NOT_RETRY:
            status = 'failed'
        elif call.get('call_status') in ('not_connected', 'error') or reason.startswith('dial_') or reason.startswith('error_'):
            status = 'no_answer'
        else:
            status = 'reached'
    elif ev == 'call_analyzed':
        analysis = call.get('call_analysis') or call.get('scrubbed_call_analysis') or {}  # PII-scrubbed storage sends the scrubbed copy
        a = analysis.get('custom_analysis_data') or {}
        status = ('voicemail' if analysis.get('in_voicemail') else 'opted_out' if a.get('opted_out')
                  else {'needs_help': 'needs_help', 'safe_and_able': 'safe'}.get(a.get('safe_status')))
    if status:
        with connect() as c:
            # Final outcomes are never overwritten, and a late or retried event can't move someone back.
            c.execute(f"UPDATE alert_recipients SET status=?,updated=? WHERE recipient=? AND status NOT IN ({','.join('?' * len(FINAL))})",
                      (status, time.time(), meta['recipient'], *FINAL))
            if status == 'needs_help':
                event(c, meta['alert_id'], 'Alert recipient needs help · follow up now')
