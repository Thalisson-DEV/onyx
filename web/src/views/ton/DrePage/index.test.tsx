/** @jest-environment jsdom */

import {
  render,
  screen,
  setupUser,
  waitFor,
  within,
} from "@tests/setup/test-utils";
import useSWR from "swr";
import { DreWorkspaceView } from "@/views/ton/DrePage";

jest.mock("swr", () => ({
  __esModule: true,
  ...jest.requireActual("swr"),
  default: jest.fn(),
}));

jest.mock("@/providers/UserProvider", () => ({
  useUser: () => ({ user: { effective_permissions: ["admin"] } }),
}));

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn(), back: jest.fn() }),
  usePathname: () => "/ton/dre",
  useSearchParams: () => new URLSearchParams(),
}));

jest.mock("next-intl", () => ({
  ...jest.requireActual("next-intl"),
  useFormatter: () => ({
    dateTime: (value: Date) => value.toISOString().slice(0, 10),
    number: (value: number) => String(value),
  }),
}));

jest.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="dre-chart">{children}</div>
  ),
  Bar: () => null,
  CartesianGrid: () => null,
  Legend: () => null,
  Tooltip: () => null,
  XAxis: () => null,
  YAxis: () => null,
}));

const mockUseSWR = useSWR as jest.MockedFunction<typeof useSWR>;
let scenario: "blocked" | "ready" | "loading" | "error" | "empty" = "blocked";
const result = {
  id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  status: "READY",
  scope: {
    normalization_run_id: "normalization-1",
    structure_version_id: "version-1",
    period: "2026-01-01",
    unit_id: null,
  },
  blockers: {},
  provenance: {
    financial_mapping_revision: 3,
    amount_basis_revision: 2,
    budget_execution_ids: ["budget-1"],
  },
  finished_at: "2026-01-02T12:00:00Z",
};
const definitions = [
  {
    code: "gross",
    label: "Gross synthetic",
    position: 1,
    parent_code: null,
    line_type: "SUBTOTAL",
  },
  {
    code: "service",
    label: "Synthetic service",
    position: 2,
    parent_code: "gross",
    line_type: "SOURCE_SUM",
  },
  {
    code: "result",
    label: "Synthetic result",
    position: 3,
    parent_code: null,
    line_type: "RESULT",
  },
];
const lines = definitions.map((line) => ({
  code: line.code,
  label: line.label,
  position: line.position,
  realizado: line.code === "result" ? "-20" : "100",
  orcado: line.code === "result" ? "0" : "80",
  variance: line.code === "result" ? "-20" : "20",
  variance_percent: line.code === "result" ? null : "25",
  realizado_ytd: "150",
  orcado_ytd: "120",
  variance_ytd: "30",
  variance_percent_ytd: "25",
}));

function responseFor(key: string | null): unknown {
  if (!key) return undefined;
  if (key.includes("/normalizations?"))
    return [{ id: "normalization-1", started_at: "2026-01-02T00:00:00Z" }];
  if (key.includes("/structures?"))
    return [{ id: "structure-1", label: "Synthetic DRE" }];
  if (key.includes("/units?"))
    return [{ id: "unit-1", code: "SYN", name: "Synthetic unit" }];
  if (key.includes("latest-version"))
    return { id: "version-1", number: 1, lines: definitions };
  if (key.includes("/readiness?"))
    return {
      periods: [
        {
          status: scenario === "ready" ? "READY" : "NOT_READY",
          scope: { period: "2026-01-01" },
          blockers:
            scenario === "ready"
              ? {}
              : { UNMAPPED_UNIT: 3, BUDGET_PERIOD_UNRESOLVED: 2 },
        },
      ],
    };
  if (key.includes("/calculations?"))
    return scenario === "ready" ? [result] : [];
  if (key.includes("/statement"))
    return {
      run: result,
      version: { id: "version-1", number: 1, lines: definitions },
      lines,
    };
  if (key.includes("/series?"))
    return [
      {
        period: "2026-01-01",
        result_id: result.id,
        realizado: "-20",
        orcado: "0",
        variance: "-20",
      },
    ];
  if (key.includes("/contributors?"))
    return {
      total: 2,
      rows: [
        {
          id: "fact-1",
          fact_type: "ACTUAL",
          account_code: "SYN-1",
          account_label: "Synthetic account",
          unit_code: "SYN",
          amount: "100",
          amount_basis: "MOVEMENT",
          record_date: "2026-01-08",
          source_name: "Synthetic NG",
          original_filename: "synthetic.xlsx",
          reference: "SYN-DOC",
          sheet_name: "Jan",
          source_row_number: 4,
          review_status: "JUSTIFIED_EXCEPTION",
        },
      ],
    };
  return undefined;
}

beforeEach(() => {
  scenario = "blocked";
  jest.clearAllMocks();
  mockUseSWR.mockImplementation(
    (key) =>
      ({
        data:
          scenario === "loading" || scenario === "error" || scenario === "empty"
            ? undefined
            : responseFor(key as string | null),
        error: scenario === "error" ? new Error("Synthetic error") : undefined,
        isLoading: scenario === "loading",
        isValidating: false,
        mutate: jest.fn(),
      }) as ReturnType<typeof useSWR>
  );
  global.fetch = jest
    .fn()
    .mockResolvedValue({ ok: true, json: async () => result });
});

it("explains the blocked DRE by business category and links each to the queue", () => {
  render(<DreWorkspaceView />);
  expect(
    screen.getByRole("heading", {
      name: "DRE de janeiro de 2026 ainda não pode ser publicada",
    })
  ).toBeInTheDocument();
  expect(screen.getByText("5 itens exigem atenção")).toBeInTheDocument();
  const resolve = screen.getAllByRole("link", { name: "Resolver" });
  expect(resolve[0]).toHaveAttribute(
    "href",
    expect.stringContaining("blocker=UNMAPPED_UNIT")
  );
  expect(resolve[1]).toHaveAttribute(
    "href",
    expect.stringContaining("blocker=BUDGET_PERIOD_UNRESOLVED")
  );
  // No figures exist while blocked.
  expect(screen.queryByText("Synthetic service")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Exportar CSV" })
  ).not.toBeInTheDocument();
});

it("renders the official statement with month, YTD, variance and drill-down", async () => {
  scenario = "ready";
  const user = setupUser();
  const { container } = render(<DreWorkspaceView />);
  expect(screen.getByText("Resultado oficial")).toBeInTheDocument();
  expect(screen.getByRole("table")).toBeInTheDocument();
  expect(
    screen.getByRole("columnheader", { name: "Acumulado" })
  ).toBeInTheDocument();
  // A null variance percent stays a dash, never zero.
  expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  expect(screen.getByRole("button", { name: "Exportar CSV" })).toBeEnabled();

  await user.click(
    screen.getByRole("button", { name: "Ver composição de Synthetic service" })
  );
  const drawer = screen.getByRole("dialog");
  // Entries read as a table; the source file is stated once in the header.
  expect(within(drawer).getByRole("table")).toBeInTheDocument();
  expect(drawer).toHaveTextContent("SYN-1");
  expect(drawer).toHaveTextContent("Jan · 4");
  expect(drawer).toHaveTextContent("Origem: Synthetic NG · synthetic.xlsx");
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

  await user.click(
    screen.getByRole("button", { name: "Recolher Gross synthetic" })
  );
  expect(
    screen.queryByRole("button", {
      name: "Ver composição de Synthetic service",
    })
  ).not.toBeInTheDocument();
  // Internal identifiers stay out of the client view.
  expect(container).not.toHaveTextContent("aaaaaaaa");
});

it("shows loading, error and unconfigured states", () => {
  scenario = "loading";
  const view = render(<DreWorkspaceView />);
  expect(screen.getByRole("status")).toBeInTheDocument();
  scenario = "error";
  view.rerender(<DreWorkspaceView />);
  expect(screen.getByRole("alert")).toBeInTheDocument();
  scenario = "empty";
  view.rerender(<DreWorkspaceView />);
  expect(
    screen.getByText(
      "A DRE ainda não tem base normalizada ou estrutura configurada."
    )
  ).toBeInTheDocument();
});

it("recalculates only on explicit action and reports the outcome", async () => {
  const user = setupUser();
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ ...result, status: "NOT_READY" }),
  });
  render(<DreWorkspaceView />);
  expect(global.fetch).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Recalcular DRE" }));
  await waitFor(() =>
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/ton/dre/calculations",
      expect.objectContaining({ method: "POST" })
    )
  );
  expect(
    await screen.findByText(
      "Recálculo concluído: a DRE continua bloqueada pelos itens abaixo."
    )
  ).toBeInTheDocument();
});
