"use client";

import { ReactNode } from "react";
import { RootLayout } from "@opal/layouts";
import TonSidebar from "@/sections/sidebar/TonSidebar";

export interface TonChromeProps {
  children: ReactNode;
}

export default function TonChrome({ children }: TonChromeProps) {
  return (
    <RootLayout.Root>
      <TonSidebar />
      <RootLayout.App>
        <div className="flex flex-1 flex-col w-full h-full min-h-0 overflow-y-auto">
          {children}
        </div>
      </RootLayout.App>
    </RootLayout.Root>
  );
}
