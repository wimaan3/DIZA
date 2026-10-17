// Only the resident's own notice and unsent draft are retained on this device.
const opened = new Promise((resolve, reject) => {
  const request = indexedDB.open("relayla-resident", 1);
  request.onupgradeneeded = () => {
    for (const name of ["drafts", "contexts"])
      request.result.createObjectStore(name);
  };
  request.onsuccess = () => resolve(request.result);
  request.onerror = () => reject(request.error);
});
export async function localGet(store, key) {
  const db = await opened;
  return new Promise((resolve, reject) => {
    const request = db.transaction(store).objectStore(store).get(key);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
export async function localPut(store, key, value) {
  const db = await opened;
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(store, "readwrite");
    transaction.objectStore(store).put(value, key);
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
    transaction.onabort = () => reject(transaction.error);
  });
}
export async function localDelete(store, key) {
  const db = await opened;
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(store, "readwrite");
    transaction.objectStore(store).delete(key);
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
    transaction.onabort = () => reject(transaction.error);
  });
}
