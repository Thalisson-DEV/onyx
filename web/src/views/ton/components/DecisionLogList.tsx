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

/** Consecutive identical decisions (one batch) read as one line. */
function grouped(entries: DecisionEntry[]): Array<DecisionEntry & { count: number }> {
  const result: Array<DecisionEntry & { count: number }> = [];
  for (const entry of entries) {
    const last = result.at(-1);
    if (
      last &&
      last.kind === entry.kind &&
      last.subject === entry.subject &&
      last.outcome === entry.outcome &&
      last.reason === entry.reason &&
      last.decided_by === entry.decided_by
    ) {
      last.count += 1;
      continue;
    }
    result.push({ ...entry, count: 1 });
  }
  return result;
}

/** Who decided what, when, why and in which version — from persisted decisions. */
export default function DecisionLogList({
  entries,
  limit,
}: {
  entries: DecisionEntry[];
  limit?: number;
}) {
  const groups = grouped(entries);
  const shown = limit ? groups.slice(0, limit) : groups;
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
              {entry.count > 1
                ? LOG.many(entry.count, LOG.kinds[entry.kind])
                : LOG.kinds[entry.kind]}
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
              entry.version != null && entry.count === 1
                ? LOG.version(entry.version)
                : null,
            ]
              .filter(Boolean)
              .join(" · ")}
          </Text>
        </li>
      ))}
    </ol>
  );
}
