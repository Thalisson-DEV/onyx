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
