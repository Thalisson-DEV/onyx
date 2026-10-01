import { test } from "@playwright/test";
import { TonWorkspacePage } from "@tests/e2e/pages/TonWorkspacePage";

test.describe("UX-002 native TON journeys", () => {
  test("A: enters TON from home and keeps every destination inside TON", async ({
    page,
  }) => {
    const workspace = new TonWorkspacePage(page);
    await workspace.enter();
    await workspace.open("chat");
    await workspace.expectNativeChat();
    await workspace.open("central");
    for (const destination of [
      "dre",
      "readiness",
      "specialists",
      "routines",
      "reports",
    ] as const)
      await workspace.open(destination);
    workspace.expectNoAdminDetour();
  });

  test("B: runs R3 and recovers its persisted report after refresh", async ({
    page,
  }) => {
    const workspace = new TonWorkspacePage(page);
    await workspace.enter();
    await workspace.runR3();
  });

  test("C: specialist, routine and coverage states match the API", async ({
    page,
  }, info) => {
    const workspace = new TonWorkspacePage(page);
    await workspace.enter();
    await workspace.open("specialists");
    const specialists = await workspace.crossCheckSpecialists();
    await workspace.open("routines");
    const routines = await workspace.crossCheckRoutines();
    await workspace.open("coverage");
    const coverage = await workspace.crossCheckCoverage();
    await info.attach("runtime-truth", {
      body: JSON.stringify({ specialists, routines, coverage }, null, 2),
      contentType: "application/json",
    });
  });

  test("D: native chat groups analysis and exposes a report artifact", async ({
    page,
  }) => {
    test.setTimeout(240000);
    const workspace = new TonWorkspacePage(page);
    await workspace.enter();
    await workspace.open("chat");
    await workspace.expectNativeChat();
    await workspace.analyzeClosing();
    workspace.expectNoAdminDetour();
  });

  test("E: resolves DRE context and inspects without approving", async ({
    page,
  }) => {
    const workspace = new TonWorkspacePage(page);
    await workspace.enter();
    await workspace.open("dre");
    await workspace.inspectReadiness();
    await workspace.open("central");
  });

  test("F: shows source history and cancels upload safely", async ({
    page,
  }) => {
    const workspace = new TonWorkspacePage(page);
    await workspace.enter();
    await workspace.open("sources");
    await workspace.sourcesAndCancelUpload();
    await workspace.open("central");
  });
});
