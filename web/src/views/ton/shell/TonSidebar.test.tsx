/** @jest-environment jsdom */

import { render, screen, setupUser, waitFor } from "@tests/setup/test-utils";
import TonSidebar from "@/views/ton/shell/TonSidebar";
import type { ChatSession } from "@/app/app/interfaces";

const mockPush = jest.fn();
const mockRefresh = jest.fn(async () => undefined);
const mockRemove = jest.fn();
const mockRename = jest.fn(async (_id: string, _name: string) => ({
  ok: true,
}));
const mockDelete = jest.fn(async (_id: string) => ({ ok: true }));
const mockSessions: Partial<ChatSession>[] = [];

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: jest.fn(), back: jest.fn() }),
  usePathname: () => "/ton/dre",
  useSearchParams: () => new URLSearchParams(),
}));
jest.mock("@/providers/UserProvider", () => ({
  useUser: () => ({ hasAdminAccess: false }),
}));
jest.mock("@/lib/ton/api", () => ({
  useTonAccess: () => ({ canRead: true }),
  useTonPersona: () => ({ data: { persona_id: 7 } }),
}));
jest.mock("@/hooks/useChatSessions", () => ({
  __esModule: true,
  default: () => ({
    chatSessions: mockSessions,
    currentChatSessionId: "s-1",
    refreshChatSessions: mockRefresh,
    removeSession: mockRemove,
  }),
}));
jest.mock("@/app/app/services/lib", () => ({
  renameChatSession: (id: string, name: string) => mockRename(id, name),
  deleteChatSession: (id: string) => mockDelete(id),
}));

beforeEach(() => {
  jest.clearAllMocks();
  mockSessions.splice(
    0,
    mockSessions.length,
    { id: "s-1", name: "Margem de junho", persona_id: 7 },
    { id: "s-2", name: "Outra persona", persona_id: 9 }
  );
});

function renderSidebar(rail = false) {
  return render(<TonSidebar open={false} rail={rail} onClose={jest.fn()} />);
}

test("lists only TON conversations and keeps the active section open", () => {
  renderSidebar();

  expect(screen.getByRole("link", { name: "Margem de junho" })).toBeVisible();
  expect(screen.queryByText("Outra persona")).toBeNull();
  expect(screen.getByRole("link", { name: "DRE" })).toHaveAttribute(
    "aria-current",
    "page"
  );
});

test("the rail keeps navigation by icon and hides the history", () => {
  renderSidebar(true);

  expect(screen.getByRole("link", { name: "Fontes" })).toBeVisible();
  expect(screen.queryByText("Fontes")).toBeNull();
  expect(screen.queryByRole("link", { name: "Margem de junho" })).toBeNull();
  // The closing group is marked current while one of its pages is open.
  expect(screen.getByRole("link", { name: "Fechamento" })).toHaveAttribute(
    "aria-current",
    "page"
  );
});

test("renames a conversation inline", async () => {
  const user = setupUser();
  renderSidebar();

  await user.click(
    screen.getByRole("button", { name: "Ações da conversa Margem de junho" })
  );
  await user.click(await screen.findByText("Renomear"));
  const input = screen.getByDisplayValue("Margem de junho");
  await user.clear(input);
  await user.type(input, "Margem consolidada{Enter}");

  await waitFor(() =>
    expect(mockRename).toHaveBeenCalledWith("s-1", "Margem consolidada")
  );
  expect(mockRefresh).toHaveBeenCalled();
});

test("deletes the open conversation after confirmation", async () => {
  const user = setupUser();
  renderSidebar();

  await user.click(
    screen.getByRole("button", { name: "Ações da conversa Margem de junho" })
  );
  await user.click(await screen.findByText("Excluir"));
  expect(mockDelete).not.toHaveBeenCalled();
  await user.click(
    await screen.findByRole("button", { name: "Excluir conversa" })
  );

  await waitFor(() => expect(mockDelete).toHaveBeenCalledWith("s-1"));
  expect(mockRemove).toHaveBeenCalledWith("s-1");
  expect(mockPush).toHaveBeenCalledWith("/ton/chat");
});
