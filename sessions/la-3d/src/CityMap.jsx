import React,{useEffect,useRef,useState} from 'react';
import {Map,NavigationControl,ScaleControl,setWorkerUrl} from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import 'maplibre-gl/dist/maplibre-gl.css';
import outlines from '../../cs2-backend/mvp/dashboard/src/offline-la.json';
import {FACILITIES,PRESETS,pointFeatures,zoneFeatures,position} from './data.js';
setWorkerUrl(workerUrl);
import {CITY_STYLE as STYLE,configureBuildings} from '../../cs2-backend/mvp/dashboard/src/city-map-data.js';
const offlineStyle = {
  version:8,sources:{outlines:{type:'geojson',data:outlines,attribution:'US Census Bureau TIGERweb · outline only'}},
  layers:[{id:'background',type:'background',paint:{'background-color':'#e9eee8'}},
    {id:'outlines',type:'line',source:'outlines',paint:{'line-color':'#a1b2a5','line-width':1.3}}],
};
function overlays(map,latest) {
  for(const id of ['facilities','incidents','zones']) map.addSource(id,{type:'geojson',data:id==='facilities'?pointFeatures(FACILITIES,'facility'):id==='incidents'?pointFeatures(latest.incidents,'incident'):zoneFeatures(latest.zones)});
  map.addLayer({id:'zones-fill',type:'fill',source:'zones',paint:{'fill-color':['get','color'],'fill-opacity':0.14}});
  map.addLayer({id:'zones-line',type:'line',source:'zones',paint:{'line-color':['get','color'],'line-width':2,'line-dasharray':[3,2]}});
  map.addLayer({id:'facilities',type:'circle',source:'facilities',paint:{'circle-radius':9,'circle-color':'#245a4b','circle-stroke-width':3,'circle-stroke-color':'#fff'}});
  map.addLayer({id:'incidents-halo',type:'circle',source:'incidents',paint:{'circle-radius':19,'circle-color':['get','color'],'circle-opacity':0.16}});
  map.addLayer({id:'incidents',type:'circle',source:'incidents',paint:{'circle-radius':8,'circle-color':['get','color'],'circle-stroke-width':2.5,'circle-stroke-color':'#fff'}});
  map.addSource('selection',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
  map.addLayer({id:'selection',type:'circle',source:'selection',paint:{'circle-radius':16,'circle-color':'transparent','circle-stroke-color':'#173d32','circle-stroke-width':2}});
}
function applyView(map,latest) {
  const building=map.getLayer('building-3d');
  if(building) map.setLayoutProperty('building-3d','visibility',latest.threeD?'visible':'none');
  for(const id of ['facilities','incidents','incidents-halo','zones-fill','zones-line']) if(map.getLayer(id)) map.setLayoutProperty(id,'visibility',latest.layers[id.split('-')[0]]?'visible':'none');
  if(map.getSource('selection')) map.getSource('selection').setData(pointFeatures(latest.selected && position(latest.selected) && latest.layers[latest.selected.kind==='facility'?'facilities':'incidents']?[latest.selected]:[],'selection'));
}
export default function CityMap({incidents,zones,selected,onSelect,view,threeD,layers,offline,onStatus}) {
  const container=useRef(null), mapRef=useRef(null), latest=useRef({});
  const [failed,setFailed]=useState(false);
  latest.current={incidents,zones,selected,onSelect,view,threeD,layers,onStatus};
  useEffect(()=>{
    let map, disposed=false, warningTimer;
    setFailed(false);
    onStatus(offline?'Offline outline':'Loading map…');
    try {
      const p=latest.current.view;
      map=new Map({container:container.current,style:offline?offlineStyle:STYLE,
        center:p.center || PRESETS[0].center,zoom:offline?Math.min(p.zoom || 11.5,11.5):p.zoom || 15.3,bearing:p.bearing || 0,
        pitch:!offline && latest.current.threeD?57:0,canvasContextAttributes:{antialias:true},
        attributionControl:{compact:true},maxPitch:70});
      mapRef.current=map;
      map.addControl(new NavigationControl({visualizePitch:true}),'top-right');
      map.addControl(new ScaleControl({unit:'imperial'}),'bottom-left');
      map.getCanvas().setAttribute('aria-label','Los Angeles city map. Use arrow keys to pan and plus or minus to zoom. Locations are also available in the sidebar.');
      warningTimer=setTimeout(()=>{if(!disposed) latest.current.onStatus('Map is taking longer to load. Offline outline is available.');},20000);
      map.on('load',()=>{
        clearTimeout(warningTimer);
        if(disposed)return;
        configureBuildings(map,latest.current.threeD);
        overlays(map,latest.current);applyView(map,latest.current);
        latest.current.onStatus(offline?'Offline outline · no 3D buildings':'3D map ready');
        for(const id of ['facilities','incidents']) {
          map.on('click',id,e=>{
            const feature=e.features?.[0];if(!feature)return;
            const item=(id==='facilities'?FACILITIES:latest.current.incidents).find(i=>String(i.id)===String(feature.properties.id));
            if(item)latest.current.onSelect({...item,kind:id==='facilities'?'facility':'incident'});
          });
          map.on('mouseenter',id,()=>{map.getCanvas().style.cursor='pointer';});
          map.on('mouseleave',id,()=>{map.getCanvas().style.cursor='';});
        }
        map.on('click','zones-fill',e=>{
          const f=e.features?.[0];
          if(f) latest.current.onStatus(`Operator zone: ${f.properties.name} · ${String(f.properties.kind || 'note').replaceAll('_',' ')}`);
        });
      });
      map.on('error',()=>{if(!disposed)latest.current.onStatus('Some map data could not load. Try the offline outline.');});
      map.on('webglcontextlost',()=>{if(!disposed){setFailed(true);latest.current.onStatus('3D graphics unavailable. Use the location list.');}});
    }catch {
      setFailed(true);latest.current.onStatus('3D graphics unavailable. Use the location list.');
    }
    return ()=>{disposed=true;clearTimeout(warningTimer);map?.remove();mapRef.current=null;};
  },[offline]);
  useEffect(()=>{
    const map=mapRef.current;if(!map?.getSource('incidents'))return;
    map.getSource('incidents').setData(pointFeatures(incidents,'incident'));
    map.getSource('zones').setData(zoneFeatures(zones));
  },[incidents,zones]);
  useEffect(()=>{const map=mapRef.current;if(map?.getSource('facilities'))applyView(map,latest.current);},[layers,selected,threeD]);
  useEffect(()=>{
    const map=mapRef.current;if(!map)return;
    const motion=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    map.easeTo({...view,zoom:offline?Math.min(view.zoom || 11.5,11.5):view.zoom,pitch:!offline&&threeD?57:0,duration:motion?0:900});
  },[view,threeD,offline]);
  return <><div ref={container} className="map-canvas" data-testid="city-map"/>{failed&&<div className="map-unavailable"><strong>Map graphics are unavailable</strong><p>All care locations and event details remain available in the sidebar.</p></div>}</>;
}
