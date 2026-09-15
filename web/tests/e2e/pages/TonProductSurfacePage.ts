import { expect, type Locator, type Page } from "@playwright/test";

/**
 * Reads the surfaces TON-FE-003 sanitized. Every assertion is about what the
 * user can see or reach in navigation, never about authorization: direct-route
 * enforcement stays with the backend.
 */
export class TonProductSurfacePage {
  private readonly mainContainer: Locator;

  constructor(private readonly page: Page) {
    this.mainContainer = page.locator("[data-main-container]");
  }

  async gotoApp(): Promise<void> {
    await this.page.goto("/app");
    await this.page.waitForLoadState("networkidle");
    await expect(this.mainContainer).toBeVisible();
  }

  async gotoAdmin(path: string): Promise<void> {
    await this.page.goto(path);
    await this.page.waitForLoadState("networkidle");
  }

  /** Visible text of the whole page, whitespace collapsed. */
  private async visibleText(): Promise<string> {
    const text = await this.page.locator("body").innerText();
    return text.replace(/\s+/g, " ");
  }

  async expectNoUpstreamAttribution(): Promise<void> {
    await expect(
      this.page.getByText("Powered by Onyx", { exact: true })
    ).toHaveCount(0);
  }

  /** The footer must carry the product identity, not an upstream slogan. */
  async expectProductFooter(): Promise<void> {
    const text = await this.visibleText();
    expect(text).not.toContain("Open Source AI Platform");
    expect(text).toMatch(/Operational Intelligence and Controllership/i);
  }

  async expectNoUpstreamLinks(): Promise<void> {
    for (const pattern of [
      /onyx\.app/i,
      /discord\.gg/i,
      /github\.com\/onyx/i,
    ]) {
      const hrefs = await this.page
        .locator("a[href]")
        .evaluateAll((nodes) =>
          nodes.map((node) => node.getAttribute("href") ?? "")
        );
      expect(hrefs.filter((href) => pattern.test(href))).toEqual([]);
    }
  }

  /** Plans, billing, trials and upgrade prompts must not be reachable by link. */
  async expectNoCommerceNavigation(): Promise<void> {
    await expect(this.page.locator('a[href^="/admin/billing"]')).toHaveCount(0);

    const text = await this.visibleText();
    for (const phrase of [
      "Upgrade Plan",
      "Plans & Billing",
      "Update Billing Information",
      "Business Plan",
      "Enterprise Plan",
      "trial",
    ]) {
      expect(text.toLowerCase()).not.toContain(phrase.toLowerCase());
    }
  }

  async expectNoBuilderProductEntry(): Promise<void> {
    await expect(this.page.getByTestId("AppSidebar/build")).toHaveCount(0);
  }

  /** Opens the account menu so its links and version line can be read. */
  async openAccountMenu(): Promise<void> {
    await this.page.locator("#onyx-user-dropdown").click();
    await expect(this.page.getByTestId("Settings/user-settings")).toBeVisible();
  }

  async expectAdminSidebarEntry(label: string): Promise<void> {
    await expect(
      this.page.getByRole("link", { name: label, exact: true })
    ).toBeVisible();
  }

  async expectAdminPageReachable(heading: RegExp): Promise<void> {
    await expect(this.page.locator("body")).toContainText(heading);
  }
}
