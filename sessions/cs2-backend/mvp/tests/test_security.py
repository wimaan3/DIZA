import json,os,tempfile,unittest
from unittest.mock import patch
os.environ['DIZA_DB']=tempfile.mktemp(suffix='.sqlite3')
os.environ['RETELL_API_KEY']='test-key'
os.environ['RETELL_FROM_NUMBER']='+15555550999'
os.environ['DIZA_RESPONDERS']=json.dumps([{'id':'t1','name':'Teammate One','phone':'+15555550001','skills':'evac_logistics,lang:en'},
                                          {'id':'t2','name':'Guard Two','phone':'(555) 555-0002','skills':'security,lang:en'}])
from backend.app.main import app,connect
from backend.app import security as S
from fastapi.testclient import TestClient
from retell.lib.webhook_auth import symmetric
ARGS={'incident':'Apartment door forced open, laptop missing','location_text':'Unit 4B, 1200 Figueroa St','caller_quote':'someone broke into my place','in_progress':False}
class SecurityBriefing(unittest.TestCase):
 def setUp(self):
  self.ctx=TestClient(app);self.c=self.ctx.__enter__();self.c.post('/api/demo/reset')
  self.placed=[]
  self.p=patch.object(S,'retell_post',side_effect=lambda path,body:(self.placed.append((path,body)),{'call_id':'call_out_1'})[1]);self.p.start()
 def tearDown(self):self.p.stop();self.ctx.__exit__(None,None,None)
 def fn(self,name,args,call_id='call_s1'):
  raw=json.dumps({'name':name,'call':{'call_id':call_id,'from_number':'+15555551234','to_number':'+15555550999','direction':'inbound'},'args':args})
  r=self.c.post(f'/retell/fn/{name}',content=raw,headers={'x-retell-signature':symmetric['sign'](raw,'test-key')})
  self.assertEqual(r.status_code,200,r.text);return r.json()
 def test_calls_the_security_skilled_teammate_with_a_briefing(self):
  out=self.fn('brief_security',ARGS)
  self.assertEqual(out['status'],'calling');self.assertEqual(out['security_name'],'Guard Two')
  path,body=self.placed[0]
  self.assertEqual(path,'/v2/create-phone-call');self.assertEqual(body['to_number'],'+15555550002')
  self.assertEqual(body['from_number'],'+15555550999');self.assertEqual(body['override_agent_id'],S.SECURITY_AGENT_ID)
  brief=body['retell_llm_dynamic_variables']['briefing']
  for want in ('forced open','already happened','Unit 4B','someone broke into my place','1 2 3 4'):self.assertIn(want,brief)
  self.assertNotIn('5555551234',brief)  # caller's full number never goes into the briefing
  with connect() as c:
   self.assertTrue(c.execute("SELECT 1 FROM events WHERE message LIKE '%security briefing%'").fetchone())
 def test_retry_does_not_call_twice(self):
  self.fn('brief_security',ARGS);self.fn('brief_security',ARGS)
  self.assertEqual(len(self.placed),1)
 def test_in_progress_is_flagged(self):
  self.fn('brief_security',{**ARGS,'in_progress':True})
  v=self.placed[0][1]['retell_llm_dynamic_variables']
  self.assertEqual(v['in_progress'],'true');self.assertIn('happening now',v['briefing'])
 def test_busy_security_falls_back_to_a_drill_stand_in(self):
  with connect() as c:c.execute("UPDATE responders SET status='busy' WHERE id='t2'")
  out=self.fn('brief_security',ARGS)
  self.assertEqual(out['status'],'calling');self.assertTrue(self.placed)
 def test_retell_failure_is_reported_not_raised(self):
  self.p.stop()
  with patch.object(S,'retell_post',side_effect=OSError('down')):
   out=self.fn('brief_security',ARGS,call_id='call_s2')
  self.p.start()
  self.assertEqual(out['status'],'failed')
 def test_route_to_human_prefers_security_skill(self):
  out=self.fn('route_to_human',{'needs':['security'],'language':'en','severity':'P2','summary':'Break-in found this morning'},call_id='call_s3')
  self.assertEqual(out['responder_name'],'Guard Two')
if __name__=='__main__':unittest.main()
