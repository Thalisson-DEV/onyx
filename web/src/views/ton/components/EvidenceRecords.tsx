"use client";

import { Text } from "@opal/components";
import { COPY, formatCurrency, formatDay, formatPeriod } from "@/lib/ton/copy";
import type { EvidenceRecord } from "@/lib/ton/decisions";

const FIELDS = COPY.decisionLoop.fields;

function facts(record: EvidenceRecord): [string, string][] {
  const items: [string, string | null][] =
    record.origin === "NG"
      ? [
          [FIELDS.document, record.document],
          [
            FIELDS.emission,
            record.emission_date ? formatDay(record.emission_date) : null,
          ],
          [FIELDS.account, record.account],
          [FIELDS.unit, record.unit],
          [FIELDS.history, record.description],
          [FIELDS.movement, record.movement_amount],
          [
            FIELDS.final,
            record.final_amount !== record.movement_amount
              ? record.final_amount
              : null,
          ],
        ]
      : [
          [FIELDS.invoice, record.document],
          [
            FIELDS.emission,
            record.emission_date ? formatDay(record.emission_date) : null,
          ],
          [
            FIELDS.competence,
            record.period ? formatPeriod(record.period) : null,
          ],
          [FIELDS.counterparty, record.counterparty],
          [FIELDS.service, record.service_amount],
          [FIELDS.net, record.net_amount],
        ];
  const money = new Set<string>([
    FIELDS.movement,
    FIELDS.final,
    FIELDS.service,
    FIELDS.net,
  ]);
  return items.flatMap(([label, value]) =>
    value == null || value === ""
      ? []
      : [[label, money.has(label) ? formatCurrency(value) : value]]
  );
}

function RecordCard({ record }: { record: EvidenceRecord }) {
  return (
    <div className="flex flex-col gap-2 rounded-12 border border-01 p-3 min-w-0">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <Text font="secondary-action" color="text-05">
          {COPY.decisionLoop.origin[record.origin]}
        </Text>
        {record.sheet && record.row != null && (
          <Text font="secondary-body" color="text-03">
            {COPY.decisionLoop.location(record.sheet, record.row)}
          </Text>
        )}
      </div>
      <dl className="grid grid-cols-[minmax(96px,auto)_1fr] gap-x-3 gap-y-1">
        {facts(record).map(([label, value]) => (
          <div key={label} className="contents">
            <dt>
              <Text font="secondary-body" color="text-03">
                {label}
              </Text>
            </dt>
            <dd className="min-w-0 break-words">
              <Text font="secondary-body" color="text-05">
                {value}
              </Text>
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

interface EvidenceRecordsProps {
  records: EvidenceRecord[];
  total: number;
  /** Reconciliation compares two sides; a missing side is itself evidence. */
  reconciliation?: boolean;
}

export default function EvidenceRecords({
  records,
  total,
  reconciliation,
}: EvidenceRecordsProps) {
  if (!records.length) {
    return (
      <Text font="secondary-body" color="text-03">
        {COPY.decisionLoop.noEvidence}
      </Text>
    );
  }
  const oneSided =
    reconciliation && new Set(records.map((item) => item.origin)).size === 1;
  return (
    <div className="flex flex-col gap-2">
      <div
        className={
          reconciliation
            ? "grid grid-cols-1 sm:grid-cols-2 gap-2"
            : "flex flex-col gap-2"
        }
      >
        {records.map((record, index) => (
          <RecordCard
            key={`${record.origin}-${record.sheet}-${record.row}-${index}`}
            record={record}
          />
        ))}
        {oneSided && (
          <div className="flex items-center rounded-12 border border-dashed border-02 p-3">
            <Text font="secondary-body" color="text-03">
              {COPY.decisionLoop.reconciliationGap}
            </Text>
          </div>
        )}
      </div>
      {!reconciliation && total > records.length && (
        <Text font="secondary-body" color="text-03">
          {COPY.decisionLoop.evidenceSample(records.length, total)}
        </Text>
      )}
    </div>
  );
}
