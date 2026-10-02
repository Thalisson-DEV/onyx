/** @jest-environment jsdom */

import { render, screen, setupUser } from "@tests/setup/test-utils";
import useSWR from "swr";
import PendingPage from "@/views/ton/PendingPage";

jest.mock("swr", () => ({
  __esModule: true,
  ...jest.requireActual("swr"),
  default: jest.fn(),
}));
jest.mock("@/providers/UserProvider", () => ({
  useUser: () => ({ user: { effective_permissions: ["admin"] } }),
}));
const mockParams = { value: "categoria=reconciliation" };
jest.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(mockParams.value),
  useRouter: () => ({ push: jest.fn(), replace: jest.fn(), back: jest.fn() }),
  usePathname: () => "/ton/pendencias",
}));

const RECONCILIATION_ROWS = [
  {
    source_id: null,
    source_key: null,
    account_id: null,
    item_id: "23bb59a2-d35f-449a-b9ce-77f769f1f6ca",
    record_count: 1,
    periods: ["2026-01-01"],
    status: "UNRESOLVED",
    candidate: null,
    legacy_evidence: null,
    line_candidate: null,
    paired: false,
    evidence:
      "BILLING_ONLY; NG no; billing yes; account mapped yes; unit mapped yes; document match unknown; amount relation unverified",
    records: [
      {
        origin: "BILLING",
        document: "4512",
        emission_date: "2026-01-10",
        period: "2026-01-01",
        account: null,
        unit: null,
        counterparty: "Cliente sintético",
        description: null,
        movement_amount: null,
        final_amount: null,
        service_amount: "100.2500000000",
        net_amount: null,
        sheet: "Export",
        row: 4,
      },
    ],
  },
];
const BUDGET_ROWS = [
  {
    source_id: "source-2",
    source_key: "408e7060-69eb-4fbc-ac55-c546b82df0b3",
    account_id: null,
    item_id: null,
    record_count: 2,
    periods: [],
    status: "UNRESOLVED",
    candidate: null,
    legacy_evidence: null,
    line_candidate: null,
    paired: null,
    evidence: "MONTHLY_CONTRACT: source has no approved calendar start",
    records: [],
  },
];
const MISSING_MONTHS = {
  total: 2,
  covered_periods: ["2026-07-01"],
  rows: ["2026-05-01", "2026-06-01"].map((period) => ({
    source_id: null,
    source_key: "NO_ACTUAL",
    account_id: null,
    item_id: null,
    record_count: 0,
    periods: [period],
    status: "UNRESOLVED",
    candidate: null,
    legacy_evidence: null,
    line_candidate: null,
    paired: null,
    evidence: "Import reviewed NG actuals for this period",
    records: [],
  })),
};
const READY_AFTER = {
  periods: [
    {
      status: "NOT_READY",
      scope: { period: "2026-07-01" },
      blockers: {
        SOURCE_RECONCILIATION_UNRESOLVED: 2,
        BUDGET_PERIOD_UNRESOLVED: 2,
        NO_ACTUAL: 6,
      },
    },
  ],
};

function json(body: unknown) {
  return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
}

beforeEach(() => {
  mockParams.value = "categoria=reconciliation";
  global.fetch = jest.fn((path: string) =>
    path.includes("/recompute")
      ? json({ id: "run-2" })
      : path.includes("/readiness?")
        ? json(READY_AFTER)
        : path.includes("/decisions")
          ? json({
              pending_decisions: 0,
              entries: [
                {
                  kind: "RECONCILIATION",
                  subject: "4512",
                  outcome: "EXPECTED_DIFFERENCE",
                  reason: "Nota fiscal conferida",
                  decided_by: "controladoria@example.com",
                  decided_at: "2026-10-02T09:00:00Z",
                  version: 4,
                  applied: true,
                },
              ],
            })
          : json({ revision_number: 4 })
  ) as jest.Mock;
  const mockSWR = useSWR as jest.MockedFunction<typeof useSWR>;
  mockSWR.mockImplementation((key) => {
    const path = typeof key === "string" ? key : "";
    const data = path.includes("/blockers/SOURCE_RECONCILIATION_UNRESOLVED")
      ? { total: 1, rows: RECONCILIATION_ROWS }
      : path.includes("/blockers/BUDGET_PERIOD_UNRESOLVED")
        ? { total: 1, rows: BUDGET_ROWS }
        : path.includes("/blockers/NO_ACTUAL")
          ? MISSING_MONTHS
          : path.includes("/readiness?")
            ? {
                periods: [
                  {
                    status: "NOT_READY",
                    scope: { period: "2026-07-01" },
                    blockers: {
                      SOURCE_RECONCILIATION_UNRESOLVED: 3,
                      BUDGET_PERIOD_UNRESOLVED: 2,
                      NO_ACTUAL: 6,
                    },
                  },
                ],
              }
            : path.includes("/latest-version")
              ? { id: "version-1", number: 1, lines: [] }
              : path.includes("/structures?")
                ? [{ id: "structure-1", label: "Estrutura", latest_version: 1 }]
                : path.includes("/normalizations?")
                  ? [
                      {
                        id: "run-1",
                        mapping_revision_number: 8,
                        started_at: "2026-10-01T01:00:00Z",
                      },
                    ]
                  : path.includes("/agent/closing") ||
                      path.includes("/readiness/changes")
                    ? undefined
                    : path.includes("/decisions")
                      ? { pending_decisions: 0, entries: [] }
                      : [];
    return {
      data,
      isLoading: false,
      isValidating: false,
      error: undefined,
      mutate: jest.fn(),
    } as ReturnType<typeof useSWR>;
  });
});

it("opens the requested category with business titles and no identifiers", () => {
  const { container } = render(<PendingPage />);
  expect(
    screen.getByRole("heading", { name: "Conciliação" })
  ).toBeInTheDocument();
  expect(
    screen.getAllByText("Somente faturamento disponível").length
  ).toBeGreaterThan(0);
  expect(screen.getByText("Realizado ausente")).toBeInTheDocument();
  // The row identifies the source record: document, counterparty and value.
  expect(container).toHaveTextContent("4512 · Cliente sintético");
  expect(container).toHaveTextContent("R$ 100,25");
  expect(container).not.toHaveTextContent("23bb59a2");
  expect(container).not.toHaveTextContent("BILLING_ONLY");
});

it("titles budget rows by meaning instead of the source identifier", () => {
  mockParams.value = "blocker=BUDGET_PERIOD_UNRESOLVED";
  const { container } = render(<PendingPage />);
  expect(
    screen.getByText("O orçamento mensal não tem data inicial aprovada")
  ).toBeInTheDocument();
  expect(container).not.toHaveTextContent("408e7060");
});

it("requires an explicit decision, a justification and a second confirmation", async () => {
  const user = setupUser();
  render(<PendingPage />);
  await user.click(screen.getByRole("button", { name: "Revisar e decidir" }));
  const review = screen.getByRole("button", { name: "Revisar decisão" });
  expect(review).toBeDisabled();
  await user.click(screen.getByRole("radio", { name: /Diferença esperada/ }));
  expect(review).toBeDisabled();
  await user.type(
    screen.getByRole("textbox", { name: "Justificativa" }),
    "Nota fiscal conferida"
  );
  expect(review).toBeEnabled();
  await user.click(review);
  expect(global.fetch).not.toHaveBeenCalled();
  expect(screen.getByText("Confirme antes de registrar")).toBeInTheDocument();
  // The step indicator shows the confirmation step as current.
  expect(
    screen
      .getByRole("list", { name: "Etapas da decisão" })
      .querySelector('[aria-current="step"]')
  ).toHaveTextContent("3");
  await user.click(screen.getByRole("button", { name: "Confirmar decisão" }));
  const calls = (global.fetch as jest.Mock).mock.calls;
  const [path, init] = calls[0];
  expect(path).toContain("/reconciliation/items/");
  expect(JSON.parse(init.body)).toEqual({
    decision: "EXPECTED_DIFFERENCE",
    reason: "Nota fiscal conferida",
  });
  // The decision is applied by an explicit recompute of the same base.
  expect(calls[1][0]).toContain("/normalizations/run-1/recompute");
  // The result shows who decided, the version and the before/after counts.
  expect(await screen.findByText("Decisão registrada")).toBeInTheDocument();
  expect(
    screen.getByText(/Versão 4 · controladoria@example.com/)
  ).toBeInTheDocument();
  const conciliation = screen
    .getAllByRole("row")
    .find((row) => row.textContent?.startsWith("Conciliação"));
  expect(conciliation).toHaveTextContent("Conciliação32");
});

it("shows the evidence and what each reconciliation option means", async () => {
  const user = setupUser();
  render(<PendingPage />);
  await user.click(screen.getByRole("button", { name: "Revisar e decidir" }));
  expect(screen.getByText("Não muda números da DRE")).toBeInTheDocument();
  expect(screen.getByText("Nota fiscal")).toBeInTheDocument();
  expect(
    screen.getByRole("radio", { name: /Diferença esperada/ })
  ).toHaveTextContent("prazo, retenção ou arredondamento");
  expect(
    screen.getByRole("link", { name: "Perguntar ao TON sobre este item" })
  ).not.toHaveAttribute("href", expect.stringContaining("100"));
});

it("treats missing months as a data import, not a decision", () => {
  mockParams.value = "blocker=NO_ACTUAL";
  const { container } = render(<PendingPage />);
  expect(container).toHaveTextContent("A base atual tem");
  expect(screen.getByText("jul/2026")).toBeInTheDocument();
  expect(screen.getByText("mai/2026")).toBeInTheDocument();
  expect(screen.getByText("jun/2026")).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Revisar e decidir" })
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Importar lançamentos do NG" })
  ).toHaveAttribute(
    "href",
    "/ton/fontes?importar=financial_launches&ate=2026-07"
  );
});
