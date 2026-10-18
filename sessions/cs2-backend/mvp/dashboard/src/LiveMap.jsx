import React,{useEffect,useRef,useState} from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import{MapPin,PenLine,WifiOff,X,Check}from'lucide-react';

// Severity is ordinal, so one hue light→dark (checked for colour-blind separation); the P0–P3 text always sits beside it.
export const COLOR={P0:'#7d1d10',P1:'#c0442a',P2:'#e8956b',P3:'#b9c0b6'};
const PLACE={shelter_site:'Shelter site',library_cooling_charging:'Cooling / charging',food:'Food',hospital_er:'Emergency room',health_center:'Health center',animal_shelter:'Animal shelter',public_safety:'Public safety',recovery_center:'Recovery center',relief_org:'Relief org'};
export const ZONE={evacuation_order:{label:'Evacuation order',color:'#7d1d10',dash:''},evacuation_warning:{label:'Evacuation warning',color:'#c0442a',dash:'6 4'},hazard:{label:'Hazard area',color:'#8a5a00',dash:'2 4'},staging:{label:'Staging / safe area',color:'#22553e',dash:''},note:{label:'Operator note',color:'#4a6fa5',dash:'4 4'}};
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

// Live map: pins by severity (P0 pulsing), rings for linked reports, verified places, operator-drawn zones.
// Click to place an unlocated report, drag any pin to correct it. If map tiles fail, a bundled LA outline map takes over.
export default function LiveMap({reports,places,zones=[],selected,onSelect,onPlace,onZone,onDeleteZone,tall}){
 const el=useRef(null),map=useRef(null),layers=useRef(null),seen=useRef(new Set()),placing=useRef(null),drawRef=useRef(null);
 const[draw,setDraw]=useState(null),[offline,setOffline]=useState(false),[zoneForm,setZoneForm]=useState(null);
 const chosen=reports.find(r=>r.id===selected);
 placing.current=chosen&&chosen.lat==null?chosen.id:null;
 drawRef.current=draw;
 useEffect(()=>{
  const m=L.map(el.current,{scrollWheelZoom:false,doubleClickZoom:false}).setView([34.1,-118.2],11);
  let failed=0;
  const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',className:'osm-tiles'})
   .on('tileerror',()=>{if(++failed===4)setOffline(true)}).on('tileload',()=>{failed=0}).addTo(m);
  m.on('click',e=>{const d=drawRef.current;if(d){setDraw([...d,[e.latlng.lat,e.latlng.lng]]);return}if(placing.current)onPlace(placing.current,e.latlng.lat,e.latlng.lng)});
  map.current=m;layers.current={tiles,base:L.layerGroup().addTo(m),zones:L.layerGroup().addTo(m),draft:L.layerGroup().addTo(m),places:L.layerGroup().addTo(m),rings:L.layerGroup().addTo(m),pins:L.layerGroup().addTo(m)};
  return()=>m.remove();
 },[]);
 // Offline fallback: freeways and city outlines from the US Census (bundled, loaded only when needed).
 useEffect(()=>{
  const{base,tiles}=layers.current;base.clearLayers();
  if(!offline){tiles.setOpacity(1);return}
  tiles.setOpacity(0);
  import('./offline-la.json').then(({default:geo})=>{
   L.geoJSON(geo,{interactive:true,style:f=>f.properties.k==='road'?{color:'#9a8f7c',weight:2,opacity:.9}:{color:'#7f948a',weight:1,fillColor:'#e9efe6',fillOpacity:.5},
    onEachFeature:(f,l)=>f.properties.n&&l.bindTooltip(esc(f.properties.n),{sticky:true})}).addTo(base);
  });
 },[offline]);
 useEffect(()=>{
  const g=layers.current.places;g.clearLayers();
  places.forEach(p=>L.marker([p.lat,p.lon],{icon:L.divIcon({className:'place-pin',iconSize:[10,10]}),keyboard:false})
   .bindTooltip(`<b>${esc(p.name)}</b><br>${esc(PLACE[p.type]||p.type)}${p.address?' · '+esc(p.address):''}`).addTo(g));
 },[places.length]);
 const zsig=zones.map(z=>z.id).join('|');
 useEffect(()=>{
  const g=layers.current.zones;g.clearLayers();
  zones.forEach(z=>{const k=ZONE[z.kind]||ZONE.note;
   L.polygon(z.points,{color:k.color,weight:2,dashArray:k.dash,fillOpacity:.07,interactive:true}).bindTooltip(`<b>${esc(z.name)}</b><br>${k.label}`,{sticky:true}).addTo(g)});
 },[zsig]);
 useEffect(()=>{
  const g=layers.current.draft;g.clearLayers();
  if(draw?.length){L.polyline(draw.length>2?[...draw,draw[0]]:draw,{color:'#22553e',weight:2,dashArray:'4 4'}).addTo(g);draw.forEach(p=>L.circleMarker(p,{radius:4,color:'#22553e',fillOpacity:1}).addTo(g))}
 },[draw]);
 const located=reports.filter(r=>r.lat!=null);
 // The dashboard polls every 1.5 s; only redraw pins when something on the map actually changed.
 const sig=located.map(r=>r.id+r.effective+r.lat+r.lon+r.cluster_id+r.gps_accuracy+(r.flags?.length||0)).join('|')+'#'+selected;
 useEffect(()=>{
  const{pins,rings}=layers.current;pins.clearLayers();rings.clearLayers();
  const groups={};located.forEach(r=>(groups[r.cluster_id]??=[]).push(r));
  Object.values(groups).filter(g=>g.length>1).forEach(g=>{
   const lat=g.reduce((a,r)=>a+r.lat,0)/g.length,lon=g.reduce((a,r)=>a+r.lon,0)/g.length,worst=g.map(r=>r.effective).sort()[0];
   L.circle([lat,lon],{radius:150+120*g.length,color:COLOR[worst],weight:1.5,fillOpacity:.08}).bindTooltip(`${g.length} linked reports`).addTo(rings);
  });
  located.forEach(r=>{
   const isNew=!seen.current.has(r.id);seen.current.add(r.id);
   L.marker([r.lat,r.lon],{draggable:true,autoPan:true,icon:L.divIcon({className:`report-pin ${r.effective}${r.gps_accuracy!=null?' gps':''}${r.id===selected?' chosen':''}${isNew?' fresh':''}${r.flags?.length&&!r.reviewed_at?' flagged':''}`,iconSize:[16,16]}),zIndexOffset:r.effective==='P0'?1000:0})
    .bindTooltip(`<b>${esc(r.effective)} · ${esc(r.category.replaceAll('_',' '))}</b><br>${esc(r.location)}${r.gps_accuracy!=null?`<br>GPS from caller ±${Math.round(r.gps_accuracy)} m`:''}${r.flags?.length?`<br><b>${esc(r.flags[0].message)}</b>`:''}<br>${esc(r.summary).slice(0,120)}`)
    .on('click',()=>onSelect(r.id)).on('dragend',e=>{const p=e.target.getLatLng();onPlace(r.id,p.lat,p.lng)}).addTo(pins);
  });
 },[sig]);
 // Follow the action: frame all pins whenever a new located report arrives.
 const count=located.length;
 useEffect(()=>{if(count)map.current.fitBounds(L.latLngBounds(located.map(r=>[r.lat,r.lon])).pad(.4),{maxZoom:15})},[count]);
 useEffect(()=>{setTimeout(()=>map.current?.invalidateSize(),50)},[tall]);
 const pending=reports.filter(r=>r.lat==null);
 async function saveZone(e){e.preventDefault();const f=new FormData(e.currentTarget);if(await onZone({name:f.get('name'),kind:f.get('kind'),points:draw})){setDraw(null);setZoneForm(null)}}
 return <section className={'panel mapcard'+(tall?' tall':'')}><div className="panel-title"><h2>Live map <span>{count}</span></h2>
  <div className="map-tools">{onZone&&(draw?<><span className="hint">{draw.length<3?`Click the map to add corners (${draw.length}/3+)`:`${draw.length} corners`}</span><button className="small primary" disabled={draw.length<3} onClick={()=>setZoneForm(true)}><Check size={14}/>Finish</button><button className="small" onClick={()=>{setDraw(null);setZoneForm(null)}}><X size={14}/>Cancel</button></>
   :<button className="small" onClick={()=>setDraw([])} title="Draw a zone on the map"><PenLine size={14}/>Draw zone</button>)}
   <button className={'small'+(offline?' on':'')} aria-pressed={offline} onClick={()=>setOffline(!offline)} title="Use the bundled outline map (works without map tiles)"><WifiOff size={14}/>{offline?'Offline map on':'Offline map'}</button></div></div>
  <div className="legend">{['P0','P1','P2','P3'].map(s=><span key={s}><i style={{background:COLOR[s]}}/>{s}</span>)}<span><i className="sq"/>Verified place</span>{zones.length>0&&<span><i className="zone"/>Zone ({zones.length})</span>}{offline&&<span className="offline-note">Offline outline map · US Census TIGER data</span>}</div>
  {zoneForm&&<form className="zone-form" onSubmit={saveZone}><input name="name" required placeholder="Zone name, e.g. Evacuation warning north of Altadena Dr" autoFocus/><select name="kind" defaultValue="evacuation_warning">{Object.entries(ZONE).map(([k,v])=><option key={k} value={k}>{v.label}</option>)}</select><button className="small primary" type="submit">Save zone</button></form>}
  {chosen&&chosen.lat==null&&!draw&&<p className="map-place">Click the map to place this report: <b>{chosen.location}</b></p>}
  <div className={'map'+((chosen&&chosen.lat==null)||draw?' placing':'')} ref={el}/>
  {pending.length>0&&<div className="unlocated"><b><MapPin size={13}/>{pending.length} without a map position</b>{pending.slice(0,8).map(r=><button key={r.id} className={'small'+(r.id===selected?' on':'')} onClick={()=>onSelect(r.id)}><span className={'severity '+r.effective}>{r.effective}</span>{r.location.startsWith('(')?'Location not given yet':r.location} · place on map</button>)}</div>}
  {zones.length>0&&onDeleteZone&&<div className="zone-list">{zones.map(z=><span key={z.id}><i style={{borderColor:(ZONE[z.kind]||ZONE.note).color}}/>{z.name}<button className="text-button" aria-label={`Remove zone ${z.name}`} onClick={()=>confirm(`Remove zone "${z.name}"?`)&&onDeleteZone(z.id)}><X size={12}/></button></span>)}</div>}
 </section>;
}
