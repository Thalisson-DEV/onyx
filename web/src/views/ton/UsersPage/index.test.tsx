/** @jest-environment jsdom */

import {
  render,
  screen,
  setupUser,
  waitFor,
  within,
} from "@tests/setup/test-utils";
import useSWR from "swr";
import UsersPage from "@/views/ton/UsersPage";

jest.mock("swr", () => ({
  __esModule: true,
  ...jest.requireActual("swr"),
  default: jest.fn(),
}));

let mockAdmin = true;
jest.mock("@/providers/UserProvider", () => ({
  useUser: () => ({ isAdmin: mockAdmin }),
}));

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn(), back: jest.fn() }),
  usePathname: () => "/ton/administracao/usuarios",
  useSearchParams: () => new URLSearchParams(),
}));

const mockUseSWR = useSWR as jest.MockedFunction<typeof useSWR>;
const units = [
  { id: "unit-1", code: "SYN", name: "Synthetic unit", kind: "OPERATIONAL" },
  { id: "unit-2", code: "SYM", name: "Second unit", kind: "OPERATIONAL" },
];
const members = [
  {
    id: "me",
    email: "admin@synthetic.test",
    name: "Synthetic Admin",
    profile: "ADMIN",
    unit_ids: [],
    active: true,
    pending_first_access: false,
    is_you: true,
  },
  {
    id: "manager",
    email: "manager@synthetic.test",
    name: null,
    profile: "MANAGER",
    unit_ids: ["unit-1"],
    active: true,
    pending_first_access: true,
    is_you: false,
  },
];

beforeEach(() => {
  mockAdmin = true;
  jest.clearAllMocks();
  mockUseSWR.mockImplementation(
    (key) =>
      ({
        data: key === "/api/ton/team" ? members : key ? units : undefined,
        error: undefined,
        isLoading: false,
        isValidating: false,
        mutate: jest.fn(),
      }) as ReturnType<typeof useSWR>
  );
});

it("lists people with profile, units and first-access status", () => {
  render(<UsersPage />);
  const rows = screen.getAllByRole("row");
  expect(rows[1]).toHaveTextContent("Synthetic Admin (você)");
  expect(rows[1]).toHaveTextContent("Administrador");
  expect(rows[1]).toHaveTextContent("Todas");
  // Nobody changes or deactivates their own access.
  expect(
    within(rows[1]!).queryByRole("button", { name: "Desativar" })
  ).not.toBeInTheDocument();
  expect(rows[2]).toHaveTextContent("Gestor de unidade");
  expect(rows[2]).toHaveTextContent("Unidade de demonstração");
  expect(rows[2]).toHaveTextContent("Aguardando primeiro acesso");
});

it("creates a unit manager and shows the first-access link", async () => {
  const user = setupUser();
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      member: { ...members[1], name: "Nova Pessoa" },
      link: "/auth/primeiro-acesso?token=abc",
      expires_at: "2026-10-30T00:00:00Z",
    }),
  });
  render(<UsersPage />);
  await user.click(screen.getByRole("button", { name: "Novo usuário" }));
  await user.type(screen.getByLabelText("Nome"), "Nova Pessoa");
  await user.type(screen.getByLabelText("E-mail"), "nova@synthetic.test");
  const save = screen.getByRole("button", { name: "Criar e gerar link" });
  // A manager needs at least one unit.
  expect(save).toBeDisabled();
  await user.click(screen.getByRole("checkbox", { name: "Second unit" }));
  await user.click(save);

  await waitFor(() =>
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/ton/team",
      expect.objectContaining({ method: "POST" })
    )
  );
  const body = JSON.parse(
    (global.fetch as jest.Mock).mock.calls[0][1].body as string
  );
  expect(body).toEqual({
    profile: "MANAGER",
    unit_ids: ["unit-2"],
    email: "nova@synthetic.test",
    name: "Nova Pessoa",
  });
  expect(
    await screen.findByText("http://localhost/auth/primeiro-acesso?token=abc")
  ).toBeInTheDocument();
});

it("keeps the screen closed to non-administrators", () => {
  mockAdmin = false;
  render(<UsersPage />);
  expect(screen.getByText("Área do administrador")).toBeInTheDocument();
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
});
