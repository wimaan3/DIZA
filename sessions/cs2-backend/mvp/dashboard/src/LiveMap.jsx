import React,{useEffect,useRef} from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import{MapPin}from'lucide-react';

const COLOR={P0:'#c4412b',P1:'#d0832c',P2:'#a8a33a',P3:'#8a958a'};
const PLACE={shelter_site:'Shelter site',library_cooling_charging:'Cooling / charging',food:'Food',hospital_er:'Emergency room',health_center:'Health center',animal_shelter:'Animal shelter',public_safety:'Public safety',recovery_center:'Recovery center',relief_org:'Relief org'};
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

// Live map of reports (pins by severity, P0 pulsing), incident rings for linked reports, and verified places.
export default function LiveMap({reports,places,selected,onSelect}){
 const el=useRef(null),map=useRef(null),layers=useRef(null),seen=useRef(new Set());
 useEffect(()=>{
  const m=L.map(el.current,{scrollWheelZoom:false}).setView([34.1,-118.2],11);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',className:'osm-tiles'}).addTo(m);
  map.current=m;layers.current={places:L.layerGroup().addTo(m),rings:L.layerGroup().addTo(m),pins:L.layerGroup().addTo(m)};
  return()=>m.remove();
 },[]);
 useEffect(()=>{
  const g=layers.current.places;g.clearLayers();
  places.forEach(p=>L.marker([p.lat,p.lon],{icon:L.divIcon({className:'place-pin',iconSize:[10,10]}),keyboard:false})
   .bindTooltip(`<b>${esc(p.name)}</b><br>${esc(PLACE[p.type]||p.type)}${p.address?' · '+esc(p.address):''}`).addTo(g));
 },[places.length]);
 const located=reports.filter(r=>r.lat!=null);
 // The dashboard polls every 1.5 s; only redraw pins when something on the map actually changed.
 const sig=located.map(r=>r.id+r.severity+r.lat+r.lon+r.cluster_id).join('|')+'#'+selected;
 useEffect(()=>{
  const{pins,rings}=layers.current;pins.clearLayers();rings.clearLayers();
  const groups={};located.forEach(r=>(groups[r.cluster_id]??=[]).push(r));
  Object.values(groups).filter(g=>g.length>1).forEach(g=>{
   const lat=g.reduce((a,r)=>a+r.lat,0)/g.length,lon=g.reduce((a,r)=>a+r.lon,0)/g.length,worst=g.map(r=>r.severity).sort()[0];
   L.circle([lat,lon],{radius:150+120*g.length,color:COLOR[worst],weight:1.5,fillOpacity:.08}).bindTooltip(`${g.length} linked reports`).addTo(rings);
  });
  located.forEach(r=>{
   const isNew=!seen.current.has(r.id);seen.current.add(r.id);
   L.marker([r.lat,r.lon],{icon:L.divIcon({className:`report-pin ${r.severity}${r.id===selected?' chosen':''}${isNew?' fresh':''}`,iconSize:[16,16]}),zIndexOffset:r.severity==='P0'?1000:0})
    .bindTooltip(`<b>${esc(r.severity)} · ${esc(r.category.replaceAll('_',' '))}</b><br>${esc(r.location)}<br>${esc(r.summary).slice(0,120)}`)
    .on('click',()=>onSelect(r.id)).addTo(pins);
  });
 },[sig]);
 // Follow the action: frame all pins whenever a new located report arrives.
 const count=located.length;
 useEffect(()=>{if(count)map.current.fitBounds(L.latLngBounds(located.map(r=>[r.lat,r.lon])).pad(.4),{maxZoom:15})},[count]);
 const pending=reports.length-count;
 return <section className="panel mapcard"><div className="panel-title"><h2>Live map <span>{count}</span></h2><div className="legend">{['P0','P1','P2','P3'].map(s=><span key={s}><i style={{background:COLOR[s]}}/>{s}</span>)}<span><i className="sq"/>Verified place</span></div></div>
  <div className="map" ref={el}/>{pending>0&&<p className="map-note"><MapPin size={12}/>{pending} report{pending!==1?'s':''} without a map position yet (location still being placed, or not given)</p>}</section>;
}
