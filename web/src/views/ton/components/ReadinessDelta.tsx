"use client";

import { Text } from "@opal/components";
import { SvgArrowRight } from "@opal/icons";
import { cn } from "@opal/utils";
import { COPY, formatNumber } from "@/lib/ton/copy";
import { blockerDeltas, blockerLabel, sumBlockers } from "@/lib/ton/decisions";
import { StatusPill } from "@/views/ton/components/ui";

type ReadinessStatus = "READY" | "NOT_READY";

interface ReadinessDeltaProps {
  before: Record<string, number>;
  after: Record<string, number>;
  statusBefore: ReadinessStatus | null;
  statusAfter: ReadinessStatus;
  /** Hide categories whose count did not move. */
  changedOnly?: boolean;
}

function statusTone(status: ReadinessStatus) {
  return status === "READY" ? "success" : "warning";
}

/** Two backend readiness results side by side. Nothing here is estimated. */
export default function ReadinessDelta({
  before,
  after,
  statusBefore,
  statusAfter,
  changedOnly,
}: ReadinessDeltaProps) {
  const rows = blockerDeltas(before, after).filter(
    (row) => !changedOnly || row.before !== row.after
  );
  const labels = COPY.decisionLoop.result;
  return (
    <div className="flex flex-col gap-3">
      {statusBefore && statusBefore !== statusAfter && (
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill tone={statusTone(statusBefore)}>
            {COPY.decisionLoop.status[statusBefore]}
          </StatusPill>
          <SvgArrowRight size={14} className="text-text-03" />
          <StatusPill tone={statusTone(statusAfter)}>
            {COPY.decisionLoop.status[statusAfter]}
          </StatusPill>
        </div>
      )}
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-01">
            <th className="text-start py-1.5 pe-3 font-normal">
              <span className="ton-eyebrow">&nbsp;</span>
            </th>
            <th className="text-end py-1.5 px-3 font-normal w-16">
              <span className="ton-eyebrow">{labels.before}</span>
            </th>
            <th className="text-end py-1.5 ps-3 font-normal w-16">
              <span className="ton-eyebrow">{labels.now}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const moved = row.before !== row.after;
            return (
              <tr key={row.blocker} className="border-b border-01">
                <td className="py-2 pe-3">
                  <Text
                    font={moved ? "main-ui-action" : "main-ui-body"}
                    color={moved ? "text-05" : "text-04"}
                  >
                    {blockerLabel(row.blocker)}
                  </Text>
                </td>
                <td className="py-2 px-3 text-end">
                  <Text font="main-ui-body" color="text-03">
                    {formatNumber(row.before)}
                  </Text>
                </td>
                <td
                  className={cn(
                    "py-2 ps-3 text-end",
                    moved && row.after < row.before && "ton-brand-text"
                  )}
                >
                  <Text
                    font={moved ? "main-ui-action" : "main-ui-body"}
                    color={moved ? "inherit" : "text-04"}
                  >
                    {formatNumber(row.after)}
                  </Text>
                </td>
              </tr>
            );
          })}
          <tr>
            <td className="py-2 pe-3">
              <Text font="main-ui-action" color="text-05">
                {labels.total}
              </Text>
            </td>
            <td className="py-2 px-3 text-end">
              <Text font="main-ui-action" color="text-03">
                {formatNumber(sumBlockers(before))}
              </Text>
            </td>
            <td className="py-2 ps-3 text-end">
              <Text font="main-ui-action" color="text-05">
                {formatNumber(sumBlockers(after))}
              </Text>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
