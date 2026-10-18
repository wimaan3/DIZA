import React, {useEffect, useState} from "react";
import OriginalBuilding from "../../cs2-backend/mvp/dashboard/src/Building.jsx";
import {CareWorkspace, useCareData} from "./CareWorkspace.jsx";

export default function BuildingWorkspace({headers, act, onError}) {
  const [building, setBuilding] = useState(new URLSearchParams(location.search).get("building") === "apartments" ? "apartments" : "care-home");
  const [apartmentsOpened, setApartmentsOpened] = useState(building === "apartments");
  const {data} = useCareData(headers);
  useEffect(() => {
    // Older care/section links now open the same combined Building screen.
    history.replaceState({}, "", building === "apartments" ? "/building?building=apartments" : "/building");
    window.scrollTo({top:0});
  }, [building]);

  return <section className="building-workspace" data-building={building} aria-label="Building workspace">
    <div className="building-context"><label htmlFor="building-select">Building</label>
      <select id="building-select" value={building} onChange={(event) => {
        setBuilding(event.target.value);
        if (event.target.value === "apartments") setApartmentsOpened(true);
      }}>
        <option value="care-home">{data?.facility || "Willow House"} · care home</option>
        <option value="apartments">Larchmont Court Apartments · demo</option>
      </select>
      <span>Repairs, room information and resident care in one workspace</span>
    </div>
    <div hidden={building !== "care-home"}><CareWorkspace view="building"/></div>
    <div className="apartment-building" hidden={building !== "apartments"}>
      {apartmentsOpened && <OriginalBuilding headers={headers} act={act} onError={onError}/>}
    </div>
  </section>;
}
