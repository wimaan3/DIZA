// One room map, mixed work queue and detail pane for the care home.
export function createBuildingWorkspace({esc, icon, age, facility, requestCard, careDetail, setCareSelection}) {
  let selected = null, roomFilter = "", filter = "open", search = "", lastItems = [];
  const done = (item) => item.kind === "care" ? item.record.status === "resolved" : item.record.status === "closed";
  const priority = (item) => item.record.urgency === "emergency" ? 0 : item.record.urgency === "urgent" ? 1 : 2;
  const visible = (item) =>
    (filter === "completed" ? done(item) : !done(item)) &&
    (filter !== "urgent" || priority(item) < 2) &&
    (filter !== "everyday" || priority(item) === 2) &&
    (!roomFilter || item.room === roomFilter) &&
    `${item.record.summary} ${item.room} ${item.record.code} ${item.name}`.toLowerCase().includes(search.toLowerCase());

  function items(data) {
    const people = Object.fromEntries(data.residents.map((person) => [person.id, person]));
    return [
      ...data.requests.map((record) => ({key:"care:" + record.id, kind:"care", record, room:people[record.resident_id]?.room || "", name:people[record.resident_id]?.name || "Resident"})),
      ...data.facility_workflow.tickets.filter((record) => !record.merged_into).map((record) => ({key:"repair:" + record.code, kind:"repair", record, room:record.unit, name:"Repair incident"})),
    ].sort((a,b) => priority(a) - priority(b) || a.record.created - b.record.created || a.key.localeCompare(b.key));
  }

  function floorPlan(data, current, disabled) {
    const rooms = data.facility_workflow.rooms;
    const stacks = [...new Set(rooms.map((room) => room.stack || "?"))].sort();
    const floors = [...new Set(rooms.map((room) => room.floor))].sort((a,b) => b-a);
    const W=176,H=88,G=12,L=40,T=32;
    const position = (room) => ({x:L+stacks.indexOf(room.stack||"?")*(W+G), y:T+floors.indexOf(room.floor)*(H+G)});
    const currentTicket = current?.kind === "repair" ? current.record : data.facility_workflow.tickets.find((ticket) => ticket.code === current?.record.facility_code);
    const related = new Set(currentTicket?.related.map((link) => data.facility_workflow.tickets.find((ticket) => ticket.code === link.code)?.unit) || []);
    const from = rooms.find((room) => room.unit === currentTicket?.unit);
    return `<section class="panel combined-floorplan" aria-labelledby="combined-map-title"><div class="panel-heading"><div><h2 id="combined-map-title">Building floor plan</h2><p>Select a room to see its care requests and repairs together.</p></div><span class="tag">${rooms.length} rooms</span></div><div class="combined-map-scroll"><svg viewBox="0 0 ${L+stacks.length*(W+G)} ${T+floors.length*(H+G)}" role="group" aria-label="Building floor plan: resident rooms, care requests and repairs">
      ${stacks.map((stack,index)=>`<text class="map-axis" x="${L+index*(W+G)+W/2}" y="18" text-anchor="middle">Riser ${esc(stack)}</text>`).join("")}
      ${floors.map((floor,index)=>`<text class="map-axis" x="4" y="${T+index*(H+G)+H/2}">F${floor}</text>`).join("")}
      ${from ? rooms.filter((room)=>related.has(room.unit)).map((room)=>{const a=position(from),b=position(room);return `<line class="room-relation-line" x1="${a.x+W/2}" y1="${a.y+H/2}" x2="${b.x+W/2}" y2="${b.y+H/2}"/>`;}).join("") : ""}
      ${rooms.map((room)=>{
        const p=position(room), needs=lastItems.filter((item)=>item.room===room.unit&&!done(item));
        const urgent=needs.some((item)=>priority(item)<2), care=needs.filter((item)=>item.kind==="care").length, repairs=needs.length-care;
        const names=data.residents.filter((person)=>person.room===room.unit).map((person)=>person.name).join(", ");
        return `<g role="button" tabindex="0" data-building-room="${esc(room.unit)}" class="combined-room ${urgent?"urgent-room":""} ${roomFilter===room.unit?"filtered-room":""} ${related.has(room.unit)?"related-room":""}" aria-pressed="${roomFilter===room.unit}" aria-label="Room ${esc(room.unit)}, ${esc(names||"unoccupied")}, ${care} care ${care===1?"request":"requests"}, ${repairs} ${repairs===1?"repair":"repairs"}${related.has(room.unit)?", related room":""}"><rect x="${p.x}" y="${p.y}" width="${W}" height="${H}" rx="8"/><text class="room-number" x="${p.x+12}" y="${p.y+23}">Room ${esc(room.unit)}${urgent?" !":""}</text><text class="room-resident" x="${p.x+12}" y="${p.y+44}">${esc(names||"Unoccupied")}</text><text class="room-count" x="${p.x+12}" y="${p.y+68}">${care} care · ${repairs} ${repairs===1?"repair":"repairs"}</text></g>`;
      }).join("")}</svg></div><div class="map-legend"><span class="tag urgent-tag">Urgent need</span><span class="tag">Everyday care / repairs</span><span class="tag shared-tag">Related room</span></div><div class="combined-room-metadata">${rooms.map((room)=>`<span>Room ${esc(room.unit)} · HVAC ${esc(room.hvac_zone)}${["care_lead","facilities"].includes(data.staff.find((staff)=>staff.id===data.workingStaff)?.role)?` <button class="edit-room" data-edit-room="${esc(room.unit)}" ${disabled}>Edit room ${esc(room.unit)}</button>`:""}</span>`).join("")}</div></section>`;
  }

  function checkins(data, disabled) {
    return `<section class="panel combined-checkins" aria-labelledby="combined-checkins-title"><div class="panel-heading"><div><h2 id="combined-checkins-title">Resident check-ins</h2><p>Today's observations and follow-up.</p></div><span class="tag">${data.residents.filter((person)=>person.checkin?.outcome==="seen_well").length}/${data.residents.length} seen well</span></div>${data.residents.map((person)=>{
      const outcome=person.checkin?.outcome;
      const status=outcome==="seen_well"?"Seen well today":outcome==="follow_up"?"Follow-up requested":outcome==="no_response"?"No response - review needed":person.checkin_due?"Check-in overdue":"Not yet checked in";
      return `<div class="combined-checkin-row"><div><strong>${esc(person.name)}</strong><span>Room ${esc(person.room)} · ${esc(status)}</span>${person.checkin?.note?`<small>${esc(person.checkin.note)}</small>`:""}</div><button class="secondary small" data-checkin="${esc(person.id)}" aria-label="${outcome?"Update":"Record"} check-in for ${esc(person.name)}" ${disabled} ${data.staff.find((staff)=>staff.id===data.workingStaff)?.role==="facilities"?"disabled":""}>${outcome?"Update":"Check in"}</button></div>`;
    }).join("")}</section>`;
  }

  function repairRow(item, chosen) {
    const ticket=item.record;
    return `<button class="request-card ${chosen?"selected":""} ${priority(item)<2?"urgent-card":""}" data-building-item="${esc(item.key)}" aria-pressed="${chosen}"><span class="request-icon sand">${icon("grid",21)}</span><span class="card-content"><span class="card-top"><strong>${esc(ticket.summary)}</strong><span class="age">${age(ticket.created)}</span></span><span class="resident-line">Room ${esc(ticket.unit)} · ${esc(ticket.code)} · ${ticket.reporters.length} reports</span><span class="card-bottom"><span class="tag">Repair incident</span><span class="tag ${priority(item)<2?"urgent-tag":""}">${esc(ticket.urgency)}</span><span class="tag">${esc(ticket.status.replaceAll("_"," "))}</span></span></span></button>`;
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
    const snapshot={...data,workingStaff:staffId};
    return `<div class="combined-building-top">${floorPlan(snapshot,current,disabled)}${checkins(snapshot,disabled)}</div><div class="workspace-grid combined-work-grid"><section class="panel queue-panel" aria-labelledby="combined-queue-title"><div class="panel-heading"><div><h2 id="combined-queue-title">Building work queue <span class="count">${list.length}</span></h2><p>Care requests and repairs, urgent first.</p></div><span class="subtle-label">J / K TO MOVE</span></div><div class="combined-filters" role="group" aria-label="Filter building work">${[["open","All open"],["urgent","Urgent"],["everyday","Everyday"],["completed","Completed"]].map(([id,label])=>`<button class="secondary small" data-building-filter="${id}" aria-pressed="${filter===id}">${label}</button>`).join("")}</div><div class="queue-tools"><label class="search">${icon("search",17)}<input id="building-search" type="search" aria-label="Search building work" placeholder="Search resident, room, or issue" value="${esc(search)}"></label></div>${roomFilter?`<div class="room-filter">Room ${esc(roomFilter)} <button data-building-room="*" aria-label="Clear room filter">${icon("close",14)}</button></div>`:""}<div class="request-list">${list.length?list.map((item)=>item.kind==="care"?requestCard(item.record,item.key===selected,true):repairRow(item,item.key===selected)).join(""):'<div class="empty"><h3>No matching work</h3><p>Choose another room, search or queue filter.</p></div>'}</div></section><aside class="panel detail-panel" aria-label="Selected building item">${current?current.kind==="care"?careDetail(current.record):facility.renderDetail(current.record,data,staffId,disabled):'<div class="detail-placeholder"><h3>Every need, in one place.</h3><p>Select a care request or repair incident.</p></div>'}</aside></div>${insights(data)}`;
  }

  return {
    render,
    select(key, reveal=false) {
      selected=key;
      if(reveal){const item=lastItems.find((entry)=>entry.key===key);roomFilter="";search="";filter=item&&done(item)?"completed":"open";}
    },
    room(value){roomFilter=value==="*"||roomFilter===value?"":value;selected=null;},
    filter(value){filter=value;selected=null;},
    search(value){search=value;selected=null;},
    move(direction){const list=lastItems.filter(visible),index=list.findIndex((item)=>item.key===selected);if(list[index+direction])selected=list[index+direction].key;},
  };
}
