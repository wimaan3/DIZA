import json,os,tempfile,unittest
os.environ['DIZA_DB']=tempfile.mktemp(suffix='.sqlite3')
os.environ['RETELL_API_KEY']='test-key'
os.environ['DIZA_RESPONDERS']=json.dumps([{'id':'t1','name':'Teammate One','phone':'+15555550001','skills':'evac_logistics,lang:es'},
                                          {'id':'t2','name':'Teammate Two','phone':'+15555550002','skills':'medical,lang:en'}])
os.environ['FORMS_DIR']=tempfile.mkdtemp()
with open(os.path.join(os.environ['FORMS_DIR'],'maintenance_request.yaml'),'w') as f:
 f.write('id: maintenance_request\nroute_pool: general_helper\nfields:\n  - {name: location, required: true, ask: "Which building"}\n  - {name: issue, required: true, ask: "What is broken"}\n  - {name: callback_phone, required: true, validate: phone, ask: "Number"}\nreadback: "{issue} at {location}"\nnext_step_text: "Facilities will follow up."\n')
from backend.app.main import app
from fastapi.testclient import TestClient
from retell.lib.webhook_auth import symmetric
CALL={'call_id':'call_abc123','from_number':'+15555550100'}
class RetellFunctions(unittest.TestCase):
 def setUp(self):
  self.ctx=TestClient(app);self.c=self.ctx.__enter__();self.c.post('/api/demo/reset')
  with __import__('backend.app.main',fromlist=['connect']).connect() as c:c.execute("UPDATE responders SET status='available'")
 def tearDown(self):self.ctx.__exit__(None,None,None)
 def fn(self,name,args,call=CALL):
  raw=json.dumps({'name':name,'call':call,'args':args})
  r=self.c.post(f'/retell/fn/{name}',content=raw,headers={'x-retell-signature':symmetric['sign'](raw,'test-key')})
  self.assertEqual(r.status_code,200,r.text);return r.json()
 def state(self):return self.c.get('/api/state').json()
 def report(self,call_id,hazard='smoke from garage',vuln=()):
  return self.fn('submit_report',{'hazard':hazard,'location_text':'Lake Ave and Altadena Dr','people_at_risk':1,'injured_or_trapped':False,'vulnerability':list(vuln),'language':'es'},{**CALL,'call_id':call_id})
 def test_cluster_match_only_for_real_matches(self):
  self.assertEqual(self.report('c1')['cluster_match'],'')
  self.assertIn('2 reports of smoke',self.report('c2')['cluster_match'])
 def test_vulnerability_and_hazard_raise_severity(self):
  self.assertEqual(self.report('c1',hazard='strange noise outside',vuln=['wheelchair'])['severity'],'P1')
  self.assertEqual(self.report('c2')['severity'],'P1')
 def test_flag_urgent_escalates_never_offers(self):
  out=self.fn('flag_urgent',{'reason':'trapped','keyword':'atrapada'});self.assertIn('911',out['instruction'])
  s=self.state();self.assertEqual(s['reports'][0]['severity'],'P0');self.assertEqual(s['requests'][0]['status'],'escalated');self.assertEqual(s['attempts'],[])
  self.assertIn('988',self.fn('flag_urgent',{'reason':'self_harm','keyword':'hurt myself'},{**CALL,'call_id':'c9'})['instruction'])
 def test_route_to_human_matches_skill_and_language_then_frees_on_call_end(self):
  out=self.fn('route_to_human',{'needs':['evac_logistics'],'language':'es','severity':'P1','summary':'Smoke, wheelchair'})
  self.assertEqual(out['oncall_number'],'+15555550001');self.assertIn('evac_logistics',out['match_reason'])
  again=self.fn('route_to_human',{'needs':['evac_logistics'],'language':'es','severity':'P1','summary':'Smoke, wheelchair'})
  self.assertEqual(again,out)  # Retell retry: same answer, nobody else reserved
  other=self.fn('route_to_human',{'needs':['evac_logistics'],'language':'es','severity':'P1','summary':'x'},{**CALL,'call_id':'c2'})
  self.assertEqual(other['oncall_number'],'+15555550002')
  third=self.fn('route_to_human',{'needs':[],'language':'en','severity':'P2','summary':'x'},{**CALL,'call_id':'c3'})
  self.assertEqual(third['oncall_number'],'');self.assertEqual(third['fallback'],'callback')
  raw=json.dumps({'event':'call_ended','call':{'call_id':'call_abc123'}})
  self.assertEqual(self.c.post('/retell/webhook',content=raw,headers={'x-retell-signature':symmetric['sign'](raw,'test-key')}).status_code,204)
  self.assertEqual(self.fn('route_to_human',{'needs':['evac_logistics'],'language':'es','severity':'P1','summary':'y'},{**CALL,'call_id':'c4'})['oncall_number'],'+15555550001')
 def hook(self,event,call):
  raw=json.dumps({'event':event,'call':call})
  self.assertEqual(self.c.post('/retell/webhook',content=raw,headers={'x-retell-signature':symmetric['sign'](raw,'test-key')}).status_code,204)
 def test_p0_and_full_report_are_one_row(self):
  self.fn('flag_urgent',{'reason':'trapped','keyword':'mi abuela está atrapada'},{**CALL,'call_id':'c7'})
  out=self.report('c7');self.assertEqual(out['severity'],'P0')
  s=self.state();self.assertEqual(len(s['reports']),1);r=s['reports'][0]
  self.assertEqual(r['location'],'Lake Ave and Altadena Dr');self.assertIn('atrapada',r['evidence']);self.assertEqual(len(s['requests']),1)
 def test_calls_logged_from_webhooks_last4_only(self):
  call={**CALL,'call_id':'c8','direction':'inbound','agent_name':'DIZA inbound','start_timestamp':1700000000000}
  self.hook('call_started',call)
  self.assertEqual(self.state()['calls'][0]['status'],'live')
  self.hook('call_ended',{**call,'end_timestamp':1700000095000,'disconnection_reason':'user_hangup'})
  self.hook('call_analyzed',{**call,'call_analysis':{'call_summary':'Caller reported smoke.','user_sentiment':'Neutral'}})
  c=self.state()['calls'][0]
  self.assertEqual((c['status'],c['duration_s'],c['caller_last4'],c['summary']),('ended',95,'0100','Caller reported smoke.'))
  self.assertNotIn('5555550100',json.dumps(self.state()['calls']))
 def test_only_real_responders_and_live_flag(self):
  s=self.state();self.assertEqual({r['id'] for r in s['responders']},{'t1','t2'});self.assertTrue(s['live'])
  self.assertEqual(self.c.post('/api/demo/surge').status_code,403)
 def test_form_loop_prefills_and_needs_confirmation(self):
  start=self.fn('start_form',{'form_type':'maintenance_request','known_fields':{'location':'Birnkrant 214','issue':'heater'}})
  self.assertEqual([f['name'] for f in start['next_fields']],['callback_phone'])
  bad=self.fn('fill_form',{'case_code':start['case_code'],'fields':{'callback_phone':'12'}});self.assertFalse(bad['complete']);self.assertEqual(bad['invalid'][0]['name'],'callback_phone')
  good=self.fn('fill_form',{'case_code':start['case_code'],'fields':{'callback_phone':'213 555 0100'}});self.assertTrue(good['complete']);self.assertEqual(good['readback'],'heater at Birnkrant 214')
  self.assertEqual(self.fn('submit_form',{'case_code':start['case_code'],'confirmed':False})['status'],'incomplete')
  done=self.fn('submit_form',{'case_code':start['case_code'],'confirmed':True});self.assertEqual(done['status'],'new')
  status=self.fn('check_status',{'code':start['case_code'],'phone_last4':'0100'});self.assertIn('received',status['status_text'])
  self.assertIn("couldn't find",self.fn('check_status',{'code':start['case_code'],'phone_last4':'9999'})['status_text'])
 def test_requests_are_idempotent_and_consent_gated(self):
  a=self.fn('create_request',{'type':'errand','details':'medication','location_text':'Expo Park'})
  self.assertEqual(a,self.fn('create_request',{'type':'errand','details':'medication','location_text':'Expo Park'}))
  self.assertEqual(self.fn('notify_contact',{'contact_name':'Ana','contact_phone':'5555550124','message':'safe','consent':False})['status'],'consent_required')
  self.assertEqual(self.fn('enroll_checkin',{'person_name':'Rosa','person_phone':'5555550123','language':'es','needs':[],'frequency':'weekly','enrolled_by':'granddaughter'})['status'],'pending_consent')
  self.assertEqual(self.fn('register_volunteer',{'name':'Min','skills':['translation'],'languages':['ko'],'availability':'evenings','area':'K-town'})['status'],'pending_verification')
 def test_unsigned_function_calls_rejected(self):
  self.assertEqual(self.c.post('/retell/fn/route_to_human',json={'name':'route_to_human','call':CALL,'args':{}}).status_code,401)
if __name__=='__main__':unittest.main()
