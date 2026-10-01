/** @jest-environment jsdom */

import { render, screen, setupUser, waitFor } from "@tests/setup/test-utils";
import useSWR from "swr";
import R3Spotlight from "@/views/ton/components/R3Spotlight";
import { Permission } from "@/lib/types";
import type { ClosingOutput, Publication } from "@/lib/ton/types";

jest.mock("swr", () => ({
  __esModule: true,
  ...jest.requireActual("swr"),
  default: jest.fn(),
  useSWRConfig: () => ({ mutate: jest.fn() }),
}));
const mockPermissions: string[] = ["admin"];
jest.mock("@/providers/UserProvider", () => ({
  useUser: () => ({
    user: { id: "synthetic-user", effective_permissions: mockPermissions },
  }),
}));
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn(), back: jest.fn() }),
  usePathname: () => "/ton/automacoes",
}));

const output: ClosingOutput = {
  period: "2026-07-01",
  scope: "Consolidado",
  unit_id: null,
  normalization_run_id: null,
  structure_version_id: null,
  data_context: "Dados sintéticos de demonstração.",
  sources: [],
  specialists: [],
  findings: [],
  findings_scope: "Escopo sintético",
  findings_may_have_more: false,
  dre_status: "Pendente",
  blockers: { "Conciliação sem decisão": 1 },
  executive_brief: { RESULTADO: "Análise preliminar." },
  generated_at: "2026-10-01T12:00:00Z",
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

beforeEach(() => {
  sessionStorage.clear();
  jest.clearAllMocks();
  mockPermissions.splice(0, mockPermissions.length, "admin");
  Object.defineProperty(globalThis.crypto, "randomUUID", {
    configurable: true,
    value: jest.fn(() => "11111111-1111-4111-8111-111111111111"),
  });
  (useSWR as jest.MockedFunction<typeof useSWR>).mockImplementation((key) => {
    const url = typeof key === "string" ? key : "";
    const data = url.includes("/routines/R3/latest")
      ? null
      : url.includes("/closing")
        ? output
        : url.includes("/routines")
          ? [
              {
                key: "R3",
                name: "Fechamento preliminar mensal",
                status: "Agendada",
                reason: "Publicação interna.",
                schedule: "Primeiro dia útil do mês, às 08:00 de Brasília.",
                next_run: "2026-11-03T11:00:00Z",
                manual_available: true,
              },
            ]
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

it("shows the real schedule and the next run", () => {
  render(<R3Spotlight />);
  expect(screen.getByText("Fechamento preliminar mensal")).toBeInTheDocument();
  expect(screen.getByText("Agendada")).toBeInTheDocument();
  expect(screen.getAllByText("Ainda não executada")).toHaveLength(2);
  expect(screen.getByText("03/11/2026, 08:00")).toBeInTheDocument();
});

it("recovers the same execution request after failure and links the result", async () => {
  const user = setupUser();
  (global.fetch as jest.Mock)
    .mockResolvedValueOnce({ ok: false })
    .mockResolvedValueOnce({ ok: true, json: async () => publication });
  render(<R3Spotlight />);
  await user.click(screen.getByRole("button", { name: "Executar agora" }));
  await screen.findByText(
    "A execução falhou. Tente novamente para retomar a mesma solicitação."
  );
  await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
  await waitFor(() =>
    expect(
      screen.getByRole("link", { name: "Abrir resultado" })
    ).toHaveAttribute("href", publication.report_url)
  );
  const requests = (global.fetch as jest.Mock).mock.calls;
  expect(requests).toHaveLength(2);
  expect(JSON.parse(requests[0][1].body).request_id).toEqual(
    JSON.parse(requests[1][1].body).request_id
  );
  expect(screen.getByText("Execução concluída")).toBeInTheDocument();
});

it("prevents duplicate runs while one is in flight", async () => {
  const user = setupUser();
  (global.fetch as jest.Mock).mockImplementation(() => new Promise(() => {}));
  render(<R3Spotlight />);
  await user.click(screen.getByRole("button", { name: "Executar agora" }));
  const running = screen.getAllByText("Executando…");
  expect(running.length).toBeGreaterThan(0);
  expect(screen.getByRole("button", { name: "Executando…" })).toBeDisabled();
  expect(sessionStorage.getItem("ton:R3:submission:synthetic-user")).toContain(
    "11111111"
  );
  expect(global.fetch).toHaveBeenCalledTimes(1);
});

it("resumes the exact pending request after reload", async () => {
  const request = {
    request_id: "pending-reload",
    period: output.period,
    unit_id: null,
    normalization_run_id: null,
    structure_version_id: null,
  };
  sessionStorage.setItem(
    "ton:R3:submission:synthetic-user",
    JSON.stringify(request)
  );
  (global.fetch as jest.Mock).mockResolvedValue({
    ok: true,
    json: async () => publication,
  });
  render(<R3Spotlight />);
  await screen.findByRole("link", { name: "Abrir resultado" });
  expect(global.fetch).toHaveBeenCalledTimes(1);
  expect(JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body)).toEqual(
    request
  );
});

it("does not offer execution to a reader without report management", () => {
  mockPermissions.splice(
    0,
    mockPermissions.length,
    Permission.READ_TON_SOURCES,
    Permission.READ_TON_OCCURRENCES,
    Permission.READ_TON_REPORTS
  );
  render(<R3Spotlight />);
  expect(
    screen.queryByRole("button", { name: "Executar agora" })
  ).not.toBeInTheDocument();
  expect(global.fetch).not.toHaveBeenCalled();
});
