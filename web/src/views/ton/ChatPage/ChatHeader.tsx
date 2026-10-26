"use client";

import type { Route } from "next";
import { Button, LineItemButton, Popover } from "@opal/components";
import { SvgChevronDown, SvgPlus, SvgSidebar } from "@opal/icons";
import { useTonClosing, useTonSpecialists } from "@/lib/ton/api";
import { COPY, formatPeriod } from "@/lib/ton/copy";

const HEADER = COPY.chat.header;

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <span className="tn-chat-chip">
      {label}
      <b>{value}</b>
    </span>
  );
}

/**
 * What this conversation is about: its title, the closing it reads, and
 * who answers (the coordinator or a specialist, switchable here).
 */
export default function ChatHeader({
  title,
  focus,
  historyOpen,
  onToggleHistory,
}: {
  title: string;
  focus: string | null;
  historyOpen: boolean;
  onToggleHistory: () => void;
}) {
  const closing = useTonClosing();
  const specialists = useTonSpecialists();
  const current = focus
    ? specialists.data?.find((item) => item.key === focus)
    : undefined;
  return (
    <header className="tn-chat-head">
      <Button
        prominence="tertiary"
        size="sm"
        icon={SvgSidebar}
        aria-label={COPY.chat.history.toggle}
        aria-pressed={historyOpen}
        tooltip={COPY.chat.history.toggle}
        onClick={onToggleHistory}
      />
      <h1 className="tn-chat-title" title={title}>
        {title}
      </h1>
      {closing.data && (
        <span className="tn-chat-chips">
          <Chip
            label={HEADER.period}
            value={formatPeriod(closing.data.period)}
          />
          <Chip label={HEADER.scope} value={closing.data.scope} />
        </span>
      )}
      <Popover>
        <Popover.Trigger asChild>
          {/* The chip opens the specialist list; Opal has no chip trigger. */}
          <button type="button" className="tn-chat-chip ton-focusable">
            {HEADER.specialist}
            <b>{current?.name ?? HEADER.coordinator}</b>
            <SvgChevronDown size={12} aria-hidden />
          </button>
        </Popover.Trigger>
        <Popover.Content align="start">
          <Popover.Menu>
            {[
              <LineItemButton
                key="coordinator"
                sizePreset="main-ui"
                rounding={2}
                href={"/ton/chat" as Route}
                state={focus ? "empty" : "selected"}
                selectVariant="select-light"
                title={HEADER.coordinator}
                description={COPY.assistant.context.coordinator}
              />,
              ...(specialists.data ?? []).map((item) => (
                <LineItemButton
                  key={item.key}
                  sizePreset="main-ui"
                  rounding={2}
                  href={`/ton/chat?foco=${item.key}` as Route}
                  state={item.key === focus ? "selected" : "empty"}
                  selectVariant="select-light"
                  title={item.name}
                  description={item.objective}
                />
              )),
            ]}
          </Popover.Menu>
        </Popover.Content>
      </Popover>
      <span className="flex-1" />
      <Button
        href={(focus ? `/ton/chat?foco=${focus}` : "/ton/chat") as Route}
        prominence="secondary"
        size="sm"
        icon={SvgPlus}
      >
        {HEADER.newConversation}
      </Button>
    </header>
  );
}
