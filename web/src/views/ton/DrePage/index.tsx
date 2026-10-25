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
import LineDrawer, { scopeLabel } from "@/views/ton/DrePage/LineDrawer";
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
      <span className="tn-field-label">{label}</span>
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
      <LineDrawer dre={dre} />
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
