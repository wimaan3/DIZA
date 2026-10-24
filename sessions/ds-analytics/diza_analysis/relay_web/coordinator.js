const $ = (id) => document.getElementById(id);
const state = {
  data: null,
  language: "en",
  filter: "all",
  token: sessionStorage.getItem("relay-operator") || "",
  detail: null,
  loading: false,
};
const pending = new Map();
const labels = {
  confirmed_current: ["Latest instruction confirmed", "confirmed"],
  updated_notice_awaiting_confirmation: [
    "Updated notice awaiting confirmation",
    "updated",
  ],
  needs_clarification: ["Needs clarification", "clarify"],
  awaiting_confirmation: ["Confirmation pending", "updated"],
  no_response: ["No response", ""],
};
const taskLabels = {
  requested: ["Awaiting owner", "clarify"],
  accepted: ["Accepted", "accepted"],
  completed: ["Completed", "confirmed"],
};
const eventLabels = {
  instruction_confirmed: "Instruction confirmed",
  clarification_requested: "Clarification requested",
  assistance_draft_saved: "Assistance draft saved",
  assistance_confirmed: "Assistance request confirmed",
  assistance_accepted: "Assistance accepted",
  assistance_completed: "Assistance completed",
  contact_no_answer: "Contact attempt: no answer",
  contact_disconnected: "Contact attempt: disconnected",
  contact_contacted: "Contact attempt recorded",
};

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function badge(text, className = "") {
  return el("span", `status ${className}`, text);
}
function date(ts) {
  return ts
    ? new Date(ts * 1000).toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      })
    : "Not contacted";
}
function message(text, error = false) {
  $("notice-message").textContent = text;
  $("notice-message").classList.toggle("error", error);
  $("notice-message").hidden = !text;
  const dialog = document.querySelector("dialog[open]");
  if (dialog && error) {
    let box = dialog.querySelector(".dialog-error");
    if (!box) {
      box = el("p", "message error dialog-error");
      box.setAttribute("role", "alert");
      dialog.append(box);
    }
    box.textContent = text;
  }
}
async function api(path, body) {
  const response = await fetch(`/api/relay${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      Authorization: `Bearer ${state.token}`,
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    cache: "no-store",
    signal: AbortSignal.timeout(20000),
  });
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401) {
      sessionStorage.removeItem("relay-operator");
      state.token = "";
      $("login").hidden = false;
      $("dashboard").hidden = true;
      $("empty").hidden = true;
    }
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Please check the required fields and try again.",
    );
  }
  return data;
}
async function mutate(path, body = {}) {
  const signature = path + JSON.stringify(body);
  if (!pending.has(signature)) pending.set(signature, crypto.randomUUID());
  const result = await api(path, {
    ...body,
    idempotency_key: pending.get(signature),
  });
  pending.delete(signature);
  return result;
}
function action(node, handler) {
  node.addEventListener("click", async () => {
    node.disabled = true;
    try {
      await handler();
    } catch (error) {
      message(error.message || "Could not connect. Please try again.", true);
    } finally {
      node.disabled = false;
    }
  });
}
function showDialog(id) {
  const dialog = $(id);
  dialog.querySelector(".dialog-error")?.remove();
  dialog.showModal();
}
function renderNotice() {
  const notice = state.data.notice;
  $("notice-title").textContent = notice.title;
  $("notice-text").textContent = notice.content[state.language].text;
  $("notice-version").textContent = `V${notice.version}`;
  $("published-at").textContent = `Published ${date(notice.published_at)}`;
  $("published-by").textContent = `By ${notice.published_by}`;
  for (const lang of ["en", "es"])
    $("notice-" + lang).setAttribute(
      "aria-pressed",
      String(lang === state.language),
    );
}
function renderPeople() {
  const search = $("search").value.trim().toLocaleLowerCase();
  const records = state.data.records
    .filter((record) => {
      const followup =
        record.missing.length > 0 ||
        (record.assistance && record.assistance.status !== "completed");
      return (
        record.resident.name.toLocaleLowerCase().includes(search) &&
        (state.filter !== "followup" || followup) &&
        (state.filter !== "assistance" ||
          (record.assistance && record.assistance.status !== "completed"))
      );
    })
    .sort((a, b) => a.resident.name.localeCompare(b.resident.name));
  $("people").replaceChildren();
  $("table-empty").hidden = records.length > 0;
  for (const record of records) {
    const row = el("tr");
    row.dataset.record = record.record_id;
    const nameCell = el("td");
    const person = el("div", "person");
    const initials = record.resident.name
      .replace(/\(.*\)/, "")
      .trim()
      .split(" ")
      .slice(0, 2)
      .map((n) => n[0])
      .join("");
    person.append(el("span", `avatar ${record.resident.language}`, initials));
    const name = el("div");
    name.append(
      el("strong", "", record.resident.name),
      el(
        "small",
        "",
        record.resident.language === "es" ? "Español" : "English",
      ),
    );
    person.append(name);
    nameCell.append(person);
    const communication = el("td");
    communication.dataset.label = "Latest instruction";
    communication.append(badge(...labels[record.communication_status]));
    if (record.confirmed_version)
      communication.append(
        el(
          "span",
          "subtext",
          record.confirmed_version === record.notice.version
            ? `Confirmed V${record.confirmed_version}`
            : `Earlier confirmation: V${record.confirmed_version}`,
        ),
      );
    const help = el("td");
    help.dataset.label = "Assistance";
    if (record.assistance) {
      help.append(badge(...taskLabels[record.assistance.status]));
      if (record.assistance.owner)
        help.append(el("span", "subtext", record.assistance.owner));
    } else if (record.draft.assistance_needed) {
      help.append(badge("Request not yet confirmed", "updated"));
    } else
      help.append(
        el(
          "span",
          "subtext",
          record.draft.assistance_needed === false
            ? "No assistance requested"
            : "Not yet asked",
        ),
      );
    const contact = el("td", "contact-time", date(record.last_attempt_at));
    contact.dataset.label = "Last contact";
    const details = el("td");
    const button = el("button", "table-link", "View record ↗");
    button.setAttribute("aria-label", `View ${record.resident.name} record`);
    action(button, () => openRecord(record.record_id));
    details.append(button);
    row.append(nameCell, communication, help, contact, details);
    $("people").append(row);
  }
}
function render() {
  const { data } = state;
  $("login").hidden = true;
  $("empty").hidden = Boolean(data.notice);
  $("dashboard").hidden = !data.notice;
  $("add-resident").hidden = !data.notice;
  if (!data.notice) return;
  $("scenario-banner").hidden = data.notice.source !== "synthetic";
  renderNotice();
  const counts = data.counts;
  $("confirmed-count").textContent = counts.confirmed_current;
  $("updated-count").textContent = counts.updated_pending;
  $("assistance-count").textContent = counts.assistance_open;
  $("no-response-count").textContent = counts.no_response;
  $("resident-total").textContent = `of ${counts.residents} residents`;
  $("people-count").textContent = counts.residents;
  $("confirmation-meter").style.width =
    `${counts.residents ? (100 * counts.confirmed_current) / counts.residents : 0}%`;
  renderPeople();
  $("versions").replaceChildren();
  for (const version of data.versions) {
    const item = el("article", "timeline-item");
    item.append(el("span", "timeline-number", version.version));
    const body = el("div");
    const title = el("div", "timeline-title");
    title.append(el("strong", "", `Version ${version.version}`));
    if (version.version === data.notice.version)
      title.append(el("span", "version-pill", "CURRENT"));
    body.append(
      title,
      el("p", "", version.content[state.language].text),
      el(
        "small",
        "",
        `${version.reason} · ${version.published_by} · ${date(version.published_at)}`,
      ),
    );
    item.append(body);
    $("versions").append(item);
  }
}
async function refresh(quiet = false) {
  if (!state.token || state.loading) return;
  state.loading = true;
  try {
    state.data = await api("/dashboard");
    render();
    $("connection").textContent = "Live workspace";
    $("connection").className = "connection connected";
  } catch (error) {
    $("connection").textContent = "Connection paused";
    $("connection").className = "connection offline";
    if (!quiet || !state.data)
      message(error.message || "Could not connect. Please try again.", true);
  } finally {
    state.loading = false;
  }
}
async function openRecord(id, updateOnly = false) {
  const record = await api(`/records/${id}`);
  state.detail = id;
  $("record-name").textContent = record.resident.name;
  const body = $("record-body");
  body.replaceChildren();
  const source = state.data.records.find((r) => r.record_id === id);
  const linkRow = el("div", "record-link");
  linkRow.append(
    el(
      "p",
      "",
      "Share this private link only with this resident. It opens the same record in either language.",
    ),
  );
  const link = el("a", "button secondary", "Open response form ↗");
  link.href = source.response_url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  const copy = el("button", "text-button", "Copy link");
  action(copy, async () => {
    await navigator.clipboard.writeText(
      new URL(source.response_url, location.origin).href,
    );
    copy.textContent = "Copied";
  });
  linkRow.append(link, copy);
  body.append(linkRow);
  const communication = el("section", "detail-block");
  communication.append(
    el("h3", "", "Instruction confirmation"),
    badge(...labels[record.communication_status]),
  );
  communication.append(
    el(
      "p",
      "",
      record.confirmed_next_step
        ? `V${record.notice.version}: “${record.confirmed_next_step}”`
        : `Version ${record.notice.version} still needs confirmation.`,
    ),
  );
  if (record.missing.length)
    communication.append(
      el(
        "p",
        "",
        `Still needed: ${record.missing.map((s) => s.replaceAll("_", " ")).join(", ")}.`,
      ),
    );
  body.append(communication);
  const assistance = el("section", "detail-block");
  assistance.append(el("h3", "", "Assistance is a separate commitment"));
  const task = record.assistance;
  if (task) {
    assistance.append(
      badge(...taskLabels[task.status]),
      el("p", "", task.details),
    );
    if (task.owner) assistance.append(el("p", "", `Owner: ${task.owner}`));
    if (task.status !== "completed") {
      const ownerLabel = el("label", "owner-field", "Coordinator name");
      ownerLabel.style.display = "flex";
      ownerLabel.style.marginTop = "14px";
      const ownerInput = el("input");
      ownerInput.value = $("owner").value;
      ownerInput.setAttribute("aria-label", "Assistance coordinator name");
      ownerInput.maxLength = 80;
      ownerInput.addEventListener("change", () => {
        $("owner").value = ownerInput.value;
        sessionStorage.setItem("relay-owner", ownerInput.value);
      });
      ownerLabel.append(ownerInput);
      assistance.append(ownerLabel);
      const button = el(
        "button",
        "button primary",
        task.status === "requested"
          ? "Accept assistance request"
          : "Record assistance completed",
      );
      action(button, async () => {
        if (ownerInput.value.trim().length < 2)
          throw new Error(
            "Enter your coordinator name before accepting or completing a request.",
          );
        await mutate(`/assistance/${task.id}/decision`, {
          action: task.status === "requested" ? "accept" : "complete",
          expected_revision: task.revision,
          owner: ownerInput.value.trim(),
        });
        await refresh();
        await openRecord(id, true);
      });
      const actions = el("div", "button-row");
      actions.append(button);
      assistance.append(actions);
    }
  } else
    assistance.append(
      el(
        "p",
        "detail-empty",
        record.draft.assistance_needed
          ? "The assistance draft is saved. The resident still needs to confirm the readback before a task is created."
          : record.draft.assistance_needed === false
            ? "The resident has not requested assistance."
            : "Assistance needs have not been recorded yet.",
      ),
    );
  body.append(assistance);
  const history = el("section", "detail-block");
  history.append(el("h3", "", "Confirmation history"));
  if (!record.confirmation_history.length)
    history.append(el("p", "", "No instruction has been confirmed yet."));
  for (const item of record.confirmation_history)
    history.append(
      el(
        "p",
        "",
        `V${item.version} · “${item.next_step}” · ${item.channel} · ${date(item.confirmed_at)}`,
      ),
    );
  body.append(history);
  const attempt = el("section", "detail-block");
  attempt.append(
    el("h3", "", "Record a contact attempt"),
    el(
      "p",
      "",
      "An unanswered or interrupted call leaves the instruction unconfirmed.",
    ),
  );
  const controls = el("div", "inline-select");
  const select = el("select");
  select.setAttribute("aria-label", "Contact result");
  for (const [value, text] of [
    ["no_answer", "No answer"],
    ["disconnected", "Conversation disconnected"],
    ["contacted", "Reached, response pending"],
  ]) {
    const option = el("option", "", text);
    option.value = value;
    select.append(option);
  }
  const save = el("button", "button secondary", "Save attempt");
  action(save, async () => {
    await mutate(`/records/${id}/attempts`, { result: select.value });
    await refresh();
    await openRecord(id, true);
  });
  controls.append(select, save);
  attempt.append(controls);
  body.append(attempt);
  const events = el("section", "detail-block");
  events.append(el("h3", "", "Record activity"));
  const list = el("ul", "detail-events");
  for (const event of record.events) {
    const item = el(
      "li",
      "",
      `${eventLabels[event.type] || event.type.replaceAll("_", " ")} · V${event.version}`,
    );
    item.append(el("small", "", date(event.ts)));
    const detail =
      event.detail.next_step ||
      event.detail.details ||
      event.detail.owner ||
      event.detail.response;
    if (detail) item.append(el("p", "", detail));
    list.append(item);
  }
  if (!list.children.length)
    list.append(
      el("li", "", "Activity will appear as conversations progress."),
    );
  events.append(list);
  body.append(events);
  if (!updateOnly) showDialog("record-dialog");
}
function publishDialog() {
  const form = $("publish-form");
  form.reset();
  const notice = state.data?.notice;
  $("publish-title").textContent = notice
    ? "Publish an updated notice"
    : "Publish your first notice";
  $("publish-submit").textContent = notice
    ? "Publish update"
    : "Publish notice";
  form.elements.title.value = notice?.title || "Community shuttle pickup";
  for (const lang of ["en", "es"]) {
    form.elements[`${lang}_text`].value = notice?.content[lang].text || "";
    form.elements[`${lang}_question`].value =
      notice?.content[lang].question ||
      (lang === "en" ? "Which entrance will you use?" : "¿Qué entrada usarás?");
    form.elements[`${lang}_step`].value =
      notice?.content[lang].next_steps.join(" | ") || "";
  }
  form.dataset.expectedVersion = notice?.version || 0;
  form.dataset.noticeId = notice?.id || "";
  showDialog("publish-dialog");
}
$("login").addEventListener("submit", async (event) => {
  event.preventDefault();
  state.token = $("operator-token").value.trim();
  sessionStorage.setItem("relay-operator", state.token);
  $("operator-token").value = "";
  message("");
  await refresh();
});
$("owner").value = sessionStorage.getItem("relay-owner") || "Coordinator";
$("owner").addEventListener("change", () =>
  sessionStorage.setItem("relay-owner", $("owner").value),
);
$("publish-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = $("publish-submit");
  button.disabled = true;
  try {
    const content = {};
    for (const lang of ["en", "es"])
      content[lang] = {
        text: form.elements[`${lang}_text`].value.trim(),
        question: form.elements[`${lang}_question`].value.trim(),
        next_steps: form.elements[`${lang}_step`].value
          .split("|")
          .map((s) => s.trim())
          .filter(Boolean),
      };
    const result = await mutate(
      form.dataset.noticeId
        ? `/notices/${form.dataset.noticeId}/publish`
        : "/notices",
      {
        expected_version: Number(form.dataset.expectedVersion),
        title: form.elements.title.value.trim(),
        reason: form.elements.reason.value.trim(),
        published_by: $("owner").value.trim(),
        content,
      },
    );
    $("publish-dialog").close();
    message(
      `Version ${result.published_version} published. Earlier confirmations are preserved; the updated instruction needs a fresh confirmation.`,
    );
    await refresh();
  } catch (error) {
    message(error.message || "Could not publish. Please try again.", true);
  } finally {
    button.disabled = false;
  }
});
$("resident-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector("button[type=submit],button:not([type])");
  button.disabled = true;
  try {
    await mutate("/residents", {
      name: form.elements.name.value.trim(),
      language: form.elements.language.value,
      opt_in: form.elements.opt_in.checked,
    });
    $("resident-dialog").close();
    form.reset();
    await refresh();
    message(
      "Resident added. Their private response link is available in View record.",
    );
  } catch (error) {
    message(
      error.message || "Could not add the resident. Please try again.",
      true,
    );
  } finally {
    button.disabled = false;
  }
});
document
  .querySelectorAll("[data-close]")
  .forEach((button) =>
    button.addEventListener("click", () => $(button.dataset.close).close()),
  );
document.querySelectorAll("[data-filter]").forEach((button) =>
  button.addEventListener("click", () => {
    state.filter = button.dataset.filter;
    document
      .querySelectorAll("[data-filter]")
      .forEach((b) => b.classList.toggle("selected", b === button));
    renderPeople();
  }),
);
for (const lang of ["en", "es"])
  $("notice-" + lang).addEventListener("click", () => {
    state.language = lang;
    render();
  });
$("search").addEventListener("input", renderPeople);
action($("refresh"), () => refresh());
action($("load-demo"), async () => {
  await api("/demo", {});
  message("");
  await refresh();
});
$("create-notice").addEventListener("click", publishDialog);
$("revise-notice").addEventListener("click", publishDialog);
$("add-resident").addEventListener("click", () =>
  showDialog("resident-dialog"),
);
if (state.token) await refresh();
else {
  $("login").hidden = false;
  $("connection").textContent = "Private workspace";
}
setInterval(() => {
  if (!document.hidden && !document.querySelector("dialog[open]"))
    refresh(true);
}, 4000);
window.addEventListener("online", () => refresh(true));
