import { defineConfig } from "vite";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";

const require = createRequire(import.meta.url);
const root = path.dirname(fileURLToPath(import.meta.url));
const upstream = path.resolve(root, "../../cs2-backend/mvp/dashboard/src/main.jsx");
const upstreamMap = path.resolve(root, "../../cs2-backend/mvp/dashboard/src/LiveMap.jsx");
const careModule = path.join(root, "CareWorkspace.jsx");

// Extend the upstream shell at build time rather than forking Imaan's dashboard
// or changing another session's files. Each anchor must occur exactly once.
// An upstream shell change fails the build explicitly instead of dropping tools.
function extendShell(source) {
  const edits = [
    ["const PATHS={ops:'/ops',supporter:'/supporter',building:'/building'};",
      "const PATHS={ops:'/ops',supporter:'/supporter',building:'/building',care:'/care'};"],
    ["</nav><div className=\"sidebar-note\">",
      "<button className={view==='care'?'active':''} onClick={()=>nav('care')}><CareNav headers={headers}/></button></nav><div className=\"sidebar-note\">"],
    ["view==='building'?t('Building'):t('Night operations')",
      "view==='care'?'Resident care':view==='building'?t('Building'):t('Night operations')"],
    ["className={view!=='building'?'on':''} aria-pressed={view!=='building'}",
      "className={view==='ops'||view==='supporter'?'on':''} aria-pressed={view==='ops'||view==='supporter'}"],
    ["</div>{data.region&&<span className=\"region\"",
      "<button className={view==='care'?'on':''} aria-pressed={view==='care'} onClick={()=>nav('care')}>Care</button></div>{data.region&&<span className=\"region\""],
    ["<div className=\"content\"><div className=\"title-row\">",
      "<div className={'content'+(view==='care'?' care-content':'')}><div className=\"title-row\">"],
    ["{!online?null:view==='building'?<Building",
      "{!online?null:view==='care'?<CareWorkspace key={token}/>:view==='building'?<Building"],
  ];
  for (const [before, after] of edits) {
    if (source.split(before).length !== 2) {
      throw new Error(`Upstream dashboard integration anchor changed: ${before}`);
    }
    source = source.replace(before, after);
  }
  return `import {CareWorkspace, CareNav} from ${JSON.stringify(careModule)};\n${source}`;
}

function preserveMapClasses(source) {
  // Leaflet adds classes to its container. React must not overwrite that node's
  // className when drawing or placing begins, or map controls lose their styles.
  const before = '<div className={\'map\'+((chosen&&chosen.lat==null)||draw?\' placing\':\'\')} ref={el}/>';
  if (source.split(before).length !== 2) {
    throw new Error("Upstream LiveMap container changed; review the care integration");
  }
  return source.replace(before,
    '<div className={\'map-state\'+((chosen&&chosen.lat==null)||draw?\' placing\':\'\')}><div className="map" ref={el}/></div>');
}

export default defineConfig({
  root,
  resolve: {
    // Both source trees share one React instance and the existing library versions.
    alias: Object.fromEntries(["react", "react-dom", "leaflet", "lucide-react"].map(
      (name) => [name, path.dirname(require.resolve(`${name}/package.json`))],
    )),
  },
  plugins: [{
    name: "diza-add-resident-care",
    enforce: "pre",
    transform(source, id) {
      if (id.split("?")[0] === upstream) return extendShell(source);
      if (id.split("?")[0] === upstreamMap) return preserveMapClasses(source);
    },
  }],
  build: { outDir: path.resolve(root, "../dist"), emptyOutDir: true },
});
