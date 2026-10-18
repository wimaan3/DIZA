import React, { useEffect, useState } from "react";

export function useCareData(headers) {
  const [data, setData] = useState(null);
  const [unavailable, setUnavailable] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    async function refresh() {
      try {
        const response = await fetch("/api/care/state", {
          headers, signal: controller.signal,
        });
        if (!response.ok) throw new Error("Care queue unavailable");
        const snapshot = await response.json();
        if (!controller.signal.aborted) { setData(snapshot); setUnavailable(false); }
      } catch {
        if (!controller.signal.aborted) setUnavailable(true);
      }
    }
    refresh();
    const timer = setInterval(refresh, 5000);
    return () => { clearInterval(timer); controller.abort(); };
  }, [headers.Authorization]);
  return {data, unavailable};
}

export function CareBadge({headers}) {
  const {data, unavailable} = useCareData(headers);
  const urgent = data?.requests.filter(
    (item) => item.urgency === "urgent" && item.status !== "resolved",
  ).length;
  return !unavailable && urgent > 0
    ? <span className="care-urgent-count" aria-label={`${urgent} urgent care requests`}>{urgent}</span>
    : null;
}

export function CareWorkspace({view = "daily"}) {
  // Same-origin isolation preserves the care UI, dialogs, keyboard handling and
  // accessibility without allowing its styles to overwrite the operations map.
  return <iframe className="care-workspace" title="Resident care workspace"
    src={`/care/workspace?embedded=1&view=${encodeURIComponent(view)}`}/>;
}
