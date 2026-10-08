/** @jest-environment jsdom */

import { render, screen } from "@tests/setup/test-utils";
import { TonToolCard } from "@/app/app/message/messageComponents/renderers/TonToolCard";

it("turns readiness blockers into the exact queue actions", () => {
  render(
    <TonToolCard
      toolName="ton_analyze_closing"
      data={{
        data: {
          output: {
            period: "2026-07-01",
            dre_status: "Pendente",
            blockers: {
              "Conciliação sem decisão": 1,
              "Períodos sem realizado no escopo": 6,
            },
          },
        },
      }}
    />
  );
  expect(screen.getByText("Conciliação · 1")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Resolver" })).toHaveAttribute(
    "href",
    "/ton/pendencias?period=2026-07-01&blocker=SOURCE_RECONCILIATION_UNRESOLVED"
  );
  expect(screen.getByRole("link", { name: "Importar" })).toHaveAttribute(
    "href",
    "/ton/pendencias?period=2026-07-01&blocker=NO_ACTUAL"
  );
});

it("summarizes what changed and points to pending recomputes", () => {
  render(
    <TonToolCard
      toolName="ton_get_recent_changes"
      data={{
        data: {
          changes: {
            previous_started_at: "2026-10-02T09:00:00Z",
            pending_decisions: 1,
            periods: [
              {
                period: "2026-07-01",
                blockers_before: { "Conciliação sem decisão": 2 },
                blockers_after: { "Conciliação sem decisão": 1 },
              },
            ],
          },
          decisions: { pending_decisions: 1, entries: [{}, {}] },
        },
      }}
    />
  );
  expect(
    screen.getByText("Pendências da DRE: 2 antes → 1 agora")
  ).toBeInTheDocument();
  expect(
    screen.getByText("2 decisões recentes; 1 aguarda recálculo")
  ).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Recalcular agora" })
  ).toHaveAttribute("href", "/ton/pendencias");
});

it("shows the automation draft card, also for drafts saved before the card kind fix", () => {
  const draft = {
    automation_id: "bf6c04a7-ece9-429a-8fd0-d8ab662049b3",
    name: "Aviso semanal de contas sem classificação",
    status: "DRAFT",
    created: true,
    summary: "Toda sexta às 17h avisa no TON.",
    when: "Toda sexta às 17:00",
    steps_text: ["Quando: Recorrência", "• Buscar contas sem classificação"],
    problems: [],
    missing: [],
    editor_url: "/ton/automacoes/bf6c04a7-ece9-429a-8fd0-d8ab662049b3/editar",
  };
  const { unmount } = render(
    <TonToolCard toolName="ton_draft_automation" data={{ ...draft, kind: "automation_draft", automation_kind: "ALERT" }} />
  );
  expect(screen.getByText("Aviso semanal de contas sem classificação")).toBeInTheDocument();
  expect(screen.getByText("Alerta")).toBeInTheDocument();
  unmount();
  render(<TonToolCard toolName="ton_draft_automation" data={{ ...draft, kind: "ALERT" }} />);
  expect(screen.getByText("Aviso semanal de contas sem classificação")).toBeInTheDocument();
});
