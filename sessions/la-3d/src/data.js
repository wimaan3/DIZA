export {PRESETS,FACILITIES} from '../../cs2-backend/mvp/dashboard/src/city-map-data.js';

// Fictional scenarios, deliberately not attributed to the real facilities above.
export const DEMO = {
  incidents:[
    {id:'demo-1',location:'Downtown · sample location',summary:'A caller asks for an accessible ride after a canceled appointment.',category:'transport',effective:'P2',lat:34.0468,lon:-118.2567,source:'simulated',language:'en',request:{status:'new'}},
    {id:'demo-2',location:'USC area · sample location',summary:'A caller reports an elevator outage and asks for staff assistance.',category:'infrastructure',effective:'P1',lat:34.025,lon:-118.281,source:'simulated',language:'zh',request:{status:'new'}},
    {id:'demo-3',location:'Westwood · sample location',summary:'A caller requests a follow-up about an upcoming community check-in.',category:'info',effective:'P3',lat:34.058,lon:-118.441,source:'simulated',language:'es',request:{status:'new'}},
  ], zones:[],
};
export const SEVERITY_COLORS = {P0:'#aa352e',P1:'#b96326',P2:'#a37e25',P3:'#326c83',UNKNOWN:'#626d69'};
export const ZONE_COLORS = {evacuation_order:'#7d1d10',evacuation_warning:'#c0442a',hazard:'#8a5a00',staging:'#22553e',note:'#4a6fa5'};
export function coordinate(value, max) {
  if (value === null || value === undefined || typeof value === 'boolean' || (typeof value !== 'number' && typeof value !== 'string') || String(value).trim() === '') return null;
  const n = Number(value);
  return Number.isFinite(n) && Math.abs(n) <= max ? n : null;
}
export function position(item) {
  const lat=coordinate(item.lat,90), lon=coordinate(item.lon,180);
  return lat === null || lon === null ? null : [lon,lat];
}
export const severity = item => Object.hasOwn(SEVERITY_COLORS,item.effective || item.severity) ? item.effective || item.severity : 'UNKNOWN';
export const collection = features => ({type:'FeatureCollection',features});
export function pointFeatures(items,kind) {
  return collection(items.filter(position).map(item=>({type:'Feature',geometry:{type:'Point',coordinates:position(item)},properties:{id:String(item.id),kind,name:kind==='facility'?item.name:item.location || 'Location not described',severity:severity(item),color:kind==='facility'?'#245a4b':SEVERITY_COLORS[severity(item)]}})));
}
export function zoneFeatures(zones) {
  return collection(zones.flatMap(zone=>{
    if (!Array.isArray(zone.points) || zone.points.length<3) return [];
    const ring=zone.points.map(p=>Array.isArray(p)&&p.length===2?position({lat:p[0],lon:p[1]}):null);
    if (ring.some(p=>!p) || new Set(ring.map(p=>p.join(','))).size<3) return [];
    if (ring[0][0]!==ring.at(-1)[0] || ring[0][1]!==ring.at(-1)[1]) ring.push([...ring[0]]);
    return [{type:'Feature',geometry:{type:'Polygon',coordinates:[ring]},properties:{id:String(zone.id),name:zone.name || 'Operator zone',kind:zone.kind,color:ZONE_COLORS[zone.kind] || ZONE_COLORS.note}}];
  }));
}
export function validateOps(payload) {
  if (!payload || !Array.isArray(payload.incidents) || !Array.isArray(payload.zones) || payload.incidents.some(i=>!i || typeof i!=='object' || i.id===undefined) || payload.zones.some(z=>!z || typeof z!=='object')) throw new Error('Unexpected backend response. Check that /api/ops is available.');
  return {incidents:payload.incidents,zones:payload.zones};
}
