import { expect, type Page } from "@playwright/test";
import { InputBar } from "@tests/e2e/chat/InputBar";

interface SpecialistView {
  key: string;
  name: string;
  status: string;
  reason: string;
  required_sources: string[];
}
interface RoutineView {
  key: string;
  name: string;
  status: string;
  schedule: string;
}
interface CapabilityView {
  status_label: string;
}
interface ClientSource {
  name: string;
  status: string;
  history: { id: string }[];
}

const destinations = {
  central: { name: /^Central$/, path: "/ton/controladoria" },
  chat: { name: /^(TON Chat|Chat TON)$/, path: "/ton/chat" },
  dre: { name: /^(Income statement|DRE)$/, path: "/ton/dre" },
  readiness: { name: /^(Pending items|Pendências)$/, path: "/ton/pendencias" },
  specialists: {
    name: /^(Specialists|Especialistas)$/,
    path: "/ton/especialistas",
  },
  routines: { name: /^(Routines|Rotinas)$/, path: "/ton/rotinas" },
  reports: { name: /^(Reports|Relatórios)$/, path: "/ton/relatorios" },
  sources: {
    name: /^(Data sources|Fontes de dados)$/,
    path: "/ton/data-sources",
  },
  coverage: {
    name: /^(TON coverage|Cobertura do TON)$/,
    path: "/ton/cobertura",
  },
};

export class TonWorkspacePage {
  readonly inputBar: InputBar;
  readonly visited: string[] = [];
  constructor(private readonly page: Page) {
    this.inputBar = new InputBar(page);
    page.on("framenavigated", (frame) => {
      if (frame === page.mainFrame())
        this.visited.push(new URL(frame.url()).pathname);
    });
  }

  async enter(): Promise<void> {
    await this.page.goto("/app");
    await this.page.getByRole("link", { name: "TON", exact: true }).click();
    await expect(this.page).toHaveURL(/\/ton\/controladoria$/);
  }

  async open(destination: keyof typeof destinations): Promise<void> {
    const target = destinations[destination];
    await this.page
      .getByRole("navigation", { name: /TON/ })
      .getByRole("link", { name: target.name })
      .click();
    await expect(this.page).toHaveURL(new RegExp(`${target.path}(\\?|$)`));
    await this.expectHumanLabels();
  }

  async expectHumanLabels(): Promise<void> {
    await expect(this.page.locator("body")).not.toContainText(
      /\bUNMAPPED\b|\bNO ACTUAL\b|\bIN PROGRESS\b|Synthetic unit/
    );
    await expect(this.page.locator("body")).not.toContainText(
      /Application error|This page could not be found/
    );
  }

  async expectNativeChat(): Promise<void> {
    await expect(this.inputBar.textbox).toBeVisible();
  }

  async runR3(): Promise<void> {
    const response = this.page.waitForResponse(
      (value) =>
        value.url().includes("/routines/R3/run") &&
        value.request().method() === "POST"
    );
    await this.page
      .getByRole("button", { name: /^(Run now|Executar agora)$/ })
      .click();
    await expect(
      this.page.getByText(/^(Closing started|Fechamento iniciado)$/)
    ).toBeVisible();
    expect((await response).ok()).toBe(true);
    await expect(
      this.page.getByText(/^(Closing completed|Fechamento concluído)$/)
    ).toBeVisible();
    const result = this.page.getByRole("link", {
      name: /^(Open result|Abrir resultado)$/,
    });
    await expect(result).toBeVisible();
    await result.click();
    await expect(this.page).toHaveURL(/\/ton\/controladoria\/reports\//);
    await expect(
      this.page.getByRole("link", { name: /Download Markdown|Baixar Markdown/ })
    ).toBeVisible();
    const downloadEvent = this.page.waitForEvent("download");
    await this.page
      .getByRole("link", { name: /Download Markdown|Baixar Markdown/ })
      .click();
    const download = await downloadEvent;
    expect(download.suggestedFilename()).toMatch(/\.md$/);
    expect(await download.failure()).toBeNull();
    await this.page.reload();
    await expect(
      this.page.getByRole("link", { name: /Download Markdown|Baixar Markdown/ })
    ).toBeVisible();
    await this.open("central");
    await this.page.reload();
    await expect(
      this.page.getByRole("link", { name: /^(Open result|Abrir resultado)$/ })
    ).toBeVisible();
  }

  async crossCheckSpecialists(): Promise<SpecialistView[]> {
    const response = await this.page.request.get("/api/ton/agent/specialists");
    expect(response.ok()).toBe(true);
    const specialists: SpecialistView[] = await response.json();
    expect(specialists).toHaveLength(9);
    for (const specialist of specialists) {
      const card = this.page.getByRole("article").filter({
        has: this.page.getByRole("heading", {
          name: specialist.name,
          exact: true,
        }),
      });
      await expect(card).toContainText(specialist.status);
      await expect(card).toContainText(specialist.reason);
      if (
        [
          "CONTRACTS",
          "COMPLIANCE",
          "FLEET",
          "COO",
          "PROCUREMENT",
          "HR",
        ].includes(specialist.key)
      )
        expect(specialist.status).toBe("Aguardando fonte");
    }
    await this.page
      .getByRole("button", { name: /View details|Ver detalhes/ })
      .first()
      .click();
    await expect(this.page.getByRole("dialog")).toContainText(
      specialists[0]?.reason ?? ""
    );
    await this.page
      .getByRole("dialog")
      .getByRole("button", { name: /^(Close|Fechar)$/ })
      .click();
    return specialists;
  }

  async crossCheckRoutines(): Promise<RoutineView[]> {
    const response = await this.page.request.get("/api/ton/agent/routines");
    expect(response.ok()).toBe(true);
    const routines: RoutineView[] = await response.json();
    expect(routines).toHaveLength(9);
    for (const routine of routines) {
      const card = this.page.getByRole("article").filter({
        has: this.page.getByRole("heading", {
          name: new RegExp(`^${routine.key} ·`),
        }),
      });
      await expect(card).toContainText(routine.name);
      await expect(card).toContainText(routine.status);
      await expect(card).toContainText(routine.schedule);
    }
    return routines;
  }

  async crossCheckCoverage(): Promise<Record<string, number>> {
    const response = await this.page.request.get("/api/ton/agent/capabilities");
    expect(response.ok()).toBe(true);
    const capabilities: CapabilityView[] = await response.json();
    const counts: Record<string, number> = {};
    for (const item of capabilities)
      counts[item.status_label] = (counts[item.status_label] ?? 0) + 1;
    for (const [status, count] of Object.entries(counts)) {
      const card = this.page.getByRole("group", { name: status, exact: true });
      await expect(card).toContainText(String(count));
    }
    return counts;
  }

  async inspectReadiness(): Promise<void> {
    const snapshotResponse = await this.page.request.get(
      "/api/ton/agent/closing"
    );
    expect(snapshotResponse.ok()).toBe(true);
    const snapshot: {
      period: string;
      normalization_run_id: string;
      structure_version_id: string;
    } = await snapshotResponse.json();
    const readinessResponse = await this.page.request.get(
      `/api/ton/financial-domain/normalizations/${snapshot.normalization_run_id}/readiness?structure_version_id=${snapshot.structure_version_id}`
    );
    expect(readinessResponse.ok()).toBe(true);
    const readiness: {
      periods: {
        scope: { period: string };
        blockers: Record<string, number>;
      }[];
    } = await readinessResponse.json();
    const period = readiness.periods.find(
      (item) => item.scope.period === snapshot.period
    );
    expect(period).toBeDefined();
    for (const [code, count] of Object.entries(period?.blockers ?? {})) {
      const resolver = this.page.locator(`a[href$="blocker=${code}"]`).first();
      await expect(resolver.locator("..")).toContainText(String(count));
    }
    await this.page
      .getByRole("link", { name: /Resolve pending items|Resolver pendências/ })
      .first()
      .click();
    await expect(this.page).toHaveURL(
      /\/ton\/pendencias\?normalization=.+&unit=.*&period=.+&blocker=.+/
    );
    await this.page
      .getByRole("button", { name: /^(Inspect|Inspecionar)$/ })
      .first()
      .click();
    await expect(this.page.getByRole("dialog")).toBeVisible();
    await this.expectHumanLabels();
    await this.page.keyboard.press("Escape");
    await expect(this.page.getByRole("dialog")).toBeHidden();
  }

  async sourcesAndCancelUpload(): Promise<ClientSource[]> {
    const response = await this.page.request.get("/api/ton/data-sources");
    expect(response.ok()).toBe(true);
    const sources: ClientSource[] = await response.json();
    const statuses: Record<string, RegExp> = {
      CURRENT: /Atualizado/,
      PROCESSING: /Em processamento/,
      ATTENTION: /Requer atenção/,
      FAILED: /Falhou/,
      UNCONFIGURED: /Não configurad/,
    };
    for (const source of sources) {
      await expect(
        this.page.getByText(source.name, { exact: true }).first()
      ).toBeVisible();
      const card = this.page
        .getByRole("heading", { name: source.name, exact: true })
        .locator("xpath=ancestor::section[1]");
      await expect(card).toContainText(
        statuses[source.status] ?? source.status
      );
    }
    await this.page
      .getByRole("button", {
        name: /Update data|Atualizar dados|Add file|Adicionar arquivo/,
      })
      .first()
      .click();
    await expect(this.page.getByRole("dialog")).toBeVisible();
    await this.page
      .getByRole("dialog")
      .getByRole("button", { name: /^(Cancel|Cancelar)$/ })
      .click();
    await expect(this.page.getByRole("dialog")).toBeHidden();
    await this.page
      .getByText(/^(Import history|Histórico de importações)$/)
      .first()
      .click();
    await expect(
      this.page
        .getByRole("table", { name: /Import history|Histórico de importações/ })
        .first()
    ).toBeVisible();
    return sources;
  }

  async analyzeClosing(): Promise<void> {
    await this.inputBar.fill(
      "Analise o fechamento preliminar. Consulte fontes, prontidão e evidências. Gere um relatório interno de fechamento. Não aprove decisões financeiras."
    );
    await this.inputBar.sendButton.click();
    await expect(this.page).toHaveURL(/\/ton\/chat\?chatId=/);
    const execution = this.page.getByRole("region", {
      name: /TON analysis execution|Execução da análise TON/,
    });
    await expect(execution).toBeVisible({ timeout: 90000 });
    await expect(
      this.page.getByRole("button", { name: /Stop generation|Parar a geração/ })
    ).toBeHidden({ timeout: 180000 });
    await expect(execution).toContainText(
      /Analysis completed|Análise concluída/,
      { timeout: 90000 }
    );
    await expect(execution.locator("pre")).toHaveCount(0);
    await expect(
      execution.getByText(/affected records|registros afetados/).first()
    ).toBeVisible();
    await this.expectHumanLabels();
    await expect(
      execution
        .getByRole("link", { name: /Open report|Abrir relatório/ })
        .first()
    ).toBeVisible({ timeout: 90000 });
    await execution.getByText(/View technical data|Ver dados técnicos/).click();
    await expect(execution.locator("pre")).toBeVisible();
  }

  expectNoAdminDetour(): void {
    expect(this.visited.filter((path) => path.startsWith("/admin"))).toEqual(
      []
    );
  }
}
