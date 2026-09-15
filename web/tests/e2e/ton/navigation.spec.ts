import { test, expect } from "@playwright/test";
import { TonNavigationPage } from "@tests/e2e/pages/TonNavigationPage";
import { loginAsRandomUser } from "@tests/e2e/utils/auth";
import { setThemeBeforeNavigation, THEMES } from "@tests/e2e/utils/theme";

/**
 * TON-FE-004 navigation contract, live.
 *
 * Proves the information architecture in the running application: the two TON
 * destinations, the workspace capability, conversation history kept apart, no
 * deferred domain, and both destinations reachable on a small viewport and in
 * either theme.
 */

const VIEWPORTS = [
  { name: "mobile", width: 375, height: 812 },
  { name: "desktop", width: 1280, height: 720 },
] as const;

for (const theme of THEMES) {
  for (const viewport of VIEWPORTS) {
    test(`TON navigation reads as TON (${theme}, ${viewport.name})`, async ({
      page,
    }) => {
      await page.setViewportSize(viewport);
      await setThemeBeforeNavigation(page, theme);
      await loginAsRandomUser(page);

      const nav = new TonNavigationPage(page);
      await nav.gotoApp();
      await nav.revealSidebar();

      await nav.expectProductNavigation();
      await nav.expectHistorySeparateFromNavigation();
      await nav.expectWorkspaceCapability();
      await nav.expectNoDeferredDestination();
      await nav.expectLegibleInCurrentTheme();
    });
  }
}

test("Central and Especialistas both open their real route", async ({
  page,
}) => {
  await loginAsRandomUser(page);

  const nav = new TonNavigationPage(page);
  await nav.gotoApp();
  await nav.revealSidebar();

  await nav.expectDestinationResolves(nav.specialists, /\/app\/agents/);

  await nav.gotoApp();
  await nav.revealSidebar();
  await nav.expectDestinationResolves(nav.central, /\/app(\?|$)/);
});

test("both destinations resolve when entered directly by URL", async ({
  page,
}) => {
  await loginAsRandomUser(page);

  const nav = new TonNavigationPage(page);

  // No in-app state transition first: a typed URL must render the destination.
  await nav.gotoDirect("/app/agents");
  await expect(page).toHaveURL(/\/app\/agents/);
  await expect(page.locator("body")).not.toContainText(
    /page could not be found/i
  );
  await nav.revealSidebar();
  await expect(nav.specialists).toBeVisible();

  await nav.gotoDirect("/app");
  await expect(page).toHaveURL(/\/app/);
  await nav.revealSidebar();
  await expect(nav.central).toBeVisible();
});

test("a deferred domain has no route to enter", async ({ page }) => {
  await loginAsRandomUser(page);

  // FE-008 and FE-009 own these. FE-004 must not have created a placeholder.
  for (const path of ["/app/occurrences", "/app/reports", "/app/sources"]) {
    const response = await page.goto(path);
    expect(response?.status()).toBe(404);
  }
});

test("the sidebar drawer still closes on a small viewport", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await loginAsRandomUser(page);

  const nav = new TonNavigationPage(page);
  await nav.gotoApp();

  // Opening and closing the drawer must not trap the user behind the overlay.
  await page.getByLabel("Open Sidebar").first().click();
  await expect(nav.central).toBeVisible();

  await page.getByLabel("Close Sidebar").click();
  await expect(page.getByLabel("Open Sidebar").first()).toBeVisible();
});
