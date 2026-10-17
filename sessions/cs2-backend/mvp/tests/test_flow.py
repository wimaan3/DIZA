import os,tempfile,time,unittest
from concurrent.futures import ThreadPoolExecutor
os.environ['DIZA_DB']=tempfile.mktemp(suffix='.sqlite3')
os.environ.pop('RETELL_API_KEY',None);os.environ.pop('DIZA_RESPONDERS',None)  # simulation mode: no phone line, placeholder team
from backend.app.main import app,connect,expire
from fastapi.testclient import TestClient
class Flows(unittest.TestCase):
 def setUp(self):
  self.ctx=TestClient(app);self.c=self.ctx.__enter__();self.c.post('/api/demo/reset')
 def tearDown(self):self.ctx.__exit__(None,None,None)
 def report(self,key='one',danger=False):
  return self.c.post('/api/reports',json={'idempotency_key':key,'location_text':'Building A','hazard':'power','summary':'Needs accessible exit','needs_assistance':True,'immediate_danger':danger}).json()
 def state(self):return self.c.get('/api/state').json()
 def test_dashboard_routes(self):
  for path in ('/ops','/supporter'):
   response=self.c.get(path)
   self.assertEqual(response.status_code,200)
   self.assertIn('text/html',response.headers['content-type'])
   self.assertIn('<div id="root"></div>',response.text)
 def test_deduplication_and_individual_needs(self):
  a=self.report();b=self.report();d=self.report('two');s=self.state()
  self.assertEqual(a['id'],b['id']);self.assertEqual(a['cluster_id'],d['cluster_id']);self.assertEqual(len(s['requests']),2)
 def test_accept_and_complete(self):
  self.report();q=self.state()['requests'][0]['id'];self.c.post(f'/api/requests/{q}/offer')
  r=self.state()['requests'][0];p=r['assignee'];self.assertEqual(r['status'],'offered')
  self.assertEqual(self.c.post(f'/api/requests/{q}/decision',json={'responder_id':p,'action':'accept'}).status_code,200)
  self.assertEqual(self.c.post(f'/api/requests/{q}/decision',json={'responder_id':p,'action':'accept'}).status_code,409)
  self.c.post(f'/api/requests/{q}/decision',json={'responder_id':p,'action':'resolve'})
  self.assertEqual(self.state()['requests'][0]['status'],'done')
 def test_timeout_uses_backup(self):
  self.report();q=self.state()['requests'][0]['id'];self.c.post(f'/api/requests/{q}/offer');old=self.state()['requests'][0]['assignee']
  with connect() as c:c.execute('UPDATE attempts SET expires=?',(time.time()-1,))
  expire();s=self.state();self.assertNotEqual(s['requests'][0]['assignee'],old);self.assertEqual(s['attempts'][0]['status'],'timed_out')
 def test_urgent_never_regular_callback(self):
  self.report(danger=True);q=self.state()['requests'][0]['id'];self.c.post(f'/api/requests/{q}/offer');s=self.state()
  self.assertEqual(s['requests'][0]['status'],'escalated');self.assertEqual(len(s['attempts']),0)
 def test_concurrent_assignments_reserve_different_people(self):
  self.report('a');self.report('b');ids=[q['id'] for q in self.state()['requests']]
  with ThreadPoolExecutor(2) as pool:list(pool.map(lambda q:self.c.post(f'/api/requests/{q}/offer'),ids))
  assigned=[q['assignee'] for q in self.state()['requests']];self.assertEqual(len(set(assigned)),2)
 def test_no_capacity_stays_visible(self):
  self.report();q=self.state()['requests'][0]['id']
  with connect() as c:c.execute("UPDATE responders SET status='busy'")
  self.c.post(f'/api/requests/{q}/offer');self.assertEqual(self.state()['requests'][0]['status'],'escalated')
 def test_retell_unconfigured_fails_closed(self):
  self.assertIn(self.c.post('/retell/webhook',json={}).status_code,(401,503))
 def test_signed_webhook_and_tampering(self):
  import json
  from unittest.mock import patch
  from retell.lib.webhook_auth import symmetric
  raw=json.dumps({'event':'call_ended','call':{'call_id':'test'}})
  with patch.dict(os.environ,{'RETELL_API_KEY':'test-key'}):
   signature=symmetric['sign'](raw,'test-key')
   self.assertEqual(self.c.post('/retell/webhook',content=raw,headers={'x-retell-signature':signature}).status_code,204)
   self.assertEqual(self.c.post('/retell/webhook',content=raw+' ',headers={'x-retell-signature':signature}).status_code,401)
if __name__=='__main__':unittest.main()
