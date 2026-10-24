import { localGet, localPut, localDelete } from "./local.js";

const $ = (id) => document.getElementById(id);
const recordId = location.pathname.split("/")[2] || "";
const tokenKey = `relay-resident-${recordId}`;
const token = location.hash.slice(1) || sessionStorage.getItem(tokenKey) || "";
if (token) sessionStorage.setItem(tokenKey, token);
const cacheKey = `${recordId}:${token}`;
const state = {
  language: "en",
  context: null,
  draft: null,
  syncing: false,
  local: true,
  dirty: false,
  call: null,
  attempt: null,
  voiceStarting: false,
  voiceFinishing: false,
};
const strings = {
  en: {
    "resident-eyebrow": "YOUR COMMUNITY. YOUR NEXT STEP.",
    greeting: "Let’s make the next step clear.",
    "resident-intro":
      "Confirm the instruction and let your coordinator know if you need a hand.",
    "approved-label": "APPROVED COMMUNITY NOTICE",
    "resident-scenario": "SCENARIO DATA · SYNTHETIC RESIDENT",
    "voice-heading": "Prefer to talk it through?",
    "voice-copy":
      "Speak with RelayLA in English or Spanish. Your saved progress stays with this record.",
    "voice-consent-label":
      "I agree to start a voice conversation. It may be recorded by the service.",
    "start-voice": "Start voice conversation",
    "end-voice": "End conversation",
    "text-eyebrow": "OR RESPOND HERE",
    "response-heading": "A short response makes a difference.",
    "clarification-label": "I need someone to clarify this instruction.",
    "assistance-question": "Do you need help getting to the pickup point?",
    "assistance-no": "No assistance needed",
    "assistance-yes": "Yes, I need a hand",
    "assistance-details-label": "What would help?",
    "readback-label": "Your assistance request",
    "confirm-assistance-label": "That matches the help I need.",
    "offline-explanation":
      "Your draft stays on this device until it reaches the server. A local draft is not a sent response.",
    "send-response": "Save my response",
    "save-draft": "Save progress",
    "resident-footer":
      "Your instruction confirmation and assistance request are separate. A coordinator must accept a request before anyone owns it.",
    notSent: "Not sent",
    sent: "Saved to your record",
    waiting:
      "Not sent. Your response is saved on this device and will be sent when the connection returns.",
    offline:
      "You’re offline. The previously loaded notice and your draft are available on this device. Voice requires a connection.",
    updated:
      "Your response was saved to its original notice version. The notice has changed. Please confirm the updated instruction below.",
    saved: "Your response reached the coordinator’s record.",
    progress:
      "Your progress is saved. Unconfirmed details still need your confirmation.",
    missingStep:
      "Please give your next step or select that you need clarification.",
    missingHelp: "Please choose whether you need assistance.",
    missingDetails: "Please describe the assistance you need.",
    missingReadback:
      "Please confirm that the assistance readback matches what you need, or use Save progress.",
    summary: "What’s saved so far",
    current: "Latest instruction confirmed",
    pending: "Latest instruction still needs confirmation",
    clarify: "A coordinator needs to clarify the instruction",
    task: "Assistance requested; awaiting an owner",
    accepted: "Assistance accepted by",
    completed: "Assistance completed by",
    helpDraft: "Assistance details saved; your confirmation is still needed.",
    helpUnknown: "We still need to ask whether you need assistance.",
    noHelp: "No assistance requested.",
    voiceUnavailable:
      "Voice is not configured yet. You can use the response form below.",
    voiceConsent: "Please agree to start a voice conversation first.",
    voiceConnecting: "Connecting…",
    voiceLive: "Conversation connected",
    voiceEnded: "Conversation ended. Saved details remain in your record.",
    voiceError: "Voice could not connect. Use the response form or try again.",
    invalid: "Open the private response link supplied by your coordinator.",
    localError:
      "This browser could not retain a local draft. Keep this page open and send your response while connected.",
    failed:
      "The response has not been confirmed by the server. Your draft stays here; retry when connected.",
    newer:
      "A newer notice is available. Your unsent response still belongs to the version shown below.",
    retry: "Retry sending",
    nextPlaceholder: "Write the entrance you will use",
    helpPlaceholder: "I use a walker and need help reaching the entrance.",
  },
  es: {
    "resident-eyebrow": "TU COMUNIDAD. TU PRÓXIMO PASO.",
    greeting: "Aclaremos el próximo paso.",
    "resident-intro":
      "Confirma la instrucción y avisa a tu coordinador si necesitas ayuda.",
    "approved-label": "AVISO APROBADO DE LA COMUNIDAD",
    "resident-scenario": "DATOS DE DEMOSTRACIÓN · RESIDENTE FICTICIO",
    "voice-heading": "¿Prefieres hablar?",
    "voice-copy":
      "Habla con RelayLA en español o inglés. Tu progreso guardado permanece en este registro.",
    "voice-consent-label":
      "Acepto iniciar una conversación de voz. El servicio puede grabarla.",
    "start-voice": "Iniciar conversación de voz",
    "end-voice": "Terminar conversación",
    "text-eyebrow": "O RESPONDE AQUÍ",
    "response-heading": "Una respuesta breve ayuda mucho.",
    "clarification-label": "Necesito que alguien aclare esta instrucción.",
    "assistance-question": "¿Necesitas ayuda para llegar al punto de recogida?",
    "assistance-no": "No necesito ayuda",
    "assistance-yes": "Sí, necesito ayuda",
    "assistance-details-label": "¿Qué ayuda necesitas?",
    "readback-label": "Tu solicitud de ayuda",
    "confirm-assistance-label": "Esto describe la ayuda que necesito.",
    "offline-explanation":
      "Tu borrador permanece en este dispositivo hasta que llegue al servidor. Un borrador local no es una respuesta enviada.",
    "send-response": "Guardar mi respuesta",
    "save-draft": "Guardar progreso",
    "resident-footer":
      "Tu confirmación y tu solicitud de ayuda son independientes. Un coordinador debe aceptar la solicitud para hacerse cargo.",
    notSent: "Sin enviar",
    sent: "Guardado en tu registro",
    waiting:
      "Sin enviar. Tu respuesta está guardada en este dispositivo y se enviará cuando vuelva la conexión.",
    offline:
      "No tienes conexión. El aviso cargado y tu borrador están disponibles en este dispositivo. La voz necesita conexión.",
    updated:
      "Tu respuesta se guardó con la versión original del aviso. El aviso cambió. Confirma la nueva instrucción a continuación.",
    saved: "Tu respuesta llegó al registro del coordinador.",
    progress:
      "Tu progreso está guardado. Los datos sin confirmar aún necesitan tu confirmación.",
    missingStep:
      "Escribe tu próximo paso o indica que necesitas una aclaración.",
    missingHelp: "Indica si necesitas ayuda.",
    missingDetails: "Describe la ayuda que necesitas.",
    missingReadback:
      "Confirma que el resumen describe la ayuda que necesitas, o elige Guardar progreso.",
    summary: "Lo que ya está guardado",
    current: "Última instrucción confirmada",
    pending: "La última instrucción aún necesita confirmación",
    clarify: "Un coordinador debe aclarar la instrucción",
    task: "Ayuda solicitada; esperando responsable",
    accepted: "Ayuda aceptada por",
    completed: "Ayuda completada por",
    helpDraft: "La ayuda está guardada; aún falta tu confirmación.",
    helpUnknown: "Aún necesitamos saber si necesitas ayuda.",
    noHelp: "No se ha solicitado ayuda.",
    voiceUnavailable:
      "La voz aún no está configurada. Puedes usar el formulario de abajo.",
    voiceConsent: "Acepta iniciar una conversación de voz primero.",
    voiceConnecting: "Conectando…",
    voiceLive: "Conversación conectada",
    voiceEnded:
      "La conversación terminó. Los datos guardados permanecen en tu registro.",
    voiceError:
      "La voz no pudo conectar. Usa el formulario o inténtalo de nuevo.",
    invalid: "Abre el enlace privado que te proporcionó tu coordinador.",
    localError:
      "Este navegador no pudo guardar un borrador local. Mantén la página abierta y envía tu respuesta con conexión.",
    failed:
      "El servidor no ha confirmado la respuesta. Tu borrador permanece aquí; reintenta cuando tengas conexión.",
    newer:
      "Hay un aviso nuevo. Tu respuesta sin enviar aún corresponde a la versión de abajo.",
    retry: "Reintentar envío",
    nextPlaceholder: "Escribe la entrada que usarás",
    helpPlaceholder:
      "Uso un andador y necesito ayuda para llegar a la entrada.",
  },
};
const t = (key) => strings[state.language][key];
function message(text, error = false) {
  $("resident-message").textContent = text;
  $("resident-message").classList.toggle("error", error);
  $("resident-message").hidden = !text;
}
function readFields() {
  const help = document.querySelector(
    'input[name="assistance"]:checked',
  )?.value;
  return {
    next_step: $("next-step").value,
    needs_clarification: $("clarification").checked,
    assistance_needed: help ? help === "yes" : null,
    assistance_details: $("assistance-details").value,
    confirm_assistance: $("confirm-assistance").checked,
  };
}
function restoreFields() {
  const fields = state.draft.fields;
  $("next-step").value = fields.next_step;
  $("clarification").checked = fields.needs_clarification;
  document.querySelectorAll('input[name="assistance"]').forEach((radio) => {
    radio.checked =
      fields.assistance_needed !== null &&
      (radio.value === "yes") === fields.assistance_needed;
  });
  $("assistance-details").value = fields.assistance_details;
  $("confirm-assistance").checked = fields.confirm_assistance;
  assistanceFields();
}
function assistanceFields() {
  $("assistance-fields").hidden =
    document.querySelector('input[name="assistance"]:checked')?.value !== "yes";
  $("readback").textContent =
    $("assistance-details").value ||
    (state.language === "es"
      ? "Tu descripción aparecerá aquí."
      : "Your description will appear here.");
}
function resetDraft(context) {
  const same = context.draft.notice_version === context.notice.version;
  state.draft = {
    notice: context.notice,
    fields: {
      next_step: same ? context.draft.next_step : "",
      needs_clarification:
        context.communication_status === "needs_clarification",
      assistance_needed: context.draft.assistance_needed,
      assistance_details: context.draft.assistance_details,
      confirm_assistance: context.draft.assistance_confirmed,
    },
    helpEdited: false,
    queued: null,
  };
  state.dirty = false;
}
async function persist() {
  if (!state.local) return;
  try {
    await localPut("drafts", cacheKey, {
      ...state.draft,
      dirty: state.dirty,
      language: state.language,
    });
  } catch {
    state.local = false;
    message(t("localError"), true);
  }
}
function summary() {
  const context = state.context;
  $("saved-summary").replaceChildren();
  const add = (tag, text, className = "") => {
    const node = document.createElement(tag);
    node.textContent = text;
    node.className = className;
    $("saved-summary").append(node);
  };
  $("saved-summary").hidden =
    !context.confirmed_version &&
    context.draft.assistance_needed === null &&
    context.communication_status !== "needs_clarification";
  add("h2", t("summary"));
  const confirmed = context.communication_status === "confirmed_current";
  add(
    "span",
    t(
      confirmed
        ? "current"
        : context.communication_status === "needs_clarification"
          ? "clarify"
          : "pending",
    ),
    `status ${confirmed ? "confirmed" : "updated"}`,
  );
  for (const item of context.confirmation_history)
    add("p", `V${item.version}: “${item.next_step}”`);
  const task = context.assistance;
  if (task)
    add(
      "p",
      task.status === "requested"
        ? t("task")
        : `${t(task.status === "accepted" ? "accepted" : "completed")} ${task.owner}.`,
    );
  else
    add(
      "p",
      t(
        context.draft.assistance_needed
          ? "helpDraft"
          : context.draft.assistance_needed === false
            ? "noHelp"
            : "helpUnknown",
      ),
    );
  if (task) add("p", task.details);
}
function render() {
  document.documentElement.lang = state.language;
  for (const id of [
    "resident-eyebrow",
    "greeting",
    "resident-intro",
    "approved-label",
    "resident-scenario",
    "voice-heading",
    "voice-copy",
    "voice-consent-label",
    "start-voice",
    "end-voice",
    "text-eyebrow",
    "response-heading",
    "clarification-label",
    "assistance-question",
    "assistance-no",
    "assistance-yes",
    "assistance-details-label",
    "readback-label",
    "confirm-assistance-label",
    "offline-explanation",
    "send-response",
    "save-draft",
    "resident-footer",
  ])
    $(id).textContent = t(id);
  for (const lang of ["en", "es"])
    $("lang-" + lang).setAttribute(
      "aria-pressed",
      String(lang === state.language),
    );
  if (!state.context) return;
  $("resident-content").hidden = false;
  const notice = state.draft.notice;
  $("resident-version").textContent = `V${notice.version}`;
  $("resident-notice-title").textContent = notice.title;
  $("resident-notice-text").textContent = notice.content[state.language].text;
  $("step-question").textContent = notice.content[state.language].question;
  $("next-step").placeholder = t("nextPlaceholder");
  $("assistance-details").placeholder = t("helpPlaceholder");
  $("resident-scenario").hidden = state.context.resident.source !== "synthetic";
  const saved =
    !state.dirty &&
    !state.draft.queued &&
    (state.context.confirmed_version ||
      state.context.draft.next_step ||
      state.context.draft.assistance_needed !== null);
  $("draft-status").textContent = t(saved ? "sent" : "notSent");
  $("draft-status").classList.toggle("sent", Boolean(saved));
  const voiceAvailable =
    state.context.voice_available && navigator.onLine && !state.draft.queued;
  $("start-voice").disabled = !voiceAvailable || state.voiceStarting;
  $("start-voice").hidden = Boolean(state.call);
  $("end-voice").hidden = !state.call;
  $("voice-consent").disabled = Boolean(state.call) || state.voiceStarting;
  if (!state.context.voice_available)
    $("voice-status").textContent = t("voiceUnavailable");
  $("send-response").disabled = state.syncing;
  $("save-draft").disabled = state.syncing;
  $("response-form")
    .querySelectorAll("input,textarea")
    .forEach((node) => {
      node.disabled = state.syncing;
    });
  if (state.draft.queued) $("send-response").textContent = t("retry");
  assistanceFields();
  summary();
}
async function api(path, body, raw = false) {
  const response = await fetch(`/api/relay/resident/${recordId}${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      "X-Relay-Token": token,
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    cache: "no-store",
    signal: AbortSignal.timeout(22000),
  });
  if (!response.ok) {
    const data = await response.json();
    const error = new Error(
      typeof data.detail === "string" ? data.detail : t("failed"),
    );
    error.status = response.status;
    throw error;
  }
  return raw ? response : response.json();
}
async function cacheContext(context) {
  state.context = context;
  if (state.local) {
    try {
      await localPut("contexts", cacheKey, context);
    } catch {
      state.local = false;
      message(t("localError"), true);
    }
  }
}
async function refresh() {
  if (!navigator.onLine || state.syncing || !state.context) return;
  try {
    const context = await api("/context");
    const old = state.context.notice.version;
    await cacheContext(context);
    if (!state.dirty && !state.draft.queued) {
      resetDraft(context);
      restoreFields();
      await persist();
    } else if (
      context.notice.version !== state.draft.notice.version &&
      old !== context.notice.version
    )
      message(t("newer"));
    render();
  } catch {
    /* Preserve the resident's current form during a temporary disconnect. */
  }
}
async function sync() {
  if (!state.draft.queued || state.syncing) return;
  if (!navigator.onLine) {
    message(t("waiting"));
    render();
    return;
  }
  state.syncing = true;
  render();
  const queued = state.draft.queued;
  try {
    const result = await api("/response", queued);
    await cacheContext({
      ...result.context,
      voice_available: state.context.voice_available,
    });
    resetDraft(state.context);
    restoreFields();
    await persist();
    message(
      t(
        result.stale
          ? "updated"
          : queued.confirm_instruction || queued.needs_clarification
            ? "saved"
            : "progress",
      ),
    );
  } catch (error) {
    if (error.status && error.status < 500) {
      state.draft.queued = null;
      await persist();
      message(error.message, true);
    } else message(t("failed"), true);
  } finally {
    state.syncing = false;
    render();
  }
}
async function submit(confirm) {
  if (state.syncing) return;
  if (state.draft.queued) {
    await sync();
    return;
  }
  const fields = readFields();
  if (confirm && !fields.next_step.trim() && !fields.needs_clarification) {
    message(t("missingStep"), true);
    $("next-step").focus();
    return;
  }
  if (confirm && fields.assistance_needed === null) {
    message(t("missingHelp"), true);
    document.querySelector('input[name="assistance"]').focus();
    return;
  }
  if (fields.assistance_needed && !fields.assistance_details.trim()) {
    message(t("missingDetails"), true);
    $("assistance-details").focus();
    return;
  }
  if (
    confirm &&
    fields.assistance_needed &&
    !fields.confirm_assistance &&
    state.draft.helpEdited
  ) {
    message(t("missingReadback"), true);
    $("confirm-assistance").focus();
    return;
  }
  state.draft.fields = fields;
  state.draft.queued = {
    idempotency_key: crypto.randomUUID(),
    notice_version: state.draft.notice.version,
    next_step: fields.next_step.trim(),
    needs_clarification: fields.needs_clarification,
    confirm_instruction:
      confirm &&
      !fields.needs_clarification &&
      Boolean(fields.next_step.trim()),
    assistance_needed: state.draft.helpEdited ? fields.assistance_needed : null,
    assistance_details: fields.assistance_details.trim(),
    confirm_assistance: confirm && fields.confirm_assistance,
  };
  state.dirty = true;
  await persist();
  render();
  await sync();
}
$("response-form").addEventListener("input", async (event) => {
  if (!state.draft || state.syncing) return;
  if (
    ["assistance-details", "confirm-assistance"].includes(event.target.id) ||
    event.target.name === "assistance"
  )
    state.draft.helpEdited = true;
  if (event.target.id === "assistance-details")
    $("confirm-assistance").checked = false;
  state.draft.fields = readFields();
  state.draft.queued = null;
  state.dirty = true;
  assistanceFields();
  render();
  await persist();
});
$("response-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  await submit(true);
});
$("save-draft").addEventListener("click", () => submit(false));
for (const lang of ["en", "es"])
  $("lang-" + lang).addEventListener("click", async () => {
    state.language = lang;
    render();
    if (state.draft) {
      await persist();
      if (!navigator.onLine)
        message(t(state.draft.queued ? "waiting" : "offline"));
    }
  });
async function finishVoice() {
  if (state.voiceFinishing) return;
  state.voiceFinishing = true;
  try {
    if (state.attempt) await api(`/voice/${state.attempt}/end`, {});
  } catch {
    /* The signed provider webhook also closes disconnected calls. */
  } finally {
    state.call = null;
    state.attempt = null;
    state.voiceStarting = false;
    state.voiceFinishing = false;
    $("voice-status").textContent = t("voiceEnded");
    await refresh();
    render();
  }
}
$("start-voice").addEventListener("click", async () => {
  if (!$("voice-consent").checked) {
    message(t("voiceConsent"), true);
    return;
  }
  if (state.dirty) {
    message(
      state.language === "es"
        ? "Guarda tu respuesta o progreso antes de iniciar la voz."
        : "Save your response or progress before starting voice.",
      true,
    );
    return;
  }
  state.voiceStarting = true;
  render();
  $("voice-status").textContent = t("voiceConnecting");
  try {
    const { voiceClient } = await import("./voice-sdk.js");
    const requestKey = crypto.randomUUID();
    const client = voiceClient(async () => {
      const response = await api(
        "/voice",
        {
          idempotency_key: requestKey,
          language: state.language,
          consent_to_voice: true,
        },
        true,
      );
      const result = await response.clone().json();
      state.attempt = result.attempt_id;
      return response;
    });
    state.call = client.createWebCall({
      agent_id: "configured-on-server",
      transcript: false,
      hooks: {
        onStatus: (status) => {
          if (status === "live") $("voice-status").textContent = t("voiceLive");
        },
        onEnd: finishVoice,
        onError: () => {
          message(t("voiceError"), true);
          finishVoice();
        },
      },
    });
    await state.call.ready;
    state.voiceStarting = false;
    render();
  } catch (error) {
    message(error.status ? error.message : t("voiceError"), true);
    await finishVoice();
  }
});
$("end-voice").addEventListener("click", async () => {
  await state.call?.end();
  await finishVoice();
});
window.addEventListener("offline", () => {
  message(t(state.draft?.queued ? "waiting" : "offline"));
  render();
});
window.addEventListener("online", async () => {
  if (state.draft?.queued) await sync();
  else await refresh();
});
window.addEventListener("pagehide", () => {
  state.call?.disconnect();
});
setInterval(() => {
  if (!document.hidden) {
    if (state.draft?.queued) sync();
    else refresh();
  }
}, 5000);
async function boot() {
  render();
  if (!/^[a-f0-9]{32}$/.test(recordId) || !/^[a-f0-9]{64}$/.test(token)) {
    message(t("invalid"), true);
    return;
  }
  let cached, draft;
  try {
    [cached, draft] = await Promise.all([
      localGet("contexts", cacheKey),
      localGet("drafts", cacheKey),
    ]);
  } catch {
    state.local = false;
  }
  try {
    await cacheContext(await api("/context"));
  } catch (error) {
    if (!cached || (error.status && error.status < 500)) {
      message(error.status ? error.message : t("invalid"), true);
      return;
    }
    state.context = cached;
  }
  state.language = draft?.language || state.context.resident.language;
  if (draft?.dirty || draft?.queued) {
    state.draft = draft;
    state.dirty = true;
  } else resetDraft(state.context);
  restoreFields();
  render();
  if (!navigator.onLine) message(t(state.draft.queued ? "waiting" : "offline"));
  else if (state.draft.queued) await sync();
  else if (state.draft.notice.version !== state.context.notice.version)
    message(t("newer"));
  else message(state.local ? "" : t("localError"), !state.local);
  if ("serviceWorker" in navigator) {
    try {
      await navigator.serviceWorker.register("/relay-sw.js", {
        scope: "/respond",
      });
    } catch {
      /* Drafts still persist; an offline reload needs the cached page shell. */
    }
  }
}
await boot();
