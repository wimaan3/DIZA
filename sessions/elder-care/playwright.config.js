import { defineConfig } from "@playwright/test";
import os from "node:os";
import path from "node:path";

export default defineConfig({
  testDir: "./tests",
  testMatch: "*.spec.js",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:8767",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: {
    command: `${process.env.CARE_PYTHON || "python3"} -m uvicorn app:app --host 127.0.0.1 --port 8767`,
    url: "http://127.0.0.1:8767/healthz",
    reuseExistingServer: false,
    env: {
      CARE_INCLUDE_LEGACY: "false",
      CARE_DB: path.join(os.tmpdir(), `diza-care-e2e-${process.pid}.sqlite3`),
      OPS_API_TOKEN: "",
      DRILL_MODE: "true",
      RETELL_API_KEY: "",
    },
  },
});
