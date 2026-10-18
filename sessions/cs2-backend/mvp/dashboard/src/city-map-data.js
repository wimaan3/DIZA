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

// Reused by the Operations map and standalone city explorer.
export const CITY_STYLE = 'https://tiles.openfreemap.org/styles/liberty';
export function configureBuildings(map, threeD=true) {
  for (const layer of map.getStyle().layers) if (layer['source-layer']==='poi') map.setLayoutProperty(layer.id,'visibility','none');
  if (map.getLayer('building')) map.setLayerZoomRange('building',13,24);
  if (!map.getLayer('building-3d')) return;
  map.setPaintProperty('building-3d','fill-extrusion-color',['interpolate',['linear'],['coalesce',['get','render_height'],0],0,'#c8d5c7',50,'#a5bba8',150,'#709e8d',300,'#396f60']);
  map.setPaintProperty('building-3d','fill-extrusion-opacity',0.92);
  map.setLayoutProperty('building-3d','visibility',threeD?'visible':'none');
}
export function position(item) {
  const valid=(n,max)=> (typeof n==='number'||typeof n==='string') && String(n).trim()!=='' && Number.isFinite(Number(n)) && Math.abs(Number(n))<=max;
  return item && valid(item.lon,180) && valid(item.lat,90) ? [Number(item.lon),Number(item.lat)] : null;
}
