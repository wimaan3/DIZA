import json,os,tempfile,time,unittest
os.environ['DIZA_DB']=tempfile.mktemp(suffix='.sqlite3')
os.environ['RETELL_API_KEY']='test-key'
os.environ['DIZA_RESPONDERS']=json.dumps([{'id':'op1','name':'Operator One','phone':'+15555550001','skills':'logistics,facilities,lang:en'}])
from backend.app.main import app,connect
from backend.app import resources as R
from fastapi.testclient import TestClient
from retell.lib.webhook_auth import symmetric
R.geocode=lambda text,deadline:None  # no network in tests
class Queue(unittest.TestCase):
 def setUp(self):
  self.ctx=TestClient(app);self.c=self.ctx.__enter__();self.c.post('/api/demo/reset')
  with connect() as c:c.execute("UPDATE responders SET status='available'")
 def tearDown(self):self.ctx.__exit__(None,None,None)
 def p2_with_trapped_caller(self,call_id='call_q1'):
  # The AI filed a P2 power report, but the caller's own words say someone is trapped: the second reader raises it to P0.
  with connect() as c:c.execute("INSERT INTO calls(call_id,direction,caller_last4,status,started,transcript) VALUES(?,'inbound','0100','live',?,?)",(call_id,time.time(),'Agent: Hi\nUser: power is out and my dad is trapped in the elevator'))
  raw=json.dumps({'name':'submit_report','call':{'call_id':call_id,'from_number':'+15555550100'},'args':{'hazard':'power','location_text':'Lake Ave','summary':'Power out','language':'en'}})
  r=self.c.post('/retell/fn/submit_report',content=raw,headers={'x-retell-signature':symmetric['sign'](raw,'test-key')});self.assertEqual(r.status_code,200,r.text)
  return r.json()['report_id']
 def test_second_reader_p0_is_never_offered_to_helpers(self):
  rid=self.p2_with_trapped_caller()
  i=self.c.get('/api/ops').json()['incidents'][0];self.assertEqual((i['severity'],i['effective']),('P2','P0'))
  q=next(q for q in self.c.get('/api/state').json()['requests'] if q['report_id']==rid)
  self.c.post(f"/api/requests/{q['id']}/offer");s=self.c.get('/api/state').json()
  self.assertEqual(next(x for x in s['requests'] if x['id']==q['id'])['status'],'escalated');self.assertEqual(s['attempts'],[])
 def test_lowering_is_judged_against_what_the_operator_sees(self):
  rid=self.p2_with_trapped_caller('call_q2')
  # Stored P2, shown P0: "setting P2" is a downgrade and needs a reason.
  self.assertEqual(self.c.post(f'/api/reports/{rid}/priority',json={'severity':'P2'}).status_code,400)
  self.assertEqual(self.c.post(f'/api/reports/{rid}/priority',json={'severity':'P2','reason':'Called back: dad is out of the elevator','by':'Ana'}).status_code,200)
  i=self.c.get('/api/ops').json()['incidents'][0];self.assertEqual(i['effective'],'P2')
  self.assertTrue(any('Ana lowered priority P0 → P2' in e['message'] for e in i['timeline']))
if __name__=='__main__':unittest.main()
