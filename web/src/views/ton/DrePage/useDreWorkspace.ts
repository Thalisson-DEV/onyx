"use client";

import { useState } from "react";
import useSWR from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";
import { useUser } from "@/providers/UserProvider";
import type {
  ContributorPage,
  DreRun,
  DreStatement,
  DreVersion,
  Normalization,
  PeriodPoint,
  ReadinessOverview,
  Structure,
  Unit,
} from "@/views/admin/DrePage/types";

export const CONTRIBUTOR_PAGE = 25;
export const CONSOLIDATED = "consolidated";

/**
 * Data for the TON DRE workspace. Same endpoints and selection rules as the
 * administrative DRE view: latest normalization and structure, the readiness
 * overview per period, and only a READY calculation run that matches both is
 * the official result. Nothing here computes financial values.
 */
export function useDreWorkspace() {
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
  const [lineChoice, setLineChoice] = useState<string | null>(null);
  const [factType, setFactType] = useState<"ACTUAL" | "BUDGET">("ACTUAL");
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(false);
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
    canRead ? "/api/ton/financial-domain/units?limit=100" : null,
    errorHandlingFetcher
  );
  const normalizationId = normalizationChoice || normalizations.data?.[0]?.id;
  const structureId = structureChoice || structures.data?.[0]?.id;
  const unitId =
    unitChoice || (isAdmin ? CONSOLIDATED : units.data?.[0]?.id) || undefined;
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
  const statement = useSWR<DreStatement>(
    ready && officialRun
      ? `/api/ton/dre/calculations/${officialRun.id}/statement`
      : null,
    errorHandlingFetcher
  );
  const definitions = statement.data?.version.lines ?? [];
  const summaryDefinition =
    [...definitions].reverse().find((line) => line.line_type === "RESULT") ??
    [...definitions].reverse().find((line) => line.line_type === "SUBTOTAL");
  const summary = statement.data?.lines.find(
    (line) => line.code === summaryDefinition?.code
  );
  const series = useSWR<PeriodPoint[]>(
    statement.data && summary
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
    officialRun && selectedDefinition?.line_type === "SOURCE_SUM"
      ? `/api/ton/dre/calculations/${officialRun.id}/lines/${encodeURIComponent(selectedDefinition.code)}/contributors?fact_type=${factType}&limit=${CONTRIBUTOR_PAGE}&offset=${offset}`
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

  function resetSelection() {
    setLineChoice(null);
    setOffset(0);
    setCalculation("idle");
  }

  async function recalculate() {
    if (!normalizationId || !version.data || !periodValue || !unitId) return;
    setBusy(true);
    setCalculation("idle");
    try {
      const response = await fetch("/api/ton/dre/calculations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          normalization_run_id: normalizationId,
          structure_version_id: version.data.id,
          period: periodValue,
          unit_id: unitId === CONSOLIDATED ? null : unitId,
        }),
      });
      if (!response.ok) throw new Error(String(response.status));
      const run: DreRun = await response.json();
      setCalculation(run.status === "READY" ? "ready" : "blocked");
      await Promise.all([revisions.mutate(), overview.mutate()]);
    } catch {
      setCalculation("failed");
    } finally {
      setBusy(false);
    }
  }

  async function exportCsv(): Promise<boolean> {
    if (!officialRun || !ready) return false;
    const response = await fetch(
      `/api/ton/dre/calculations/${officialRun.id}/export.csv`
    );
    if (!response.ok) return false;
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `dre-${officialRun.scope.period}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
    return true;
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
    definitions,
    summary,
    summaryDefinition,
    series,
    selectedLine,
    selectedDefinition,
    contributors,
    factType,
    offset,
    busy,
    calculation,
    recalculate,
    exportCsv,
    select: {
      normalization(value: string) {
        setNormalizationChoice(value);
        resetSelection();
      },
      structure(value: string) {
        setStructureChoice(value);
        resetSelection();
      },
      unit(value: string) {
        setUnitChoice(value);
        resetSelection();
      },
      period(value: string) {
        setPeriodChoice(value);
        resetSelection();
      },
      line(code: string | null) {
        setLineChoice(code);
        setFactType("ACTUAL");
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
