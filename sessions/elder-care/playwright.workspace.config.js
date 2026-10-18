import { defineConfig } from "@playwright/test";
import os from "node:os";
import path from "node:path";

const temp = path.join(os.tmpdir(), `diza-workspace-e2e-${process.pid}`);
export default defineConfig({
  testDir: "./tests",
  testMatch: "workspace.spec.js",
  outputDir: "workspace-test-results",
  workers: 1,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:8768",
    viewport: { width: 1440, height: 1000 },
    reducedMotion: "reduce",
    launchOptions: {args: ["--enable-unsafe-swiftshader"]},
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: {
    command: `npm run build && ${process.env.CARE_PYTHON || "python3"} -m uvicorn app:app --host 127.0.0.1 --port 8768`,
    url: "http://127.0.0.1:8768/healthz",
    reuseExistingServer: false,
    env: {
      CARE_INCLUDE_LEGACY: "true",
      CARE_DB: `${temp}-care.sqlite3`,
      DIZA_DB: `${temp}-operations.sqlite3`,
      OPS_API_TOKEN: "workspace-test-token",
      DRILL_MODE: "true",
      RETELL_API_KEY: "",
      DIZA_RESPONDERS: "",
    },
  },
});
