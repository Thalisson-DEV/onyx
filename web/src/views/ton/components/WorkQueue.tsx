"use client";

import type { Route } from "next";
import Link from "next/link";
import { Button, Text } from "@opal/components";
import { SvgArrowRight, SvgCheckCircle } from "@opal/icons";
import { COPY, formatDay } from "@/lib/ton/copy";
import type { WorkItem } from "@/lib/ton/workQueue";
import { ErrorState, LoadingBlock } from "@/views/ton/components/ui";
import { Tag } from "@/views/ton/components/kit";

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

/** One table of what needs a person, shared by Home and Fechamento. */
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
  const hasDeadline = shown.some((item) => item.deadline);
  return (
    <section className="tn-card" aria-labelledby={id}>
      <div className="flex flex-wrap items-end gap-3 px-4 pt-3.5 pb-3">
        <div className="flex flex-col gap-0.5 min-w-0 flex-1">
          <Text as="h2" id={id} font="main-ui-action" color="text-05">
            {title}
          </Text>
          {description && (
            <Text font="secondary-body" color="text-03">
              {description}
            </Text>
          )}
        </div>
        {action && (
          <Link href={action.href} className="tn-link ton-focusable">
            {action.label}
          </Link>
        )}
      </div>
      {isLoading && shown.length === 0 && (
        <div className="px-4 pb-4">
          <LoadingBlock label={COPY.common.loading} />
        </div>
      )}
      {failed && (
        <div className="px-4 pb-4">
          <ErrorState compact />
        </div>
      )}
      {!isLoading && !failed && shown.length === 0 && (
        <div className="tn-notice mx-4 mb-4">
          <SvgCheckCircle size={16} />
          {QUEUE.empty}
        </div>
      )}
      {shown.length > 0 && (
        <div className="overflow-x-auto border-t border-01">
          <table className="tp-table">
            <thead>
              <tr>
                <th scope="col" className="w-10">
                  #
                </th>
                <th scope="col">{QUEUE.columns.what}</th>
                <th scope="col">{QUEUE.columns.impact}</th>
                <th scope="col">{QUEUE.columns.where}</th>
                {hasDeadline && <th scope="col">{QUEUE.columns.when}</th>}
                <th scope="col">
                  <span className="sr-only">{QUEUE.columns.action}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {shown.map((item, index) => (
                <tr key={item.key}>
                  <td className="tp-muted tn-num">{index + 1}</td>
                  <td className="tp-wrap">
                    <span className="flex flex-col">
                      <span className="tp-strong">{item.title}</span>
                      {item.detail && (
                        <span className="tp-muted">{item.detail}</span>
                      )}
                    </span>
                  </td>
                  <td>
                    <Tag
                      tone={
                        item.impact === "blocks"
                          ? "danger"
                          : item.impact === "urgent"
                            ? "warn"
                            : "neutral"
                      }
                    >
                      {QUEUE.impact[item.impact]}
                    </Tag>
                  </td>
                  <td className="tp-muted">
                    {[
                      QUEUE.origins[item.origin],
                      item.owner ? QUEUE.owner(item.owner) : null,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </td>
                  {hasDeadline && (
                    <td className="tp-muted">
                      {item.deadline ? formatDay(item.deadline) : "—"}
                    </td>
                  )}
                  <td className="tp-end">
                    <Button
                      href={item.href}
                      size="sm"
                      prominence={index === 0 ? "primary" : "secondary"}
                      rightIcon={SvgArrowRight}
                    >
                      {item.action}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {limit && items.length > limit && (
        <div className="px-4 py-3 border-t border-01">
          <Text font="secondary-body" color="text-03">
            {QUEUE.more(items.length - limit)}
          </Text>
        </div>
      )}
    </section>
  );
}
