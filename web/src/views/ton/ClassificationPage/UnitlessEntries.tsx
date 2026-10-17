"use client";

import { useState } from "react";
import useSWR from "swr";
import { Button, Text } from "@opal/components";
import { SvgRefreshCw } from "@opal/icons";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { CLASSIFICATION_COPY } from "@/lib/ton/classification";
import { formatCurrency } from "@/lib/ton/copy";
import type { EvidenceRecord } from "@/lib/ton/decisions";
import { postTonJson } from "@/lib/ton/decisions";
import { getBusinessLabel } from "@/lib/ton/labels";
import { ErrorState, LoadingBlock, StatusPill } from "@/views/ton/components/ui";

const COPY = CLASSIFICATION_COPY.unitless;
const LIST_KEY = "/api/ton/financial-review/unit-missing";

interface UnitlessItem {
  occurrence_id: string;
  open: boolean;
  records: EvidenceRecord[];
  assigned_unit_id: string | null;
}

interface UnitOption {
  id: string;
  name: string;
}

function day(value: string | null): string {
  return value ? value.slice(0, 10).split("-").reverse().join("/") : "—";
}

/**
 * NG entries without a unit, open or already accepted: the Controladoria says
 * which unit each belongs to. It takes effect when the base is recalculated.
 */
export default function UnitlessEntries({ units }: { units: UnitOption[] }) {
  const list = useSWR<UnitlessItem[]>(LIST_KEY, errorHandlingFetcher);
  const [selected, setSelected] = useState<string[]>([]);
  const [target, setTarget] = useState("");
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  // An empty unit undoes the assignment: the entry goes back to no unit.
  async function assign(ids: string[], unitId: string) {
    if (!ids.length) return;
    setBusy(true);
    setFailed(false);
    setMessage(null);
    try {
      for (const id of ids) {
        await postTonJson(
          `/api/ton/financial-review/occurrences/${id}/unit-assignment`,
          { unit_id: unitId || null, reason: "" }
        );
      }
      setPending((value) => value + ids.length);
      setSelected([]);
      await list.mutate();
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  async function recalculate() {
    setBusy(true);
    setFailed(false);
    try {
      const runs = await errorHandlingFetcher<Array<{ id: string }>>(
        "/api/ton/financial-domain/normalizations?limit=1"
      );
      const latest = runs[0];
      if (latest)
        await postTonJson(
          `/api/ton/financial-domain/normalizations/${latest.id}/recompute`,
          {}
        );
      setPending(0);
      setMessage(COPY.recalculated);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  if (list.isLoading) return <LoadingBlock label={COPY.loading} />;
  if (list.error) return <ErrorState onRetry={() => list.mutate()} />;
  const items = list.data ?? [];
  if (!items.length) return null;
  const assignedCount = items.filter((item) => item.assigned_unit_id).length;
  const allSelected = selected.length === items.length;
  return (
    <section className="flex flex-col gap-3" aria-labelledby="ton-unitless-title">
      <div className="flex flex-col gap-1">
        <span id="ton-unitless-title">
          <Text as="h3" font="heading-h3" color="text-05">
            {COPY.title}
          </Text>
        </span>
        <Text as="p" font="secondary-body" color="text-03">
          {COPY.intro(items.length, assignedCount)}
        </Text>
      </div>
      {(pending > 0 || message) && (
        <div className="ton-guide">
          <Text font="main-ui-body" color="text-04">
            {pending > 0 ? COPY.pending(pending) : message ?? ""}
          </Text>
          {pending > 0 && (
            <Button
              icon={SvgRefreshCw}
              disabled={busy}
              onClick={() => void recalculate()}
            >
              {COPY.recalculate}
            </Button>
          )}
        </div>
      )}
      {selected.length > 0 && (
        <div className="ton-bulk-bar">
          <Text font="main-ui-action" color="text-05">
            {COPY.selected(selected.length)}
          </Text>
          <span className="flex-1" />
          <select
            className="ton-select ton-focusable max-w-64"
            aria-label={COPY.bulkUnit}
            value={target}
            onChange={(event) => setTarget(event.target.value)}
          >
            <option value="">{COPY.chooseUnit}</option>
            {units.map((unit) => (
              <option key={unit.id} value={unit.id}>
                {getBusinessLabel(unit.name)}
              </option>
            ))}
          </select>
          <Button
            disabled={busy || !target}
            onClick={() => void assign(selected, target)}
          >
            {COPY.assign}
          </Button>
        </div>
      )}
      {failed && (
        <Text font="secondary-body" color="status-error-05">
          {COPY.failed}
        </Text>
      )}
      <div className="ton-queue-table-wrap">
        <table className="ton-queue-table w-full border-collapse">
          <thead>
            <tr>
              <th scope="col" className="w-10">
                <input
                  type="checkbox"
                  className="ton-checkbox"
                  aria-label={COPY.selectAll}
                  checked={allSelected}
                  onChange={() =>
                    setSelected(
                      allSelected ? [] : items.map((item) => item.occurrence_id)
                    )
                  }
                />
              </th>
              <th scope="col" className="text-start">
                {COPY.columns.entry}
              </th>
              <th scope="col" className="text-start">
                {COPY.columns.date}
              </th>
              <th scope="col" className="text-end">
                {COPY.columns.amount}
              </th>
              <th scope="col" className="text-start">
                {COPY.columns.unit}
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const record = item.records[0];
              const checked = selected.includes(item.occurrence_id);
              return (
                <tr key={item.occurrence_id} aria-selected={checked || undefined}>
                  <td>
                    <input
                      type="checkbox"
                      className="ton-checkbox"
                      aria-label={COPY.selectRow(record?.document ?? "")}
                      checked={checked}
                      onChange={() =>
                        setSelected((old) =>
                          checked
                            ? old.filter((id) => id !== item.occurrence_id)
                            : [...old, item.occurrence_id]
                        )
                      }
                    />
                  </td>
                  <td className="ton-queue-item">
                    <span className="flex flex-wrap items-center gap-2">
                      <Text font="main-ui-action" color="text-05">
                        {[record?.document, record?.account]
                          .filter(Boolean)
                          .join(" · ")}
                      </Text>
                      <StatusPill tone={item.open ? "warning" : "neutral"}>
                        {item.open ? COPY.open : COPY.accepted}
                      </StatusPill>
                    </span>
                    <span className="ton-queue-detail">
                      {record?.description ?? ""}
                    </span>
                  </td>
                  <td className="whitespace-nowrap">
                    {day(record?.emission_date ?? null)}
                  </td>
                  <td className="text-end whitespace-nowrap ton-queue-amount">
                    {record?.movement_amount
                      ? formatCurrency(record.movement_amount)
                      : "—"}
                  </td>
                  <td>
                    <select
                      className="ton-select ton-focusable"
                      aria-label={COPY.unitOf(record?.document ?? "")}
                      value={item.assigned_unit_id ?? ""}
                      disabled={busy}
                      onChange={(event) =>
                        void assign([item.occurrence_id], event.target.value)
                      }
                    >
                      <option value="">{COPY.noUnit}</option>
                      {units.map((unit) => (
                        <option key={unit.id} value={unit.id}>
                          {getBusinessLabel(unit.name)}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
