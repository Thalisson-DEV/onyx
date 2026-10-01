import { defineConfig, devices } from "@playwright/test";
import base from "./playwright.config";

export default defineConfig({
  ...base,
  globalSetup: require.resolve("./tests/e2e/ton/ux002.setup"),
  testMatch: /.*\/tests\/e2e\/ton\/ux002\.spec\.ts/,
  workers: 1,
  projects: [
    {
      name: "ton",
      use: {
        ...devices["Desktop Chrome"],
        storageState: "output/ton-ux002/auth.json",
      },
    },
  ],
});
