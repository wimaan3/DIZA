import React, { useEffect, useState } from "react";
import { HeartHandshake } from "lucide-react";

export function CareNav({ headers }) {
  const [urgent, setUrgent] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    async function refresh() {
      try {
        const response = await fetch("/api/care/state", {
          headers, signal: controller.signal,
        });
        if (!response.ok) throw new Error("Care queue unavailable");
        const data = await response.json();
        setUrgent(data.requests.filter(
          (item) => item.urgency === "urgent" && item.status !== "resolved",
        ).length);
      } catch {
        if (!controller.signal.aborted) setUrgent(null);
      }
    }
    refresh();
    const timer = setInterval(refresh, 5000);
    return () => { clearInterval(timer); controller.abort(); };
  }, [headers.Authorization]);

  return <><HeartHandshake size={18}/><span>Resident care</span>
    {urgent > 0 && <span className="care-urgent-count" aria-label={`${urgent} urgent care requests`}>{urgent}</span>}
  </>;
}

export function CareWorkspace() {
  // Same-origin isolation preserves the care UI, dialogs, keyboard handling and
  // accessibility without allowing its styles to overwrite the operations map.
  return <iframe className="care-workspace" title="Resident care workspace"
    src="/care/workspace?embedded=1"/>;
}
