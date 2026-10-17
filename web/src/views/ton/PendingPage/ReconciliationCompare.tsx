"use client";

import { Text } from "@opal/components";
import { COPY, formatCurrency, formatPeriod } from "@/lib/ton/copy";
import type { EvidenceRecord } from "@/lib/ton/decisions";
import { StatusPill } from "@/views/ton/components/ui";

const T = COPY.pending.compare;

function day(value: string | null): string {
  return value ? value.slice(0, 10).split("-").reverse().join("/") : "—";
}

function amountOf(record: EvidenceRecord): string | null {
  return record.origin === "NG" ? record.movement_amount : record.service_amount;
}

/** Up to three decimals, so a billing value like 0,078 is not hidden. */
function exact(value: string | null): string {
  if (value == null) return "—";
  const number = Number(value);
  const cents = Math.round(number * 100) / 100;
  return cents === number
    ? formatCurrency(value)
    : `${formatCurrency(String(cents))} (${number.toLocaleString("pt-BR", {
        minimumFractionDigits: 3,
        maximumFractionDigits: 3,
      })})`;
}

/**
 * The NG entry and the billing invoice of one match side by side, with the
 * fields that differ marked and the difference in value stated.
 */
export default function ReconciliationCompare({
  records,
}: {
  records: EvidenceRecord[];
}) {
  const fields: Array<[string, (record: EvidenceRecord) => string]> = [
    [T.document, (record) => record.document ?? "—"],
    [T.emission, (record) => day(record.emission_date)],
    [
      T.competence,
      (record) => (record.period ? formatPeriod(record.period) : "—"),
    ],
    [T.who, (record) => record.unit ?? record.counterparty ?? "—"],
    [T.account, (record) => record.account ?? "—"],
    [T.amount, (record) => exact(amountOf(record))],
    [T.net, (record) => (record.net_amount ? exact(record.net_amount) : "—")],
    [T.description, (record) => record.description ?? "—"],
    [
      T.where,
      (record) => (record.sheet ? `${record.sheet} · ${record.row ?? "—"}` : "—"),
    ],
  ];
  const ng = records.filter((record) => record.origin === "NG");
  const billing = records.filter((record) => record.origin === "BILLING");
  const ngTotal = ng.reduce((sum, record) => sum + Number(amountOf(record) ?? 0), 0);
  const billingTotal = billing.reduce(
    (sum, record) => sum + Number(amountOf(record) ?? 0),
    0
  );
  const difference = ngTotal - billingTotal;
  const rounding = Math.abs(difference) > 0 && Math.abs(difference) < 0.01;
  const ordered = [...ng, ...billing];
  return (
    <div className="ton-compare">
      {ng.length > 0 && billing.length > 0 && (
        <div className="ton-compare-summary">
          <span>
            <Text font="secondary-body" color="text-03">
              {T.ngTotal}
            </Text>
            <Text font="main-ui-action" color="text-05">
              {exact(String(ngTotal))}
            </Text>
          </span>
          <span>
            <Text font="secondary-body" color="text-03">
              {T.billingTotal}
            </Text>
            <Text font="main-ui-action" color="text-05">
              {exact(String(billingTotal))}
            </Text>
          </span>
          <span>
            <Text font="secondary-body" color="text-03">
              {T.difference}
            </Text>
            <Text font="main-ui-action" color="text-05">
              {rounding
                ? T.rounding(
                    Math.abs(difference).toLocaleString("pt-BR", {
                      maximumFractionDigits: 4,
                    })
                  )
                : formatCurrency(String(difference))}
            </Text>
          </span>
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th scope="col">
                <span className="sr-only">{T.field}</span>
              </th>
              {ordered.map((record, index) => (
                <th scope="col" key={`${record.origin}-${index}`}>
                  <StatusPill tone={record.origin === "NG" ? "brand" : "neutral"}>
                    {record.origin === "NG" ? T.ng : T.billing}
                  </StatusPill>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {fields.map(([label, read]) => {
              const values = ordered.map(read);
              const differs =
                ordered.length > 1 &&
                new Set(values.filter((value) => value !== "—")).size > 1;
              return (
                <tr key={label} data-differs={differs || undefined}>
                  <th scope="row">
                    <Text font="secondary-body" color="text-03">
                      {label}
                    </Text>
                  </th>
                  {values.map((value, index) => (
                    <td key={index}>{value}</td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
