"""Text DIZA from a browser: a chat page that talks to the same Retell text agent as SMS.

SMS to the DIZA number needs carrier (A2P 10DLC) registration first; this page gives people who can't talk
(deaf or hard of hearing, hiding, noisy place) a text channel today. Same rules, tools and dashboard as calls.
"""
import json, os, time, urllib.request
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

router = APIRouter()
MAX_MESSAGES = 40          # per conversation
MAX_CHATS_PER_HOUR = 300   # whole line; protects Retell credits from abuse
_chats = {}                # chat_id -> message count (resets on restart; Retell keeps the real history)
_started = []


def retell(path, body):
    req = urllib.request.Request('https://api.retellai.com' + path, data=json.dumps(body).encode(), method='POST',
                                 headers={'Authorization': 'Bearer ' + os.environ['RETELL_API_KEY'], 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b'{}')


def agent_id():
    # The SMS chat agent created by agents/sms_push.py; its id is in agents/retell.ids.json (not secret).
    if os.getenv('RETELL_SMS_AGENT_ID'):
        return os.environ['RETELL_SMS_AGENT_ID']
    ids = Path(__file__).resolve().parents[5] / 'agents' / 'retell.ids.json'
    return json.loads(ids.read_text()).get('sms', {}).get('chat_agent_id', '') if ids.exists() else ''


@router.post('/text/api/start')
def start():
    if not (os.getenv('RETELL_API_KEY') and agent_id()):
        raise HTTPException(503, 'Texting is not set up on this server')
    now = time.time()
    _started[:] = [t for t in _started if now - t < 3600]
    if len(_started) >= MAX_CHATS_PER_HOUR:
        raise HTTPException(429, 'Too many conversations right now. Please call the line instead.')
    _started.append(now)
    chat = retell('/create-chat', {'agent_id': agent_id()})
    _chats[chat['chat_id']] = 0
    return {'chat_id': chat['chat_id']}


class Message(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


@router.post('/text/api/{chat_id}')
def send(chat_id: str, m: Message):
    if chat_id not in _chats:
        raise HTTPException(404, 'Conversation not found. Reload the page to start again.')
    if _chats[chat_id] >= MAX_MESSAGES:
        raise HTTPException(429, 'This conversation is very long. Please call the line or start a new one.')
    _chats[chat_id] += 1
    r = retell('/create-chat-completion', {'chat_id': chat_id, 'content': m.content})
    return {'replies': [x['content'] for x in r.get('messages', []) if x.get('role') == 'agent' and x.get('content')]}


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Text DIZA</title><style>
:root{color-scheme:light}body{margin:0;font-family:system-ui,sans-serif;background:#f6f7f3;color:#20362f;display:flex;flex-direction:column;height:100dvh}
header{background:#153f32;color:#fff;padding:14px 16px}header b{font-size:17px}header p{margin:4px 0 0;font-size:12px;color:#b8cfc2}
.warn{background:#fff0ea;color:#a5432e;font-size:13px;padding:10px 16px}#log{flex:1;overflow:auto;padding:14px 16px;display:flex;flex-direction:column;gap:8px}
.m{max-width:82%;padding:10px 13px;border-radius:14px;font-size:15px;line-height:1.45;white-space:pre-wrap;word-wrap:break-word}.a{background:#fff;border:1px solid #e0e5dc;align-self:flex-start}.u{background:#22553e;color:#fff;align-self:flex-end}
.a a{color:#22553e}form{display:flex;gap:8px;padding:10px 12px;border-top:1px solid #e0e5dc;background:#fff}input{flex:1;font-size:16px;padding:12px;border:1px solid #dce4d4;border-radius:10px}
button{font-size:16px;padding:0 18px;border:0;border-radius:10px;background:#22553e;color:#fff}button:disabled{opacity:.5}.t{font-size:12px;color:#8b957f;align-self:flex-start}
</style></head><body><header><b>Text the DIZA Community Line</b><p>Automated assistant · English, Español, 한국어, 中文 · USC student project</p></header>
<div class="warn"><b>In danger right now?</b> Call 911 (or text 911 if you can't call). DIZA cannot send police, fire or an ambulance.</div>
<div id="log" aria-live="polite"><div class="m a">Hi, this is the DIZA Community Line (automated). What's going on? You can write in any language.</div></div>
<form id="f"><input id="i" placeholder="Type a message" autocomplete="off" aria-label="Message"><button id="b">Send</button></form>
<script>
let chat=null;const log=document.getElementById('log'),i=document.getElementById('i'),b=document.getElementById('b');
const esc=s=>s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function add(t,who){const d=document.createElement('div');d.className='m '+who;d.innerHTML=esc(t).replace(/(https?:\\/\\/[^\\s]+)/g,'<a href="$1" target="_blank" rel="noopener">$1</a>');log.append(d);log.scrollTop=1e9}
document.getElementById('f').onsubmit=async e=>{e.preventDefault();const t=i.value.trim();if(!t)return;add(t,'u');i.value='';b.disabled=true;
 const typing=document.createElement('div');typing.className='t';typing.textContent='DIZA is typing…';log.append(typing);
 try{if(!chat){const r=await fetch('/text/api/start',{method:'POST'});const j=await r.json();if(!r.ok)throw Error(j.detail);chat=j.chat_id}
  const r=await fetch('/text/api/'+chat,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:t})});const j=await r.json();if(!r.ok)throw Error(j.detail);
  j.replies.forEach(x=>add(x,'a'))}catch(err){add((err.message||'Something went wrong.')+' If this is an emergency, call 911.','a')}finally{typing.remove();b.disabled=false;i.focus()}};
</script></body></html>"""


@router.get('/text', response_class=HTMLResponse)
def page():
    return PAGE
