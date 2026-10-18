import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  workers: 1,
  retries: 0,
  timeout: 30000,
  use: {
    baseURL: "http://127.0.0.1:18776",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    command:
      "../.venv/bin/python ../scripts/serve_hotel.py --demo --ephemeral --port 18776",
    url: "http://127.0.0.1:18776/health/hotel",
    env: { HOTEL_DEMO_TOKEN: "hotel-demo-local" },
    reuseExistingServer: false,
  },
});
