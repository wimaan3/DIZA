"""Browser verification; start Vite first. pip install playwright; playwright install chromium.
CITY_MAP_URL overrides the local URL. PLAYWRIGHT_CHANNEL=chrome uses installed Chrome.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ARTIFACTS = Path(__file__).resolve().parents[1] / '.artifacts'
ARTIFACTS.mkdir(exist_ok=True)
URL = os.environ.get('CITY_MAP_URL', 'http://127.0.0.1:18783/city-3d/')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel=os.environ.get('PLAYWRIGHT_CHANNEL') or None)
    page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(URL)
    expect(page.get_by_text('3D map ready', exact=True)).to_be_visible(timeout=45000)
    expect(page.locator('canvas')).to_have_count(1)
    page.screenshot(path=str(ARTIFACTS / 'desktop.png'))
    page.get_by_role('button', name='2D', exact=True).click()
    expect(page.get_by_role('button', name='2D', exact=True)).to_have_attribute('aria-pressed','true')
    page.get_by_role('button', name='3D', exact=True).click()
    for name in ['USC / West Adams', 'Westwood', 'Santa Monica']:
        page.get_by_role('button',name=name,exact=True).click()
        expect(page.get_by_role('heading', name=name, exact=True)).to_be_visible()
    page.get_by_role('button',name='LA overview',exact=True).click()
    expect(page.get_by_role('heading',name='Greater Los Angeles')).to_be_visible()
    page.get_by_role('button', name='Sakura Gardens Boyle Heights').click()
    expect(page.get_by_role('heading', name='Sakura Gardens of Los Angeles')).to_be_visible()
    expect(page.get_by_role('link', name='Facility website')).to_have_attribute('href','https://sakuragardenslosangeles.com/contact-us/')
    page.get_by_role('button', name='Close location details').click()
    page.get_by_role('checkbox',name='Care locations',exact=True).uncheck()
    page.get_by_role('checkbox',name='Care locations',exact=True).check()
    page.get_by_role('checkbox',name='Offline outline',exact=True).check()
    expect(page.get_by_text('Offline outline · no 3D buildings',exact=True)).to_be_visible()
    expect(page.get_by_role('button', name='3D', exact=True)).to_be_disabled()
    page.screenshot(path=str(ARTIFACTS / 'offline.png'))

    # Isolate backend behavior: no real records or provider calls.
    responses = {'status':401,'data':{'detail':'Operator token required'}}
    def ops(route):
        route.fulfill(status=responses['status'],content_type='application/json',body=json.dumps(responses['data']))
    page.route('**/api/ops',ops)
    page.get_by_role('button',name='Backend events',exact=True).click()
    expect(page.get_by_text('Operator access required.',exact=False)).to_be_visible()
    page.get_by_role('tab',name='Events',exact=False).click()
    expect(page.get_by_text('Events unavailable. Check the connection above.')).to_be_visible()
    assert 'A caller asks' not in page.locator('.location-list').inner_text()
    responses.update(status=200,data={'incidents':[
        {'id':'test-without-location','location':'Test caller without coordinates','summary':'Test only','effective':'P1','lat':None,'lon':None},
        {'id':'test-located','location':'Test located caller','summary':'Test only','effective':'P2','lat':34.04,'lon':-118.25}], 'zones':[]})
    page.get_by_role('button',name='Connect',exact=True).click()
    expect(page.get_by_role('button',name='Test caller without coordinates Location needed')).to_be_visible()
    page.get_by_role('button',name='Test caller without coordinates Location needed').click()
    expect(page.get_by_text('No usable coordinates.',exact=False)).to_be_visible()
    assert page.locator('.stats strong').all_text_contents() == ['04','02','01']
    responses.update(status=503,data={})
    expect(page.get_by_text('Showing the last successful snapshot.',exact=False)).to_be_visible(timeout=15000)
    responses.update(status=401,data={})
    expect(page.get_by_text('Operator access required.',exact=False)).to_be_visible(timeout=15000)
    expect(page.get_by_role('button',name='Test caller without coordinates Location needed')).to_have_count(0)

    page.get_by_role('button',name='Demo scenarios',exact=True).click()
    page.get_by_role('tab',name='Care directory',exact=False).click()
    page.set_viewport_size({'width':390,'height':844})
    page.get_by_role('checkbox',name='Offline outline',exact=True).uncheck()
    page.get_by_role('button',name='Reset Downtown view').click()
    expect(page.get_by_text('3D map ready',exact=True)).to_be_visible(timeout=45000)
    page.screenshot(path=str(ARTIFACTS / 'mobile.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    assert not errors, errors
    browser.close()
    print('PASS: 3D rendering, areas, facilities, layers, offline, API auth/error recovery, unlocated events, mobile layout; no JS errors.')
