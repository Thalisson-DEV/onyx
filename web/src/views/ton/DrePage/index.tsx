"use client";

import { useEffect, useRef, useState } from "react";
import type { Route } from "next";
import { Button, InputSingleSelect, Text } from "@opal/components";
import {
  SvgAlertTriangle,
  SvgArrowRight,
  SvgCheckCircle,
  SvgChevronDown,
  SvgClipboard,
  SvgDownload,
  SvgEdit,
  SvgLock,
  SvgRefreshCw,
  SvgSparkle,
  SvgX,
} from "@opal/icons";
import { groupBlockers, totalBlockers } from "@/lib/ton/blockers";
import {
  COPY,
  formatCurrency,
  formatDay,
  formatDateTime,
  formatNumber,
  formatPercent,
  formatMonthName,
  formatPeriod,
} from "@/lib/ton/copy";
import { getBusinessLabel } from "@/lib/ton/labels";
import YearStatement from "@/views/ton/DrePage/YearStatement";
import StructureEditor from "@/views/ton/DrePage/StructureEditor";
import UnitPicker from "@/views/ton/DrePage/UnitPicker";
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
    <label className="flex flex-col gap-1 min-w-56">
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

function ModelPicker({ dre }: { dre: DreWorkspace }) {
  const [creating, setCreating] = useState(false);
  const [failed, setFailed] = useState(false);
  if (dre.structures.length > 1)
    return (
      <Select
        label={COPY.dre.model}
        value={dre.structureId ?? ""}
        onChange={dre.select.structure}
        options={dre.structures.map((item) => ({
          value: item.id,
          label: getBusinessLabel(item.label),
        }))}
      />
    );
  if (!dre.access.isAdmin || dre.structures.length === 0) return null;
  return (
    <span className="flex flex-col gap-1 self-end">
      <Button
        prominence="secondary"
        disabled={creating}
        onClick={() => {
          setCreating(true);
          setFailed(false);
          dre
            .createSimplified()
            .catch(() => setFailed(true))
            .finally(() => setCreating(false));
        }}
      >
        {creating ? COPY.dre.creatingSimplified : COPY.dre.createSimplified}
      </Button>
      {failed && (
        <Text font="secondary-body" color="status-error-05">
          {COPY.dre.createSimplifiedFailed}
        </Text>
      )}
    </span>
  );
}

function Toolbar({ dre }: { dre: DreWorkspace }) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <Select
        label={COPY.dre.closingUntil}
        value={dre.periodValue ?? ""}
        onChange={dre.select.period}
        options={dre.periods.map((item) => ({
          value: item.scope.period,
          label: formatPeriod(item.scope.period),
        }))}
      />
      <ModelPicker dre={dre} />
      <UnitPicker dre={dre} />
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
          </div>
        </details>
      )}
    </div>
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
      {dre.busy
        ? dre.progress
          ? COPY.dre.recalculatingMonth(dre.progress.done, dre.progress.total)
          : COPY.dre.recalculating
        : COPY.dre.recalculate}
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
  const account = dre.selectedAccount;
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
                dre.drillRun ? formatPeriod(dre.drillRun.scope.period) : null,
                scopeLabel(dre),
              ]
                .filter(Boolean)
                .join(" · ")}
            </Text>
            {account && (
              <span className="flex flex-wrap items-baseline gap-x-3">
                <Text font="secondary-body" color="text-04">
                  {COPY.dre.drawer.onlyAccount(
                    account.code,
                    account.label ?? ""
                  )}
                </Text>
                <button
                  type="button"
                  className="ton-focusable ton-link-button"
                  onClick={dre.select.allAccounts}
                >
                  {COPY.dre.drawer.allAccounts}
                </button>
              </span>
            )}
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
            value={formatCurrency(account ? account.amount : line.realizado)}
          />
          {dre.budgetPresent && !account && (
            <Metric
              label={COPY.dre.kpi.budget}
              value={formatCurrency(line.orcado)}
            />
          )}
          {dre.budgetPresent && !account && (
            <Metric
              label={COPY.dre.kpi.variance}
              value={formatCurrency(line.variance)}
            />
          )}
          {page && (
            <Metric
              label={COPY.dre.drawer.entries}
              value={formatNumber(page.total)}
            />
          )}
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-3">
          {/* No budget, or one NG account: only the realized entries. The
              segmented display beats a `hidden` class, so it is not rendered. */}
          {!dre.budgetPresent || account ? (
            <span />
          ) : (
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
          )}
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
                  <th scope="col">{columns.accountName}</th>
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
                        {fact.record_date ? formatDay(fact.record_date) : "—"}
                      </td>
                      <td>
                        {getBusinessLabel(fact.unit_name ?? fact.unit_code)}
                      </td>
                      <td>{fact.source_account_code ?? fact.account_code}</td>
                      <td className="ton-ledger-account-name">
                        {fact.source_account_label ?? fact.account_label}
                      </td>
                      <td>{fact.reference ?? "—"}</td>
                      <td className="ton-ledger-history">
                        <span>{fact.description || "—"}</span>
                        {fact.treatment_title && (
                          <span className="ton-ledger-muted block pt-1">
                            {COPY.dre.drawer.treatedDetail(
                              formatCurrency(
                                fact.original_amount ?? fact.amount
                              ),
                              fact.treatment_title,
                              fact.treatment_version,
                              fact.original_account_label
                            )}
                          </span>
                        )}
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
                        {fact.treatment_title && (
                          <span className="block pt-1">
                            <StatusPill tone="brand">
                              {COPY.dre.drawer.treated}
                            </StatusPill>
                          </span>
                        )}
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
  const [editing, setEditing] = useState(false);
  const [savedVersion, setSavedVersion] = useState<number | null>(null);
  const [excelState, setExcelState] = useState<"idle" | "loading" | "failed">(
    "idle"
  );
  const run = dre.officialRun;
  // A ready month without a result (a new unit, a new structure version):
  // calculate it right away instead of asking for a click.
  const autoScope = `${dre.unitId}|${dre.periodValue}|${dre.version?.id}`;
  const autoStarted = useRef<string | null>(null);
  useEffect(() => {
    if (run || !dre.access.canRun || dre.busy) return;
    if (autoStarted.current === autoScope) return;
    autoStarted.current = autoScope;
    void dre.recalculate();
  }, [run, autoScope, dre]);
  if (!run) {
    return (
      <TonCard className="flex flex-col gap-4 p-5">
        <EmptyState
          icon={SvgClipboard}
          tone="brand"
          title={
            dre.busy
              ? dre.progress
                ? COPY.dre.recalculatingMonth(
                    dre.progress.done,
                    dre.progress.total
                  )
                : COPY.dre.recalculating
              : COPY.dre.readyNoResult
          }
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
  const first = dre.yearMonths[0]?.period;
  const monthName = dre.periodValue ? formatMonthName(dre.periodValue) : "";
  return (
    <div className="flex flex-col gap-5">
      <TonCard className="flex flex-col gap-4 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-col gap-1 min-w-0">
            <span className="flex flex-wrap items-center gap-2">
              <StatusPill tone="success">{COPY.dre.official}</StatusPill>
              <Text font="secondary-body" color="text-03">
                {COPY.dre.calculatedAt(formatDateTime(run.finished_at))}
              </Text>
            </span>
            <Text as="h2" font="heading-h2" color="text-05">
              {COPY.dre.headline(
                scopeLabel(dre),
                first ?? run.scope.period,
                run.scope.period
              )}
            </Text>
          </div>
          <div className="flex flex-wrap gap-2">
            {dre.access.isAdmin && dre.version && dre.structureId && (
              <Button
                prominence="tertiary"
                icon={SvgEdit}
                onClick={() => setEditing(true)}
              >
                {COPY.dre.editStructure}
              </Button>
            )}
            <RecalculateButton dre={dre} />
            <Button
              icon={SvgDownload}
              disabled={excelState === "loading"}
              tooltip={COPY.dre.excelHint(scopeLabel(dre))}
              onClick={() => {
                setExcelState("loading");
                void dre
                  .exportExcel()
                  .catch(() => false)
                  .then((ok) => setExcelState(ok ? "idle" : "failed"));
              }}
            >
              {excelState === "loading"
                ? COPY.dre.excelLoading
                : COPY.dre.excel}
            </Button>
          </div>
        </div>
        {summary && definition && (
          <dl className="ton-summary-strip">
            <div>
              <dt>
                {COPY.dre.summaryMonth(
                  getBusinessLabel(definition.label),
                  monthName
                )}
              </dt>
              <dd>{valueOf(summary, definition, "realizado")}</dd>
            </div>
            <div>
              <dt>{COPY.dre.kpi.ytd}</dt>
              <dd>{valueOf(summary, definition, "realizado_ytd")}</dd>
            </div>
            {dre.budgetPresent && (
              <div>
                <dt>{COPY.dre.kpi.budget}</dt>
                <dd>{valueOf(summary, definition, "orcado_ytd")}</dd>
              </div>
            )}
            {dre.budgetPresent && (
              <div>
                <dt>{COPY.dre.kpi.variance}</dt>
                <dd>{valueOf(summary, definition, "variance_ytd")}</dd>
              </div>
            )}
          </dl>
        )}
        <CalculationFeedback dre={dre} />
        {savedVersion !== null && (
          <Text font="secondary-body" color="text-04">
            {COPY.dre.structureSaved(savedVersion)}
          </Text>
        )}
        {excelState === "failed" && (
          <ErrorState compact message={COPY.dre.excelFailed} />
        )}
      </TonCard>
      <TonCard className="flex flex-col gap-4 p-5">
        {(dre.year.isLoading || dre.statement.isLoading) && (
          <LoadingBlock label={COPY.common.loading} lines={8} />
        )}
        {dre.year.error && (
          <ErrorState
            compact
            message={COPY.dre.year.loadFailed}
            onRetry={() => dre.year.mutate()}
          />
        )}
        {dre.year.data && dre.statement.data && <YearStatement dre={dre} />}
      </TonCard>
      {dre.statement.data && (
        <Text as="p" font="secondary-body" color="text-03">
          {`${COPY.dre.version}: ${COPY.dre.versionStructure(dre.statement.data.version.number)} · ${formatDateTime(run.finished_at)}`}
        </Text>
      )}
      <DrillDrawer dre={dre} />
      {editing && dre.version && dre.structureId && (
        <StructureEditor
          structureId={dre.structureId}
          version={{
            ...dre.version,
            assignments: dre.version.assignments ?? [],
          }}
          onClose={() => setEditing(false)}
          onSaved={async (number) => {
            setEditing(false);
            setSavedVersion(number);
            await dre.structureSaved();
          }}
        />
      )}
    </div>
  );
}

/** The DRE of a set of units: each month is the sum of their results. */
function UnitsState({ dre }: { dre: DreWorkspace }) {
  const [excelState, setExcelState] = useState<"idle" | "loading" | "failed">(
    "idle"
  );
  const data = dre.unitsYear.data;
  const missing = new Set(
    data?.months.flatMap((month) => month.missing_unit_ids)
  );
  const absent = dre.unitSet.filter(
    (id) => !data?.months.some((month) => month.ready_unit_ids.includes(id))
  );
  // Units without a result for the closing month are calculated right away.
  const autoKey = `${dre.unitSet.join(",")}|${dre.periodValue}|${dre.version?.id}`;
  const started = useRef<string | null>(null);
  const lastMonth = data?.months.find(
    (month) => month.period === dre.periodValue
  );
  const toCalculate = data
    ? dre.unitSet.filter((id) => !lastMonth?.ready_unit_ids.includes(id))
    : [];
  useEffect(() => {
    if (!data || !toCalculate.length || !dre.access.canRun || dre.busy) return;
    if (started.current === autoKey) return;
    started.current = autoKey;
    void dre.calculateUnits(toCalculate);
  }, [data, toCalculate, autoKey, dre]);

  const names = dre.unitSet
    .map((id) => dre.units.find((unit) => unit.id === id))
    .map((unit) => getBusinessLabel(unit?.name ?? unit?.code ?? ""));
  const first = dre.yearMonths[0]?.period;
  const definition = dre.summaryDefinition;
  const summary = dre.summary;
  const summaryYtd = dre.yearMonths
    .at(-1)
    ?.lines.find((line) => line.code === definition?.code);
  return (
    <div className="flex flex-col gap-5">
      <TonCard className="flex flex-col gap-4 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-col gap-1 min-w-0">
            <span className="flex flex-wrap items-center gap-2">
              <StatusPill tone={missing.size ? "warning" : "success"}>
                {missing.size ? COPY.dre.units.partial : COPY.dre.units.summed}
              </StatusPill>
              <Text font="secondary-body" color="text-03">
                {names.join(" · ")}
              </Text>
            </span>
            <Text as="h2" font="heading-h2" color="text-05">
              {COPY.dre.headline(
                COPY.dre.units.many(dre.unitSet.length),
                first ?? dre.periodValue ?? "",
                dre.periodValue ?? ""
              )}
            </Text>
          </div>
          <div className="flex flex-wrap gap-2">
            {dre.access.canRun && (
              <Button
                prominence="secondary"
                icon={SvgRefreshCw}
                disabled={dre.busy}
                onClick={() => void dre.calculateUnits()}
              >
                {dre.busy
                  ? dre.progress
                    ? COPY.dre.units.calculating(
                        dre.progress.done,
                        dre.progress.total
                      )
                    : COPY.dre.recalculating
                  : COPY.dre.recalculate}
              </Button>
            )}
            <Button
              icon={SvgDownload}
              disabled={excelState === "loading" || !data}
              tooltip={COPY.dre.units.excelHint}
              onClick={() => {
                setExcelState("loading");
                void dre
                  .exportUnitsExcel()
                  .catch(() => false)
                  .then((ok) => setExcelState(ok ? "idle" : "failed"));
              }}
            >
              {excelState === "loading"
                ? COPY.dre.excelLoading
                : COPY.dre.excel}
            </Button>
          </div>
        </div>
        {summary && definition && (
          <dl className="ton-summary-strip">
            <div>
              <dt>
                {COPY.dre.summaryMonth(
                  getBusinessLabel(definition.label),
                  dre.periodValue ? formatMonthName(dre.periodValue) : ""
                )}
              </dt>
              <dd>{valueOf(summary, definition, "realizado")}</dd>
            </div>
            {summaryYtd && (
              <div>
                <dt>{COPY.dre.kpi.ytd}</dt>
                <dd>{valueOf(summaryYtd, definition, "realizado_ytd")}</dd>
              </div>
            )}
          </dl>
        )}
        {absent.length > 0 && !dre.busy && (
          <Text font="secondary-body" color="text-04">
            {COPY.dre.units.absent(
              absent
                .map((id) =>
                  getBusinessLabel(
                    dre.units.find((unit) => unit.id === id)?.name ?? id
                  )
                )
                .join(", ")
            )}
          </Text>
        )}
        {/* Units left out are named above; "blocked" has no list here. */}
        {dre.calculation !== "blocked" && <CalculationFeedback dre={dre} />}
        {excelState === "failed" && (
          <ErrorState compact message={COPY.dre.excelFailed} />
        )}
      </TonCard>
      <TonCard className="flex flex-col gap-4 p-5">
        {dre.unitsYear.isLoading && (
          <LoadingBlock label={COPY.common.loading} lines={8} />
        )}
        {dre.unitsYear.error && (
          <ErrorState
            compact
            message={COPY.dre.year.loadFailed}
            onRetry={() => dre.unitsYear.mutate()}
          />
        )}
        {data && data.months.length > 0 && <YearStatement dre={dre} />}
        {data && (
          <Text font="secondary-body" color="text-03">
            {COPY.dre.units.drillHint}
          </Text>
        )}
      </TonCard>
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
      </div>
      {!dre.period ? (
        <TonCard>
          <EmptyState icon={SvgClipboard} title={COPY.dre.noPeriods} />
        </TonCard>
      ) : dre.multi ? (
        <UnitsState dre={dre} />
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
