/** @jest-environment jsdom */

import { render, screen, setupUser, waitFor } from "@tests/setup/test-utils";
import useSWR from "swr";
import FinancialReadinessPage from "./index";

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
  usePathname: () => "/admin/financial-readiness",
}));

jest.mock("next-intl", () => ({
  ...jest.requireActual("next-intl"),
  useFormatter: () => ({ dateTime: (value: Date) => value.toISOString() }),
}));

const mockUseSWR = useSWR as jest.MockedFunction<typeof useSWR>;
const sourceId = "11111111-1111-4111-8111-111111111111";
const targetId = "22222222-2222-4222-8222-222222222222";
let mode: "ready" | "loading" | "error" | "empty" = "ready";

function responseFor(key: string | null) {
  if (!key) return undefined;
  if (key.includes("latest-version")) return { id: "v1", number: 1, lines: [] };
  if (key.includes("/readiness/blockers/"))
    return {
      total: 1,
      rows: [
        {
          source_id: sourceId,
          source_key: "SYN-UNIT",
          account_id: null,
          item_id: null,
          record_count: 3,
          periods: ["2026-01-01"],
          status: "CANDIDATE",
          candidate: {
            target_id: targetId,
            code: "SYN-UNIT",
            label: "Synthetic unit",
            evidence: "EXACT_CODE",
          },
          legacy_evidence: null,
          evidence: "Exact source field",
        },
      ],
    };
  if (key.includes("/readiness?"))
    return {
      periods: [
        {
          status: "NOT_READY",
          scope: { period: "2026-01-01" },
          blockers: { UNMAPPED_UNIT: 3 },
        },
      ],
    };
  if (key.includes("/normalizations?"))
    return [{ id: "run-1", started_at: "2026-01-02T00:00:00Z" }];
  if (key.includes("/structures?"))
    return [{ id: "structure-1", label: "Synthetic DRE", latest_version: 1 }];
  if (key.includes("/units?"))
    return [{ id: targetId, code: "SYN-UNIT", name: "Synthetic unit" }];
  return [];
}

beforeEach(() => {
  mode = "ready";
  jest.clearAllMocks();
  mockUseSWR.mockImplementation(
    (key) =>
      ({
        data:
          mode === "ready"
            ? responseFor(key as string | null)
            : mode === "empty"
              ? []
              : undefined,
        error: mode === "error" ? new Error("Synthetic failure") : undefined,
        isLoading: mode === "loading",
        isValidating: false,
        mutate: jest.fn(),
      }) as ReturnType<typeof useSWR>,
  );
  global.fetch = jest.fn().mockResolvedValue({ ok: true, status: 200 });
});

it("shows loading, error, and empty states", () => {
  mode = "loading";
  const view = render(<FinancialReadinessPage />);
  expect(screen.getByRole("status")).toBeInTheDocument();
  mode = "error";
  view.rerender(<FinancialReadinessPage />);
  expect(
    screen.getByText("Could not load financial readiness."),
  ).toBeInTheDocument();
  mode = "empty";
  view.rerender(<FinancialReadinessPage />);
  expect(
    screen.getByText("No normalization run or DRE structure is available."),
  ).toBeInTheDocument();
});

it("requires a reason and confirmation before approving a candidate", async () => {
  const user = setupUser();
  render(<FinancialReadinessPage />);
  expect(screen.getByText("Not ready")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Inspect" }));
  const review = screen.getByRole("button", { name: "Review approval" });
  expect(review).toBeDisabled();
  await user.type(
    screen.getByRole("textbox", { name: "Reason or reference" }),
    "Checked source code",
  );
  await user.click(review);
  expect(global.fetch).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Apply decision" }));
  await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));
  const call = jest.mocked(global.fetch).mock.calls[0];
  expect(call).toBeDefined();
  if (!call) throw new Error("Approval request missing");
  const [path, request] = call;
  expect(path).toBe("/api/ton/financial-domain/mappings");
  expect(JSON.parse(String(request?.body))).toMatchObject({
    source_id: sourceId,
    source_key: "SYN-UNIT",
    unit_id: targetId,
    reason: "Checked source code",
  });
});
