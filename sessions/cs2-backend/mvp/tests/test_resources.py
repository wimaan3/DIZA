import json,os,tempfile,unittest
from unittest.mock import patch
os.environ.setdefault('DIZA_DB',tempfile.mktemp(suffix='.sqlite3'))
os.environ['RETELL_API_KEY']='test-key'
RES=tempfile.mktemp(suffix='.yaml')
open(RES,'w').write('''resources:
  - {id: usc_health, name: USC Engemann Student Health Center, type: health_center, address: 1031 W 34th St, city: Los Angeles, lat: 34.024463, lon: -118.287788, eligibility: USC students, transfer_ok: true, transfer_number: "+12137409355", source_urls: [https://studenthealth.usc.edu/]}
  - {id: pcc, name: Pasadena Convention Center, type: shelter_site, address: 300 E Green St, city: Pasadena, lat: null, lon: null, status_note: "Used as an evacuation shelter during the Eaton Fire; open only when activated. Confirm via 211 before sending anyone.", source_urls: [https://www.cityofpasadena.net/]}
  - {id: fairplex, name: Pomona Fairplex, type: shelter_site, address: 1101 W McKinley Ave, city: Pomona, lat: 34.080412, lon: -117.765916, only_for: [large_animals], source_urls: [https://file.lacounty.gov/]}
  - {id: humane, name: Pasadena Humane, type: animal_shelter, address: 361 S Raymond Ave, city: Pasadena, lat: 34.139559, lon: -118.148895, pets_allowed: true, transfer_ok: true, transfer_number: "+16267927151", source_urls: [https://pasadenahumane.org/]}
  - {id: la_211, name: 211 LA County, type: hotline, topics: [utility bills, shelter, food], phone: 2-1-1 or 1-800-339-6993, transfer_ok: true, transfer_number: "+18003396993", source_urls: [https://211la.org]}
''')
os.environ['RESOURCES_FILE']=RES
from backend.app import resources
from backend.app.main import app
from fastapi.testclient import TestClient
from retell.lib.webhook_auth import symmetric
ALTADENA=(34.19,-118.13)
class Lookup(unittest.TestCase):
 def setUp(self):
  self.ctx=TestClient(app);self.c=self.ctx.__enter__();self.c.post('/api/demo/reset')
 def tearDown(self):self.ctx.__exit__(None,None,None)
 def ask(self,question,location='',needs=(),call_id='call_l1'):
  raw=json.dumps({'name':'lookup_info','call':{'call_id':call_id,'from_number':'+15555550100'},'args':{'question':question,'location_text':location,'needs':list(needs)}})
  return self.c.post('/retell/fn/lookup_info',content=raw,headers={'x-retell-signature':symmetric['sign'](raw,'test-key')}).json()
 def test_shelter_never_claims_open_and_skips_large_animal_site(self):
  with patch.object(resources,'geocode',return_value=ALTADENA):
   out=self.ask('where is the nearest shelter','Lake and Woodbury, Pasadena')
  self.assertEqual(out['resource_name'],'Pasadena Convention Center');self.assertIn('Confirm via 211',out['answer'])
 def test_large_animals_go_to_fairplex(self):
  with patch.object(resources,'geocode',return_value=ALTADENA):
   self.assertEqual(self.ask('where can I take my horses','Altadena',['large_animals'])['resource_name'],'Pomona Fairplex')
 def test_distance_and_eligibility(self):
  with patch.object(resources,'geocode',return_value=(34.0205,-118.2856)):
   out=self.ask('I need a doctor, is there a clinic','Leavey Library')
  self.assertIn('USC students only',out['answer']);self.assertIn('miles away',out['answer'])
 def test_hotline_without_location_and_drill_mode_blocks_transfer(self):
  out=self.ask("I can't pay my utility bills, who can help");self.assertEqual(out['resource_name'],'211 LA County')
  self.assertEqual(out['transfer_number'],'')  # DRILL_MODE defaults to true: read the number, never transfer
  with patch('backend.app.retell_fns.DEMO',False):
   self.assertEqual(self.ask("I can't pay my utility bills, who can help",call_id='c2')['transfer_number'],'+18003396993')
 def test_unknown_question_logs_gap_then_supervisor_answer_is_served(self):
  out=self.ask('is the 110 freeway closed near downtown');self.assertTrue(out.get('gap_logged'))
  gap=self.c.get('/api/kb').json()['gaps'][0];self.assertIn('110 freeway',gap['question'])
  self.assertEqual(self.c.post('/api/kb_items',json={'question':'Is the 110 freeway closed near downtown?','answer':'Caltrans reports the 110 is open; check quickmap.dot.ca.gov.','source':'Caltrans QuickMap','approved_by':'supervisor','gap_id':gap['id']}).status_code,200)
  again=self.ask('is the 110 freeway closed near downtown',call_id='c3');self.assertIn('Caltrans',again['answer'])
  self.assertEqual(self.c.get('/api/kb').json()['gaps'],[])
class NamedTown(unittest.TestCase):
 # Offline: a fake Nominatim. The LA-first search finds a street or a building; the town with that exact name wins.
 def fake(self,local,anywhere):
  def get(url,deadline):
   return [local] if 'countrycodes' in url else [anywhere]
  return get
 def geo(self,text,local,anywhere):
  resources._geo_cache.clear()
  with patch.object(resources,'_get_json',self.fake(local,anywhere)):return resources.geocode(text,__import__('time').monotonic()+5)
 def test_building_or_street_loses_to_the_named_town(self):
  bldg={'class':'building','name':'CSU Bakersfield–Antelope Valley','lat':'34.68','lon':'-118.18'}
  town={'class':'boundary','name':'Bakersfield','lat':'35.37','lon':'-119.02'}
  self.assertEqual(self.geo('Bakersfield',bldg,town),(35.37,-119.02))
  self.assertEqual(self.geo('Tulsa',{'class':'highway','name':'Tulsa','lat':'34.27','lon':'-118.46'},{'class':'place','name':'Tulsa','lat':'36.16','lon':'-95.99'}),(36.16,-95.99))
 def test_local_place_with_the_exact_name_stays(self):
  beach={'class':'natural','name':'Venice Beach','lat':'33.98','lon':'-118.47'}
  self.assertEqual(self.geo('Venice Beach',beach,{'class':'place','name':'Venice Beach','lat':'27.0','lon':'-82.4'}),(33.98,-118.47))
  lib={'class':'amenity','name':'Altadena Main Library','lat':'34.19','lon':'-118.14'}
  self.assertEqual(self.geo('Altadena Library',lib,{'class':'amenity','name':'Altadena Main Library','lat':'34.19','lon':'-118.14'}),(34.19,-118.14))
if __name__=='__main__':unittest.main()
