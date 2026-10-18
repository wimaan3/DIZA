// One resident-services workflow for apartments and assisted living.
const done = (item) => item.kind === "care" ? item.record.status === "resolved" : item.record.status === "closed" && item.requests.every((request) => request.status === "resolved");
  const priority = (item) => item.urgency === "emergency" ? 0 : item.urgency === "urgent" ? 1 : 2;

export function residentRequests(data) {
    const people = Object.fromEntries(data.residents.map((person) => [person.id, person]));
    const tickets = data.facility_workflow.tickets;
    const grouped = tickets.filter((ticket) => !ticket.merged_into).map((record) => {
      const origins = tickets.filter((ticket) => ticket.code === record.code || ticket.merged_into === record.code);
      const codes = new Set(origins.map((ticket) => ticket.code));
      const requests = data.requests.filter((request) => codes.has(request.facility_code));
      const urgency = record.urgency === "emergency" ? "emergency" : record.urgency === "urgent" || requests.some((request) => request.urgency === "urgent" && request.status !== "resolved") ? "urgent" : "routine";
      return {key:"repair:"+record.code, kind:"repair", record, requests, urgency,
        rooms:[...new Set(origins.map((ticket) => ticket.unit))], room:record.unit,
        name:[...new Set(requests.map((request) => people[request.resident_id]?.name || "Resident"))].join(", "),
        reports:origins.reduce((sum,ticket) => sum+ticket.reporters.length,0)};
    });
    const groupedIds = new Set(grouped.flatMap((item) => item.requests.map((request) => request.id)));
    return [
      ...data.requests.filter((request) => !groupedIds.has(request.id)).map((record) => ({key:"care:"+record.id, kind:"care", record, requests:[record], urgency:record.urgency, rooms:[people[record.resident_id]?.room || ""], room:people[record.resident_id]?.room || "", name:people[record.resident_id]?.name || "Resident"})),
      ...grouped,
    ].sort((a,b) => priority(a)-priority(b) || a.record.created-b.record.created || a.key.localeCompare(b.key));
  }

export function residentRequestCounts(data) {
  const open=residentRequests(data).filter((item)=>!done(item));
  return {urgent:open.filter((item)=>priority(item)<2).length,
    everyday:open.filter((item)=>priority(item)===2).length};
}

export function createBuildingWorkspace({esc, icon, age, facility, requestCard, careDetail, setCareSelection}) {
  let selected = null, roomFilter = "", filter = "open", search = "", lastItems = [], focusedResident = null;
  const visible = (item) =>
    (filter === "completed" ? done(item) : !done(item)) &&
    (filter !== "urgent" || priority(item) < 2) &&
    (filter !== "everyday" || priority(item) === 2) &&
    (!roomFilter || item.rooms.includes(roomFilter)) &&
    `${item.record.summary} ${item.rooms.join(" ")} ${item.record.code} ${item.name} ${item.requests.map((request)=>request.summary+" "+request.quote).join(" ")}`.toLowerCase().includes(search.toLowerCase());

  const items=residentRequests;

  function floorPlan(data, current, disabled) {
    const rooms = data.facility_workflow.rooms;
    const stacks = [...new Set(rooms.map((room) => room.stack || "?"))].sort();
    const floors = [...new Set(rooms.map((room) => room.floor))].sort((a,b) => b-a);
    const W=176,H=88,G=12,L=40,T=32;
    const position = (room) => ({x:L+stacks.indexOf(room.stack||"?")*(W+G), y:T+floors.indexOf(room.floor)*(H+G)});
    const currentTicket = current?.kind === "repair" ? current.record : data.facility_workflow.tickets.find((ticket) => ticket.code === current?.record.facility_code);
    const related = new Set(currentTicket?.related.map((link) => data.facility_workflow.tickets.find((ticket) => ticket.code === link.code)?.unit) || []);
    const from = rooms.find((room) => room.unit === currentTicket?.unit);
    return `<section class="panel combined-floorplan" aria-labelledby="combined-map-title"><div class="panel-heading"><div><h2 id="combined-map-title">Building floor plan</h2><p>Select a unit to see every resident request, from repairs to personal support.</p></div><span class="tag">${rooms.length} rooms</span></div><div class="combined-map-scroll"><svg viewBox="0 0 ${L+stacks.length*(W+G)} ${T+floors.length*(H+G)}" role="group" aria-label="Building floor plan: resident rooms, care requests and repairs">
      ${stacks.map((stack,index)=>`<text class="map-axis" x="${L+index*(W+G)+W/2}" y="18" text-anchor="middle">Riser ${esc(stack)}</text>`).join("")}
      ${floors.map((floor,index)=>`<text class="map-axis" x="4" y="${T+index*(H+G)+H/2}">F${floor}</text>`).join("")}
      ${from ? rooms.filter((room)=>related.has(room.unit)).map((room)=>{const a=position(from),b=position(room);return `<line class="room-relation-line" x1="${a.x+W/2}" y1="${a.y+H/2}" x2="${b.x+W/2}" y2="${b.y+H/2}"/>`;}).join("") : ""}
      ${rooms.map((room)=>{
        const p=position(room), needs=lastItems.filter((item)=>item.rooms.includes(room.unit)&&!done(item));
        const urgent=needs.some((item)=>priority(item)<2);
        const names=data.residents.filter((person)=>person.room===room.unit).map((person)=>person.name).join(", ");
        return `<g role="button" tabindex="0" data-building-room="${esc(room.unit)}" class="combined-room ${urgent?"urgent-room":""} ${roomFilter===room.unit?"filtered-room":""} ${related.has(room.unit)?"related-room":""}" aria-pressed="${roomFilter===room.unit}" aria-label="Room ${esc(room.unit)}, ${esc(names||"unoccupied")}, ${needs.length} open ${needs.length===1?"request":"requests"}${related.has(room.unit)?", related room":""}"><rect x="${p.x}" y="${p.y}" width="${W}" height="${H}" rx="8"/><text class="room-number" x="${p.x+12}" y="${p.y+23}">Room ${esc(room.unit)}${urgent?" !":""}</text><text class="room-resident" x="${p.x+12}" y="${p.y+44}">${esc(names.length>23?names.slice(0,21)+"…":names||"Unoccupied")}</text><text class="room-count" x="${p.x+12}" y="${p.y+68}">${needs.length} open ${needs.length===1?"request":"requests"}</text></g>`;
      }).join("")}</svg></div><div class="map-legend"><span class="tag urgent-tag">Urgent need</span><span class="tag">Everyday requests</span><span class="tag shared-tag">Related room</span></div><div class="combined-room-metadata">${rooms.map((room)=>`<span>Room ${esc(room.unit)} · HVAC ${esc(room.hvac_zone)}${["care_lead","facilities","manager"].includes(data.staff.find((staff)=>staff.id===data.workingStaff)?.role)?` <button class="edit-room" data-edit-room="${esc(room.unit)}" ${disabled}>Edit room ${esc(room.unit)}</button>`:""}</span>`).join("")}</div></section>`;
  }

  function checkins(data, disabled) {
    const canManage=["nurse","care_lead","manager"].includes(data.staff.find((staff)=>staff.id===data.workingStaff)?.role);
    const enrolled=data.residents.filter((person)=>person.checkin_enabled);
    return `<section class="panel combined-checkins" aria-labelledby="combined-checkins-title"><div class="panel-heading"><div><h2 id="combined-checkins-title">Residents & support</h2><p>Check-ins are optional for each resident.</p></div>${canManage?`<button class="secondary small" data-profile="new" ${disabled}>Add resident</button>`:""}</div><p class="support-summary">${enrolled.filter((person)=>person.checkin?.outcome==="seen_well").length}/${enrolled.length} scheduled check-ins seen well today</p>${data.residents.map((person)=>{
      const outcome=person.checkin?.outcome;
      const status=!person.checkin_enabled?"Check-ins not scheduled":outcome==="seen_well"?"Seen well today":outcome==="follow_up"?"Follow-up requested":outcome==="no_response"?"No response - review needed":person.checkin_due?"Check-in overdue":"Not yet checked in";
      return `<div class="combined-checkin-row"><div><strong>${esc(person.name)}</strong><span>Room ${esc(person.room)} · ${esc(status)}</span>${person.checkin_enabled&&person.checkin?.note?`<small>${esc(person.checkin.note)}</small>`:""}</div><div class="resident-row-actions">${person.checkin_enabled?`<button class="secondary small" data-checkin="${esc(person.id)}" aria-label="${outcome?"Update":"Record"} check-in for ${esc(person.name)}" ${disabled} ${data.staff.find((staff)=>staff.id===data.workingStaff)?.role==="facilities"?"disabled":""}>${outcome?"Update":"Check in"}</button>`:""}${canManage?`<button class="text-button" data-profile="${esc(person.id)}" aria-label="Edit profile for ${esc(person.name)}" ${disabled}>Edit</button>`:""}</div></div>`;
    }).join("")}</section>`;
  }

  function repairRow(item, chosen) {
    const ticket=item.record;
    return `<button class="request-card ${chosen?"selected":""} ${priority(item)<2?"urgent-card":""}" data-building-item="${esc(item.key)}" aria-pressed="${chosen}"><span class="request-icon sand">${icon("grid",21)}</span><span class="card-content"><span class="card-top"><strong>${esc(ticket.summary)}</strong><span class="age">${age(ticket.created)}</span></span><span class="resident-line">Room ${esc(ticket.unit)} · ${esc(ticket.code)} · ${item.reports} reports</span><span class="card-bottom"><span class="tag">Maintenance</span><span class="tag ${priority(item)<2?"urgent-tag":""}">${esc(item.urgency)}</span><span class="tag">${ticket.status==="closed"&&!done(item)?"Resident follow-up pending":esc(ticket.status.replaceAll("_"," "))}</span></span></span></button>`;
  }

  function insights(data) {
    const info=data.facility_workflow.insights;
    const seconds=info.median_first_action_s;
    const elapsed=seconds==null?"Not recorded":seconds<60?"Under 1 min":seconds<3600?`${Math.round(seconds/60)} min`:`${Math.round(seconds/3600)} hr`;
    const top=info.top_repeats[0];
    return `<section class="facility-insights combined-repair-insights" aria-label="Building response insights"><article><span>Median first repair action</span><strong>${elapsed}</strong><small>Assignment, note or resident update</small></article><article><span>Duplicate reports grouped</span><strong>${info.duplicates_merged_week}</strong><small>Every original report is retained</small></article><article><span>Top shared problem</span><strong>${top?top.count+" linked":"None yet"}</strong><small>${top?esc(top.problem+" · "+top.where):"Same room, riser or HVAC zone"}</small></article><article><span>Report languages</span><strong>${Object.keys(info.language_mix||{}).length}</strong><small>${esc(Object.keys(info.language_mix||{}).join(", ")||"No reports yet")}</small></article></section>`;
  }

  function render(data, staffId, disabled) {
    lastItems=items(data);
    const list=lastItems.filter(visible);
    const current=list.find((item)=>item.key===selected)||list[0];
    selected=current?.key||null;
    if(current?.kind==="care") setCareSelection(current.record.id);
    const focused=current?.kind==="repair"?current.requests.find((request)=>request.id===focusedResident):null;
    if(focused) setCareSelection(focused.id);
    const content=current?.kind==="care"?careDetail(current.record):focused?`<div class="case-context"><strong>${esc(current.record.code)} · Maintenance</strong><button class="secondary small" data-building-item="${esc(current.key)}">Back to repair & reports</button></div>${careDetail(focused)}`:current?facility.renderDetail(current.record,data,staffId,disabled):"";
    const snapshot={...data,workingStaff:staffId};
    return `<div class="combined-building-top">${floorPlan(snapshot,current,disabled)}${checkins(snapshot,disabled)}</div><div class="workspace-grid combined-work-grid"><section class="panel queue-panel" aria-labelledby="combined-queue-title"><div class="panel-heading"><div><h2 id="combined-queue-title">Resident requests <span class="count">${list.length}</span></h2><p>Repairs, everyday help and urgent support. One request per issue.</p></div><span class="subtle-label">J / K TO MOVE</span></div><div class="combined-filters" role="group" aria-label="Filter building work">${[["open","All open"],["urgent","Urgent"],["everyday","Everyday"],["completed","Completed"]].map(([id,label])=>`<button class="secondary small" data-building-filter="${id}" aria-pressed="${filter===id}">${label}</button>`).join("")}</div><div class="queue-tools"><label class="search">${icon("search",17)}<input id="building-search" type="search" aria-label="Search building work" placeholder="Search resident, room, or issue" value="${esc(search)}"></label></div>${roomFilter?`<div class="room-filter">Room ${esc(roomFilter)} <button data-building-room="*" aria-label="Clear room filter">${icon("close",14)}</button></div>`:""}<div class="request-list">${list.length?list.map((item)=>item.kind==="care"?requestCard(item.record,item.key===selected,true):repairRow(item,item.key===selected)).join(""):'<div class="empty"><h3>No matching work</h3><p>Choose another room, search or queue filter.</p></div>'}</div></section><aside class="panel detail-panel" aria-label="Selected building item">${current?content:'<div class="detail-placeholder"><h3>Every need, in one place.</h3><p>Select a resident request to coordinate the response.</p></div>'}</aside></div>${insights(data)}`;
  }

  return {
    render,
    overview:residentRequestCounts,
    select(key, reveal=false) {
      focusedResident=null;
      if(key.startsWith("care:")) {
        const id=key.slice(5),group=lastItems.find((item)=>item.kind==="repair"&&item.requests.some((request)=>request.id===id));
        if(group){key=group.key;focusedResident=id;}
      }
      selected=key;
      if(reveal){const item=lastItems.find((entry)=>entry.key===key);if(!item||!visible(item)){roomFilter="";search="";filter=item&&done(item)?"completed":"open";}}
    },
    room(value){roomFilter=value==="*"||roomFilter===value?"":value;selected=null;},
    filter(value){filter=value;selected=null;},
    search(value){search=value;selected=null;},
    move(direction){const list=lastItems.filter(visible),index=list.findIndex((item)=>item.key===selected);if(list[index+direction])selected=list[index+direction].key;},
  };
}
