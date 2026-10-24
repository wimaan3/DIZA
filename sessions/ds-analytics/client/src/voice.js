import { RetellClient } from "retell-client-js-sdk";

export function voiceClient(createSession) {
  return new RetellClient({
    key: "server-managed",
    fetch: async (url, init) => {
      if (!new URL(String(url)).pathname.endsWith("/create-web-call")) {
        throw new Error("Unsupported voice operation");
      }
      return createSession();
    },
  });
}
