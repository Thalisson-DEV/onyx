"use client";

import { useState } from "react";
import type { Route } from "next";
import { Button, Text } from "@opal/components";
import { SvgBubbleText } from "@opal/icons";
import { useTonSpecialists } from "@/lib/ton/api";
import { COPY, formatRelativeDateTime } from "@/lib/ton/copy";
import type { SpecialistView } from "@/lib/ton/types";
import {
  ErrorState,
  LoadingBlock,
  specialistTone,
} from "@/views/ton/components/ui";
import {
  Drawer,
  DrawerSection,
  PageFrame,
  PageHead,
  Tag,
  ViewTabs,
  type TagTone,
} from "@/views/ton/components/kit";

/** The specialist's own conversation, focused on its domain. */
function chatHref(specialist: SpecialistView): Route {
  const query = new URLSearchParams({ foco: specialist.key });
  return `/ton/chat?${query.toString()}` as Route;
}

function toneOf(status: string): TagTone {
  const tone = specialistTone(status);
  return tone === "success" ? "ok" : tone === "warning" ? "warn" : "neutral";
}

function Items({ items }: { items: string[] }) {
  return (
    <ul className="flex flex-col gap-1.5 m-0 p-0 list-none">
      {items.map((item) => (
        <li key={item} className="flex gap-2">
          <span aria-hidden className="tn-bullet mt-2" />
          <Text font="main-ui-body" color="text-04">
            {item}
          </Text>
        </li>
      ))}
    </ul>
  );
}

function SpecialistDrawer({
  specialist,
  onClose,
}: {
  specialist: SpecialistView;
  onClose: () => void;
}) {
  const working = specialistTone(specialist.status) !== "neutral";
  return (
    <Drawer
      open
      onClose={onClose}
      storageKey="specialist"
      eyebrow={COPY.specialists.title}
      title={specialist.name}
      description={specialist.objective}
      summary={
        <>
          <Tag tone={toneOf(specialist.status)}>{specialist.status}</Tag>
          <span className="tn-hint">
            {specialist.last_execution
              ? COPY.specialists.lastRun(
                  formatRelativeDateTime(specialist.last_execution)
                )
              : COPY.specialists.neverRan}
          </span>
        </>
      }
      footer={
        <>
          <span className="tn-spacer" />
          <Button href={chatHref(specialist)} icon={SvgBubbleText}>
            {COPY.specialists.ask}
          </Button>
        </>
      }
    >
      {specialist.reason && (
        <Text as="p" font="main-ui-body" color="text-04">
          {specialist.reason}
        </Text>
      )}
      {specialist.available_capabilities.length > 0 && (
        <DrawerSection title={COPY.specialists.can}>
          <Items items={specialist.available_capabilities} />
        </DrawerSection>
      )}
      {specialist.blocked_capabilities.length > 0 && (
        <DrawerSection title={COPY.specialists.limits}>
          <Items items={specialist.blocked_capabilities} />
        </DrawerSection>
      )}
      {!working && specialist.required_sources.length > 0 && (
        <DrawerSection title={COPY.specialists.needs}>
          <Items items={specialist.required_sources} />
        </DrawerSection>
      )}
    </Drawer>
  );
}

type View = "working" | "waiting";

export default function SpecialistsPage() {
  const specialists = useTonSpecialists();
  const [view, setView] = useState<View>("working");
  const [openKey, setOpenKey] = useState<string | null>(null);
  const list = specialists.data ?? [];
  const working = list.filter(
    (item) => specialistTone(item.status) !== "neutral"
  );
  const waiting = list.filter(
    (item) => specialistTone(item.status) === "neutral"
  );
  const rows = view === "working" ? working : waiting;
  const open = list.find((item) => item.key === openKey) ?? null;
  return (
    <PageFrame>
      <PageHead
        title={COPY.specialists.title}
        description={`${COPY.specialists.description} ${COPY.specialists.policy}`}
      />
      {specialists.isLoading && <LoadingBlock label={COPY.common.loading} />}
      {specialists.error && <ErrorState onRetry={() => specialists.mutate()} />}
      {specialists.data && (
        <>
          <ViewTabs
            label={COPY.specialists.title}
            value={view}
            onChange={setView}
            views={[
              {
                key: "working",
                label: COPY.specialists.working,
                count: working.length,
                tone: "ok",
              },
              {
                key: "waiting",
                label: COPY.specialists.waiting,
                count: waiting.length,
                tone: "neutral",
              },
            ]}
          />
          <section className="tn-card" aria-label={COPY.specialists.title}>
            {view === "waiting" && (
              <div className="px-4 pt-3 pb-2">
                <Text font="secondary-body" color="text-03">
                  {COPY.specialists.waitingDescription}
                </Text>
              </div>
            )}
            <div className="overflow-x-auto border-t border-01">
              <table className="tp-table">
                <thead>
                  <tr>
                    <th scope="col">{COPY.specialists.columns.name}</th>
                    <th scope="col">{COPY.specialists.columns.status}</th>
                    <th scope="col">
                      {view === "working"
                        ? COPY.specialists.columns.lastRun
                        : COPY.specialists.needs}
                    </th>
                    <th scope="col">
                      <span className="sr-only">{COPY.specialists.ask}</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((item) => (
                    <tr
                      key={item.key}
                      className="tp-row"
                      tabIndex={0}
                      aria-label={item.name}
                      onClick={() => setOpenKey(item.key)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") setOpenKey(item.key);
                      }}
                    >
                      <td className="tp-wrap">
                        <span className="flex flex-col">
                          <span className="tp-strong">{item.name}</span>
                          <span className="tp-muted">{item.objective}</span>
                        </span>
                      </td>
                      <td>
                        <Tag tone={toneOf(item.status)}>{item.status}</Tag>
                      </td>
                      <td className="tp-muted tp-wrap">
                        {view === "working"
                          ? item.last_execution
                            ? formatRelativeDateTime(item.last_execution)
                            : COPY.specialists.neverRan
                          : item.required_sources.join(", ")}
                      </td>
                      <td className="tp-end">
                        <Button
                          href={chatHref(item)}
                          size="sm"
                          prominence="secondary"
                          icon={SvgBubbleText}
                        >
                          {COPY.specialists.ask}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
      {open && (
        <SpecialistDrawer
          key={open.key}
          specialist={open}
          onClose={() => setOpenKey(null)}
        />
      )}
    </PageFrame>
  );
}
