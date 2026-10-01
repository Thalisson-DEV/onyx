/** @jest-environment jsdom */

import { render, screen, setupUser } from "@tests/setup/test-utils";
import useSWR from "swr";
import FinancialReadinessPage from "@/views/admin/FinancialReadinessPage";

jest.mock("swr", () => ({
  __esModule: true,
  ...jest.requireActual("swr"),
  default: jest.fn(),
}));
jest.mock("@/providers/UserProvider", () => ({
  useUser: () => ({ user: { effective_permissions: ["admin"] } }),
}));
jest.mock("next/navigation", () => ({
  useSearchParams: () =>
    new URLSearchParams(
      "normalization=run-1&period=2026-07-01&blocker=UNMAPPED_UNIT"
    ),
  useRouter: () => ({ push: jest.fn(), replace: jest.fn(), back: jest.fn() }),
  usePathname: () => "/ton/pendencias",
}));
jest.mock("next-intl", () => ({
  ...jest.requireActual("next-intl"),
  useFormatter: () => ({
    dateTime: (date: Date) => date.toISOString().slice(0, 10),
    number: String,
  }),
}));

beforeEach(() => {
  global.fetch = jest.fn();
  const mockSWR = useSWR as jest.MockedFunction<typeof useSWR>;
  mockSWR.mockImplementation((key) => {
    const path = typeof key === "string" ? key : "";
    const data = path.includes("/blockers/")
      ? {
          total: 1,
          rows: [
            {
              source_id: "source-1",
              source_key: "001 - Synthetic unit",
              account_id: null,
              item_id: null,
              record_count: 2,
              periods: ["2026-07-01"],
              status: "UNMAPPED",
              candidate: null,
              legacy_evidence: null,
              line_candidate: null,
              paired: null,
              evidence: "Exact source field from reviewed NG records",
            },
          ],
        }
      : path.includes("/readiness?")
        ? {
            periods: [
              {
                status: "NOT_READY",
                scope: { period: "2026-07-01" },
                blockers: { UNMAPPED_UNIT: 2, NO_ACTUAL: 6 },
              },
            ],
          }
        : path.includes("/latest-version")
          ? { id: "version-1", number: 1, lines: [] }
          : path.includes("/structures?")
            ? [
                {
                  id: "structure-1",
                  label: "Estrutura de demonstração",
                  latest_version: 1,
                },
              ]
            : path.includes("/normalizations?")
              ? [
                  {
                    id: "run-1",
                    mapping_revision_number: 1,
                    started_at: "2026-07-01",
                  },
                ]
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

it("humanizes blocker categories, compound unit names and evidence during inspection", async () => {
  const user = setupUser();
  const { container } = render(<FinancialReadinessPage />);
  expect(container).not.toHaveTextContent("NO ACTUAL");
  expect(container).not.toHaveTextContent("Synthetic unit");
  expect(container).not.toHaveTextContent("UNMAPPED");
  expect(screen.getByText("001 - Unidade de demonstração")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Inspect" }));
  expect(screen.getByRole("dialog")).toHaveTextContent(
    "This approval can affect 2 records"
  );
  expect(screen.getByRole("dialog")).toHaveTextContent(
    "Origem: lançamentos financeiros revisados"
  );
  await user.click(screen.getByRole("button", { name: "Close" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(global.fetch).not.toHaveBeenCalled();
});
