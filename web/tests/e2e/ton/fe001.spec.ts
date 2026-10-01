import { test } from "@playwright/test";
import { TonProductPage } from "@tests/e2e/pages/TonProductPage";

test.describe("TON-FE-001 client journey", () => {
  test("enters TON and walks every product area without leaving TON", async ({
    page,
  }) => {
    const ton = new TonProductPage(page);
    await ton.enterFromRoot();
    await ton.expectShell();
    await ton.expectOverview();
    await ton.open("Assistente");
    await ton.expectAssistantWelcome();
    await ton.open("Fechamento");
    await ton.expectClosingBlocked();
    await ton.open("Pendências");
    await ton.inspectFirstPendingDecision();
    await ton.open("DRE");
    await ton.open("Automações");
    await ton.expectR3Scheduled();
    await ton.open("Relatórios");
    await ton.openLatestReport();
    await ton.open("Fontes");
    await ton.expectNgPendingDirectIntegration();
    await ton.open("Especialistas");
    ton.expectNoAdminDetour();
  });

  test("analyzes the closing with grouped progress and a report", async ({
    page,
  }) => {
    test.setTimeout(240000);
    const ton = new TonProductPage(page);
    await ton.enterFromRoot();
    await ton.open("Assistente");
    await ton.analyzeClosing();
    ton.expectNoAdminDetour();
  });
});
