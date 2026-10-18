"""Caller location links: the agent texts a one-time link, the caller taps it and shares GPS from the browser.

This is what 911 centers and tools like Carbyne c-Lite do when carrier location isn't available. Our line never
gets carrier location (ANI/ALI goes only to PSAPs), so the caller's explicit consent on the page is the only source.
Links expire after LINK_TTL seconds; the page says exactly what is shared and why.
"""
import json, os, secrets, time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from .main import Report, connect, event, save_report
from .retell_fns import once, parse

LINK_TTL = 1800
router = APIRouter()


def init_locate():
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS locations(token TEXT PRIMARY KEY,call_id TEXT,created REAL,shared REAL,lat REAL,lon REAL,accuracy REAL)')


def base_url():
    domain = os.getenv('RAILWAY_PUBLIC_DOMAIN', '')  # set by Railway
    return os.getenv('PUBLIC_BASE_URL') or (f'https://{domain}' if domain else 'http://localhost:8000')


def reports_for_call(c, call_id):
    # Reports from phone calls carry the call id at the start of their dedupe key.
    return c.execute('SELECT id FROM reports WHERE substr(dedupe,1,?)=?', (len(call_id) + 1, call_id + ':')).fetchall()


@router.post('/retell/fn/request_location')
def request_location(p=Depends(parse)):
    call, args = p

    def make():
        token = secrets.token_urlsafe(9)
        with connect() as c:
            c.execute('INSERT INTO locations(token,call_id,created) VALUES(?,?,?)', (token, call['call_id'], time.time()))
            event(c, call['call_id'], 'Location link created · waiting for the caller to share')
        return {'link': f'{base_url()}/l/{token}', 'expires_minutes': LINK_TTL // 60}
    return once('request_location', call, args, make)


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Share your location · DIZA</title><style>
body{font-family:system-ui,sans-serif;margin:0;background:#f6f7f3;color:#20362f}main{max-width:440px;margin:auto;padding:28px 20px}
h1{font-size:24px;margin:8px 0 12px}p{line-height:1.55;font-size:15px;color:#4d5e55}button{width:100%;padding:16px;font-size:17px;border:0;border-radius:10px;background:#22553e;color:#fff;margin:18px 0 10px}
.box{background:#fff;border:1px solid #e0e5dc;border-radius:12px;padding:16px;margin-top:14px;font-size:14px}.warn{background:#fff0ea;color:#a5432e;border-color:#f3d2c6}small{color:#7b877a}
</style></head><body><main><b>DIZA Community Line</b><h1>Share your exact location</h1>
<p>Tap the button and allow location. Your position is sent once to the DIZA team for this call so we can find you on our map. Nothing else on your phone is shared.</p>
<button id="b">Share my location</button><div id="s" class="box">%STATUS%</div>
<div class="box warn"><b>In danger right now?</b> Call %EMERGENCY%. DIZA cannot send police, fire or an ambulance.</div>
<p><small>Link expires 30 minutes after it was sent. USC student project; drill use.</small></p></main>
<script>
const s=document.getElementById('s'),b=document.getElementById('b');
b.onclick=()=>{if(!navigator.geolocation){s.textContent='This browser cannot share location. Tell the agent your cross streets or a landmark instead.';return}
s.textContent='Asking your phone for your location…';
navigator.geolocation.getCurrentPosition(async p=>{const r=await fetch(location.pathname,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lat:p.coords.latitude,lon:p.coords.longitude,accuracy:p.coords.accuracy})});
s.textContent=r.ok?'Sent. The DIZA team can now see where you are (within about '+Math.round(p.coords.accuracy)+' m). You can close this page.':'This link has expired. Tell the agent your cross streets instead.';if(r.ok)b.remove()},
e=>{s.textContent=e.code===1?'Location permission was declined. That is okay: tell the agent your cross streets or a landmark.':'Could not get your location. Tell the agent your cross streets or a landmark.'},{enableHighAccuracy:true,timeout:15000,maximumAge:0})};
</script></body></html>"""


def valid(c, token):
    row = c.execute('SELECT * FROM locations WHERE token=?', (token,)).fetchone()
    return row if row and time.time() - row['created'] < LINK_TTL else None


@router.get('/l/{token}', response_class=HTMLResponse)
def location_page(token: str):
    with connect() as c:
        ok = valid(c, token)
    from .regions import region
    return PAGE.replace('%EMERGENCY%', region()['emergency_spoken']).replace('%STATUS%', 'Ready when you are.' if ok else 'This link has expired or is not valid. Tell the agent your cross streets instead.')


class Position(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    accuracy: float = Field(default=0, ge=0, le=100000)


@router.post('/l/{token}')
def share_location(token: str, pos: Position):
    with connect() as c:
        row = valid(c, token)
        if not row:
            raise HTTPException(410, 'Link expired')
        c.execute('UPDATE locations SET shared=?,lat=?,lon=?,accuracy=? WHERE token=?', (time.time(), pos.lat, pos.lon, pos.accuracy, token))
        found = reports_for_call(c, row['call_id'])
    if not found:
        # No report yet on this call: the location alone is still worth a pin for the team.
        save_report(Report(idempotency_key=f"{row['call_id']}:loc", location_text=f'GPS shared by caller ({pos.lat:.5f}, {pos.lon:.5f})',
                           hazard='other', summary='Caller shared their exact location from the DIZA text link', source='retell'))
    with connect() as c:
        for r in reports_for_call(c, row['call_id']):
            c.execute('UPDATE reports SET lat=?,lon=?,geo_tried=1,gps_accuracy=? WHERE id=?', (pos.lat, pos.lon, pos.accuracy, r['id']))
        event(c, row['call_id'], f'Caller shared GPS location (±{round(pos.accuracy)} m)')
    return {'ok': True}


def gps_for_call(c, call_id):
    return c.execute('SELECT lat,lon,accuracy FROM locations WHERE call_id=? AND shared IS NOT NULL ORDER BY shared DESC LIMIT 1', (call_id,)).fetchone()
