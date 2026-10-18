import json,os,tempfile,unittest
from unittest.mock import patch
os.environ['DIZA_DB']=tempfile.mktemp(suffix='.sqlite3')
os.environ['RETELL_API_KEY']='test-key'
from backend.app.main import app
from backend.app import regions as G
from backend.app.retell_fns import urgent_instruction
from fastapi.testclient import TestClient
from retell.lib.webhook_auth import symmetric

class Regions(unittest.TestCase):
 def test_us_default(self):
  v=G.agent_variables('+13105550100')
  self.assertEqual(v['emergency_number'],'911');self.assertIn('988',v['crisis_line_name']);self.assertEqual(v['caller_country'],'US')
 def test_china_line_never_says_911_or_988(self):
  with patch.dict(os.environ,{'DIZA_COUNTRY':'CN'}):
   v=G.agent_variables('+8613800000000')
   self.assertEqual(v['emergency_number'],'119 for fire, 120 for an ambulance, or 110 for police');self.assertEqual(v['caller_country'],'CN')
   for text in (json.dumps(v),urgent_instruction('trapped')['instruction'],urgent_instruction('self_harm')['instruction']):
    self.assertNotIn('911',text);self.assertNotIn('988',text)
   self.assertEqual(G.region()['ui_language'],'zh')
 def test_number_follows_the_line_not_the_caller(self):
  # A Chinese tourist calling the LA line must still be told 911.
  v=G.agent_variables('+8613800000000');self.assertEqual((v['emergency_number'],v['caller_country']),('911','CN'))
 def test_calling_codes(self):
  for n,c in [('+85291234567','HK'),('+8613800000000','CN'),('+447700900000','GB'),('+61400000000','AU'),('3105550100','US'),('+37410000000','AM'),('','')]:
   self.assertEqual(G.caller_country(n),c,n)
 def test_unknown_country_falls_back_to_us(self):
  with patch.dict(os.environ,{'DIZA_COUNTRY':'ZZ'}):self.assertEqual(G.region()['country'],'US')

class Api(unittest.TestCase):
 def setUp(self):self.ctx=TestClient(app);self.c=self.ctx.__enter__()
 def tearDown(self):self.ctx.__exit__(None,None,None)
 def test_inbound_webhook_and_pages_use_the_region(self):
  with patch.dict(os.environ,{'DIZA_COUNTRY':'JP'}):
   raw=json.dumps({'event':'call_inbound','call_inbound':{'from_number':'+819012345678','to_number':'+15555550999'}})
   d=self.c.post('/retell/inbound',content=raw,headers={'x-retell-signature':symmetric['sign'](raw,'test-key')}).json()['call_inbound']['dynamic_variables']
   self.assertEqual(d['emergency_number'],'119 for fire or an ambulance, 110 for police');self.assertEqual(d['drill_mode'],'true')
   page=self.c.get('/text').text;self.assertIn('119 for fire',page);self.assertNotIn('911',page)
   self.assertEqual(self.c.get('/api/state').json()['region']['country'],'JP')
if __name__=='__main__':unittest.main()
