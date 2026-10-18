import React,{useEffect,useState} from 'react';
import{AlertTriangle,Clock,ShieldCheck,ArrowUp,ArrowDown,Pin}from'lucide-react';

// 911 mode queue: urgent (P0/P1) above non-urgent (P2/P3). GET /api/ops (backend/app/ops.py) ranks the cards
// (P0 pinned, then score, then longest wait) and gives the reasons behind each priority. Rules only raise priority;
// lowering takes a person and a written reason, and is logged.
const SEV=['P0','P1','P2','P3'];
const SEV_TEXT={P0:'Life-threatening',P1:'Urgent',P2:'Needs review',P3:'Information'};
const wait=s=>{s=Math.max(0,Math.floor(s));return s>=3600?`${Math.floor(s/3600)}h ${Math.floor(s%3600/60)}m`:`${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`};
function useTick(){const[,set]=useState(0);useEffect(()=>{const id=setInterval(()=>set(x=>x+1),1000);return()=>clearInterval(id)},[]);return Date.now()/1000}
// Poll the ranked queue next to /api/state and attach each card's priority to its report.
export function useOps(headers,on){
 const[ops,setOps]=useState(null);
 useEffect(()=>{if(!on)return;let live=true;const get=()=>fetch('/api/ops',{headers}).then(r=>r.ok?r.json():null).then(d=>{if(live&&d)setOps(d)}).catch(()=>{});
  get();const id=setInterval(get,1500);return()=>{live=false;clearInterval(id)}},[on,headers.Authorization]);
 return ops}
export function withOps(reports,ops){
 if(!ops)return reports;const at={};ops.incidents.forEach((i,n)=>{at[i.id]=[n,i]});
 const pr=i=>({severity:i.effective,score:i.score,urgent:['P0','P1'].includes(i.effective),pinned:i.effective==='P0',target_s:i.target_s,reviewed:!!i.reviewed_at,handled:i.handled,
  reasons:[...(i.effective!==i.severity?[`raised ${i.severity}→${i.effective} by second reader`]:[]),...i.flags.map(f=>f.message),...i.score_reasons.filter(([l])=>!l.endsWith(' base')).map(([l,p])=>`${l} +${p}`)]});
 return reports.map(r=>at[r.id]?{...r,priority:pr(at[r.id][1])}:r).sort((a,b)=>(at[a.id]?.[0]??1e9)-(at[b.id]?.[0]??1e9))}
const typing=e=>e.target.closest('input,textarea,select')||e.ctrlKey||e.metaKey||e.altKey;

export function QueueSections({rows,requests,selected,onSelect,labels}){
 const now=useTick();
 const urgent=rows.filter(r=>r.priority?.urgent),rest=rows.filter(r=>!r.priority?.urgent);
 useEffect(()=>{const key=e=>{if(typing(e)||!['j','k'].includes(e.key))return;const i=rows.findIndex(r=>r.id===selected);const n=rows[e.key==='j'?i+1:Math.max(0,i-1)];if(n){e.preventDefault();onSelect(n.id)}};
  addEventListener('keydown',key);return()=>removeEventListener('keydown',key)});
 const card=r=>{const p=r.priority||{severity:r.severity,reasons:[]},q=requests.find(q=>q.report_id===r.id),age=now-r.created;const late=!p.reviewed&&!p.handled&&age>p.target_s;
  return <button key={r.id} className={'report opsq sev-'+p.severity+(selected===r.id?' selected':'')} onClick={()=>onSelect(r.id)} aria-current={selected===r.id}>
   <div className="report-top"><span className={'severity '+p.severity}>{p.pinned&&<Pin size={10}/>}{p.severity} · {SEV_TEXT[p.severity]}</span><span className="category">{r.category.replaceAll('_',' ')}</span><span className={'age'+(late?' late':'')}><Clock size={11}/>{wait(age)}{late&&<b> past {wait(p.target_s)}</b>}{p.reviewed&&' · reviewed'}</span></div>
   <strong>{r.location}</strong><p>{r.summary}</p>
   <div className="reasons" aria-label="Priority reasons">{p.reasons?.map((x,i)=><span key={i} className={x.startsWith('raised')||x.startsWith('Possible')?'rule':''}>{x}</span>)}<span className="score">score {p.score}</span></div>
   <div className="report-bottom"><span className={q&&!['accepted','done'].includes(q.status)?'attention':''}>{q?labels[q.status]:'No follow-up task'}</span><span>{r.language.toUpperCase()} · {r.source}</span></div>
  </button>};
 return <>{urgent.length>0||rest.length===0?<h3 className="qgroup urgent"><AlertTriangle size={14}/>Urgent · P0/P1 <span>{urgent.length}</span><small>P0 pinned at the top</small></h3>:null}{urgent.map(card)}
  <h3 className="qgroup"><Clock size={14}/>Non-urgent · P2/P3 <span>{rest.length}</span><small>by priority, then wait</small></h3>{rest.length?rest.map(card):<p className="none">None.</p>}</>}

export function PriorityPanel({report,act}){
 const p=report.priority||{severity:report.severity,reasons:[]};const[lower,setLower]=useState(null),[reason,setReason]=useState(''),[review,setReview]=useState(false);
 useEffect(()=>{setLower(null);setReason('');setReview(false)},[report.id]);
 function choose(sev){if(SEV.indexOf(sev)<SEV.indexOf(p.severity)){act(`/api/reports/${report.id}/priority`,{severity:sev,by:'operator'})}else if(sev!==p.severity){setLower(sev);setReview(false)}}
 useEffect(()=>{const key=e=>{if(typing(e))return;const n='1234'.indexOf(e.key);if(n>=0){e.preventDefault();choose(SEV[n])}if(e.key==='r'){e.preventDefault();setReview(true);setLower(null)}};
  addEventListener('keydown',key);return()=>removeEventListener('keydown',key)});
 const submit=e=>{e.preventDefault();if(reason.trim().length<3)return;(lower?act(`/api/reports/${report.id}/priority`,{severity:lower,reason:reason.trim(),by:'operator'}):act(`/api/reports/${report.id}/reviewed`,{reason:reason.trim(),by:'operator'})).then(ok=>{if(ok){setLower(null);setReview(false);setReason('')}})};
 return <div className="prio"><div className="prio-head"><b>Priority {p.severity} · {SEV_TEXT[p.severity]}</b><span>score {p.score}{p.reviewed?' · reviewed':''}</span></div>
  <div className="reasons">{p.reasons?.map((x,i)=><span key={i} className={x.startsWith('raised')||x.startsWith('Possible')?'rule':''}>{x}</span>)}</div>
  <div className="prio-btns" role="group" aria-label="Set priority">{SEV.map((s,i)=><button key={s} className={s===p.severity?'on':''} aria-pressed={s===p.severity} onClick={()=>choose(s)} title={`Key ${i+1}`}>
   {SEV.indexOf(s)<SEV.indexOf(p.severity)?<ArrowUp size={12}/>:SEV.indexOf(s)>SEV.indexOf(p.severity)?<ArrowDown size={12}/>:null}{s}<kbd>{i+1}</kbd></button>)}
   <button onClick={()=>{setReview(true);setLower(null)}}><ShieldCheck size={13}/>Mark reviewed<kbd>R</kbd></button></div>
  {(lower||review)&&<form className="prio-form" onSubmit={submit}><label>{lower?`Lowering ${p.severity} → ${lower} needs a reason (logged with your name)`:'What did you check? (logged; does not lower priority)'}
   <input autoFocus value={reason} onChange={e=>setReason(e.target.value)} placeholder={lower?'e.g. Called back: everyone is out and safe':'e.g. Location confirmed with caller'}/></label>
   <span className="row2"><button className="primary" type="submit" disabled={reason.trim().length<3}>{lower?`Lower to ${lower}`:'Mark reviewed'}</button><button type="button" onClick={()=>{setLower(null);setReview(false)}}>Cancel</button></span></form>}
  <small className="prio-note">Raising is free. Only a person can lower a priority, with a reason. Keys: <kbd>J</kbd>/<kbd>K</kbd> move, <kbd>1</kbd>–<kbd>4</kbd> set, <kbd>R</kbd> reviewed.</small></div>}
