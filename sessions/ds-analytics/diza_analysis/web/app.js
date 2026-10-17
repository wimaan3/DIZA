"use strict";

const get = (id) => document.getElementById(id);
let token = sessionStorage.getItem("diza-token") || "";
let inFlight = false;
const languageNames = { en: "English", es: "Spanish", ko: "Korean", zh: "Chinese", hy: "Armenian", tl: "Tagalog", und: "Unknown" };
const formatRate = (rate) => rate && rate.value !== null ? `${Math.round(rate.value * 100)}%` : "Unmeasured";

function message(text, kind) {
  get("message").textContent = text;
  get("message").className = `notice ${kind || ""}`;
}

function bars(id, values, labels = {}) {
  const container = get(id);
  container.replaceChildren();
  const entries = Object.entries(values).filter(([, count]) => count > 0).sort((a, b) => b[1] - a[1]);
  if (!entries.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "Measurements will appear as consented calls are recorded.";
    container.append(empty);
    return;
  }
  const maximum = Math.max(...entries.map(([, count]) => count));
  for (const [name, count] of entries) {
    const row = document.createElement("div");
    const label = document.createElement("div");
    label.className = "bar-label";
    const title = document.createElement("span");
    title.textContent = labels[name] || name.replaceAll("_", " ");
    const number = document.createElement("strong");
    number.textContent = count;
    label.append(title, number);
    const track = document.createElement("div");
    track.className = "bar-track";
    const fill = document.createElement("span");
    fill.className = "bar-fill";
    fill.style.width = `${Math.max(0, Math.min(100, count / maximum * 100))}%`;
    track.append(fill);
    row.append(label, track);
    container.append(row);
  }
}

function render(data) {
  const m = data.metrics;
  get("calls").textContent = m.calls;
  get("peak").textContent = m.peak_concurrent === null ? "Unmeasured" : m.peak_concurrent;
  get("reach").textContent = formatRate(m.non_en_es);
  get("reach-detail").textContent = `${m.non_en_es.numerator} of ${m.non_en_es.denominator} calls with known language`;
  get("recall").textContent = formatRate(m.p0_recall);
  get("recorded").textContent = data.coverage.operational_calls;
  get("included").textContent = data.coverage.analytics_calls;
  get("unknown").textContent = data.coverage.missing_consent_link;
  get("opted-out").textContent = data.coverage.opted_out_calls;
  get("updated").textContent = `Updated ${new Date(m.as_of).toLocaleTimeString()}`;
  get("resolved").textContent = formatRate(m.ai_resolved_nonurgent);
  get("routing").textContent = formatRate(m.routing_match);
  get("safety").textContent = formatRate(m.safety_compliance);
  const delay = m.time_to_human.P1.median_seconds;
  get("human-time").textContent = delay === null ? "Unmeasured" : `${Math.round(delay)} seconds`;
  bars("categories", data.categories);
  bars("languages", data.languages, languageNames);
  bars("predictions", data.triage_predictions);
  get("dashboard").hidden = false;
  get("login").hidden = true;
  if (!data.configured) {
    message("Analytics needs a private key. Set DIZA_ANALYTICS_SALT in the deployment settings to enable collection.", "error");
  } else if (!m.calls) {
    message("Connected to live data. Analytics will appear after calls have a recorded consent link. Earlier calls remain excluded until consent can be verified.", "success");
  } else {
    message("Live analytics is connected. Metrics include consented calls; unobserved quality scores remain unmeasured.", "success");
  }
}

async function refresh() {
  if (inFlight) return;
  inFlight = true;
  get("refresh").disabled = true;
  try {
    const response = await fetch("/api/analytics", {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
    });
    if (response.status === 401) {
      get("login").hidden = false;
      get("dashboard").hidden = true;
      throw new Error(token ? "The operator token was not accepted." : "Enter the operator token to view analytics.");
    }
    if (!response.ok) throw new Error("Analytics is unavailable. Please try again.");
    const data = await response.json();
    render(data);
    get("connection-dot").classList.add("online");
    get("connection-label").textContent = "Live analytics connected";
  } catch (error) {
    get("connection-dot").classList.remove("online");
    get("connection-label").textContent = "Not connected";
    message(error.message || "Could not refresh analytics.", "error");
  } finally {
    inFlight = false;
    get("refresh").disabled = false;
  }
}

get("login").addEventListener("submit", (event) => {
  event.preventDefault();
  token = get("token").value;
  sessionStorage.setItem("diza-token", token);
  get("token").value = "";
  refresh();
});
get("refresh").addEventListener("click", refresh);
refresh();
setInterval(() => { if (!document.hidden) refresh(); }, 10000);
