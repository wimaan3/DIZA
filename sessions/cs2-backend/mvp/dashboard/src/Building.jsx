import React,{useEffect,useMemo,useRef,useState} from 'react';
import{Building2,Clock,Users,Link2,Languages,Wrench,AlertTriangle,CheckCircle2,Pencil,Plus,X,Scale,DoorOpen,MessageSquare,GitMerge}from'lucide-react';

// Building mode: the manager's queue of tenant tickets. Rules on the backend set urgency, merge duplicates and
// cross-reference related tickets; every reason is shown here. Nothing is hidden: closed and merged tickets stay listed.
const URG=['emergency','urgent','routine'];
const URG_LABEL={emergency:'Emergency',urgent:'Urgent',routine:'Routine'};
const URG_MARK={emergency:'!!',urgent:'!',routine:'·'};
const CAT={water_leak:'Water leak',no_heat:'No heat',no_hot_water:'No hot water',electrical:'Electrical',gas_smell:'Gas smell',lockout:'Lockout',pest:'Pests',appliance:'Appliance',noise:'Noise',security:'Security',other:'Other'};
const STATUS={new:'New',assigned:'Assigned',in_progress:'In progress',waiting_tenant:'Waiting on tenant',closed:'Closed'};
const LANG={en:'English',es:'Spanish',ko:'Korean',zh:'Chinese',vi:'Vietnamese',ru:'Russian',hy:'Armenian',fa:'Persian',tl:'Tagalog',fil:'Filipino'};
const REL={unit:'same unit',stack:'stack',hvac_zone:'HVAC zone',floor:'floor'};
export const dur=s=>{s=Math.max(0,Math.floor(s));const d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);return d?`${d}d ${h}h`:h?`${h}h ${m}m`:`${m}m ${String(s%60).padStart(2,'0')}s`};
const clock=t=>new Date(t*1000).toLocaleString([],{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});

function useNow(){const[n,setN]=useState(Date.now()/1000);useEffect(()=>{const id=setInterval(()=>setN(Date.now()/1000),1000);return()=>clearInterval(id)},[]);return n}

export default function Building({headers,act,onError}){
 const[data,setData]=useState(null),[sel,setSel]=useState(null),[unitFilter,setUnitFilter]=useState(''),[catFilter,setCatFilter]=useState(''),[showClosed,setShowClosed]=useState(false),[edit,setEdit]=useState(false);
 const seen=useRef(null),[fresh,setFresh]=useState({});const now=useNow();
 async function refresh(){try{const r=await fetch('/api/building',{headers});if(!r.ok)throw Error('Building data unavailable');const d=await r.json();
  // A new ticket or a new reporter on an existing one is highlighted for 5 s (not on first load).
  const sig=Object.fromEntries(d.tickets.map(t=>[t.code,t.reporters.length]));
  if(seen.current){const hot=Object.keys(sig).filter(c=>sig[c]!==seen.current[c]);if(hot.length){const until=Date.now()+5000;setFresh(f=>({...f,...Object.fromEntries(hot.map(c=>[c,until]))}))}}
  seen.current=sig;setData(d)}catch(e){onError(e.message)}}
 useEffect(()=>{refresh();const id=setInterval(refresh,1500);return()=>clearInterval(id)},[headers.Authorization]);
 async function run(path,body){if(await act(path,body))refresh()}
 const tickets=data?.tickets||[];
 const byCode=useMemo(()=>Object.fromEntries(tickets.map(t=>[t.code,t])),[data]);
 const units=data?.units||[];const unitOf=Object.fromEntries(units.map(u=>[u.unit,u]));
 const visible=tickets.filter(t=>(!unitFilter||t.unit===unitFilter)&&(!catFilter||t.category===catFilter));
 // Category chips: only categories with open tickets (counted within the unit filter), most common first.
 const cats=Object.entries(tickets.filter(t=>t.status!=='closed'&&!t.merged_into&&(!unitFilter||t.unit===unitFilter)).reduce((a,t)=>({...a,[t.category]:(a[t.category]||0)+1}),{})).sort((a,b)=>b[1]-a[1]);
 const open=visible.filter(t=>t.status!=='closed'&&!t.merged_into);
 const groups=URG.map(u=>[u,open.filter(t=>t.urgency===u).sort((a,b)=>a.created-b.created)]);
 const closed=visible.filter(t=>t.status==='closed'&&!t.merged_into);
 const order=[...groups.flatMap(([,l])=>l),...(showClosed?closed:[])];
 const ticket=byCode[sel]||order[0];
 useEffect(()=>{const key=e=>{if(e.target.closest('input,textarea,select'))return;const i=order.findIndex(t=>t.code===ticket?.code);
  if(e.key==='j'&&order[i+1])setSel(order[i+1].code);if(e.key==='k'&&i>0)setSel(order[i-1].code)};addEventListener('keydown',key);return()=>removeEventListener('keydown',key)});
 if(!data)return <div className="empty"><Building2 size={30}/><h3>Loading the building…</h3></div>;
 const ins=data.insights;
 return <div className="building">
  <div className="stats ins">
   <Stat label="Open tickets" icon={<Wrench/>} value={URG.reduce((a,u)=>a+ins.open_by_urgency[u],0)} detail={URG.map(u=>`${ins.open_by_urgency[u]} ${u}`).join(' · ')} urgent={ins.open_by_urgency.emergency>0}/>
   <Stat label="Median to first human action" icon={<Clock/>} value={ins.median_first_action_s==null?'—':dur(ins.median_first_action_s)} detail="Assign, status, note or tenant notified · last 30 days"/>
   <Stat label="Duplicates merged this week" icon={<GitMerge/>} value={ins.duplicates_merged_week} detail="Every caller is kept on the ticket"/>
   <Stat label="Top repeat problem" icon={<Link2/>} value={ins.top_repeats[0]?`${ins.top_repeats[0].count}×`:'—'} detail={ins.top_repeats.length?ins.top_repeats.slice(0,2).map(r=>`${r.problem} ${r.where}`).join(' · '):'No repeats this week'}/>
   <Stat label="Languages this week" icon={<Languages/>} value={Object.keys(ins.language_mix).length} detail={Object.entries(ins.language_mix).map(([l,n])=>`${LANG[l]||l} ${n}`).join(' · ')||'No calls yet'}/>
  </div>
  <div className="bgrid">
   <section className="panel bqueue"><div className="panel-title"><h2>Ticket queue <span>{open.length}</span></h2>{unitFilter&&<button className="chip-btn" onClick={()=>setUnitFilter('')}>Unit {unitFilter} <X size={12} aria-label="Clear unit filter"/></button>}</div>
    {cats.length>1&&<div className="catfilter" role="group" aria-label="Filter by category"><button className={'chip-btn'+(catFilter?'':' on')} aria-pressed={!catFilter} onClick={()=>setCatFilter('')}>All</button>{cats.map(([c,n])=><button key={c} className={'chip-btn'+(catFilter===c?' on':'')} aria-pressed={catFilter===c} onClick={()=>setCatFilter(catFilter===c?'':c)}>{CAT[c]||c} <span>{n}</span></button>)}</div>}
    <p className="hint">Grouped by urgency, oldest first. <kbd>J</kbd>/<kbd>K</kbd> to move.</p>
    <div className="report-list">{groups.map(([u,list])=><div key={u}><h3 className={'ugroup '+u}><span className={'umark '+u}>{URG_MARK[u]}</span>{URG_LABEL[u]} <span>{list.length}</span><small>target {dur(data.targets[u])}</small></h3>
     {list.length?list.map(t=><TicketRow key={t.code} t={t} now={now} chosen={ticket?.code===t.code} fresh={fresh[t.code]>Date.now()} onClick={()=>setSel(t.code)} children={tickets.filter(x=>x.merged_into===t.code)}/>):<p className="none">None open.</p>}</div>)}
     <button className="text-button closed-toggle" onClick={()=>setShowClosed(!showClosed)}>{showClosed?'Hide':'Show'} closed ({closed.length})</button>
     {showClosed&&closed.map(t=><TicketRow key={t.code} t={t} now={now} chosen={ticket?.code===t.code} onClick={()=>setSel(t.code)} children={[]}/>)}
    </div></section>
   <section className="panel bcard">{ticket?<TicketCard t={ticket} data={data} byCode={byCode} unit={unitOf[ticket.unit]} now={now} run={run} onSelect={setSel}/>:<div className="empty full"><CheckCircle2 size={38}/><h3>No tickets yet.</h3><p>Tenant calls appear here within two seconds.{data.demo&&' Load the demo building from the menu to see a sample week.'}</p></div>}</section>
   <section className="panel bmap"><div className="panel-title"><h2>{data.building.name}</h2><button className={'text-button'+(edit?' on':'')} onClick={()=>setEdit(!edit)} aria-pressed={edit}><Pencil size={13}/>{edit?'Done editing':'Edit units'}</button></div>
    <FloorPlan units={units} tickets={tickets} ticket={ticket} filter={unitFilter} onUnit={u=>edit?null:setUnitFilter(unitFilter===u?'':u)} edit={edit} run={run} buildingId={data.building.id}/>
   </section>
  </div>
 </div>
}

function Stat({label,value,detail,icon,urgent}){return <div className={'stat '+(urgent?'warm':'')}><div className="stat-label">{label}{icon}</div><strong>{value}</strong><small>{detail}</small></div>}

function Age({t,now}){const age=(t.closed_at||now)-t.created,late=!t.closed_at&&!t.first_human_action_at&&age>t.target_s;const over=!t.closed_at&&age>t.target_s;
 return <span className={'age'+(over?' late':'')} title={`Target ${dur(t.target_s)}`}><Clock size={11}/>{dur(age)}{over&&<b> past target</b>}{late&&' · no one has acted'}</span>}

function TicketRow({t,now,chosen,fresh,onClick,children}){
 const groups={};t.related.forEach(l=>(groups[l.relation]??=[]).push(l));
 const top=Object.entries(groups).sort((a,b)=>b[1].length-a[1].length)[0];
 return <button className={'report ticket '+t.urgency+(chosen?' selected':'')+(fresh?' fresh':'')} onClick={onClick} aria-current={chosen}>
  <div className="report-top"><span className={'urg '+t.urgency}>{URG_MARK[t.urgency]} {URG_LABEL[t.urgency]}</span><span className="category">{CAT[t.category]||t.category}</span><span className="time">{t.code}</span></div>
  <strong>Unit {t.unit}{!t.unit_verified&&<em className="warnchip">unit not on file</em>}</strong><p>{t.summary}</p>
  <div className="badges">
   {t.reporters.length>1&&<span className="badge"><Users size={11}/>{t.reporters.length} callers</span>}
   {top&&<span className="badge xref"><Link2 size={11}/>{top[1].length} related, {REL[top[0]]}{top[0]==='stack'||top[0]==='floor'||top[0]==='hvac_zone'?' '+(top[1][0].reason.match(/(?:stack|zone|floor) (\S+)/)?.[1]||''):''}</span>}
   {t.ca_clock&&t.ca_clock.level!=='ok'&&<span className={'badge clock '+t.ca_clock.level}><Scale size={11}/>{t.ca_clock.days} days</span>}
   {children.length>0&&<span className="badge"><GitMerge size={11}/>{children.length} merged in</span>}
  </div>
  <div className="report-bottom"><span className={t.status==='new'?'attention':''}>{STATUS[t.status]}{t.assignee?` · ${t.assignee}`:''}</span><Age t={t} now={now}/></div>
 </button>}

const DANGER=/\b(gas|fire|smoke|burning|sparks?|flood\w*|pouring|everywhere|hurt|bleeding|humo|fuego|incendio)\b/gi;
function Transcript({text}){const lines=(text||'').trim().split('\n').filter(Boolean).slice(-30);
 return <div className="transcript">{lines.map((l,i)=>{const[who,...rest]=l.split(':');return <p key={i}><b className={who.trim().toLowerCase()==='agent'?'ag':'us'}>{who.trim()==='Agent'?'Agent':'Tenant'}</b>{rest.join(':').split(DANGER).map((p,j)=>j%2?<mark key={j}>{p}</mark>:p)}</p>})}</div>}

function TicketCard({t,data,byCode,unit,now,run,onSelect}){
 const[note,setNote]=useState(''),[mergeTo,setMergeTo]=useState('');
 useEffect(()=>{setNote('');setMergeTo('')},[t.code]);
 const calls=t.reporters.map(r=>({r,call:data.calls.find(c=>c.call_id===r.call_id)}));
 const candidates=data.tickets.filter(x=>x.code!==t.code&&!x.merged_into&&x.status!=='closed');
 const staff=data.staff;const who=staff.find(s=>s.id===t.assignee);
 return <><div className="panel-title"><h2>{t.code} · Unit {t.unit}</h2><span className={'urg '+t.urgency}>{URG_MARK[t.urgency]} {URG_LABEL[t.urgency]}</span></div>
 <div className="detail-body">
  <div className="detail-heading"><span>{(CAT[t.category]||t.category).toUpperCase()}</span><span>{STATUS[t.status]}{who?` · ${who.name}`:''}</span></div>
  <h2>{t.summary}</h2>
  <div className="reason"><AlertTriangle size={17}/><div><b>Why {t.urgency}</b><p>{t.urgency_reason}</p><small>Rule-based · target {dur(t.target_s)} · <Age t={t} now={now}/></small></div></div>
  {t.merged_into&&<div className="association"><GitMerge size={18}/><div><b>Merged into {t.merged_into}</b><p>Still listed so nothing is lost. <button className="text-button" onClick={()=>run(`/api/tickets/${t.code}/unmerge`,{})}>Unmerge</button></p></div></div>}
  <div className="facts">
   <div><label>UNIT</label><b>{t.unit}</b>{unit?<small>Floor {unit.floor} · stack {unit.stack} · HVAC {unit.hvac_zone||'—'}</small>:<small className="warn">Not in the building records: confirm with the tenant</small>}</div>
   <div><label>ACCESS</label><b><DoorOpen size={13}/> {t.access_ok==null?'Not asked':t.access_ok?'OK to enter':'Do not enter'}</b><small>{t.access_ok?'Tenant gave permission on the call':'Arrange a time first'}</small></div>
   <div><label>TENANT NOTIFIED</label><b>{t.tenant_notified_at?clock(t.tenant_notified_at):'Not yet'}</b><small>Language: {LANG[t.language]||t.language}</small></div>
  </div>
  {t.ca_clock&&<div className={'caclock '+t.ca_clock.level}><Scale size={16}/><div><b>California repair clock</b><p>{t.ca_clock.text}</p><small>First notice {clock(t.created)}{t.ca_clock.closed?' · stopped at close':''}. Civ. Code §1942: 30 days is presumed reasonable; §1942.4: 35 days after an inspector's notice.</small></div></div>}
  <div className="field"><label>WHAT TENANTS SAID ({t.reporters.length} caller{t.reporters.length!==1?'s':''})</label>
   {calls.map(({r,call},i)=><div className="quote" key={i}><blockquote>“{r.quote||'No quote recorded.'}”</blockquote><small>••{r.last4||'????'} · {LANG[r.language]||r.language} · {clock(r.ts)}{call?.duration_s!=null&&` · ${Math.floor(call.duration_s/60)}:${String(call.duration_s%60).padStart(2,'0')}`}
    {t.reporters.length>1&&<> · <button className="text-button" onClick={()=>run(`/api/tickets/${t.code}/split`,{call_id:r.call_id})}>Split into own ticket</button></>}</small>
    {call?.summary&&<p className="callsum">{call.summary}</p>}{call?.transcript&&<details><summary>Transcript</summary><Transcript text={call.transcript}/></details>}</div>)}
  </div>
  <div className="field"><label>RELATED TICKETS ({t.related.length})</label>{t.related.length?t.related.map(l=>{const o=byCode[l.code];return <button key={l.code} className="related" onClick={()=>onSelect(l.code)}><Link2 size={13}/><span><b>{l.code}{o?` · ${o.unit} · ${STATUS[o.status]}`:''}</b><small>{l.reason}</small></span></button>}):<p className="none tight">No related tickets in the last 7 days (same category, sharing a unit, stack, HVAC zone or floor).</p>}
   {t.related.length>0&&<small className="rulenote">Linked by rule, never closed automatically. You decide whether it is one problem.</small>}</div>
  <div className="handoff"><div className="handoff-title"><h3>Actions</h3></div>
   <div className="actions">
    <label>Assign to<select value={t.assignee||''} onChange={e=>e.target.value&&run(`/api/tickets/${t.code}/assign`,{assignee:e.target.value})}><option value="">Choose staff or vendor…</option>{staff.map(s=><option key={s.id} value={s.id}>{s.name} · {s.role}</option>)}</select></label>
    <label>Status<select value={t.status} onChange={e=>run(`/api/tickets/${t.code}/status`,{status:e.target.value})}>{Object.entries(STATUS).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
    {!t.merged_into&&<label>Merge into<span className="row2"><select value={mergeTo} onChange={e=>setMergeTo(e.target.value)}><option value="">Choose a ticket…</option>{candidates.map(x=><option key={x.code} value={x.code}>{x.code} · {x.unit} · {CAT[x.category]}</option>)}</select><button disabled={!mergeTo} onClick={()=>run(`/api/tickets/${t.code}/merge`,{into:mergeTo})}><GitMerge size={14}/>Merge</button></span></label>}
    <button onClick={()=>run(`/api/tickets/${t.code}/notified`,{})}><MessageSquare size={14}/>Mark tenant notified</button>
   </div>
   <form className="note" onSubmit={e=>{e.preventDefault();if(note.trim())run(`/api/tickets/${t.code}/note`,{text:note.trim()}).then(()=>setNote(''))}}><input value={note} onChange={e=>setNote(e.target.value)} placeholder="Add a note (visible on the timeline)" aria-label="Add a note"/><button type="submit" disabled={!note.trim()}>Add note</button></form>
   <h3 className="tl-title">Timeline</h3>
   <div className="timeline">{t.timeline.map(e=><div key={e.id}><span className={'timeline-dot k-'+e.kind}/><p>{e.message}<small>{clock(e.ts)} · {e.actor}</small></p></div>)}</div>
  </div>
 </div></>}

// Our own building map: an SVG grid of floors x stacks drawn from the units table. No map provider involved.
function FloorPlan({units,tickets,ticket,filter,onUnit,edit,run,buildingId}){
 const[form,setForm]=useState(null);
 const stacks=[...new Set(units.map(u=>u.stack||'?'))].sort(),floors=[...new Set(units.map(u=>u.floor))].sort((a,b)=>b-a);
 const W=64,H=46,G=8,L=34,T=24;
 const pos={};units.forEach(u=>{pos[u.unit]={x:L+stacks.indexOf(u.stack||'?')*(W+G),y:T+floors.indexOf(u.floor)*(H+G)}});
 const worst={},count={};tickets.filter(t=>t.status!=='closed'&&!t.merged_into).forEach(t=>{count[t.unit]=(count[t.unit]||0)+1;if(!worst[t.unit]||URG.indexOf(t.urgency)<URG.indexOf(worst[t.unit]))worst[t.unit]=t.urgency});
 const links=ticket?ticket.related.filter(l=>l.relation!=='unit'):[];const byCode=Object.fromEntries(tickets.map(t=>[t.code,t]));
 const relUnits=new Set(links.map(l=>byCode[l.code]?.unit));
 const hiStack=ticket&&ticket.related.some(l=>l.relation==='stack')?(units.find(u=>u.unit===ticket.unit)?.stack):null;
 const hiZone=ticket&&ticket.related.some(l=>l.relation==='hvac_zone')?(units.find(u=>u.unit===ticket.unit)?.hvac_zone):null;
 const width=L+stacks.length*(W+G),height=T+floors.length*(H+G);
 return <div className="floorplan">
  <svg viewBox={`0 0 ${width} ${height}`} role="group" aria-label="Building floor plan: floors by stack, coloured by the worst open ticket">
   {stacks.map((s,i)=><g key={s}>{s===hiStack&&<rect className="stackhi" x={L+i*(W+G)-4} y={T-4} width={W+8} height={floors.length*(H+G)} rx="8"/>}<text className="axis" x={L+i*(W+G)+W/2} y={14} textAnchor="middle">Stack {s}</text></g>)}
   {floors.map((f,i)=><text key={f} className="axis" x={4} y={T+i*(H+G)+H/2+4}>F{f}</text>)}
   {links.map(l=>{const o=byCode[l.code];const a=pos[ticket.unit],b=o&&pos[o.unit];if(!a||!b)return null;
    return <line key={l.code} className="xline" x1={a.x+W/2} y1={a.y+H/2} x2={b.x+W/2} y2={b.y+H/2}/>})}
   {units.map(u=>{const p=pos[u.unit],w=worst[u.unit],sel=ticket?.unit===u.unit,zone=hiZone&&u.hvac_zone===hiZone,rel=relUnits.has(u.unit);
    return <g key={u.unit} className={'unit '+(w||'clear')+(sel?' sel':'')+(filter===u.unit?' filt':'')+(zone?' zone':'')+(rel?' rel':'')} tabIndex={0} role="button"
     aria-label={`Unit ${u.unit}, floor ${u.floor}, stack ${u.stack}${w?`, ${count[u.unit]} open, worst ${w}`:', no open tickets'}${rel?', related to the selected ticket':''}`}
     onClick={()=>edit?setForm({...u,rename_to:''}):onUnit(u.unit)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();edit?setForm({...u,rename_to:''}):onUnit(u.unit)}}}>
     <rect x={p.x} y={p.y} width={W} height={H} rx="6"/><text x={p.x+8} y={p.y+18} className="uname">{u.unit}</text>
     {w&&<text x={p.x+W-8} y={p.y+18} textAnchor="end" className="umk">{URG_MARK[w]}</text>}
     {w&&<text x={p.x+8} y={p.y+36} className="ucount">{count[u.unit]} open</text>}
     {u.tenant_language&&<text x={p.x+W-8} y={p.y+36} textAnchor="end" className="ulang">{u.tenant_language}</text>}</g>})}
  </svg>
  <div className="legend plan">{URG.map(u=><span key={u}><i className={'sw '+u}/>{URG_MARK[u]} {URG_LABEL[u]}</span>)}<span><i className="sw clear"/>No open tickets</span><span><i className="ln"/>Cross-referenced</span></div>
  <p className="hint">{edit?'Click a unit to rename it or set its floor, stack and HVAC zone.':'Click a unit to filter the queue. Lines join the selected ticket to related units.'}</p>
  {edit&&<button className="text-button" onClick={()=>setForm({unit:'',floor:'',stack:'',hvac_zone:'',isNew:true})}><Plus size={13}/>Add a unit</button>}
  {form&&<form className="unitform" onSubmit={e=>{e.preventDefault();const b={building_id:buildingId,unit:form.unit,floor:form.floor===''?null:Number(form.floor),stack:form.stack||null,hvac_zone:form.hvac_zone||null};if(form.rename_to)b.rename_to=form.rename_to;run('/api/units',b).then(()=>setForm(null))}}>
   <b>{form.isNew?'Add unit':`Edit unit ${form.unit}`}</b>
   {form.isNew?<label>Unit<input required value={form.unit} onChange={e=>setForm({...form,unit:e.target.value})}/></label>:<label>Rename to<input value={form.rename_to} onChange={e=>setForm({...form,rename_to:e.target.value})} placeholder={form.unit}/></label>}
   <label>Floor<input type="number" value={form.floor} onChange={e=>setForm({...form,floor:e.target.value})}/></label>
   <label>Stack / riser<input value={form.stack||''} onChange={e=>setForm({...form,stack:e.target.value})}/></label>
   <label>HVAC zone<input value={form.hvac_zone||''} onChange={e=>setForm({...form,hvac_zone:e.target.value})}/></label>
   <span className="row2"><button className="primary" type="submit">Save</button><button type="button" onClick={()=>setForm(null)}>Cancel</button></span></form>}
 </div>}
