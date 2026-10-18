import React,{useEffect,useMemo,useRef,useState} from 'react';
import{AlertTriangle,CheckCircle2,Circle,CircleDot,Clock,GitMerge,Headphones,Layers,MapPin,Phone,PhoneCall,Shield,Users,Zap,Languages,Timer,ArrowDownRight}from'lucide-react';
import LiveMap,{COLOR} from './LiveMap.jsx';
import{t,emergencyText}from'./i18n.js';

// 911 mode: rules on the backend rank the queue, a second reader flags danger the AI may have missed, and every
// reason is shown here. Errors only push up: lowering a priority asks for a reason. Nothing is hidden.
const SEV=['P0','P1','P2','P3'];
const SEV_LABEL={P0:'Life threat',P1:'Urgent',P2:'Needs review',P3:'Information'};
const SEV_MARK={P0:'!!',P1:'!',P2:'·',P3:'i'};
const LANG={en:'English',es:'Spanish',ko:'Korean',zh:'Chinese',vi:'Vietnamese',ru:'Russian',hy:'Armenian',fa:'Persian',tl:'Tagalog',fil:'Filipino'};
const HANDOFF={new:'Unassigned',offered:'Awaiting acceptance',accepted:'Accepted',done:'Completed by responder',escalated:'Needs supervisor'};
const cat=c=>t((c||'other').replaceAll('_',' '));
// Score reasons arrive as English rule names ("trapped", "P1 base", "3 people"); show them in the operator's language.
const reasonLabel=l=>{let m;if((m=l.match(/^(P\d) base$/)))return t('{s} base',{s:m[1]});if((m=l.match(/^(\d+) people$/)))return t('{n} people',{n:m[1]});
 if((m=l.match(/^(\d+) independent callers$/)))return t('{n} independent callers',{n:m[1]});if((m=l.match(/^(\w+) \(possible\)$/)))return `${t(m[1])} ${t('(possible)')}`;return t(l)};
const flagText=f=>t('Possible missed danger: caller said “{w}”',{w:f.word})+(f.message.includes('misheard')?' '+t('(may be “{m}” misheard)',{m:(f.message.match(/'(\w+)' misheard/)||[])[1]||''}):'');
const flagWhy=(f,i)=>f.why.startsWith('AI filed it as')?t('AI filed it as {c}; the caller mentioned {k}',{c:cat(i.category),k:t(f.kind)}):t('AI filed it as {s} {c}; “{k}” implies {i}',{s:i.severity,c:cat(i.category),k:t(f.kind),i:f.implied});
const mmss=s=>`${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,'0')}`;
function useNow(){const[n,setN]=useState(Date.now()/1000);useEffect(()=>{const id=setInterval(()=>setN(Date.now()/1000),1000);return()=>clearInterval(id)},[]);return n}

export default function Ops({headers,act,state,wall,onError,me,setMe}){
 const[data,setData]=useState(null),[sel,setSel]=useState(null),[merge,setMerge]=useState(false);
 const now=useNow(),seen=useRef(null),[fresh,setFresh]=useState({}),[arrivals,setArrivals]=useState([]);
 async function refresh(){try{const r=await fetch('/api/ops',{headers});if(!r.ok)throw Error(t('Operator queue unavailable'));const d=await r.json();
  const ids=new Set(d.incidents.map(i=>i.id));
  if(seen.current){const hot=[...ids].filter(i=>!seen.current.has(i));if(hot.length){const until=Date.now()+5000;setFresh(f=>({...f,...Object.fromEntries(hot.map(i=>[i,until]))}));setArrivals(a=>[...hot,...a.filter(x=>!hot.includes(x))].slice(0,3))}}
  seen.current=ids;setData(d)}catch(e){onError(e.message)}}
 useEffect(()=>{refresh();const id=setInterval(refresh,1500);return()=>clearInterval(id)},[headers.Authorization]);
 // A new report stays announced until the operator opens it: in a long queue it may land far below the fold.
 function show(id){setSel(id);setArrivals(a=>a.filter(x=>x!==id));setTimeout(()=>document.getElementById('q-'+id)?.scrollIntoView({block:'center',behavior:'smooth'}),50)}
 async function run(path,body){const ok=await act(path,body);if(ok)refresh();return ok}
 const inc=data?.incidents||[];
 const urgent=inc.filter(i=>['P0','P1'].includes(i.effective)),routine=inc.filter(i=>!['P0','P1'].includes(i.effective));
 const order=[...urgent,...routine];
 const cur=order.find(i=>i.id===sel)||order[0];
 const operator=me||state.responders[0]?.id||'';
 async function setPriority(i,s){
  const lower=SEV.indexOf(s)>SEV.indexOf(i.severity);
  const reason=lower?prompt(t('Lower {a} → {b}: why? (logged on the card)',{a:i.severity,b:s})):'';
  if(lower&&!reason)return;
  run(`/api/reports/${i.id}/priority`,{severity:s,reason:reason||'',by:nameOf(operator)})}
 function review(i){const reason=prompt(t('Mark reviewed: what did you check? (logged on the card)'));if(reason)run(`/api/reports/${i.id}/reviewed`,{reason,by:nameOf(operator)})}
 const nameOf=id=>state.responders.find(r=>r.id===id)?.name||'operator';
 const take=i=>operator&&run(`/api/reports/${i.id}/take`,{responder_id:operator});
 const callback=i=>run(`/api/reports/${i.id}/callback`,{responder_id:operator});  // the selected teammate gets a call with the caller's number
 // Keyboard: J/K move, T take call, M merge, 1–4 set priority, C callback, R reviewed.
 useEffect(()=>{function key(e){
  if(e.target.closest('input,textarea,select')||e.metaKey||e.ctrlKey||e.altKey||!cur)return;
  const k=e.key.toLowerCase(),at=order.findIndex(i=>i.id===cur.id);
  if(k==='j'||k==='k'){e.preventDefault();const n=order[Math.min(order.length-1,Math.max(0,at+(k==='j'?1:-1)))];if(n){setSel(n.id);document.getElementById('q-'+n.id)?.scrollIntoView({block:'nearest'})}}
  else if(k==='t')take(cur);else if(k==='m')setMerge(true);else if(k==='c')callback(cur);else if(k==='r')review(cur);
  else if('1234'.includes(k)&&k)setPriority(cur,SEV[+k-1]);
 }window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key)},[cur?.id,order.length,operator]);
 if(!data)return <div className="empty"><Clock size={30}/><h3>{t('Loading the operator queue…')}</h3></div>;
 const m=data.metrics;
 const newBar=arrivals.length>0&&<div className="arrivals" role="status" aria-live="polite">{arrivals.map(id=>{const i=inc.find(x=>x.id===id);return i&&<button key={id} className="arrival" onClick={()=>show(id)}><span className={'severity '+i.effective}>{SEV_MARK[i.effective]} {i.effective}</span><b>{t('New report')}</b><span className="where">{i.location.startsWith('(')?t('Location not given yet'):i.location}</span><span className="what">{i.summary}</span><span className="go">{t('Show')} →</span></button>})}<button className="small dismiss" onClick={()=>setArrivals([])} aria-label={t('Dismiss')}>×</button></div>;
 const map=<LiveMap reports={inc} places={state.places} zones={data.zones} center={state.region?.center} selected={cur?.id} onSelect={setSel} tall={wall}
  onPlace={(id,lat,lon)=>run(`/api/reports/${id}/location`,{lat,lon})} onZone={z=>run('/api/zones',{...z,by:nameOf(operator)})} onDeleteZone={id=>run(`/api/zones/${id}/delete`)}/>;
 const lane=(title,list,hint,cls)=><section className={'panel lane '+cls}><div className="panel-title"><h2>{title} <span>{list.length}</span></h2><small>{hint}</small></div>
  <div className="report-list">{list.length?list.map(i=><QueueCard key={i.id} i={i} now={now} on={cur?.id===i.id} fresh={fresh[i.id]>Date.now()} pick={()=>setSel(i.id)}/>):<p className="none">{cls==='urgent'?t('No urgent reports right now.'):t('Nothing waiting.')}</p>}</div></section>;
 if(wall)return <div className="wall">{newBar}<LoadStrip m={m} big/><div className="wall-grid">{map}{lane(t('Urgent'),urgent,t('P0 pinned on top, then score, then wait'),'urgent')}</div></div>;
 return <>
  {newBar}
  <LoadStrip m={m}/>
  <div className="ops-toolbar"><label>{t('I am')} <select value={operator} onChange={e=>setMe(e.target.value)}>{state.responders.map(r=><option key={r.id} value={r.id}>{r.name} · {t(r.status)}</option>)}</select></label>
   <span className="keys"><kbd>J</kbd><kbd>K</kbd> {t('move')} · <kbd>T</kbd> {t('take call')} · <kbd>M</kbd> {t('merge')} · <kbd>1</kbd>–<kbd>4</kbd> {t('priority')} · <kbd>C</kbd> {t('callback')} · <kbd>R</kbd> {t('reviewed')}</span>
   {state.demo&&<button className="small" onClick={()=>run('/api/demo/seed?mode=crisis')}>{t('Load demo: falls & freeway crash')}</button>}{!state.live&&<button className="small" onClick={()=>run('/api/demo/surge')}>{t('Simulate surge')}</button>}<a className="small linkbtn" href="/ops?wall=1" target="_blank" rel="noreferrer">{t('Wall view ↗')}</a></div>
  {map}
  <div className="ops-grid">
   <div className="lanes">{lane(t('Urgent'),urgent,t('P0–P1 · P0 pinned, then score, then wait'),'urgent')}{lane(t('Not urgent'),routine,t('P2–P3 · review, info, follow-ups'),'routine')}</div>
   {cur?<IncidentCard i={cur} all={inc} state={state} now={now} merge={merge} setMerge={setMerge} operator={operator} nameOf={nameOf}
     run={run} setPriority={setPriority} review={review} take={take} callback={callback}/>:<section className="panel detail"><div className="empty full"><Layers size={38}/><h3>{t('No reports yet.')}</h3><p>{t('Calls to the line appear here within seconds. In drill mode, load the demo (elderly falls and a freeway crash) to see a busy night.')}</p></div></section>}
  </div><div className="trends"><LoadStrip m={m} charts/></div></>;
}

function QueueCard({i,now,on,fresh,pick}){
 const wait=i.handled?null:now-i.created,late=wait!=null&&wait>i.target_s,flag=i.flags.length&&!i.reviewed_at;
 const reasons=i.score_reasons.slice(1).map(([l,p])=>`${reasonLabel(l)} +${p}`);
 return <button id={'q-'+i.id} className={'report qcard'+(on?' selected':'')+(fresh?' fresh':'')+(flag?' flagged':'')} onClick={pick} aria-label={`${i.effective} ${cat(i.category)} at ${i.location}`}>
  <div className="report-top"><span className={'severity '+i.effective}>{SEV_MARK[i.effective]} {i.effective}</span><span className="category">{cat(i.category)}</span>
   {wait!=null?<span className={'timer'+(late?' late':'')}><Clock size={11}/>{mmss(wait)}</span>:<span className="timer done"><CheckCircle2 size={11}/>{i.claimed_by?t('taken'):t('handled')}</span>}</div>
  <strong>{i.location.startsWith('(')?t('Location not given yet'):i.location}</strong>
  {flag?<p className="flagline"><AlertTriangle size={12}/>{flagText(i.flags[0])}</p>:<p>{i.summary}</p>}
  <div className="why">{[...reasons,wait!=null&&t('waiting {t}',{t:mmss(wait)})].filter(Boolean).join(' · ')||i.reason}</div>
  <div className="badges">{i.severity!==i.effective&&<span className="b warn">{t('raised from {s}',{s:i.severity})}</span>}{i.corroboration.independent_callers>1&&<span className="b"><Users size={11}/>{t('{n} callers',{n:i.corroboration.independent_callers})}</span>}
   {i.gps_accuracy!=null&&<span className="b ok">GPS</span>}{i.lat==null&&<span className="b warn"><MapPin size={11}/>{t('no pin')}</span>}{i.call_status==='live'&&<span className="b live">{t('on call')}</span>}
   {i.language!=='en'&&<span className="b">{(LANG[i.language]||i.language).slice(0,3).toUpperCase()}</span>}{i.reviewed_at&&<span className="b ok">{t('reviewed')}</span>}</div>
 </button>;
}

function IncidentCard({i,all,state,now,merge,setMerge,operator,nameOf,run,setPriority,review,take,callback}){
 const call=state.calls.find(c=>c.call_id===i.call_id);
 const others=all.filter(x=>x.id!==i.id&&x.cluster_id!==i.cluster_id).sort((a,b)=>(b.category===i.category)-(a.category===i.category));
 const co=i.corroboration,taken=i.claimed_by&&nameOf(i.claimed_by);
 const offer=i.request&&state.attempts.find(a=>a.request_id===i.request.id&&a.status==='offered');
 const words=i.hits.map(w=>w.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'));
 const mark=s=>words.length?s.split(new RegExp(`(${words.join('|')})`,'gi')).map((p,j)=>j%2?<mark key={j}>{p}</mark>:p):s;
 const ok=i.checklist.filter(c=>c.state!=='missing').length;
 return <section className="panel detail incident"><div className="panel-title"><h2>{t('Incident card')}</h2><span className="unverified">{t('UNVERIFIED REPORT')}</span></div><div className="detail-body">
  <div className="detail-heading"><span className={'severity '+i.effective}>{SEV_MARK[i.effective]} {i.effective} · {t(SEV_LABEL[i.effective])}</span><span>{cat(i.category).toUpperCase()}</span>{i.caller_last4&&<span className="muted">{t('Caller ••{x}',{x:i.caller_last4})}</span>}</div>
  <h2>{i.location.startsWith('(')?t('Location not given yet'):i.location}</h2><p className="summary">{i.summary}</p>
  {i.flags.map((f,k)=><div key={k} className={'second-reader'+(i.reviewed_at?' settled':'')} role="alert"><AlertTriangle size={17}/><div><b>{flagText(f)}</b><p>{t('Second reader')}: {flagWhy(f,i)}. {i.reviewed_at?t('Reviewed by {who}: {note}',{who:i.reviewed_by,note:i.review_note}):t('Priority raised until a person reviews it.')}</p></div></div>)}
  <div className="actions">
   <button className="primary" onClick={()=>take(i)} disabled={!operator} title="T">{taken?<><Headphones size={15}/>{t('Taken by {who}',{who:taken})}</>:<><Headphones size={15}/>{t('Take call')} <kbd>T</kbd></>}</button>
   <div className="prio" role="group" aria-label="Set priority">{SEV.map((s,k)=><button key={s} className={'small sev-'+s+(i.severity===s?' on':'')} aria-pressed={i.severity===s} onClick={()=>setPriority(i,s)} title={`${k+1}`}>{s}</button>)}</div>
   <button className="small" onClick={()=>callback(i)} title="C"><PhoneCall size={14}/>{t('Callback')} <kbd>C</kbd></button>
   <button className="small" onClick={()=>review(i)} title="R"><CheckCircle2 size={14}/>{t('Reviewed')} <kbd>R</kbd></button>
   <button className="small" onClick={()=>setMerge(!merge)} title="M"><GitMerge size={14}/>{t('Merge')} <kbd>M</kbd></button>
  </div>
  {merge&&<div className="merge-pick"><label>{t('Link this report to the incident at')}<select autoFocus defaultValue="" onChange={async e=>{if(e.target.value&&await run(`/api/reports/${i.id}/merge`,{into:e.target.value}))setMerge(false)}}><option value="" disabled>{t('Choose an incident…')}</option>{others.slice(0,30).map(x=><option key={x.id} value={x.id}>{x.effective} · {cat(x.category)} · {x.location}</option>)}</select></label>{co.reports>1&&<button className="small" onClick={()=>run(`/api/reports/${i.id}/unmerge`).then(()=>setMerge(false))}>{t('Unlink from its incident')}</button>}<small>{t('Both reports stay listed; only the grouping changes.')}</small></div>}
  {i.request?<div className="handoff"><div className="handoff-title"><h3>{t('Responsibility')}</h3><span className={'status '+i.request.status}>{t(HANDOFF[i.request.status]||i.request.status)}</span></div>
   {i.request.assignee&&<p>{nameOf(i.request.assignee)}{offer&&` · ${t('{n}s to accept',{n:Math.max(0,Math.ceil(offer.expires-now))})}`}</p>}
   {!['accepted','done','offered'].includes(i.request.status)&&!(i.effective==='P0'&&i.request.status==='escalated')&&<button className="small" onClick={()=>run(`/api/requests/${i.request.id}/offer`)}>{i.effective==='P0'?t('Flag for supervisor review'):t('Offer to eligible responder')}</button>}
   {i.effective==='P0'&&<p className="urgent-note">{t('Immediate danger reported. Contact emergency services directly ({num}). DIZA does not dispatch or call them.',{num:emergencyText(state.region)})}</p>}</div>
  :<div className="association"><CheckCircle2 size={18}/><p>{t('Information request recorded. No follow-up task was created.')}</p></div>}
  <div className="why-score"><Zap size={15}/><div><b>{t('Priority score {n}',{n:i.score})}</b><p>{i.score_reasons.map(([l,p])=>`${reasonLabel(l)} +${p}`).join(' · ')}{!i.handled&&` · ${t('waiting {t}',{t:mmss(now-i.created)})}`}</p><small>{t('Rule-based ranking · not a validated emergency triage system.')} {i.reason}</small></div></div>
  <div className="field"><label>{t('COMPLETENESS')} {ok}/{i.checklist.length}</label><ul className="checklist">{i.checklist.map(c=><li key={c.key} className={c.state}>{c.state==='ok'?<CheckCircle2 size={15}/>:c.state==='approx'?<CircleDot size={15}/>:<Circle size={15}/>}<b>{t(c.label)}</b><span>{c.value||(c.state==='missing'?t('Not collected yet'):'')}</span></li>)}</ul></div>
  {(i.gps_accuracy!=null||i.agency)&&<div className="gps"><MapPin size={16}/><div>{i.gps_accuracy!=null&&<><b>{t('Exact location shared by caller')}</b><p>GPS ±{Math.round(i.gps_accuracy)} m · {i.lat.toFixed(5)}, {i.lon.toFixed(5)} · <a href={`https://www.google.com/maps?q=${i.lat},${i.lon}`} target="_blank" rel="noreferrer">{t('Open in Google Maps')}</a></p></>}{i.agency&&<p>{t('Agency for this location:')} <b>{i.agency}</b></p>}</div></div>}
  <div className="field"><label>{t("CALLER'S WORDS")}</label>{i.quotes.length?i.quotes.map((q,k)=><blockquote key={k}>“{mark(q)}”</blockquote>):<blockquote>{t('No caller quote recorded.')}</blockquote>}</div>
  {call?.transcript&&<details className="field" open={call.status==='live'}><summary>{call.status==='live'?t('LIVE TRANSCRIPT'):t('TRANSCRIPT')} · {call.agent||'agent'}</summary><div className={'transcript'+(call.status==='live'?' live':'')}>{call.transcript.trim().split('\n').slice(-30).map((l,k)=>{const[who,...rest]=l.split(':');return <p key={k}><b className={who.trim().toLowerCase()==='agent'?'ag':'us'}>{who.trim()==='Agent'?t('Agent'):t('Caller')}</b>{mark(rest.join(':'))}</p>})}{call.status==='live'&&<span className="typing">● live</span>}</div></details>}
  <div className="field"><label>{t('CORROBORATION · shown, never used to hide a card')}</label><div className="corro">
   <Tile n={co.independent_callers} label={t('independent callers')} d={t('{n} reports in this incident',{n:co.reports})}/>
   <Tile n={co.on_scene} label={t('on scene')} d={t('{n} third party',{n:co.third_party})}/>
   <Tile n={co.gps} label={t('with GPS')} d={t('{n} stated address only',{n:co.stated_address})}/>
   <Tile n={co.callback_answered?t('Yes'):t('No')} label={t('callback answered')} d={t('an outbound call reached them')}/></div></div>
  <div className="field"><label>{t('TIMELINE')}</label><div className="timeline">{i.timeline.length?i.timeline.map((e,k)=><div key={k}><span className="timeline-dot"/><p>{e.message}<small>{new Date(e.ts*1000).toLocaleTimeString()}</small></p></div>):<p className="none">{t('No actions yet.')}</p>}</div></div>
 </div></section>;
}
const Tile=({n,label,d})=><div className="ctile"><strong>{n}</strong><b>{label}</b><small>{d}</small></div>;

// "Load taken off": what the line handled so people didn't have to. Measured from stored calls; estimates say so.
function LoadStrip({m,big,charts}){
 const tiles=[
  {icon:<Phone/>,label:t('Calls handled with no operator'),value:`${m.ai_only}`,of:m.calls?t('of {n}',{n:m.calls}):'',detail:t('{n} warm transfers to a person',{n:m.transferred})},
  {icon:<Users/>,label:t('Callers answered at once (peak)'),value:m.peak_concurrent,detail:t('no hold queue while the AI takes the call')},
  {icon:<Layers/>,label:t('Duplicate reports folded'),value:m.folded,detail:t('{a} reports → {b} incidents',{a:m.reports,b:m.incidents})},
  {icon:<Timer/>,label:t('Operator time saved (estimate)'),value:`${m.minutes_saved}`,of:t('min'),detail:t('{n} answers pre-collected × {s} s each',{n:m.prefilled,s:m.question_seconds})},
  {icon:<Zap/>,label:t('Call to ranked card (median)'),value:m.median_to_card_s==null?'–':mmss(m.median_to_card_s),detail:t('from pickup to a card in this queue')},
  {icon:<ArrowDownRight/>,label:t('Handled outside 911'),value:m.diverted,detail:t('info answered + follow-ups queued')},
 ];
 return <section className={'loadstrip'+(big?' big':'')} aria-label={charts?'Trends, last hour and 24 hours':'Load taken off operators, last 24 hours'}>{!charts&&<div className="load-tiles">{tiles.map(x=><div className="stat" key={x.label}><div className="stat-label">{x.label}{x.icon}</div><strong>{x.value}{x.of&&<em> {x.of}</em>}</strong><small>{x.detail}</small></div>)}</div>}
  {charts&&<div className="load-charts"><Surge buckets={m.buckets}/><Bars title={t('What callers report')} rows={m.categories.map(c=>({k:cat(c.category),v:c.count}))}/><Bars title={t('Languages')} rows={m.languages.map(c=>({k:LANG[c.language]||c.language,v:c.count}))}/></div>}
  {!charts&&(m.waiting_p0>0||m.flags>0)&&<p className="load-alert"><AlertTriangle size={14}/>{m.waiting_p0>0&&t('{n} life-threat reports with nobody on them.',{n:m.waiting_p0})+' '}{m.flags>0&&t('{n} possible missed dangers to review.',{n:m.flags})}</p>}</section>;
}

// Reports per 5 minutes over the last hour, stacked by priority (P0 at the baseline). Hover a column for counts.
function Surge({buckets}){
 const[hover,setHover]=useState(null),[W,setW]=useState(300),box=useRef(null);
 // Draw at the real pixel width so bars, text and the 4 px rounded tops never stretch.
 useEffect(()=>{const ro=new ResizeObserver(([e])=>setW(Math.max(160,e.contentRect.width)));ro.observe(box.current);return()=>ro.disconnect()},[]);
 const H=110,pad=18,bw=(W-pad)/buckets.length,max=Math.max(1,...buckets.map(b=>SEV.reduce((a,s)=>a+b[s],0)));
 const y=v=>(H-14)*v/max;
 return <figure className="chart"><figcaption>{t('Reports per 5 min · last hour')}</figcaption>
  <div className="chart-box" ref={box}><svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Reports per 5 minutes. Most recent: ${SEV.map(s=>`${buckets.at(-1)[s]} ${s}`).join(', ')}`}>
   <line x1={pad} x2={W} y1={H-12} y2={H-12} className="axis"/><text x={pad-4} y={H-12-y(max)+4} className="tick" textAnchor="end">{max}</text><line x1={pad} x2={W} y1={H-12-y(max)} y2={H-12-y(max)} className="grid"/>
   {buckets.map((b,k)=>{let base=H-12;const x=pad+k*bw+2,w=bw-4,parts=SEV.filter(s=>b[s]);
    return <g key={k} onMouseEnter={()=>setHover(k)} onMouseLeave={()=>setHover(null)}>{parts.map((s,j)=>{const h=y(b[s]),top=j===parts.length-1;base-=h;const r=<path key={s} d={top?`M${x},${base+h} V${base+Math.min(4,h)} Q${x},${base} ${x+Math.min(4,w/2)},${base} H${x+w-Math.min(4,w/2)} Q${x+w},${base} ${x+w},${base+Math.min(4,h)} V${base+h} Z`:`M${x},${base+h} V${base} H${x+w} V${base+h} Z`} fill={COLOR[s]} stroke="#fcfcfb" strokeWidth="1"/>;return r})}
     <rect x={pad+k*bw} y={0} width={bw} height={H-12} fill="transparent"/></g>})}
   <text x={pad} y={H-1} className="tick">{t('−60 min')}</text><text x={W} y={H-1} className="tick" textAnchor="end">{t('now')}</text></svg>
   {hover!=null&&<div className="tip" style={{left:`${(pad+hover*bw+bw/2)/W*100}%`}}><b>{new Date(buckets[hover].start*1000).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}–{new Date((buckets[hover].start+300)*1000).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</b>{SEV.map(s=><span key={s}><i style={{background:COLOR[s]}}/>{s} {buckets[hover][s]}</span>)}</div>}</div>
  <div className="legend">{SEV.map(s=><span key={s}><i style={{background:COLOR[s]}}/>{s}</span>)}</div></figure>;
}

function Bars({title,rows}){
 const max=Math.max(1,...rows.map(r=>r.v));
 return <figure className="chart bars"><figcaption>{title}</figcaption>{rows.length?<div className="hbars">{rows.map(r=><div key={r.k} className="hbar" title={`${r.k}: ${r.v}`}><span className="k">{r.k}</span><span className="track"><i style={{width:`${r.v/max*100}%`}}/></span><span className="v">{r.v}</span></div>)}</div>:<p className="none">{t('No reports in the last 24 h.')}</p>}</figure>;
}
