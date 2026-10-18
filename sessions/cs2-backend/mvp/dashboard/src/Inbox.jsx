import React,{useEffect,useState} from 'react';
import{CheckCircle2,Phone,Wrench,Inbox as InboxIcon}from'lucide-react';
import{t}from'./i18n.js';

// One teammate's work, from both sides: 911 requests offered to them and building tickets assigned to them.
// The same work also reaches them by phone (DIZA calls); these buttons are the dashboard way to answer.
const LABEL={offered:'Offered to you',accepted:'Yours · in progress'};
const TSTATUS={assigned:'Assigned to you',in_progress:'In progress',waiting_tenant:'Waiting on resident'};
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
  <select value={me} onChange={e=>setMe(e.target.value)} aria-label={t('Who are you')}>{data.responders.map(r=><option key={r.id} value={r.id}>{r.name} · {t(r.status)}</option>)}</select></div>
  <p className="demo-note">{t('Everything assigned to {who}: 911 requests offered to you and building tickets assigned to you. DIZA also calls you about each one; answer there or here.',{who:who?.name||t('you')})}</p>
  {mine.map(q=>{const a=attempt(q);return <div className="task-card" key={q.id}><div className="task-kind"><Phone size={14}/>{t('911 request')} · <span className={'severity '+q.report.severity}>{q.report.severity}</span> {t(LABEL[q.status])}{a&&<small> · {t('{n}s to answer',{n:Math.max(0,Math.ceil(a.expires-Date.now()/1000))})}</small>}</div>
   <h2>{q.report.location.startsWith('(')?t('Location not given yet'):q.report.location}</h2><p>{q.report.summary}</p><p className="subtitle">{t(q.report.reason)}</p>
   <div className="buttons">{q.status==='offered'?<><button className="primary" disabled={busy} onClick={()=>run(`/api/requests/${q.id}/decision`,{responder_id:me,action:'accept'})}>{t("Accept")}</button><button disabled={busy} onClick={()=>run(`/api/requests/${q.id}/decision`,{responder_id:me,action:'decline'})}>{t("Decline \u00b7 goes to your backup")}</button></>
    :<button className="primary" disabled={busy} onClick={()=>run(`/api/requests/${q.id}/decision`,{responder_id:me,action:'resolve'})}>{t("Mark done")}</button>}</div></div>})}
  {tickets.map(x=><div className="task-card" key={x.code}><div className="task-kind"><Wrench size={14}/>{t('Resident request {code}',{code:x.code})} · <b className={'urg '+x.urgency}>{t(x.urgency)}</b> · {t(TSTATUS[x.status]||x.status)}</div>
   <h2>{t('Unit {unit}',{unit:x.unit})} · {t(x.category.replaceAll('_',' '))}</h2><p>{x.summary}</p>{x.ca_clock&&<p className="subtitle">{x.ca_clock.text}</p>}
   <div className="buttons">{x.status!=='in_progress'&&<button className="primary" disabled={busy} onClick={()=>run(`/api/tickets/${x.code}/status`,{status:'in_progress',actor:who?.name||'staff'})}>{t("Start")}</button>}
    <button className={x.status==='in_progress'?'primary':''} disabled={busy} onClick={()=>run(`/api/tickets/${x.code}/status`,{status:'closed',actor:who?.name||'staff'})}>{t("Close \u00b7 fixed")}</button>
    <a className="text-button" href="/building">{t("Open in Senior care")}</a></div></div>)}
  {!mine.length&&!tickets.length&&<div className="empty"><InboxIcon size={36}/><h3>{t('Nothing assigned to {who} right now.',{who:who?.name||t('you')})}</h3>
   <p>{t('Work lands here when a manager assigns you a building ticket on')} <a href="/building">{t("Building")}</a>, {t('or an operator clicks')} <b>{t("Offer to eligible responder")}</b> {t('on a 911 card in')} <a href="/ops">{t("911 operations")}</a>. {t('Life-threatening (P0) cards go to the supervisor, not here. DIZA also phones you about each assignment.')}</p></div>}
 </section>;
}
