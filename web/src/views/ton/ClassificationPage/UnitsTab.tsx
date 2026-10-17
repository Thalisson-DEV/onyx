"use client";

import { useState } from "react";
import useSWR from "swr";
import { Text } from "@opal/components";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { CLASSIFICATION_COPY } from "@/lib/ton/classification";
import { getBusinessLabel } from "@/lib/ton/labels";
import { ErrorState, LoadingBlock } from "@/views/ton/components/ui";
import UnitlessEntries from "./UnitlessEntries";

const COPY = CLASSIFICATION_COPY.units;
const UNITS_KEY = "/api/ton/financial-domain/units?limit=100";

interface UnitRow {
  id: string;
  code: string;
  name: string;
  kind: string;
  is_active: boolean;
}

/** Units that no longer operate leave the pickers; history stays intact. */
export default function UnitsTab() {
  const units = useSWR<UnitRow[]>(UNITS_KEY, errorHandlingFetcher);
  const [saving, setSaving] = useState<string | null>(null);
  const [failed, setFailed] = useState<string | null>(null);

  async function save(
    unit: UnitRow,
    change: { is_active?: boolean; kind?: string }
  ) {
    setSaving(unit.id);
    setFailed(null);
    try {
      const response = await fetch(
        `/api/ton/financial-domain/units/${unit.id}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(change),
        }
      );
      if (!response.ok) throw new Error(String(response.status));
      await units.mutate();
    } catch {
      setFailed(unit.id);
    } finally {
      setSaving(null);
    }
  }

  if (units.isLoading) return <LoadingBlock label={COPY.loading} />;
  if (units.error) return <ErrorState onRetry={() => units.mutate()} />;
  const rows = units.data ?? [];
  return (
    <div className="flex flex-col gap-4">
      <Text as="p" font="secondary-body" color="text-03">
        {COPY.intro}
      </Text>
      <div className="ton-card overflow-x-auto">
        <table className="ton-statement ton-classification-grid w-full min-w-[560px] border-collapse">
          <thead>
            <tr>
              <th scope="col">{COPY.columns.code}</th>
              <th scope="col">{COPY.columns.name}</th>
              <th scope="col">{COPY.columns.kind}</th>
              <th scope="col">{COPY.columns.status}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((unit) => (
              <tr key={unit.id} data-inactive={!unit.is_active || undefined}>
                <td>
                  <Text font="secondary-action" color="text-05">
                    {unit.code}
                  </Text>
                </td>
                <th scope="row">
                  <Text font="secondary-body" color="text-05">
                    {getBusinessLabel(unit.name)}
                  </Text>
                </th>
                <td>
                  <select
                    className="ton-select ton-focusable"
                    aria-label={COPY.kindOf(getBusinessLabel(unit.name))}
                    value={unit.kind}
                    disabled={saving === unit.id}
                    onChange={(event) =>
                      void save(unit, { kind: event.target.value })
                    }
                  >
                    {Object.entries(COPY.kinds).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      role="switch"
                      aria-checked={unit.is_active}
                      className="ton-checkbox"
                      checked={unit.is_active}
                      disabled={saving === unit.id}
                      aria-label={COPY.toggle(getBusinessLabel(unit.name))}
                      onChange={() =>
                        void save(unit, { is_active: !unit.is_active })
                      }
                    />
                    <Text font="secondary-body" color="text-04">
                      {unit.is_active ? COPY.active : COPY.inactive}
                    </Text>
                  </label>
                  {failed === unit.id && (
                    <Text font="secondary-body" color="status-error-05">
                      {COPY.failed}
                    </Text>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <UnitlessEntries
        units={rows
          .filter((unit) => unit.is_active)
          .map((unit) => ({ id: unit.id, name: unit.name }))}
      />
    </div>
  );
}
