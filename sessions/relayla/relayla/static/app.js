/* DIZA / RelayLA. All content from the API is rendered as text, never HTML. */
"use strict";

(() => {
  const $ = (id) => document.getElementById(id);
  const OUTBOX_KEY = "relayla.pending-intake.v1";
  const TOKEN_KEY = "relayla.operator-token";
  const APP_BASE = new URL("./", document.baseURI);
  const app = {
    state: null, selectedId: null, filter: "all", search: "", online: false,
    lastSync: null, fetching: false, syncing: false, actionBusy: false,
    caseSignature: "", noticeLanguages: {}, editNotice: null, outbox: [],
    live: { caseId: null, status: "idle", message: "", module: null },
  };

  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined && text !== null) element.textContent = String(text);
    return element;
  }
  function button(text, className = "button", onClick) {
    const element = node("button", className, text);
    element.type = "button";
    if (onClick) element.addEventListener("click", onClick);
    return element;
  }
  function append(parent, ...children) {
    children.filter(Boolean).forEach((child) => parent.append(child));
    return parent;
  }
  function dot(color = "") { return node("span", `status-dot ${color}`); }
  function titleCase(value) { return String(value || "").replaceAll("_", " ").replace(/\b\w/g, (ch) => ch.toUpperCase()); }
  function languageLabel(value) { return value === "es" ? "Español" : "English"; }
  function eventId() {
    return globalThis.crypto?.randomUUID?.() || `web-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }
  function readToken() {
    try { return sessionStorage.getItem(TOKEN_KEY) || ""; } catch { return ""; }
  }
  function writeToken(token) {
    try {
      if (token) sessionStorage.setItem(TOKEN_KEY, token);
      else sessionStorage.removeItem(TOKEN_KEY);
    } catch { throw new Error("This browser is blocking session storage. Enable it to use an operator token."); }
  }
  function clock(value, options = {}) {
    const date = new Date(value);
    if (!value || Number.isNaN(date.getTime())) return "—";
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", ...options });
  }
  function when(value) {
    const date = new Date(value);
    if (!value || Number.isNaN(date.getTime())) return "Time unavailable";
    return date.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  }
  function age(value) {
    const seconds = Math.max(0, (Date.now() - new Date(value).getTime()) / 1000);
    if (!Number.isFinite(seconds)) return "";
    if (seconds < 60) return "Just now";
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
    return `${Math.floor(seconds / 86400)}d`;
  }
  function noticeFor(c) { return app.state?.notices?.find((n) => n.id === c?.notice_id) || null; }
  function caseById(id) { return app.state?.cases?.find((c) => c.id === id); }
  function currentCase() { return caseById(app.selectedId); }
  function needsHuman(c) {
    return ["P0", "P1"].includes(c.severity) && c.assistance_status !== "completed" ||
      ["requested", "assigned"].includes(c.assistance_status) ||
      ["human_review", "contact_review"].includes(c.callback_stage) || c.communication_status === "needs_clarification";
  }
  function openAssistance(c) { return c.assistance_status && !["none", "completed"].includes(c.assistance_status); }
  function confirmation(c) {
    const n = noticeFor(c);
    if (!n) return { label: "No notice attached", short: "No notice", color: "", detail: "A service request can proceed independently." };
    if (c.communication_status === "confirmed" && Number(c.acknowledged_version) === Number(n.version)) {
      return { label: "Current instruction confirmed", short: `Confirmed v${n.version}`, color: "teal", detail: `Confirmed v${c.acknowledged_version} · Latest v${n.version}` };
    }
    if (c.communication_status === "needs_clarification") return { label: "Read-back needs clarification", short: "Needs clarification", color: "amber", detail: `Confirmed ${c.acknowledged_version ? `v${c.acknowledged_version}` : "—"} · Latest v${n.version}` };
    if (c.communication_status === "update_pending" || c.acknowledged_version && Number(c.acknowledged_version) < Number(n.version)) {
      return { label: "Updated instruction pending", short: `Needs v${n.version} update`, color: "amber", detail: `Confirmed v${c.acknowledged_version || "—"} · Latest v${n.version}` };
    }
    if (c.communication_status === "awaiting_confirmation") return { label: "Awaiting read-back", short: "Awaiting read-back", color: "", detail: `Confirmed — · Latest v${n.version}` };
    return { label: "Not yet confirmed", short: "Unconfirmed", color: "", detail: `Confirmed — · Latest v${n.version}` };
  }
  function assistanceLabel(c) {
    const labels = { none: "No handoff requested", requested: "Human handoff requested", assigned: "Awaiting human acceptance", accepted: "Human handoff accepted", completed: "Assistance completed" };
    if (c.assistance_status === "none" && needsHuman(c)) return "Human review required";
    return labels[c.assistance_status] || "Human review required";
  }
  function contactLabel(status) {
    return { not_contacted: "Not contacted", connected: "Connected", dropped: "Call interrupted", no_answer: "No answer", resumed: "Contact resumed", ended: "Call ended" }[status] || titleCase(status || "not_contacted");
  }
  function callbackLabel(stage) {
    return { none: "No callback planned", retry_pending: "Retry planned", contact_review: "Contact review needed", human_review: "Human review needed" }[stage] || titleCase(stage);
  }
  function getErrorText(data, fallback) {
    if (typeof data?.detail === "string") return data.detail;
    if (typeof data?.message === "string") return data.message;
    if (typeof data?.error === "string") return data.error;
    if (typeof data?.detail?.message === "string") return data.detail.message;
    if (Array.isArray(data?.detail)) return data.detail.map((item) => `${(item.loc || []).slice(1).join(" ")}: ${item.msg || "Invalid value"}`).join(". ");
    return fallback;
  }

  async function request(path, options = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 18000);
    const headers = { Accept: "application/json", ...(options.body ? { "Content-Type": "application/json" } : {}) };
    const token = readToken();
    if (token) headers["X-Operator-Token"] = token;
    try {
      const response = await fetch(new URL(path.replace(/^\//, ""), APP_BASE), { ...options, headers: { ...headers, ...options.headers }, signal: controller.signal, cache: "no-store" });
      const contentType = response.headers.get("content-type") || "";
      const data = contentType.includes("application/json") ? await response.json() : null;
      if (!response.ok) {
        const error = new Error(getErrorText(data, `Request could not be completed (${response.status}).`));
        error.status = response.status;
        throw error;
      }
      if (!data) throw new Error("The server returned an unexpected response. Refresh and try again.");
      return data;
    } catch (error) {
      if (error.name === "AbortError" || error instanceof TypeError) {
        const unavailable = new Error(error.name === "AbortError" ? "The connection timed out. Your last known state is still shown." : "The server cannot be reached. Your last known state is still shown.");
        unavailable.network = true;
        throw unavailable;
      }
      throw error;
    } finally { clearTimeout(timer); }
  }
  function showError(message, target = "global-error") {
    $(target).textContent = message;
    $(target).hidden = false;
  }
  function clearError(target = "global-error") { $(target).hidden = true; $(target).replaceChildren(); }
  function toast(message, type = "") {
    const item = node("div", `toast ${type}`, message);
    $("toast-region").append(item);
    setTimeout(() => item.remove(), type === "error" ? 8500 : 6000);
  }
  function openDialog(id) { const dialog = $(id); if (!dialog.open) dialog.showModal(); }
  function closeDialog(id) { $(id).close(); }
  function renderSync() {
    const text = !app.state ? "Connecting" : app.online ? `Synced ${clock(app.lastSync)}` : "Connection unavailable";
    $("sync-status").replaceChildren(dot(app.online ? "teal" : "amber"), node("span", "", text));
  }
  function applyState(state) {
    if (!state || !Array.isArray(state.cases)) throw new Error("Dashboard data is incomplete.");
    app.state = state;
    app.online = true;
    app.lastSync = new Date().toISOString();
    if (!caseById(app.selectedId)) app.selectedId = sortedCases()[0]?.id || null;
    clearError();
    render();
  }
  async function refreshState({ quiet = false, force = false } = {}) {
    if (app.fetching) return;
    app.fetching = true;
    $("refresh-button").disabled = true;
    try {
      if (force) app.caseSignature = "";
      applyState(await request("/api/state"));
    } catch (error) {
      app.online = false;
      renderSync();
      if (error.status === 401 || error.status === 403) {
        showError("This response desk requires a valid operator token. Open connection settings to continue.");
        const accessButton = button("Connection settings →", "text-button", openSettings);
        $("global-error").append(accessButton);
      } else if (!quiet || !app.state) showError(error.message);
      if (!app.state) $("queue-list").replaceChildren(append(node("div", "empty-state"), node("p", "", "Waiting for a connection to the response desk."), button("Try again", "button button-small", () => refreshState())));
    } finally { app.fetching = false; $("refresh-button").disabled = false; }
  }
  async function act(action, payload, { success = "Saved.", control = null, errorTarget = null, id = null } = {}) {
    if (control) control.disabled = true;
    if (errorTarget) clearError(errorTarget);
    try {
      const response = await request(`/api/actions/${encodeURIComponent(action)}`, { method: "POST", body: JSON.stringify({ event_id: id || eventId(), payload }) });
      if (response.state) applyState(response.state);
      else await refreshState({ force: true });
      if (success) toast(success);
      return response;
    } catch (error) {
      if (errorTarget) showError(error.message, errorTarget);
      else toast(error.message, "error");
      if (error.network) { app.online = false; renderSync(); }
      throw error;
    } finally { if (control?.isConnected) control.disabled = false; }
  }
  function runAction(action, payload, options) { return act(action, payload, options).catch(() => null); }

  function sortedCases() {
    return [...(app.state?.cases || [])].sort((a, b) => Number(a.severity?.slice(1) || 3) - Number(b.severity?.slice(1) || 3) || new Date(a.created_at) - new Date(b.created_at) || a.id.localeCompare(b.id));
  }
  function matchesFilter(c, filter) {
    if (filter === "attention") return needsHuman(c);
    if (filter === "updates") return confirmation(c).short.startsWith("Needs v");
    if (filter === "handoffs") return openAssistance(c);
    return true;
  }
  function renderMetrics() {
    const metrics = app.state.metrics || {};
    const cards = [
      { name: "Total requests", value: metrics.total_cases ?? app.state.cases.length, icon: "↗", note: "Across the response workspace", color: "" },
      { name: "Current confirmations", value: metrics.current_confirmations ?? 0, icon: "✓", note: `${metrics.pending_updates ?? 0} need the latest instruction`, color: "teal" },
      { name: "Need human attention", value: metrics.needs_human ?? app.state.cases.filter(needsHuman).length, icon: "!", note: "Review, acceptance, or follow-up", color: "amber" },
      { name: "Open assistance", value: metrics.open_assistance ?? app.state.cases.filter(openAssistance).length, icon: "⇄", note: "Independent of message confirmation", color: "" },
    ];
    $("metrics-grid").replaceChildren(...cards.map((card) => append(node("div", `metric-card ${card.color}`), append(node("div", "metric-top"), node("span", "", card.name), node("span", "metric-symbol", card.icon)), node("div", "metric-value", card.value), node("div", "metric-bottom", card.note))));
  }
  function renderQueue() {
    const all = sortedCases();
    const filters = [["all", "All"], ["attention", "Attention"], ["updates", "Updates"], ["handoffs", "Handoffs"]];
    $("queue-filters").replaceChildren(...filters.map(([key, label]) => {
      const chip = button(label, `filter-chip ${key === app.filter ? "active" : ""}`, () => { app.filter = key; renderQueue(); });
      chip.setAttribute("aria-pressed", String(key === app.filter));
      chip.append(node("span", "", all.filter((c) => matchesFilter(c, key)).length));
      return chip;
    }));
    const needle = app.search.toLowerCase().trim();
    const visible = all.filter((c) => matchesFilter(c, app.filter) && (!needle || [c.resident_name, c.resident_id, c.id, c.summary, c.zone, c.severity, c.category].join(" ").toLowerCase().includes(needle)));
    $("queue-count").textContent = visible.length;
    if (!visible.length) {
      $("queue-list").replaceChildren(append(node("div", "empty-state"), node("h3", "", "No requests in this view"), node("p", "", "Try another filter or search term.")));
      return;
    }
    const previousScroll = $("queue-list").scrollTop;
    $("queue-list").replaceChildren(...visible.map((c) => {
      const selected = c.id === app.selectedId;
      const row = button("", `case-row ${selected ? "selected" : ""}`, () => selectCase(c.id));
      row.setAttribute("aria-pressed", String(selected));
      row.setAttribute("aria-label", `${c.severity}, ${c.resident_name}, ${confirmation(c).label}, ${assistanceLabel(c)}`);
      const heading = append(node("div", "row-heading"), node("span", `priority ${c.severity?.toLowerCase()}`, c.severity), node("span", "row-name", c.resident_name), node("span", "row-language", c.language === "es" ? "ES" : "EN"));
      const status = confirmation(c);
      const statusLine = append(node("span", `mini-status ${status.color}`), dot(status.color), document.createTextNode(status.short));
      const handoff = append(node("div", `row-handoff ${openAssistance(c) ? "assistance-open" : ""}`), node("span", "", c.assistance_status === "completed" ? "✓" : "↳"), node("span", "", assistanceLabel(c)));
      append(row, heading, node("p", "row-summary", c.summary || "No summary provided"), append(node("div", "row-bottom"), statusLine, node("span", "row-age", age(c.created_at))), handoff);
      return row;
    }));
    $("queue-list").scrollTop = previousScroll;
  }
  function selectCase(id) {
    app.selectedId = id;
    app.caseSignature = "";
    renderQueue(); renderCase();
    if (window.innerWidth <= 780) $("case-panel").scrollIntoView({ behavior: "smooth", block: "start" });
  }
  function section(number, title, action) {
    const wrap = node("section", "case-section");
    append(wrap, append(node("div", "section-heading"), append(node("div", "section-title"), node("span", "section-number", number), node("h3", "", title)), action));
    return wrap;
  }
  function stateCell(label, value, detail, color = "") {
    return append(node("div", "state-cell"), node("span", "state-label", label), append(node("span", `state-value ${color}`), dot(color), document.createTextNode(value)), node("p", "state-detail", detail));
  }
  function buildCaseHeading(c) {
    const conf = confirmation(c);
    const owner = app.state.responders?.find((r) => r.id === c.owner_id);
    const initials = c.resident_name?.split(/\s+/).map((word) => word[0]).filter(Boolean).slice(0, 2).join("").toUpperCase() || "DR";
    const meta = append(node("div", "case-meta"), node("span", "", languageLabel(c.language)), node("span", "", "·"), node("span", "", c.zone), node("span", "", "·"), node("span", "", titleCase(c.category)));
    const heading = node("div", "case-heading");
    append(heading,
      append(node("div", "case-topline"), append(node("span", "case-ref"), node("span", "", "REQUEST"), node("span", "", c.id.toUpperCase())), node("span", "", `Updated ${clock(c.updated_at)}`)),
      append(node("div", "case-person"), node("div", "avatar", initials), append(node("div", ""), node("h2", "", c.resident_name), meta), node("span", `priority ${c.severity?.toLowerCase()}`, c.severity)),
      node("p", "case-summary", c.summary),
      append(node("div", "state-grid"), stateCell("Message confirmation", conf.label, conf.detail, conf.color), stateCell("Human follow-through", assistanceLabel(c), owner ? `Owner: ${owner.name}` : "No accepted owner yet", ["accepted", "completed"].includes(c.assistance_status) ? "teal" : needsHuman(c) ? "amber" : ""))
    );
    return heading;
  }
  function alternateAction(n) {
    const isSouth = /south|sur/i.test(`${n.action_key} ${n.action_label_en}`);
    return isSouth ? { key: "north_entrance", en: "North entrance", es: "Entrada norte" } : { key: "south_entrance", en: "South entrance", es: "Entrada sur" };
  }
  function buildReadback(c, n, lang) {
    const form = node("form", "readback-form");
    form.setAttribute("aria-label", "Record the person's read-back");
    const alternate = alternateAction(n);
    const options = [
      { key: n.action_key, label: lang === "es" ? n.action_label_es : n.action_label_en, help: "Current approved action" },
      { key: alternate.key, label: lang === "es" ? alternate.es : alternate.en, help: "Alternate action · demo error" },
    ];
    const textarea = node("textarea"); textarea.name = "readback_text"; textarea.rows = 2; textarea.required = true; textarea.maxLength = 1200; textarea.placeholder = lang === "es" ? "Lo que dijo la persona…" : "Record what the person said…";
    const choices = node("div", "choice-grid");
    options.forEach((option) => {
      const input = node("input"); input.type = "radio"; input.name = "action_key"; input.value = option.key; input.required = true;
      input.addEventListener("change", () => { textarea.value = lang === "es" ? `Voy a ir a: ${option.label}.` : `I will go to: ${option.label}.`; });
      choices.append(append(node("label", "choice-card"), input, append(node("span", "choice-text"), node("span", "", option.label), node("small", "", option.help))));
    });
    const submit = node("button", "button button-primary button-small", "Record read-back"); submit.type = "submit";
    const error = node("div", "form-error"); error.hidden = true; error.setAttribute("role", "alert");
    append(form, node("label", "readback-label", "What did the person say they will do?"), choices, append(node("label", "field"), node("span", "", "Read-back in the person's words"), textarea), error, append(node("div", "form-action-row"), node("span", "field-hint", "The selected action determines confirmation. Connection alone does not."), submit));
    form.addEventListener("submit", async (event) => {
      event.preventDefault(); error.hidden = true;
      const data = new FormData(form);
      const correct = data.get("action_key") === n.action_key;
      try {
        await act("acknowledge", { case_id: c.id, notice_version: n.version, action_key: data.get("action_key"), readback_text: String(data.get("readback_text")).trim() }, { control: submit, success: correct ? `Notice v${n.version} read-back confirmed. Assistance remains independently tracked.` : "Read-back needs clarification. The instruction was not marked confirmed." });
      } catch (failure) { if (error.isConnected) { error.textContent = failure.message; error.hidden = false; } }
    });
    return form;
  }
  function buildNotice(c) {
    const n = noticeFor(c);
    const wrap = section("01", "Confirm the current instruction", n ? button("Revise notice ↗", "text-button", () => openNoticeEditor(n.id)) : null);
    if (!n) { wrap.append(node("div", "note-placeholder", "There is no approved notice attached to this request. Human handoff and follow-up can still proceed.")); return wrap; }
    const lang = app.noticeLanguages[c.id] || c.language || "en";
    const langSwitch = node("div", "lang-switch");
    [["en", "EN"], ["es", "ES"]].forEach(([key, label]) => {
      const control = button(label, `lang-button ${key === lang ? "active" : ""}`, () => { app.noticeLanguages[c.id] = key; app.caseSignature = ""; renderCase(); });
      control.setAttribute("aria-pressed", String(key === lang)); control.setAttribute("aria-label", `Show notice in ${languageLabel(key)}`); langSwitch.append(control);
    });
    const infoTop = append(node("div", "notice-meta"), node("span", "notice-version", `APPROVED · V${n.version}`), node("span", "notice-title", n.title));
    infoTop.style.justifyContent = "space-between"; infoTop.append(langSwitch);
    const box = append(node("div", "notice-box"), infoTop, node("p", "notice-body", lang === "es" ? n.body_es : n.body_en), append(node("div", "action-target"), node("span", "", "↗"), node("span", "", lang === "es" ? n.action_label_es : n.action_label_en)), node("p", "notice-source", `Source: ${n.source_label} · Approved by ${n.approved_by} · ${when(n.updated_at)}`));
    box.lang = lang;
    append(wrap, box, buildReadback(c, n, lang));
    return wrap;
  }
  function labeledInput(label, input) { return append(node("label", "field"), node("span", "", label), input); }
  function buildContact(c) {
    const wrap = section("02", "Contact & callback", node("span", "simulation-label", "Demo controls"));
    const contactColor = ["dropped", "no_answer"].includes(c.contact_status) ? "amber" : "";
    append(wrap, append(node("div", "contact-details"), append(node("span", `status-pill ${contactColor}`), dot(contactColor || "teal"), document.createTextNode(contactLabel(c.contact_status))), node("span", "", `${c.contact_failures || 0} failed ${c.contact_failures === 1 ? "attempt" : "attempts"}`)));
    const controls = node("div", "simulation-controls");
    [["connected", "Connected"], ["dropped", "Dropped call"], ["no_answer", "No answer"], ["resumed", "Resume contact"]].forEach(([outcome, label]) => {
      const control = button(label, "button button-small", () => runAction("contact", { case_id: c.id, outcome }, { control, success: `Simulated resident contact: ${contactLabel(outcome).toLowerCase()}.` }));
      control.title = `Simulation only: record ${label.toLowerCase()}; no call is placed.`;
      controls.append(control);
    });
    append(wrap, controls, node("p", "simulation-note", "Simulated resident contact only. These buttons do not place calls or send messages."));
    if (c.callback_stage && c.callback_stage !== "none") {
      const due = c.callback_due_at ? ` · Due ${clock(c.callback_due_at)}` : "";
      append(wrap, append(node("div", "callback-strip"), node("span", "", "↻"), append(node("span", ""), node("strong", "", callbackLabel(c.callback_stage)), document.createTextNode(`${due}. Follow-up work is planned, not sent.`))));
    }
    if (c.severity === "P0") {
      wrap.append(node("div", "guard-note", "P0 requires immediate human response. This workflow does not permit a timed callback for a P0 request."));
    } else {
      const form = node("form", "callback-form");
      const minutes = node("input"); minutes.name = "minutes"; minutes.type = "number"; minutes.min = "1"; minutes.max = "60"; minutes.value = "5"; minutes.required = true;
      const reason = node("input"); reason.name = "reason"; reason.placeholder = "Reason for follow-up"; reason.required = true; reason.maxLength = 600;
      const submit = node("button", "button", "Plan callback"); submit.type = "submit";
      append(form, append(node("div", "callback-fields"), labeledInput("Minutes", minutes), labeledInput("Follow-up reason", reason), submit));
      form.addEventListener("submit", (event) => { event.preventDefault(); runAction("callback", { case_id: c.id, minutes: Number(minutes.value), reason: reason.value.trim() }, { control: submit, success: "Callback work recorded. No call or message has been sent." }); });
      wrap.append(form);
    }
    const live = node("div", "live-call-controls"); live.id = "live-call-controls";
    wrap.append(live); renderLiveControls(live, c);
    return wrap;
  }
  function eligibleResponders(c) {
    return (app.state.responders || []).filter((r) => r.available && Number(r.active_count || 0) < Number(r.capacity || 0) && !(c.failed_responder_ids || []).includes(r.id) && (r.languages || []).includes(c.language) && (c.skills_needed || []).every((skill) => (r.skills || []).includes(skill)) && !(c.severity === "P0" && r.role === "volunteer"));
  }
  function buildHandoff(c, sectionNumber = "03") {
    const wrap = section(sectionNumber, "Human handoff", node("span", "tiny-label", "Explicit acceptance required"));
    const required = c.needs_assistance || ["P0", "P1"].includes(c.severity) || c.assistance_status !== "none" || c.communication_status === "needs_clarification" || ["contact_review", "human_review"].includes(c.callback_stage);
    if (!required) { wrap.append(node("div", "note-placeholder", "No assistance is currently requested. Message confirmation remains independently tracked.")); return wrap; }
    if (c.assistance_details) wrap.append(node("p", "assistance-text", c.assistance_details));
    const steps = [["requested", "Requested"], ["assigned", "Assigned"], ["accepted", "Accepted"], ["completed", "Completed"]];
    const index = Math.max(0, steps.findIndex(([key]) => key === c.assistance_status));
    const stepper = node("div", "stepper");
    steps.forEach(([key, label], i) => { append(stepper, append(node("div", `step ${i < index ? "done" : ""} ${i === index ? "current" : ""}`), node("span", "step-circle", i < index ? "✓" : i + 1), node("span", "", label))); });
    wrap.append(stepper);
    const owner = app.state.responders?.find((r) => r.id === c.owner_id);
    if (owner) {
      const info = append(node("div", "owner-info"), node("strong", "", owner.name), node("span", "", `${titleCase(owner.role)} · ${(owner.languages || []).map((l) => l.toUpperCase()).join(" / ")} · ${c.assistance_status === "assigned" ? "Acceptance pending" : titleCase(c.assistance_status)}`));
      const ownerCard = append(node("div", "owner-card"), info);
      if (c.assistance_status === "assigned") {
        const accept = button("Record acceptance", "button button-primary button-small", () => runAction("accept", { case_id: c.id, responder_id: owner.id }, { control: accept, success: "Human acceptance recorded. The handoff is now accepted." }));
        ownerCard.append(accept);
      }
      wrap.append(ownerCard);
      if (c.assistance_status === "assigned") {
        const failed = button("Simulate unanswered handoff", "button button-small", () => runAction("handoff_failed", { case_id: c.id, responder_id: owner.id, reason: "Demo: the assigned responder did not acknowledge the proposed handoff." }, { control: failed, success: "Simulated responder non-response recorded. The request is still pending; resident contact attempts are unchanged." }));
        append(wrap, failed, node("p", "simulation-note", "Simulation only: a responder fails to accept. This is separate from a resident not answering."));
      }
    }
    if (!["accepted", "completed"].includes(c.assistance_status)) {
      const eligible = eligibleResponders(c);
      const form = node("form", "assignment-form"); form.style.marginTop = owner ? "15px" : "0";
      const select = node("select"); select.required = true;
      if (!eligible.length) { const item = node("option", "", "No eligible responder available"); item.value = ""; select.append(item); select.disabled = true; }
      eligible.forEach((r) => {
        const item = node("option", "", `${r.name} · ${titleCase(r.role)} · ${r.active_count || 0}/${r.capacity} active`);
        item.value = r.id; if (r.id === c.recommended_responder_id) item.selected = true; select.append(item);
      });
      const submit = node("button", "button", owner ? "Reassign" : "Assign human"); submit.type = "submit"; submit.disabled = !eligible.length;
      append(form, labeledInput(owner ? "Another eligible responder" : "Eligible responder", select), submit);
      form.addEventListener("submit", (event) => { event.preventDefault(); runAction("assign", { case_id: c.id, responder_id: select.value }, { control: submit, success: "Handoff assigned. Human acceptance is still required." }); });
      append(wrap, form, node("p", "eligibility-note", `Matches ${languageLabel(c.language)}, ${(c.skills_needed || []).length ? `required skills (${c.skills_needed.join(", ")})` : "required skills"}, availability, and capacity.${c.severity === "P0" ? " P0 excludes volunteers." : ""}`));
    }
    if (c.assistance_status === "accepted") {
      const form = node("form", "resolve-form");
      const input = node("textarea"); input.name = "note"; input.rows = 2; input.required = true; input.maxLength = 1200; input.placeholder = "Record what was completed and who verified it.";
      const submit = node("button", "button button-primary button-small", "Record completion"); submit.type = "submit";
      append(form, labeledInput("Completion note", input), submit);
      form.addEventListener("submit", (event) => { event.preventDefault(); runAction("resolve", { case_id: c.id, note: input.value.trim() }, { control: submit, success: "Assistance completion recorded. Message confirmation remains separately tracked." }); });
      wrap.append(form);
    }
    if (c.assistance_status === "completed") wrap.append(node("div", "note-placeholder", "Human assistance has been marked completed. A new or unconfirmed notice can still require follow-up."));
    wrap.append(node("p", "section-footnote", "Assignment proposes responsibility. Record acceptance only when that human has accepted the handoff."));
    return wrap;
  }
  function buildAudit(c, sectionNumber = "04") {
    const events = (app.state.events || []).filter((e) => e.case_id === c.id || !e.case_id).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    const wrap = section(sectionNumber, "Activity trail", node("span", "audit-count", `${events.length} ${events.length === 1 ? "event" : "events"}`)); wrap.classList.add("audit-section");
    const list = node("ol", "audit-list");
    events.slice(0, 25).forEach((e) => {
      const detail = typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail || {});
      const info = append(node("div", "audit-detail"), node("span", "", detail || titleCase(e.kind)), node("span", "audit-actor", `${titleCase(e.kind)} · ${e.actor || "System"}`));
      const time = node("time", "audit-time", clock(e.created_at)); time.dateTime = e.created_at || ""; time.title = when(e.created_at);
      append(list, append(node("li", "audit-event"), node("span", "audit-dot"), info, time));
    });
    wrap.append(events.length ? list : node("p", "notices-empty", "No recorded events for this request yet."));
    return wrap;
  }
  function captureCaseInputs() {
    const values = [];
    $("case-panel").querySelectorAll("form").forEach((form, formIndex) => {
      [...form.elements].forEach((field, fieldIndex) => {
        if (["INPUT", "TEXTAREA", "SELECT"].includes(field.tagName)) values.push({ formIndex, fieldIndex, value: field.value, checked: field.checked, type: field.type });
      });
    });
    return values;
  }
  function restoreCaseInputs(values) {
    const forms = $("case-panel").querySelectorAll("form");
    values.forEach((saved) => {
      const field = forms[saved.formIndex]?.elements[saved.fieldIndex];
      if (!field || field.type !== saved.type) return;
      if (["radio", "checkbox"].includes(field.type)) { if (field.value === saved.value) field.checked = saved.checked; }
      else if (field.tagName !== "SELECT" || [...field.options].some((o) => o.value === saved.value)) field.value = saved.value;
    });
  }
  function renderCase() {
    const c = currentCase();
    if (!c) return;
    const relevantEvents = (app.state.events || []).filter((e) => e.case_id === c.id || !e.case_id);
    const signature = JSON.stringify([c, noticeFor(c), app.state.responders, relevantEvents, app.state.integration, app.noticeLanguages[c.id]]);
    if (signature === app.caseSignature) return;
    const panel = $("case-panel");
    const sameVersion = panel.dataset.caseId === c.id && panel.dataset.noticeVersion === String(noticeFor(c)?.version || "");
    const saved = sameVersion ? captureCaseInputs() : [];
    app.caseSignature = signature;
    const urgentWithoutNotice = ["P0", "P1"].includes(c.severity) && !noticeFor(c);
    const sections = urgentWithoutNotice ? [buildHandoff(c, "01"), buildContact(c)] : [buildNotice(c), buildContact(c), buildHandoff(c)];
    panel.replaceChildren(buildCaseHeading(c), ...sections, buildAudit(c, urgentWithoutNotice ? "03" : "04"));
    panel.dataset.caseId = c.id; panel.dataset.noticeVersion = String(noticeFor(c)?.version || "");
    if (sameVersion) restoreCaseInputs(saved);
  }
  function renderIntegration() {
    const integration = app.state.integration || {};
    const voice = integration.retell_configured ? "Ready on request" : "Not connected";
    $("integration-status").replaceChildren(append(node("div", ""), document.createTextNode("Browser voice · "), node("strong", "", voice)), append(node("div", ""), document.createTextNode("SMS · "), node("strong", "", integration.sms || "Not connected")));
  }
  function render() { renderSync(); renderMetrics(); renderQueue(); renderCase(); renderIntegration(); renderOutbox(); if ($("notices-dialog").open) renderNotices(); }

  function openIntake() {
    if (!app.state) { toast("Connect to the response desk before recording a new intake.", "warning"); return; }
    clearError("intake-error");
    const zones = app.state.zones || [];
    $("intake-zone").replaceChildren(...zones.map((z) => { const option = node("option", "", z.id); option.value = z.id; return option; }));
    $("intake-notice").replaceChildren(append(node("option", "", "No notice attached")));
    $("intake-notice").firstChild.value = "";
    app.state.notices.forEach((n) => { const option = node("option", "", `${n.title} · v${n.version}`); option.value = n.id; $("intake-notice").append(option); });
    if (currentCase()?.notice_id) $("intake-notice").value = currentCase().notice_id;
    const ref = $("intake-form").elements.resident_id;
    if (!ref.value) ref.value = `demo-${Date.now().toString().slice(-6)}`;
    openDialog("intake-dialog");
  }
  function getIntakePayload(form) {
    const data = new FormData(form);
    return {
      resident_name: String(data.get("resident_name")).trim(), resident_id: String(data.get("resident_id")).trim(), language: data.get("language"),
      zone: data.get("zone"), category: data.get("category"), severity: data.get("severity"),
      skills_needed: String(data.get("skills_needed") || "").split(",").map((value) => value.trim().toLowerCase()).filter(Boolean),
      summary: String(data.get("summary")).trim(), notice_id: data.get("notice_id") || null,
      needs_assistance: data.get("needs_assistance") === "on", assistance_details: String(data.get("assistance_details") || "").trim(),
    };
  }
  function loadOutbox() {
    try {
      const parsed = JSON.parse(localStorage.getItem(OUTBOX_KEY) || "[]");
      app.outbox = Array.isArray(parsed) ? parsed.filter((item) => item && typeof item.event_id === "string" && item.action === "submit_report" && item.payload && typeof item.payload === "object").slice(0, 100) : [];
    } catch { app.outbox = []; }
  }
  function saveOutbox() {
    try { localStorage.setItem(OUTBOX_KEY, JSON.stringify(app.outbox)); return true; }
    catch { toast("Browser storage is unavailable. This unsent draft exists only while this page stays open.", "warning"); return false; }
  }
  function queueIntake(payload, id, simulated = false) {
    app.outbox.push({ action: "submit_report", event_id: id, payload, created_at: new Date().toISOString(), simulated });
    const saved = saveOutbox(); renderOutbox();
    toast(saved ? "Unsent draft saved in this browser. It is not received until sync succeeds." : "Unsent draft kept on this page only. It has not been received.", "warning");
  }
  function renderOutbox() {
    const count = app.outbox.length;
    $("nav-outbox-count").textContent = count;
    $("outbox-banner").hidden = !count;
    $("outbox-banner-text").textContent = `${count} unsent ${count === 1 ? "draft is" : "drafts are"} saved locally. These requests have not been marked received.`;
    $("sync-drafts").disabled = app.syncing;
    $("sync-drafts").textContent = app.syncing ? "Syncing…" : "Sync now";
    $("outbox-sync-button").disabled = !count || app.syncing;
    $("outbox-sync-button").textContent = app.syncing ? "Syncing…" : "Sync saved drafts";
    $("outbox-sync-label").textContent = `${count} ${count === 1 ? "draft" : "drafts"} awaiting delivery`;
    if (!count) {
      $("outbox-list").replaceChildren(append(node("div", "empty-state"), node("h3", "", "No unsent drafts"), node("p", "", "Disconnected text intake will appear here until you sync it.")));
      return;
    }
    $("outbox-list").replaceChildren(...app.outbox.map((draft) => {
      const discard = button("Discard draft", "text-button", () => { app.outbox = app.outbox.filter((item) => item.event_id !== draft.event_id); saveOutbox(); renderOutbox(); });
      discard.disabled = app.syncing;
      return append(node("article", "outbox-item"), append(node("div", "outbox-item-header"), node("h3", "", draft.payload.resident_name || "Unsent request"), discard), node("p", "", draft.payload.summary || "No summary"), node("small", "", `UNSENT · ${draft.payload.severity} · ${languageLabel(draft.payload.language)} · Saved ${when(draft.created_at)}${draft.simulated ? " · Disconnected-intake simulation" : ""}`));
    }));
  }
  async function syncOutbox() {
    if (app.syncing || !app.outbox.length) return;
    app.syncing = true; renderOutbox(); let completed = 0;
    try {
      for (const draft of [...app.outbox]) {
        const response = await request("/api/actions/submit_report", { method: "POST", body: JSON.stringify({ event_id: draft.event_id, payload: draft.payload }) });
        app.outbox = app.outbox.filter((item) => item.event_id !== draft.event_id); saveOutbox(); completed++;
        if (response.state) applyState(response.state);
      }
      toast(`${completed} saved ${completed === 1 ? "request was" : "requests were"} received by the response desk.`);
    } catch (error) {
      toast(`${completed ? `${completed} received. ` : ""}Remaining drafts are still unsent: ${error.message}`, "error");
    } finally { app.syncing = false; renderOutbox(); }
  }
  function replaceText(body, oldText, nextText) {
    if (!oldText) return body;
    const escaped = oldText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return String(body).replace(new RegExp(escaped, "gi"), nextText);
  }
  function openNoticeEditor(id) {
    const n = app.state?.notices.find((item) => item.id === id);
    if (!n) return;
    const alternative = alternateAction(n);
    const form = $("notice-form");
    app.editNotice = { id: n.id, expectedVersion: n.version };
    let en = replaceText(n.body_en, n.action_label_en, alternative.en);
    let es = replaceText(n.body_es, n.action_label_es, alternative.es);
    if (en === n.body_en) en = `${n.body_en}\nUpdated pickup point: ${alternative.en}.`;
    if (es === n.body_es) es = `${n.body_es}\nPunto de recogida actualizado: ${alternative.es}.`;
    form.elements.body_en.value = en; form.elements.body_es.value = es;
    form.elements.action_key.value = alternative.key; form.elements.action_label_en.value = alternative.en; form.elements.action_label_es.value = alternative.es;
    form.elements.source_label.value = n.source_label; form.elements.approved_by.value = n.approved_by;
    const affected = app.state.cases.filter((c) => c.notice_id === n.id).length;
    $("notice-change-callout").textContent = `Editing ${n.title}, currently v${n.version}. The next pickup point is prefilled for the demo. Review both languages before publishing. ${affected} linked ${affected === 1 ? "request will" : "requests will"} need the current instructions; existing human handoffs keep their own state.`;
    clearError("notice-error"); closeDialog("notices-dialog"); openDialog("notice-dialog");
  }
  function renderNotices() {
    if (!app.state) return;
    $("notices-list").replaceChildren(...app.state.notices.map((n) => {
      const card = node("article", "notice-list-item");
      append(card, append(node("div", "notice-meta"), node("span", "notice-version", `V${n.version}`), node("h3", "", n.title)), node("p", "notice-body", n.body_en), node("p", "notice-body", n.body_es), node("p", "notice-source", `${n.source_label} · Approved by ${n.approved_by} · ${when(n.updated_at)}`), button("Revise approved notice", "button button-small", () => openNoticeEditor(n.id)));
      return card;
    }));
  }
  function openSettings() {
    $("settings-form").elements.token.value = readToken();
    clearError("settings-error");
    const integration = app.state?.integration || {};
    $("connection-detail").textContent = `Browser voice: ${integration.retell_configured ? "configured; starts only when requested" : "not connected"}. SMS: ${integration.sms || "not connected"}. Demo contact controls do not use either channel.`;
    openDialog("settings-dialog");
  }
  function renderLiveControls(target, c) {
    target.replaceChildren();
    const configured = app.state.integration?.retell_configured;
    if (!configured) { append(target, dot(), node("span", "", "Live browser voice is not connected. The demo above is simulated.")); return; }
    const active = ["connecting", "live"].includes(app.live.status);
    if (active) {
      append(target, append(node("span", "live-call-status"), dot("teal"), document.createTextNode(app.live.status === "live" ? " Live browser session" : " Connecting browser voice…")));
      const stop = button("End browser call", "button button-small", async () => {
        stop.disabled = true;
        try { await app.live.module?.endRetellCall(); setLiveStatus("ended"); }
        catch (error) { toast(`Could not end the browser call: ${error.message}`, "error"); }
        finally { if (stop.isConnected) stop.disabled = false; }
      });
      target.append(stop);
      if (app.live.caseId !== c.id) target.append(node("span", "", `Session belongs to ${app.live.caseId}.`));
    } else {
      const start = button("Start live browser call", "button button-small", () => startLive(c));
      append(target, start, node("span", "", "Uses your microphone. No telephone number is dialed."));
      if (app.live.status === "error") target.append(node("span", "live-call-status", app.live.message || "The live connection could not be started."));
    }
  }
  function setLiveStatus(status, message = "") {
    app.live.status = status; app.live.message = message;
    const target = $("live-call-controls");
    if (target && currentCase()) renderLiveControls(target, currentCase());
    if (status === "ended") refreshState({ quiet: true });
  }
  async function startLive(c) {
    app.live.caseId = c.id; setLiveStatus("connecting");
    try {
      if (!app.live.module) app.live.module = await import(new URL("static/retell-client.js", APP_BASE).href);
      await app.live.module.startRetellCall({
        caseId: c.id, language: c.language || "en", token: readToken(),
        onStatus: (status, message) => {
          if (typeof status === "string") setLiveStatus(status, typeof message === "string" ? message : "");
          else if (status && typeof status === "object") setLiveStatus(status.status || "error", status.message || "");
        },
        onTranscript: () => {},
      });
    } catch (error) {
      setLiveStatus("error", error.message || "Unable to connect browser voice.");
      toast(`Live browser voice could not connect: ${error.message || "Check configuration and microphone permissions."}`, "error");
    }
  }

  document.querySelectorAll("[data-close]").forEach((control) => control.addEventListener("click", () => closeDialog(control.dataset.close)));
  document.querySelectorAll("dialog").forEach((dialog) => dialog.addEventListener("click", (event) => { if (event.target === dialog) { const rect = dialog.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close(); } }));
  $("new-intake-button").addEventListener("click", openIntake);
  $("refresh-button").addEventListener("click", () => refreshState({ force: true }));
  $("connection-settings").addEventListener("click", openSettings);
  $("nav-desk").addEventListener("click", () => $("main").scrollIntoView({ behavior: "smooth" }));
  $("nav-notices").addEventListener("click", () => { if (!app.state) return toast("Connect to load approved notices.", "warning"); renderNotices(); openDialog("notices-dialog"); });
  ["nav-outbox", "view-drafts"].forEach((id) => $(id).addEventListener("click", () => { renderOutbox(); openDialog("outbox-dialog"); }));
  ["sync-drafts", "outbox-sync-button"].forEach((id) => $(id).addEventListener("click", syncOutbox));
  $("queue-search").addEventListener("input", (event) => { app.search = event.target.value; if (app.state) renderQueue(); });
  $("help-toggle").addEventListener("click", () => { const open = $("demo-help").hidden; $("demo-help").hidden = !open; $("help-toggle").setAttribute("aria-expanded", String(open)); });
  $("try-demo").addEventListener("click", () => {
    const candidate = app.state?.cases.find((c) => c.id === "case-001") || app.state?.cases.find((c) => c.notice_id && c.needs_assistance);
    if (candidate) selectCase(candidate.id);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName) && !document.querySelector("dialog[open]")) { event.preventDefault(); $("queue-search").focus(); }
  });
  $("intake-form").addEventListener("submit", async (event) => {
    event.preventDefault(); clearError("intake-error");
    const form = event.currentTarget;
    const payload = getIntakePayload(form); const id = eventId();
    const submit = form.querySelector("button[type=submit]");
    if (!payload.resident_name || !payload.resident_id || !payload.summary) { showError("Please include a resident name, reference, and request summary.", "intake-error"); return; }
    if (form.elements.save_offline.checked || !navigator.onLine) {
      queueIntake(payload, id, form.elements.save_offline.checked); closeDialog("intake-dialog"); form.reset(); return;
    }
    submit.disabled = true;
    try {
      const response = await request("/api/actions/submit_report", { method: "POST", body: JSON.stringify({ event_id: id, payload }) });
      if (response.state) {
        const created = response.state.cases.find((c) => c.resident_id === payload.resident_id);
        if (created) app.selectedId = created.id;
        applyState(response.state);
      } else await refreshState({ force: true });
      toast("Request received by the response desk."); closeDialog("intake-dialog"); form.reset();
    } catch (error) {
      if (error.network) { queueIntake(payload, id); closeDialog("intake-dialog"); form.reset(); }
      else showError(error.message, "intake-error");
    } finally { submit.disabled = false; }
  });
  $("notice-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!app.editNotice) return;
    const data = new FormData(event.currentTarget);
    const payload = { notice_id: app.editNotice.id, expected_version: app.editNotice.expectedVersion };
    ["body_en", "body_es", "action_key", "action_label_en", "action_label_es", "source_label", "approved_by"].forEach((key) => { payload[key] = String(data.get(key) || "").trim(); });
    const submit = event.currentTarget.querySelector("button[type=submit]");
    try {
      await act("revise_notice", payload, { control: submit, errorTarget: "notice-error", success: "Notice revised. Prior confirmations now need the current instruction; handoff state is preserved." });
      closeDialog("notice-dialog");
    } catch (error) {
      if (error.status === 409) { await refreshState({ quiet: true }); showError(`${error.message} Close and reopen this editor to review the latest version. Your current edits have not been published.`, "notice-error"); }
    }
  });
  $("settings-form").addEventListener("submit", async (event) => {
    event.preventDefault(); clearError("settings-error");
    const submit = event.currentTarget.querySelector("button[type=submit]"); submit.disabled = true;
    try { writeToken(event.currentTarget.elements.token.value.trim()); applyState(await request("/api/state")); closeDialog("settings-dialog"); toast("Connected to the response desk."); }
    catch (error) { showError(error.message, "settings-error"); }
    finally { submit.disabled = false; }
  });
  $("clear-token").addEventListener("click", () => { try { writeToken(""); $("settings-form").elements.token.value = ""; toast("Operator token cleared for this tab."); } catch (error) { showError(error.message, "settings-error"); } });
  window.addEventListener("online", () => { refreshState({ quiet: true }); if (app.outbox.length) toast("Connection restored. Your saved drafts are ready to sync when you choose.", "warning"); });
  window.addEventListener("offline", () => { app.online = false; renderSync(); toast("Connection lost. New text intake can be saved locally for later sync.", "warning"); });
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refreshState({ quiet: true }); });

  loadOutbox(); renderOutbox(); refreshState();
  setInterval(() => { if (!document.hidden) refreshState({ quiet: true }); }, 7000);
})();
