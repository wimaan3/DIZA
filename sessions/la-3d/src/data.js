export const PRESETS = [
  {id:'downtown', name:'Downtown', subtitle:'The city at a glance', center:[-118.255,34.049], zoom:15.3, bearing:-24},
  {id:'usc', name:'USC / West Adams', subtitle:'Campus & surrounding neighborhoods', center:[-118.285,34.023], zoom:15.4, bearing:24},
  {id:'westwood', name:'Westwood', subtitle:'West Los Angeles', center:[-118.435,34.061], zoom:15.2, bearing:-24},
  {id:'santa-monica', name:'Santa Monica', subtitle:'The Westside coast', center:[-118.489,34.025], zoom:15.1, bearing:30},
];
const verified = '2026-10-17';
export const FACILITIES = [
  {id:'sakura', name:'Sakura Gardens', fullName:'Sakura Gardens of Los Angeles', type:'Assisted living', area:'Boyle Heights', address:'325 S Boyle Ave, Los Angeles, CA 90033', lon:-118.219828031771, lat:34.045119592941, source:'https://sakuragardenslosangeles.com/contact-us/', verified},
  {id:'st-john', name:'St. John of God', fullName:'St. John of God Retirement and Care Center', type:'Assisted living & skilled nursing campus', area:'West Adams', address:'2468 S St Andrews Pl, Los Angeles, CA 90018', lon:-118.311220383682, lat:34.033328959907, source:'https://stjog.org/', verified},
  {id:'belmont', name:'Belmont Village Westwood', fullName:'Belmont Village Westwood', type:'Senior living', area:'Westwood', address:'10475 Wilshire Blvd, Los Angeles, CA 90024', lon:-118.431481361332, lat:34.065071565508, source:'https://www.belmontvillage.com/locations/westwood-los-angeles-california/', verified},
  {id:'ivy', name:'Ivy Park at Santa Monica', fullName:'Ivy Park at Santa Monica', type:'Assisted living & memory care', area:'Santa Monica', address:'1312 15th St, Santa Monica, CA 90404', lon:-118.486123840506, lat:34.025941461588, source:'https://ivyliving.com/santamonica/', verified},
].map(f=>({...f, kind:'facility', geocoder:'US Census address interpolation', geocodeSource:`https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address=${encodeURIComponent(f.address)}&benchmark=Public_AR_Current&format=json`}));

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
