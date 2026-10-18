import React, {useRef, useState} from "react";
import {HeartHandshake, LayoutGrid} from "lucide-react";
import OriginalBuilding from "../../cs2-backend/mvp/dashboard/src/Building.jsx";
import {CareWorkspace, useCareData} from "./CareWorkspace.jsx";

const careViews = new Set(["daily", "urgent", "residents", "facility", "history"]);

export default function BuildingWorkspace({headers, act, onError}) {
  const query = new URLSearchParams(location.search);
  const [section, setSection] = useState(query.get("section") === "care" ? "care" : "repairs");
  const [careView, setCareView] = useState(careViews.has(query.get("careView")) ? query.get("careView") : "daily");
  const [careOpened, setCareOpened] = useState(section === "care");
  const tabs = useRef([]);
  const {data, unavailable} = useCareData(headers);
  const open = data?.requests.filter((item) => item.status !== "resolved") || [];
  const urgent = open.filter((item) => item.urgency === "urgent").length;

  function navigate(next, view = careView) {
    setSection(next);
    setCareView(view);
    if (next === "care") setCareOpened(true);
    const params = new URLSearchParams(location.search);
    if (next === "care") {
      params.set("section", "care"); params.set("careView", view);
    } else {
      params.delete("section"); params.delete("careView");
    }
    history.replaceState({}, "", `/building${params.size ? "?" + params : ""}`);
  }

  function moveTab(event, index) {
    const direction = {ArrowLeft: -1, ArrowRight: 1, Home: -index, End: 1 - index}[event.key];
    if (direction === undefined) return;
    event.preventDefault();
    const next = (index + direction + 2) % 2;
    navigate(next === 0 ? "repairs" : "care");
    tabs.current[next]?.focus();
  }

  const metrics = data ? [
    ["Urgent care", urgent, "Nurse or care lead review", "urgent"],
    ["Everyday care", open.length - urgent, "Meals, water and daily needs", "daily"],
    ["Resident check-ins", data.residents.filter((person) => person.checkin?.outcome !== "seen_well").length,
      "Residents to check on today", "residents"],
    ["Care-home repairs", data.facility_workflow.tickets.filter((item) => !item.merged_into && item.status !== "closed").length,
      "Room issues linked to resident care", "facility"],
  ] : [];

  return <section className="building-workspace" data-section={section} aria-label="Building and resident care">
    <div className="building-tabs" role="tablist" aria-label="Building workspace">
      {[["repairs", "Repairs & floor plan", LayoutGrid], ["care", "Resident care", HeartHandshake]].map(([id, label, Icon], index) =>
        <button key={id} type="button" role="tab" id={`building-${id}-tab`}
          ref={(element) => {tabs.current[index] = element;}}
          aria-controls={`building-${id}-panel`} aria-selected={section === id}
          tabIndex={section === id ? 0 : -1} onKeyDown={(event) => moveTab(event, index)}
          onClick={() => navigate(id)}>
          <Icon size={17}/><span>{label}</span>
          {id === "care" && !unavailable && urgent > 0 && <span className="care-urgent-count" aria-label={`${urgent} urgent care requests`}>{urgent}</span>}
        </button>)}
    </div>
    <div role="tabpanel" id="building-repairs-panel" aria-labelledby="building-repairs-tab" hidden={section !== "repairs"}>
      <section className="building-care-summary" aria-labelledby="building-care-heading">
        <div className="building-care-heading"><div><h2 id="building-care-heading">Resident care{data ? ` at ${data.facility}` : ""}</h2>
          <p>Care requests, wellbeing checks and linked room repairs, alongside your building tools.</p></div>
          <button className="primary" onClick={() => navigate("care")}>Open resident care</button></div>
        {unavailable && <p role="status">Care summary unavailable. Open resident care to reconnect and check the queue.</p>}
        {!data && !unavailable && <p role="status">Loading resident care...</p>}
        {data && <div className="building-care-metrics" aria-label={unavailable ? "Last connected care summary" : "Care overview"}>
          {metrics.map(([label, count, detail, view]) => <button key={view} className={view === "urgent" && count > 0 ? "urgent-care" : ""}
            onClick={() => navigate("care", view)}><span>{label}</span><strong>{count}</strong><small>{detail}</small></button>)}
        </div>}
      </section>
      <OriginalBuilding headers={headers} act={act} onError={onError}/>
    </div>
    <div role="tabpanel" id="building-care-panel" aria-labelledby="building-care-tab" hidden={section !== "care"}>
      {careOpened && <CareWorkspace view={careView}/>}
    </div>
  </section>;
}
