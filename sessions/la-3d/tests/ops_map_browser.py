"""Integrated Operations map test against an isolated local server (never production).
Requires OPS_MAP_TEST_DB for the server's disposable SQLite database.
The server must disable Retell and set OPS_API_TOKEN=ops-map-test.
"""
import os,pathlib,sqlite3,httpx
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright,expect
BASE=os.environ.get('OPS_MAP_TEST_URL','http://127.0.0.1:18785')
assert urlparse(BASE).hostname in ('localhost','127.0.0.1'), 'Local test server only'
DB=pathlib.Path(os.environ['OPS_MAP_TEST_DB'])
assert DB.exists()
OUT=pathlib.Path(__file__).resolve().parents[1]/'.artifacts'
OUT.mkdir(exist_ok=True)
client=httpx.Client(base_url=BASE,headers={'Authorization':'Bearer ops-map-test'},timeout=10)
assert client.get('/api/state').json()['live'] is False
ids=[]
for key,location,point in [('one','3D map integration — downtown',(-118.255,34.049)),('two','3D map integration — nearby',(-118.254,34.049)),('pending','Unlocated integration report',None)]:
 r=client.post('/api/reports',json={'idempotency_key':'map-edit-'+key,'location_text':location,'hazard':'info','summary':'Synthetic integration test, no real caller.'})
 assert r.status_code==200,r.text
 rid=r.json()['id'];ids.append(rid)
 with sqlite3.connect(DB) as db:db.execute('UPDATE reports SET geo_tried=1,lat=NULL,lon=NULL WHERE id=?',(rid,))
 if point:assert client.post('/api/reports/'+rid+'/location',json={'lat':point[1],'lon':point[0]}).status_code==200
with sync_playwright() as p:
 browser=p.chromium.launch(channel=os.environ.get('PLAYWRIGHT_CHANNEL','chrome'),headless=True)
 context=browser.new_context(viewport={'width':1500,'height':1100},reduced_motion='reduce')
 context.add_init_script("sessionStorage.setItem('diza-token','ops-map-test')")
 page=context.new_page();errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(BASE+'/ops')
 card=page.locator('.ops-map-3d')
 expect(card.locator('.ops3d-marker')).to_have_count(2,timeout=45000)
 assert page.locator('.leaflet-container').count()==0
 expect(card.get_by_role('button',name='3D',exact=True)).to_have_attribute('aria-pressed','true')
 card.scroll_into_view_if_needed()
 card.get_by_role('button',name='Downtown',exact=True).click()
 card.screenshot(path=str(OUT/'ops-3d-desktop.png'))

 # Existing selection callback, draggable pin persistence and unlocated placement.
 marker=card.locator(f'[data-report-id="{ids[0]}"]')
 marker.click()
 expect(marker.locator('.chosen')).to_have_count(1)
 before=next(x for x in client.get('/api/ops').json()['incidents'] if x['id']==ids[0])
 box=marker.bounding_box();x=box['x']+box['width']/2;y=box['y']+box['height']/2
 with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/'+ids[0]+'/location')) as response:
  page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+50,y+25,steps=12);page.mouse.up()
 assert response.value.status==200
 after=next(x for x in client.get('/api/ops').json()['incidents'] if x['id']==ids[0])
 assert (before['lat'],before['lon'])!=(after['lat'],after['lon'])
 card.get_by_role('button',name='Unlocated integration report · place on map',exact=False).click()
 canvas=card.locator('canvas');bounds=canvas.bounding_box()
 with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/'+ids[2]+'/location')) as response:
  page.mouse.click(bounds['x']+180,bounds['y']+250)
 assert response.value.status==200
 expect(card.locator('.ops3d-marker')).to_have_count(3)
 expect(card.locator('.unlocated')).to_have_count(0)

 # Existing zone create/delete APIs, with coordinates drawn on the 3D canvas.
 card.get_by_role('button',name='Draw zone',exact=True).click()
 for dx,dy in [(110,100),(240,100),(220,220)]:page.mouse.click(bounds['x']+dx,bounds['y']+dy)
 card.get_by_role('button',name='Finish',exact=True).click()
 card.locator('input[name=name]').fill('3D integration zone')
 with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/api/zones')) as response:card.get_by_role('button',name='Save zone',exact=True).click()
 assert response.value.status==200
 expect(card.locator('.zone-list').get_by_text('3D integration zone',exact=False)).to_be_visible()
 page.once('dialog',lambda d:d.accept())
 with page.expect_response(lambda r:r.request.method=='POST' and '/api/zones/' in r.url and r.url.endswith('/delete')) as response:card.get_by_role('button',name='Remove zone 3D integration zone',exact=True).click()
 assert response.value.status==200
 expect(card.get_by_role('button',name='Remove zone 3D integration zone',exact=True)).to_have_count(0)

 card.get_by_role('button',name='2D',exact=True).click()
 expect(card.get_by_role('button',name='2D',exact=True)).to_have_attribute('aria-pressed','true')
 card.get_by_role('button',name='3D',exact=True).click()
 card.get_by_role('button',name='Offline map',exact=True).click()
 expect(card.get_by_role('button',name='3D',exact=True)).to_be_disabled()
 expect(card.locator('.ops3d-marker')).to_have_count(3)
 card.get_by_role('button',name='Offline map on',exact=True).click()
 expect(card.locator('.ops3d-marker')).to_have_count(3)
 for name in ['USC / West Adams','Westwood','Santa Monica','Downtown']:card.get_by_role('button',name=name,exact=True).click()
 card.get_by_role('checkbox',name='Care locations',exact=True).uncheck()
 expect(card.locator('.ops3d-place.care')).to_have_count(0)
 card.get_by_role('checkbox',name='Care locations',exact=True).check()
 expect(card.locator('.ops3d-place.care')).to_have_count(4)
 card.get_by_role('button',name='Westwood',exact=True).click()
 card.get_by_role('button',name='Belmont Village Westwood',exact=True).click()
 expect(card.get_by_role('link',name='Facility website',exact=True)).to_be_visible()
 with page.expect_response(lambda r:r.request.method=='GET' and r.url.endswith('/api/state')):pass
 expect(card.get_by_role('link',name='Facility website',exact=True)).to_be_visible()
 card.get_by_role('checkbox',name='Care locations',exact=True).uncheck()
 expect(card.get_by_role('link',name='Facility website',exact=True)).to_have_count(0)
 card.get_by_role('checkbox',name='Care locations',exact=True).check()
 card.get_by_role('button',name='Downtown',exact=True).click()
 page.set_viewport_size({'width':390,'height':844})
 card.screenshot(path=str(OUT/'ops-3d-mobile.png'))
 assert card.evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
 page.set_viewport_size({'width':1500,'height':1100})
 page.goto(BASE+'/ops?wall=1')
 expect(page.locator('.ops-map-3d.tall .ops3d-marker')).to_have_count(3,timeout=45000)
 assert not errors,errors
 browser.close()
print('PASS: existing /ops and wall view use 3D; selection, drag, unlocated placement, zone create/delete, regions, layers, offline and mobile layout preserve the operational workflow.')
