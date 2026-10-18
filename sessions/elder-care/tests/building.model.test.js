import {test} from "node:test";
import assert from "node:assert/strict";
import {residentRequests, residentRequestCounts} from "../web/building.js";

const resident={id:"resident",name:"Jamie Rivers",room:"2D"};
const report=(id, facility_code, status="new")=>({id,facility_code,status,resident_id:resident.id,urgency:"routine",created:1});
const ticket=(code,unit,status="new",merged_into=null)=>({code,unit,status,merged_into,urgency:"routine",created:1,reporters:[{}]});
const snapshot=(requests,tickets)=>({residents:[resident],requests,facility_workflow:{tickets}});

test("duplicate maintenance reports occupy one queue entry and retain each follow-up",()=>{
  const data=snapshot([report("a","T1"),report("b","T1")],[ticket("T1","2D")]);
  const rows=residentRequests(data);
  assert.equal(rows.length,1);
  assert.equal(rows[0].requests.length,2);
  assert.deepEqual(residentRequestCounts(data),{urgent:0,everyday:1});
});

test("completion requires both physical work and every resident outcome",()=>{
  const data=snapshot([report("a","T1","resolved"),report("b","T1")],[ticket("T1","2D","closed")]);
  assert.equal(residentRequestCounts(data).everyday,1);
  data.requests[1].status="resolved";
  assert.equal(residentRequestCounts(data).everyday,0);
  data.facility_workflow.tickets[0].status="in_progress";
  assert.equal(residentRequestCounts(data).everyday,1);
});

test("a shared repair retains every affected unit and urgent resident need",()=>{
  const data=snapshot([report("a","T1"),{...report("b","T2"),urgency:"urgent"}],
    [ticket("T1","2D"),ticket("T2","3D","new","T1")]);
  const rows=residentRequests(data);
  assert.equal(rows.length,1);
  assert.deepEqual(rows[0].rooms,["2D","3D"]);
  assert.equal(rows[0].reports,2);
  assert.deepEqual(residentRequestCounts(data),{urgent:1,everyday:0});
});

test("personal requests coexist with maintenance and missing repair links stay visible",()=>{
  const data=snapshot([report("a",null),report("b","T1"),report("c","missing")],[ticket("T1","2D")]);
  assert.equal(residentRequests(data).length,3);
  assert.deepEqual(residentRequestCounts(data),{urgent:0,everyday:3});
});
