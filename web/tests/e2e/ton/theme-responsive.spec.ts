import { test } from "@playwright/test";
import { TonThemePage } from "@tests/e2e/pages/TonThemePage";
import { loginAs } from "@tests/e2e/utils/auth";
import { setThemeBeforeNavigation, THEMES } from "@tests/e2e/utils/theme";

const VIEWPORTS = [
  { name: "mobile", width: 375, height: 812 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "desktop", width: 1280, height: 720 },
] as const;

for (const theme of THEMES) {
  for (const viewport of VIEWPORTS) {
    test(`TON ${theme} theme at ${viewport.name} width`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await setThemeBeforeNavigation(page, theme);
      await loginAs(page, "admin");

      const tonTheme = new TonThemePage(page);
      await tonTheme.gotoChat();
      await tonTheme.expectRuntimeTheme(theme);
      await tonTheme.expectNoHorizontalOverflow();
      await tonTheme.expectComposerFocus();

      if (viewport.width < 724) {
        await tonTheme.expectMobileSidebarInteraction();
      } else if (viewport.width >= 912) {
        await tonTheme.expectDesktopSidebar();
      }

      await tonTheme.capture(`ton-${theme}-${viewport.name}-chat`);

      await tonTheme.gotoAgents();
      await tonTheme.expectNoHorizontalOverflow();

      await tonTheme.gotoSettings();
      await tonTheme.expectNoHorizontalOverflow();
      await tonTheme.expectSettingsPopover();
    });
  }
}
