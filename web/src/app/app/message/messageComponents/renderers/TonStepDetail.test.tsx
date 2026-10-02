/** @jest-environment jsdom */

import { render, screen } from "@tests/setup/test-utils";
import TonStepDetail from "@/app/app/message/messageComponents/renderers/TonStepDetail";

it("shows what each specialist did in a closing analysis", () => {
  render(
    <TonStepDetail
      toolName="Análise do fechamento"
      data={{
        output: {
          period: "2026-07-01",
          dre_status: "Pendente",
          blockers: {
            "Conciliação sem decisão": 1,
            "Unidade não vinculada": 2,
          },
          specialists: [
            {
              key: "CFO",
              name: "TON CFO",
              status: "Parcial",
              reason: "Prontidão consultada.",
            },
          ],
        },
        steps: [
          {
            specialist: "CFO",
            code: "Consulta das fontes",
            status: "Concluído",
            reason: null,
          },
          {
            specialist: "CFO",
            code: "Validação da base",
            status: "Bloqueado",
            reason: "Publicação financeira bloqueada.",
          },
        ],
      }}
    />
  );
  expect(
    screen.getByText("Julho de 2026: 3 pendências impedem a DRE · Pendente")
  ).toBeInTheDocument();
  expect(screen.getByText("TON CFO")).toBeInTheDocument();
  expect(
    screen.getByText("Validação da base — Publicação financeira bloqueada.")
  ).toBeInTheDocument();
});

it("ignores tools that are not TON queries", () => {
  const { container } = render(
    <TonStepDetail toolName="run_python" data={{ stdout: "ok" }} />
  );
  expect(container).toBeEmptyDOMElement();
});
