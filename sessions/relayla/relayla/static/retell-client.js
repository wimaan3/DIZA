// Pinned optional SDK. It is fetched only after an operator starts live voice.
// All local dashboard, simulation and text paths work without this dependency.
const SDK_URL = 'https://esm.sh/retell-client-js-sdk@3.0.2?bundle';
let activeCall = null;
let starting = false;

export async function startRetellCall({ caseId, language, token = '', onStatus = () => {} }) {
  if (starting || (activeCall && activeCall.status !== 'ended')) {
    throw new Error('End the current browser call before starting another.');
  }
  starting = true;
  onStatus('connecting');
  try {
    const { RetellClient } = await import(SDK_URL);
    const endpoint = new URL('../api/retell/web-call', import.meta.url);
    const client = new RetellClient({
      key: 'server-managed',
      // This is a single allowlisted operation, not an unrestricted API proxy.
      // Agent IDs, metadata and context are selected again on our backend.
      fetch: async (url, init) => {
        if (new URL(String(url)).pathname !== '/v3/create-web-call' || init?.method !== 'POST') {
          throw new Error('This demo only permits creating its configured browser call.');
        }
        return fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...(token ? { 'X-Operator-Token': token } : {}) },
          body: JSON.stringify({ case_id: caseId, language }),
          credentials: 'same-origin',
        });
      },
    });
    activeCall = client.createWebCall({
      agent_id: 'configured-on-server',
      // Transcript monitoring requires a more privileged key. The dashboard
      // shows saved tool events instead; no server API key enters the browser.
      transcript: false,
      hooks: {
        onStatus,
        onEnd: () => onStatus('ended'),
        onError: () => onStatus('error'),
      },
    });
    await activeCall.ready;
    return activeCall;
  } catch (error) {
    if (activeCall && activeCall.status !== 'ended') {
      try { await activeCall.end(); } catch { /* original connection error wins */ }
    }
    activeCall = null;
    onStatus('error');
    throw new Error(error?.message || 'Live voice could not connect. Check Retell configuration, network and microphone permission.');
  } finally {
    starting = false;
  }
}

export async function endRetellCall() {
  if (activeCall) {
    const call = activeCall;
    activeCall = null;
    await call.end();
  }
}
