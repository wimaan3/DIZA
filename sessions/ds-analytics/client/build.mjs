import { build } from "esbuild";
await build({
  entryPoints: ["src/voice.js"],
  bundle: true,
  format: "esm",
  target: "es2022",
  outfile: "dist/voice-sdk.js",
  minify: true,
});
