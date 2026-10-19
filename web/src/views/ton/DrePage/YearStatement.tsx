"use client";

import { Fragment, useState } from "react";
import { Text } from "@opal/components";
import {
  SvgChevronDown,
  SvgChevronRight,
  SvgColumn,
  SvgMenu,
} from "@opal/icons";
import { cn } from "@opal/utils";
import { COPY, formatAmount, formatMonthName } from "@/lib/ton/copy";
import { getBusinessLabel } from "@/lib/ton/labels";
import type { DreDefinition, DreLine } from "@/views/admin/DrePage/types";
import type {
  DreWorkspace,
  YearMonthView,
} from "@/views/ton/DrePage/useDreWorkspace";

const T = COPY.dre.year;

function depthOf(definition: DreDefinition, definitions: DreDefinition[]) {
  let depth = 0;
  let parent = definition.parent_code;
  while (parent) {
    depth += 1;
    parent =
      definitions.find((item) => item.code === parent)?.parent_code ?? null;
  }
  return depth;
}

function hiddenBy(
  definition: DreDefinition,
  definitions: DreDefinition[],
  collapsed: string[]
) {
  let parent = definition.parent_code;
  while (parent) {
    if (collapsed.includes(parent)) return true;
    parent =
      definitions.find((item) => item.code === parent)?.parent_code ?? null;
  }
  return false;
}

function isPercent(definition: DreDefinition) {
  return definition.line_type === "PERCENTAGE";
}

/** Number cell: no currency symbol per cell, negatives tinted. */
function Amount({
  value,
  definition,
}: {
  value: string | null | undefined;
  definition: DreDefinition;
}) {
  if (value == null) return <span className="ton-amount-empty">—</span>;
  const number = Number(value);
  return (
    <span
      className={cn(
        number < 0 && "ton-amount-negative",
        number === 0 && "ton-amount-zero"
      )}
    >
      {isPercent(definition) ? `${formatAmount(value)}%` : formatAmount(value)}
    </span>
  );
}

function useCollapsed() {
  const [collapsed, setCollapsed] = useState<string[]>([]);
  return {
    collapsed,
    toggle(code: string) {
      setCollapsed((old) =>
        old.includes(code)
          ? old.filter((item) => item !== code)
          : [...old, code]
      );
    },
  };
}

function LineLabel({
  definition,
  definitions,
  collapsed,
  onToggle,
  onDrill,
}: {
  definition: DreDefinition;
  definitions: DreDefinition[];
  collapsed: string[];
  onToggle: (code: string) => void;
  /** Opens the entries of the line; only lines fed by entries have it. */
  onDrill?: () => void;
}) {
  const label = getBusinessLabel(definition.label);
  const hasChildren = definitions.some(
    (item) => item.parent_code === definition.code
  );
  const isCollapsed = collapsed.includes(definition.code);
  return (
    <span
      className="flex items-center gap-1"
      style={{
        paddingInlineStart: depthOf(definition, definitions) * 16,
      }}
    >
      {hasChildren ? (
        <button
          type="button"
          className="ton-focusable flex items-center justify-center w-5 h-5 rounded-04 text-text-03 hover:text-text-05"
          aria-label={
            isCollapsed
              ? COPY.dre.table.expand(label)
              : COPY.dre.table.collapse(label)
          }
          aria-expanded={!isCollapsed}
          onClick={() => onToggle(definition.code)}
        >
          {isCollapsed ? (
            <SvgChevronRight size={14} />
          ) : (
            <SvgChevronDown size={14} />
          )}
        </button>
      ) : (
        <span className="w-5 shrink-0" aria-hidden />
      )}
      {onDrill && definition.line_type === "SOURCE_SUM" ? (
        <button
          type="button"
          className="ton-focusable ton-statement-drill text-start rounded-04 truncate"
          aria-label={COPY.dre.table.drill(label)}
          onClick={onDrill}
        >
          {label}
        </button>
      ) : (
        <span className="truncate">{label}</span>
      )}
      {definition.excluded && (
        <span className="shrink-0">
          <Text font="secondary-body" color="text-03">
            {`(${COPY.dre.table.excluded})`}
          </Text>
        </span>
      )}
    </span>
  );
}

/** A value that opens the entries behind it, for one month. */
function DrillCell({
  dre,
  definition,
  month,
  line,
}: {
  dre: DreWorkspace;
  definition: DreDefinition;
  month: YearMonthView;
  line: DreLine | undefined;
}) {
  const period = month.period;
  const selected =
    dre.selectedLine?.code === definition.code &&
    dre.drillRun?.scope.period === period;
  // A set of units has no single result to open: drill needs one unit.
  if (definition.line_type !== "SOURCE_SUM" || !line || !month.runId) {
    return (
      <td>
        <Amount value={line?.realizado} definition={definition} />
      </td>
    );
  }
  return (
    <td aria-selected={selected || undefined}>
      <button
        type="button"
        className="ton-focusable ton-cell-drill"
        aria-label={T.drillCell(
          getBusinessLabel(definition.label),
          formatMonthName(period)
        )}
        onClick={() => dre.select.line(definition.code, period)}
      >
        <Amount value={line.realizado} definition={definition} />
      </button>
    </td>
  );
}

function byCode(month: YearMonthView | undefined) {
  return new Map((month?.lines ?? []).map((line) => [line.code, line]));
}

/** Lines from top to bottom, one column per selected month, then the year. */
function ColumnsView({ dre }: { dre: DreWorkspace }) {
  const { collapsed, toggle } = useCollapsed();
  const definitions = dre.definitions;
  const months = dre.shownMonths;
  const monthLines = months.map(byCode);
  const latestShown = months.at(-1)?.period;
  // The last column adds up the months on screen: with every month shown it
  // is the year to date; with a few chosen, it is the total of those.
  const everyMonth = months.length === dre.yearMonths.length;
  const totalOf = (code: string): string | null => {
    let total = 0;
    let any = false;
    for (const lines of monthLines) {
      const value = lines.get(code)?.realizado;
      if (value == null) continue;
      total += Number(value);
      any = true;
    }
    return any ? total.toFixed(2) : null;
  };
  return (
    <div className="ton-statement-scroll">
      <table className="ton-statement ton-matrix w-full border-collapse">
        <thead>
          <tr>
            <th scope="col" className="text-start">
              {T.lineHeader}
            </th>
            {months.map((month) => (
              <th key={month.period} scope="col">
                {formatMonthName(month.period)}
              </th>
            ))}
            {months.length > 1 && (
              <th scope="col" className="ton-statement-ytd">
                {everyMonth
                  ? T.ytdHeader(months[0]?.period ?? "", latestShown ?? "")
                  : T.shownTotal(months.map((month) => month.period))}
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {definitions.map((definition) => {
            if (hiddenBy(definition, definitions, collapsed)) return null;
            return (
              <tr key={definition.code} data-type={definition.line_type}>
                <th scope="row">
                  <LineLabel
                    definition={definition}
                    definitions={definitions}
                    collapsed={collapsed}
                    onToggle={toggle}
                    onDrill={
                      latestShown && !dre.multi
                        ? () => dre.select.line(definition.code, latestShown)
                        : undefined
                    }
                  />
                </th>
                {months.map((month, index) => (
                  <DrillCell
                    key={month.period}
                    dre={dre}
                    definition={definition}
                    month={month}
                    line={monthLines[index]?.get(definition.code)}
                  />
                ))}
                {months.length > 1 && (
                  <td className="ton-statement-ytd">
                    <Amount value={totalOf(definition.code)} definition={definition} />
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function MonthBlock({
  dre,
  month,
  open,
  onToggle,
}: {
  dre: DreWorkspace;
  month: YearMonthView;
  open: boolean;
  onToggle: () => void;
}) {
  const { collapsed, toggle } = useCollapsed();
  const definitions = dre.definitions;
  const lines = byCode(month);
  const period = month.period;
  const summary = dre.summaryDefinition;
  const result = summary ? lines.get(summary.code) : undefined;
  const id = `ton-dre-month-${period}`;
  return (
    <section className="ton-month-block" aria-labelledby={`${id}-title`}>
      <button
        type="button"
        className="ton-focusable ton-month-block-header"
        aria-expanded={open}
        aria-controls={id}
        onClick={onToggle}
      >
        {open ? <SvgChevronDown size={16} /> : <SvgChevronRight size={16} />}
        <span id={`${id}-title`} className="flex-1 text-start">
          <Text font="main-ui-action" color="text-05">
            {formatMonthName(period, true)}
          </Text>
        </span>
        {summary && result && (
          <span className="flex items-baseline gap-2">
            <Text font="secondary-body" color="text-03">
              {getBusinessLabel(summary.label)}
            </Text>
            <span className="ton-month-block-total">
              <Amount value={result.realizado} definition={summary} />
            </span>
          </span>
        )}
      </button>
      {open && (
        <div id={id} className="overflow-x-auto">
          <table className="ton-statement w-full border-collapse">
            <thead>
              <tr>
                <th scope="col" className="text-start">
                  {T.lineHeader}
                </th>
                <th scope="col">{formatMonthName(period)}</th>
                {dre.budgetPresent && (
                  <th scope="col">{COPY.dre.table.budget}</th>
                )}
                {dre.budgetPresent && (
                  <th scope="col">{COPY.dre.table.variance}</th>
                )}
                <th scope="col" className="ton-statement-ytd">
                  {T.ytdUntil(period)}
                </th>
              </tr>
            </thead>
            <tbody>
              {definitions.map((definition) => {
                if (hiddenBy(definition, definitions, collapsed)) return null;
                const line = lines.get(definition.code);
                return (
                  <tr key={definition.code} data-type={definition.line_type}>
                    <th scope="row">
                      <LineLabel
                        definition={definition}
                        definitions={definitions}
                        collapsed={collapsed}
                        onToggle={toggle}
                        onDrill={
                          dre.multi
                            ? undefined
                            : () => dre.select.line(definition.code, period)
                        }
                      />
                    </th>
                    <DrillCell
                      dre={dre}
                      definition={definition}
                      month={month}
                      line={line}
                    />
                    {dre.budgetPresent && (
                      <td>
                        <Amount value={line?.orcado} definition={definition} />
                      </td>
                    )}
                    {dre.budgetPresent && (
                      <td>
                        <Amount
                          value={line?.variance}
                          definition={definition}
                        />
                      </td>
                    )}
                    <td className="ton-statement-ytd">
                      <Amount
                        value={line?.realizado_ytd}
                        definition={definition}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

/** One block per month from top to bottom; the latest one starts open. */
function StackedView({ dre }: { dre: DreWorkspace }) {
  const latest = dre.shownMonths.at(-1)?.period;
  const [open, setOpen] = useState<string[]>(latest ? [latest] : []);
  const all = dre.shownMonths.map((month) => month.period);
  const everyOpen = all.every((period) => open.includes(period));
  return (
    <div className="flex flex-col gap-2">
      <div className="flex justify-end">
        <button
          type="button"
          className="ton-focusable ton-link-button"
          onClick={() => setOpen(everyOpen ? [] : all)}
        >
          {everyOpen ? T.collapseAll : T.expandAll}
        </button>
      </div>
      {dre.shownMonths.map((month) => {
        const period = month.period;
        return (
          <MonthBlock
            key={period}
            dre={dre}
            month={month}
            open={open.includes(period)}
            onToggle={() =>
              setOpen((old) =>
                old.includes(period)
                  ? old.filter((item) => item !== period)
                  : [...old, period]
              )
            }
          />
        );
      })}
    </div>
  );
}

/** View switch and the months to show; blocked months cannot be picked. */
function MonthControls({ dre }: { dre: DreWorkspace }) {
  const calculated = new Set(
    dre.yearMonths.map((month) => month.period)
  );
  const shown = new Set(dre.shownMonths.map((month) => month.period));
  const periods = dre.periods.filter(
    (item) => !dre.periodValue || item.scope.period <= dre.periodValue
  );
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div
        className="flex flex-wrap items-center gap-1.5"
        role="group"
        aria-label={T.monthsLabel}
      >
        {periods.map((item) => {
          const period = item.scope.period;
          const available = calculated.has(period);
          const pressed = shown.has(period);
          return (
            <button
              key={period}
              type="button"
              disabled={!available}
              aria-pressed={pressed}
              title={
                available
                  ? formatMonthName(period, true)
                  : item.status === "READY"
                    ? T.notCalculated
                    : T.blocked
              }
              onClick={() => dre.select.month(period)}
              className={cn(
                "ton-month ton-focusable flex items-center gap-1.5 px-2.5 py-1",
                pressed && "ton-month-selected",
                !available && "ton-month-disabled"
              )}
            >
              {!available && (
                <span aria-hidden className="ton-dot" data-tone="warning" />
              )}
              <Text font="secondary-action" color="inherit">
                {formatMonthName(period)}
              </Text>
            </button>
          );
        })}
        {dre.monthChoice !== null && (
          <button
            type="button"
            className="ton-focusable ton-link-button ms-1"
            onClick={dre.select.allMonths}
          >
            {T.allMonths}
          </button>
        )}
      </div>
      <div className="ton-segmented" role="group" aria-label={T.viewLabel}>
        {(
          [
            ["columns", SvgColumn, T.columns],
            ["stacked", SvgMenu, T.stacked],
          ] as const
        ).map(([value, Icon, label]) => (
          <button
            key={value}
            type="button"
            aria-pressed={dre.view === value}
            className="ton-focusable ton-segment flex items-center gap-1.5"
            onClick={() => dre.select.view(value)}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function YearStatement({ dre }: { dre: DreWorkspace }) {
  return (
    <Fragment>
      <MonthControls dre={dre} />
      {dre.view === "columns" ? (
        <ColumnsView dre={dre} />
      ) : (
        <StackedView dre={dre} />
      )}
    </Fragment>
  );
}
