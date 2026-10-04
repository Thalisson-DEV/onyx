"use client";

import Link from "next/link";
import type { Route } from "next";
import type { ReactNode } from "react";
import { Text } from "@opal/components";
import { useDeferredStart, useTonClosing } from "@/lib/ton/api";
import { COPY, formatPeriod } from "@/lib/ton/copy";
import { PageContainer, PageHeader } from "@/views/ton/components/ui";

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
  actions?: ReactNode;
  children: ReactNode;
  wide?: boolean;
}

export default function ClosingFrame({
  active,
  title,
  description,
  actions,
  children,
  wide = false,
}: ClosingFrameProps) {
  // Only the eyebrow needs it; the page under the frame loads first.
  const closing = useTonClosing(undefined, useDeferredStart());
  const eyebrow = closing.data
    ? `${COPY.closing.eyebrow} · ${formatPeriod(closing.data.period)} · ${closing.data.scope}`
    : COPY.closing.eyebrow;
  return (
    <PageContainer className={wide ? "max-w-[1360px]" : undefined}>
      <PageHeader
        eyebrow={eyebrow}
        title={title}
        description={description}
        actions={actions}
      />
      <nav
        aria-label={COPY.closing.eyebrow}
        className="flex shrink-0 gap-1 border-b border-01 -mt-2 overflow-x-auto overflow-y-hidden"
      >
        {TABS.map((tab) => {
          const selected = tab.key === active;
          return (
            <Link
              key={tab.key}
              href={tab.href}
              aria-current={selected ? "page" : undefined}
              className={
                selected
                  ? "ton-focusable ton-brand-text px-3 py-2.5 border-b-2 border-(--vale-norte-green-80) -mb-px"
                  : "ton-focusable px-3 py-2.5 border-b-2 border-transparent -mb-px text-text-03 hover:text-text-05"
              }
            >
              <Text font="main-ui-action" color="inherit">
                {COPY.closing.tabs[tab.key]}
              </Text>
            </Link>
          );
        })}
      </nav>
      {children}
    </PageContainer>
  );
}
