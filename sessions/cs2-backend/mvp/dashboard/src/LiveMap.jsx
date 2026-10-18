import React,{useEffect,useRef,useState} from 'react';
import {Map as GLMap,Marker,Popup,NavigationControl,ScaleControl,LngLatBounds,setWorkerUrl} from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import 'maplibre-gl/dist/maplibre-gl.css';
import {MapPin,PenLine,WifiOff,X,Check,Building2,Focus} from 'lucide-react';
import {t,language} from './i18n.js';
import {PRESETS,FACILITIES,CITY_STYLE,configureBuildings,position} from './city-map-data.js';
import outlines from './offline-la.json';
import './ops-map-3d.css';
setWorkerUrl(workerUrl);
export const COLOR={P0:'#7d1d10',P1:'#c0442a',P2:'#e8956b',P3:'#b9c0b6'};
const PLACE={shelter_site:'Shelter site',library_cooling_charging:'Cooling / charging',food:'Food',hospital_er:'Emergency room',health_center:'Health center',animal_shelter:'Animal shelter',public_safety:'Public safety',recovery_center:'Recovery center',relief_org:'Relief org'};
export const ZONE={evacuation_order:{label:'Evacuation order',color:'#7d1d10'},evacuation_warning:{label:'Evacuation warning',color:'#c0442a'},hazard:{label:'Hazard area',color:'#8a5a00'},staging:{label:'Staging / safe area',color:'#22553e'},note:{label:'Operator note',color:'#4a6fa5'}};
const fc=features=>({type:'FeatureCollection',features});
const offlineStyle={version:8,sources:{outlines:{type:'geojson',data:outlines,attribution:'US Census TIGERweb · LA outline only'}},layers:[{id:'background',type:'background',paint:{'background-color':'#e9eee8'}},{id:'outlines',type:'line',source:'outlines',paint:{'line-color':'#9aab9d','line-width':1.4}}]};
const duration=()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches?0:700;
function polygon(points,properties={}) {
 if(!Array.isArray(points)||points.length<3)return null;
 const ring=points.map(p=>Array.isArray(p)&&p.length===2?position({lat:p[0],lon:p[1]}):null);
 if(ring.some(p=>!p)||new Set(ring.map(p=>p.join(','))).size<3)return null;
 if(ring[0].join(',')!==ring.at(-1).join(','))ring.push([...ring[0]]);
 return {type:'Feature',geometry:{type:'Polygon',coordinates:[ring]},properties};
}
function linkedRings(reports) {
 const groups=new Map();
 reports.filter(r=>r.cluster_id&&position(r)).forEach(r=>groups.set(r.cluster_id,[...(groups.get(r.cluster_id)||[]),r]));
 return fc([...groups.values()].filter(g=>g.length>1).map(g=>{
  const lat=g.reduce((a,r)=>a+Number(r.lat),0)/g.length,lon=g.reduce((a,r)=>a+Number(r.lon),0)/g.length;
  const radius=150+120*g.length,points=Array.from({length:48},(_,i)=>{
   const angle=i/48*Math.PI*2;
   return [lat+Math.sin(angle)*radius/111320,lon+Math.cos(angle)*radius/(111320*Math.max(.01,Math.cos(lat*Math.PI/180)))];
  });
  return polygon(points,{color:COLOR[g.map(r=>r.effective).sort()[0]]||COLOR.P3,count:g.length});
 }).filter(Boolean));
}
function popupNode(title,body,source) {
 const node=document.createElement('div'),strong=document.createElement('strong'),text=document.createElement('p');
 strong.textContent=title;text.textContent=body;node.append(strong,text);
 if(source){const a=document.createElement('a');a.href=source;a.target='_blank';a.rel='noreferrer';a.textContent=t('Facility website');node.append(a);}
 return node;
}
function initialView(center) {
 const p=position({lat:center?.[0],lon:center?.[1]})||PRESETS[0].center;
 return Math.abs(p[0]+118.2)<.5&&Math.abs(p[1]-34.1)<.4?PRESETS[0]:{center:p,zoom:13,bearing:0};
}

// Replacement for the original Live map: same props and mutation callbacks, same operational data.
export default function LiveMap({reports=[],places=[],zones=[],selected,onSelect,onPlace,onZone,onDeleteZone,tall,center=[34.1,-118.2]}) {
 const el=useRef(null),map=useRef(null),latest=useRef({}),markers=useRef(new Map()),placeMarkers=useRef([]),placePopups=useRef([]),lastView=useRef(null);
 const [ready,setReady]=useState(0),[offline,setOffline]=useState(false),[threeD,setThreeD]=useState(true),[care,setCare]=useState(true);
 const [draw,setDraw]=useState(null),[zoneForm,setZoneForm]=useState(false),[saving,setSaving]=useState(false),[mapError,setMapError]=useState(''),[failed,setFailed]=useState(false);
 const chosen=reports.find(r=>r.id===selected),located=reports.filter(position),pending=reports.filter(r=>!position(r));
 latest.current={reports,places,zones,selected,onSelect,onPlace,onZone,onDeleteZone,draw,threeD,offline,care,chosen};
 function go(view){map.current?.easeTo({...view,zoom:offline?Math.min(view.zoom,11.5):view.zoom,pitch:!offline&&threeD?57:0,duration:duration()});}
 function allReports(){if(!located.length||!map.current)return;const b=new LngLatBounds();located.forEach(r=>b.extend(position(r)));map.current.fitBounds(b,{padding:60,maxZoom:offline?11.5:16,pitch:!offline&&threeD?45:0,duration:duration()});}
 useEffect(()=>{
  let m,resize,timer;
  setFailed(false);setMapError('');setReady(0);
  const view=lastView.current||initialView(center);
  try {
   m=new GLMap({container:el.current,style:offline?offlineStyle:CITY_STYLE,center:view.center,zoom:offline?Math.min(view.zoom,11.5):view.zoom,bearing:view.bearing||0,pitch:offline?0:latest.current.threeD?57:0,maxPitch:70,canvasContextAttributes:{antialias:true}});
   map.current=m;m.scrollZoom.disable();m.doubleClickZoom.disable();
   m.addControl(new NavigationControl({visualizePitch:true}),'top-right');m.addControl(new ScaleControl(),'bottom-left');
   m.getCanvas().setAttribute('aria-label',t('Live map'));
   timer=setTimeout(()=>setMapError(t('Map loading slowly. Try Offline map.')),20000);
   m.on('load',()=>{
    clearTimeout(timer);configureBuildings(m,latest.current.threeD);
    for(const name of ['zones','rings','draft'])m.addSource(name,{type:'geojson',data:fc([])});
    for(const name of ['zones','rings']){
     m.addLayer({id:name+'-fill',type:'fill',source:name,paint:{'fill-color':['get','color'],'fill-opacity':.1}});
     m.addLayer({id:name+'-line',type:'line',source:name,paint:{'line-color':['get','color'],'line-width':name==='zones'?2:1.5}});
    }
    m.addLayer({id:'draft-line',type:'line',source:'draft',paint:{'line-color':'#22553e','line-width':2,'line-dasharray':[3,2]}});
    m.on('click','zones-fill',e=>{
     const s=latest.current;if(s.draw||s.chosen&&!position(s.chosen))return;
     const f=e.features?.[0];if(f)new Popup().setLngLat(e.lngLat).setDOMContent(popupNode(f.properties.name,t((ZONE[f.properties.kind]||ZONE.note).label))).addTo(m);
    });
    setMapError('');setReady(n=>n+1);
   });
   m.on('click',e=>{
    const s=latest.current;
    if(s.draw){setDraw(d=>d?[...d,[e.lngLat.lat,e.lngLat.lng]]:d);return;}
    if(s.chosen&&!position(s.chosen))s.onPlace?.(s.chosen.id,e.lngLat.lat,e.lngLat.lng);
   });
   m.on('error',()=>setMapError(t('Map data unavailable. Try Offline map.')));
   m.on('webglcontextlost',()=>{setFailed(true);setMapError(t('3D graphics unavailable. Event cards remain available below.'));});
   resize=new ResizeObserver(()=>m.resize());resize.observe(el.current);
  }catch{setFailed(true);setMapError(t('3D graphics unavailable. Event cards remain available below.'));}
  return ()=>{
   clearTimeout(timer);resize?.disconnect();
   if(m)lastView.current={center:m.getCenter().toArray(),zoom:m.getZoom(),bearing:m.getBearing()};
   markers.current.forEach(x=>x.marker.remove());markers.current.clear();placeMarkers.current.forEach(x=>x.remove());placeMarkers.current=[];placePopups.current.forEach(x=>x.remove());placePopups.current=[];
   m?.remove();map.current=null;
  };
 },[offline]);
 useEffect(()=>{
  const m=map.current;if(!ready||!m)return;
  const ids=new Set(located.map(r=>r.id));
  markers.current.forEach((value,id)=>{if(!ids.has(id)){value.marker.remove();markers.current.delete(id);}});
  for(const r of located){
   let item=markers.current.get(r.id);
   if(!item){
    const button=document.createElement('button');button.type='button';button.className='ops3d-marker';button.dataset.reportId=r.id;
    const dot=document.createElement('span');button.append(dot);
    const marker=new Marker({element:button,draggable:!!onPlace}).setLngLat(position(r)).addTo(m);
    item={marker,button,dot,dragging:false};markers.current.set(r.id,item);
    button.addEventListener('click',e=>{
     e.stopPropagation();const s=latest.current;
     if(s.draw){const p=marker.getLngLat();setDraw(d=>d?[...d,[p.lat,p.lng]]:d);return;}
     s.onSelect(r.id);
    });
    marker.on('dragstart',()=>{item.dragging=true;});
    marker.on('dragend',async()=>{
     item.dragging=false;const p=marker.getLngLat(),previous=position(latest.current.reports.find(x=>x.id===r.id));
     try{if(await latest.current.onPlace?.(r.id,p.lat,p.lng)===false&&previous)marker.setLngLat(previous);}
     catch{if(previous)marker.setLngLat(previous);}
    });
   }
   if(!item.dragging)item.marker.setLngLat(position(r));
   item.marker.setDraggable(!!onPlace&&!draw);
   item.dot.className=`report-pin ${r.effective||'P3'}${r.id===selected?' chosen':''}${r.gps_accuracy!=null?' gps':''}${r.flags?.length&&!r.reviewed_at?' flagged':''}`;
   item.button.setAttribute('aria-label',`${r.effective||''} · ${r.location||''}`);
   item.button.title=`${r.effective||''} · ${(r.category||'').replaceAll('_',' ')}\n${r.location||''}\n${r.summary||''}${r.gps_accuracy!=null?'\n'+t('GPS from caller ±{m} m',{m:Math.round(r.gps_accuracy)}):''}${r.flags?.length?'\n'+r.flags[0].message:''}`;
   item.button.style.zIndex=r.id===selected?'20':r.effective==='P0'?'10':'1';
  }
  m.getSource('rings').setData(linkedRings(located));
 },[reports,selected,draw,ready,language()]);
 const placeSignature=JSON.stringify(places);
 useEffect(()=>{
  const m=map.current;if(!ready||!m)return;
  placeMarkers.current.forEach(x=>x.remove());placeMarkers.current=[];placePopups.current.forEach(x=>x.remove());placePopups.current=[];
  for(const p of [...places,...(care?FACILITIES:[])].filter(position)){
   const button=document.createElement('button');button.type='button';button.className='ops3d-place'+(p.kind==='facility'?' care':'');button.setAttribute('aria-label',p.name);button.title=p.name;
   const pop=new Popup({offset:10}).setDOMContent(popupNode(p.fullName||p.name,`${PLACE[p.type]||p.type||''}${p.address?' · '+p.address:''}${p.kind==='facility'?'\n'+t('Approximate address position. Verify facility availability.'):''}`,p.kind==='facility'?p.source:null));
   const marker=new Marker({element:button}).setLngLat(position(p)).addTo(m);
   button.addEventListener('click',e=>{e.stopPropagation();if(latest.current.draw){setDraw(d=>d?[...d,[p.lat,p.lon]]:d);return;}pop.setLngLat(position(p)).addTo(m);});
   placeMarkers.current.push(marker);placePopups.current.push(pop);
  }
 },[placeSignature,care,ready,language()]);
 useEffect(()=>{
  const m=map.current;if(!ready||!m)return;
  m.getSource('zones').setData(fc(zones.map(z=>polygon(z.points,{name:z.name,kind:z.kind,color:(ZONE[z.kind]||ZONE.note).color})).filter(Boolean)));
  const coords=(draw||[]).map(p=>[p[1],p[0]]);if(coords.length>2)coords.push(coords[0]);
  m.getSource('draft').setData(fc(coords.length>1?[{type:'Feature',geometry:{type:'LineString',coordinates:coords},properties:{}}]:[]));
  m.getCanvas().style.cursor=draw||chosen&&!position(chosen)?'crosshair':'';
 },[zones,draw,selected,reports,ready]);
 useEffect(()=>{
  const m=map.current;if(!m)return;
  if(m.getLayer('building-3d'))m.setLayoutProperty('building-3d','visibility',threeD?'visible':'none');
  m.easeTo({pitch:threeD&&!offline?57:0,duration:duration()});
 },[threeD,offline,ready]);
 useEffect(()=>{const p=position(chosen);if(p)go({center:p,zoom:16.1,bearing:map.current?.getBearing()||0});},[selected]);
 async function saveZone(e){
  e.preventDefault();if(saving||!polygon(draw))return;
  const f=new FormData(e.currentTarget);setSaving(true);
  try{if(await onZone({name:f.get('name'),kind:f.get('kind'),points:draw})){setDraw(null);setZoneForm(false);}}finally{setSaving(false);}
 }
 return <section className={'panel mapcard ops-map-3d'+(tall?' tall':'')}>
  <div className="panel-title"><h2>{t('Live map')} <span>{located.length}</span></h2><div className="map-tools">
   <button className={'small'+(threeD&&!offline?' on':'')} aria-pressed={threeD&&!offline} disabled={offline||failed} onClick={()=>setThreeD(true)}><Building2 size={14}/>3D</button><button className={'small'+(!threeD||offline?' on':'')} aria-pressed={!threeD||offline} onClick={()=>setThreeD(false)}>2D</button>
   <button className="small" disabled={!located.length||failed} onClick={allReports}><Focus size={14}/>{t('All reports')}</button>
   {onZone&&(draw?<><span className="hint">{draw.length<3?t('Click the map to add corners ({n}/3+)',{n:draw.length}):t('{n} corners',{n:draw.length})}</span><button className="small primary" disabled={!polygon(draw)||saving} onClick={()=>setZoneForm(true)}><Check size={14}/>{t('Finish')}</button><button className="small" disabled={saving} onClick={()=>{setDraw(null);setZoneForm(false)}}><X size={14}/>{t('Cancel')}</button></>:<button className="small" disabled={failed} onClick={()=>setDraw([])}><PenLine size={14}/>{t('Draw zone')}</button>)}
   <button className={'small'+(offline?' on':'')} aria-pressed={offline} onClick={()=>setOffline(!offline)}><WifiOff size={14}/>{offline?t('Offline map on'):t('Offline map')}</button>
  </div></div>
  <div className="legend">{Object.keys(COLOR).map(s=><span key={s}><i style={{background:COLOR[s]}}/>{s}</span>)}<span><i className="sq"/>{t('Verified place')}</span>{zones.length>0&&<span><i className="zone"/>{t('Zone ({n})',{n:zones.length})}</span>}<label><input type="checkbox" checked={care} onChange={e=>setCare(e.target.checked)}/>{t('Care locations')}</label>{offline&&<span className="offline-note">{t('Offline outline map · US Census TIGER data')}</span>}</div>
  <div className="ops3d-regions"><span>{t('Jump to')}</span>{PRESETS.map(p=><button type="button" className="small" key={p.id} disabled={failed} onClick={()=>go(p)}>{p.name}</button>)}<button className="small" disabled={failed} onClick={()=>go(initialView(center))}>{t('Deployment area')}</button></div>
  {zoneForm&&<form className="zone-form" onSubmit={saveZone}><input name="name" required placeholder={t('Zone name, e.g. Evacuation warning north of the river')} autoFocus/><select name="kind" defaultValue="evacuation_warning">{Object.entries(ZONE).map(([k,v])=><option key={k} value={k}>{t(v.label)}</option>)}</select><button className="small primary" type="submit" disabled={saving}>{t('Save zone')}</button></form>}
  {chosen&&!position(chosen)&&!draw&&<p className="map-place">{t('Click the map to place this report:')} <b>{chosen.location}</b></p>}
  {mapError&&<p className="map-note" role="status">{mapError}</p>}
  <div className={'map'+(chosen&&!position(chosen)||draw?' placing':'')} ref={el}/>
  <p className="map-note">{t('3D buildings appear when zoomed in. Heights may be estimated.')}</p>
  {pending.length>0&&<div className="unlocated"><b><MapPin size={13}/>{t('{n} without a map position',{n:pending.length})}</b>{pending.slice(0,8).map(r=><button key={r.id} className={'small'+(r.id===selected?' on':'')} onClick={()=>onSelect(r.id)}><span className={'severity '+r.effective}>{r.effective}</span>{r.location?.startsWith('(')?t('Location not given yet'):r.location} · {t('place on map')}</button>)}</div>}
  {zones.length>0&&onDeleteZone&&<div className="zone-list">{zones.map(z=><span key={z.id}><i style={{borderColor:(ZONE[z.kind]||ZONE.note).color}}/>{z.name}<button className="text-button" aria-label={`Remove zone ${z.name}`} onClick={()=>confirm(t('Remove zone “{n}”?',{n:z.name}))&&onDeleteZone(z.id)}><X size={12}/></button></span>)}</div>}
 </section>;
}
