"use client";

import { useEffect, useRef, useState } from "react";
import type { Route } from "next";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Button, InputSingleSelect, Text } from "@opal/components";
import {
  SvgAlertTriangle,
  SvgArrowRight,
  SvgCheckCircle,
  SvgChevronDown,
  SvgChevronRight,
  SvgClipboard,
  SvgDownload,
  SvgLock,
  SvgRefreshCw,
  SvgSparkle,
  SvgX,
} from "@opal/icons";
import { cn } from "@opal/utils";
import { groupBlockers, totalBlockers } from "@/lib/ton/blockers";
import {
  COPY,
  formatCurrency,
  formatDate,
  formatDateTime,
  formatNumber,
  formatPercent,
  formatPeriod,
  formatShortMonth,
} from "@/lib/ton/copy";
import { getBusinessLabel } from "@/lib/ton/labels";
import type { DreDefinition, DreLine } from "@/views/admin/DrePage/types";
import ClosingFrame from "@/views/ton/components/ClosingFrame";
import { askHref } from "@/views/ton/shell/TonCommandMenu";
import {
  EmptyState,
  ErrorState,
  IconTile,
  LoadingBlock,
  Metric,
  StatusPill,
  TonCard,
} from "@/views/ton/components/ui";
import {
  CONSOLIDATED,
  CONTRIBUTOR_PAGE,
  useDreWorkspace,
  type DreWorkspace,
} from "@/views/ton/DrePage/useDreWorkspace";

/** Blocker codes the pending queue can open directly. */
const QUEUE_BLOCKERS = new Set([
  "UNMAPPED_UNIT",
  "UNMAPPED_ACCOUNT",
  "BUDGET_PERIOD_UNRESOLVED",
  "BUDGET_UNMAPPED_ACCOUNT",
  "BUDGET_UNMAPPED_UNIT",
  "SOURCE_RECONCILIATION_UNRESOLVED",
  "SOURCE_RECONCILIATION_AMBIGUOUS",
  "ACTUAL_AMOUNT_SEMANTICS_UNRESOLVED",
  "DRE_ACCOUNT_UNMAPPED",
  "DRE_MAPPING_PENDING_APPROVAL",
]);

function pendingLink(
  dre: DreWorkspace,
  codes: string[] = [],
  category?: string
): Route {
  const query = new URLSearchParams();
  if (dre.periodValue) query.set("period", dre.periodValue);
  if (dre.normalizationId) query.set("normalization", dre.normalizationId);
  if (dre.unitId && dre.unitId !== CONSOLIDATED) query.set("unit", dre.unitId);
  const blocker = codes.find((code) => QUEUE_BLOCKERS.has(code));
  if (blocker) query.set("blocker", blocker);
  else if (category) query.set("categoria", category);
  return `/ton/pendencias?${query.toString()}` as Route;
}

interface SelectProps {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}

function Select({ label, value, options, onChange }: SelectProps) {
  return (
    <label className="flex flex-col gap-1 min-w-44">
      <span className="ton-eyebrow">{label}</span>
      <InputSingleSelect value={value} onValueChange={onChange}>
        <InputSingleSelect.Trigger placeholder={label} aria-label={label} />
        <InputSingleSelect.Content>
          {options.map((option) => (
            <InputSingleSelect.Item key={option.value} value={option.value}>
              {option.label}
            </InputSingleSelect.Item>
          ))}
        </InputSingleSelect.Content>
      </InputSingleSelect>
    </label>
  );
}

function Toolbar({ dre }: { dre: DreWorkspace }) {
  const scopeOptions = [
    ...(dre.access.isAdmin
      ? [{ value: CONSOLIDATED, label: COPY.dre.consolidated }]
      : []),
    ...dre.units.map((unit) => ({
      value: unit.id,
      label: unit.name
        ? `${getBusinessLabel(unit.code)} · ${getBusinessLabel(unit.name)}`
        : getBusinessLabel(unit.code),
    })),
  ];
  return (
    <div className="flex flex-wrap items-end gap-3">
      <Select
        label={COPY.dre.period}
        value={dre.periodValue ?? ""}
        onChange={dre.select.period}
        options={dre.periods.map((item) => ({
          value: item.scope.period,
          label: formatPeriod(item.scope.period),
        }))}
      />
      <Select
        label={COPY.dre.scope}
        value={dre.unitId ?? ""}
        onChange={dre.select.unit}
        options={scopeOptions}
      />
      {dre.access.isAdmin && (
        <details className="group self-end">
          <summary className="ton-focusable flex items-center gap-1 cursor-pointer list-none rounded-08 px-1 py-2 text-text-03 hover:text-text-05">
            <Text font="secondary-action" color="inherit">
              {COPY.dre.advanced}
            </Text>
            <SvgChevronDown
              size={14}
              className="transition-transform group-open:rotate-180"
            />
          </summary>
          <div className="flex flex-wrap gap-3 pt-2">
            <Select
              label={COPY.dre.normalization}
              value={dre.normalizationId ?? ""}
              onChange={dre.select.normalization}
              options={dre.normalizations.map((run) => ({
                value: run.id,
                label: formatDateTime(run.started_at),
              }))}
            />
            <Select
              label={COPY.dre.structure}
              value={dre.structureId ?? ""}
              onChange={dre.select.structure}
              options={dre.structures.map((item) => ({
                value: item.id,
                label: getBusinessLabel(item.label),
              }))}
            />
          </div>
        </details>
      )}
    </div>
  );
}

/** Readiness of every month in the overview: the closing calendar at a glance. */
function MonthStrip({ dre }: { dre: DreWorkspace }) {
  if (dre.periods.length < 2) return null;
  return (
    <nav aria-label={COPY.dre.months} className="flex flex-col gap-2">
      <span className="ton-eyebrow">{COPY.dre.months}</span>
      <ol className="flex flex-wrap gap-1.5">
        {dre.periods.map((item) => {
          const selected = item.scope.period === dre.periodValue;
          const ready = item.status === "READY";
          return (
            <li key={item.scope.period}>
              <button
                type="button"
                onClick={() => dre.select.period(item.scope.period)}
                aria-current={selected ? "true" : undefined}
                title={`${formatPeriod(item.scope.period)} · ${ready ? COPY.dre.monthReady : COPY.dre.monthBlocked}`}
                className={cn(
                  "ton-month ton-focusable flex items-center gap-1.5 px-2.5 py-1 rounded-full",
                  selected && "ton-month-selected"
                )}
              >
                <span
                  aria-hidden
                  className="ton-dot"
                  data-tone={ready ? "success" : "warning"}
                />
                <Text font="secondary-action" color="inherit">
                  {formatShortMonth(item.scope.period)}
                </Text>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

function RecalculateButton({ dre }: { dre: DreWorkspace }) {
  if (!dre.access.canRun) return null;
  return (
    <Button
      prominence="secondary"
      icon={SvgRefreshCw}
      disabled={dre.busy}
      onClick={() => void dre.recalculate()}
    >
      {dre.busy ? COPY.dre.recalculating : COPY.dre.recalculate}
    </Button>
  );
}

function CalculationFeedback({ dre }: { dre: DreWorkspace }) {
  if (dre.calculation === "idle") return null;
  const message =
    dre.calculation === "ready"
      ? COPY.dre.recalcReady
      : dre.calculation === "blocked"
        ? COPY.dre.recalcBlocked
        : COPY.dre.recalcFailed;
  return (
    <div role="status" className="flex items-center gap-2">
      {dre.calculation === "ready" ? (
        <SvgCheckCircle size={16} className="ton-brand-text" />
      ) : (
        <SvgAlertTriangle
          size={16}
          className={
            dre.calculation === "failed"
              ? "text-status-error-05"
              : "text-status-warning-05"
          }
        />
      )}
      <Text font="secondary-body" color="text-04">
        {message}
      </Text>
    </div>
  );
}

function BlockedState({ dre }: { dre: DreWorkspace }) {
  const blockers = dre.period?.blockers ?? {};
  const groups = groupBlockers(blockers);
  const total = totalBlockers(blockers);
  const period = dre.periodValue ? formatPeriod(dre.periodValue) : "";
  return (
    <TonCard className="flex flex-col gap-5 p-5 sm:p-6">
      <div className="flex items-start gap-4">
        <IconTile icon={SvgAlertTriangle} tone="warning" size="lg" />
        <div className="flex flex-col gap-1 min-w-0">
          <Text as="h2" font="heading-h2" color="text-05">
            {COPY.dre.blockedTitle(period.toLowerCase())}
          </Text>
          <span className="text-status-warning-05">
            <Text font="main-ui-action" color="inherit">
              {COPY.dre.blockedCount(total)}
            </Text>
          </span>
          <Text as="p" font="secondary-body" color="text-03">
            {COPY.dre.blockedBody}
          </Text>
        </div>
      </div>
      <ul className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
        {groups.map((group) => {
          const category = COPY.blockers.categories[group.category];
          return (
            <li
              key={group.category}
              className="flex flex-col gap-2 rounded-12 border border-01 bg-background-neutral-01 p-4"
            >
              <span className="ton-eyebrow">{category.short}</span>
              <span className="ton-metric">
                <Text font="heading-h2" color="inherit">
                  {formatNumber(group.count)}
                </Text>
              </span>
              <Text as="p" font="secondary-body" color="text-03">
                {category.description}
              </Text>
              <ul className="flex flex-col gap-0.5">
                {group.labels.map((code) => (
                  <li key={code} className="flex justify-between gap-2">
                    <Text font="secondary-body" color="text-04">
                      {getBusinessLabel(code)}
                    </Text>
                    <Text font="secondary-action" color="text-05">
                      {formatNumber(blockers[code] ?? 0)}
                    </Text>
                  </li>
                ))}
              </ul>
              <span className="mt-auto pt-1">
                <Button
                  size="sm"
                  prominence="secondary"
                  rightIcon={SvgArrowRight}
                  href={pendingLink(dre, group.labels, group.category)}
                >
                  {COPY.dre.resolve}
                </Button>
              </span>
            </li>
          );
        })}
      </ul>
      <CalculationFeedback dre={dre} />
      <div className="flex flex-wrap gap-2">
        <Button href={pendingLink(dre)} rightIcon={SvgArrowRight}>
          {COPY.dre.resolveAll}
        </Button>
        <RecalculateButton dre={dre} />
        <Button
          prominence="tertiary"
          icon={SvgSparkle}
          href={askHref(COPY.dre.askPrompt(period.toLowerCase()))}
        >
          {COPY.dre.ask}
        </Button>
      </div>
    </TonCard>
  );
}

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

function isHidden(
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

function valueOf(
  line: DreLine,
  definition: DreDefinition,
  field: keyof Pick<
    DreLine,
    | "realizado"
    | "orcado"
    | "variance"
    | "variance_percent"
    | "realizado_ytd"
    | "orcado_ytd"
    | "variance_ytd"
  >
) {
  return definition.line_type === "PERCENTAGE" || field === "variance_percent"
    ? formatPercent(line[field])
    : formatCurrency(line[field]);
}

function StatementTable({ dre }: { dre: DreWorkspace }) {
  const [collapsed, setCollapsed] = useState<string[]>([]);
  const lines = dre.statement.data?.lines ?? [];
  const definitions = dre.definitions;
  return (
    <div className="ton-card overflow-x-auto">
      <table className="ton-statement w-full min-w-[960px] border-collapse">
        <thead>
          <tr>
            <th rowSpan={2} scope="col" className="text-start">
              {COPY.dre.table.line}
            </th>
            <th colSpan={4} scope="colgroup" className="ton-statement-group">
              {COPY.dre.table.month}
            </th>
            <th colSpan={3} scope="colgroup" className="ton-statement-group">
              {COPY.dre.table.ytd}
            </th>
          </tr>
          <tr>
            <th scope="col">{COPY.dre.table.actual}</th>
            <th scope="col">{COPY.dre.table.budget}</th>
            <th scope="col">{COPY.dre.table.variance}</th>
            <th scope="col">{COPY.dre.table.variancePercent}</th>
            <th scope="col">{COPY.dre.table.actual}</th>
            <th scope="col">{COPY.dre.table.budget}</th>
            <th scope="col">{COPY.dre.table.variance}</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line) => {
            const definition = definitions.find(
              (item) => item.code === line.code
            );
            if (!definition || isHidden(definition, definitions, collapsed))
              return null;
            const label = getBusinessLabel(line.label);
            const hasChildren = definitions.some(
              (item) => item.parent_code === line.code
            );
            const isCollapsed = collapsed.includes(line.code);
            const drillable = definition.line_type === "SOURCE_SUM";
            return (
              <tr
                key={line.code}
                data-type={definition.line_type}
                aria-selected={dre.selectedLine?.code === line.code}
              >
                <th scope="row" className="text-start">
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
                        onClick={() =>
                          setCollapsed((old) =>
                            isCollapsed
                              ? old.filter((code) => code !== line.code)
                              : [...old, line.code]
                          )
                        }
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
                    {drillable ? (
                      <button
                        type="button"
                        className="ton-focusable ton-statement-drill text-start rounded-04"
                        aria-label={COPY.dre.table.drill(label)}
                        onClick={() => dre.select.line(line.code)}
                      >
                        {label}
                      </button>
                    ) : (
                      <span>{label}</span>
                    )}
                  </span>
                </th>
                <td>{valueOf(line, definition, "realizado")}</td>
                <td>{valueOf(line, definition, "orcado")}</td>
                <td>{valueOf(line, definition, "variance")}</td>
                <td>{valueOf(line, definition, "variance_percent")}</td>
                <td className="ton-statement-ytd">
                  {valueOf(line, definition, "realizado_ytd")}
                </td>
                <td>{valueOf(line, definition, "orcado_ytd")}</td>
                <td>{valueOf(line, definition, "variance_ytd")}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Trend({ dre }: { dre: DreWorkspace }) {
  const data = (dre.series.data ?? []).map((point) => ({
    period: point.period,
    month: formatShortMonth(point.period),
    realizado: Number(point.realizado),
    orcado: Number(point.orcado),
  }));
  return (
    <TonCard className="flex flex-col gap-3 p-5">
      <Text as="h3" font="heading-h3" color="text-05">
        {`${COPY.dre.trend} · ${getBusinessLabel(dre.summary?.label ?? "")}`}
      </Text>
      {dre.series.isLoading && <LoadingBlock label={COPY.common.loading} />}
      {dre.series.error && <ErrorState compact />}
      {!dre.series.isLoading && !dre.series.error && data.length < 2 && (
        <Text as="p" font="secondary-body" color="text-03">
          {COPY.dre.trendEmpty}
        </Text>
      )}
      {data.length >= 2 && (
        <div className="h-56 w-full" role="img" aria-label={COPY.dre.trend}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="month" tickLine={false} axisLine={false} />
              <YAxis
                tickLine={false}
                axisLine={false}
                tickFormatter={(value: number) =>
                  value.toLocaleString("pt-BR", { notation: "compact" })
                }
              />
              <Tooltip
                formatter={(value) => formatCurrency(String(value))}
                labelFormatter={(_, payload) =>
                  payload?.[0]?.payload?.period
                    ? formatPeriod(payload[0].payload.period)
                    : ""
                }
              />
              <Bar
                name={COPY.dre.kpi.actual}
                dataKey="realizado"
                fill="var(--ton-brand)"
                radius={[4, 4, 0, 0]}
              />
              <Bar
                name={COPY.dre.kpi.budget}
                dataKey="orcado"
                fill="var(--ton-gold)"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </TonCard>
  );
}

function scopeLabel(dre: DreWorkspace): string {
  if (!dre.unitId || dre.unitId === CONSOLIDATED) return COPY.dre.consolidated;
  const unit = dre.units.find((item) => item.id === dre.unitId);
  if (!unit) return "";
  return getBusinessLabel(unit.name ?? unit.code);
}

function DrillDrawer({ dre }: { dre: DreWorkspace }) {
  const line = dre.selectedLine;
  const closeRef = useRef<HTMLButtonElement>(null);
  const open = !!line && dre.selectedDefinition?.line_type === "SOURCE_SUM";

  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") dre.select.line(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, dre.select]);

  if (!open || !line) return null;
  const page = dre.contributors.data;
  const first = page?.rows[0];
  const columns = COPY.dre.drawer.columns;
  return (
    <>
      <div
        aria-hidden
        className="ton-scrim fixed inset-0 z-40"
        onClick={() => dre.select.line(null)}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="ton-drill-title"
        className="ton-drawer fixed inset-y-0 end-0 z-50 flex flex-col w-full lg:w-[min(1040px,calc(100vw-6rem))]"
      >
        <header className="flex items-start justify-between gap-4 px-6 pt-5 pb-4 border-b border-01">
          <div className="flex flex-col gap-1 min-w-0">
            <span className="ton-eyebrow">{COPY.dre.drawer.title}</span>
            <Text
              as="h2"
              id="ton-drill-title"
              font="heading-h2"
              color="text-05"
            >
              {getBusinessLabel(line.label)}
            </Text>
            <Text font="secondary-body" color="text-03">
              {[
                dre.periodValue ? formatPeriod(dre.periodValue) : null,
                scopeLabel(dre),
              ]
                .filter(Boolean)
                .join(" · ")}
            </Text>
          </div>
          <Button
            ref={closeRef}
            icon={SvgX}
            prominence="tertiary"
            aria-label={COPY.dre.drawer.close}
            onClick={() => dre.select.line(null)}
          />
        </header>
        <div className="flex flex-wrap items-end gap-x-10 gap-y-3 px-6 py-4 border-b border-01">
          <Metric
            label={COPY.dre.kpi.actual}
            value={formatCurrency(line.realizado)}
          />
          <Metric
            label={COPY.dre.kpi.budget}
            value={formatCurrency(line.orcado)}
          />
          <Metric
            label={COPY.dre.kpi.variance}
            value={formatCurrency(line.variance)}
          />
          {page && (
            <Metric
              label={COPY.dre.drawer.entries}
              value={formatNumber(page.total)}
            />
          )}
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-3">
          <div className="ton-segmented" role="group">
            {(["ACTUAL", "BUDGET"] as const).map((type) => (
              <button
                key={type}
                type="button"
                aria-pressed={dre.factType === type}
                className="ton-focusable ton-segment"
                onClick={() => dre.select.factType(type)}
              >
                {type === "ACTUAL"
                  ? COPY.dre.drawer.actual
                  : COPY.dre.drawer.budget}
              </button>
            ))}
          </div>
          {first && (
            <Text font="secondary-body" color="text-03">
              {COPY.dre.drawer.sourceOnce(
                first.source_name,
                first.original_filename
              )}
            </Text>
          )}
        </div>
        <div className="flex-1 overflow-auto px-6 pb-4">
          {dre.contributors.isLoading && (
            <LoadingBlock label={COPY.common.loading} lines={6} />
          )}
          {dre.contributors.error && (
            <ErrorState compact onRetry={() => dre.contributors.mutate()} />
          )}
          {page && page.rows.length === 0 && (
            <Text as="p" font="secondary-body" color="text-03">
              {COPY.dre.drawer.empty}
            </Text>
          )}
          {page && page.rows.length > 0 && (
            <table className="ton-ledger w-full border-collapse">
              <thead>
                <tr>
                  <th scope="col">{columns.date}</th>
                  <th scope="col">{columns.unit}</th>
                  <th scope="col">{columns.account}</th>
                  <th scope="col">{columns.document}</th>
                  <th scope="col" className="w-full">
                    {columns.history}
                  </th>
                  <th scope="col" className="ton-ledger-end">
                    {columns.amount}
                  </th>
                  <th scope="col">{columns.origin}</th>
                </tr>
              </thead>
              <tbody>
                {page.rows.map((fact) => {
                  const flagged =
                    !!fact.review_status && fact.review_status !== "ACCEPTED";
                  return (
                    <tr key={fact.id}>
                      <td>
                        {fact.record_date ? formatDate(fact.record_date) : "—"}
                      </td>
                      <td>
                        {getBusinessLabel(fact.unit_name ?? fact.unit_code)}
                      </td>
                      <td title={fact.source_account_label ?? undefined}>
                        {fact.source_account_code ?? fact.account_code}
                      </td>
                      <td>{fact.reference ?? "—"}</td>
                      <td className="ton-ledger-history">
                        <span>{fact.description || "—"}</span>
                        {flagged && (
                          <span className="block pt-1">
                            <StatusPill tone="warning">
                              {`${COPY.dre.drawer.review}: ${getBusinessLabel(fact.review_status ?? "")}`}
                            </StatusPill>
                          </span>
                        )}
                      </td>
                      <td className="ton-ledger-end ton-ledger-amount">
                        {formatCurrency(fact.amount)}
                      </td>
                      <td className="ton-ledger-muted">
                        {COPY.dre.drawer.row(
                          fact.sheet_name,
                          fact.source_row_number
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
        {page && (
          <footer className="flex flex-wrap items-center justify-between gap-2 px-6 py-3 border-t border-01">
            <Text font="secondary-body" color="text-03">
              {`${COPY.dre.drawer.sorted} · ${COPY.dre.drawer.page(
                page.total === 0 ? 0 : dre.offset + 1,
                Math.min(dre.offset + CONTRIBUTOR_PAGE, page.total),
                page.total
              )}`}
            </Text>
            {page.total > CONTRIBUTOR_PAGE && (
              <div className="flex gap-1">
                <Button
                  size="sm"
                  prominence="secondary"
                  disabled={dre.offset === 0}
                  onClick={() =>
                    dre.select.offset(
                      Math.max(0, dre.offset - CONTRIBUTOR_PAGE)
                    )
                  }
                >
                  {COPY.dre.drawer.previous}
                </Button>
                <Button
                  size="sm"
                  prominence="secondary"
                  disabled={dre.offset + CONTRIBUTOR_PAGE >= page.total}
                  onClick={() =>
                    dre.select.offset(dre.offset + CONTRIBUTOR_PAGE)
                  }
                >
                  {COPY.dre.drawer.next}
                </Button>
              </div>
            )}
          </footer>
        )}
      </aside>
    </>
  );
}

function ReadyState({ dre }: { dre: DreWorkspace }) {
  const [exportFailed, setExportFailed] = useState(false);
  const run = dre.officialRun;
  if (!run) {
    return (
      <TonCard className="flex flex-col gap-4 p-5">
        <EmptyState
          icon={SvgClipboard}
          tone="brand"
          title={COPY.dre.readyNoResult}
        />
        <CalculationFeedback dre={dre} />
        <div className="flex justify-center">
          <RecalculateButton dre={dre} />
        </div>
      </TonCard>
    );
  }
  const summary = dre.summary;
  const definition = dre.summaryDefinition;
  return (
    <div className="flex flex-col gap-5">
      <TonCard className="flex flex-col gap-5 p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-col gap-1">
            <span className="flex items-center gap-2">
              <StatusPill tone="success">{COPY.dre.official}</StatusPill>
              <Text font="secondary-body" color="text-03">
                {COPY.dre.calculatedAt(formatDateTime(run.finished_at))}
              </Text>
            </span>
            <Text as="h2" font="heading-h2" color="text-05">
              {getBusinessLabel(summary?.label ?? COPY.dre.title)}
            </Text>
          </div>
          <div className="flex flex-wrap gap-2">
            <RecalculateButton dre={dre} />
            <Button
              prominence="secondary"
              icon={SvgDownload}
              onClick={() =>
                void dre.exportCsv().then((ok) => setExportFailed(!ok))
              }
            >
              {COPY.dre.export}
            </Button>
          </div>
        </div>
        {summary && definition && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Metric
              label={COPY.dre.kpi.actual}
              value={valueOf(summary, definition, "realizado")}
              detail={`${COPY.dre.kpi.ytd}: ${valueOf(summary, definition, "realizado_ytd")}`}
            />
            <Metric
              label={COPY.dre.kpi.budget}
              value={valueOf(summary, definition, "orcado")}
              detail={`${COPY.dre.kpi.ytd}: ${valueOf(summary, definition, "orcado_ytd")}`}
            />
            <Metric
              label={COPY.dre.kpi.variance}
              value={valueOf(summary, definition, "variance")}
              detail={`${COPY.dre.kpi.ytd}: ${valueOf(summary, definition, "variance_ytd")}`}
            />
            <Metric
              label={COPY.dre.kpi.variancePercent}
              value={formatPercent(summary.variance_percent)}
              detail={`${COPY.dre.kpi.ytd}: ${formatPercent(summary.variance_percent_ytd)}`}
            />
          </div>
        )}
        <CalculationFeedback dre={dre} />
        {exportFailed && <ErrorState compact message={COPY.dre.exportFailed} />}
      </TonCard>
      {dre.statement.isLoading && (
        <TonCard className="p-5">
          <LoadingBlock label={COPY.common.loading} lines={6} />
        </TonCard>
      )}
      {dre.statement.error && (
        <ErrorState onRetry={() => dre.statement.mutate()} />
      )}
      {dre.statement.data && (
        <>
          <StatementTable dre={dre} />
          <Trend dre={dre} />
          <Text as="p" font="secondary-body" color="text-03">
            {`${COPY.dre.version}: ${COPY.dre.versionStructure(dre.statement.data.version.number)} · ${formatDateTime(run.finished_at)}`}
          </Text>
        </>
      )}
      <DrillDrawer dre={dre} />
    </div>
  );
}

export function DreWorkspaceView() {
  const dre = useDreWorkspace();
  if (!dre.access.canRead)
    return <EmptyState icon={SvgLock} title={COPY.dre.noAccess} />;
  if (dre.loading)
    return (
      <TonCard className="p-5">
        <LoadingBlock label={COPY.common.loading} lines={5} />
      </TonCard>
    );
  if (dre.error) return <ErrorState onRetry={dre.retry} />;
  if (!dre.configured)
    return (
      <TonCard>
        <EmptyState icon={SvgClipboard} title={COPY.dre.noConfiguration} />
      </TonCard>
    );
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-4">
        <Toolbar dre={dre} />
        <MonthStrip dre={dre} />
      </div>
      {!dre.period ? (
        <TonCard>
          <EmptyState icon={SvgClipboard} title={COPY.dre.noPeriods} />
        </TonCard>
      ) : dre.ready ? (
        <ReadyState dre={dre} />
      ) : (
        <BlockedState dre={dre} />
      )}
    </div>
  );
}

export default function TonDrePage() {
  return (
    <ClosingFrame
      active="dre"
      title={COPY.dre.title}
      description={COPY.dre.description}
      wide
    >
      <DreWorkspaceView />
    </ClosingFrame>
  );
}
