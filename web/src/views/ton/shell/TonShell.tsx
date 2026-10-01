"use client";

import "@/views/ton/shell/ton.css";
import { useEffect, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import {
  IllustrationContent,
  RootLayoutRightPanelSlotContext,
} from "@opal/layouts";
import { SvgNoAccess } from "@opal/illustrations";
import { useUser } from "@/providers/UserProvider";
import { useTonAccess } from "@/lib/ton/api";
import { COPY } from "@/lib/ton/copy";
import TonHeader from "@/views/ton/shell/TonHeader";
import TonSidebar from "@/views/ton/shell/TonSidebar";

/** Hosts the native chat runtime: its document panel hoists into this slot. */
function ChatFrame({ children }: { children: ReactNode }) {
  const [rightPanel, setRightPanel] = useState<ReactNode>(null);
  return (
    <RootLayoutRightPanelSlotContext.Provider value={setRightPanel}>
      <div data-main-container className="flex flex-1 min-w-0 min-h-0">
        <div className="@container relative isolate flex-1 flex flex-col min-w-0 min-h-0">
          {children}
        </div>
        {rightPanel}
      </div>
    </RootLayoutRightPanelSlotContext.Provider>
  );
}

function NoAccess() {
  return (
    <div className="flex flex-1 items-center justify-center p-6">
      <IllustrationContent
        illustration={SvgNoAccess}
        title={COPY.shell.noAccessTitle}
        description={COPY.shell.noAccessDescription}
      />
    </div>
  );
}

export interface TonShellProps {
  children: ReactNode;
}

export default function TonShell({ children }: TonShellProps) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const { user } = useUser();
  const { canRead } = useTonAccess();
  const isChat = pathname.startsWith("/ton/chat");

  useEffect(() => setMenuOpen(false), [pathname]);

  const content = user && !canRead ? <NoAccess /> : children;

  return (
    <div className="ton-shell">
      <TonHeader
        menuOpen={menuOpen}
        onToggleMenu={() => setMenuOpen((value) => !value)}
      />
      <div className="flex flex-1 min-h-0">
        <TonSidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
        {isChat ? (
          <ChatFrame>{content}</ChatFrame>
        ) : (
          <main className="flex flex-1 min-w-0 min-h-0 overflow-y-auto">
            {content}
          </main>
        )}
      </div>
    </div>
  );
}
