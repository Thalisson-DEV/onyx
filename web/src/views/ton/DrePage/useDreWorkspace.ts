"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { Route } from "next";
import useSWR from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { postTonJson } from "@/lib/ton/decisions";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";
import { useUser } from "@/providers/UserProvider";
import type {
  ContributorPage,
  DreRun,
  DreLine,
  DreStatement,
  DreUnitsYear,
  DreVersion,
  DreYear,
  Normalization,
  PeriodPoint,
  ReadinessOverview,
  Structure,
  Unit,
} from "@/views/admin/DrePage/types";

export const CONTRIBUTOR_PAGE = 25;

/** An NG account of a natureza line, with its amount in the drilled month. */
export interface DrillAccount {
  code: string;
  label: string | null;
  amount: string;
}
export const CONSOLIDATED = "consolidated";

/** One month of the year as the statement shows it, for one unit or a set. */
export interface YearMonthView {
  period: string;
  /** The month's result when one scope is shown; null for a set of units. */
  runId: string | null;
  lines: DreLine[];
  /** Selected units still without a result this month. */
  missingUnits: number;
}

/** Months side by side in columns, or one block per month from top to bottom. */
export type DreView = "columns" | "stacked";
const VIEW_KEY = "ton.dre.view";

function storedView(): DreView {
  try {
    return window.localStorage.getItem(VIEW_KEY) === "stacked"
      ? "stacked"
      : "columns";
  } catch {
    return "columns";
  }
}

/**
 * Data for the TON DRE workspace. Same endpoints and selection rules as the
 * administrative DRE view: latest normalization and structure, the readiness
 * overview per period, and only a READY calculation run that matches both is
 * the official result. Nothing here computes financial values.
 */
/** "vale-norte-caixa" -> "caixa": the model name used in the URL. */
export function modelOf(key: string): string {
  return key.split("-").at(-1) ?? key;
}

export function useDreWorkspace() {
  const { user } = useUser();
  const permissions = user?.effective_permissions ?? [];
  const canRead = hasPermission(permissions, Permission.READ_TON_SOURCES);
  // Importers calculate any scope; a reader (a unit manager) calculates the
  // units they see, which the API enforces.
  const canRun =
    canRead || hasPermission(permissions, Permission.IMPORT_TON_SOURCES);
  const isAdmin = hasPermission(
    permissions,
    Permission.FULL_ADMIN_PANEL_ACCESS
  );

  const [normalizationChoice, setNormalizationChoice] = useState("");
  // The DRE model lives in the URL (?modelo=caixa), so the sidebar can link
  // straight to each one.
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const model = searchParams?.get("modelo") ?? "";
  const [unitChoice, setUnitChoice] = useState("");
  // Two or more units: the DRE of the set, each month summed over them.
  const [unitSet, setUnitSet] = useState<string[]>([]);
  const multi = unitSet.length >= 2;
  const [periodChoice, setPeriodChoice] = useState("");
  const [lineChoice, setLineChoice] = useState<string | null>(null);
  // The drawer of a natureza line opened from one of its NG accounts.
  const [accountChoice, setAccountChoice] = useState<DrillAccount | null>(null);
  const [drillPeriod, setDrillPeriod] = useState<string | null>(null);
  // null: every calculated month of the year.
  const [monthChoice, setMonthChoice] = useState<string[] | null>(null);
  const [view, setView] = useState<DreView>("columns");
  useEffect(() => setView(storedView()), []);
  const [factType, setFactType] = useState<"ACTUAL" | "BUDGET">("ACTUAL");
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<{
    done: number;
    total: number;
  } | null>(null);
  const [calculation, setCalculation] = useState<
    "idle" | "failed" | "blocked" | "ready"
  >("idle");

  const normalizations = useSWR<Normalization[]>(
    canRead ? "/api/ton/financial-domain/normalizations?limit=20" : null,
    errorHandlingFetcher
  );
  const structures = useSWR<Structure[]>(
    canRead ? "/api/ton/dre/structures?limit=100" : null,
    errorHandlingFetcher
  );
  const units = useSWR<Unit[]>(
    canRead
      ? "/api/ton/financial-domain/units?limit=100&active_only=true"
      : null,
    errorHandlingFetcher
  );
  const normalizationId = normalizationChoice || normalizations.data?.[0]?.id;
  const structureId =
    (model &&
      structures.data?.find((item) => modelOf(item.key) === model)?.id) ||
    structures.data?.[0]?.id;
  const unitId = multi
    ? isAdmin
      ? CONSOLIDATED
      : unitSet[0]
    : unitChoice || (isAdmin ? CONSOLIDATED : units.data?.[0]?.id) || undefined;
  const version = useSWR<DreVersion>(
    structureId
      ? `/api/ton/dre/structures/${structureId}/latest-version`
      : null,
    errorHandlingFetcher
  );
  const unitQuery =
    unitId && unitId !== CONSOLIDATED ? `&unit_id=${unitId}` : "";
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
  const officialRun = revisions.data?.find(
    (run) =>
      run.status === "READY" &&
      run.scope.normalization_run_id === normalizationId &&
      run.scope.structure_version_id === version.data?.id
  );
  const ready = period?.status === "READY";
  const unitParam =
    unitId && unitId !== CONSOLIDATED ? `&unit_id=${unitId}` : "";
  const year = useSWR<DreYear>(
    ready && normalizationId && version.data && periodValue
      ? `/api/ton/dre/calculations/year?normalization_run_id=${normalizationId}&structure_version_id=${version.data.id}&year=${periodValue.slice(0, 4)}${unitParam}`
      : null,
    errorHandlingFetcher
  );
  const unitsQuery = unitSet
    .map((id) => `&unit_ids=${encodeURIComponent(id)}`)
    .join("");
  const unitsYear = useSWR<DreUnitsYear>(
    multi && normalizationId && version.data && periodValue
      ? `/api/ton/dre/calculations/units-year?normalization_run_id=${normalizationId}&structure_version_id=${version.data.id}&year=${periodValue.slice(0, 4)}${unitsQuery}`
      : null,
    errorHandlingFetcher
  );
  const rawMonths: YearMonthView[] = multi
    ? (unitsYear.data?.months ?? []).map((month) => ({
        period: month.period,
        runId: null,
        lines: month.lines,
        missingUnits: month.missing_unit_ids.length,
      }))
    : (year.data?.months ?? []).map((month) => ({
        period: month.run.scope.period,
        runId: month.run.id,
        lines: month.lines,
        missingUnits: 0,
      }));
  // Months up to the selected period; later months belong to another closing.
  const yearMonths = rawMonths.filter(
    (month) => !periodValue || month.period <= periodValue
  );
  const shownMonths = yearMonths.filter(
    (month) => monthChoice === null || monthChoice.includes(month.period)
  );
  const budgetPresent = yearMonths.some((month) =>
    month.lines.some(
      (line) => Number(line.orcado) !== 0 || Number(line.orcado_ytd) !== 0
    )
  );
  const drillRun =
    (year.data?.months ?? []).find(
      (month) => month.run.scope.period === drillPeriod
    )?.run ?? officialRun;
  const statement = useSWR<DreStatement>(
    ready && officialRun
      ? `/api/ton/dre/calculations/${officialRun.id}/statement`
      : null,
    errorHandlingFetcher
  );
  const allDefinitions =
    (multi ? unitsYear.data?.version.lines : statement.data?.version.lines) ??
    [];
  // Lines that receive NG naturezas: they open into their NG accounts.
  const natureLineCodes = new Set(
    (statement.data?.version.assignments ?? []).map((item) => item.line_code)
  );
  // A line hidden in the structure (and everything under it) stays in every
  // total but leaves the screen, as it leaves the Excel.
  const hiddenCodes = new Set<string>();
  for (const line of [...allDefinitions].sort(
    (a, b) => a.position - b.position
  )) {
    if (line.hidden || (line.parent_code && hiddenCodes.has(line.parent_code)))
      hiddenCodes.add(line.code);
  }
  const definitions = allDefinitions.filter(
    (line) => !hiddenCodes.has(line.code)
  );
  const summaryDefinition =
    [...definitions].reverse().find((line) => line.line_type === "RESULT") ??
    [...definitions].reverse().find((line) => line.line_type === "SUBTOTAL");
  const summary = (
    multi ? yearMonths.at(-1)?.lines : statement.data?.lines
  )?.find((line) => line.code === summaryDefinition?.code);
  const series = useSWR<PeriodPoint[]>(
    !multi && statement.data && summary
      ? `/api/ton/dre/calculations/series?normalization_run_id=${statement.data.run.scope.normalization_run_id}&structure_version_id=${statement.data.run.scope.structure_version_id}&year=${periodValue?.slice(0, 4)}&line_code=${encodeURIComponent(summary.code)}${unitQuery}`
      : null,
    errorHandlingFetcher
  );
  const drillLines =
    yearMonths.find((month) => month.period === drillRun?.scope.period)
      ?.lines ?? statement.data?.lines;
  const selectedLine = drillLines?.find((line) => line.code === lineChoice);
  const selectedDefinition = definitions.find(
    (line) => line.code === lineChoice
  );
  const contributors = useSWR<ContributorPage>(
    drillRun && selectedDefinition?.line_type === "SOURCE_SUM"
      ? `/api/ton/dre/calculations/${drillRun.id}/lines/${encodeURIComponent(selectedDefinition.code)}/contributors?fact_type=${factType}&limit=${CONTRIBUTOR_PAGE}&offset=${offset}${accountChoice ? `&account_code=${encodeURIComponent(accountChoice.code)}` : ""}`
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
  const error =
    normalizations.error ??
    structures.error ??
    units.error ??
    version.error ??
    overview.error ??
    revisions.error;

  /** Calculates the year of every selected unit, then reloads the sum. */
  async function calculateUnits(only?: string[]) {
    if (!normalizationId || !version.data || !periodValue) return;
    const targets = only ?? unitSet;
    setBusy(true);
    setCalculation("idle");
    try {
      for (const [index, id] of targets.entries()) {
        setProgress({ done: index, total: targets.length });
        const response = await fetch("/api/ton/dre/calculations/year", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            normalization_run_id: normalizationId,
            structure_version_id: version.data.id,
            period: periodValue,
            unit_id: id,
          }),
        });
        if (!response.ok) throw new Error(String(response.status));
      }
      const data = await unitsYear.mutate();
      const last = data?.months.at(-1);
      setCalculation(
        last && last.missing_unit_ids.length === 0 ? "ready" : "blocked"
      );
    } catch {
      setCalculation("failed");
    } finally {
      setProgress(null);
      setBusy(false);
    }
  }

  /** Excel of the selected units: their sum, then each unit. */
  async function exportUnitsExcel(): Promise<boolean> {
    if (!normalizationId || !version.data || !periodValue) return false;
    const response = await fetch(
      `/api/ton/dre/calculations/units-year/export.xlsx?normalization_run_id=${normalizationId}&structure_version_id=${version.data.id}&period=${periodValue}${unitsQuery}`
    );
    if (!response.ok) return false;
    const url = URL.createObjectURL(await response.blob());
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `dre-unidades-${periodValue.slice(0, 4)}-01-a-${periodValue.slice(5, 7)}.xlsx`;
    anchor.click();
    URL.revokeObjectURL(url);
    return true;
  }

  function resetSelection() {
    setLineChoice(null);
    setDrillPeriod(null);
    setAccountChoice(null);
    setOffset(0);
    setCalculation("idle");
  }

  /** Calculates every month from January to the selected one, in order. */
  async function recalculate() {
    if (!normalizationId || !version.data || !periodValue || !unitId) return;
    const [calendarYear, month] = periodValue.split("-").map(Number) as [
      number,
      number,
    ];
    const months = Array.from(
      { length: month },
      (_, index) => `${calendarYear}-${String(index + 1).padStart(2, "0")}-01`
    );
    setBusy(true);
    setCalculation("idle");
    try {
      let last: DreRun | null = null;
      // One request computes the whole year with each month loaded once.
      setProgress({ done: 0, total: months.length });
      const yearResponse = await fetch("/api/ton/dre/calculations/year", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          normalization_run_id: normalizationId,
          structure_version_id: version.data.id,
          period: periodValue,
          unit_id: unitId === CONSOLIDATED ? null : unitId,
        }),
      });
      if (yearResponse.ok) {
        // SAFETY: the endpoint returns the DreRunView list, January first.
        const runs = (await yearResponse.json()) as DreRun[];
        last = runs.at(-1) ?? null;
        setCalculation(last?.status === "READY" ? "ready" : "blocked");
        await Promise.all([
          revisions.mutate(),
          overview.mutate(),
          year.mutate(),
        ]);
        return;
      }
      if (yearResponse.status !== 404 && yearResponse.status !== 405)
        throw new Error(String(yearResponse.status));
      for (const [index, value] of months.entries()) {
        setProgress({ done: index, total: months.length });
        const response = await fetch("/api/ton/dre/calculations", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            normalization_run_id: normalizationId,
            structure_version_id: version.data.id,
            period: value,
            unit_id: unitId === CONSOLIDATED ? null : unitId,
          }),
        });
        if (!response.ok) throw new Error(String(response.status));
        last = await response.json();
      }
      setCalculation(last?.status === "READY" ? "ready" : "blocked");
      await Promise.all([revisions.mutate(), overview.mutate(), year.mutate()]);
    } catch {
      setCalculation("failed");
    } finally {
      setProgress(null);
      setBusy(false);
    }
  }

  async function download(path: string, filename: string): Promise<boolean> {
    if (!officialRun || !ready) return false;
    const response = await fetch(
      `/api/ton/dre/calculations/${officialRun.id}/${path}`
    );
    if (!response.ok) return false;
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
    return true;
  }

  function exportCsv(): Promise<boolean> {
    return download("export.csv", `dre-${officialRun?.scope.period}.csv`);
  }

  /** Year to date workbook built by the backend from the persisted DRE. */
  function exportExcel(): Promise<boolean> {
    const month = periodValue?.slice(5, 7);
    return download(
      "export.xlsx",
      `dre-${periodValue?.slice(0, 4)}-01-a-${month}.xlsx`
    );
  }

  function retry() {
    void normalizations.mutate();
    void structures.mutate();
    void units.mutate();
    void version.mutate();
    void overview.mutate();
    void revisions.mutate();
  }

  return {
    access: { canRead, canRun, isAdmin },
    loading,
    error,
    retry,
    configured: Boolean(normalizationId && version.data && unitId),
    multi,
    unitSet,
    unitsYear,
    calculateUnits,
    exportUnitsExcel,
    version: version.data,
    async structureSaved() {
      await Promise.all([structures.mutate(), version.mutate()]);
    },
    /** Creates the Caixa and Econômica DREs of the Controladoria's model. */
    async createSimplified() {
      await postTonJson("/api/ton/dre/structures/simplified", {});
      await structures.mutate();
    },
    normalizations: normalizations.data ?? [],
    structures: structures.data ?? [],
    units: units.data ?? [],
    normalizationId,
    structureId,
    unitId,
    periods,
    period,
    periodValue,
    ready,
    officialRun,
    statement,
    year,
    yearMonths,
    shownMonths,
    monthChoice,
    budgetPresent,
    view,
    drillRun,
    definitions,
    natureLineCodes,
    summary,
    summaryDefinition,
    series,
    selectedLine,
    selectedDefinition,
    selectedAccount: accountChoice,
    contributors,
    factType,
    offset,
    busy,
    calculation,
    recalculate,
    progress,
    exportCsv,
    exportExcel,
    select: {
      normalization(value: string) {
        setNormalizationChoice(value);
        resetSelection();
      },
      structure(value: string) {
        const key = structures.data?.find((item) => item.id === value)?.key;
        const params = new URLSearchParams(searchParams?.toString() ?? "");
        if (key) params.set("modelo", modelOf(key));
        // SAFETY: same typed route, only the query string changes.
        router.replace(`${pathname}?${params.toString()}` as Route);
        resetSelection();
      },
      unit(value: string) {
        setUnitChoice(value);
        setUnitSet([]);
        resetSelection();
      },
      /** Several units at once; one unit falls back to the single view. */
      units(ids: string[]) {
        if (ids.length === 1) {
          setUnitChoice(ids[0] ?? "");
          setUnitSet([]);
        } else {
          setUnitSet(ids);
        }
        resetSelection();
      },
      period(value: string) {
        setPeriodChoice(value);
        resetSelection();
      },
      view(value: DreView) {
        setView(value);
        try {
          window.localStorage.setItem(VIEW_KEY, value);
        } catch {
          // The choice still applies to this visit.
        }
      },
      /** Toggle one month; the last visible month cannot be hidden. */
      month(period: string) {
        const all = yearMonths.map((month) => month.period);
        const current = monthChoice ?? all;
        const next = current.includes(period)
          ? current.filter((item) => item !== period)
          : [...current, period];
        if (next.length === 0) return;
        setMonthChoice(next.length === all.length ? null : next);
      },
      allMonths() {
        setMonthChoice(null);
      },
      line(code: string | null, period?: string, account?: DrillAccount) {
        setLineChoice(code);
        setDrillPeriod(period ?? null);
        setAccountChoice(account ?? null);
        setFactType("ACTUAL");
        setOffset(0);
      },
      /** Back to every NG account of the open line. */
      allAccounts() {
        setAccountChoice(null);
        setOffset(0);
      },
      factType(value: "ACTUAL" | "BUDGET") {
        setFactType(value);
        setOffset(0);
      },
      offset: setOffset,
    },
  };
}

export type DreWorkspace = ReturnType<typeof useDreWorkspace>;
