"use client";

import Link from "next/link";
import type { Route } from "next";
import type { ReactNode } from "react";
import { useUser } from "@/providers/UserProvider";
import { COPY } from "@/lib/ton/copy";
import { PageFrame, PageHead } from "@/views/ton/components/kit";

type ClosingTab = "overview" | "dre" | "pending";

const TABS: { key: ClosingTab; href: Route }[] = [
  { key: "overview", href: "/ton/fechamento" },
  { key: "dre", href: "/ton/dre" },
  { key: "pending", href: "/ton/pendencias" },
];

interface ClosingFrameProps {
  active: ClosingTab;
  title: string;
  description?: string;
  /** Tags beside the title (ready to publish, official result...). */
  status?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  /** Kept for callers; every closing page now uses the full workspace. */
  wide?: boolean;
}

export default function ClosingFrame({
  active,
  title,
  description,
  status,
  actions,
  children,
}: ClosingFrameProps) {
  const { isAdmin } = useUser();
  return (
    <PageFrame>
      <PageHead
        title={title}
        description={description}
        status={status}
        actions={actions}
      />
      {/* A unit manager has only the DRE: no closing overview, no queue. */}
      {isAdmin && (
        <nav aria-label={COPY.closing.eyebrow} className="tn-views">
          {TABS.map((tab) => (
            <Link
              key={tab.key}
              href={tab.href}
              aria-current={tab.key === active ? "page" : undefined}
              className="tn-view ton-focusable"
            >
              {COPY.closing.tabs[tab.key]}
            </Link>
          ))}
        </nav>
      )}
      {children}
    </PageFrame>
  );
}
