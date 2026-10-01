/** @jest-environment jsdom */

import { render, screen, setupUser, waitFor } from "@tests/setup/test-utils";
import useSWR from "swr";
import DrePage from "@/views/admin/DrePage";

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
  usePathname: () => "/admin/dre",
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

it("shows real style blockers and routes to readiness without a fabricated result", () => {
  render(<DrePage />);
  expect(screen.getByRole("region", { name: "Not ready" })).toBeInTheDocument();
  expect(screen.getByText("Unmapped units")).toBeInTheDocument();
  expect(screen.getByText("Unresolved budget periods")).toBeInTheDocument();
  expect(
    screen.getAllByRole("link", { name: "Resolve pending items" })[0]
  ).toHaveAttribute(
    "href",
    expect.stringContaining("/ton/pendencias?normalization=normalization-1")
  );
  expect(screen.queryByText("Synthetic service")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Export CSV" })
  ).not.toBeInTheDocument();
});

it("renders stored READY lines, YTD, chart, null percent, and paged provenance", async () => {
  scenario = "ready";
  const user = setupUser();
  render(<DrePage />);
  expect(screen.getByText("Official stored result")).toBeInTheDocument();
  expect(
    screen.getByRole("region", { name: "DRE statement" })
  ).toBeInTheDocument();
  expect(screen.getByTestId("dre-chart")).toBeInTheDocument();
  expect(screen.getAllByText("Realizado YTD").length).toBeGreaterThan(0);
  expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  expect(screen.getByRole("button", { name: "Export CSV" })).toBeEnabled();
  await user.click(screen.getByRole("button", { name: "Synthetic service" }));
  expect(screen.getByText("SYN-1 · Synthetic account")).toBeInTheDocument();
  expect(
    screen.getByText("Review status: JUSTIFIED_EXCEPTION")
  ).toBeInTheDocument();
  expect(screen.getByText("Source sheet Jan, row 4")).toBeInTheDocument();
  expect(screen.getByText("Synthetic NG, synthetic.xlsx")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
  await user.click(
    screen.getByRole("button", { name: "Collapse Gross synthetic" })
  );
  expect(
    screen.queryByRole("button", { name: "Synthetic service" })
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Version details" }));
  expect(screen.getByText("Mapping revision")).toBeInTheDocument();
});

it("shows loading, error, and empty states", () => {
  scenario = "loading";
  const view = render(<DrePage />);
  expect(screen.getByRole("status")).toBeInTheDocument();
  scenario = "error";
  view.rerender(<DrePage />);
  expect(screen.getByText("Could not load DRE data.")).toBeInTheDocument();
  scenario = "empty";
  view.rerender(<DrePage />);
  expect(
    screen.getByText("No normalization or DRE structure is available.")
  ).toBeInTheDocument();
});

it("runs calculation only after explicit action", async () => {
  scenario = "ready";
  const user = setupUser();
  render(<DrePage />);
  expect(global.fetch).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Recalculate DRE" }));
  await waitFor(() =>
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/ton/dre/calculations",
      expect.objectContaining({ method: "POST" })
    )
  );
});
