import asyncio, hashlib, json, os, re, sqlite3, time, uuid
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
DB = os.getenv('DIZA_DB', str(ROOT / 'diza.sqlite3'))
TIMEOUT = int(os.getenv('OFFER_TIMEOUT_SECONDS', '30'))
DEMO = os.getenv('DRILL_MODE', 'true').lower() == 'true'

@contextmanager
def connect():
    c = sqlite3.connect(DB, timeout=10)
    c.row_factory = sqlite3.Row
    try:
        with c:
            yield c
    finally:
        c.close()

def event(c, request_id, message):
    c.execute('INSERT INTO events VALUES(?,?,?,?)', (str(uuid.uuid4()), request_id, time.time(), message))

def init():
    with connect() as c:
        c.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS responders(id TEXT PRIMARY KEY,name TEXT,skills TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY,dedupe TEXT UNIQUE,cluster_id TEXT,location TEXT,category TEXT,summary TEXT,evidence TEXT,unknowns TEXT,severity TEXT,reason TEXT,language TEXT,source TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY,report_id TEXT UNIQUE,status TEXT,assignee TEXT,created REAL,updated REAL);
        CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY,request_id TEXT,responder_id TEXT,status TEXT,expires REAL);
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,request_id TEXT,ts REAL,message TEXT);
        CREATE TABLE IF NOT EXISTS webhook_events(id TEXT PRIMARY KEY,created REAL);
        CREATE TABLE IF NOT EXISTS calls(call_id TEXT PRIMARY KEY,direction TEXT,agent TEXT,caller_last4 TEXT,status TEXT,started REAL,ended REAL,
          duration_s INTEGER,disconnection_reason TEXT,summary TEXT,sentiment TEXT,updated REAL);
        ''')
        # Placeholder team for local runs only; init_fns() replaces it with DIZA_RESPONDERS when that is set.
        for row in [('alex','Alex Chen','facilities,logistics','available'),('sam','Sam Rivera','facilities,logistics,medical,safety','available'),('maya','Maya Patel','medical,safety','available')]:
            c.execute('INSERT OR IGNORE INTO responders VALUES(?,?,?,?)', row)

class Report(BaseModel):
    idempotency_key: str = Field(min_length=1,max_length=200)
    location_text: str = Field(min_length=1,max_length=300)
    hazard: str = Field(default='info',max_length=60)
    summary: str = Field(min_length=1,max_length=2000)
    evidence: str = Field(default='',max_length=2000)
    unknowns: list[str] = Field(default_factory=list,max_length=20)
    language: str = 'en'
    immediate_danger: bool = False
    needs_assistance: bool = False
    people_at_risk: int = Field(default=0,ge=0,le=10000)
    vulnerability: list[str] = Field(default_factory=list,max_length=20)
    source: str = 'simulated'

ACTIVE_HAZARDS={'fire','smoke','gas','flood'}
CATEGORY_WORDS=[('fire',('fire','flame','burn','fuego','incendio','불','火')),('smoke',('smoke','humo','연기','烟')),
    ('gas',('gas',)),('flood',('flood','water rising','inundaci','침수','水灾')),('power',('power','outage','lights out','electric','luz')),
    ('medical',('medical','injur','breath','chest','bleed','unconscious','faint')),('safety_crime',('crime','weapon','gun','attack','follow','threat')),
    ('infrastructure',('collapse','road','tree down','lines down','sinkhole','building')),('welfare_check',('welfare',))]

def category(hazard):
    # Map the agent's free-text hazard onto the shared category enum so grouping works.
    h=(hazard or '').lower()
    if h in {c for c,_ in CATEGORY_WORDS} or h=='info': return h
    return next((c for c,words in CATEGORY_WORDS if any(w in h for w in words)),'other')

def classify(r):
    if r.immediate_danger:
        return 'P0', 'Reported immediate danger · urgent supervisor review; direct emergency-services path'
    if r.needs_assistance:
        return 'P1', 'Individual assistance requested · a person must accept responsibility'
    if r.hazard in ACTIVE_HAZARDS:
        return 'P1', 'Active hazard reported · counts toward zone detection'
    if r.hazard != 'info' and (r.vulnerability or r.people_at_risk):
        return 'P1', 'People at risk or vulnerability reported · escalate-only'
    if r.hazard != 'info':
        return 'P2', 'Unverified incident report · review needed'
    return 'P3', 'Information request · verified event information available'

def save_report(r):
    severity, reason = classify(r)
    now = time.time()
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        existing=c.execute('SELECT * FROM reports WHERE dedupe=?',(r.idempotency_key,)).fetchone()
        if existing:
            return dict(existing)
        # Conservative exact-location/category grouping within 10 minutes; never deletes individual reports.
        prev=c.execute('SELECT cluster_id FROM reports WHERE lower(trim(location))=? AND category=? AND created>? ORDER BY created DESC LIMIT 1',(r.location_text.strip().lower(),r.hazard,now-600)).fetchone()
        cluster=prev['cluster_id'] if prev else str(uuid.uuid4())
        rid=str(uuid.uuid4())
        c.execute('INSERT INTO reports VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(rid,r.idempotency_key,cluster,r.location_text,r.hazard,r.summary,r.evidence,json.dumps(r.unknowns),severity,reason,r.language,r.source,now))
        if severity != 'P3':
            qid=str(uuid.uuid4())
            c.execute('INSERT INTO requests VALUES(?,?,?,?,?,?)',(qid,rid,'new',None,now,now))
            event(c,qid,'Request saved · no person has accepted responsibility')
        return dict(c.execute('SELECT * FROM reports WHERE id=?',(rid,)).fetchone())

def offer(c,qid):
    q=c.execute('SELECT q.*,r.category,r.severity FROM requests q JOIN reports r ON r.id=q.report_id WHERE q.id=?',(qid,)).fetchone()
    if not q: raise HTTPException(404,'Request not found')
    if q['status'] in ('accepted','in_progress','done','offered'): return
    if q['severity']=='P0':
        c.execute("UPDATE requests SET status='escalated',updated=? WHERE id=?",(time.time(),qid))
        event(c,qid,'Urgent supervisor review required · not routed to general helpers; DIZA never contacts emergency services')
        return
    skill={'power':'facilities','infrastructure':'facilities','medical':'medical','safety_crime':'safety'}.get(q['category'],'logistics')
    rows=c.execute("SELECT * FROM responders WHERE status='available' AND id NOT IN (SELECT responder_id FROM attempts WHERE request_id=?) ORDER BY id",(qid,)).fetchall()
    candidate=next((r for r in rows if skill in r['skills'].split(',')),None)
    if not candidate:
        c.execute("UPDATE requests SET status='escalated',assignee=NULL,updated=? WHERE id=?",(time.time(),qid))
        event(c,qid,'No eligible responder available · supervisor action required')
        return
    c.execute("UPDATE responders SET status='reserved' WHERE id=?",(candidate['id'],))
    c.execute("UPDATE requests SET status='offered',assignee=?,updated=? WHERE id=?",(candidate['id'],time.time(),qid))
    c.execute('INSERT INTO attempts VALUES(?,?,?,?,?)',(str(uuid.uuid4()),qid,candidate['id'],'offered',time.time()+TIMEOUT))
    event(c,qid,f"Offer visible in supporter inbox: {candidate['name']} · awaiting acceptance (no phone notification sent)")

def expire():
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        for a in c.execute("SELECT * FROM attempts WHERE status='offered' AND expires<=?",(time.time(),)).fetchall():
            c.execute("UPDATE attempts SET status='timed_out' WHERE id=?",(a['id'],))
            c.execute("UPDATE responders SET status='available' WHERE id=?",(a['responder_id'],))
            c.execute("UPDATE requests SET status='new',assignee=NULL WHERE id=?",(a['request_id'],))
            event(c,a['request_id'],'Acceptance timeout · trying the next eligible responder')
            offer(c,a['request_id'])

@asynccontextmanager
async def lifespan(app):
    init()
    init_fns()
    init_alerts()
    async def worker():
        while True:
            expire()
            await asyncio.sleep(1)
    task=asyncio.create_task(worker())
    yield
    task.cancel()

app=FastAPI(title='DIZA MVP',lifespan=lifespan)

@app.middleware('http')
async def guard(request,call_next):
    # Local demo only. Set OPS_API_TOKEN for remote deployment; UI supports entering it.
    token=os.getenv('OPS_API_TOKEN','')
    if request.url.path.startswith('/api/') and token and request.headers.get('authorization') != 'Bearer '+token:
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail':'Operator token required'},status_code=401)
    return await call_next(request)

LIVE = bool(os.getenv('RETELL_API_KEY'))

@app.get('/api/state')
def state():
    with connect() as c:
        return {'demo':DEMO,'live':LIVE,'line_number':os.getenv('RETELL_FROM_NUMBER',''),'timeout':TIMEOUT,'reports':[dict(r) for r in c.execute('SELECT * FROM reports ORDER BY created DESC')],
          'requests':[dict(r) for r in c.execute('SELECT * FROM requests ORDER BY created')],
          'responders':[dict(r) for r in c.execute('SELECT * FROM responders')],
          'attempts':[dict(r) for r in c.execute('SELECT * FROM attempts ORDER BY expires')],
          'events':[dict(r) for r in c.execute('SELECT * FROM events ORDER BY ts DESC LIMIT 100')],
          'cases':[dict(r) for r in c.execute('SELECT code,type,status,pool,created,updated FROM cases ORDER BY created DESC LIMIT 200')],
          'calls':[dict(r) for r in c.execute('SELECT * FROM calls ORDER BY started DESC LIMIT 100')],
          'kb_gaps':[dict(r) for r in c.execute('SELECT id,question,created FROM kb_gaps ORDER BY created DESC LIMIT 50')],
          'alerts':list_alerts()['alerts']}

@app.post('/api/reports')
def submit(r:Report):
    if not DEMO or LIVE: raise HTTPException(403,'Manual simulation is off while the line is live')
    r.source='simulated'
    return save_report(r)

@app.post('/api/requests/{qid}/offer')
def assign(qid:str):
    with connect() as c:
        c.execute('BEGIN IMMEDIATE'); offer(c,qid)
    return {'ok':True}

class Decision(BaseModel):
    responder_id:str
    action:str

@app.post('/api/requests/{qid}/decision')
def decide(qid:str,d:Decision):
    if d.action not in ('accept','decline','resolve'): raise HTTPException(400,'Invalid action')
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        q=c.execute('SELECT * FROM requests WHERE id=?',(qid,)).fetchone()
        if not q or q['assignee']!=d.responder_id: raise HTTPException(409,'Assignment changed')
        if d.action=='resolve':
            if q['status']!='accepted': raise HTTPException(409,'Must accept first')
            c.execute("UPDATE requests SET status='done',updated=? WHERE id=?",(time.time(),qid))
            c.execute("UPDATE responders SET status='available' WHERE id=?",(d.responder_id,))
            event(c,qid,'Responder marked task completed · caller confirmation not collected')
        else:
            a=c.execute("SELECT * FROM attempts WHERE request_id=? AND status='offered'",(qid,)).fetchone()
            if not a or a['expires']<=time.time(): raise HTTPException(409,'Offer expired')
            accepted=d.action=='accept'
            c.execute('UPDATE attempts SET status=? WHERE id=?',('accepted' if accepted else 'declined',a['id']))
            c.execute('UPDATE responders SET status=? WHERE id=?',('busy' if accepted else 'available',d.responder_id))
            c.execute('UPDATE requests SET status=?,assignee=?,updated=? WHERE id=?',('accepted' if accepted else 'new',d.responder_id if accepted else None,time.time(),qid))
            event(c,qid,'Responder explicitly accepted responsibility' if accepted else 'Responder declined · trying backup')
            if not accepted: offer(c,qid)
    return {'ok':True}

@app.post('/api/demo/surge')
def surge():
    if not DEMO or LIVE: raise HTTPException(403,'Simulated surges are off while the line is live')
    batch=str(uuid.uuid4())
    for i in range(12):
        save_report(Report(idempotency_key=f'{batch}-{i}',location_text='Building A',hazard='power',summary='Power outage reported at the event.' if i<10 else 'I need assistance reaching the accessible exit.',evidence='The lights went out.' if i<10 else 'I cannot use the stairs.',needs_assistance=i>=10,unknowns=['Cause of outage'],language='es' if i%3==0 else 'en'))
    return {'created':12,'simulated':True}

@app.post('/api/demo/reset')
def reset():
    if not DEMO: raise HTTPException(403)
    with connect() as c:
        for table in ('attempts','requests','reports','events','webhook_events','calls','cases','fn_results','routings','kb_gaps','kb_items','alerts','alert_recipients','consents'): c.execute(f'DELETE FROM {table}')
        c.execute("UPDATE responders SET status='available'")
    return {'ok':True}

async def verified_body(req):
    raw=await req.body()
    key=os.getenv('RETELL_API_KEY')
    if not key: raise HTTPException(503,'Retell not configured; demo API remains available')
    from retell.lib.webhook_auth import verify
    if not verify(raw.decode(),key,req.headers.get('x-retell-signature','')):
        raise HTTPException(401,'Invalid Retell signature')
    return json.loads(raw)

async def signed(req:Request):
    return await verified_body(req)

@app.post('/retell/inbound')
def inbound(data=Depends(signed)):
    return {'call_inbound':{'dynamic_variables':{'drill_mode':str(DEMO).lower(),'zone_level':'normal','known_incidents':'Use verified information only'}}}

@app.post('/retell/fn/submit_report')
def retell_submit(data=Depends(signed)):
    args=data.get('args',{})
    call_id=data.get('call',{}).get('call_id','')
    if not call_id: raise HTTPException(422,'call.call_id required')
    args['idempotency_key']=call_id+':'+hashlib.sha256(json.dumps(args,sort_keys=True).encode()).hexdigest()
    args['source']='retell'
    args.setdefault('summary',args.get('hazard','Report'))
    args['hazard']=category(args.get('hazard'))
    args['immediate_danger']=bool(args.get('immediate_danger') or args.get('injured_or_trapped'))
    if args.get('vulnerability') and not args.get('evidence'):
        args['evidence']='Vulnerability: '+', '.join(args['vulnerability'])
    r=merge_into_p0(call_id,Report(**args)) or save_report(Report(**args))
    with connect() as c:
        others=c.execute('SELECT COUNT(*) FROM reports WHERE cluster_id=? AND id!=?',(r['cluster_id'],r['id'])).fetchone()[0]
    # Read aloud by the agent, so only say something when other callers reported the same thing.
    match=f"We already have {others+1} reports of {r['category'].replace('_',' ')} near {r['location']}, and we're tracking it." if others else ''
    return {'report_id':r['id'],'severity':r['severity'],'priority':{'P0':100,'P1':80,'P2':50,'P3':10}[r['severity']],'reason':r['reason'],'cluster_match':match}

def merge_into_p0(call_id,r):
    # flag_urgent already opened a P0 report for this call; the full report fills it in instead of adding a second row.
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        p0=c.execute('SELECT * FROM reports WHERE substr(dedupe,1,?)=? ORDER BY created LIMIT 1',(len(call_id)+4,call_id+':p0:')).fetchone()
        if not p0: return None
        prev=c.execute('SELECT cluster_id FROM reports WHERE lower(trim(location))=? AND category=? AND created>? AND id!=? ORDER BY created DESC LIMIT 1',
                       (r.location_text.strip().lower(),r.hazard,time.time()-600,p0['id'])).fetchone()
        summary=r.summary if r.summary.startswith(p0['summary']) else f"{r.summary} · {p0['summary']}"
        evidence=' · '.join(x for x in (p0['evidence'],r.evidence) if x)
        c.execute('UPDATE reports SET location=?,category=?,summary=?,evidence=?,unknowns=?,language=?,cluster_id=? WHERE id=?',
                  (r.location_text,r.hazard,summary[:2000],evidence[:2000],json.dumps(r.unknowns),r.language,prev['cluster_id'] if prev else p0['cluster_id'],p0['id']))
        q=c.execute('SELECT id FROM requests WHERE report_id=?',(p0['id'],)).fetchone()
        if q: event(c,q['id'],f'Caller details added: {r.location_text}')
        return dict(c.execute('SELECT * FROM reports WHERE id=?',(p0['id'],)).fetchone())

def log_call(data):
    # Every call the agents handle, from Retell's call_started / call_ended / call_analyzed webhooks. Last 4 digits only.
    call=data.get('call') or {}
    cid=call.get('call_id')
    if not cid: return
    from .retell_fns import person_number
    analysis=call.get('call_analysis') or {}
    ended=(call.get('end_timestamp') or 0)/1000 or None
    started=(call.get('start_timestamp') or 0)/1000 or time.time()
    status={'call_started':'live','call_ended':'ended','call_analyzed':'ended'}.get(data.get('event'),'live')
    with connect() as c:
        c.execute('''INSERT INTO calls VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(call_id) DO UPDATE SET
            status=CASE WHEN excluded.status='ended' THEN 'ended' ELSE calls.status END,
            ended=COALESCE(excluded.ended,calls.ended),duration_s=COALESCE(excluded.duration_s,calls.duration_s),
            disconnection_reason=COALESCE(excluded.disconnection_reason,calls.disconnection_reason),
            summary=COALESCE(excluded.summary,calls.summary),sentiment=COALESCE(excluded.sentiment,calls.sentiment),updated=excluded.updated''',
            (cid,call.get('direction') or '',call.get('agent_name') or call.get('agent_id') or '',re.sub(r'\D','',person_number(call))[-4:],status,started,ended,
             int(ended-started) if ended else None,call.get('disconnection_reason'),analysis.get('call_summary'),analysis.get('user_sentiment'),time.time()))

@app.post('/retell/webhook',status_code=204)
def webhook(data=Depends(signed)):
    call_id=(data.get('call') or {}).get('call_id','')
    key=f"{data.get('event','')}:{call_id}" if call_id else hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
    with connect() as c:
        fresh=c.execute('INSERT OR IGNORE INTO webhook_events VALUES(?,?)',(key,time.time())).rowcount
    if not fresh:
        return  # retry or duplicate (Retell retries; agent swaps with both_agents send twice)
    log_call(data)
    # Report submission happens during the call; call_ended frees whoever we routed it to.
    if data.get('event')=='call_ended':
        release_call(call_id)
    on_alert_call_event(data)

from .retell_fns import router as retell_fn_router, init_fns, release_call
app.include_router(retell_fn_router)
from .alerts import init_alerts, on_alert_call_event, list_alerts

DIST=ROOT/'dashboard'/'dist'
if DIST.exists():
    app.mount('/assets',StaticFiles(directory=DIST/'assets'),name='assets')
    @app.get('/{path:path}')
    def spa(path:str):
        return FileResponse(DIST/'index.html')
