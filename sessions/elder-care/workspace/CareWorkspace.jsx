import {residentRequestCounts} from "../web/building.js";
import React, { useEffect, useRef, useState } from "react";

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
  const urgent = data ? residentRequestCounts(data).urgent : 0;
  return !unavailable && urgent > 0
    ? <span className="care-urgent-count" aria-label={`${urgent} urgent resident requests`}>{urgent}</span>
    : null;
}

export function CareWorkspace({view = "daily"}) {
  const frame = useRef(null);
  useEffect(() => {
    function resize() {
      const element = frame.current;
      if (!element || !element.getBoundingClientRect().width) return;
      const top = Math.max(0, element.getBoundingClientRect().top);
      element.style.height = `${Math.max(240, window.innerHeight - top)}px`;
    }
    // The actual space differs on mobile as the sidebar and header
    // wrap. Keep dialogs inside the visible frame rather than below the screen.
    const observer = new ResizeObserver(resize);
    observer.observe(frame.current.parentElement.parentElement);
    window.addEventListener("resize", resize);
    window.addEventListener("scroll", resize, {passive:true});
    resize();
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", resize);
      window.removeEventListener("scroll", resize);
    };
  }, []);
  // Same-origin isolation preserves the care UI, dialogs, keyboard handling and
  // accessibility without allowing its styles to overwrite the operations map.
  return <iframe ref={frame} className="care-workspace" title={view === "building" ? "Building workspace" : "Resident care workspace"}
    src={`/care/workspace?embedded=1&view=${encodeURIComponent(view)}`}/>;
}
