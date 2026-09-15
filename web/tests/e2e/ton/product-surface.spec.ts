import { test } from "@playwright/test";
import { TonProductSurfacePage } from "@tests/e2e/pages/TonProductSurfacePage";
import { loginAs, loginAsRandomUser } from "@tests/e2e/utils/auth";
import { setThemeBeforeNavigation, THEMES } from "@tests/e2e/utils/theme";

const VIEWPORTS = [
  { name: "mobile", width: 375, height: 812 },
  { name: "desktop", width: 1280, height: 720 },
] as const;

for (const theme of THEMES) {
  for (const viewport of VIEWPORTS) {
    test(`normal user sees only TON product surfaces (${theme}, ${viewport.name})`, async ({
      page,
    }) => {
      await page.setViewportSize(viewport);
      await setThemeBeforeNavigation(page, theme);
      await loginAsRandomUser(page);

      const surface = new TonProductSurfacePage(page);
      await surface.gotoApp();

      await surface.expectNoUpstreamAttribution();
      await surface.expectProductFooter();
      await surface.expectNoUpstreamLinks();
      await surface.expectNoCommerceNavigation();
      await surface.expectNoBuilderProductEntry();

      // The account menu is where the upstream help and changelog links lived.
      if (viewport.width >= 912) {
        await surface.openAccountMenu();
        await surface.expectNoUpstreamLinks();
      }
    });
  }
}

test("normal user settings carry no plan or upgrade prompt", async ({
  page,
}) => {
  await loginAsRandomUser(page);

  const surface = new TonProductSurfacePage(page);
  await surface.gotoAdmin("/app/settings/general");
  await surface.expectNoCommerceNavigation();
  await surface.expectNoUpstreamLinks();
});

test("admin keeps the configuration TON needs and no commerce navigation", async ({
  page,
}) => {
  await loginAs(page, "admin");

  const surface = new TonProductSurfacePage(page);
  await surface.gotoAdmin("/admin/language-models");

  // Model provider configuration stays an administrator capability.
  await surface.expectAdminPageReachable(/Language Models/i);
  await surface.expectAdminSidebarEntry("Users");
  await surface.expectAdminSidebarEntry("Agents");
  await surface.expectAdminSidebarEntry("Security & Hardening");

  await surface.expectNoCommerceNavigation();
  await surface.expectNoUpstreamAttribution();
});

test("admin can still reach connectors and index settings", async ({
  page,
}) => {
  await loginAs(page, "admin");

  const surface = new TonProductSurfacePage(page);
  await surface.gotoAdmin("/admin/add-connector");
  await surface.expectAdminSidebarEntry("Add Connector");
  await surface.expectAdminSidebarEntry("Existing Connectors");
  await surface.expectAdminSidebarEntry("Document Sets");
});
