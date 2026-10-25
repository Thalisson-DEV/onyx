"use client";

import { Fragment, useState, type ReactNode } from "react";
import useSWR from "swr";
import { Text } from "@opal/components";
import {
  SvgChevronDown,
  SvgChevronRight,
  SvgColumn,
  SvgMenu,
  SvgSearch,
} from "@opal/icons";
import { cn } from "@opal/utils";
import { COPY, formatAmount, formatMonthName } from "@/lib/ton/copy";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { getBusinessLabel } from "@/lib/ton/labels";
import type {
  DreDefinition,
  DreLine,
  DreLineAccount,
} from "@/views/admin/DrePage/types";
import type {
  DreWorkspace,
  YearMonthView,
} from "@/views/ton/DrePage/useDreWorkspace";
import { ViewTabs } from "@/views/ton/components/kit";

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

/** A line fed by NG naturezas: it opens into its NG accounts, as in the BI. */
function isNatureLine(definition: DreDefinition) {
  return (
    definition.line_type === "SOURCE_SUM" &&
    (definition.source ?? "NG_ACCOUNTS") === "NG_ACCOUNTS"
  );
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
  accountsOpen,
  onAccounts,
}: {
  definition: DreDefinition;
  definitions: DreDefinition[];
  collapsed: string[];
  onToggle: (code: string) => void;
  /** Opens the entries of the line; only lines fed by entries have it. */
  onDrill?: () => void;
  accountsOpen?: boolean;
  /** Shows or hides the NG accounts of a natureza line. */
  onAccounts?: () => void;
}) {
  const label = getBusinessLabel(definition.label);
  const hasChildren = definitions.some(
    (item) => item.parent_code === definition.code
  );
  const isCollapsed = collapsed.includes(definition.code);
  const accountsToggle =
    !hasChildren && onAccounts ? (
      <button
        type="button"
        className="ton-focusable flex items-center justify-center w-5 h-5 rounded-04 text-text-03 hover:text-text-05"
        aria-label={
          accountsOpen
            ? COPY.dre.table.hideAccounts(label)
            : COPY.dre.table.showAccounts(label)
        }
        aria-expanded={!!accountsOpen}
        onClick={onAccounts}
      >
        {accountsOpen ? (
          <SvgChevronDown size={14} />
        ) : (
          <SvgChevronRight size={14} />
        )}
      </button>
    ) : null;
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
        (accountsToggle ?? <span className="w-5 shrink-0" aria-hidden />)
      )}
      {onDrill ? (
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
  if (!line || !month.runId) {
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

function useOpenAccounts() {
  const [open, setOpen] = useState<string[]>([]);
  return {
    open,
    toggle(code: string) {
      setOpen((old) =>
        old.includes(code)
          ? old.filter((item) => item !== code)
          : [...old, code]
      );
    },
  };
}

/** The NG accounts of a natureza line, one row each, right under it. */
function AccountRows({
  definition,
  definitions,
  runIds,
  span,
  cells,
}: {
  definition: DreDefinition;
  definitions: DreDefinition[];
  /** The month results whose accounts are read. */
  runIds: string[];
  /** Columns after the label, for the loading and error rows. */
  span: number;
  cells: (account: DreLineAccount) => ReactNode;
}) {
  const query = runIds
    .map((id) => `run_ids=${encodeURIComponent(id)}`)
    .join("&");
  const accounts = useSWR<DreLineAccount[]>(
    runIds.length
      ? `/api/ton/dre/lines/${encodeURIComponent(definition.code)}/accounts?${query}`
      : null,
    errorHandlingFetcher
  );
  const indent = (depthOf(definition, definitions) + 1) * 16 + 24;
  if (!accounts.data) {
    return (
      <tr data-type="ACCOUNT">
        <th
          scope="row"
          colSpan={span + 1}
          style={{ paddingInlineStart: indent }}
        >
          {accounts.error
            ? COPY.dre.table.accountsFailed
            : COPY.dre.table.accountsLoading}
        </th>
      </tr>
    );
  }
  return (
    <>
      {accounts.data.map((account) => (
        <tr key={account.account_code ?? ""} data-type="ACCOUNT">
          <th
            scope="row"
            aria-label={
              [account.account_code, account.account_label]
                .filter(Boolean)
                .join(" ") || COPY.dre.table.noAccount
            }
          >
            <span
              className="flex items-baseline gap-2"
              style={{ paddingInlineStart: indent }}
            >
              <span className="ton-account-code shrink-0">
                {account.account_code ?? ""}
              </span>
              <span className="truncate">
                {account.account_label ??
                  (account.account_code ? "" : COPY.dre.table.noAccount)}
              </span>
            </span>
          </th>
          {cells(account)}
        </tr>
      ))}
    </>
  );
}

/** An account's value in one month, opening its entries when it has a code. */
function AccountCell({
  dre,
  definition,
  account,
  period,
}: {
  dre: DreWorkspace;
  definition: DreDefinition;
  account: DreLineAccount;
  period: string;
}) {
  const value = account.months[period];
  const code = account.account_code;
  if (value == null || !code) {
    return (
      <td>
        <Amount value={value} definition={definition} />
      </td>
    );
  }
  return (
    <td>
      <button
        type="button"
        className="ton-focusable ton-cell-drill"
        aria-label={T.drillCell(
          `${code} ${account.account_label ?? ""}`.trim(),
          formatMonthName(period)
        )}
        onClick={() =>
          dre.select.line(definition.code, period, {
            code,
            label: account.account_label,
            amount: value,
          })
        }
      >
        <Amount value={value} definition={definition} />
      </button>
    </td>
  );
}

/** A change of 10% or more against the month before deserves a look. */
const CHANGE_THRESHOLD = 10;

function ChangeCell({ value }: { value: number | null }) {
  const big = value != null && Math.abs(value) >= CHANGE_THRESHOLD;
  return (
    <td className="ton-statement-ytd">
      <span className={cn("ton-change", big && "ton-change-big")}>
        {formatChange(value)}
      </span>
    </td>
  );
}

function sumOf(account: DreLineAccount, periods: string[]): string | null {
  let total = 0;
  let any = false;
  for (const period of periods) {
    const value = account.months[period];
    if (value == null) continue;
    total += Number(value);
    any = true;
  }
  return any ? total.toFixed(2) : null;
}

function byCode(month: YearMonthView | undefined) {
  return new Map((month?.lines ?? []).map((line) => [line.code, line]));
}

/** Change of the last shown month against the one before, in percent. */
function changeOf(last: string | undefined, previous: string | undefined) {
  if (last == null || previous == null) return null;
  const before = Number(previous);
  if (!before) return null;
  // By size: a cost that fell reads as a fall, whatever its sign.
  return ((Math.abs(Number(last)) - Math.abs(before)) / Math.abs(before)) * 100;
}

function formatChange(value: number | null): string {
  if (value == null) return "—";
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${Math.abs(value).toLocaleString("pt-BR", { maximumFractionDigits: 1, minimumFractionDigits: 1 })}%`;
}

export type StatementFilter = "all" | "changed" | "excluded";

interface ColumnsViewProps {
  dre: DreWorkspace;
  filter: StatementFilter;
  query: string;
}

/** Lines from top to bottom, one column per selected month, then the year. */
function ColumnsView({ dre, filter, query }: ColumnsViewProps) {
  const { collapsed, toggle } = useCollapsed();
  const accounts = useOpenAccounts();
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
  const lastLines = monthLines.at(-1);
  const previousLines = monthLines.at(-2);
  const showChange = months.length > 1;
  const needle = query.trim().toLowerCase();
  const filtering = filter !== "all" || !!needle;
  const matches = (definition: DreDefinition) => {
    if (
      needle &&
      !`${definition.code} ${getBusinessLabel(definition.label)}`
        .toLowerCase()
        .includes(needle)
    )
      return false;
    if (filter === "excluded") return !!definition.excluded;
    if (filter === "changed") {
      const change = changeOf(
        lastLines?.get(definition.code)?.realizado,
        previousLines?.get(definition.code)?.realizado
      );
      return change != null && Math.abs(change) >= CHANGE_THRESHOLD;
    }
    return true;
  };
  const shown = filtering
    ? definitions.filter(matches)
    : definitions.filter(
        (definition) => !hiddenBy(definition, definitions, collapsed)
      );
  if (filtering && shown.length === 0)
    return (
      <div className="py-6 text-center">
        <Text font="secondary-body" color="text-03">
          {T.noMatch}
        </Text>
      </div>
    );
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
            {showChange && (
              <th scope="col" className="ton-statement-ytd">
                {T.changeHeader(
                  months.at(-1)?.period ?? "",
                  months.at(-2)?.period ?? ""
                )}
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {shown.map((definition) => {
            const canOpen =
              !dre.multi &&
              isNatureLine(definition) &&
              dre.natureLineCodes.has(definition.code);
            const open = canOpen && accounts.open.includes(definition.code);
            const periods = months.map((month) => month.period);
            return (
              <Fragment key={definition.code}>
                <tr data-type={definition.line_type}>
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
                      accountsOpen={open}
                      onAccounts={
                        canOpen
                          ? () => accounts.toggle(definition.code)
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
                      {latestShown && !dre.multi ? (
                        <button
                          type="button"
                          className="ton-focusable ton-cell-drill"
                          aria-label={T.drillTotal(
                            getBusinessLabel(definition.label)
                          )}
                          onClick={() =>
                            dre.select.line(definition.code, latestShown)
                          }
                        >
                          <Amount
                            value={totalOf(definition.code)}
                            definition={definition}
                          />
                        </button>
                      ) : (
                        <Amount
                          value={totalOf(definition.code)}
                          definition={definition}
                        />
                      )}
                    </td>
                  )}
                  {showChange && (
                    <ChangeCell
                      value={changeOf(
                        lastLines?.get(definition.code)?.realizado,
                        previousLines?.get(definition.code)?.realizado
                      )}
                    />
                  )}
                </tr>
                {open && (
                  <AccountRows
                    definition={definition}
                    definitions={definitions}
                    runIds={months.flatMap((month) =>
                      month.runId ? [month.runId] : []
                    )}
                    span={months.length + (months.length > 1 ? 2 : 0)}
                    cells={(account) => (
                      <>
                        {months.map((month) => (
                          <AccountCell
                            key={month.period}
                            dre={dre}
                            definition={definition}
                            account={account}
                            period={month.period}
                          />
                        ))}
                        {months.length > 1 && (
                          <td className="ton-statement-ytd">
                            <Amount
                              value={sumOf(account, periods)}
                              definition={definition}
                            />
                          </td>
                        )}
                        {showChange && (
                          <ChangeCell
                            value={changeOf(
                              account.months[months.at(-1)?.period ?? ""],
                              account.months[months.at(-2)?.period ?? ""]
                            )}
                          />
                        )}
                      </>
                    )}
                  />
                )}
              </Fragment>
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
  const accounts = useOpenAccounts();
  const definitions = dre.definitions;
  const lines = byCode(month);
  const period = month.period;
  // The accounts' year to date reads every month up to this one.
  const untilMonths = dre.yearMonths.filter((item) => item.period <= period);
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
                const canOpen =
                  !dre.multi &&
                  isNatureLine(definition) &&
                  dre.natureLineCodes.has(definition.code);
                const open = canOpen && accounts.open.includes(definition.code);
                return (
                  <Fragment key={definition.code}>
                    <tr data-type={definition.line_type}>
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
                          accountsOpen={open}
                          onAccounts={
                            canOpen
                              ? () => accounts.toggle(definition.code)
                              : undefined
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
                          <Amount
                            value={line?.orcado}
                            definition={definition}
                          />
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
                    {open && (
                      <AccountRows
                        definition={definition}
                        definitions={definitions}
                        runIds={untilMonths.flatMap((item) =>
                          item.runId ? [item.runId] : []
                        )}
                        span={dre.budgetPresent ? 4 : 2}
                        cells={(account) => (
                          <>
                            <AccountCell
                              dre={dre}
                              definition={definition}
                              account={account}
                              period={period}
                            />
                            {dre.budgetPresent && (
                              <td>
                                <Amount value={null} definition={definition} />
                              </td>
                            )}
                            {dre.budgetPresent && (
                              <td>
                                <Amount value={null} definition={definition} />
                              </td>
                            )}
                            <td className="ton-statement-ytd">
                              <Amount
                                value={sumOf(
                                  account,
                                  untilMonths.map((item) => item.period)
                                )}
                                definition={definition}
                              />
                            </td>
                          </>
                        )}
                      />
                    )}
                  </Fragment>
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
  const calculated = new Set(dre.yearMonths.map((month) => month.period));
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

/** How many lines each view would show, for the counts on the tabs. */
function useFilterCounts(dre: DreWorkspace) {
  const months = dre.shownMonths;
  const last = byCode(months.at(-1));
  const previous = byCode(months.at(-2));
  let changed = 0;
  let excluded = 0;
  for (const definition of dre.definitions) {
    if (definition.excluded) excluded += 1;
    const change = changeOf(
      last.get(definition.code)?.realizado,
      previous.get(definition.code)?.realizado
    );
    if (change != null && Math.abs(change) >= CHANGE_THRESHOLD) changed += 1;
  }
  return { all: dre.definitions.length, changed, excluded };
}

export default function YearStatement({ dre }: { dre: DreWorkspace }) {
  const [filter, setFilter] = useState<StatementFilter>("all");
  const [query, setQuery] = useState("");
  const counts = useFilterCounts(dre);
  const canCompare = dre.shownMonths.length > 1;
  return (
    <Fragment>
      <ViewTabs
        label={T.viewsLabel}
        value={filter}
        onChange={setFilter}
        views={[
          { key: "all", label: T.viewAll, count: counts.all },
          ...(canCompare
            ? [
                {
                  key: "changed" as const,
                  label: T.viewChanged(CHANGE_THRESHOLD),
                  count: counts.changed,
                  tone: "info" as const,
                },
              ]
            : []),
          ...(counts.excluded
            ? [
                {
                  key: "excluded" as const,
                  label: T.viewExcluded,
                  count: counts.excluded,
                  tone: "neutral" as const,
                },
              ]
            : []),
        ]}
      />
      <div className="flex flex-wrap items-center gap-2">
        <label className="tn-search">
          <SvgSearch size={14} />
          <input
            type="search"
            aria-label={T.search}
            placeholder={T.search}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <div className="flex-1 min-w-0">
          <MonthControls dre={dre} />
        </div>
      </div>
      {dre.view === "columns" || filter !== "all" || query.trim() ? (
        <ColumnsView dre={dre} filter={filter} query={query} />
      ) : (
        <StackedView dre={dre} />
      )}
    </Fragment>
  );
}
