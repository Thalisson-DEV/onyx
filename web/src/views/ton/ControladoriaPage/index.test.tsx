/** @jest-environment jsdom */

import { render, screen, setupUser, waitFor } from "@tests/setup/test-utils";
import useSWR from "swr";
import ControladoriaPage from "@/views/ton/ControladoriaPage";
import type {
  ClosingOutput,
  Publication,
} from "@/views/ton/ControladoriaPage/types";

jest.mock("swr", () => ({
  __esModule: true,
  ...jest.requireActual("swr"),
  default: jest.fn(),
}));
const mockPermissions = ["admin"];
jest.mock("@/providers/UserProvider", () => ({
  useUser: () => ({ user: { effective_permissions: mockPermissions } }),
}));
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn(), back: jest.fn() }),
  usePathname: () => "/ton/controladoria",
}));
jest.mock("next-intl", () => ({
  ...jest.requireActual("next-intl"),
  useFormatter: () => ({
    dateTime: (value: Date) => value.toISOString().slice(0, 10),
    number: (value: number) => String(value),
  }),
}));

const output: ClosingOutput = {
  period: "2026-01-01",
  scope: "Consolidado",
  unit_id: null,
  normalization_run_id: null,
  structure_version_id: null,
  data_context: "Dados sintéticos de demonstração.",
  sources: [],
  specialists: [
    {
      key: "CFO",
      name: "CFO",
      status: "Parcial",
      reason: "Synthetic missing source",
      actions: [],
      limitations: [],
    },
  ],
  findings: [],
  findings_scope: "Synthetic review scope",
  findings_may_have_more: false,
  dre_status: "Pendente",
  blockers: { "Synthetic missing account": 1 },
  executive_brief: { IMPACTO: "Não quantificado" },
  generated_at: "2026-01-02T00:00:00Z",
};
const publication: Publication = {
  run_id: "synthetic-run",
  report_id: "synthetic-report",
  revision_id: "synthetic-revision",
  status: "Concluído com bloqueios",
  routine_code: "R3",
  report_url: "/ton/controladoria/reports/synthetic-revision",
  download_url: "/api/ton/agent/reports/synthetic-revision/download",
  output,
  steps: [],
};
const mockUseSWR = useSWR as jest.MockedFunction<typeof useSWR>;

beforeEach(() => {
  jest.clearAllMocks();
  mockPermissions.splice(0, mockPermissions.length, "admin");
  Object.defineProperty(globalThis.crypto, "randomUUID", {
    configurable: true,
    value: jest.fn(() => "11111111-1111-4111-8111-111111111111"),
  });
  mockUseSWR.mockImplementation((key) => {
    const url = typeof key === "string" ? key : "";
    const data = url.includes("/closing")
      ? output
      : url.includes("/configuration")
        ? { persona_id: 5 }
        : url.includes("/routines")
          ? [
              {
                key: "R3",
                name: "Fechamento preliminar",
                status: "Execução manual disponível",
                reason: "Synthetic dependency",
                schedule: "Agendamento não configurado",
                manual_available: true,
              },
            ]
          : url
            ? []
            : undefined;
    return {
      data,
      isLoading: false,
      isValidating: false,
      error: undefined,
      mutate: jest.fn(),
    } as ReturnType<typeof useSWR>;
  });
  global.fetch = jest.fn();
});

it("shows the synthetic notice, blockers and chat navigation", () => {
  render(<ControladoriaPage />);
  expect(screen.getByText(output.data_context)).toBeInTheDocument();
  expect(screen.getByText("Synthetic missing account: 1")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open TON chat" })).toHaveAttribute(
    "href",
    "/app?agentId=5"
  );
  expect(screen.getByRole("button", { name: "Run now" })).toBeEnabled();
});

it("recovers the same execution request after failure and opens its persisted result", async () => {
  const user = setupUser();
  (global.fetch as jest.Mock)
    .mockResolvedValueOnce({ ok: false })
    .mockResolvedValueOnce({ ok: true, json: async () => publication });
  render(<ControladoriaPage />);
  await user.click(screen.getByRole("button", { name: "Run now" }));
  await screen.findByText(
    "Execution failed. Try again to recover or complete the same request."
  );
  await user.click(screen.getByRole("button", { name: "Run now" }));
  await waitFor(() =>
    expect(screen.getByRole("link", { name: "Open result" })).toHaveAttribute(
      "href",
      publication.report_url
    )
  );
  const requests = (global.fetch as jest.Mock).mock.calls;
  expect(requests).toHaveLength(2);
  expect(JSON.parse(requests[0][1].body).request_id).toEqual(
    JSON.parse(requests[1][1].body).request_id
  );
  expect(screen.getByRole("button", { name: "Run now" })).toBeEnabled();
});

it("does not offer execution without the required permissions", () => {
  mockPermissions.splice(0, mockPermissions.length);
  render(<ControladoriaPage />);
  expect(
    screen.getByText("You do not have permission to view this analysis.")
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Run now" })
  ).not.toBeInTheDocument();
  expect(global.fetch).not.toHaveBeenCalled();
});
