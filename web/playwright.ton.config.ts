import { defineConfig, devices } from "@playwright/test";
import base from "./playwright.config";

export default defineConfig({
  ...base,
  globalSetup: require.resolve("./tests/e2e/ton/ton.setup"),
  testMatch: /.*\/tests\/e2e\/ton\/fe001\.spec\.ts/,
  workers: 1,
  projects: [
    {
      name: "ton",
      use: {
        ...devices["Desktop Chrome"],
        storageState: "output/ton-e2e/auth.json",
      },
    },
  ],
});
