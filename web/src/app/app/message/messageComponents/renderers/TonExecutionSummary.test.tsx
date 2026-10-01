import { render, screen, setupUser } from "@tests/setup/test-utils";
import { TonExecutionSummary } from "@/app/app/message/messageComponents/renderers/TonExecutionSummary";
import { TonToolCard } from "@/app/app/message/messageComponents/renderers/TonToolCard";
import { PacketType } from "@/app/app/services/streamingModels";
import type { TurnGroup } from "@/app/app/message/messageComponents/timeline/transformers";

const mockPermissions: string[] = [];
jest.mock("@/providers/UserProvider", () => ({
  useUser: () => ({ user: { effective_permissions: mockPermissions } }),
}));

const groups: TurnGroup[] = [0, 1].map((turnIndex) => ({
  turnIndex,
  isParallel: false,
  steps: [
    {
      key: String(turnIndex),
      turnIndex,
      tabIndex: 0,
      packets: [
        {
          placement: { turn_index: turnIndex, tab_index: 0 },
          obj: {
            type: PacketType.CUSTOM_TOOL_START,
            tool_name: "Evidência da pendência",
          },
        },
        {
          placement: { turn_index: turnIndex, tab_index: 0 },
          obj: {
            type: PacketType.CUSTOM_TOOL_DELTA,
            tool_name: "Evidência da pendência",
            response_type: "json",
            data: {
              evidence: [
                {
                  sheet_name: "Financeiro",
                  row_number: 12,
                  confidence_level: "HIGH",
                },
              ],
            },
          },
        },
        {
          placement: { turn_index: turnIndex, tab_index: 0 },
          obj: { type: PacketType.SECTION_END },
        },
      ],
    },
  ],
}));

beforeEach(() => mockPermissions.splice(0));

it("renders aggregate readiness evidence without inventing spreadsheet coordinates", () => {
  const { container } = render(
    <TonToolCard
      toolName="ton_get_readiness_evidence"
      data={{
        data_context: "Synthetic demonstration data",
        data: {
          rows: [
            {
              source_key: "001 - Synthetic unit",
              record_count: 2,
              status: "UNRESOLVED",
              evidence: "Exact source field from reviewed NG records",
            },
          ],
        },
      }}
    />
  );
  expect(
    screen.getByText("2 registros afetados · 001 - Unidade de demonstração")
  ).toBeInTheDocument();
  expect(screen.getByText("Sem decisão")).toBeInTheDocument();
  expect(container).not.toHaveTextContent("Synthetic unit");
  expect(container).not.toHaveTextContent("Synthetic demonstration data");
  expect(container).not.toHaveTextContent("Planilha");
  expect(container.querySelector("pre")).toBeNull();
});

it("keeps the analysis running between completed tool batches", () => {
  render(
    <TonExecutionSummary turnGroups={groups} tools={[]} stopped={false} />
  );
  expect(screen.getByText("TON está analisando…")).toBeInTheDocument();
  expect(screen.queryByText("Análise concluída")).not.toBeInTheDocument();
});

it("summarizes tools as business phases and keeps technical JSON out of the client DOM", () => {
  const { container } = render(
    <TonExecutionSummary turnGroups={groups} tools={[]} stopped />
  );
  expect(screen.getByText("Análise concluída")).toBeInTheDocument();
  expect(screen.getByText("Evidências consolidadas")).toBeInTheDocument();
  expect(screen.getByText("Evidência da pendência")).toBeInTheDocument();
  expect(screen.getByText("2 consultas · Concluída")).toBeInTheDocument();
  expect(screen.queryByText("Dados técnicos (JSON)")).not.toBeInTheDocument();
  expect(container.querySelector("pre")).toBeNull();
  expect(container.querySelector("details")).not.toHaveAttribute("open");
});

it("shows the evidence card below the answer once the analysis stops", () => {
  const { container, rerender } = render(
    <TonExecutionSummary
      part="artifacts"
      turnGroups={groups}
      tools={[]}
      stopped={false}
    />
  );
  expect(container).toBeEmptyDOMElement();
  rerender(
    <TonExecutionSummary
      part="artifacts"
      turnGroups={groups}
      tools={[]}
      stopped
    />
  );
  expect(
    screen.getByText(/Planilha Financeiro · linha 12/)
  ).toBeInTheDocument();
});

it("renders grouped technical payload only after an administrator opens it", async () => {
  mockPermissions.push("admin");
  const user = setupUser();
  const { container } = render(
    <TonExecutionSummary turnGroups={groups} tools={[]} stopped />
  );
  expect(container.querySelector("pre")).toBeNull();
  await user.click(screen.getByText("Ver detalhes da análise"));
  await user.click(screen.getByText("Dados técnicos (JSON)"));
  expect(container.querySelector("pre")).toHaveTextContent("row_number");
});
