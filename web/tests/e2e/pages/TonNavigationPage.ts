import { expect, type Locator, type Page } from "@playwright/test";

/**
 * Reads the TON information architecture that TON-FE-004 established.
 *
 * The sidebar must present two TON destinations, the workspace capabilities
 * that exist today, and conversation history kept apart from all three. Every
 * assertion below is about navigation only: hiding an entry is never a security
 * control, and no assertion here implies one.
 */
export class TonNavigationPage {
  /** Pinned TON destinations. Never inside the scrolling history area. */
  private readonly productNav: Locator;
  private readonly historyNav: Locator;

  constructor(private readonly page: Page) {
    this.productNav = page.getByRole("navigation", { name: "TON navigation" });
    this.historyNav = page.getByRole("navigation", {
      name: "Conversation history",
    });
  }

  async gotoApp(): Promise<void> {
    await this.page.goto("/app");
    await this.page.waitForLoadState("networkidle");
  }

  /** Navigates straight to a URL, with no in-app state transition first. */
  async gotoDirect(path: string): Promise<void> {
    await this.page.goto(path);
    await this.page.waitForLoadState("networkidle");
  }

  /** Opens the sidebar when the viewport keeps it folded. */
  async revealSidebar(): Promise<void> {
    const opener = this.page.getByLabel("Open Sidebar").first();
    if (await opener.isVisible()) await opener.click();
  }

  get central(): Locator {
    return this.productNav.getByRole("link", { name: "Central", exact: true });
  }

  get specialists(): Locator {
    return this.productNav.getByRole("link", {
      name: "Specialists",
      exact: true,
    });
  }

  /** Both TON destinations exist, in order, inside one landmark. */
  async expectProductNavigation(): Promise<void> {
    await expect(this.productNav).toBeVisible();
    await expect(this.central).toBeVisible();
    await expect(this.specialists).toBeVisible();
    await expect(this.central).toHaveAttribute("href", "/app");
    await expect(this.specialists).toHaveAttribute("href", "/app/agents");

    const hrefs = await this.productNav
      .locator("a[href]")
      .evaluateAll((nodes) =>
        nodes.map((node) => node.getAttribute("href") ?? "")
      );
    expect(hrefs).toEqual(["/app", "/app/agents"]);
  }

  /** History is present, and is not the product navigation. */
  async expectHistorySeparateFromNavigation(): Promise<void> {
    await expect(this.historyNav).toBeVisible();
    await expect(this.historyNav.getByText("Conversations")).toBeVisible();
    await expect(this.productNav.getByTestId("ChatButton")).toHaveCount(0);
    await expect(
      this.historyNav.getByRole("link", { name: "Central", exact: true })
    ).toHaveCount(0);
  }

  /** The workspace capability TON surfaces today. */
  async expectWorkspaceCapability(): Promise<void> {
    await expect(
      this.page.getByText("Projects", { exact: true })
    ).toBeVisible();
  }

  /** No navigation entry may promise a domain TON has not built. */
  async expectNoDeferredDestination(): Promise<void> {
    for (const segment of ["occurrences", "reports", "sources"]) {
      await expect(this.page.locator(`a[href*="${segment}"]`)).toHaveCount(0);
    }

    const text = (await this.page.locator("body").innerText()).replace(
      /\s+/g,
      " "
    );
    for (const phrase of [
      "Occurrences",
      "Ocorrências",
      "Reports",
      "Relatórios",
      "Coming soon",
      "Em breve",
    ]) {
      expect(text).not.toContain(phrase);
    }
  }

  /** Every sidebar link resolves; none lands on the app's not-found page. */
  async expectDestinationResolves(
    link: Locator,
    expectedUrl: RegExp
  ): Promise<void> {
    await link.click();
    await expect(this.page).toHaveURL(expectedUrl);
    await expect(this.page.locator("body")).not.toContainText(
      /page could not be found|404/i
    );
  }

  /**
   * Both destinations read legibly: the accessible name carries the
   * destination, so state is never communicated by colour alone.
   */
  async expectLegibleInCurrentTheme(): Promise<void> {
    for (const link of [this.central, this.specialists]) {
      await expect(link).toBeVisible();
      const name = await link.getAttribute("aria-label");
      expect(name?.trim()).toBeTruthy();
    }

    // The label text renders with a resolved, non-transparent colour.
    const colours = await this.productNav
      .locator(".opal-sidebar-tab")
      .evaluateAll((nodes) =>
        nodes.map((node) => {
          const title = node.querySelector("p, span, div");
          return title ? getComputedStyle(title).color : "";
        })
      );
    for (const colour of colours) {
      expect(colour).not.toContain("rgba(0, 0, 0, 0)");
    }
  }
}
