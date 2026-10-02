"use client";

import { Text } from "@opal/components";
import { COPY, formatRelativeDateTime } from "@/lib/ton/copy";
import type { DecisionEntry } from "@/lib/ton/decisions";
import { getBusinessLabel } from "@/lib/ton/labels";
import { StatusPill } from "@/views/ton/components/ui";

const LOG = COPY.decisionLoop.log;

function outcomeText(entry: DecisionEntry): string {
  return LOG.outcomes[entry.outcome] ?? getBusinessLabel(entry.outcome);
}

/** Who decided what, when, why and in which version — from persisted decisions. */
export default function DecisionLogList({
  entries,
  limit,
}: {
  entries: DecisionEntry[];
  limit?: number;
}) {
  const shown = limit ? entries.slice(0, limit) : entries;
  if (!shown.length) {
    return (
      <Text font="secondary-body" color="text-03">
        {LOG.empty}
      </Text>
    );
  }
  return (
    <ol className="flex flex-col divide-y divide-border-01">
      {shown.map((entry, index) => (
        <li
          key={`${entry.kind}-${entry.version ?? entry.decided_at}-${index}`}
          className="flex flex-col gap-0.5 py-2.5 first:pt-0 last:pb-0"
        >
          <div className="flex flex-wrap items-center gap-2">
            <Text font="main-ui-action" color="text-05">
              {LOG.kinds[entry.kind]}
            </Text>
            {entry.applied === false && (
              <StatusPill tone="warning">{LOG.pending}</StatusPill>
            )}
          </div>
          <Text font="secondary-body" color="text-04">
            {`${getBusinessLabel(entry.subject)} → ${outcomeText(entry)}`}
          </Text>
          {entry.reason && (
            <Text font="secondary-body" color="text-03">
              {`“${entry.reason}”`}
            </Text>
          )}
          <Text font="secondary-body" color="text-03">
            {[
              formatRelativeDateTime(entry.decided_at),
              entry.decided_by ? LOG.by(entry.decided_by) : null,
              entry.version != null ? LOG.version(entry.version) : null,
            ]
              .filter(Boolean)
              .join(" · ")}
          </Text>
        </li>
      ))}
    </ol>
  );
}
