import { renderHook } from "@testing-library/react";
import { useAppPosition } from "@/lib/position/hooks";

let mockPathname = "/ton/chat";
let mockQuery = new URLSearchParams();
const mockPush = jest.fn();
const mockReplace = jest.fn();

jest.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
  useSearchParams: () => mockQuery,
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
}));

beforeEach(() => {
  mockPathname = "/ton/chat";
  mockQuery = new URLSearchParams();
  jest.clearAllMocks();
});

test("TON preserves native conversation and Persona navigation", () => {
  const { result } = renderHook(() => useAppPosition());
  expect(result.current.chatHref("persisted-chat")).toBe(
    "/ton/chat?chatId=persisted-chat"
  );
  result.current.openChat("persisted-chat");
  expect(mockPush).toHaveBeenCalledWith("/ton/chat?chatId=persisted-chat");
  result.current.openAgent(42);
  expect(mockPush).toHaveBeenCalledWith("/ton/chat?agentId=42");
  result.current.openNewSession({ replace: true });
  expect(mockReplace).toHaveBeenCalledWith("/ton/chat");
});

test("TON reads persisted conversation IDs from the native query", () => {
  mockQuery = new URLSearchParams("chatId=persisted-chat");
  const { result } = renderHook(() => useAppPosition());
  expect(result.current.chat()).toBe("persisted-chat");
  expect(result.current.href()).toBe("/ton/chat?chatId=persisted-chat");
});

test("generic Onyx conversations retain their route", () => {
  mockPathname = "/app";
  const { result } = renderHook(() => useAppPosition());
  result.current.openChat("onyx-chat");
  expect(mockPush).toHaveBeenCalledWith("/app?chatId=onyx-chat");
});
