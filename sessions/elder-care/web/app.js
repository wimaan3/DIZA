import { createFacilityWorkspace } from "./facility.js";

const app = document.querySelector("#app");
const dialogRoot = document.querySelector("#dialog-root");
const announce = document.querySelector("#announcer");
let data,
  selected,
  view = "daily",
  statusFilter = "open",
  search = "",
  staffId = sessionStorage.getItem("diza-care-staff") || "nurse-jordan";
let busy = false,
  error = "",
  connected = false,
  lastSuccess = 0,
  modal = null;
let token = sessionStorage.getItem("diza-care-token") || "";
let retrySubmission = null;
const labels = {
  new: "Awaiting staff",
  accepted: "Accepted",
  in_progress: "In progress",
  resolved: "Resolved",
};
const roleNames = {
  nurse: "Nurse",
  caregiver: "Caregiver",
  care_lead: "Care lead",
  facilities: "Facilities",
};
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const icon = (name, size = 20) => {
  const paths = {
    heart:
      '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/>',
    grid: '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
    alert:
      '<path d="m10.3 3.9-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3.1l-8-14a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4m0 4h.01"/>',
    users:
      '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m20 0v-2a4 4 0 0 0-3-3.9"/><circle cx="9" cy="7" r="4"/><path d="M16 3.1a4 4 0 0 1 0 7.8"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    arrow: '<path d="M7 17 17 7M7 7h10v10"/>',
    leaf: '<path d="M20 4C10 2 2 6 4 14c1 5 10 8 14 1 2-4 1-7 2-11Z"/><path d="m5 19 9-10"/>',
    close: '<path d="m6 6 12 12M6 18 18 6"/>',
    note: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M8 13h8M8 17h5"/>',
    mug: '<path d="M3 8h13v8a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4ZM16 8h2a3 3 0 0 1 0 6h-2M6 2v3M11 2v3"/>',
    shield:
      '<path d="m12 3 8 4v5c0 5-8 9-8 9s-8-4-8-9V7Z"/><path d="m8 12 3 3 5-6"/>',
  };
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.heart}</svg>`;
};
const personFor = (id) => data.residents.find((r) => r.id === id);
const staffFor = (id) => data.staff.find((s) => s.id === id);
const active = () => data.requests.filter((r) => r.status !== "resolved");
const age = (timestamp) => {
  const minutes = Math.max(0, Math.floor((Date.now() / 1000 - timestamp) / 60));
  return minutes < 1
    ? "Just now"
    : minutes < 60
      ? `${minutes} min`
      : minutes < 1440
        ? `${Math.floor(minutes / 60)} hr ${minutes % 60} min`
        : `${Math.floor(minutes / 1440)} days`;
};
const clock = (ts) =>
  new Date(ts * 1000).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
    timeZone: data.timezone,
  });
const categoryIcon = (r) =>
  r.urgency === "urgent"
    ? "alert"
    : {
        meal: "mug",
        companionship: "heart",
        maintenance: "grid",
        medication: "shield",
        wellbeing: "users",
      }[r.category] || "heart";

const facilityWorkspace = createFacilityWorkspace({ esc, icon, age, clock });

async function api(path, body) {
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    if (response.status === 401) throw new Error("Staff access token required");
    throw new Error(
      typeof payload.detail === "string"
        ? payload.detail
        : "Please check the details and try again.",
    );
  }
  return response.json();
}

async function refresh(render = true) {
  try {
    data = await api("/api/care/state");
    connected = true;
    lastSuccess = Date.now();
    if (!staffFor(staffId)) staffId = data.staff[0]?.id || "";
    if (
      error.startsWith("Connection") ||
      error === "Staff access token required"
    )
      error = "";
  } catch (e) {
    connected = false;
    error =
      e.message === "Staff access token required"
        ? e.message
        : "Connection lost. Requests may be out of date. Reconnect before acting.";
    if (e.message === "Staff access token required") data = undefined;
  }
  if (render) draw();
}

async function mutate(path, body, success) {
  if (busy || !connected) return false;
  busy = true;
  error = "";
  draw();
  try {
    await api(path, body);
    await refresh(false);
    announce.textContent = success;
    return true;
  } catch (e) {
    error = e.message;
    announce.textContent = error;
    return false;
  } finally {
    busy = false;
    draw();
  }
}

function draw() {
  const focus = document.activeElement;
  const focusId = focus?.id;
  const cursor = focus?.selectionStart;
  const focusKey = [
    "action",
    "view",
    "request",
    "checkin",
    "facilityCode",
    "roomFilter",
    "editRoom",
    "facilityAction",
  ].find((key) => focus?.dataset?.[key]);
  const focusValue = focusKey ? focus.dataset[focusKey] : null;
  if (!data) {
    app.innerHTML = `<main class="boot"><span class="brand large">${icon("heart", 30)} DIZA<span>care</span></span><h1>${error ? "Connect to your care workspace" : "Opening your care workspace"}</h1><p>${esc(error || "Loading the care queue...")}</p>${error === "Staff access token required" ? tokenForm() : '<button class="primary" data-action="refresh">Try again</button>'}</main>`;
    return;
  }
  const urgent = active().filter((r) => r.urgency === "urgent");
  const daily = active().filter((r) => r.urgency === "routine");
  const unresolvedCheckins = data.residents.filter(
    (r) => r.checkin?.outcome !== "seen_well",
  );
  const due = data.residents.filter((r) => r.checkin_due);
  const title = {
    daily: "Care, in good hands.",
    urgent: "Every urgent need, seen.",
    residents: "A little attention. Every day.",
    history: "Every handoff has a story.",
    facility: "One home. A coordinated response.",
  }[view];
  app.innerHTML = `<div class="layout">
    <aside class="sidebar"><a class="brand" href="/care" aria-label="DIZA Care home"><span class="brand-icon">${icon("heart", 23)}</span>DIZA<span>care</span></a>
      <div class="facility"><span class="facility-mark">WH</span><div><strong>${esc(data.facility)}</strong><small>Residential care home</small></div></div>
      <div class="nav-label">CARE WORKSPACE</div><nav aria-label="Care workspace">
        ${nav("daily", "grid", "Daily care", daily.length)}${nav("urgent", "alert", "Urgent response", urgent.length)}${nav("residents", "users", "Residents & check-ins")}${nav("facility", "grid", "Rooms & repairs")}${nav("history", "clock", "Completed care")}
      </nav>
      <div class="sidebar-message">${icon("leaf", 29)}<strong>Small moments.<br>Thoughtful care.</strong><p>One team, looking after<br>every resident.</p></div>
      ${data.legacy_available ? `<a class="legacy-link" href="/ops">Original operations ${icon("arrow", 15)}</a>` : ""}
      <div class="sidebar-foot"><span class="avatar">${initials(staffFor(staffId)?.name || "")}</span><div><label for="staff-select">Working as</label><select id="staff-select" aria-label="Working as staff member">${data.staff.map((s) => `<option value="${esc(s.id)}" ${s.id === staffId ? "selected" : ""}>${esc(s.name)} · ${roleNames[s.role]}</option>`).join("")}</select></div></div>
    </aside>
    <div class="main-wrap"><header class="topbar"><span>Care workspace <span class="slash">/</span> ${view === "facility" ? "Rooms & repairs" : view === "residents" ? "Residents" : view === "history" ? "Completed care" : view === "urgent" ? "Urgent response" : "Daily overview"}</span><div><span class="connection ${connected ? "" : "offline"}"><i></i>${connected ? "Queue connected" : "Connection lost"}</span><span class="date">${new Intl.DateTimeFormat("en", { month: "short", day: "numeric", timeZone: data.timezone }).format(new Date())}</span></div></header>
    <main id="main" tabindex="-1"><div class="page-heading"><div><div class="eyebrow">${esc(data.facility.toUpperCase())} / CARE TEAM</div><h1>${title}</h1><p class="subtitle">${view === "facility" ? "Coordinate shared room issues and follow through on every resident’s care." : view === "urgent" ? "Prioritize urgent needs. Confirm who is taking responsibility." : view === "residents" ? "Keep wellbeing checks personal, visible, and followed through." : view === "history" ? "Review completed requests and the people who followed through." : "A shared view of what matters, and who needs you next."}</p></div><button class="primary" data-action="new" ${disabled()}>${icon("plus", 17)} Record a request</button></div>
    ${error ? `<div role="alert" class="error-banner">${icon("alert")}<span>${esc(error)}</span><button data-action="refresh">Reconnect</button></div>` : ""}
    ${!connected && lastSuccess ? `<p class="stale">Last connected ${esc(new Date(lastSuccess).toLocaleTimeString())}. Actions are paused.</p>` : ""}
    <div class="demo-note">${icon("shield", 16)} <span>${data.demo ? "Demo workspace · fictional residents and staff." : "Care coordination workspace."} Staff selection is a demo control. No calls, pages, or emergency dispatch are sent.</span>${data.demo ? `<button data-action="demo" ${disabled()}>Load demo scenarios ${icon("arrow", 14)}</button>` : ""}</div>
    ${urgent.length ? `<div class="urgent-banner"><span class="urgent-icon">${icon("alert", 22)}</span><div><strong>${urgent.length} urgent ${urgent.length === 1 ? "request needs" : "requests need"} attention</strong><p>${urgent.filter((r) => r.status === "new").length} awaiting a nurse or care lead. Follow your home's emergency procedure for immediate danger.</p></div><button data-view="urgent">Open urgent queue <span aria-hidden="true">→</span></button></div>` : ""}
    ${view !== "facility" ? `<section class="stats" aria-label="Care overview">${stat("Urgent needs", urgent.length, urgent.length ? "Nurse or care lead required" : "No open urgent requests", "alert", "rose")}${stat("Everyday requests", daily.length, `${daily.filter((r) => r.status === "new").length} awaiting staff acceptance`, "mug", "sand")}${stat("Check-ins to review", unresolvedCheckins.length, due.length ? `${due.length} not recorded after 10 am` : "Daily check-in target: 10 am", "users", "lavender")}${stat("Care in progress", active().filter((r) => r.status === "in_progress").length, "Responsibility accepted by staff", "heart", "mint")}</section>` : ""}
    ${view === "facility" ? facilityWorkspace.render(data, staffId, disabled()) : view === "residents" ? residentsView() : queueView()}
    <footer><span>${icon("heart", 14)} Designed around people. Supported by DIZA.</span><span>${data.residents.length} residents · ${esc(data.timezone.replaceAll("_", " "))}</span></footer>
    </main></div></div>`;
  if (focusId && document.getElementById(focusId)) {
    const restored = document.getElementById(focusId);
    restored.focus({ preventScroll: true });
    if (cursor != null && restored.type === "search")
      restored.setSelectionRange(cursor, cursor);
  } else if (focusKey && !modal) {
    app
      .querySelector(
        `button[data-${focusKey.replace(/([A-Z])/g, "-$1").toLowerCase()}="${CSS.escape(focusValue)}"]:not(:disabled)`,
      )
      ?.focus({ preventScroll: true });
  }
}

function initials(name) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((x) => x[0])
    .join("");
}
function disabled() {
  return busy || !connected ? "disabled" : "";
}
function tokenForm() {
  return '<form id="token-form"><label>Staff access token<input name="token" type="password" required autocomplete="off"></label><button class="primary">Connect</button></form>';
}
function nav(id, ico, label, count) {
  return `<button data-view="${id}" class="nav-item ${view === id ? "active" : ""} ${id === "urgent" ? "urgent-nav" : ""}" ${view === id ? 'aria-current="page"' : ""}>${icon(ico, 19)}<span>${label}</span>${count ? `<b>${count}</b>` : ""}</button>`;
}
function stat(label, count, detail, ico, color) {
  return `<article class="stat"><div><span>${label}</span><span class="stat-icon ${color}">${icon(ico, 19)}</span></div><strong>${String(count).padStart(2, "0")}</strong><small>${detail}</small></article>`;
}

function filtered() {
  return data.requests.filter((r) => {
    const person = personFor(r.resident_id);
    const mode =
      view === "history"
        ? r.status === "resolved"
        : r.status !== "resolved" &&
          r.urgency === (view === "urgent" ? "urgent" : "routine");
    return (
      mode &&
      (statusFilter === "open" || r.status === statusFilter) &&
      `${person.name} ${person.room} ${r.summary} ${r.code}`
        .toLowerCase()
        .includes(search.toLowerCase())
    );
  });
}

function queueView() {
  const rows = filtered();
  let item = rows.find((r) => r.id === selected) || rows[0];
  selected = item?.id || null;
  const awaiting = rows.filter((r) => r.status === "new").length;
  return `<div class="workspace-grid"><section class="queue-panel panel" aria-labelledby="queue-title"><div class="panel-heading"><div><h2 id="queue-title">${view === "history" ? "Completed requests" : view === "urgent" ? "Urgent care queue" : "Everyday care queue"} <span class="count">${rows.length}</span></h2><p>${view === "urgent" ? "Urgent requests remain here until resolved by staff." : view === "history" ? "Recorded outcomes and handoff history." : `${awaiting} waiting for a helping hand`}</p></div><span class="subtle-label">${view === "urgent" ? "URGENT FIRST" : "OLDEST FIRST"}</span></div>
    <div class="queue-tools"><label class="search">${icon("search", 17)}<input id="queue-search" type="search" placeholder="Search resident, room, or request" aria-label="Search care requests" value="${esc(search)}"></label>${view !== "history" ? `<select id="status-filter" aria-label="Filter by request status"><option value="open" ${statusFilter === "open" ? "selected" : ""}>All open</option>${["new", "accepted", "in_progress"].map((s) => `<option value="${s}" ${statusFilter === s ? "selected" : ""}>${labels[s]}</option>`).join("")}</select>` : ""}</div>
    <div class="request-list">${rows.length ? rows.map((r) => requestCard(r, r.id === selected)).join("") : `<div class="empty">${icon(view === "urgent" ? "shield" : "mug", 35)}<h3>${search || statusFilter !== "open" ? "No matching requests" : view === "urgent" ? "No open urgent needs" : view === "history" ? "Care history starts here" : "A little breathing room."}</h3><p>${search || statusFilter !== "open" ? "Try another search or status filter." : view === "urgent" ? "New urgent reports will appear here for nurse review." : view === "history" ? "Resolved requests will appear with their recorded outcome." : "Record a request when a resident needs a hand, or load the fictional demo scenarios."}</p>${!search && view === "daily" ? `<button class="secondary" data-action="new" ${disabled()}>${icon("plus", 16)} Record a request</button>` : ""}</div>`}</div></section>
    <aside class="detail-panel panel" aria-label="Selected request">${item ? detail(item) : `<div class="detail-placeholder">${icon("note", 38)}<h3>The person behind the request.</h3><p>Select a request to see resident preferences, take responsibility, and keep the next shift informed.</p></div>`}</aside></div>
    ${view === "daily" ? `<section class="checkin-strip"><div class="strip-icon">${icon("users", 25)}</div><div><h2>A moment to check in.</h2><p>${data.residents.filter((r) => r.checkin?.outcome === "seen_well").length} of ${data.residents.length} residents recorded as seen well today. Follow-ups stay visible in the queue.</p></div><button class="secondary" data-view="residents">View residents <span aria-hidden="true">→</span></button></section>` : ""}`;
}

function requestCard(r, chosen) {
  const person = personFor(r.resident_id);
  const owner = staffFor(r.assignee);
  const waiting = r.urgency === "urgent" && r.status === "new";
  return `<button class="request-card ${chosen ? "selected" : ""} ${r.urgency === "urgent" ? "urgent-card" : ""}" data-request="${esc(r.id)}" aria-pressed="${chosen}"><div class="request-icon ${r.urgency === "urgent" ? "rose" : "sand"}">${icon(categoryIcon(r), 21)}</div><div class="card-content"><div class="card-top"><strong>${esc(r.summary)}</strong><span class="age ${waiting ? "urgent-text" : ""}">${icon("clock", 12)} ${age(r.created)}</span></div><div class="resident-line">${esc(person.name)} <span>·</span> Room ${esc(person.room)} <span>·</span> ${esc(person.wing)} wing</div><div class="card-bottom"><span class="tag ${r.urgency === "urgent" ? "urgent-tag" : ""}">${r.urgency === "urgent" ? "Urgent" : esc(data.categories[r.category])}</span><span class="status ${r.status}"><i></i>${labels[r.status]}</span>${owner ? `<span class="owner">${esc(owner.name)}</span>` : ""}</div></div></button>`;
}

function detail(r) {
  const person = personFor(r.resident_id);
  const owner = staffFor(r.assignee);
  const events = data.events.filter((e) => e.request_id === r.id).slice(0, 12);
  const staff = staffFor(staffId);
  const clinical = r.urgency === "urgent" || r.category === "medication";
  const eligible = clinical
    ? ["nurse", "care_lead"].includes(staff.role)
    : staff.role !== "facilities" || r.category === "maintenance";
  return `<div class="detail-heading"><span class="eyebrow">REQUEST DETAILS</span><span class="code">${esc(r.code)}</span></div><div class="person-block"><span class="person-avatar">${initials(person.name)}</span><h2>${esc(person.name)}</h2><p>Room ${esc(person.room)} · ${esc(person.wing)} wing</p><span class="tag">${esc(person.language)} preferred</span></div>
    <div class="detail-body"><div class="preference">${icon("heart", 17)}<p>${esc(person.preferences)}</p></div><h3>${esc(r.summary)}</h3><p class="detail-location">Reported location: ${esc(r.location)}</p>${r.quote ? `<blockquote><span>RESIDENT / REPORTER'S WORDS</span>“${esc(r.quote)}”</blockquote>` : '<p class="muted">No direct quote recorded.</p>'}
    ${clinical ? `<div class="clinical-note ${r.urgency === "urgent" ? "danger" : ""}">${icon("shield", 17)}<div><strong>${r.urgency === "urgent" ? "Urgent human review" : "Nurse review required"}</strong><p>${esc(r.reason)}${r.urgency === "urgent" ? ". Follow the home’s emergency procedure for immediate danger. No emergency services have been contacted by DIZA." : ". Medication decisions stay with qualified staff."}</p></div></div>` : ""}
    ${r.facility_code ? `<div class="care-incident-link"><strong>Shared room incident</strong><button class="secondary full" data-facility-code="${esc(r.facility_code)}">Open ${esc(r.facility_code)} ${icon("arrow", 14)}</button><p>Repair coordination and resident care each keep their own outcome.</p></div>` : ""}${careCallContext(r)}
    <dl class="metadata"><div><dt>Recorded by</dt><dd>${esc(r.reported_by)}</dd></div><div><dt>Responsible</dt><dd>${owner ? esc(owner.name) : "Not yet accepted"}</dd></div><div><dt>Received</dt><dd>${clock(r.created)} · ${r.source === "voice" ? "Voice intake" : "Staff entry"}</dd></div></dl>
    ${r.status !== "resolved" ? `<div class="request-actions">${r.status === "new" ? `<button class="primary full" data-action="accept" ${disabled()} ${!eligible ? "disabled" : ""}>${icon("check", 17)} Accept responsibility</button>${!eligible ? `<p class="action-hint">${clinical ? "A nurse or care lead must accept this request." : "This request requires a care team member."}</p>` : ""}` : r.assignee === staffId ? `<button class="primary full" data-action="${r.status === "accepted" ? "start" : "resolve"}" ${disabled()}>${icon(r.status === "accepted" ? "heart" : "check", 17)} ${r.status === "accepted" ? "Start care" : "Record outcome & resolve"}</button>` : `<p class="action-hint">${esc(owner?.name)} has accepted responsibility.</p>`}<div class="secondary-actions"><button class="secondary" data-action="note" ${disabled()}>${icon("note", 15)} Add note</button>${r.urgency !== "urgent" ? `<button class="text-danger" data-action="escalate" ${disabled()}>Mark urgent</button>` : ""}</div></div>` : `<div class="resolved-note">${icon("check", 17)} Resolved by staff. Outcome recorded below.</div>`}
    <div class="timeline"><h3>Handoff history</h3>${events.map((e) => `<div class="timeline-entry"><i></i><p>${esc(e.message)}</p><small>${esc(e.actor)} · ${clock(e.created)}</small></div>`).join("")}</div></div>`;
}

function careCallContext(request) {
  const call = data.calls.find((c) => c.call_id === request.call_id);
  return call
    ? `<details class="call-context"><summary>Call summary & transcript</summary><p class="muted">${esc(call.source)}</p><p>${esc(call.summary || "Summary pending")}</p><pre>${esc(call.transcript || "Transcript not yet available")}</pre></details>`
    : "";
}

function residentsView() {
  return `<section class="panel residents-panel"><div class="panel-heading"><div><h2>Today's wellbeing check-ins</h2><p>Record what staff observed. A concern creates a follow-up request automatically.</p></div><span class="tag">${esc(data.today)}</span></div><div class="residents-grid">${data.residents
    .map((r) => {
      const outcome = r.checkin?.outcome;
      const title =
        {
          seen_well: "Seen well today",
          follow_up: "Follow-up requested",
          no_response: "No response recorded",
        }[outcome] ||
        (r.checkin_due ? "Check-in overdue" : "Not yet checked in");
      return `<article class="resident-card"><div class="resident-card-heading"><span class="avatar">${initials(r.name)}</span><span class="tag">Room ${esc(r.room)}</span></div><h3>${esc(r.name)}</h3><p>${esc(r.wing)} wing · ${esc(r.language)}</p><p class="resident-pref">${esc(r.preferences)}</p><span class="checkin-status ${outcome === "seen_well" ? "well" : outcome || r.checkin_due ? "review" : ""}">${icon(outcome === "seen_well" ? "check" : "clock", 15)} ${title}</span>${r.checkin?.note ? `<p class="checkin-observation">${esc(r.checkin.note)}</p>` : ""}<button class="secondary full" data-checkin="${esc(r.id)}" ${disabled()} ${staffFor(staffId)?.role === "facilities" ? "disabled" : ""}>${outcome ? "Update check-in" : "Record check-in"}</button></article>`;
    })
    .join("")}</div></section>`;
}

let returnFocus;
function openDialog(type, residentId, reporterId) {
  if (modal) return;
  returnFocus = document.activeElement;
  modal = { type, residentId };
  retrySubmission = null;
  const request = data.requests.find((r) => r.id === selected);
  if (request) modal.request = { ...request };
  let title, description, fields, submit;
  if (type === "new") {
    title = "Record a care request";
    description =
      "Capture the need in their own words. Urgent requests go straight to nurse review.";
    fields = `<label>Resident<select name="resident_id" required><option value="" selected disabled>Select a resident and room</option>${data.residents.map((r) => `<option value="${esc(r.id)}">${esc(r.name)} · Room ${esc(r.room)}</option>`).join("")}</select></label><div class="form-row"><label>Type of request<select name="category">${Object.entries(
      data.categories,
    )
      .map(
        ([key, value]) =>
          `<option value="${key}" ${key === "personal_care" ? "selected" : ""}>${esc(value)}</option>`,
      )
      .join(
        "",
      )}</select></label><label>Priority<select name="urgency"><option value="routine">Everyday care</option><option value="urgent">Urgent - needs a nurse now</option></select></label></div><fieldset id="facility-fields" hidden disabled><legend>Room incident details</legend><label>Room issue type<select name="facility_category">${Object.entries(
      data.facility_workflow.categories,
    )
      .map(
        ([key, label]) =>
          `<option value="${key}" ${key === "other" ? "selected" : ""}>${esc(label)}</option>`,
      )
      .join(
        "",
      )}</select></label><label>Permission to enter<select name="access_ok"><option value="">Not yet confirmed</option><option value="yes">Resident gave permission; knock first</option><option value="no">Do not enter; arrange access</option></select></label></fieldset><label>What is needed?<input name="summary" required minlength="3" maxlength="1200" placeholder="For example, help getting ready for lunch"></label><label>Resident or reporter's exact words<textarea name="quote" maxlength="2000" rows="3" placeholder="Keep the original words, especially any urgent concerns."></textarea></label><label>Location, if away from their room<input name="location" maxlength="200" placeholder="Defaults to the resident's room and wing"></label>`;
    submit = "Record request";
  } else if (type.startsWith("facility-")) {
    const config = facilityWorkspace.dialog(
      type.slice(9),
      residentId,
      data,
      reporterId,
    );
    modal.facility = config;
    ({ title, description, fields, submit } = config);
  } else if (type === "checkin") {
    title = `Check in with ${personFor(residentId).name.split(" ")[0]}`;
    description =
      "Record a direct staff observation. Follow-up and no response create a care request.";
    fields =
      '<label>Check-in outcome<select name="outcome"><option value="seen_well">Seen well by staff</option><option value="follow_up">Needs follow-up</option><option value="no_response">No response - needs staff review</option></select></label><label>Observation<textarea name="note" maxlength="1200" rows="4" placeholder="Record what you observed. Add details for follow-up or no response."></textarea></label>';
    submit = "Save check-in";
  } else {
    title = {
      note: "Add a handoff note",
      escalate: "Escalate to urgent",
      resolve: "Record the care outcome",
    }[type];
    description = {
      note: "Keep the next person informed with a clear observation.",
      escalate:
        "This stays urgent until a nurse or care lead resolves it. Add the reason for escalation.",
      resolve:
        "Confirm what was done and how the resident was left. The request will move to completed care.",
    }[type];
    fields = `<label>${type === "resolve" ? "Outcome and follow-up" : type === "escalate" ? "Reason for urgency" : "Handoff note"}<textarea name="note" required maxlength="1200" rows="4"></textarea></label>`;
    submit = {
      note: "Save note",
      escalate: "Mark urgent",
      resolve: "Resolve request",
    }[type];
  }
  dialogRoot.innerHTML = `<dialog aria-labelledby="dialog-title" aria-describedby="dialog-description"><form id="care-form"><div class="modal-heading"><span class="eyebrow">DIZA CARE / STAFF ENTRY</span><button type="button" class="icon-button" data-action="close" aria-label="Close dialog">${icon("close")}</button></div><h2 id="dialog-title">${esc(title)}</h2><p id="dialog-description">${esc(description)}</p><div class="modal-error" role="alert" hidden></div>${fields}<div class="modal-footer"><button type="button" class="secondary" data-action="close">Cancel</button><button class="primary" type="submit">${submit}</button></div></form></dialog>`;
  const dialog = dialogRoot.querySelector("dialog");
  dialog.showModal();
  dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    if (!busy) closeDialog();
  });
}

function closeDialog() {
  dialogRoot.querySelector("dialog")?.close();
  dialogRoot.innerHTML = "";
  modal = null;
  retrySubmission = null;
  if (returnFocus?.isConnected) returnFocus.focus();
  else document.querySelector('[data-action="new"]')?.focus();
}

async function submitDialog(form) {
  if (busy || !connected) return;
  const fields = Object.fromEntries(new FormData(form));
  const type = modal.type;
  let path, body;
  if (type === "new") {
    path = "/api/care/requests";
    if ("access_ok" in fields)
      fields.access_ok =
        fields.access_ok === "" ? null : fields.access_ok === "yes";
    body = { ...fields, reported_by: staffFor(staffId).name, source: "staff" };
  } else if (type === "facility-edit-room") {
    path = "/api/care/facility/rooms";
    body = {
      ...fields,
      floor: Number(fields.floor),
      room: modal.facility.room.unit,
      version: modal.facility.room.version,
      staff_id: staffId,
    };
  } else if (type.startsWith("facility-")) {
    path = `/api/care/facility/tickets/${modal.facility.ticket.code}/actions`;
    body = {
      ...fields,
      action: type.slice(9),
      staff_id: staffId,
      version: modal.facility.ticket.version,
    };
    if (body.action === "merge")
      body.target_version = modal.facility.targetVersions[body.target_code];
    if (body.action === "split") body.reporter_id = modal.facility.reporterId;
  } else if (type === "checkin") {
    path = `/api/care/residents/${modal.residentId}/checkins`;
    body = { ...fields, staff_id: staffId };
  } else {
    path = `/api/care/requests/${modal.request.id}/actions`;
    body = {
      ...fields,
      action: type,
      staff_id: staffId,
      version: modal.request.version,
    };
  }
  if (type === "new" || type === "checkin") {
    // Reuse the key on a retry with the same content after an ambiguous network error.
    const fingerprint = JSON.stringify(body);
    if (retrySubmission?.fingerprint !== fingerprint)
      retrySubmission = { fingerprint, key: crypto.randomUUID() };
    body.idempotency_key = retrySubmission.key;
  }
  const controls = [...form.elements];
  controls.forEach((el) => {
    el.disabled = true;
  });
  const saved = await mutate(
    path,
    body,
    type === "new" ? "Care request recorded." : "Care record updated.",
  );
  if (saved) closeDialog();
  else {
    controls.forEach((el) => {
      el.disabled = false;
    });
    const message = form.querySelector(".modal-error");
    message.textContent = error;
    message.hidden = false;
  }
}

document.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button || button.disabled) return;
  if (button.dataset.view) {
    view = button.dataset.view;
    search = "";
    statusFilter = "open";
    selected = null;
    draw();
    return;
  }
  if (button.dataset.facilityCode) {
    view = "facility";
    facilityWorkspace.select(button.dataset.facilityCode);
    draw();
    return;
  }
  if (button.dataset.roomFilter) {
    facilityWorkspace.filter(button.dataset.roomFilter);
    draw();
    return;
  }
  if (button.hasAttribute("data-facility-toggle-closed")) {
    facilityWorkspace.toggleClosed();
    draw();
    return;
  }
  if (button.dataset.openCare) {
    const item = data.requests.find((r) => r.id === button.dataset.openCare);
    if (item) {
      view =
        item.status === "resolved"
          ? "history"
          : item.urgency === "urgent"
            ? "urgent"
            : "daily";
      selected = item.id;
      search = "";
      statusFilter = "open";
      draw();
    }
    return;
  }
  if (button.dataset.editRoom) {
    openDialog("facility-edit-room", button.dataset.editRoom);
    return;
  }
  if (button.dataset.facilityAction) {
    const action = button.dataset.facilityAction,
      code = button.dataset.code;
    if (["start", "notified"].includes(action)) {
      const ticket = data.facility_workflow.tickets.find(
        (t) => t.code === code,
      );
      await mutate(
        `/api/care/facility/tickets/${code}/actions`,
        { staff_id: staffId, version: ticket.version, action },
        "Room incident updated.",
      );
    } else openDialog("facility-" + action, code, button.dataset.reporter);
    return;
  }
  if (button.dataset.request) {
    selected = button.dataset.request;
    draw();
    return;
  }
  if (button.dataset.checkin) {
    openDialog("checkin", button.dataset.checkin);
    return;
  }
  const action = button.dataset.action;
  if (action === "close") {
    if (!busy) closeDialog();
    return;
  }
  if (action === "refresh") {
    await refresh();
    return;
  }
  if (action === "new") {
    openDialog("new");
    return;
  }
  if (action === "demo") {
    await mutate("/api/care/demo", {}, "Fictional demo scenarios loaded.");
    return;
  }
  if (["resolve", "note", "escalate"].includes(action)) {
    openDialog(action);
    return;
  }
  if (["accept", "start"].includes(action)) {
    const request = data.requests.find((r) => r.id === selected);
    if (request)
      await mutate(
        `/api/care/requests/${request.id}/actions`,
        { staff_id: staffId, action, version: request.version },
        action === "accept" ? "Responsibility accepted." : "Care started.",
      );
  }
});
document.addEventListener("change", (event) => {
  if (event.target.name === "category") {
    const fields = document.getElementById("facility-fields");
    if (fields)
      fields.hidden = fields.disabled = event.target.value !== "maintenance";
  }
  if (event.target.id === "staff-select") {
    staffId = event.target.value;
    sessionStorage.setItem("diza-care-staff", staffId);
    draw();
  }
  if (event.target.id === "status-filter") {
    statusFilter = event.target.value;
    selected = null;
    draw();
  }
});
document.addEventListener("input", (event) => {
  if (event.target.id === "queue-search") {
    search = event.target.value;
    selected = null;
    draw();
  }
});
document.addEventListener("submit", async (event) => {
  if (event.target.id === "care-form") {
    event.preventDefault();
    await submitDialog(event.target);
  }
  if (event.target.id === "token-form") {
    event.preventDefault();
    token = new FormData(event.target).get("token");
    sessionStorage.setItem("diza-care-token", token);
    await refresh();
  }
});
document.addEventListener("keydown", (event) => {
  if (
    view !== "facility" ||
    modal ||
    event.ctrlKey ||
    event.metaKey ||
    event.altKey ||
    event.target.closest("input,textarea,select")
  )
    return;
  if (["j", "k"].includes(event.key)) {
    event.preventDefault();
    facilityWorkspace.navigate(event.key === "j" ? 1 : -1);
    draw();
  }
});
await refresh();
// Do not rebuild the active form or move keyboard focus during background polling.
setInterval(() => {
  if (
    !busy &&
    !modal &&
    !["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement?.tagName)
  )
    refresh();
}, 4000);
