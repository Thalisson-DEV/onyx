"use client";

import { ReactNode } from "react";
import { RootLayout } from "@opal/layouts";
import TonSidebar from "@/sections/sidebar/TonSidebar";
import { usePathname } from "next/navigation";
import AppChrome from "@/layouts/chromes/AppChrome";

export interface TonChromeProps {
  children: ReactNode;
}

export default function TonChrome({ children }: TonChromeProps) {
  const isChat = usePathname().startsWith("/ton/chat");
  return (
    <RootLayout.Root>
      <TonSidebar />
      {isChat ? (
        <AppChrome>{children}</AppChrome>
      ) : (
        <RootLayout.App>
          <div className="flex flex-1 flex-col w-full h-full min-h-0 overflow-y-auto">
            {children}
          </div>
        </RootLayout.App>
      )}
    </RootLayout.Root>
  );
}
