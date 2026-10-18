import json,os,tempfile,time,unittest
os.environ['DIZA_DB']=tempfile.mktemp(suffix='.sqlite3')
os.environ['RETELL_API_KEY']='test-key'
os.environ['DIZA_RESPONDERS']=json.dumps([{'id':'op1','name':'Operator One','phone':'+15555550001','skills':'medical,lang:en'},
                                          {'id':'op2','name':'Operator Two','phone':'+15555550002','skills':'logistics,lang:es'}])
from backend.app.main import app,connect
from backend.app import ops as O, resources as R
from fastapi.testclient import TestClient
from retell.lib.webhook_auth import symmetric
# No network in tests: a fixed gazetteer stands in for the geocoder.
SPOTS={'Kansas City':(39.10,-94.58),'Wichita':(37.69,-97.34),'Tulsa':(36.16,-95.99),'Lake Ave and Altadena Dr':(34.19,-118.13)}
R.geocode=lambda text,deadline:SPOTS.get(text)

class SecondReader(unittest.TestCase):
 def kinds(self,text):return {h['kind'] for h in O.danger_hits(text)}
 def test_languages(self):
  for text,kind in [('my grandmother is trapped upstairs','trapped'),('mi mamá está atrapada','trapped'),('차 안에 갇혔어요','trapped'),('我们被困在楼上','trapped'),
                    ('chúng tôi bị mắc kẹt','trapped'),('мы застряли в доме','trapped'),('մենք փակված ենք','trapped'),('ما گیر افتاده ایم','trapped'),('kami ay nakulong','trapped'),
                    ("he can't breathe",'breathing'),('no puede respirar','breathing'),('Мой сосед без сознания','unconscious'),('有人开枪','weapon'),('hay humo','smoke'),
                    ('Cháy lớn gần nhà tôi','fire'),('آتش همه جا هست','fire')]:
   self.assertIn(kind,self.kinds(text),text)
 def test_negation_and_innocent_words(self):
  self.assertNotIn('trapped',self.kinds('no one is trapped, we all got out'))
  self.assertNotIn('injured',self.kinds("nobody is hurt"))
  self.assertNotIn('weapon',self.kinds('칼국수 먹고 있었어요'))  # noodles, not a knife
  self.assertIn('trapped',self.kinds('no, my mom is trapped'))
 def test_falls(self):
  for text in ("she fell in the bathroom and can't get up",'Mi abuela se cayó','我爷爷摔倒了，起不来','할머니가 넘어졌어요','Мой сосед упал','nahulog si lola'):
   self.assertIn('fall',self.kinds(text),text)
  self.assertNotIn('fall',self.kinds('I fell asleep on the couch'))
  self.assertIn('unconscious',self.kinds("he's not responding"))
  f=O.second_reader('P2','welfare_check',O.danger_hits('我爷爷摔倒了，起不来'));self.assertEqual(f[0]['implied'],'P1')
 def test_soundalikes(self):
  h=[x for x in O.danger_hits('I think he has a kite in his hand') if x['kind']=='weapon']
  self.assertEqual(h[0]['soundalike'],'knife')
  self.assertEqual(O.danger_hits('he pulled a gone on me')[0]['soundalike'],'gun')
  self.assertFalse([x for x in O.danger_hits('the kids are flying a kite') if x['kind']=='weapon'])
 def test_flags_only_on_disagreement(self):
  hits=O.danger_hits('the power is out and my grandmother is trapped upstairs')
  f=O.second_reader('P2','power',hits);self.assertEqual(f[0]['implied'],'P0');self.assertIn("caller said 'trapped'",f[0]['message'])
  self.assertEqual(O.second_reader('P0','fire',O.danger_hits('there is fire and someone is trapped')),[])
  self.assertTrue(O.second_reader('P1','power',O.danger_hits('he has a gun')))  # category disagrees
 def test_rank_reasons(self):
  score,reasons=O.rank('P1',O.danger_hits('my dad is trapped'),['wheelchair'],4,3)
  self.assertEqual(reasons,[('P1 base',70),('trapped',40),('wheelchair',10),('4 people',10),('3 independent callers',10)]);self.assertEqual(score,140)
 def test_place_list(self):
  self.assertEqual(R.place_list('Kansas City, Wichita, and Tulsa'),['Kansas City','Wichita','Tulsa'])
  for keep in ('Lake Ave and Altadena Dr','Wichita, Kansas','Los Angeles, CA','123 Main St, Tulsa','Building A'):self.assertEqual(R.place_list(keep),[],keep)

class Api(unittest.TestCase):
 def setUp(self):
  self.ctx=TestClient(app);self.c=self.ctx.__enter__();self.c.post('/api/demo/reset')
 def tearDown(self):self.ctx.__exit__(None,None,None)
 def fn(self,name,args,call_id='call_o1'):
  raw=json.dumps({'name':name,'call':{'call_id':call_id,'from_number':'+15555550100','to_number':'+15555550999','direction':'inbound'},'args':args})
  r=self.c.post(f'/retell/fn/{name}',content=raw,headers={'x-retell-signature':symmetric['sign'](raw,'test-key')})
  self.assertEqual(r.status_code,200,r.text);return r.json()
 def ops(self):return self.c.get('/api/ops').json()
 def wait(self,cond):
  for _ in range(40):
   d=self.ops()
   if cond(d):return d
   time.sleep(0.05)
  return d
 def report(self,loc='Lake Ave and Altadena Dr',hazard='fire',call_id='call_o1',**kw):
  return self.fn('submit_report',{'hazard':hazard,'location_text':loc,'people_at_risk':1,'injured_or_trapped':False,'vulnerability':[],'language':'en','summary':'Report',**kw},call_id)
 def test_three_cities_in_one_call_become_three_pins(self):
  self.fn('flag_urgent',{'reason':'keypad_hurt','keyword':'elderly person fell'},'call_k')
  self.report('Kansas City, Wichita, and Tulsa','medical','call_k',summary='elderly person fell')
  d=self.wait(lambda d:sum(i['lat'] is not None for i in d['incidents'])==3)
  got=sorted((i['location'],i['lat'],i['effective']) for i in d['incidents'])
  self.assertEqual(got,[('Kansas City',39.10,'P0'),('Tulsa',36.16,'P0'),('Wichita',37.69,'P0')])
  self.assertTrue(all('One of 3 places' in i['summary'] and i['call_id']=='call_k' and i['request'] for i in d['incidents']))
  self.assertEqual(len({i['cluster_id'] for i in d['incidents']}),3)
 def test_update_incident_fills_card_and_reports_missing(self):
  self.fn('flag_urgent',{'reason':'trapped','keyword':'stuck'},'call_u')
  out=self.fn('update_incident',{'field':'people','value':'3 adults'},'call_u')
  self.assertTrue(out['ok']);self.assertIn('location',out['missing']);self.assertNotIn('people',out['missing'])
  out=self.fn('update_incident',{'field':'location','value':'Lake Ave and Altadena Dr'},'call_u')
  self.assertNotIn('location',out['missing'])
  d=self.wait(lambda d:d['incidents'][0]['lat'] is not None)
  i=d['incidents'][0];self.assertEqual(i['location'],'Lake Ave and Altadena Dr');self.assertEqual(i['fields']['people'],'3 adults')
  self.assertFalse(self.fn('update_incident',{'field':'shoe_size','value':'9'},'call_u')['ok'])
 def test_errors_only_push_up_and_lowering_needs_reason(self):
  with connect() as c:c.execute("INSERT INTO calls(call_id,direction,caller_last4,status,started,transcript) VALUES('call_p','inbound','0100','live',?,?)",(time.time(),'Agent: Hi\nUser: the power is out and my grandmother is trapped upstairs'))
  rid=self.report('Lincoln Ave','power','call_p',people_at_risk=0)['report_id']
  i=self.ops()['incidents'][0];self.assertEqual((i['severity'],i['effective']),('P2','P0'));self.assertIn('trapped',i['flags'][0]['message'])
  self.assertEqual(self.c.post(f'/api/reports/{rid}/priority',json={'severity':'P3'}).status_code,400)
  self.assertEqual(self.c.post(f'/api/reports/{rid}/priority',json={'severity':'P1','reason':'called back: grandmother got out','by':'Op'}).status_code,200)
  i=self.ops()['incidents'][0];self.assertEqual((i['severity'],i['effective']),('P1','P1'));self.assertTrue(i['flags'])  # flag still shown after review
  self.assertTrue(any('lowered priority P0 → P1' in e['message'] for e in i['timeline']))  # judged against the P0 the operator saw
 def test_take_call_routes_next_transfer_to_that_operator(self):
  rid=self.report(call_id='call_t')['report_id']
  self.assertEqual(self.c.post(f'/api/reports/{rid}/take',json={'responder_id':'op2'}).status_code,200)
  out=self.fn('route_to_human',{'needs':['medical'],'language':'en','severity':'P1','summary':'x'},'call_t')
  self.assertEqual(out['responder_name'],'Operator Two')
 def test_merge_keeps_both_and_zones(self):
  a=self.report(call_id='c1')['report_id'];b=self.report('Altadena Dr east of Lake','fire','c2')['report_id']
  self.assertEqual(self.c.post(f'/api/reports/{b}/merge',json={'into':a}).status_code,200)
  d=self.ops();self.assertEqual(len(d['incidents']),2);self.assertEqual(len({i['cluster_id'] for i in d['incidents']}),1)
  self.assertEqual(d['metrics']['folded'],1)
  z=self.c.post('/api/zones',json={'name':'Warning','kind':'evacuation_warning','points':[[34.2,-118.1],[34.2,-118.2],[34.1,-118.2]]})
  self.assertEqual(z.status_code,200);self.assertEqual(len(self.ops()['zones']),1)
  self.assertEqual(self.c.post('/api/zones',json={'name':'x','points':[[1,2]]}).status_code,422)
  self.c.post(f"/api/zones/{z.json()['id']}/delete");self.assertEqual(self.ops()['zones'],[])
 def test_regeocode_once_fixes_old_pins_but_not_gps_or_operator(self):
  with connect() as c:
   for rid,loc,gps,src in [('a','Kansas City, Wichita, and Tulsa',None,'retell'),('b','Pasadena',12,'retell'),('c','Placed by operator (1, 2)',None,'retell'),('d','Lake Ave and Altadena Dr',None,'demo')]:
    c.execute("INSERT INTO reports(id,dedupe,cluster_id,location,category,summary,evidence,unknowns,severity,reason,language,source,created,lat,lon,geo_tried,gps_accuracy) VALUES(?,?,?,?,'fire','x','','[]','P1','r','en',?,?,1,1,1,?)",(rid,'call_'+rid+':h',rid,loc,src,time.time(),gps))
   self.assertEqual(O.regeocode_once(c,'t-once'),1);self.assertEqual(O.regeocode_once(c,'t-once'),0)
  d=self.wait(lambda d:sum(i['lat'] is not None for i in d['incidents'])==6)
  self.assertEqual(sorted(i['location'] for i in d['incidents'] if i['source']=='retell' and i['lat']!=1),['Kansas City','Tulsa','Wichita'])
 def test_crisis_seed_and_load_metrics(self):
  self.assertEqual(self.c.post('/api/demo/seed?mode=crisis').json()['created'],16)
  d=self.ops();m=d['metrics'];inc=d['incidents']
  self.assertEqual(inc[0]['effective'],'P0')
  self.assertEqual(m['reports'],16);self.assertGreater(m['folded'],0);self.assertGreater(m['ai_only'],m['transferred']);self.assertEqual(m['transferred'],1)
  self.assertGreaterEqual(m['peak_concurrent'],2);self.assertGreater(m['prefilled'],20)
  flagged={i['location'] for i in inc if i['flags']}
  # The AI filed these lower than the caller's words imply: a trapped crash victim, two falls, an unconscious neighbor.
  self.assertTrue({O.CRASH,'Hill St and College St, Chinatown','Western Ave and 6th St, Koreatown','Fairfax Ave and Santa Monica Blvd'}<=flagged,flagged)
  crash=[i for i in inc if i['location']==O.CRASH][0]
  self.assertEqual(crash['corroboration']['reports'],5);self.assertEqual(crash['corroboration']['independent_callers'],5)
  self.assertEqual(sum(i['lat'] is None for i in inc),2)  # unlocated reports stay listed
if __name__=='__main__':unittest.main()
