import json,os,tempfile,unittest
from unittest.mock import patch
os.environ.setdefault('DIZA_DB',tempfile.mktemp(suffix='.sqlite3'))
os.environ.update(RETELL_API_KEY='test-key',RETELL_FROM_NUMBER='+15555550199',RETELL_ALERT_AGENT_ID='agent_alert_test')
CSV=tempfile.mktemp(suffix='.csv')
open(CSV,'w').write('name,phone,language,opted_out\nRosa Diaz,+15555550001,es,\nMin Park,+15555550002,ko,\nSam Lee,+15555550003,en,\nNo Thanks,+15555550004,en,yes\nBad,555,en,\n')
os.environ['ALERT_CONTACTS_FILE']=CSV
from backend.app.main import app  # main first, as uvicorn does; it imports alerts
from backend.app import alerts
from fastapi.testclient import TestClient
from retell.lib.webhook_auth import symmetric
DRAFT={'mode':'drill','zone_name':'west Altadena','source':'lacounty.gov/emergency',
       'messages':{'en':{'message':'Evacuation warning for west Altadena.','action':'Leave now if you need extra time.'},
                   'es':{'message':'Advertencia de evacuación para el oeste de Altadena.','action':'Salga ahora si necesita más tiempo.'}}}
class Alerts(unittest.TestCase):
 def setUp(self):
  self.ctx=TestClient(app);self.c=self.ctx.__enter__();self.c.post('/api/demo/reset')
 def tearDown(self):self.ctx.__exit__(None,None,None)
 def hook(self,event,recipient,alert_id,**call):
  raw=json.dumps({'event':event,'call':{'call_id':'c_'+recipient+event,'metadata':{'alert_id':alert_id,'recipient':recipient},**call}})
  self.assertEqual(self.c.post('/retell/webhook',content=raw,headers={'x-retell-signature':symmetric['sign'](raw,'test-key')}).status_code,204)
 def send(self):
  aid=self.c.post('/api/alerts',json=DRAFT).json()['id']
  with patch.object(alerts,'retell_post',return_value={'batch_call_id':'batch_1'}) as post:
   out=self.c.post(f'/api/alerts/{aid}/approve',json={'approved_by':'Supervisor Kim'}).json()
  return aid,out,post.call_args[0][1]
 def test_approval_sends_one_batch_to_opted_in_only(self):
  aid,out,body=self.send()
  self.assertEqual(out['calls'],3);self.assertEqual(len(body['tasks']),3);self.assertEqual(body['reserved_concurrency'],8)
  self.assertIn('call_time_window',body)  # drill: 8 AM-9 PM only
  es=[t for t in body['tasks'] if t['to_number'].endswith('0001')][0]['retell_llm_dynamic_variables']
  self.assertTrue(es['alert_message'].startswith('Esto es un simulacro'));self.assertEqual(es['language'],'es')
  ko=[t for t in body['tasks'] if t['to_number'].endswith('0002')][0]
  self.assertEqual(ko['retell_llm_dynamic_variables']['language'],'en')  # no Korean text approved -> English text
  self.assertEqual(self.c.post(f'/api/alerts/{aid}/approve',json={'approved_by':'Again'}).status_code,409)  # no double send
 def test_live_alerts_blocked_by_default(self):
  aid=self.c.post('/api/alerts',json={**DRAFT,'mode':'live'}).json()['id']
  self.assertEqual(self.c.post(f'/api/alerts/{aid}/approve',json={'approved_by':'Kim'}).status_code,403)
 def test_outcomes_tally_and_retry_no_answers(self):
  aid,_,body=self.send();rec={t['to_number'][-4:]:t['metadata']['recipient'] for t in body['tasks']}
  self.hook('call_ended',rec['0001'],aid,disconnection_reason='user_hangup')
  self.hook('call_analyzed',rec['0001'],aid,call_analysis={'custom_analysis_data':{'safe_status':'needs_help'}})
  self.hook('call_ended',rec['0002'],aid,disconnection_reason='dial_no_answer')
  self.hook('call_ended',rec['0003'],aid,disconnection_reason='voicemail_reached')
  self.hook('call_ended',rec['0001'],aid,disconnection_reason='user_hangup')  # late duplicate must not downgrade needs_help
  tally=self.c.get('/api/alerts').json()['alerts'][0]['tally']
  self.assertEqual(tally,{'needs_help':1,'no_answer':1,'voicemail':1})
  with patch.object(alerts,'retell_post',return_value={'batch_call_id':'batch_2'}) as post:
   self.assertEqual(self.c.post(f'/api/alerts/{aid}/retry').json()['calls'],1)
  self.assertEqual([t['to_number'] for t in post.call_args[0][1]['tasks']],['+15555550002'])
if __name__=='__main__':unittest.main()
