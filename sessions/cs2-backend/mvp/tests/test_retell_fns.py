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
  self.hook('call_analyzed',{**call,'scrubbed_call_analysis':{'call_summary':'Caller reported smoke.','user_sentiment':'Neutral'}})
  c=self.state()['calls'][0]
  self.assertEqual((c['status'],c['duration_s'],c['caller_last4'],c['summary']),('ended',95,'0100','Caller reported smoke.'))
  self.assertNotIn('5555550100',json.dumps(self.state()['calls']))
 def test_only_real_responders_and_live_flag(self):
  s=self.state();self.assertEqual({r['id'] for r in s['responders']},{'t1','t2'});self.assertTrue(s['live'])
  self.assertEqual(self.c.post('/api/demo/surge').status_code,403)
 def test_reports_get_map_positions_and_places_listed(self):
  import backend.app.main as m, backend.app.resources as res
  real=res.geocode;res.geocode=lambda text,deadline:(34.18,-118.13) if 'Lake' in text else None
  try:
   self.fn('flag_urgent',{'reason':'trapped','keyword':'stuck'},{**CALL,'call_id':'c10'});m.geocode_pending()
   r=self.state()['reports'][0];self.assertIsNone(r['lat'])  # placeholder location is never geocoded
   self.report('c10');m.geocode_pending();self.wait_pinned();r=self.state()['reports'][0]
   self.assertEqual((r['lat'],r['lon']),(34.18,-118.13))
  finally:res.geocode=real
  self.assertTrue(all(p['lat'] is not None for p in self.state()['places']))
 def test_stuck_responder_freed_without_call_ended(self):
  import backend.app.main as m
  self.assertEqual(self.fn('route_to_human',{'needs':['evac_logistics'],'language':'es','severity':'P1','summary':'x'},{**CALL,'call_id':'c11'})['oncall_number'],'+15555550001')
  with m.connect() as c:c.execute('UPDATE routings SET created=created-?',(m.ROUTE_HOLD+1,))
  m.expire()
  self.assertEqual(next(r for r in self.state()['responders'] if r['id']=='t1')['status'],'available')
 def test_live_transcript_then_scrubbed_copy(self):
  call={**CALL,'call_id':'c12','direction':'inbound','start_timestamp':1700000000000}
  for t in ('Agent: How can I help?','Agent: How can I help?\nUser: smoke at Lake Ave'):
   self.hook('transcript_updated',{**call,'transcript':t})
  self.assertIn('smoke at Lake Ave',self.state()['calls'][0]['transcript'])
  self.hook('call_analyzed',{**call,'transcript':'User: my SSN is 123','scrubbed_transcript':'User: my SSN is [ssn]'})
  self.assertEqual(self.state()['calls'][0]['transcript'],'User: my SSN is [ssn]')
 def test_location_link_pins_the_callers_report(self):
  self.fn('flag_urgent',{'reason':'trapped','keyword':'stuck'},{**CALL,'call_id':'c13'})
  link=self.fn('request_location',{},{**CALL,'call_id':'c13'})['link'];token=link.rsplit('/',1)[1]
  self.assertIn('Share my location',self.c.get(f'/l/{token}').text)
  self.assertEqual(self.c.post(f'/l/{token}',json={'lat':34.0219,'lon':-118.2859,'accuracy':12}).status_code,200)
  r=self.state()['reports'][0];self.assertEqual((r['lat'],r['lon'],r['gps_accuracy']),(34.0219,-118.2859,12))
  import backend.app.main as m;self.report('c13');m.geocode_pending();self.wait_pinned()  # the full report keeps the GPS pin, not a geocode
  r=self.state()['reports'][0];self.assertEqual((r['lat'],r['gps_accuracy']),(34.0219,12))
  self.assertEqual(self.c.post('/l/nope',json={'lat':1,'lon':1}).status_code,410)
 def test_location_without_report_still_pins(self):
  token=self.fn('request_location',{},{**CALL,'call_id':'c14'})['link'].rsplit('/',1)[1]
  self.c.post(f'/l/{token}',json={'lat':34.1,'lon':-118.2,'accuracy':30})
  self.assertEqual(self.state()['reports'][0]['lat'],34.1)
 def test_text_chat_functions_and_page(self):
  raw=json.dumps({'name':'create_request','chat':{'chat_id':'chat_1','agent_id':'a'},'args':{'type':'errand','details':'water','location_text':'Expo Park'}})
  r=self.c.post('/retell/fn/create_request',content=raw,headers={'x-retell-signature':symmetric['sign'](raw,'test-key')})
  self.assertEqual(r.status_code,200,r.text);self.assertTrue(r.json()['code'].startswith('D-'))
  raw=json.dumps({'event':'chat_analyzed','chat':{'chat_id':'chat_1','start_timestamp':1700000000000,'chat_analysis':{'chat_summary':'x'}}})
  self.c.post('/retell/webhook',content=raw,headers={'x-retell-signature':symmetric['sign'](raw,'test-key')})
  self.assertEqual(self.state()['calls'][0]['direction'],'text')
  self.assertIn('Text the DIZA Community Line',self.c.get('/text').text)
 def test_retry_in_same_call_keeps_responder_and_phone_is_e164(self):
  from backend.app.retell_fns import e164
  self.assertEqual([e164(x) for x in ('+1<5555550001>','(555) 555-0001','5555550001','+1 555-555-0001')],['+15555550001']*4)
  a=self.fn('route_to_human',{'needs':['listener'],'language':'en','severity':'P3','summary':'wants a human'},{**CALL,'call_id':'c15'})
  b=self.fn('route_to_human',{'needs':['listener'],'language':'en','severity':'P0','summary':'now urgent'},{**CALL,'call_id':'c15'})
  self.assertTrue(a['oncall_number']);self.assertEqual(a['oncall_number'],b['oncall_number'])
 def test_operator_places_pin(self):
  self.fn('flag_urgent',{'reason':'trapped','keyword':'stuck'},{**CALL,'call_id':'c16'})
  rid=self.state()['reports'][0]['id']
  self.assertEqual(self.c.post(f'/api/reports/{rid}/location',json={'lat':34.02,'lon':-118.28}).status_code,200)
  r=self.state()['reports'][0];self.assertEqual((r['lat'],r['lon']),(34.02,-118.28));self.assertIn('Placed by operator',r['location'])
  self.assertEqual(self.c.post('/api/reports/nope/location',json={'lat':1,'lon':1}).status_code,404)
 def test_removed_responder_stops_getting_calls(self):
  import backend.app.retell_fns as f
  with __import__('backend.app.main',fromlist=['connect']).connect() as c:
   c.execute("INSERT OR REPLACE INTO responders VALUES('old','Old Friend','evac_logistics','available')");c.execute("INSERT OR REPLACE INTO responder_phones VALUES('old','+15555550009')")
  f.init_fns()
  self.assertNotIn('old',{r['id'] for r in self.state()['responders']})
 def test_flag_after_report_upgrades_it(self):
  self.report('c17');self.fn('flag_urgent',{'reason':'trapped','keyword':'stuck'},{**CALL,'call_id':'c17'})
  s=self.state();rs=[r for r in s['reports']]
  self.assertEqual(len(rs),1);self.assertEqual(rs[0]['severity'],'P0');self.assertEqual(rs[0]['location'],'Lake Ave and Altadena Dr')
 def test_four_parallel_callers_all_pinned(self):
  import backend.app.main as m, backend.app.resources as res, time as t
  spots={'Santa Monica':(34.02,-118.49),'Venice Beach':(33.99,-118.47),'Pasadena':(34.15,-118.14),'Burbank':(34.18,-118.31)}
  real=res.geocode;res.geocode=lambda text,deadline:next((v for k,v in spots.items() if k in text),None)
  try:
   from concurrent.futures import ThreadPoolExecutor
   def one(i_loc):
    i,loc=i_loc;return self.fn('submit_report',{'hazard':'fire','location_text':loc,'people_at_risk':1,'injured_or_trapped':False,'vulnerability':[],'language':'en'},{**CALL,'call_id':f'p{i}'})
   with ThreadPoolExecutor(4) as ex: list(ex.map(one,enumerate(['Santa Monica','near Venice Beach','Pasadena','Burbank'])))
   for _ in range(30):
    if all(r['lat'] is not None for r in self.state()['reports']): break
    t.sleep(0.1)
   self.assertEqual(sorted(r['lat'] for r in self.state()['reports']),sorted(v[0] for v in spots.values()))
  finally:res.geocode=real
 def wait_pinned(self):
  import time as t
  for _ in range(40):
   if all(r['geo_tried']==1 for r in self.state()['reports']): return
   t.sleep(0.05)
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
