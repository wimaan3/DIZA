const CACHE = "relayla-resident-shell-v1";
const ASSETS = [
  "/respond",
  "/relay/assets/relay.css",
  "/relay/assets/resident.js",
  "/relay/assets/local.js",
];
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(ASSETS))
      .then(() => self.skipWaiting()),
  );
});
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key.startsWith("relayla-") && key !== CACHE)
            .map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (
    event.request.method !== "GET" ||
    url.origin !== self.location.origin ||
    url.pathname.startsWith("/api/")
  )
    return;
  if (
    event.request.mode === "navigate" &&
    url.pathname.startsWith("/respond")
  ) {
    event.respondWith(
      fetch(event.request).catch(() => caches.match("/respond")),
    );
    return;
  }
  if (ASSETS.includes(url.pathname))
    event.respondWith(
      fetch(event.request).catch(() => caches.match(url.pathname)),
    );
});
