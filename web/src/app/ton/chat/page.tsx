import type { Metadata } from "next";

import TonChatPage from "@/views/ton/ChatPage";

export default function Page() {
  return <TonChatPage />;
}

export const metadata: Metadata = { title: "Assistente" };
