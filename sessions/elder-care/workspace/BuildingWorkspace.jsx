import React, {useEffect} from "react";
import {CareWorkspace} from "./CareWorkspace.jsx";

export default function BuildingWorkspace() {
  useEffect(() => {
    history.replaceState({}, "", "/building");
    window.scrollTo({top:0});
  }, []);
  return <section className="building-workspace" aria-label="Building workspace">
    <CareWorkspace view="building"/>
  </section>;
}
