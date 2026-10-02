"use client";

import type { Route } from "next";
import { Button, Text } from "@opal/components";
import { SvgArrowRight, SvgCheckCircle } from "@opal/icons";
import { COPY, formatDay } from "@/lib/ton/copy";
import type { WorkItem } from "@/lib/ton/workQueue";
import {
  CardHeader,
  ErrorState,
  LoadingBlock,
  StatusPill,
  TonCard,
} from "@/views/ton/components/ui";

const QUEUE = COPY.workQueue;

interface WorkQueueProps {
  id: string;
  title: string;
  description?: string;
  items: WorkItem[];
  isLoading?: boolean;
  failed?: boolean;
  limit?: number;
  action?: { href: Route; label: string };
}

/** One list of what needs a person, shared by Home and Fechamento. */
export default function WorkQueue({
  id,
  title,
  description,
  items,
  isLoading,
  failed,
  limit,
  action,
}: WorkQueueProps) {
  const shown = limit ? items.slice(0, limit) : items;
  return (
    <TonCard className="flex flex-col gap-3 p-5" labelledBy={id}>
      <CardHeader
        id={id}
        title={title}
        description={description}
        action={action}
      />
      {isLoading && <LoadingBlock label={COPY.common.loading} />}
      {failed && <ErrorState compact />}
      {!isLoading && !failed && shown.length === 0 && (
        <div className="flex items-center gap-2 py-1">
          <SvgCheckCircle size={16} className="ton-brand-text" />
          <Text font="main-ui-body" color="text-04">
            {QUEUE.empty}
          </Text>
        </div>
      )}
      {shown.length > 0 && (
        <ol className="flex flex-col divide-y divide-border-01">
          {shown.map((item, index) => (
            <li
              key={item.key}
              className="flex flex-wrap items-center gap-3 py-3 first:pt-0 last:pb-0"
            >
              <span
                className="ton-step"
                data-state={index === 0 ? "current" : "next"}
              >
                {index + 1}
              </span>
              <div className="flex flex-col gap-0.5 min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <Text font="main-ui-action" color="text-05">
                    {item.title}
                  </Text>
                  <StatusPill
                    tone={item.impact === "blocks" ? "warning" : "neutral"}
                  >
                    {QUEUE.impact[item.impact]}
                  </StatusPill>
                </div>
                {item.detail && (
                  <Text font="secondary-body" color="text-03">
                    {item.detail}
                  </Text>
                )}
                <Text font="secondary-body" color="text-03">
                  {[
                    QUEUE.origins[item.origin],
                    item.owner ? QUEUE.owner(item.owner) : null,
                    item.deadline
                      ? QUEUE.deadline(formatDay(item.deadline))
                      : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </Text>
              </div>
              <Button
                href={item.href}
                size="md"
                prominence={index === 0 ? "primary" : "secondary"}
                rightIcon={SvgArrowRight}
              >
                {item.action}
              </Button>
            </li>
          ))}
        </ol>
      )}
      {limit && items.length > limit && (
        <Text font="secondary-body" color="text-03">
          {QUEUE.more(items.length - limit)}
        </Text>
      )}
    </TonCard>
  );
}
