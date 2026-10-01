"use client";

import { useState } from "react";
import { useFormatter, useTranslations } from "next-intl";
import useSWR from "swr";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Button, InputSingleSelect, Text } from "@opal/components";
import { SvgBarChart, SvgSimpleLoader } from "@opal/icons";
import { SettingsLayouts } from "@opal/layouts";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";
import { useUser } from "@/providers/UserProvider";
import { BLOCKER_GROUPS, getBusinessLabel } from "@/lib/ton/labels";
import type {
  ContributorPage,
  DreDefinition,
  DreLine,
  DreRun,
  DreStatement,
  DreVersion,
  Normalization,
  PeriodPoint,
  ReadinessOverview,
  Structure,
  Unit,
} from "@/views/admin/DrePage/types";

const PAGE_SIZE = 25;
const BLOCKER_KEYS = [
  "UNMAPPED_UNIT",
  "UNMAPPED_ACCOUNT",
  "ACTUAL_AMOUNT_SEMANTICS_UNRESOLVED",
  "DRE_ACCOUNT_UNMAPPED",
  "DRE_MAPPING_PENDING_APPROVAL",
  "BUDGET_PERIOD_UNRESOLVED",
  "BUDGET_UNMAPPED_ACCOUNT",
  "BUDGET_UNMAPPED_UNIT",
  "SOURCE_RECONCILIATION_UNRESOLVED",
  "SOURCE_RECONCILIATION_AMBIGUOUS",
  "REVIEW_UNRESOLVED",
  "EXCLUDED_SOURCE_ROWS",
  "BILLING_COMPETENCE_UNRESOLVED",
  "UNSUPPORTED_DERIVATION",
  "IR_RETENTION_UNRESOLVED",
  "ACTUAL_UNIT_SCOPE_UNRESOLVED",
  "FORMULA_DENOMINATOR_ZERO",
  "DRE_STRUCTURE_INVALID",
] as const;
const COLUMN_KEYS = [
  "line",
  "actual",
  "budget",
  "variance",
  "variancePercent",
  "actualYtd",
  "budgetYtd",
  "varianceYtd",
] as const;

function isBlockerKey(value: string): value is (typeof BLOCKER_KEYS)[number] {
  return BLOCKER_KEYS.some((key) => key === value);
}

function DrePage() {
  const t = useTranslations("dre");
  const nav = useTranslations("sidebar");
  const runtime = useTranslations("tonRuntime");
  const format = useFormatter();
  const { user } = useUser();
  const permissions = user?.effective_permissions ?? [];
  const canRead = hasPermission(permissions, Permission.READ_TON_SOURCES);
  const canRun = hasPermission(permissions, Permission.IMPORT_TON_SOURCES);
  const isAdmin = hasPermission(
    permissions,
    Permission.FULL_ADMIN_PANEL_ACCESS
  );
  const [normalizationChoice, setNormalizationChoice] = useState("");
  const [structureChoice, setStructureChoice] = useState("");
  const [unitChoice, setUnitChoice] = useState("");
  const [periodChoice, setPeriodChoice] = useState("");
  const [revisionChoice, setRevisionChoice] = useState("");
  const [lineChoice, setLineChoice] = useState<string | null>(null);
  const [factType, setFactType] = useState<"ACTUAL" | "BUDGET">("ACTUAL");
  const [offset, setOffset] = useState(0);
  const [collapsed, setCollapsed] = useState<string[]>([]);
  const [showVersion, setShowVersion] = useState(false);
  const [busy, setBusy] = useState(false);
  const [calculationError, setCalculationError] = useState(false);
  const [calculationBlockers, setCalculationBlockers] = useState<Record<
    string,
    number
  > | null>(null);

  const normalizations = useSWR<Normalization[]>(
    canRead ? "/api/ton/financial-domain/normalizations?limit=20" : null,
    errorHandlingFetcher
  );
  const structures = useSWR<Structure[]>(
    canRead ? "/api/ton/dre/structures?limit=100" : null,
    errorHandlingFetcher
  );
  const units = useSWR<Unit[]>(
    canRead ? "/api/ton/financial-domain/units?limit=100" : null,
    errorHandlingFetcher
  );
  const normalizationId = normalizationChoice || normalizations.data?.[0]?.id;
  const structureId = structureChoice || structures.data?.[0]?.id;
  const unitId = unitChoice || (isAdmin ? "consolidated" : units.data?.[0]?.id);
  const version = useSWR<DreVersion>(
    structureId
      ? `/api/ton/dre/structures/${structureId}/latest-version`
      : null,
    errorHandlingFetcher
  );
  const unitQuery =
    unitId && unitId !== "consolidated" ? `&unit_id=${unitId}` : "";
  const overview = useSWR<ReadinessOverview>(
    normalizationId && version.data && unitId
      ? `/api/ton/financial-domain/normalizations/${normalizationId}/readiness?structure_version_id=${version.data.id}${unitQuery}`
      : null,
    errorHandlingFetcher
  );
  const periods = overview.data?.periods ?? [];
  const period =
    periods.find((item) => item.scope.period === periodChoice) ??
    periods.at(-1);
  const periodValue = period?.scope.period;
  const revisions = useSWR<DreRun[]>(
    periodValue && unitId
      ? `/api/ton/dre/calculations?period=${periodValue}${unitQuery}&limit=100`
      : null,
    errorHandlingFetcher
  );
  const currentRun = revisions.data?.find(
    (run) =>
      run.status === "READY" &&
      run.scope.normalization_run_id === normalizationId &&
      run.scope.structure_version_id === version.data?.id
  );
  const selectedRun = revisionChoice
    ? revisions.data?.find((run) => run.id === revisionChoice)
    : currentRun;
  const historical = Boolean(selectedRun && selectedRun.id !== currentRun?.id);
  const ready = period?.status === "READY";
  const statement = useSWR<DreStatement>(
    ready && selectedRun?.status === "READY"
      ? `/api/ton/dre/calculations/${selectedRun.id}/statement`
      : null,
    errorHandlingFetcher
  );
  const definitions = statement.data?.version.lines ?? [];
  const summaryDefinition =
    [...definitions].reverse().find((line) => line.line_type === "RESULT") ??
    [...definitions].reverse().find((line) => line.line_type === "SUBTOTAL") ??
    [...definitions].reverse().find((line) => line.line_type === "SOURCE_SUM");
  const summary = statement.data?.lines.find(
    (line) => line.code === summaryDefinition?.code
  );
  const series = useSWR<PeriodPoint[]>(
    statement.data && summary && summaryDefinition?.line_type !== "PERCENTAGE"
      ? `/api/ton/dre/calculations/series?normalization_run_id=${statement.data.run.scope.normalization_run_id}&structure_version_id=${statement.data.run.scope.structure_version_id}&year=${periodValue?.slice(0, 4)}&line_code=${encodeURIComponent(summary.code)}${unitQuery}`
      : null,
    errorHandlingFetcher
  );
  const selectedLine = statement.data?.lines.find(
    (line) => line.code === lineChoice
  );
  const selectedDefinition = definitions.find(
    (line) => line.code === lineChoice
  );
  const contributors = useSWR<ContributorPage>(
    selectedRun &&
      selectedDefinition?.line_type === "SOURCE_SUM" &&
      selectedLine
      ? `/api/ton/dre/calculations/${selectedRun.id}/lines/${encodeURIComponent(selectedLine.code)}/contributors?fact_type=${factType}&limit=${PAGE_SIZE}&offset=${offset}`
      : null,
    errorHandlingFetcher
  );
  const loading =
    normalizations.isLoading ||
    structures.isLoading ||
    units.isLoading ||
    version.isLoading ||
    overview.isLoading ||
    revisions.isLoading;
  const failed =
    normalizations.error ||
    structures.error ||
    units.error ||
    version.error ||
    overview.error ||
    revisions.error;

  function money(value: string | null | undefined): string {
    return value == null
      ? t("unavailable")
      : format.number(Number(value), {
          style: "currency",
          currency: "BRL",
          maximumFractionDigits: 2,
        });
  }

  function percent(value: string | null | undefined): string {
    return value == null
      ? t("unavailable")
      : `${format.number(Number(value), { maximumFractionDigits: 2 })}%`;
  }

  function valueFor(
    line: DreLine,
    definition: DreDefinition | undefined,
    field:
      | "realizado"
      | "orcado"
      | "variance"
      | "variance_percent"
      | "realizado_ytd"
      | "orcado_ytd"
      | "variance_ytd"
      | "variance_percent_ytd"
  ): string {
    const value = line[field];
    return definition?.line_type === "PERCENTAGE" ||
      field === "variance_percent" ||
      field === "variance_percent_ytd"
      ? percent(value)
      : money(value);
  }

  function openLine(code: string) {
    setLineChoice(code);
    setFactType("ACTUAL");
    setOffset(0);
  }

  function changeScope() {
    setRevisionChoice("");
    setLineChoice(null);
    setOffset(0);
    setCalculationBlockers(null);
  }

  async function recalculate() {
    if (!normalizationId || !version.data || !periodValue || !unitId) return;
    setBusy(true);
    setCalculationError(false);
    setCalculationBlockers(null);
    try {
      const response = await fetch("/api/ton/dre/calculations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          normalization_run_id: normalizationId,
          structure_version_id: version.data.id,
          period: periodValue,
          unit_id: unitId === "consolidated" ? null : unitId,
        }),
      });
      if (!response.ok) throw new Error(String(response.status));
      const run: DreRun = await response.json();
      if (run.status === "NOT_READY") setCalculationBlockers(run.blockers);
      await revisions.mutate();
      await overview.mutate();
    } catch {
      setCalculationError(true);
    } finally {
      setBusy(false);
    }
  }

  async function exportCsv() {
    if (!selectedRun || selectedRun.status !== "READY" || !ready) return;
    const response = await fetch(
      `/api/ton/dre/calculations/${selectedRun.id}/export.csv`
    );
    if (!response.ok) {
      setCalculationError(true);
      return;
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `dre-${selectedRun.scope.period}-${selectedRun.id}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  const blockers = calculationBlockers ?? period?.blockers ?? {};
  const blockerCount = Object.values(blockers).reduce(
    (sum, count) => sum + count,
    0
  );
  const firstBlocker = Object.keys(blockers)[0] ?? "";
  const readinessHref = `/ton/pendencias?normalization=${normalizationId ?? ""}&unit=${unitId === "consolidated" ? "" : (unitId ?? "")}&period=${periodValue ?? ""}&blocker=${firstBlocker}`;
  const chartData = (series.data ?? []).map((point) => ({
    month: format.dateTime(new Date(`${point.period}T12:00:00Z`), {
      month: "short",
    }),
    period: point.period,
    realizado: Number(point.realizado),
    orcado: Number(point.orcado),
  }));

  return (
    <SettingsLayouts.Root width="full">
      <SettingsLayouts.Header
        icon={SvgBarChart}
        title={t("title")}
        description={t("description")}
        divider
      />
      <SettingsLayouts.Body>
        <div className="pb-5">
          <Button href="/ton/data-sources" prominence="secondary">
            {nav("adminNav.items.dataSources.label")}
          </Button>
        </div>
        {!canRead && (
          <Text font="main-ui-body" color="text-03">
            {t("permissionDenied")}
          </Text>
        )}
        {canRead && loading && (
          <div role="status" className="flex items-center gap-2">
            <SvgSimpleLoader />
            <Text font="main-ui-body" color="text-03">
              {t("loading")}
            </Text>
          </div>
        )}
        {canRead && failed && (
          <Text font="main-ui-body" color="status-error-05">
            {t("loadError")}
          </Text>
        )}
        {canRead &&
          !loading &&
          !failed &&
          (!normalizationId || !version.data || !unitId) && (
            <div className="flex flex-col gap-2">
              <Text font="main-ui-body" color="text-03">
                {t("noConfiguration")}
              </Text>
              <Text font="main-ui-body" color="text-03">
                {t("noConfigurationHelp")}
              </Text>
            </div>
          )}
        {canRead &&
          !loading &&
          !failed &&
          normalizationId &&
          version.data &&
          unitId && (
            <div className="flex flex-col gap-6">
              <div className="flex flex-col gap-3 border-b border-01 pb-5">
                <div className="flex flex-wrap items-end gap-3">
                  <Filter
                    label={t("period")}
                    value={periodValue ?? ""}
                    onChange={(value) => {
                      setPeriodChoice(value);
                      changeScope();
                    }}
                    options={periods.map((item) => ({
                      value: item.scope.period,
                      label: format.dateTime(
                        new Date(`${item.scope.period}T12:00:00Z`),
                        { month: "long", year: "numeric" }
                      ),
                    }))}
                  />
                  <Filter
                    label={t("scope")}
                    value={unitId}
                    onChange={(value) => {
                      setUnitChoice(value);
                      changeScope();
                    }}
                    options={[
                      ...(isAdmin
                        ? [{ value: "consolidated", label: t("consolidated") }]
                        : []),
                      ...(units.data ?? []).map((item) => ({
                        value: item.id,
                        label: item.name
                          ? `${getBusinessLabel(item.code)} · ${getBusinessLabel(item.name)}`
                          : getBusinessLabel(item.code),
                      })),
                    ]}
                  />

                  <details className="inline-block text-xs self-end pb-2 group">
                    <summary className="cursor-pointer text-text-03 hover:text-text-05 select-none font-medium flex items-center gap-1 list-none">
                      <Text font="secondary-action">{runtime("advanced")}</Text>
                      <span className="text-[10px] transform group-open:rotate-180 transition-transform">
                        ▼
                      </span>
                    </summary>
                    <div className="flex flex-wrap items-end gap-3 pt-3">
                      <Filter
                        label={t("normalization")}
                        value={normalizationId}
                        onChange={(value) => {
                          setNormalizationChoice(value);
                          changeScope();
                        }}
                        options={(normalizations.data ?? []).map((run) => ({
                          value: run.id,
                          label: format.dateTime(new Date(run.started_at), {
                            dateStyle: "medium",
                          }),
                        }))}
                      />
                      <Filter
                        label={t("structure")}
                        value={structureId ?? ""}
                        onChange={(value) => {
                          setStructureChoice(value);
                          changeScope();
                        }}
                        options={(structures.data ?? []).map((item) => ({
                          value: item.id,
                          label: getBusinessLabel(item.label),
                        }))}
                      />
                    </div>
                  </details>
                </div>
              </div>
              {!period && (
                <Text font="main-ui-body" color="text-03">
                  {t("noPeriods")}
                </Text>
              )}
              {period && !ready && (
                <section
                  className="border border-01 background-neutral-00 rounded-lg p-5"
                  aria-label={t("notReady")}
                >
                  <Text as="h2" font="heading-h3" color="text-05">
                    {t("notReady")}
                  </Text>
                  <Text font="main-ui-body" color="text-03">
                    {t("blockedScope", {
                      period: format.dateTime(
                        new Date(`${periodValue}T12:00:00Z`),
                        { month: "long", year: "numeric" }
                      ),
                      scope:
                        unitId === "consolidated"
                          ? t("consolidated")
                          : (units.data?.find((item) => item.id === unitId)
                              ?.code ?? unitId),
                      count: blockerCount,
                    })}
                  </Text>
                  <div className="grid gap-2 py-4 sm:grid-cols-2">
                    {BLOCKER_GROUPS.map((group) => {
                      const entries = Object.entries(blockers).filter(([key]) =>
                        group.blockerKeys.includes(key)
                      );
                      if (!entries.length) return null;
                      return (
                        <div
                          key={group.id}
                          className="flex flex-col gap-2 border border-01 rounded-12 p-3"
                        >
                          <Text as="h3" font="main-ui-action">
                            {group.label}
                          </Text>
                          <Text as="p" font="secondary-body" color="text-03">
                            {group.description}
                          </Text>
                          {entries.map(([key, count]) => (
                            <div
                              key={key}
                              className="flex justify-between gap-2"
                            >
                              <Text font="main-ui-body">
                                {isBlockerKey(key)
                                  ? t(`blockers.${key}`)
                                  : getBusinessLabel(key)}
                              </Text>
                              <Text font="main-ui-action">
                                {format.number(count)}
                              </Text>
                            </div>
                          ))}
                          <Button
                            href={`${readinessHref.replace(/&blocker=.*$/, "")}&blocker=${entries[0]?.[0] ?? ""}`}
                            prominence="secondary"
                            size="sm"
                          >
                            {t("resolve")}
                          </Button>
                        </div>
                      );
                    })}
                    {Object.entries(blockers)
                      .filter(
                        ([key]) =>
                          !BLOCKER_GROUPS.some((group) =>
                            group.blockerKeys.includes(key)
                          )
                      )
                      .sort(([a], [b]) => a.localeCompare(b))
                      .map(([key, count]) => (
                        <div
                          key={key}
                          className="flex justify-between gap-3 border-b border-01 py-2"
                        >
                          <Text font="main-ui-body" color="text-05">
                            {isBlockerKey(key)
                              ? t(`blockers.${key}`)
                              : getBusinessLabel(key)}
                          </Text>
                          <Text font="main-ui-action" color="text-05">
                            {format.number(count)}
                          </Text>
                        </div>
                      ))}
                  </div>
                  {calculationError && (
                    <Text font="main-ui-body" color="status-error-05">
                      {t("calculationFailed")}
                    </Text>
                  )}
                  <div className="flex flex-wrap gap-2">
                    <Button href={readinessHref}>{t("resolve")}</Button>
                    {canRun && (
                      <Button
                        prominence="secondary"
                        disabled={busy}
                        onClick={recalculate}
                      >
                        {busy ? t("calculating") : t("recalculate")}
                      </Button>
                    )}
                  </div>
                </section>
              )}
              {period && ready && (
                <>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex flex-col gap-1">
                      <Text as="h2" font="heading-h3" color="text-05">
                        {t("statement")}
                      </Text>
                      <Text font="main-ui-muted" color="text-03">
                        {historical
                          ? t("historical")
                          : selectedRun
                            ? t("official")
                            : t("readyNoResult")}
                      </Text>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {canRun && (
                        <Button
                          prominence="secondary"
                          disabled={busy}
                          onClick={recalculate}
                        >
                          {busy ? t("calculating") : t("recalculate")}
                        </Button>
                      )}
                      {selectedRun?.status === "READY" && (
                        <Button prominence="secondary" onClick={exportCsv}>
                          {t("export")}
                        </Button>
                      )}
                    </div>
                  </div>
                  {calculationError && (
                    <Text font="main-ui-body" color="status-error-05">
                      {t("calculationFailed")}
                    </Text>
                  )}
                  {revisionChoice && !selectedRun && (
                    <Text font="main-ui-body" color="status-error-05">
                      {t("revisionUnavailable")}
                    </Text>
                  )}
                  {(revisions.data?.length ?? 0) > 0 && (
                    <Filter
                      label={t("revision")}
                      value={revisionChoice || currentRun?.id || "none"}
                      onChange={(value) => {
                        setRevisionChoice(value === "none" ? "" : value);
                        setLineChoice(null);
                      }}
                      options={[
                        { value: "none", label: t("latest") },
                        ...(revisions.data ?? [])
                          .filter((run) => run.status === "READY")
                          .map((run) => ({
                            value: run.id,
                            label: `${format.dateTime(new Date(run.finished_at), { dateStyle: "short", timeStyle: "short" })} · ${run.id.slice(0, 8)}`,
                          })),
                      ]}
                    />
                  )}
                  {!selectedRun && (
                    <Text font="main-ui-body" color="text-03">
                      {t("readyNoResultHelp")}
                    </Text>
                  )}
                  {selectedRun && statement.isLoading && (
                    <div role="status">
                      <SvgSimpleLoader />
                      <Text font="main-ui-body" color="text-03">
                        {t("loadingResult")}
                      </Text>
                    </div>
                  )}
                  {statement.error && (
                    <Text font="main-ui-body" color="status-error-05">
                      {t("loadError")}
                    </Text>
                  )}
                  {statement.data && (
                    <>
                      {summary && (
                        <section
                          className="grid gap-3 border-y border-01 py-4 sm:grid-cols-2 lg:grid-cols-4"
                          aria-label={t("summary")}
                        >
                          <Metric
                            label={t("actual")}
                            value={valueFor(
                              summary,
                              summaryDefinition,
                              "realizado"
                            )}
                          />
                          <Metric
                            label={t("budget")}
                            value={valueFor(
                              summary,
                              summaryDefinition,
                              "orcado"
                            )}
                          />
                          <Metric
                            label={t("variance")}
                            value={valueFor(
                              summary,
                              summaryDefinition,
                              "variance"
                            )}
                          />
                          <Metric
                            label={t("variancePercent")}
                            value={percent(summary.variance_percent)}
                          />
                          <Metric
                            label={t("actualYtd")}
                            value={valueFor(
                              summary,
                              summaryDefinition,
                              "realizado_ytd"
                            )}
                          />
                          <Metric
                            label={t("budgetYtd")}
                            value={valueFor(
                              summary,
                              summaryDefinition,
                              "orcado_ytd"
                            )}
                          />
                          <Metric
                            label={t("varianceYtd")}
                            value={valueFor(
                              summary,
                              summaryDefinition,
                              "variance_ytd"
                            )}
                          />
                          <Metric
                            label={t("variancePercentYtd")}
                            value={percent(summary.variance_percent_ytd)}
                          />
                        </section>
                      )}
                      <div
                        className={`grid gap-6 ${
                          selectedLine && selectedDefinition
                            ? "xl:grid-cols-[minmax(0,1fr)_380px]"
                            : "grid-cols-1"
                        }`}
                      >
                        <div className="min-w-0 flex flex-col gap-6">
                          <section
                            aria-label={t("statement")}
                            className="min-w-0 overflow-x-auto rounded-lg border border-01 background-neutral-00"
                          >
                            <table className="w-full min-w-[1080px] border-collapse text-end">
                              <thead className="background-neutral-01">
                                <tr>
                                  {COLUMN_KEYS.map((key) => (
                                    <th
                                      key={key}
                                      className={`border-b border-01 px-3 py-3 ${key === "line" ? "text-start" : "text-end"}`}
                                    >
                                      <Text
                                        font="main-ui-muted"
                                        color="text-03"
                                      >
                                        {t(key)}
                                      </Text>
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {statement.data.lines.map((line) => {
                                  const definition = definitions.find(
                                    (item) => item.code === line.code
                                  );
                                  if (!definition) return null;
                                  let depth = 0;
                                  let parent = definition.parent_code;
                                  let hidden = false;
                                  while (parent) {
                                    depth += 1;
                                    if (collapsed.includes(parent))
                                      hidden = true;
                                    parent =
                                      definitions.find(
                                        (item) => item.code === parent
                                      )?.parent_code ?? null;
                                  }
                                  if (hidden) return null;
                                  const children = definitions.some(
                                    (item) => item.parent_code === line.code
                                  );
                                  const emphasized =
                                    definition.line_type === "SUBTOTAL" ||
                                    definition.line_type === "RESULT";
                                  return (
                                    <tr
                                      key={line.code}
                                      className={
                                        definition.line_type === "RESULT"
                                          ? "border-y-2 border-03 bg-background-neutral-01 font-bold text-text-05"
                                          : definition.line_type === "SUBTOTAL"
                                            ? "border-t-2 border-02 bg-background-neutral-00 font-semibold text-text-05"
                                            : "border-t border-01 hover:bg-background-neutral-01/60 transition-colors"
                                      }
                                    >
                                      <td className="px-3 py-2 text-start">
                                        <div
                                          className="flex items-center gap-1"
                                          style={{
                                            paddingInlineStart: depth * 16,
                                          }}
                                        >
                                          {children && (
                                            <Button
                                              size="sm"
                                              prominence="tertiary"
                                              aria-label={
                                                collapsed.includes(line.code)
                                                  ? t("expand", {
                                                      line: getBusinessLabel(
                                                        line.label
                                                      ),
                                                    })
                                                  : t("collapse", {
                                                      line: getBusinessLabel(
                                                        line.label
                                                      ),
                                                    })
                                              }
                                              onClick={() =>
                                                setCollapsed((old) =>
                                                  old.includes(line.code)
                                                    ? old.filter(
                                                        (code) =>
                                                          code !== line.code
                                                      )
                                                    : [...old, line.code]
                                                )
                                              }
                                            >
                                              {collapsed.includes(line.code)
                                                ? "+"
                                                : "−"}
                                            </Button>
                                          )}
                                          {definition.line_type ===
                                          "SOURCE_SUM" ? (
                                            <Button
                                              size="sm"
                                              prominence="tertiary"
                                              onClick={() =>
                                                openLine(line.code)
                                              }
                                            >
                                              {getBusinessLabel(line.label)}
                                            </Button>
                                          ) : (
                                            <Text
                                              font="main-ui-body"
                                              color="text-05"
                                            >
                                              {getBusinessLabel(line.label)}
                                            </Text>
                                          )}
                                        </div>
                                      </td>
                                      {(
                                        [
                                          "realizado",
                                          "orcado",
                                          "variance",
                                          "variance_percent",
                                          "realizado_ytd",
                                          "orcado_ytd",
                                          "variance_ytd",
                                        ] as const
                                      ).map((field) => (
                                        <td
                                          key={field}
                                          className="whitespace-nowrap px-3 py-2 tabular-nums"
                                        >
                                          <Text
                                            font="main-ui-body"
                                            color="text-05"
                                          >
                                            {valueFor(line, definition, field)}
                                          </Text>
                                        </td>
                                      ))}
                                    </tr>
                                  );
                                })}
                              </tbody>
                            </table>
                          </section>
                          <section
                            aria-label={t("periodAnalysis")}
                            className="border border-01 rounded-lg p-4"
                          >
                            <Text as="h3" font="heading-h3" color="text-05">
                              {t("periodAnalysis")}
                            </Text>
                            {series.isLoading && (
                              <Text font="main-ui-body" color="text-03">
                                {t("loading")}
                              </Text>
                            )}
                            {series.error && (
                              <Text font="main-ui-body" color="status-error-05">
                                {t("loadError")}
                              </Text>
                            )}
                            {!series.isLoading &&
                              !series.error &&
                              chartData.length === 0 && (
                                <Text font="main-ui-body" color="text-03">
                                  {t("noSeries")}
                                </Text>
                              )}
                            {chartData.length > 0 && (
                              <div
                                className="h-56 w-full"
                                role="img"
                                aria-label={t("chartDescription")}
                              >
                                <ResponsiveContainer width="100%" height="100%">
                                  <BarChart data={chartData}>
                                    <CartesianGrid
                                      strokeDasharray="3 3"
                                      vertical={false}
                                    />
                                    <XAxis dataKey="month" />
                                    <YAxis
                                      tickFormatter={(value: number) =>
                                        format.number(value, {
                                          notation: "compact",
                                        })
                                      }
                                    />
                                    <Tooltip
                                      formatter={(value) =>
                                        money(String(value))
                                      }
                                    />
                                    <Legend />
                                    <Bar
                                      name={t("actual")}
                                      dataKey="realizado"
                                      fill="var(--text-05)"
                                    />
                                    <Bar
                                      name={t("budget")}
                                      dataKey="orcado"
                                      fill="var(--status-info-04)"
                                    />
                                  </BarChart>
                                </ResponsiveContainer>
                              </div>
                            )}
                            {chartData.length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                {chartData.map((point) => (
                                  <Button
                                    key={point.period}
                                    size="sm"
                                    prominence="tertiary"
                                    onClick={() => {
                                      setPeriodChoice(point.period);
                                      changeScope();
                                    }}
                                  >
                                    {point.month}
                                  </Button>
                                ))}
                              </div>
                            )}
                          </section>
                        </div>
                        {selectedLine && selectedDefinition && (
                          <aside
                            className="min-w-0 border-t border-01 pt-4 xl:border-t-0 xl:border-s xl:ps-5 xl:pt-0"
                            aria-label={t("details")}
                          >
                            <div className="flex flex-col gap-4">
                              <div className="flex items-start justify-between gap-2">
                                <Text as="h3" font="heading-h3" color="text-05">
                                  {getBusinessLabel(selectedLine.label)}
                                </Text>
                                <Button
                                  size="sm"
                                  prominence="tertiary"
                                  onClick={() => setLineChoice(null)}
                                >
                                  {t("close")}
                                </Button>
                              </div>
                              <Text font="main-ui-muted" color="text-03">
                                {t("sourceSumDetail")}
                              </Text>
                              <div className="grid grid-cols-2 gap-2">
                                <Metric
                                  label={t("actual")}
                                  value={money(selectedLine.realizado)}
                                />
                                <Metric
                                  label={t("budget")}
                                  value={money(selectedLine.orcado)}
                                />
                                <Metric
                                  label={t("variance")}
                                  value={money(selectedLine.variance)}
                                />
                              </div>
                              <div className="flex gap-2">
                                <Button
                                  size="sm"
                                  prominence={
                                    factType === "ACTUAL"
                                      ? "primary"
                                      : "secondary"
                                  }
                                  onClick={() => {
                                    setFactType("ACTUAL");
                                    setOffset(0);
                                  }}
                                >
                                  {t("actualContributors")}
                                </Button>
                                <Button
                                  size="sm"
                                  prominence={
                                    factType === "BUDGET"
                                      ? "primary"
                                      : "secondary"
                                  }
                                  onClick={() => {
                                    setFactType("BUDGET");
                                    setOffset(0);
                                  }}
                                >
                                  {t("budgetContributors")}
                                </Button>
                              </div>
                              {contributors.isLoading && (
                                <Text font="main-ui-body" color="text-03">
                                  {t("loading")}
                                </Text>
                              )}
                              {contributors.error && (
                                <Text
                                  font="main-ui-body"
                                  color="status-error-05"
                                >
                                  {t("loadError")}
                                </Text>
                              )}
                              {contributors.data && (
                                <>
                                  <Text font="main-ui-muted" color="text-03">
                                    {t("contributorCount", {
                                      count: contributors.data.total,
                                    })}
                                  </Text>
                                  {contributors.data.rows.length === 0 && (
                                    <Text font="main-ui-body" color="text-03">
                                      {t("noContributors")}
                                    </Text>
                                  )}
                                  {contributors.data.rows.map((fact) => (
                                    <div
                                      key={fact.id}
                                      className="border-t border-01 py-3 text-sm"
                                    >
                                      <Text
                                        font="main-ui-action"
                                        color="text-05"
                                      >{`${fact.account_code} · ${fact.account_label}`}</Text>
                                      <Text
                                        font="main-ui-body"
                                        color="text-05"
                                      >{`${money(fact.amount)} · ${getBusinessLabel(fact.unit_code)}`}</Text>
                                      <Text
                                        font="main-ui-muted"
                                        color="text-03"
                                      >{`${fact.amount_basis} · ${fact.reference ?? t("noReference")}`}</Text>
                                      {fact.record_date && (
                                        <Text
                                          font="main-ui-muted"
                                          color="text-03"
                                        >
                                          {format.dateTime(
                                            new Date(
                                              `${fact.record_date}T12:00:00Z`
                                            ),
                                            { dateStyle: "medium" }
                                          )}
                                        </Text>
                                      )}
                                      <Text
                                        font="main-ui-muted"
                                        color="text-03"
                                      >
                                        {t("sourceFile", {
                                          source: fact.source_name,
                                          file: fact.original_filename,
                                        })}
                                      </Text>
                                      <Text
                                        font="main-ui-muted"
                                        color="text-03"
                                      >
                                        {t("sourceLocation", {
                                          sheet: fact.sheet_name,
                                          row: fact.source_row_number,
                                        })}
                                      </Text>
                                      {fact.review_status && (
                                        <Text
                                          font="main-ui-muted"
                                          color="text-03"
                                        >
                                          {t("reviewStatus", {
                                            status: fact.review_status,
                                          })}
                                        </Text>
                                      )}
                                    </div>
                                  ))}
                                  <div className="flex items-center justify-between gap-2">
                                    <Button
                                      size="sm"
                                      prominence="tertiary"
                                      disabled={offset === 0}
                                      onClick={() =>
                                        setOffset(
                                          Math.max(0, offset - PAGE_SIZE)
                                        )
                                      }
                                    >
                                      {t("previous")}
                                    </Button>
                                    <Text font="main-ui-muted" color="text-03">
                                      {t("page", {
                                        start: contributors.data.total
                                          ? offset + 1
                                          : 0,
                                        end: Math.min(
                                          offset + PAGE_SIZE,
                                          contributors.data.total
                                        ),
                                        total: contributors.data.total,
                                      })}
                                    </Text>
                                    <Button
                                      size="sm"
                                      prominence="tertiary"
                                      disabled={
                                        offset + PAGE_SIZE >=
                                        contributors.data.total
                                      }
                                      onClick={() =>
                                        setOffset(offset + PAGE_SIZE)
                                      }
                                    >
                                      {t("next")}
                                    </Button>
                                  </div>
                                </>
                              )}
                            </div>
                          </aside>
                        )}
                      </div>
                      <section className="border-t border-01 pt-4">
                        <Button
                          prominence="tertiary"
                          onClick={() => setShowVersion(!showVersion)}
                        >
                          {t("versionDetails")}
                        </Button>
                        {showVersion && (
                          <div className="grid gap-2 pt-3 sm:grid-cols-2">
                            <Metric
                              label={t("calculatedAt")}
                              value={format.dateTime(
                                new Date(statement.data.run.finished_at),
                                { dateStyle: "medium", timeStyle: "short" }
                              )}
                            />
                            <Metric
                              label={t("structureVersion")}
                              value={String(statement.data.version.number)}
                            />
                            <Metric
                              label={t("normalizationRevision")}
                              value={String(
                                statement.data.run.provenance
                                  .financial_mapping_revision ??
                                  t("unavailable")
                              )}
                            />
                            <Metric
                              label={t("amountBasisRevision")}
                              value={String(
                                statement.data.run.provenance
                                  .amount_basis_revision ?? t("unavailable")
                              )}
                            />
                            <Metric
                              label={t("budgetVersion")}
                              value={
                                Array.isArray(
                                  statement.data.run.provenance
                                    .budget_execution_ids
                                )
                                  ? statement.data.run.provenance.budget_execution_ids.join(
                                      ", "
                                    )
                                  : t("unavailable")
                              }
                            />
                            <Metric
                              label={t("normalizationRun")}
                              value={
                                statement.data.run.scope.normalization_run_id
                              }
                            />
                            <Metric
                              label={t("datasetRevision")}
                              value={String(
                                statement.data.run.provenance
                                  .dataset_revision ?? t("unavailable")
                              )}
                            />
                            <Metric
                              label={t("resultRevision")}
                              value={statement.data.run.id.slice(0, 8)}
                            />
                          </div>
                        )}
                      </section>
                    </>
                  )}
                </>
              )}
            </div>
          )}
      </SettingsLayouts.Body>
    </SettingsLayouts.Root>
  );
}

interface FilterProps {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}

function Filter({ label, value, options, onChange }: FilterProps) {
  return (
    <div className="min-w-40 flex flex-col gap-1">
      <Text font="main-ui-muted" color="text-03">
        {label}
      </Text>
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
    </div>
  );
}

interface MetricProps {
  label: string;
  value: string;
}

function Metric({ label, value }: MetricProps) {
  return (
    <div className="flex min-w-0 flex-col gap-1 break-all">
      <Text font="main-ui-muted" color="text-03">
        {label}
      </Text>
      <Text font="main-ui-action" color="text-05">
        {value}
      </Text>
    </div>
  );
}

export default DrePage;
