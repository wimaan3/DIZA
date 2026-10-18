export function createFacilityWorkspace({ esc, icon, age, clock }) {
  let selected = null,
    roomFilter = "",
    showClosed = false,
    lastData = null;
  const levels = ["emergency", "urgent", "routine"];
  const statuses = {
    new: "Unassigned",
    assigned: "Assigned",
    in_progress: "Repair in progress",
    waiting_tenant: "Arranging room access",
    closed: "Repair closed",
  };
  const duration = (seconds) =>
    seconds == null
      ? "Not recorded"
      : seconds < 60
        ? "Under 1 min"
        : seconds < 3600
          ? `${Math.floor(seconds / 60)} min`
          : seconds < 86400
            ? `${Math.round(seconds / 3600)} hr`
            : `${Math.round(seconds / 86400)} days`;
  const isCoordinator = (data) =>
    ["care_lead", "facilities"].includes(
      data.staff.find((s) => s.id === data.workingStaff)?.role,
    );
  const parent = (ticket, tickets) =>
    tickets.find((t) => t.code === ticket.merged_into) || ticket;
  function rows(data) {
    const tickets = data.facility_workflow.tickets;
    return tickets
      .filter(
        (t) =>
          !t.merged_into &&
          (showClosed || t.status !== "closed") &&
          (!roomFilter ||
            t.unit === roomFilter ||
            tickets.some(
              (child) =>
                child.merged_into === t.code && child.unit === roomFilter,
            )),
      )
      .sort(
        (a, b) =>
          Number(a.status === "closed") - Number(b.status === "closed") ||
          levels.indexOf(a.urgency) - levels.indexOf(b.urgency) ||
          a.created - b.created,
      );
  }
  function select(code) {
    const ticket = lastData?.facility_workflow.tickets.find(
      (t) => t.code === code,
    );
    if (ticket?.status === "closed") showClosed = true;
    selected = ticket?.merged_into || code;
    roomFilter = "";
  }
  function navigate(direction) {
    if (!lastData) return;
    const list = rows(lastData),
      index = list.findIndex((t) => t.code === selected);
    if (list[index + direction]) selected = list[index + direction].code;
  }
  function map(data, current, disabled) {
    const workflow = data.facility_workflow,
      all = workflow.tickets;
    const related = new Set(
      current?.related.map(
        (link) => all.find((t) => t.code === link.code)?.unit,
      ) || [],
    );
    const floors = [...new Set(workflow.rooms.map((room) => room.floor))].sort(
      (a, b) => b - a,
    );
    return `<section class="panel room-map" aria-labelledby="room-map-title"><div class="panel-heading"><div><h2 id="room-map-title">Resident rooms & shared systems</h2><p>Select a room to filter incidents. Shared-system links are hints for staff review.</p></div><span class="tag">${workflow.rooms.length} rooms</span></div>
      <div class="map-legend"><span class="urgent-tag tag">Urgent care / incident</span><span class="tag">Everyday care / routine repair</span><span class="tag shared-tag">Related room</span></div>
      ${floors
        .map(
          (floor) =>
            `<div class="room-floor"><h3>Floor ${floor}</h3><div class="room-grid">${workflow.rooms
              .filter((room) => room.floor === floor)
              .map((room) => {
                const residents = data.residents.filter(
                  (r) => r.room === room.unit,
                );
                const needs = data.requests.filter(
                  (r) =>
                    residents.some((p) => p.id === r.resident_id) &&
                    r.status !== "resolved",
                );
                const issues = all.filter(
                  (t) =>
                    t.unit === room.unit && parent(t, all).status !== "closed",
                );
                const urgent =
                  needs.some((r) => r.urgency === "urgent") ||
                  issues.some((t) => parent(t, all).urgency !== "routine");
                return `<div class="map-room-wrap"><button class="map-room ${urgent ? "has-urgent" : ""} ${related.has(room.unit) ? "related-room" : ""} ${roomFilter === room.unit ? "room-selected" : ""}" data-room-filter="${esc(room.unit)}" aria-pressed="${roomFilter === room.unit}"><strong>Room ${esc(room.unit)}</strong><span>${residents.map((r) => esc(r.name)).join(", ") || "Unoccupied"}</span><small>${needs.length} care ${needs.length === 1 ? "need" : "needs"} · ${issues.length} ${issues.length === 1 ? "incident" : "incidents"}</small><span class="map-priority">${urgent ? "Urgent review" : needs.length || issues.length ? "Everyday follow-up" : "No open needs"}${related.has(room.unit) ? " · Related room" : ""}</span></button><div class="room-systems"><span>Riser ${esc(room.stack)} · HVAC ${esc(room.hvac_zone)}</span>${isCoordinator(data) ? `<button class="edit-room" data-edit-room="${esc(room.unit)}" ${disabled}>Edit room ${esc(room.unit)}</button>` : ""}</div></div>`;
              })
              .join("")}</div></div>`,
        )
        .join("")}</section>`;
  }
  function detail(ticket, data, disabled) {
    const workflow = data.facility_workflow,
      all = workflow.tickets;
    const children = all.filter((t) => t.merged_into === ticket.code);
    const linked = [ticket, ...children].flatMap((t) => t.care_requests);
    const originalReports = [ticket, ...children].flatMap((origin) =>
      origin.reporters.map((reporter) => ({ origin, reporter })),
    );
    const owner = workflow.staff.find((s) => s.id === ticket.assignee);
    const coordinator = isCoordinator(data),
      actionsDisabled = disabled || (!coordinator ? "disabled" : "");
    const action = (name, label, extra = "") =>
      `<button class="secondary" data-facility-action="${name}" data-code="${esc(ticket.code)}" ${extra} ${["note", "notified"].includes(name) ? disabled : actionsDisabled}>${label}</button>`;
    return `<div class="detail-heading"><span class="eyebrow">SHARED ROOM INCIDENT</span><span class="code">${esc(ticket.code)}</span></div><div class="detail-body facility-detail"><h2>${esc(ticket.summary)}</h2><p class="detail-location">${ticket.unit_verified ? "Room" : "Reported location"} ${esc(ticket.unit)} · ${esc(workflow.categories[ticket.category])}${ticket.unit_verified ? "" : " · Confirm location before grouping"}</p><div class="clinical-note ${ticket.urgency !== "routine" ? "danger" : ""}">${icon("alert", 18)}<div><strong>${esc(ticket.urgency.charAt(0).toUpperCase() + ticket.urgency.slice(1))} room issue</strong><p>${esc(ticket.urgency_reason)}. Staff decide the response.</p></div></div>
      <dl class="metadata"><div><dt>Repair status</dt><dd>${statuses[ticket.status]}</dd></div><div><dt>Assigned to</dt><dd>${owner ? esc(owner.name) : "Not assigned"}</dd></div><div><dt>Entry permission</dt><dd>${ticket.access_ok === false ? "Do not enter; arrange access" : ticket.access_ok === true ? "Permission recorded; knock first" : "Confirm with each resident"}</dd></div><div><dt>Resident update</dt><dd>${ticket.tenant_notified_at ? "Recorded by staff at " + clock(ticket.tenant_notified_at) : "Not recorded"}</dd></div></dl>
      <div class="repair-actions">${ticket.status === "closed" ? action("reopen", "Reopen repair") : `${action("assign", owner ? "Change assignee" : "Assign facilities / vendor")}${["assigned", "waiting_tenant"].includes(ticket.status) ? action("start", ticket.status === "waiting_tenant" ? "Resume repair" : "Start repair") : ""}${ticket.status === "in_progress" ? action("resolve", "Record repair outcome") + action("waiting", "Arrange room access") : ""}${action("notified", "Record resident update")}${action("merge", "Link into shared incident")}`}${action("note", "Add facilities note")}</div>${!coordinator ? '<p class="action-hint">The care lead or facilities team coordinates repairs and vendors.</p>' : ""}
      <section class="linked-care"><h3>Resident follow-up stays separate</h3><p>Closing a repair does not close anyone's care request.</p>${linked.map((item) => `<button class="related-care-link" data-open-care="${esc(item.id)}"><strong>${esc(item.name)}</strong><span>${esc(item.code)} · ${esc(item.status.replaceAll("_", " "))} ${icon("arrow", 13)}</span></button>`).join("")}</section>
      <section class="facility-reporters"><h3>Original reports (${originalReports.length})</h3>${originalReports
        .map(({ origin, reporter }) => {
          const item = origin.care_requests.find(
            (r) => "care:" + r.id === reporter.call_id,
          );
          const call = data.calls.find((c) => c.call_id === item?.call_id);
          return `<div class="facility-report"><strong>${esc(item?.name || "Reporter")} · ${esc(reporter.language)}</strong>${origin.code !== ticket.code ? `<p class="muted">From merged incident ${esc(origin.code)} · ${esc(origin.unit)}</p>` : ""}<blockquote>“${esc(reporter.quote || "No direct quote recorded")}”</blockquote>${call ? `<details class="call-context"><summary>Call summary & transcript</summary><p class="muted">${esc(call.source)}</p><p>${esc(call.summary || "Summary pending")}</p><pre>${esc(call.transcript || "Transcript not yet available")}</pre></details>` : ""}${!origin.merged_into && origin.reporters.length > 1 ? action("split", "Separate this report", `data-reporter="${esc(reporter.call_id)}"`) : ""}</div>`;
        })
        .join("")}</section>
      <section class="facility-related"><h3>Related incidents (${ticket.related.length})</h3>${ticket.related.length ? ticket.related.map((link) => `<button class="related-incident" data-facility-code="${esc(link.code)}"><strong>${esc(link.code)}</strong><span>${esc(link.reason)}</span></button>`).join("") : '<p class="muted">No related room incidents in the last seven days.</p>'}${children.length ? `<h3>Merged incidents (${children.length})</h3>${children.map((child) => `<div class="merged-incident"><p>${esc(child.code)} · Room ${esc(child.unit)} · ${esc(child.summary)}</p><button class="secondary" data-facility-action="unmerge" data-code="${esc(child.code)}" ${actionsDisabled}>Unmerge ${esc(child.code)}</button></div>`).join("")}` : ""}</section>
      <div class="timeline"><h3>Facilities timeline</h3>${ticket.timeline.map((event) => `<div class="timeline-entry"><i></i><p>${esc(event.message)}</p><small>${esc(event.actor)} · ${clock(event.ts)}</small></div>`).join("")}</div></div>`;
  }
  function render(data, workingStaff, disabled) {
    lastData = { ...data, workingStaff };
    const workflow = data.facility_workflow,
      list = rows(data);
    const ticket = list.find((t) => t.code === selected) || list[0];
    selected = ticket?.code || null;
    const insights = workflow.insights;
    return `<section class="facility-insights" aria-label="Facilities response overview"><article><span>Open room incidents</span><strong>${workflow.tickets.filter((t) => !t.merged_into && t.status !== "closed").length}</strong><small>Resident care requests tracked separately</small></article><article><span>Median first staff action</span><strong>${duration(insights.median_first_action_s)}</strong><small>Assign, note, or update · last 30 days</small></article><article><span>Duplicate reports grouped</span><strong>${insights.duplicates_merged_week}</strong><small>Every original report is retained</small></article><article><span>Top shared problem</span><strong>${insights.top_repeats[0] ? insights.top_repeats[0].count + " linked" : "None yet"}</strong><small>${esc(insights.top_repeats[0] ? insights.top_repeats[0].problem + " · " + insights.top_repeats[0].where : "Same room, riser, floor, or HVAC zone")}</small></article></section>
      ${map(lastData, ticket, disabled)}<div class="workspace-grid facility-grid"><section class="panel incident-queue" aria-labelledby="incident-queue-title"><div class="panel-heading"><div><h2 id="incident-queue-title">Room incident queue <span class="count">${list.length}</span></h2><p>Urgency first, then oldest. J / K to navigate.</p></div><button class="secondary small" data-facility-toggle-closed>${showClosed ? "Hide" : "Show"} closed</button></div>${roomFilter ? `<div class="room-filter">Room ${esc(roomFilter)} <button data-room-filter="${esc(roomFilter)}" aria-label="Clear room filter">${icon("close", 14)}</button></div>` : ""}<div class="request-list">${list.length ? list.map((t) => `<button class="request-card ${t.code === selected ? "selected" : ""} ${t.urgency !== "routine" ? "urgent-card" : ""}" data-facility-code="${esc(t.code)}" aria-pressed="${t.code === selected}"><span class="request-icon ${t.urgency !== "routine" ? "rose" : "sand"}">${icon("grid")}</span><span class="card-content"><span class="card-top"><strong>${esc(t.summary)}</strong><span class="age ${Date.now() / 1000 - t.created > t.target_s && t.status !== "closed" ? "urgent-text" : ""}">${age(t.created)}</span></span><span class="resident-line">${t.unit_verified ? "Room" : "Location"} ${esc(t.unit)} · ${esc(t.code)} · ${t.reporters.length} ${t.reporters.length === 1 ? "report" : "reports"}</span><span class="card-bottom"><span class="tag ${t.urgency !== "routine" ? "urgent-tag" : ""}">${esc(t.urgency)}</span><span class="tag">${statuses[t.status]}</span>${t.related.length ? `<span class="tag shared-tag">${t.related.length} related</span>` : ""}</span><span class="incident-target">Demo review target: ${duration(t.target_s)}${Date.now() / 1000 - t.created > t.target_s && t.status !== "closed" ? " · Past target" : ""}</span></span></button>`).join("") : `<div class="empty">${icon("grid", 35)}<h3>${roomFilter ? "No incidents for this room" : "No room incidents yet"}</h3><p>Room and maintenance requests create shared facilities tickets automatically.</p></div>`}</div></section><aside class="panel" aria-label="Room incident details">${ticket ? detail(ticket, lastData, disabled) : '<div class="detail-placeholder"><h3>One repair. Every resident considered.</h3><p>Select an incident to coordinate the work and review linked resident needs.</p></div>'}</aside></div>`;
  }
  function dialog(action, code, data, reporterId) {
    if (action === "edit-room") {
      const room = data.facility_workflow.rooms.find((r) => r.unit === code);
      return {
        title: `Edit room ${room.unit}`,
        description:
          "Update room records and shared-system links. Resident and incident links follow a renamed room.",
        submit: "Save room",
        room,
        fields: `<label>Room number<input name="rename_to" required pattern="[A-Za-z0-9-]+" maxlength="20" value="${esc(room.unit)}"></label><label>Floor<input name="floor" type="number" min="0" max="30" required value="${room.floor}"></label><label>Shared riser<input name="stack" maxlength="20" value="${esc(room.stack)}"></label><label>HVAC zone<input name="hvac_zone" maxlength="40" value="${esc(room.hvac_zone)}"></label>`,
      };
    }
    const ticket = data.facility_workflow.tickets.find((t) => t.code === code);
    const titles = {
      assign: "Assign facilities or a vendor",
      resolve: "Record the repair outcome",
      reopen: "Reopen the repair",
      note: "Add a facilities handoff note",
      waiting: "Arrange room access",
      merge: "Link into a shared incident",
      unmerge: "Unmerge the incident",
      split: "Separate this report",
    };
    let fields = "";
    if (action === "assign")
      fields = `<label>Assigned team member or vendor<select name="assignee" required><option value="" disabled selected>Choose a team member or vendor</option>${data.facility_workflow.staff.map((s) => `<option value="${esc(s.id)}">${esc(s.name)} · ${esc(s.role)}</option>`).join("")}</select></label>`;
    if (action === "merge")
      fields = `<label>Shared incident<select name="target_code" required><option value="" disabled selected>Choose an open incident of the same kind</option>${data.facility_workflow.tickets
        .filter(
          (t) =>
            t.code !== code &&
            !t.merged_into &&
            t.status !== "closed" &&
            t.category === ticket.category,
        )
        .map(
          (t) =>
            `<option value="${esc(t.code)}">${esc(t.code)} · Room ${esc(t.unit)} · ${esc(t.summary)}</option>`,
        )
        .join("")}</select></label>`;
    fields += `<label>${action === "resolve" ? "Repair outcome" : "Facilities note"}<textarea name="note" ${action === "assign" ? "" : "required"} maxlength="1200" rows="4" placeholder="Record what staff observed or agreed."></textarea></label>`;
    return {
      title: titles[action],
      description:
        action === "resolve"
          ? "Record the completed work. Individual resident care requests remain open for their own follow-up."
          : "This updates the room incident and its timeline. No call, page, or vendor message is sent.",
      fields,
      submit:
        {
          assign: "Save assignment",
          resolve: "Close repair",
          merge: "Link incidents",
          split: "Separate report",
          unmerge: "Unmerge incident",
        }[action] || "Save update",
      ticket,
      reporterId,
      targetVersions: Object.fromEntries(
        data.facility_workflow.tickets.map((t) => [t.code, t.version]),
      ),
    };
  }
  return {
    render,
    dialog,
    select,
    navigate,
    selected: () => selected,
    filter: (room) => {
      roomFilter = roomFilter === room ? "" : room;
      selected = null;
    },
    toggleClosed: () => {
      showClosed = !showClosed;
    },
  };
}
