"use client";

import { Text } from "@opal/components";
import { COPY, formatCurrency } from "@/lib/ton/copy";
import type { EvidenceRecord } from "@/lib/ton/decisions";
import { StatusPill } from "@/views/ton/components/ui";

const T = COPY.pending.duplicate;

function day(value: string | null): string {
  return value ? value.slice(0, 10).split("-").reverse().join("/") : "—";
}

/**
 * The two rows of a duplicate next to each other, with the differences
 * marked, so the person sees what repeats before deciding.
 */
export default function DuplicateCompare({
  kept,
  repeated,
}: {
  kept: EvidenceRecord;
  repeated: EvidenceRecord;
}) {
  const fields: Array<[string, (record: EvidenceRecord) => string]> = [
    [T.where, (record) => (record.sheet ? `${record.sheet} · ${record.row ?? "—"}` : "—")],
    [T.document, (record) => record.document ?? "—"],
    [T.date, (record) => day(record.emission_date)],
    [T.account, (record) => record.account ?? "—"],
    [T.unit, (record) => record.unit ?? "—"],
    [T.amount, (record) => formatCurrency(record.movement_amount)],
    [T.history, (record) => record.description ?? "—"],
  ];
  return (
    <div className="ton-compare">
      <table className="w-full border-collapse">
        <thead>
          <tr>
            <th scope="col">
              <span className="sr-only">{T.field}</span>
            </th>
            <th scope="col">
              <span className="flex flex-col items-start gap-1">
                {T.kept}
                <StatusPill tone="success">{T.stays}</StatusPill>
              </span>
            </th>
            <th scope="col">
              <span className="flex flex-col items-start gap-1">
                {T.repeated}
                <StatusPill tone="warning">{T.inQuestion}</StatusPill>
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          {fields.map(([label, read]) => {
            const left = read(kept);
            const right = read(repeated);
            const differs = left !== right;
            return (
              <tr key={label} data-differs={differs || undefined}>
                <th scope="row">
                  <Text font="secondary-body" color="text-03">
                    {label}
                  </Text>
                </th>
                <td>{left}</td>
                <td>{right}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <Text as="p" font="secondary-body" color="text-03">
        {T.note}
      </Text>
    </div>
  );
}
