import json,os,tempfile,time,unittest
from unittest.mock import patch
os.environ['DIZA_DB']=tempfile.mktemp(suffix='.sqlite3')
os.environ['RETELL_API_KEY']='test-key'
os.environ['DIZA_COLD_WEATHER']='true'
os.environ['DIZA_RESPONDERS']=json.dumps([{'id':'t1','name':'Teammate One','phone':'+15555550001','skills':'security,lang:en'}])
RES=tempfile.mktemp(suffix='.yaml')
open(RES,'w').write('''resources:
  - {id: lapd_nonemergency, name: LAPD non-emergency (test), type: police_nonemergency, covers: [Los Angeles, Koreatown, Venice], transfer_ok: true, transfer_number: "+15555550901", source_urls: [https://example.org]}
  - {id: pasadena_pd, name: Pasadena PD non-emergency (test), type: police_nonemergency, covers: [Pasadena, Altadena], transfer_ok: true, transfer_number: "+15555550902", source_urls: [https://example.org]}
  - {id: unverified, name: Not on the allowlist, type: police_nonemergency, covers: [Glendale], transfer_ok: false, transfer_number: "+15555550903"}
''')
os.environ['RESOURCES_FILE']=RES
from backend.app.main import app,connect
from backend.app import building as B
from fastapi.testclient import TestClient
from retell.lib.webhook_auth import symmetric
NOON=1760814000.0   # 2025-10-18 12:00 PDT
NIGHT=1760846400.0  # 2025-10-18 21:00 PDT
class Rules(unittest.TestCase):
 def test_urgency(self):
  for cat,text,want in [('gas_smell','',"emergency"),('other','I smell smoke in the hallway','emergency'),('water_leak','water pouring from the ceiling','emergency'),
                        ('water_leak','leak under the sink',"emergency"),('water_leak','old stain on the ceiling, it stopped','routine'),
                        ('no_hot_water','','urgent'),('electrical','outlet is sparking','emergency'),('electrical','half the outlets are dead','urgent'),
                        ('pest','roaches','routine'),('noise','loud music','routine'),('other','smoke detector chirping, needs a battery','routine'),
                        ('appliance','가스 냄새가 나요','emergency'),('other','有烟','emergency')]:
   self.assertEqual(B.urgency(cat,text,NOON)[0],want,(cat,text))
 def test_urgency_by_time_and_season(self):
  self.assertEqual(B.urgency('lockout','',NIGHT)[0],'urgent');self.assertEqual(B.urgency('lockout','',NOON)[0],'routine')
  self.assertEqual(B.urgency('no_heat','',NOON)[0],'urgent')
  with patch.dict(os.environ,{'DIZA_COLD_WEATHER':'false'}):self.assertEqual(B.urgency('no_heat','',NOON)[0],'routine')
 def test_hint_only_raises(self):
  self.assertEqual(B.urgency('pest','',NOON,'emergency')[0],'emergency')
  self.assertEqual(B.urgency('gas_smell','',NOON,'routine')[0],'emergency')
 def test_unit_normalising(self):
  for raw in ('4b','Unit 4-B','apt #4B','four B',' 4 b '):self.assertEqual(B.norm_unit(raw),'4B',raw)
 def test_california_clock(self):
  day=86400
  self.assertIsNone(B.ca_clock({'category':'noise','created':0}))
  self.assertEqual(B.ca_clock({'category':'no_heat','created':0},5*day)['level'],'ok')
  self.assertEqual(B.ca_clock({'category':'no_heat','created':0},24*day)['level'],'soon')
  c=B.ca_clock({'category':'water_leak','created':0},31*day);self.assertEqual(c['level'],'past_30');self.assertIn('§1942',c['text']);self.assertIn('not legal advice',c['text'])
  c=B.ca_clock({'category':'pest','created':0},40*day);self.assertEqual((c['days'],c['level']),(40,'past_35'));self.assertIn('§1942.4',c['text'])
  self.assertEqual(B.ca_clock({'category':'pest','created':0,'closed_at':3*day},40*day)['days'],3)  # the clock stops when closed
 def test_reason_text(self):
  u={'unit':'6B','stack':'B','floor':6,'hvac_zone':'West'}
  self.assertEqual(B.xref_reason('water_leak','stack',u,['6B','4B','5B']),'3rd leak report on stack B this week (4B, 5B, 6B): likely the same pipe')
  self.assertEqual(B.xref_reason('no_heat','hvac_zone',u,['6B','1A']),'2nd no-heat report in HVAC zone West this week (1A, 6B): likely the same heating system')

class Api(unittest.TestCase):
 def setUp(self):
  self.ctx=TestClient(app);self.c=self.ctx.__enter__();self.c.post('/api/demo/reset')
 def tearDown(self):self.ctx.__exit__(None,None,None)
 def fn(self,name,args,call_id='call_b1',number='+15555550100'):
  raw=json.dumps({'name':name,'call':{'call_id':call_id,'from_number':number,'to_number':'+15555550999','direction':'inbound'},'args':args})
  r=self.c.post(f'/retell/fn/{name}',content=raw,headers={'x-retell-signature':symmetric['sign'](raw,'test-key')})
  self.assertEqual(r.status_code,200,r.text);return r.json()
 def ticket(self,unit,cat='water_leak',call_id='call_b1',quote='Water is coming through my ceiling',number='+15555550100',**kw):
  return self.fn('create_ticket',{'unit':unit,'category':cat,'summary':'Leak','caller_quote':quote,'access_ok':True,'language':'en',**kw},call_id,number)
 def tickets(self):return {t['code']:t for t in self.c.get('/api/building').json()['tickets']}
 def test_lookup_unit_and_unknown_unit(self):
  self.assertEqual(self.fn('lookup_unit',{'unit':'apt 4b'}),{'ok':True,'building':'Larchmont Court Apartments (demo)','unit':'4B','floor':4,'stack':'B'})
  self.assertEqual(self.fn('lookup_unit',{'unit':'9Z'}),{'ok':False,'ask':'Which unit number is on your door?'})
  out=self.ticket('9Z');self.assertEqual(out['ask'],'Which unit number is on your door?')  # still saved: a report is never dropped
  t=self.tickets()[out['code']];self.assertFalse(t['unit_verified']);self.assertTrue(any('not in the building records' in e['message'] for e in t['timeline']))
 def test_create_ticket_contract_and_idempotent_retry(self):
  a=self.ticket('4B');self.assertEqual(a['urgency'],'emergency');self.assertTrue(a['code'].startswith('T-'))
  self.assertEqual(a['eta_text'],"The manager will review it; you'll get updates by text.")
  self.assertEqual(self.ticket('4B'),a)  # Retell retry: stored answer, no second reporter
  t=self.tickets()[a['code']];self.assertEqual(len(t['reporters']),1);self.assertEqual(t['reporters'][0]['last4'],'0100')
  self.assertNotIn('5555550100',json.dumps(self.c.get('/api/building').json()))
 def test_duplicate_merge_within_2h(self):
  a=self.ticket('4B');b=self.ticket('4b',call_id='call_b2',number='+15555550177',quote='Hay agua en el techo')
  self.assertEqual(b['merged_into'],a['code']);t=self.tickets();self.assertEqual(len(t),1);self.assertEqual(len(t[a['code']]['reporters']),2)
  with connect() as c:c.execute('UPDATE tickets SET created=created-?',(3*3600,))
  self.assertNotIn('merged_into',self.ticket('4B',call_id='call_b3'))  # older than 2 h: a new ticket
  self.assertNotIn('merged_into',self.ticket('4B','pest',call_id='call_b4'))  # other category: a new ticket
 def test_cross_reference_stack_reason_both_ways_never_closed(self):
  a=self.ticket('2B',call_id='c1');b=self.ticket('3B',call_id='c2');c=self.ticket('4B',call_id='c3')
  self.assertEqual(c['related_reason'],'3rd leak report on stack B this week (2B, 3B, 4B): likely the same pipe')
  t=self.tickets()
  self.assertEqual({l['code'] for l in t[c['code']]['related']},{a['code'],b['code']})
  self.assertIn(c['code'],{l['code'] for l in t[a['code']]['related']})
  self.assertTrue(all(l['reason'].startswith('3rd') for l in t[a['code']]['related']))  # older links get the updated count
  self.assertTrue(all(x['status']=='new' for x in t.values()))
  self.assertNotIn('related_reason',self.ticket('1E','water_leak',call_id='c4'))  # different stack, zone and floor: not related
 def test_cross_reference_by_zone_and_floor(self):
  self.ticket('1A','no_heat',call_id='c1',quote='no heat');out=self.ticket('3C','no_heat',call_id='c2',quote='no heat')
  self.assertIn('HVAC zone West',out['related_reason']);self.assertIn('heating system',out['related_reason'])
  self.ticket('2D','electrical',call_id='c3',quote='outlets dead');out=self.ticket('2F','electrical',call_id='c4',quote='lights flicker')
  self.assertIn('floor 2',out['related_reason'])
 def test_ticket_status_needs_matching_last4(self):
  code=self.ticket('4B')['code']
  self.assertIn('received',self.fn('ticket_status',{'code':code,'phone_last4':'0100'},'c9')['status_text'])
  self.assertIn("couldn't find",self.fn('ticket_status',{'code':code,'phone_last4':'9999'},'c9')['status_text'])
  self.c.post(f'/api/tickets/{code}/assign',json={'assignee':'plumb'})
  self.assertIn('assigned to our plumber',self.fn('ticket_status',{'code':code[2:],'phone_last4':'0100'},'c9')['status_text'])
 def test_manager_actions_and_first_human_action(self):
  code=self.ticket('4B')['code'];self.assertIsNone(self.tickets()[code]['first_human_action_at'])
  self.assertEqual(self.c.post(f'/api/tickets/{code}/assign',json={'assignee':'nobody'}).status_code,400)
  self.c.post(f'/api/tickets/{code}/assign',json={'assignee':'plumb'});t=self.tickets()[code]
  self.assertEqual((t['status'],t['assignee']),('assigned','plumb'));self.assertIsNotNone(t['first_human_action_at'])
  self.c.post(f'/api/tickets/{code}/note',json={'text':'Shut off valve in 5B'});self.c.post(f'/api/tickets/{code}/notified',json={})
  self.assertEqual(self.c.post(f'/api/tickets/{code}/status',json={'status':'gone'}).status_code,400)
  self.c.post(f'/api/tickets/{code}/status',json={'status':'closed'});t=self.tickets()[code]
  self.assertIsNotNone(t['closed_at']);self.assertIsNotNone(t['tenant_notified_at'])
  self.assertEqual([e['kind'] for e in t['timeline']],['created','assign','note','notified','status'])
 def test_manual_merge_unmerge_and_split(self):
  a=self.ticket('4B',call_id='c1')['code'];b=self.ticket('5A','pest',call_id='c2')['code']
  self.c.post(f'/api/tickets/{b}/merge',json={'into':a});t=self.tickets();self.assertEqual(t[b]['merged_into'],a)
  self.assertIn(b,t)  # merged tickets stay visible
  self.c.post(f'/api/tickets/{b}/unmerge',json={});self.assertIsNone(self.tickets()[b]['merged_into'])
  self.ticket('4B',call_id='c3',number='+15555550177')
  new=self.c.post(f'/api/tickets/{a}/split',json={'call_id':'c3'}).json()['code'];t=self.tickets()
  self.assertEqual(len(t[a]['reporters']),1);self.assertEqual(t[new]['reporters'][0]['last4'],'0177')
 def test_local_contact_drill_and_live(self):
  out=self.fn('local_contact',{'kind':'police_nonemergency','location_text':'Lake Ave, Altadena'})
  self.assertEqual(out['transfer_number'],'+15555550001');self.assertIn('drill stand-in for Pasadena PD',out['name'])
  with patch.object(B,'DEMO',False):
   self.assertEqual(self.fn('local_contact',{'kind':'police_nonemergency','location_text':'Lake Ave, Altadena'},'c2')['transfer_number'],'+15555550902')
   self.assertEqual(self.fn('local_contact',{'kind':'police_nonemergency','location_text':'Venice boardwalk'},'c3')['transfer_number'],'+15555550901')
   self.assertEqual(self.fn('local_contact',{'kind':'police_nonemergency','location_text':'Glendale Galleria'},'c4')['transfer_number'],'')  # not allowlisted
   # Building security has no phone in the environment, so it falls back to the building's police non-emergency line.
   self.assertEqual(self.fn('local_contact',{'kind':'security','building_id':'bldg-demo'},'c5')['transfer_number'],'+15555550901')
  with patch.dict(os.environ,{'DIZA_RESPONDERS':'[]'}):
   self.assertEqual(self.fn('local_contact',{'kind':'security'},'c6'),{'name':'','transfer_number':''})  # drill with no teammate: empty
 def test_transfer_logged_on_ticket(self):
  code=self.ticket('3A','noise',call_id='c7',quote='loud party next door')['code']
  self.fn('local_contact',{'kind':'security'},'c7')
  self.assertTrue(any(e['kind']=='transfer' for e in self.tickets()[code]['timeline']))
 def test_units_edit_and_rename(self):
  code=self.ticket('4B')['code']
  self.c.post('/api/units',json={'unit':'5A','floor':5,'stack':'A','hvac_zone':'West'})
  self.c.post('/api/units',json={'unit':'4B','rename_to':'4B-1'})
  s=self.c.get('/api/building').json();units={u['unit']:u for u in s['units']}
  self.assertIn('5A',units);self.assertIn('4B1',units);self.assertEqual(self.tickets()[code]['unit'],'4B1')
 def test_seed_and_insights(self):
  out=self.c.post('/api/demo/seed?mode=building').json();self.assertEqual(out['created'],11)
  s=self.c.get('/api/building').json();i=s['insights']
  self.assertEqual(i['top_repeats'][0],{'problem':'leak','where':'on stack B','count':3})
  self.assertGreaterEqual(i['duplicates_merged_week'],1);self.assertIn('es',i['language_mix'])
  self.assertTrue(any(t['ca_clock'] and t['ca_clock']['level']=='past_30' for t in s['tickets']))
  self.assertNotIn('after_hours_phone',s['building'])
  start=time.monotonic();self.c.get('/api/building');self.assertLess(time.monotonic()-start,0.5)
if __name__=='__main__':unittest.main()
