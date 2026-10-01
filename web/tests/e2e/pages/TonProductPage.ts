import { expect, type Page } from "@playwright/test";

type Destination =
  | "Visão Geral"
  | "Assistente"
  | "Fechamento"
  | "DRE"
  | "Pendências"
  | "Automações"
  | "Relatórios"
  | "Fontes"
  | "Especialistas";

const PATHS: Record<Destination, RegExp> = {
  "Visão Geral": /\/ton$/,
  Assistente: /\/ton\/chat/,
  Fechamento: /\/ton\/fechamento/,
  DRE: /\/ton\/dre/,
  Pendências: /\/ton\/pendencias/,
  Automações: /\/ton\/automacoes/,
  Relatórios: /\/ton\/relatorios/,
  Fontes: /\/ton\/fontes/,
  Especialistas: /\/ton\/especialistas/,
};

/** The rebuilt TON client (TON-FE-001): shell, overview and product areas. */
export class TonProductPage {
  private readonly visited: string[] = [];

  constructor(private readonly page: Page) {
    page.on("framenavigated", (frame) => {
      if (frame === page.mainFrame()) this.visited.push(frame.url());
    });
  }

  async enterFromRoot(): Promise<void> {
    await this.page.goto("/");
    await expect(this.page).toHaveURL(PATHS["Visão Geral"]);
    await expect(
      this.page.getByRole("heading", { level: 1, name: /^Olá/ })
    ).toBeVisible();
  }

  async open(destination: Destination): Promise<void> {
    await this.page
      .getByRole("navigation", { name: "Navegação do TON" })
      .getByRole("link", { name: destination, exact: true })
      .click();
    await expect(this.page).toHaveURL(PATHS[destination]);
  }

  async expectShell(): Promise<void> {
    await expect(this.page.getByAltText("Vale Norte").first()).toBeVisible();
    await expect(
      this.page.getByRole("link", { name: "Nova conversa" })
    ).toBeVisible();
    await expect(
      this.page.getByText("Powered by", { exact: false })
    ).toHaveCount(0);
  }

  async expectOverview(): Promise<void> {
    await expect(
      this.page.getByRole("heading", { name: "O que precisa de atenção" })
    ).toBeVisible();
    await expect(
      this.page.getByRole("heading", { name: "Atividade do TON" })
    ).toBeVisible();
    await expect(
      this.page.getByRole("heading", { name: "Fechamento preliminar mensal" })
    ).toBeVisible();
  }

  async expectAssistantWelcome(): Promise<void> {
    await expect(
      this.page.getByRole("heading", { name: "Olá, sou o TON." })
    ).toBeVisible();
    await expect(
      this.page.getByRole("button", { name: "Analisar fechamento" })
    ).toBeVisible();
    await expect(this.page.getByText("deepseek", { exact: false })).toHaveCount(
      0
    );
  }

  async analyzeClosing(): Promise<void> {
    await this.page
      .getByRole("button", { name: "Analisar fechamento" })
      .click();
    await expect(this.page.getByText("Análise concluída")).toBeVisible({
      timeout: 180000,
    });
    await expect(
      this.page.getByRole("link", { name: "Abrir relatório" }).first()
    ).toBeVisible();
    await expect(
      this.page.getByTestId("onyx-ai-message").last()
    ).not.toContainText(
      /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/
    );
  }

  async expectClosingBlocked(): Promise<void> {
    await expect(
      this.page.getByRole("heading", { name: /ainda não pode ser publicada/ })
    ).toBeVisible();
  }

  async inspectFirstPendingDecision(): Promise<void> {
    await this.page.getByRole("button", { name: "Analisar" }).first().click();
    const dialog = this.page.getByRole("dialog");
    await expect(dialog.getByText("O que o TON encontrou")).toBeVisible();
    await expect(dialog).not.toContainText(
      /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/
    );
    await dialog.getByRole("button", { name: "Fechar" }).click();
    await expect(dialog).toHaveCount(0);
  }

  async expectR3Scheduled(): Promise<void> {
    await expect(
      this.page.getByText(/Primeiro dia útil do mês/).first()
    ).toBeVisible();
    await expect(this.page.getByText("Agendada").first()).toBeVisible();
  }

  async openLatestReport(): Promise<void> {
    await this.page.getByRole("link", { name: "Abrir" }).first().click();
    await expect(this.page).toHaveURL(/\/ton\/controladoria\/reports\//);
    await expect(this.page.getByText("Resumo executivo").first()).toBeVisible();
    await expect(
      this.page.getByRole("link", { name: "Baixar relatório" })
    ).toBeVisible();
  }

  async expectNgPendingDirectIntegration(): Promise<void> {
    const ng = this.page
      .getByRole("article")
      .filter({ hasText: "NG / Lançamentos financeiros" });
    await expect(ng.getByText("Integração direta")).toBeVisible();
    await expect(ng).not.toContainText(/conectad/i);
  }

  expectNoAdminDetour(): void {
    expect(
      this.visited.filter((url) => new URL(url).pathname.startsWith("/admin"))
    ).toEqual([]);
  }
}
