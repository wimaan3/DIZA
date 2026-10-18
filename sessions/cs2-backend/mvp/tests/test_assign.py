import json,os,tempfile,time,unittest
from unittest.mock import patch
os.environ['DIZA_DB']=tempfile.mktemp(suffix='.sqlite3')
os.environ['RETELL_API_KEY']='test-key'
os.environ['RETELL_FROM_NUMBER']='+15555550999'
os.environ['RETELL_ASSIGN_AGENT_ID']='agent_assign_test'
os.environ['DIZA_RESPONDERS']=json.dumps([
 {'id':'ana','name':'Ana Ruiz','phone':'5555550001','skills':['medical'],'backup':'ben'},
 {'id':'ben','name':'Ben Cho','phone':'5555550002','skills':['medical']}])
from backend.app.main import app,connect,save_report,Report
from backend.app import assign as A
from fastapi.testclient import TestClient
from retell.lib.webhook_auth import symmetric
PLACED=[]
A.retell_post=lambda path,body:(PLACED.append(body),{'call_id':f'call_out_{len(PLACED)}'})[1]

class Api(unittest.TestCase):
 def setUp(self):
  self.ctx=TestClient(app);self.c=self.ctx.__enter__();self.c.post('/api/demo/reset');PLACED.clear()
  with connect() as c:c.execute('DELETE FROM assignment_calls')
 def tearDown(self):self.ctx.__exit__(None,None,None)
 def request(self,key):
  r=save_report(Report(idempotency_key=key,location_text='Adams Blvd and Normandie Ave',hazard='medical',summary='Grandmother fell and cannot get up',needs_assistance=True,language='es'))
  with connect() as c:return c.execute('SELECT id FROM requests WHERE report_id=?',(r['id'],)).fetchone()[0]
 def wait_calls(self,n):
  for _ in range(40):
   if len(PLACED)>=n:return
   time.sleep(0.05)
 def answer(self,qid,decision,to):
  raw=json.dumps({'name':'respond_assignment','call':{'call_id':f'out_{to}_{decision}_{qid[:4]}','from_number':'+15555550999','to_number':to,'direction':'outbound'},'args':{'assignment_id':qid,'decision':decision}})
  r=self.c.post('/retell/fn/respond_assignment',content=raw,headers={'x-retell-signature':symmetric['sign'](raw,'test-key')});self.assertEqual(r.status_code,200,r.text);return r.json()
 def state(self,qid):
  with connect() as c:return dict(c.execute('SELECT status,assignee FROM requests WHERE id=?',(qid,)).fetchone())
 def test_offer_calls_the_person_and_yes_accepts(self):
  qid=self.request('a1');self.assertEqual(self.c.post(f'/api/requests/{qid}/offer').status_code,200);self.wait_calls(1)
  body=PLACED[0];v=body['retell_llm_dynamic_variables']
  self.assertEqual((body['to_number'],body['override_agent_id'],v['assignment_id'],v['responder_name']),('+15555550001','agent_assign_test',qid,'Ana'))
  self.assertIn('Adams Blvd and Normandie Ave',v['briefing']);self.assertIn('Spanish',v['briefing'])
  with connect() as c:self.assertGreater(c.execute("SELECT expires FROM attempts WHERE request_id=?",(qid,)).fetchone()[0],time.time()+60)  # held open while it rings
  self.assertEqual(self.answer(qid,'accept','+15555550001'),{'ok':True})
  self.assertEqual(self.state(qid),{'status':'accepted','assignee':'ana'})
  with connect() as c:self.assertTrue(any('accepted responsibility by phone' in e[0] for e in c.execute('SELECT message FROM events WHERE request_id=?',(qid,))))
 def test_no_goes_to_backup_who_is_called_too(self):
  qid=self.request('a2');self.c.post(f'/api/requests/{qid}/offer');self.wait_calls(1)
  self.assertEqual(self.answer(qid,'decline','+15555550001'),{'ok':True});self.wait_calls(2)
  self.assertEqual(self.state(qid),{'status':'offered','assignee':'ben'});self.assertEqual(PLACED[1]['to_number'],'+15555550002')
 def test_only_the_dialled_person_can_answer(self):
  qid=self.request('a3');self.c.post(f'/api/requests/{qid}/offer');self.wait_calls(1)
  self.assertFalse(self.answer(qid,'accept','+15555550002')['ok'])
  self.assertEqual(self.state(qid)['status'],'offered')
 def test_not_set_up_just_notes_it(self):
  with patch.dict(os.environ,{'RETELL_ASSIGN_AGENT_ID':''}),patch.object(A,'agent_id',lambda:''):
   qid=self.request('a4');self.c.post(f'/api/requests/{qid}/offer')
   for _ in range(40):
    with connect() as c:msgs=[e[0] for e in c.execute('SELECT message FROM events WHERE request_id=?',(qid,))]
    if any("aren't set up" in m for m in msgs):break
    time.sleep(0.05)
  self.assertTrue(any("aren't set up" in m for m in msgs));self.assertEqual(PLACED,[])
class TicketCalls(unittest.TestCase):
 setUp=Api.setUp;tearDown=Api.tearDown;wait_calls=Api.wait_calls;answer=Api.answer
 def ticket(self):
  self.c.post('/api/demo/seed?mode=building')
  t=[x for x in self.c.get('/api/building').json()['tickets'] if x['status']=='new'][0];return t['code'],t['unit']
 def test_assigning_a_ticket_calls_the_person_and_yes_starts_it(self):
  code,unit=self.ticket();self.assertEqual(self.c.post(f'/api/tickets/{code}/assign',json={'assignee':'plumb'}).status_code,200);self.wait_calls(1)
  v=PLACED[0]['retell_llm_dynamic_variables'];self.assertEqual((v['assignment_id'],PLACED[0]['to_number']),(code,'+15555550001'))  # demo vendor: a teammate stands in
  self.assertIn(f'unit {unit}',v['briefing'])
  self.assertEqual(self.answer(code,'accept','+15555550001'),{'ok':True})
  t=[x for x in self.c.get('/api/building').json()['tickets'] if x['code']==code][0];self.assertEqual(t['status'],'in_progress')
  self.assertTrue(any('stand-in for Westside Plumbing' in e['message'] for e in t['timeline']))
 def test_no_puts_the_ticket_back(self):
  code,_=self.ticket();self.c.post(f'/api/tickets/{code}/assign',json={'assignee':'plumb'});self.wait_calls(1)
  self.assertFalse(self.answer(code,'decline','+15555550002')['ok'])  # someone else's phone can't answer
  self.assertEqual(self.answer(code,'decline','+15555550001'),{'ok':True})
  t=[x for x in self.c.get('/api/building').json()['tickets'] if x['code']==code][0];self.assertEqual((t['status'],t['assignee']),('new',None))
class Callbacks(unittest.TestCase):
 setUp=Api.setUp;tearDown=Api.tearDown;wait_calls=Api.wait_calls;answer=Api.answer
 def report(self,cid):
  r=save_report(Report(idempotency_key=f'{cid}:h',location_text='6th Street and Broadway, Santa Monica',hazard='fire',summary='fire',source='retell'))
  with connect() as c:c.execute("INSERT OR REPLACE INTO calls(call_id,direction,caller_last4,status,started) VALUES(?,?,?,?,?)",(cid,'inbound','0123','ended',time.time()))
  return r['id']
 def test_callback_calls_the_teammate_with_the_callers_number(self):
  rid=self.report('cb1')
  with patch.object(A,'caller_number',lambda cid:'+13105550123'):
   code=self.c.post(f'/api/reports/{rid}/callback',json={'responder_id':'ben'}).json()['code'];self.wait_calls(1)
  b=PLACED[0];v=b['retell_llm_dynamic_variables']
  self.assertEqual((b['to_number'],v['assignment_id']),('+15555550002',code));self.assertIn('3 1 0, 5 5 5, 0 1 2 3',v['briefing'])
  self.assertEqual(self.answer(code,'accept','+15555550002'),{'ok':True})
  with connect() as c:self.assertEqual(c.execute('SELECT status FROM cases WHERE code=?',(code,)).fetchone()[0],'in_progress')
 def test_take_on_an_ended_call_calls_the_operator(self):
  rid=self.report('cb2')
  with patch.object(A,'caller_number',lambda cid:'+13105550123'):
   self.assertEqual(self.c.post(f'/api/reports/{rid}/take',json={'responder_id':'ana'}).status_code,200);self.wait_calls(1)
  self.assertEqual(PLACED[0]['to_number'],'+15555550001')
if __name__=='__main__':unittest.main()
