import React,{useEffect,useState} from 'react';
import{CheckCircle2,Phone,Wrench,Inbox as InboxIcon}from'lucide-react';
import{t}from'./i18n.js';

// One teammate's work, from both sides: 911 requests offered to them and building tickets assigned to them.
// The same work also reaches them by phone (DIZA calls); these buttons are the dashboard way to answer.
const LABEL={offered:'Offered to you',accepted:'Yours · in progress'};
const TSTATUS={assigned:'Assigned to you',in_progress:'In progress',waiting_tenant:'Waiting on tenant'};
export default function Inbox({data,me,setMe,act,headers,busy}){
 const[building,setBuilding]=useState(null);
 async function load(){try{const r=await fetch('/api/building',{headers});if(r.ok)setBuilding(await r.json())}catch{}}
 useEffect(()=>{load();const id=setInterval(load,3000);return()=>clearInterval(id)},[headers.Authorization]);
 async function run(path,body){if(await act(path,body))load()}
 const requests=data.requests.map(q=>({...q,report:data.reports.find(r=>r.id===q.report_id)})).filter(q=>q.report);
 const mine=requests.filter(q=>q.assignee===me&&['offered','accepted'].includes(q.status));
 const tickets=(building?.tickets||[]).filter(x=>x.assignee===`tm-${me}`&&x.status!=='closed'&&!x.merged_into);
 const who=data.responders.find(r=>r.id===me);
 const attempt=q=>data.attempts.find(a=>a.request_id===q.id&&a.status==='offered');
 return <section className="panel supporter"><div className="panel-title"><h2>{t('Supporter inbox')} <span>{mine.length+tickets.length}</span></h2>
  <select value={me} onChange={e=>setMe(e.target.value)} aria-label="Who are you">{data.responders.map(r=><option key={r.id} value={r.id}>{r.name} · {t(r.status)}</option>)}</select></div>
  <p className="demo-note">Everything assigned to {who?.name||'you'}: 911 requests offered to you and building tickets assigned to you. DIZA also calls you about each one; answer there or here.</p>
  {mine.map(q=>{const a=attempt(q);return <div className="task-card" key={q.id}><div className="task-kind"><Phone size={14}/>911 request · <span className={'severity '+q.report.severity}>{q.report.severity}</span> {LABEL[q.status]}{a&&<small> · {Math.max(0,Math.ceil(a.expires-Date.now()/1000))}s to answer</small>}</div>
   <h2>{q.report.location.startsWith('(')?'Location not given yet':q.report.location}</h2><p>{q.report.summary}</p><p className="subtitle">{q.report.reason}</p>
   <div className="buttons">{q.status==='offered'?<><button className="primary" disabled={busy} onClick={()=>run(`/api/requests/${q.id}/decision`,{responder_id:me,action:'accept'})}>Accept</button><button disabled={busy} onClick={()=>run(`/api/requests/${q.id}/decision`,{responder_id:me,action:'decline'})}>Decline · goes to your backup</button></>
    :<button className="primary" disabled={busy} onClick={()=>run(`/api/requests/${q.id}/decision`,{responder_id:me,action:'resolve'})}>Mark done</button>}</div></div>})}
  {tickets.map(x=><div className="task-card" key={x.code}><div className="task-kind"><Wrench size={14}/>Building ticket {x.code} · <b className={'urg '+x.urgency}>{x.urgency}</b> · {TSTATUS[x.status]||x.status}</div>
   <h2>Unit {x.unit} · {x.category.replaceAll('_',' ')}</h2><p>{x.summary}</p>{x.ca_clock&&<p className="subtitle">{x.ca_clock.text}</p>}
   <div className="buttons">{x.status!=='in_progress'&&<button className="primary" disabled={busy} onClick={()=>run(`/api/tickets/${x.code}/status`,{status:'in_progress',actor:who?.name||'staff'})}>Start</button>}
    <button className={x.status==='in_progress'?'primary':''} disabled={busy} onClick={()=>run(`/api/tickets/${x.code}/status`,{status:'closed',actor:who?.name||'staff'})}>Close · fixed</button>
    <a className="text-button" href="/building">Open in Building</a></div></div>)}
  {!mine.length&&!tickets.length&&<div className="empty"><InboxIcon size={36}/><h3>Nothing assigned to {who?.name||'you'} right now.</h3>
   <p>Work lands here when a manager assigns you a building ticket on <a href="/building">Building</a>, or an operator clicks <b>Offer to eligible responder</b> on a 911 card in <a href="/ops">911 operations</a>. Life-threatening (P0) cards go to the supervisor, not here. DIZA also phones you about each assignment.</p></div>}
 </section>;
}
