import { expect, type Locator, type Page } from "@playwright/test";
import { ChatPage } from "@tests/e2e/chat/ChatPage";
import { expectScreenshot } from "@tests/e2e/utils/visualRegression";
import type { Theme } from "@tests/e2e/utils/theme";

export class TonThemePage {
  readonly chat: ChatPage;
  private readonly mainContainer: Locator;
  private readonly sidebarOverlay: Locator;

  constructor(private readonly page: Page) {
    this.chat = new ChatPage(page);
    this.mainContainer = page.locator("[data-main-container]");
    this.sidebarOverlay = page.locator(".opal-sidebar-root__overlay");
  }

  async gotoChat(): Promise<void> {
    await this.chat.goto();
    await expect(this.mainContainer).toBeVisible();
  }

  async gotoAgents(): Promise<void> {
    await this.page.goto("/app/agents");
    await this.page.waitForLoadState("networkidle");
    await expect(this.mainContainer).toBeVisible();
  }

  async gotoSettings(): Promise<void> {
    await this.page.goto("/app/settings/general");
    await this.page.waitForLoadState("networkidle");
    await expect(this.mainContainer).toBeVisible();
  }

  async expectNoHorizontalOverflow(): Promise<void> {
    await expect
      .poll(() =>
        this.page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth + 1
        )
      )
      .toBe(true);
  }

  async expectRuntimeTheme(theme: Theme): Promise<void> {
    const expected =
      theme === "light"
        ? {
            primary: "#145c42",
            action: "#145c42",
            surface: "#f8f9f8",
          }
        : {
            primary: "#c3ded2",
            action: "#227653",
            surface: "#131c17",
          };

    await expect
      .poll(() =>
        this.page.evaluate(() => {
          const styles = getComputedStyle(document.documentElement);
          return {
            primary: styles.getPropertyValue("--theme-primary-05").trim(),
            action: styles.getPropertyValue("--action-selection-05").trim(),
            surface: styles.getPropertyValue("--background-tint-01").trim(),
          };
        })
      )
      .toEqual(expected);
  }

  async expectComposerFocus(): Promise<void> {
    await this.chat.inputBar.focus();
    await this.chat.inputBar.expectFocused();
  }

  async expectMobileSidebarInteraction(): Promise<void> {
    await expect(this.sidebarOverlay).toHaveAttribute("data-folded", "true");
    await this.mainContainer.getByLabel("Open Sidebar").click();
    await expect(this.sidebarOverlay).toHaveAttribute("data-folded", "false");
    await this.sidebarOverlay.getByLabel("Close Sidebar").click();
    await expect(this.sidebarOverlay).toHaveAttribute("data-folded", "true");
    await this.chat.inputBar.focus();
    await this.chat.inputBar.expectFocused();
  }

  async expectDesktopSidebar(): Promise<void> {
    await expect(this.page.locator(".opal-sidebar-root__column")).toBeVisible();
  }

  async expectSettingsPopover(): Promise<void> {
    const select = this.page.getByRole("combobox").first();
    await expect(select).toBeVisible();
    await select.click();
    await expect(this.page.getByRole("listbox")).toBeVisible();
    await this.page.keyboard.press("Escape");
    await expect(this.page.getByRole("listbox")).toBeHidden();
  }

  async capture(name: string): Promise<void> {
    await expectScreenshot(this.page, { name });
  }
}
