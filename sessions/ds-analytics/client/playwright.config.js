import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 30000,
  use: {
    baseURL: "http://127.0.0.1:18773",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    command:
      "../.venv/bin/python ../scripts/serve_relay.py --ephemeral --demo --port 18773",
    url: "http://127.0.0.1:18773/health/relay",
    reuseExistingServer: false,
    env: {
      OPS_API_TOKEN: "relay-demo-local",
      RETELL_API_KEY: "",
      RELAY_RETELL_AGENT_ID: "",
    },
  },
});
