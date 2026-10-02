/** @jest-environment jsdom */

import { render, screen, setupUser, within } from "@tests/setup/test-utils";
import useSWR from "swr";
import SourcesPage from "@/views/ton/SourcesPage";
import AutomationsPage from "@/views/ton/AutomationsPage";

jest.mock("swr", () => ({
  __esModule: true,
  ...jest.requireActual("swr"),
  default: jest.fn(),
}));
jest.mock("@/providers/UserProvider", () => ({
  useUser: () => ({
    user: {
      id: "user-1",
      effective_permissions: [
        "read:ton_sources",
        "read:ton_occurrences",
        "read:ton_reports",
      ],
    },
  }),
}));
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn(), back: jest.fn() }),
  usePathname: () => "/ton/fontes",
  useSearchParams: () => new URLSearchParams(),
}));

const NG = {
  key: "financial_launches",
  name: "NG / Lançamentos financeiros",
  description: "Movimentações financeiras do NG.",
  format: "XLSX",
  source_id: "source-1",
  can_import: false,
  status: "CURRENT",
  last_success_at: "2026-10-01T01:43:18Z",
  last_attempt_at: "2026-10-01T01:43:18Z",
  latest: null,
  history: [],
};

const ROUTINES = [
  {
    key: "R3",
    name: "Fechamento preliminar mensal",
    status: "Agendada",
    reason: "Publicação interna.",
    schedule: "Primeiro dia útil do mês, às 08:00 de Brasília.",
    next_run: "2026-11-03T11:00:00Z",
    manual_available: true,
  },
  {
    key: "R2",
    name: "Auditoria semanal de combustível",
    status: "Bloqueada",
    reason: "Capacidade pendente: Frota e abastecimento integrados.",
    schedule: "Agendamento não configurado",
    manual_available: false,
  },
];

beforeEach(() => {
  (useSWR as jest.MockedFunction<typeof useSWR>).mockImplementation((key) => {
    const path = typeof key === "string" ? key : "";
    const data =
      path === "/api/ton/data-sources"
        ? [NG]
        : path.startsWith("/api/ton/agent/closing")
          ? {
              sources: [
                {
                  key: "financial_launches",
                  direct_integration: "Aguardando acesso e configuração",
                },
              ],
            }
          : path === "/api/ton/agent/routines"
            ? ROUTINES
            : path.startsWith("/api/ton/agent/reports")
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
});

it("shows NG as file-fed with direct integration still pending", async () => {
  const user = setupUser();
  const { container } = render(<SourcesPage />);
  const card = screen.getByRole("article");
  await user.click(
    within(card).getByRole("button", { name: /Mostrar detalhes de/ })
  );
  expect(within(card).getByText("Arquivo XLSX")).toBeInTheDocument();
  expect(
    within(card).getByText("Aguardando acesso e configuração")
  ).toBeInTheDocument();
  expect(container).not.toHaveTextContent(/conectad/i);
  expect(
    screen.queryByRole("button", { name: "Atualizar dados" })
  ).not.toBeInTheDocument();
});

it("separates the scheduled flagship from routines waiting on capabilities", () => {
  render(<AutomationsPage />);
  expect(screen.getByText("Aguardando capacidade (1)")).toBeInTheDocument();
  expect(
    screen.getByText("Frota e abastecimento integrados")
  ).toBeInTheDocument();
  expect(screen.queryByText("Ativas")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Executar agora" })
  ).not.toBeInTheDocument();
});
