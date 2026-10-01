import { request, type FullConfig } from "@playwright/test";
import { mkdir } from "node:fs/promises";

export default async function setup(config: FullConfig): Promise<void> {
  const username = process.env.TON_E2E_EMAIL;
  const password = process.env.TON_E2E_PASSWORD;
  if (!username || !password)
    throw new Error(
      "Set TON_E2E_EMAIL and TON_E2E_PASSWORD for an authorized local test account."
    );
  const context = await request.newContext({
    baseURL: config.projects[0]?.use.baseURL,
  });
  try {
    const response = await context.post("/api/auth/login", {
      form: { username, password },
    });
    if (!response.ok())
      throw new Error(`TON test login failed: ${response.status()}`);
    await mkdir("output/ton-ux002", { recursive: true });
    await context.storageState({ path: "output/ton-ux002/auth.json" });
  } finally {
    await context.dispose();
  }
}
