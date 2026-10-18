import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import {ArrowUpRight,Building2,ChevronRight,Globe2,HeartHandshake,Layers,MapPin,Radio,RotateCcw,Search,ShieldCheck,TriangleAlert,X} from 'lucide-react';
import CityMap from './CityMap.jsx';
import {FACILITIES,PRESETS,position,severity,SEVERITY_COLORS} from './data.js';
import {useOps} from './useOps.js';
import './styles.css';
import {logoLight,logoLightStill} from '../../elder-care/branding/logo.js';
const EMPTY=[];
function App() {
  const [mode,setMode]=useState('demo'), [token,setToken]=useState(''),[draftToken,setDraftToken]=useState(''),[retry,setRetry]=useState(0);
  const [activeArea,setActiveArea]=useState('downtown'),[view,setView]=useState(PRESETS[0]),[threeD,setThreeD]=useState(true),[offline,setOffline]=useState(false);
  const [layers,setLayers]=useState({facilities:true,incidents:true,zones:true}),[tab,setTab]=useState('facilities'),[query,setQuery]=useState(''),[selected,setSelected]=useState(null),[mapStatus,setMapStatus]=useState('Loading map…');
  const ops=useOps(mode,token,retry), incidents=ops.data?.incidents || EMPTY,zones=ops.data?.zones || EMPTY;
  const currentSelected=selected?.kind==='incident'?incidents.find(i=>String(i.id)===String(selected.id)):selected;
  const detail=currentSelected?{...currentSelected,kind:selected.kind}:null;
  const located=incidents.filter(position).length;
  function select(item) {
    setSelected(item);
    const p=position(item);
    if(p){setView({center:p,zoom:16.2,bearing:-20});setActiveArea('');}
  }
  function go(p){setActiveArea(p.id);setView(p);setSelected(null);}
  function switchMode(next){setMode(next);setSelected(null);}
  const list=(tab==='facilities'?FACILITIES:incidents).filter(i=>[i.name,i.location,i.address,i.summary,i.area].some(s=>s?.toLowerCase().includes(query.toLowerCase())));
  const Icon=tab==='facilities'?HeartHandshake:Radio;
  return <div className="app-shell">
    <header className="topbar">
      <a className="brand" href="/" aria-label="DIZA dashboard"><picture><source media="(prefers-reduced-motion: reduce)" srcSet={logoLightStill}/><img className="diza-logo" src={logoLight} alt="DIZA" width="431" height="128"/></picture><span className="brand-divider"/><span className="product-name">Community operations</span></a>
      <div className="topbar-right"><span className="region-label">LOS ANGELES, CA</span><a className="dashboard-link" href="/">Operations dashboard <ArrowUpRight size={14}/></a></div>
    </header>
    <main className="workspace">
      <aside className="sidebar" aria-label="Location directory">
        <div className="sidebar-heading"><div className="eyebrow"><span className="live-dot"/>COMMUNITY AT A GLANCE</div><h1>A closer look<br/>{' '}at Los Angeles.</h1><p>Connect the places people live<br className="desktop-break"/> with the support they need.</p></div>
        <div className="dataset-selector" aria-label="Event data source"><button className={mode==='demo'?'active':''} aria-pressed={mode==='demo'} onClick={()=>switchMode('demo')}>Demo scenarios</button><button className={mode==='live'?'active':''} aria-pressed={mode==='live'} onClick={()=>switchMode('live')}>Backend events</button></div>
        {mode==='live'&&<form className="connection" onSubmit={e=>{e.preventDefault();setToken(draftToken.trim());setRetry(n=>n+1);}}><label htmlFor="operator-token">Operator access</label><div><input id="operator-token" type="password" value={draftToken} onChange={e=>setDraftToken(e.target.value)} placeholder="Token, if configured" autoComplete="off"/><button type="submit">Connect</button></div></form>}
        <div className={`data-notice ${ops.error?'error':''}`} role="status">{ops.error?<><TriangleAlert size={15}/><span>{ops.error}{ops.data?' Showing the last successful snapshot.':''}</span></>:mode==='demo'?<><ShieldCheck size={15}/><span>Fictional events · real public care locations</span></>:<><Radio size={15}/><span>{ops.loading?'Connecting to DIZA…':ops.updated?`Updated ${ops.updated.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'})}`:'Waiting for backend'}</span></>}</div>
        <div className="stats"><div><strong>{FACILITIES.length.toString().padStart(2,'0')}</strong><span>Care locations</span></div><div><strong>{incidents.length.toString().padStart(2,'0')}</strong><span>{mode==='demo'?'Sample events':'Backend events'}</span></div><div><strong>{located.toString().padStart(2,'0')}</strong><span>On the map</span></div></div>
        <div className="directory-tabs" role="tablist" aria-label="Directory"><button role="tab" aria-selected={tab==='facilities'} onClick={()=>{setTab('facilities');setQuery('');}}>Care directory <span>{FACILITIES.length}</span></button><button role="tab" aria-selected={tab==='incidents'} onClick={()=>{setTab('incidents');setQuery('');}}>Events <span>{incidents.length}</span></button></div>
        <label className="search"><Search size={16}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder={tab==='facilities'?'Find a care location…':'Find an event…'} aria-label="Search locations or events"/></label>
        <div className="location-list" role="tabpanel" aria-label={tab==='facilities'?'Care directory':'Events'}>
          {list.map(item=><button className={`location-card ${detail?.id===item.id?'selected':''}`} key={item.id} onClick={()=>select({...item,kind:tab==='facilities'?'facility':'incident'})} aria-pressed={detail?.id===item.id}>
            <span className={`location-icon ${tab==='incidents'?'event-icon':''}`} style={tab==='incidents'?{color:SEVERITY_COLORS[severity(item)]}:undefined}><Icon size={19}/></span>
            <span className="card-copy"><strong>{item.name || item.location || 'Location not described'}</strong><span>{tab==='facilities'?item.area:!position(item)?'Location needed':`${severity(item)} · ${item.source==='simulated'?'Simulated':item.category || 'Report'}`}</span></span><ChevronRight size={16}/>
          </button>)}
          {!list.length&&<p className="empty-state">{query?'No matching locations.':ops.error?'Events unavailable. Check the connection above.':ops.loading?'Loading events…':'No events in this dataset.'}</p>}
        </div>
        <div className="directory-foot"><ShieldCheck size={17}/><p>Curated public locations.<br/><span>Not a complete directory or shelter list.</span></p></div>
      </aside>
      <section className="map-section" aria-label="Los Angeles 3D map">
        <div className="map-toolbar"><div className="area-tabs" aria-label="Map area">{PRESETS.map(p=><button key={p.id} className={activeArea===p.id?'active':''} aria-pressed={activeArea===p.id} onClick={()=>go(p)}>{p.name}</button>)}</div><button className="overview" onClick={()=>go({id:'overview',center:[-118.356,34.045],zoom:10.8,bearing:0})}><Globe2 size={15}/>LA overview</button></div>
        <div className="map-frame">
          <CityMap incidents={incidents} zones={zones} selected={detail} onSelect={select} view={view} threeD={threeD} layers={layers} offline={offline} onStatus={setMapStatus}/>
          <div className="map-heading"><span className="eyebrow">{offline?'OFFLINE OUTLINE':threeD?'3D CITY EXPLORER':'2D CITY EXPLORER'}</span><h2>{PRESETS.find(p=>p.id===activeArea)?.name || (activeArea==='overview'?'Greater Los Angeles':detail?.area || 'Selected location')}</h2><span className={`mode-tag ${mode==='demo'?'demo':''}`}><span/>{mode==='demo'?'SIMULATED EVENTS':ops.error?'BACKEND CONNECTION ISSUE':ops.loading?'CONNECTING…':'BACKEND EVENTS'}</span></div>
          <div className="view-tools"><div className="segmented" aria-label="Map perspective"><button disabled={offline} aria-pressed={threeD&&!offline} className={threeD&&!offline?'active':''} onClick={()=>setThreeD(true)}><Building2 size={15}/>3D</button><button aria-pressed={!threeD||offline} className={!threeD||offline?'active':''} onClick={()=>setThreeD(false)}>2D</button></div><button className="reset" aria-label="Reset Downtown view" title="Reset Downtown view" onClick={()=>go(PRESETS[0])}><RotateCcw size={16}/></button></div>
          <div className="layer-control"><div><Layers size={15}/><strong>Map layers</strong></div>{[['facilities','Care locations','green'],['incidents',mode==='demo'?'Sample events':'Backend events','orange'],['zones','Operator zones','purple']].map(([id,label,color])=><label key={id}><input type="checkbox" checked={layers[id]} onChange={e=>setLayers({...layers,[id]:e.target.checked})}/><span className={`legend-dot ${color}`}/>{label}</label>)}<label className="offline-toggle"><input type="checkbox" checked={offline} onChange={e=>setOffline(e.target.checked)}/>Offline outline</label></div>
          {detail&&<article className="detail-card" aria-label="Selected location"><button className="close-detail" aria-label="Close location details" onClick={()=>setSelected(null)}><X size={18}/></button><div className="eyebrow">{detail.kind==='facility'?'CARE LOCATION':detail.source==='simulated'?'SIMULATED EVENT':'BACKEND EVENT'}</div><h3>{detail.fullName || detail.location || 'Location not described'}</h3><p>{detail.kind==='facility'?detail.type:detail.summary}</p>{detail.kind==='facility'?<><div className="detail-address"><MapPin size={16}/>{detail.address}</div><p className="fine-print">Approximate address position · US Census geocoder.<br/>Services and availability must be checked with the facility.</p><a href={detail.source} target="_blank" rel="noreferrer">Facility website <ArrowUpRight size={15}/></a></>:<><div className="event-meta"><span>{severity(detail)}</span><span>{detail.request?.status || 'Reported'}</span><span>{detail.language || 'Language unknown'}</span></div><p className="fine-print">{position(detail)?'Reported or geocoded position; verify before use.':'No usable coordinates. This event is listed but has no map pin.'}</p><a href="/">Review in operations <ArrowUpRight size={15}/></a></>}</article>}
          {!detail&&<div className="map-hint"><MapPin size={16}/><span>Select a location to see its details.</span></div>}
        </div>
        <footer className="map-footer"><span role="status">{mapStatus==='3D map ready'?`${threeD?'3D':'2D'} map ready`:mapStatus}</span><span>Building heights may be estimated · no indoor layouts</span></footer>
      </section>
    </main>
  </div>;
}
createRoot(document.getElementById('root')).render(<App/>);
