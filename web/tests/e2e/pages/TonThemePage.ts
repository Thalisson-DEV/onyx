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
            card: "#ffffff",
            surface: "#f8f9f8",
            sidebar: "#eff2f0",
            elevated: "#e3e7e4",
            field: "#ffffff",
            border: "#e6e6e6",
          }
        : {
            primary: "#c3ded2",
            action: "#2f795a",
            card: "#18231d",
            surface: "#27332c",
            sidebar: "#344139",
            elevated: "#414f47",
            field: "#0b1410",
            border: "#44524a",
          };

    await expect
      .poll(() =>
        this.page.evaluate(() => {
          const styles = getComputedStyle(document.documentElement);
          // The production CSS pipeline minifies #ffffff to #fff, so expand short
          // hex before comparing against the token values.
          const read = (name: string): string => {
            const value = styles.getPropertyValue(name).trim().toLowerCase();
            return /^#[0-9a-f]{3}$/.test(value)
              ? "#" +
                  value
                    .slice(1)
                    .split("")
                    .map((c) => c + c)
                    .join("")
              : value;
          };
          return {
            primary: read("--theme-primary-05"),
            action: read("--action-selection-05"),
            card: read("--background-tint-00"),
            surface: read("--background-tint-01"),
            sidebar: read("--background-tint-02"),
            elevated: read("--background-tint-03"),
            field: read("--background-neutral-00"),
            border: read("--border-01"),
          };
        })
      )
      .toEqual(expected);
  }

  /**
   * The rendered surfaces must actually differ, not just the variables. This
   * catches a component that paints a surface outside the token system.
   */
  async expectDistinctRenderedSurfaces(): Promise<void> {
    const painted = await this.page.evaluate(() => {
      const read = (selector: string): string | null => {
        const element = document.querySelector(selector);
        return element ? getComputedStyle(element).backgroundColor : null;
      };
      return {
        body: getComputedStyle(document.body).backgroundColor,
        sidebar:
          read(".opal-sidebar-root__column") ??
          read(".opal-sidebar-root__overlay"),
      };
    });

    expect(painted.sidebar).not.toBeNull();
    expect(painted.sidebar).not.toBe(painted.body);
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
