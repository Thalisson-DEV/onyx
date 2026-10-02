"use client";

import type { Route } from "next";
import { Button, Text } from "@opal/components";
import { SvgBubbleText, SvgLock, SvgShield, SvgSparkle } from "@opal/icons";
import { SEARCH_PARAM_NAMES } from "@/app/app/services/searchParams";
import { useTonSpecialists } from "@/lib/ton/api";
import { COPY, formatRelativeDateTime } from "@/lib/ton/copy";
import type { SpecialistView } from "@/lib/ton/types";
import {
  IconTile,
  LoadingBlock,
  PageContainer,
  PageHeader,
  StatusPill,
  TonCard,
  specialistTone,
} from "@/views/ton/components/ui";

function askHref(specialist: SpecialistView): Route {
  const query = new URLSearchParams({
    firstMessage: COPY.specialists.askPrompt(
      specialist.name,
      specialist.objective
    ),
    [SEARCH_PARAM_NAMES.SUBMIT_ON_LOAD]: "true",
    foco: specialist.key,
  });
  return `/ton/chat?${query.toString()}` as Route;
}

function List({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div className="flex flex-col gap-1">
      <span className="ton-eyebrow">{title}</span>
      <ul className="flex flex-col gap-1">
        {items.map((item) => (
          <li key={item}>
            <Text font="secondary-body" color="text-04">
              {item}
            </Text>
          </li>
        ))}
      </ul>
    </div>
  );
}

function WorkingCard({ specialist }: { specialist: SpecialistView }) {
  return (
    <TonCard as="article" className="flex flex-col gap-4 p-5">
      <div className="flex items-start gap-3">
        <IconTile icon={SvgSparkle} size="lg" />
        <div className="flex flex-col gap-1 min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Text as="h2" font="heading-h3" color="text-05">
              {specialist.name}
            </Text>
            <StatusPill tone={specialistTone(specialist.status)}>
              {specialist.status}
            </StatusPill>
          </div>
          <Text font="main-ui-body" color="text-04">
            {specialist.objective}
          </Text>
          <Text font="secondary-body" color="text-03">
            {specialist.last_execution
              ? COPY.specialists.lastRun(
                  formatRelativeDateTime(specialist.last_execution)
                )
              : COPY.specialists.neverRan}
          </Text>
        </div>
      </div>
      <Text font="secondary-body" color="text-03">
        {specialist.reason}
      </Text>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <List
          title={COPY.specialists.can}
          items={specialist.available_capabilities}
        />
        <List
          title={COPY.specialists.limits}
          items={specialist.blocked_capabilities}
        />
      </div>
      <div>
        <Button
          href={askHref(specialist)}
          prominence="secondary"
          icon={SvgBubbleText}
        >
          {COPY.specialists.ask}
        </Button>
      </div>
    </TonCard>
  );
}

function WaitingCard({ specialist }: { specialist: SpecialistView }) {
  return (
    <TonCard as="article" className="flex flex-col gap-3 p-4">
      <div className="flex items-start gap-3">
        <IconTile icon={SvgLock} tone="neutral" />
        <div className="flex flex-col gap-0.5 min-w-0 flex-1">
          <Text as="h3" font="main-ui-action" color="text-05">
            {specialist.name}
          </Text>
          <Text font="secondary-body" color="text-03">
            {specialist.objective}
          </Text>
        </div>
        <StatusPill tone="neutral">{specialist.status}</StatusPill>
      </div>
      <div className="flex flex-col gap-0.5 rounded-08 bg-background-neutral-01 px-3 py-2">
        <span className="ton-eyebrow">{COPY.specialists.needs}</span>
        <Text font="secondary-body" color="text-04">
          {specialist.required_sources.join(", ")}
        </Text>
      </div>
    </TonCard>
  );
}

export default function SpecialistsPage() {
  const specialists = useTonSpecialists();
  const list = specialists.data ?? [];
  const working = list.filter(
    (item) => specialistTone(item.status) !== "neutral"
  );
  const waiting = list.filter(
    (item) => specialistTone(item.status) === "neutral"
  );
  return (
    <PageContainer>
      <PageHeader
        title={COPY.specialists.title}
        description={COPY.specialists.description}
      />
      <div className="flex items-center gap-2 rounded-12 bg-background-neutral-02 px-4 py-3">
        <SvgShield size={16} className="shrink-0" />
        <Text font="secondary-body" color="text-04">
          {COPY.specialists.policy}
        </Text>
      </div>
      {specialists.isLoading && (
        <TonCard className="p-5">
          <LoadingBlock label={COPY.common.loading} />
        </TonCard>
      )}
      {specialists.error && (
        <TonCard className="p-5">
          <Text font="main-ui-body" color="text-03">
            {COPY.common.error}
          </Text>
        </TonCard>
      )}
      {working.length > 0 && (
        <section className="flex flex-col gap-3">
          <Text as="h2" font="heading-h3" color="text-05">
            {`${COPY.specialists.working} (${working.length})`}
          </Text>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            {working.map((item) => (
              <WorkingCard key={item.key} specialist={item} />
            ))}
          </div>
        </section>
      )}
      {waiting.length > 0 && (
        <section className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <Text as="h2" font="heading-h3" color="text-05">
              {`${COPY.specialists.waiting} (${waiting.length})`}
            </Text>
            <Text font="secondary-body" color="text-03">
              {COPY.specialists.waitingDescription}
            </Text>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {waiting.map((item) => (
              <WaitingCard key={item.key} specialist={item} />
            ))}
          </div>
        </section>
      )}
    </PageContainer>
  );
}
