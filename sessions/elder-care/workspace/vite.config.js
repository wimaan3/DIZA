import { defineConfig } from "vite";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";

const require = createRequire(import.meta.url);
const root = path.dirname(fileURLToPath(import.meta.url));
const upstream = path.resolve(root, "../../cs2-backend/mvp/dashboard/src/main.jsx");
const upstreamMap = path.resolve(root, "../../cs2-backend/mvp/dashboard/src/LiveMap.jsx");
const careModule = path.join(root, "CareWorkspace.jsx");
const buildingModule = path.join(root, "BuildingWorkspace.jsx");

// Extend the upstream shell at build time rather than forking Imaan's dashboard
// or changing another session's files. Each anchor must occur exactly once.
// An upstream shell change fails the build explicitly instead of dropping tools.
function extendShell(source) {
  const edits = [
    ["import Building from './Building.jsx';",
      `import Building from ${JSON.stringify(buildingModule)};`],
    ["<Building2 size={18}/>{t('Building management')}",
      "<Building2 size={18}/><span>{t('Building management')}</span><CareBadge headers={headers}/>"],
    ['t("BUILDING MODE / TENANT TICKETS")', "t('BUILDING / REPAIRS & RESIDENT CARE')"],
    ['t("Every tenant call, ranked and linked.")', "t('One building. Every resident looked after.')"],
    ['t("Rules set urgency, merge duplicates and link related problems. You assign, decide and close.")',
      "t('Coordinate repairs, review the floor plan, and follow through on urgent and everyday resident care.')"],
  ];
  for (const [before, after] of edits) {
    if (source.split(before).length !== 2) {
      throw new Error(`Upstream dashboard integration anchor changed: ${before}`);
    }
    source = source.replace(before, after);
  }
  return `import {CareBadge} from ${JSON.stringify(careModule)};\n${source}`;
}

function preserveMapClasses(source) {
  // MapLibre adds classes to its container. React must not overwrite that node's
  // className when drawing or placing begins, or map controls lose their styles.
  const before = '<div className={\'map\'+(chosen&&!position(chosen)||draw?\' placing\':\'\')} ref={el}/>';
  if (source.split(before).length !== 2) {
    throw new Error("Upstream LiveMap container changed; review the care integration");
  }
  return source.replace(before,
    '<div className={\'map-state\'+(chosen&&!position(chosen)||draw?\' placing\':\'\')}><div className="map" ref={el}/></div>');
}

export default defineConfig({
  root,
  resolve: {
    // Both source trees share one React instance and the existing library versions.
    alias: Object.fromEntries(["react", "react-dom", "maplibre-gl", "lucide-react"].map(
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
  build: {
    outDir: path.resolve(root, "../dist"), emptyOutDir: true,
    rollupOptions: {output: {manualChunks: {maplibre: ["maplibre-gl"]}}},
  },
});
