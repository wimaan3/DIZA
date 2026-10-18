import test from 'node:test';
import assert from 'node:assert/strict';
import {position,pointFeatures,zoneFeatures,validateOps,FACILITIES,DEMO,severity} from '../src/data.js';

test('backend lat/lon becomes GeoJSON lon/lat; missing positions are never guessed',()=>{
  assert.deepEqual(position({lat:'34.025',lon:-118.28}),[-118.28,34.025]);
  assert.deepEqual(position({lat:0,lon:0}),[0,0]);
  for(const lat of [null,undefined,'', ' ',true,[],{},Infinity,'NaN',91]) assert.equal(position({lat,lon:-118.28}),null);
  assert.equal(position({lat:34,lon:181}),null);
  const report={id:'missing',lat:null,lon:-118.28};
  assert.equal(pointFeatures([report],'incident').features.length,0);
  assert.equal(report.lat,null);
});

test('read-only zones convert coordinate order, close the ring, and reject broken polygons',()=>{
  const points=[[34,-118],[34.01,-118],[34,-118.01]];
  const result=zoneFeatures([{id:'z',kind:'hazard',points}]);
  assert.deepEqual(result.features[0].geometry.coordinates[0],[[-118,34],[-118,34.01],[-118.01,34],[-118,34]]);
  assert.equal(points.length,3);
  for(const invalid of [[[null,-118],[34,-118],[34,-117]],[[34,-118],[34,-118],[34,-118]]]) assert.equal(zoneFeatures([{points:invalid}]).features.length,0);
});

test('bad API responses cannot masquerade as an empty operation',()=>{
  for(const payload of [null,{}, {incidents:[]}, {incidents:[null],zones:[]}, {incidents:[],zones:[null]}]) assert.throws(()=>validateOps(payload));
  assert.deepEqual(validateOps({incidents:[],zones:[]}),{incidents:[],zones:[]});
  assert.equal(severity({effective:'P0',severity:'P3'}),'P0');
  assert.equal(severity({}),'UNKNOWN');
});

test('facility provenance is preserved and demos do not impersonate facilities',()=>{
  assert.equal(FACILITIES.length,4);
  for(const f of FACILITIES){assert.ok(position(f));assert.ok(f.source.startsWith('https://'));assert.ok(f.geocodeSource.startsWith('https://geocoding.geo.census.gov/'));}
  for(const i of DEMO.incidents){assert.equal(i.source,'simulated');assert.ok(!FACILITIES.some(f=>JSON.stringify(position(f))===JSON.stringify(position(i))));}
});
