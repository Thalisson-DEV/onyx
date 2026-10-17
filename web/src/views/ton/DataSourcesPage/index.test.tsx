/** @jest-environment jsdom */

import { render, screen, setupUser, waitFor } from "@tests/setup/test-utils";
import useSWR from "swr";
import DataSourcesPage from "@/views/ton/DataSourcesPage";

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
  usePathname: () => "/ton/data-sources",
}));

jest.mock("next-intl", () => ({
  ...jest.requireActual("next-intl"),
  useFormatter: () => ({
    dateTime: (value: Date) => value.toISOString().slice(0, 10),
    number: (value: number) => String(value),
  }),
}));

const mockUseSWR = useSWR as jest.MockedFunction<typeof useSWR>;
const source = {
  key: "billing_invoices",
  name: "Faturamento / Notas fiscais",
  description: "Notas fiscais e valores de faturamento.",
  format: "XLS",
  source_id: "11111111-1111-4111-8111-111111111111",
  can_import: true,
  status: "CURRENT",
  last_success_at: null,
  last_attempt_at: null,
  latest: null,
  history: [],
};
const result = {
  id: "22222222-2222-4222-8222-222222222222",
  source_id: source.source_id,
  status: "PARTIAL",
  filename: "synthetic.xls",
  format: "XLS",
  size_bytes: 1024,
  started_at: "2026-01-01T00:00:00Z",
  finished_at: "2026-01-01T00:00:01Z",
  imported: 2,
  rejected: 1,
  warnings: 1,
  errors: 1,
  needs_review: null,
  available_for_analysis: null,
  diagnostics: [{ code: "INVALID_AMOUNT", count: 1 }],
  downstream: ["financial_readiness", "dre"],
};

beforeEach(() => {
  jest.clearAllMocks();
  mockUseSWR.mockReturnValue({
    data: [source],
    isLoading: false,
    isValidating: false,
    error: undefined,
    mutate: jest.fn(),
  } as ReturnType<typeof useSWR>);
  global.fetch = jest.fn();
});

it("shows a financial source and links to readiness and DRE", () => {
  render(<DataSourcesPage />);
  expect(screen.getByText(source.name)).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Financial readiness" })
  ).toHaveAttribute("href", "/ton/pendencias");
  expect(screen.getByRole("link", { name: "DRE" })).toHaveAttribute(
    "href",
    "/ton/dre"
  );
});

it("previews a billing file, then shows the result with its diagnostics", async () => {
  const user = setupUser();
  (global.fetch as jest.Mock)
    .mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        imported: 2,
        rejected: 1,
        has_previous_review: false,
        carried_over: 0,
        evidence_changed: 0,
        still_open: 0,
        reopened: 0,
        new: 0,
        not_detected: 0,
        changes_actuals: false,
      }),
    })
    .mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => result,
    });
  render(<DataSourcesPage />);
  await user.click(screen.getByRole("button", { name: "Add file" }));
  const file = new File(["synthetic"], "synthetic.xls", {
    type: "application/vnd.ms-excel",
  });
  await user.upload(screen.getByLabelText("Choose file"), file);
  await user.click(screen.getByRole("button", { name: "Ver o que muda" }));
  expect(
    await screen.findByText("2 notas lidas · 1 rejeitadas")
  ).toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: "Confirmar importação" })
  );
  await waitFor(() =>
    expect(screen.getByText("Needs attention")).toBeInTheDocument()
  );
  expect(screen.getByText("Invalid amount")).toBeInTheDocument();
  expect(screen.getByText("Rejeitados")).toBeInTheDocument();
  expect(screen.getByText(/^synthetic\.xls · .* · 1 KB$/)).toBeInTheDocument();
});

it("explains an unsupported structure", async () => {
  const user = setupUser();
  (global.fetch as jest.Mock).mockResolvedValue({ ok: false, status: 400 });
  render(<DataSourcesPage />);
  await user.click(screen.getByRole("button", { name: "Add file" }));
  const file = new File(["synthetic"], "synthetic.xls", {
    type: "application/vnd.ms-excel",
  });
  await user.upload(screen.getByLabelText("Choose file"), file);
  await user.click(screen.getByRole("button", { name: "Ver o que muda" }));
  await waitFor(() =>
    expect(
      screen.getByText(
        "This file does not match a recognized format for this source."
      )
    ).toBeInTheDocument()
  );
});
