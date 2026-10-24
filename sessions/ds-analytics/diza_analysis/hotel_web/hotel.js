const $ = (id) => document.getElementById(id);
const state = {
  data: null,
  filter: "open",
  room: "",
  detail: null,
  guest: null,
  session: null,
  busy: false,
  staffLoading: false,
  lastMessage: null,
  pendingRevision: null,
  token: sessionStorage.getItem("hotel-staff-token") || "hotel-demo-local",
};
const keys = new Map();
const statusLabels = {
  new: "Awaiting owner",
  assigned: "Assigned",
  in_progress: "In progress",
  completed: "Completed",
};
const teams = {
  maintenance: "Maintenance",
  housekeeping: "Housekeeping",
  front_desk: "Front desk",
};
const prompts = {
  en: {
    wifi: "How do I connect to the Wi-Fi?",
    towels: "Could I have two extra towels, please?",
    ac: "The air conditioning in my room is blowing warm air.",
  },
  es: {
    wifi: "¿Cómo me conecto al wifi?",
    towels: "¿Podría tener dos toallas extra, por favor?",
    ac: "El aire acondicionado de mi habitación no enfría.",
  },
};
function node(tag, className, text) {
  const result = document.createElement(tag);
  if (className) result.className = className;
  if (text !== undefined) result.textContent = text;
  return result;
}
function badge(text, style = "") {
  return node("span", `badge ${style}`, text);
}
function age(timestamp) {
  const minutes = Math.max(0, Math.floor((Date.now() / 1000 - timestamp) / 60));
  return minutes < 1
    ? "Just now"
    : minutes < 60
      ? `${minutes}m ago`
      : `${Math.floor(minutes / 60)}h ${minutes % 60}m ago`;
}
function time(timestamp) {
  return new Date(timestamp * 1000).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
function notice(text, error = false) {
  $("message").textContent = text;
  $("message").classList.toggle("error", error);
  $("message").hidden = !text;
}
async function api(path, body, guest = false) {
  const response = await fetch(`/api/hotel${path}`, {
    method: body === undefined ? "GET" : "POST",
    cache: "no-store",
    signal: AbortSignal.timeout(15000),
    headers: {
      ...(guest
        ? { "X-Guest-Token": state.session?.token || "" }
        : { Authorization: `Bearer ${state.token}` }),
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const result = await response.json();
  if (!response.ok) {
    const error = new Error(
      typeof result.detail === "string"
        ? result.detail
        : "Please check the required fields.",
    );
    error.status = response.status;
    throw error;
  }
  return result;
}
async function mutate(path, body, guest = false) {
  const signature = path + JSON.stringify(body);
  if (!keys.has(signature)) keys.set(signature, crypto.randomUUID());
  const result = await api(
    path,
    { ...body, idempotency_key: keys.get(signature) },
    guest,
  );
  keys.delete(signature);
  return result;
}
function buttonAction(button, action) {
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await action();
    } catch (error) {
      report(error);
    } finally {
      button.disabled = false;
    }
  });
}
function report(error) {
  const text = error.message || "Connection interrupted. Please try again.";
  if ($("ticket-dialog").open) {
    $("dialog-message").textContent = text;
    $("dialog-message").hidden = false;
  } else notice(text, true);
}
function renderDesk() {
  const data = state.data;
  if (!data) return;
  $("staff-content").hidden = false;
  $("staff-login").hidden = true;
  $("open-count").textContent = data.counts.open;
  $("priority-count").textContent = data.counts.priority;
  $("working-count").textContent = data.counts.in_progress;
  $("answered-count").textContent = data.counts.answered;
  const search = $("search").value.trim().toLowerCase();
  const visible = data.tickets.filter(
    (ticket) =>
      (state.filter === "open"
        ? ticket.status !== "completed"
        : ticket.status === state.filter) &&
      (!state.room || ticket.room === state.room) &&
      `${ticket.room} ${ticket.code} ${ticket.quote} ${ticket.summary}`
        .toLowerCase()
        .includes(search),
  );
  $("ticket-total").textContent = visible.length;
  $("request-list").replaceChildren();
  $("requests-empty").hidden = visible.length > 0;
  for (const ticket of visible) {
    const row = node(
      "button",
      `request-row ${Date.now() / 1000 - ticket.created < 12 ? "fresh" : ""}`,
    );
    row.dataset.ticket = ticket.id;
    row.setAttribute(
      "aria-label",
      `Open ${ticket.code}, room ${ticket.room}, ${ticket.summary}`,
    );
    row.append(node("span", "room-number", ticket.room));
    const copy = node("span");
    copy.append(
      node("span", "request-title", ticket.summary),
      node("span", "request-quote", ticket.quote),
    );
    const meta = node("span", "request-meta");
    meta.append(
      node("span", "", ticket.code),
      node("span", "", teams[ticket.department]),
      node("span", "", age(ticket.created)),
    );
    copy.append(meta);
    if (ticket.related.length)
      copy.append(
        node(
          "span",
          "related-chip",
          `Also reported in ${ticket.related.map((r) => r.room).join(", ")} · Same floor`,
        ),
      );
    const status = node("span", "request-state");
    if (ticket.urgency !== "routine" && ticket.status !== "completed")
      status.append(
        badge(
          ticket.urgency === "emergency" ? "Safety alert" : "Priority",
          ticket.urgency,
        ),
      );
    status.append(
      badge(statusLabels[ticket.status], ticket.status),
      node("span", "request-owner", ticket.owner || "Not assigned"),
    );
    row.append(copy, status);
    buttonAction(row, () => openTicket(ticket.id));
    $("request-list").append(row);
  }
  $("rooms").replaceChildren();
  for (const floor of [4, 3]) {
    const line = node("div", "floor-line");
    line.append(node("span", "floor-label", `Floor ${floor}`));
    const rooms = node("div", "floor-rooms");
    for (const room of data.rooms.filter((r) => r.floor === floor)) {
      const open = data.tickets.filter(
        (t) => t.room === room.number && t.status !== "completed",
      );
      const working =
        open.length && open.every((t) => t.status === "in_progress");
      const button = node(
        "button",
        `room-chip ${open.length ? (working ? "working" : "has-request") : ""} ${state.room === room.number ? "chosen" : ""}`,
        room.number,
      );
      button.setAttribute(
        "aria-label",
        `Room ${room.number}, ${open.length} open requests`,
      );
      button.setAttribute("aria-pressed", String(state.room === room.number));
      button.addEventListener("click", () => {
        state.room = state.room === room.number ? "" : room.number;
        state.filter = "open";
        filterButtons();
        renderDesk();
        $("request-list").scrollIntoView({
          block: "nearest",
          behavior: "smooth",
        });
      });
      rooms.append(button);
    }
    line.append(rooms);
    $("rooms").append(line);
  }
  $("clear-room").hidden = !state.room;
}
function filterButtons() {
  document
    .querySelectorAll("[data-filter]")
    .forEach((button) =>
      button.classList.toggle("active", state.filter === button.dataset.filter),
    );
}
async function refresh() {
  if (state.staffLoading) return;
  state.staffLoading = true;
  try {
    state.data = await api("/state");
    renderDesk();
    $("connection").textContent = "Live workspace";
    $("connection").classList.remove("offline");
  } catch (error) {
    $("connection").textContent = "Connection paused";
    $("connection").classList.add("offline");
    if (error.status === 401) {
      $("staff-login").hidden = false;
      $("staff-content").hidden = true;
    } else if (!state.data)
      notice(
        "Could not connect to the front desk. Please try refreshing.",
        true,
      );
  } finally {
    state.staffLoading = false;
  }
}
async function openTicket(id, update = false) {
  const ticket = await api(`/tickets/${id}`);
  state.detail = id;
  $("detail-code").textContent =
    `${ticket.code} · ROOM ${ticket.room} · ${teams[ticket.department].toUpperCase()}`;
  $("detail-title").textContent = ticket.summary;
  $("ticket-body").replaceChildren();
  $("dialog-message").hidden = true;
  const body = $("ticket-body");
  const badges = node("div", "detail-badges");
  badges.append(
    badge(statusLabels[ticket.status], ticket.status),
    badge(
      ticket.urgency === "emergency"
        ? "Safety alert"
        : ticket.urgency === "priority"
          ? "Priority"
          : "Routine",
      ticket.urgency,
    ),
  );
  body.append(badges);
  body.append(node("div", "detail-quote", `“${ticket.quote}”`));
  const context = node("section", "detail-section");
  context.append(
    node("h3", "", "Guest details"),
    node(
      "p",
      "",
      `Room ${ticket.room} · ${ticket.language === "es" ? "Español" : "English"}`,
    ),
    node(
      "p",
      "",
      ticket.access_ok
        ? "Guest permits staff entry while away."
        : "Entry while the guest is away has not been authorized.",
    ),
    node("p", "", `Reported ${time(ticket.created)}`),
  );
  body.append(context);
  const assignment = node("section", "detail-section");
  assignment.append(node("h3", "", "A person owns the next step"));
  if (ticket.status === "new") {
    assignment.append(
      node(
        "p",
        "",
        "This request is saved and awaiting staff acceptance. No arrival or completion time has been promised.",
      ),
    );
    const select = node("select");
    select.setAttribute("aria-label", "Assign request to staff");
    for (const person of state.data.staff.filter(
      (s) =>
        s.department === ticket.department || s.department === "front_desk",
    )) {
      const option = node(
        "option",
        "",
        `${person.name} · ${teams[person.department]}`,
      );
      option.value = person.id;
      option.selected = person.department === ticket.department;
      select.append(option);
    }
    assignment.append(select);
    const accept = node("button", "button primary", "Accept request");
    buttonAction(accept, () =>
      decide(ticket, "assign", { staff_id: select.value }),
    );
    const row = node("div", "button-row");
    row.append(accept);
    assignment.append(row);
  } else {
    assignment.append(node("p", "", `Owner: ${ticket.owner}`));
    if (ticket.status === "completed")
      assignment.append(
        node(
          "div",
          "complete-banner",
          `Completion recorded ${time(ticket.completed)}. The guest can see the updated status.`,
        ),
      );
    else {
      const action = ticket.status === "assigned" ? "start" : "complete";
      const button = node(
        "button",
        "button primary",
        action === "start" ? "Start work" : "Record completed",
      );
      buttonAction(button, () => decide(ticket, action));
      const row = node("div", "button-row");
      row.append(button);
      assignment.append(row);
    }
  }
  body.append(assignment);
  if (ticket.related.length) {
    const related = node("section", "detail-section");
    related.append(node("h3", "", "Related reports"));
    for (const item of ticket.related)
      related.append(
        node("p", "", `${item.code} · Room ${item.room} · ${item.reason}`),
      );
    related.append(
      node(
        "p",
        "",
        "A shared floor or category is a reason to review these together. Each room keeps its own task.",
      ),
    );
    body.append(related);
  }
  const notes = node("section", "detail-section");
  notes.append(node("h3", "", "Leave a handover note"));
  const input = node("textarea");
  input.setAttribute("aria-label", "Staff handover note");
  input.maxLength = 1000;
  input.placeholder = "What should the next person know?";
  notes.append(input);
  const saveNote = node("button", "button secondary", "Save note");
  buttonAction(saveNote, () => decide(ticket, "note", { note: input.value }));
  const noteActions = node("div", "button-row");
  noteActions.append(saveNote);
  notes.append(noteActions);
  body.append(notes);
  const history = node("section", "detail-section");
  history.append(node("h3", "", "Request history"));
  const list = node("ul", "timeline");
  for (const event of ticket.events) {
    const item = node("li", "", event.detail);
    item.append(node("small", "", time(event.created)));
    list.append(item);
  }
  history.append(list);
  body.append(history);
  if (!update) $("ticket-dialog").showModal();
}
async function decide(ticket, action, fields = {}) {
  await mutate(`/tickets/${ticket.id}`, {
    expected_revision: ticket.revision,
    action,
    ...fields,
  });
  await refresh();
  await openTicket(ticket.id, true);
  await refreshGuest();
}
function guestLabels() {
  const spanish = $("guest-language").value === "es";
  $("guest-text").placeholder = spanish
    ? "¿Cómo podemos mejorar tu estancia?"
    : "How can we make your stay better?";
  $("start-session").textContent = spanish
    ? "Iniciar conversación ↗"
    : "Start conversation ↗";
  $("readback-label").textContent = spanish
    ? "REVISA TU SOLICITUD"
    : "YOUR REQUEST, READ BACK";
  $("entry-label").textContent = spanish
    ? "El personal puede entrar mientras estoy fuera."
    : "Staff may enter while I’m away.";
  $("confirm-request").textContent = spanish
    ? "Confirmar solicitud"
    : "Confirm request";
  $("cancel-request").textContent = spanish ? "Cancelar" : "Cancel";
  for (const [kind, english, translated] of [
    ["wifi", "Wi-Fi help", "Ayuda con wifi"],
    ["towels", "Extra towels", "Toallas extra"],
    ["ac", "AC not cooling", "El aire no enfría"],
  ])
    document.querySelector(`[data-prompt="${kind}"]`).textContent = spanish
      ? translated
      : english;
}
function renderGuest() {
  guestLabels();
  if (!state.guest) return;
  const guest = state.guest;
  const spanish = guest.language === "es";
  const latest = guest.messages.at(-1)?.id;
  if (latest !== state.lastMessage) {
    $("conversation").replaceChildren();
    for (const message of guest.messages) {
      const row = node("div", `chat-message ${message.role}`);
      row.append(
        node("span", "chat-icon", message.role === "guest" ? "G" : "✦"),
      );
      const copy = node("div");
      copy.append(
        node("div", "chat-content", message.text),
        node(
          "div",
          "chat-time",
          new Date(message.created * 1000).toLocaleTimeString([], {
            hour: "numeric",
            minute: "2-digit",
          }),
        ),
      );
      row.append(copy);
      $("conversation").append(row);
    }
    state.lastMessage = latest;
    $("conversation").scrollTop = $("conversation").scrollHeight;
  }
  $("request-readback").hidden = !guest.pending;
  if (guest.pending) {
    $("readback-title").textContent =
      `${spanish ? "Habitación" : "Room"} ${guest.room} · ${teams[guest.pending.department]}`;
    $("readback-quote").textContent = guest.pending.quote;
    if (state.pendingRevision !== guest.revision) {
      $("entry-permission").checked = false;
      state.pendingRevision = guest.revision;
    }
  }
  $("guest-tasks").replaceChildren();
  $("guest-tasks").hidden = guest.tickets.length === 0;
  if (guest.tickets.length) {
    $("guest-tasks").append(
      node(
        "h3",
        "",
        spanish ? "Tus solicitudes guardadas" : "Your saved requests",
      ),
    );
    for (const ticket of guest.tickets) {
      const row = node("div", "guest-task");
      row.append(node("strong", "", `${ticket.code} · ${ticket.summary}`));
      const translated = {
        new: "Esperando responsable",
        assigned: "Asignada",
        in_progress: "En curso",
        completed: "Completada",
      };
      row.append(
        node(
          "div",
          "",
          `${spanish ? translated[ticket.status] : statusLabels[ticket.status]}${ticket.owner ? ` · ${ticket.owner}` : ""}`,
        ),
      );
      $("guest-tasks").append(row);
    }
  }
}
async function startGuest() {
  state.session = await mutate(
    "/guest/start",
    { room: $("guest-room").value, language: $("guest-language").value },
    true,
  );
  localStorage.setItem("hotel-guest-session", JSON.stringify(state.session));
  state.lastMessage = null;
  state.pendingRevision = null;
  state.guest = await api(
    `/guest/${state.session.session_id}`,
    undefined,
    true,
  );
  renderGuest();
  $("guest-status").textContent =
    state.guest.language === "es"
      ? "Conversación guardada. Las solicitudes necesitan tu confirmación."
      : "Conversation saved. Service requests need your confirmation.";
}
async function guestAction(action) {
  if (state.busy) return;
  state.busy = true;
  document.querySelectorAll(".guest-panel button").forEach((button) => {
    button.disabled = true;
  });
  $("guest-status").classList.remove("error");
  try {
    await action();
  } catch (error) {
    $("guest-status").textContent = error.status
      ? error.message
      : "Connection interrupted. Your text is still here; try again when connected.";
    $("guest-status").classList.add("error");
  } finally {
    state.busy = false;
    document.querySelectorAll(".guest-panel button").forEach((button) => {
      button.disabled = false;
    });
  }
}
async function sendGuest(text) {
  if (!text.trim()) return;
  await guestAction(async () => {
    if (
      !state.session ||
      state.guest?.room !== $("guest-room").value ||
      state.guest?.language !== $("guest-language").value
    )
      await startGuest();
    state.guest = await mutate(
      `/guest/${state.session.session_id}/message`,
      { text: text.trim() },
      true,
    );
    $("guest-text").value = "";
    sessionStorage.removeItem("hotel-compose");
    renderGuest();
    await refresh();
    $("guest-status").textContent =
      state.guest.language === "es"
        ? "Guardado en tu conversación."
        : "Saved to your conversation.";
  });
}
async function confirmGuest(confirmed) {
  await guestAction(async () => {
    state.guest = await mutate(
      `/guest/${state.session.session_id}/confirm`,
      {
        expected_revision: state.guest.revision,
        confirmed,
        access_ok: $("entry-permission").checked,
      },
      true,
    );
    renderGuest();
    await refresh();
    $("guest-status").textContent =
      state.guest.language === "es"
        ? "Tu registro está actualizado."
        : "Your saved record is up to date.";
  });
}
async function refreshGuest() {
  if (!state.session || state.busy) return;
  try {
    state.guest = await api(
      `/guest/${state.session.session_id}`,
      undefined,
      true,
    );
    renderGuest();
  } catch (error) {
    if ([401, 404].includes(error.status)) {
      state.session = null;
      state.guest = null;
      localStorage.removeItem("hotel-guest-session");
      $("guest-status").textContent =
        "Start a new guest conversation for this demo.";
    }
  }
}
$("today").textContent = new Date().toLocaleDateString([], {
  weekday: "long",
  month: "short",
  day: "numeric",
});
$("staff-login").addEventListener("submit", async (event) => {
  event.preventDefault();
  state.token = $("staff-token").value.trim();
  sessionStorage.setItem("hotel-staff-token", state.token);
  $("staff-token").value = "";
  await refresh();
});
$("search").addEventListener("input", renderDesk);
document.querySelectorAll("[data-filter]").forEach((button) =>
  button.addEventListener("click", () => {
    state.filter = button.dataset.filter;
    filterButtons();
    renderDesk();
  }),
);
$("clear-room").addEventListener("click", () => {
  state.room = "";
  renderDesk();
});
buttonAction($("refresh"), refresh);
$("close-dialog").addEventListener("click", () => $("ticket-dialog").close());
$("start-session").addEventListener("click", () => guestAction(startGuest));
$("guest-language").addEventListener("change", guestLabels);
$("guest-form").addEventListener("submit", (event) => {
  event.preventDefault();
  sendGuest($("guest-text").value);
});
$("guest-text").addEventListener("input", () =>
  sessionStorage.setItem("hotel-compose", $("guest-text").value),
);
$("guest-text").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    sendGuest($("guest-text").value);
  }
});
document
  .querySelectorAll("[data-prompt]")
  .forEach((button) =>
    button.addEventListener("click", () =>
      sendGuest(prompts[$("guest-language").value][button.dataset.prompt]),
    ),
  );
$("confirm-request").addEventListener("click", () => confirmGuest(true));
$("cancel-request").addEventListener("click", () => confirmGuest(false));
try {
  const options = await api("/options");
  for (const room of options.rooms) {
    const option = node("option", "", room);
    option.value = room;
    option.selected = room === "402";
    $("guest-room").append(option);
  }
  const saved = localStorage.getItem("hotel-guest-session");
  if (saved) {
    state.session = JSON.parse(saved);
    state.guest = await api(
      `/guest/${state.session.session_id}`,
      undefined,
      true,
    );
    $("guest-room").value = state.guest.room;
    $("guest-language").value = state.guest.language;
    renderGuest();
  }
} catch {
  state.session = null;
  state.guest = null;
  localStorage.removeItem("hotel-guest-session");
}
$("guest-text").value = sessionStorage.getItem("hotel-compose") || "";
await refresh();
guestLabels();
setInterval(() => {
  if (!document.hidden) {
    refresh();
    refreshGuest();
  }
}, 2500);
window.addEventListener("online", () => {
  refresh();
  refreshGuest();
});
