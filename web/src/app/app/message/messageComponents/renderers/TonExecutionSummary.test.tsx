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

it("shows the evidence card below the answer once the analysis stops", () => {
  const { container, rerender } = render(
    <TonExecutionSummary turnGroups={groups} tools={[]} stopped={false} />
  );
  expect(container).toBeEmptyDOMElement();
  rerender(<TonExecutionSummary turnGroups={groups} tools={[]} stopped />);
  expect(
    screen.getByText(/Planilha Financeiro · linha 12/)
  ).toBeInTheDocument();
});

it("offers navigation follow-ups only for the areas the analysis touched", () => {
  render(<TonExecutionSummary turnGroups={groups} tools={[]} stopped={true} />);
  expect(screen.getByRole("link", { name: "Ver pendências" })).toHaveAttribute(
    "href",
    "/ton/pendencias"
  );
  expect(
    screen.queryByRole("link", { name: "Abrir DRE" })
  ).not.toBeInTheDocument();
});

it("shows no follow-ups while the analysis is still running", () => {
  render(
    <TonExecutionSummary turnGroups={groups} tools={[]} stopped={false} />
  );
  expect(
    screen.queryByRole("link", { name: "Ver pendências" })
  ).not.toBeInTheDocument();
});
