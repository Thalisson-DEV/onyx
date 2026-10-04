"use client";

import { Fragment } from "react";
import { InputSingleSelect, Text } from "@opal/components";
import { SvgAlertTriangle, SvgCheckCircle } from "@opal/icons";
import { cn } from "@opal/utils";
import { formatCurrency } from "@/lib/ton/copy";
import {
  CLASSIFICATION_COPY,
  sectionOf,
  type ClassificationRow,
  type NatureView,
  type Section,
} from "@/lib/ton/classification";
import { NEW_NATURE } from "./shared";

const COPY = CLASSIFICATION_COPY.list;
const SECTIONS: Section[] = ["needs_you", "agrees", "confirmed"];

interface AccountGridProps {
  rows: ClassificationRow[];
  natures: NatureView[];
  selected: string | null;
  showConfirmed: boolean;
  onSelect: (code: string) => void;
  onPick: (code: string, accountId: string) => void;
  onNewNature: (code: string) => void;
}

function AssistantCell({ row }: { row: ClassificationRow }) {
  const suggestion = row.suggestion;
  if (!suggestion) {
    return (
      <Text font="secondary-body" color="text-03">
        {COPY.notAnalyzed}
      </Text>
    );
  }
  if (suggestion.agrees_with_current) {
    return (
      <span className="flex items-center gap-1.5">
        <SvgCheckCircle size={14} className="ton-brand-text shrink-0" />
        <Text font="secondary-body" color="text-04">
          {COPY.agrees}
        </Text>
      </span>
    );
  }
  return (
    <span className="flex items-start gap-1.5">
      <SvgAlertTriangle
        size={14}
        className="text-status-warning-05 shrink-0 mt-0.5"
      />
      <Text font="secondary-action" color="text-05">
        {COPY.suggests(suggestion.natureza)}
      </Text>
    </span>
  );
}

export default function AccountGrid({
  rows,
  natures,
  selected,
  showConfirmed,
  onSelect,
  onPick,
  onNewNature,
}: AccountGridProps) {
  const groups = SECTIONS.map((section) => ({
    section,
    rows: rows.filter((row) => sectionOf(row) === section),
  })).filter(
    (group) =>
      group.rows.length > 0 && (group.section !== "confirmed" || showConfirmed)
  );

  if (!groups.length) {
    return (
      <div className="ton-card p-5">
        <Text font="secondary-body" color="text-03">
          {COPY.empty}
        </Text>
      </div>
    );
  }

  return (
    <div className="ton-card overflow-x-auto">
      <table className="ton-statement ton-classification-grid w-full min-w-[720px] border-collapse">
        <thead>
          <tr>
            <th scope="col" className="text-start">
              {COPY.columns.code}
            </th>
            <th scope="col" className="text-start">
              {COPY.columns.description}
            </th>
            <th scope="col" className="text-start">
              {COPY.columns.nature}
            </th>
            <th scope="col" className="text-start">
              {COPY.columns.assistant}
            </th>
            <th scope="col">{COPY.columns.total}</th>
          </tr>
        </thead>
        <tbody>
          {groups.map((group) => (
            <Fragment key={group.section}>
              <tr data-type="SECTION">
                <td colSpan={5} className="text-start">
                  <span className="flex flex-wrap items-baseline gap-x-2">
                    <Text font="main-ui-action" color="text-05">
                      {`${COPY.sections[group.section].title} (${group.rows.length})`}
                    </Text>
                    <Text font="secondary-body" color="text-03">
                      {COPY.sections[group.section].hint}
                    </Text>
                  </span>
                </td>
              </tr>
              {group.rows.map((row) => (
                <tr
                  key={row.account_code}
                  aria-selected={row.account_code === selected}
                  data-code={row.account_code}
                  onClick={() => onSelect(row.account_code)}
                  className="cursor-pointer"
                >
                  <th scope="row" className="!min-w-0">
                    <Text font="secondary-action" color="text-05">
                      {row.account_code}
                    </Text>
                  </th>
                  <td className="text-start !whitespace-normal min-w-[12rem]">
                    <Text font="secondary-body" color="text-05">
                      {row.description || "—"}
                    </Text>
                  </td>
                  <td
                    className="text-start min-w-[13rem]"
                    onClick={(event) => event.stopPropagation()}
                  >
                    <InputSingleSelect
                      value={row.account_id ?? ""}
                      onValueChange={(value) => {
                        onSelect(row.account_code);
                        if (value === NEW_NATURE) onNewNature(row.account_code);
                        else if (value !== row.account_id)
                          onPick(row.account_code, value);
                      }}
                    >
                      <InputSingleSelect.Trigger
                        placeholder={COPY.noNature}
                        aria-label={`${COPY.columns.nature} ${row.account_code}`}
                      />
                      <InputSingleSelect.Content>
                        {natures.map((item) => (
                          <InputSingleSelect.Item
                            key={item.account_id}
                            value={item.account_id}
                          >
                            {item.natureza}
                          </InputSingleSelect.Item>
                        ))}
                        <InputSingleSelect.Item value={NEW_NATURE}>
                          {COPY.newNatureOption}
                        </InputSingleSelect.Item>
                      </InputSingleSelect.Content>
                    </InputSingleSelect>
                  </td>
                  <td className="text-start !whitespace-normal">
                    <AssistantCell row={row} />
                  </td>
                  <td>
                    <span
                      className={cn(
                        "ton-metric-num",
                        Number(row.total_amount) < 0 && "text-text-04"
                      )}
                    >
                      <Text font="secondary-body" color="inherit">
                        {formatCurrency(row.total_amount)}
                      </Text>
                    </span>
                  </td>
                </tr>
              ))}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
