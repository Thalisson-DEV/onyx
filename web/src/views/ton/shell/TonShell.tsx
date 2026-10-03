"use client";

import "@/views/ton/shell/ton.css";
import { useEffect, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import {
  IllustrationContent,
  RootLayoutRightPanelSlotContext,
} from "@opal/layouts";
import { SvgNoAccess } from "@opal/illustrations";
import { useScreenSize } from "@opal/hooks";
import { useUser } from "@/providers/UserProvider";
import { useTonAccess } from "@/lib/ton/api";
import { COPY } from "@/lib/ton/copy";
import TonHeader from "@/views/ton/shell/TonHeader";
import TonSidebar from "@/views/ton/shell/TonSidebar";

const RAIL_STORAGE_KEY = "ton.sidebar.rail";
/** Tailwind `lg`: the sidebar is a drawer below it and docked above it. */
const DOCKED_MIN_WIDTH = 1024;

function readRail(): boolean {
  try {
    return window.localStorage.getItem(RAIL_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

function writeRail(rail: boolean) {
  try {
    window.localStorage.setItem(RAIL_STORAGE_KEY, rail ? "1" : "0");
  } catch {
    // Storage can be blocked; the toggle still works for this visit.
  }
}

function isEditable(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable ||
      ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))
  );
}

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
  const [rail, setRail] = useState(false);
  const { width, isMounted } = useScreenSize();
  const { user } = useUser();
  const { canRead } = useTonAccess();
  const isChat = pathname.startsWith("/ton/chat");
  const docked = isMounted && width >= DOCKED_MIN_WIDTH;

  useEffect(() => setRail(readRail()), []);
  useEffect(() => setMenuOpen(false), [pathname]);
  useEffect(() => {
    if (docked) setMenuOpen(false);
  }, [docked]);

  function toggleRail() {
    setRail((value) => {
      writeRail(!value);
      return !value;
    });
  }

  function toggleNavigation() {
    if (docked) toggleRail();
    else setMenuOpen((value) => !value);
  }

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && menuOpen) {
        setMenuOpen(false);
        return;
      }
      if (
        (event.ctrlKey || event.metaKey) &&
        !event.shiftKey &&
        !event.altKey &&
        event.key.toLowerCase() === "b" &&
        !isEditable(event.target)
      ) {
        event.preventDefault();
        toggleNavigation();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  });

  const content = user && !canRead ? <NoAccess /> : children;

  return (
    <div className="ton-shell">
      <TonHeader
        docked={docked}
        menuOpen={menuOpen}
        rail={rail}
        onToggleNavigation={toggleNavigation}
      />
      <div className="flex flex-1 min-h-0">
        <TonSidebar
          open={menuOpen}
          rail={docked && rail}
          onClose={() => setMenuOpen(false)}
        />
        <div className="ton-workspace flex flex-1 min-w-0 min-h-0">
          {isChat ? (
            <ChatFrame>{content}</ChatFrame>
          ) : (
            <main className="flex flex-1 min-w-0 min-h-0 overflow-y-auto">
              {content}
            </main>
          )}
        </div>
      </div>
    </div>
  );
}
