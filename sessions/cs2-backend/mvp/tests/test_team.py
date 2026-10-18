import json,os,tempfile,time,unittest
from datetime import datetime
from zoneinfo import ZoneInfo
os.environ['DIZA_DB']=tempfile.mktemp(suffix='.sqlite3')
os.environ['RETELL_API_KEY']='test-key'
os.environ['DIZA_RESPONDERS']=json.dumps([
 {'id':'ana','name':'Ana','phone':'5555550001','skills':['medical'],'languages':['es','en'],'areas':['Altadena'],'backup':'ben'},
 {'id':'ben','name':'Ben','phone':'5555550002','skills':'medical,evac_logistics','languages':['en']},
 {'id':'cho','name':'Cho','phone':'5555550003','skills':['medical'],'languages':['ko'],'home':[34.06,-118.30],'radius_km':5},
 {'id':'dee','name':'Dee','phone':'5555550004','skills':['medical','security'],'languages':['en'],'hours':'Mon 03:00-03:01'},
 {'id':'vol','name':'Val','phone':'5555550005','skills':['volunteer','listener'],'languages':['es'],'backup':'nobody'}])
from backend.app.main import app,connect
from backend.app import team as T, resources as R
from fastapi.testclient import TestClient
from retell.lib.webhook_auth import symmetric
R.geocode=lambda text,deadline:None
LA=ZoneInfo('America/Los_Angeles')
at=lambda *a:datetime(*a,tzinfo=LA).timestamp()

class Rules(unittest.TestCase):
 def test_normalize(self):
  skills,prof=T.normalize({'skills':'Logistics','languages':['KO','lang:en'],'areas':'Altadena, Pasadena','home':[1,2]})
  self.assertEqual(skills.split(','),['logistics','lang:ko','lang:en','evac_logistics'])
  self.assertEqual((prof['areas'],prof['radius_km']),(['Altadena','Pasadena'],10.0))
 def test_hours(self):
  mon9=at(2026,10,19,9,0)  # a Monday
  self.assertTrue(T.on_duty('Mon-Fri 08:00-20:00',mon9));self.assertFalse(T.on_duty('Sat-Sun 08:00-20:00',mon9))
  self.assertTrue(T.on_duty('Sun 22:00-06:00',at(2026,10,19,2,0)))   # overnight shift from Sunday
  self.assertFalse(T.on_duty('Sun 22:00-06:00',at(2026,10,19,7,0)))
  self.assertTrue(T.on_duty('',mon9));self.assertIsNone(T.parse_hours('whenever'))
 def test_area(self):
  self.assertEqual(T.area_match({'areas':['Altadena']},'Lake Ave, Altadena',None),'covers Altadena')
  self.assertEqual(T.area_match({'home':[34.06,-118.30],'radius_km':5},'',(34.07,-118.29)),'1 km away')
  self.assertEqual(T.area_match({'home':[34.06,-118.30],'radius_km':5},'',(34.19,-118.13)),'')

class Api(unittest.TestCase):
 def setUp(self):
  self.ctx=TestClient(app);self.c=self.ctx.__enter__();self.c.post('/api/demo/reset')
 def tearDown(self):self.ctx.__exit__(None,None,None)
 def fn(self,name,args,call_id):
  raw=json.dumps({'name':name,'call':{'call_id':call_id,'from_number':'+15555550100','to_number':'+15555550999','direction':'inbound'},'args':args})
  r=self.c.post(f'/retell/fn/{name}',content=raw,headers={'x-retell-signature':symmetric['sign'](raw,'test-key')})
  self.assertEqual(r.status_code,200,r.text);return r.json()
 def route(self,call_id,lang='en',needs=('medical',),sev='P1',**kw):
  return self.fn('route_to_human',{'needs':list(needs),'language':lang,'severity':sev,'summary':'x',**kw},call_id)
 def test_area_and_language_pick_and_reason(self):
  self.fn('submit_report',{'hazard':'medical','location_text':'Lake Ave, Altadena','summary':'fall','language':'es'},'c_area')
  out=self.route('c_area','es');self.assertEqual(out['responder_name'],'Ana')
  self.assertEqual(out['match_reason'],'speaks Spanish, medical, covers Altadena')
 def test_failed_transfer_goes_to_backup_then_next(self):
  first=self.route('c_bk','es',location_text='Altadena');self.assertEqual(first['responder_name'],'Ana')
  again=self.route('c_bk','es',sev='P0',location_text='Altadena');self.assertEqual(again['match_reason'],'already assigned to this call')
  b=self.route('c_bk','es',location_text='Altadena',transfer_failed=True)
  self.assertEqual(b['responder_name'],'Ben');self.assertTrue(b['match_reason'].startswith('backup'))
  with connect() as c:
   self.assertEqual(c.execute("SELECT status FROM responders WHERE id='ana'").fetchone()[0],'available')
   self.assertTrue(any("Ana didn't answer" in e[0] for e in c.execute("SELECT message FROM events WHERE request_id='c_bk'")))
  n=self.route('c_bk','es',sev='P2',location_text='Altadena',transfer_failed=True)
  self.assertNotIn(n['responder_name'],('Ana','Ben'))  # never ring someone who already didn't answer on this call
 def test_off_duty_and_volunteers_are_skipped(self):
  names=set()
  for i in range(4):names.add(self.route(f'c_off{i}','en',sev='P0')['responder_name'] or 'none')
  self.assertNotIn('Dee',names);self.assertNotIn('Val',names)
  st={r['id']:r for r in self.c.get('/api/state').json()['responders']}
  self.assertFalse(st['dee']['on_duty']);self.assertEqual(st['ana']['areas'],['Altadena']);self.assertEqual(st['vol']['backup'],'')  # unknown backup dropped
 def test_radius_pick(self):
  with connect() as c:c.execute("UPDATE responders SET status='busy' WHERE id IN ('ana','ben')")
  self.fn('submit_report',{'hazard':'medical','location_text':'Koreatown','summary':'x','language':'en'},'c_rad')
  for _ in range(40):  # let the background geocoder finish before pinning by hand
   with connect() as c:
    if c.execute('SELECT geo_tried FROM reports').fetchone()[0]==1:break
   time.sleep(0.05)
  with connect() as c:c.execute("UPDATE reports SET lat=34.07,lon=-118.29")
  self.assertEqual(self.route('c_rad','en')['match_reason'],'medical, 1 km away')
 def test_dashboard_decline_offers_backup(self):
  with connect() as c:
   from backend.app.main import save_report,Report,offer
   r=save_report(Report(idempotency_key='d1',location_text='Altadena',hazard='medical',summary='x',needs_assistance=True))
   q=c.execute('SELECT id FROM requests WHERE report_id=?',(r['id'],)).fetchone()[0]
  self.assertEqual(self.c.post(f'/api/requests/{q}/offer').status_code,200)
  with connect() as c:self.assertEqual(c.execute('SELECT assignee FROM requests WHERE id=?',(q,)).fetchone()[0],'ana')  # covers Altadena
  self.assertEqual(self.c.post(f'/api/requests/{q}/decision',json={'responder_id':'ana','action':'decline'}).status_code,200)
  with connect() as c:
   self.assertEqual(c.execute('SELECT assignee FROM requests WHERE id=?',(q,)).fetchone()[0],'ben')
   self.assertTrue(any('Ben (backup)' in e[0] for e in c.execute('SELECT message FROM events WHERE request_id=?',(q,))))
 def test_no_skill_match_still_reaches_a_teammate(self):
  # We are the staff: a power outage needs 'facilities', which nobody has; it goes to an on-duty teammate, never a dead end.
  from backend.app.main import save_report,Report
  r=save_report(Report(idempotency_key='pw1',location_text='Pasadena',hazard='power',summary='power out, oxygen machine',needs_assistance=True))
  with connect() as c:q=c.execute('SELECT id FROM requests WHERE report_id=?',(r['id'],)).fetchone()[0]
  self.c.post(f'/api/requests/{q}/offer')
  with connect() as c:
   row=c.execute('SELECT status,assignee FROM requests WHERE id=?',(q,)).fetchone()
   self.assertEqual(row['status'],'offered');self.assertNotIn(row['assignee'],('dee','vol'))  # off duty and volunteers excluded
   self.assertTrue(any('no one with facilities on duty' in e[0] for e in c.execute('SELECT message FROM events WHERE request_id=?',(q,))))
if __name__=='__main__':unittest.main()
