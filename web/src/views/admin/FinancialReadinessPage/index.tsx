"use client";

import { useState } from "react";
import { useFormatter, useTranslations } from "next-intl";
import useSWR from "swr";
import { useSearchParams } from "next/navigation";
import { Button, InputTypeIn, Text } from "@opal/components";
import { SvgBarChart, SvgSimpleLoader } from "@opal/icons";
import { SettingsLayouts } from "@opal/layouts";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";
import { useUser } from "@/providers/UserProvider";

interface Normalization {
  id: string;
  mapping_revision_number: number;
  started_at: string;
}

interface Structure {
  id: string;
  label: string;
  latest_version: number;
}

interface Version {
  id: string;
  number: number;
  lines: Array<{ code: string; label: string; line_type: string }>;
}

interface PeriodReadiness {
  status: "READY" | "NOT_READY";
  scope: { period: string };
  blockers: Record<string, number>;
}

interface Overview {
  periods: PeriodReadiness[];
}

interface Candidate {
  target_id: string;
  code: string;
  label: string;
  evidence: "EXACT_CODE" | "APPROVED_MAPPING";
}

interface BlockerRow {
  source_id: string | null;
  source_key: string | null;
  account_id: string | null;
  item_id: string | null;
  record_count: number;
  periods: string[];
  status: string;
  candidate: Candidate | null;
  legacy_evidence: {
    suggested_code: string;
    suggested_label: string | null;
    reference_label: string;
    reference_digest: string;
  } | null;
  line_candidate: string | null;
  paired: boolean | null;
  evidence: string | null;
}

interface BlockerPage {
  total: number;
  rows: BlockerRow[];
}

interface Target {
  id: string;
  code: string;
  label?: string;
  name?: string;
}

const CATEGORIES = [
  { key: "units", blocker: "UNMAPPED_UNIT" },
  { key: "accounts", blocker: "UNMAPPED_ACCOUNT" },
  { key: "budgetAccounts", blocker: "BUDGET_UNMAPPED_ACCOUNT" },
  { key: "budgetUnits", blocker: "BUDGET_UNMAPPED_UNIT" },
  { key: "amountBasis", blocker: "ACTUAL_AMOUNT_SEMANTICS_UNRESOLVED" },
  { key: "dreAssignment", blocker: "DRE_ACCOUNT_UNMAPPED" },
  { key: "drePending", blocker: "DRE_MAPPING_PENDING_APPROVAL" },
  { key: "budgetPeriods", blocker: "BUDGET_PERIOD_UNRESOLVED" },
  { key: "reconciliation", blocker: "SOURCE_RECONCILIATION_UNRESOLVED" },
  {
    key: "reconciliationAmbiguous",
    blocker: "SOURCE_RECONCILIATION_AMBIGUOUS",
  },
] as const;

const RECONCILIATION_DECISIONS = [
  "SUPPLEMENTAL",
  "EXPECTED_DIFFERENCE",
  "NOT_SAME_EVENT",
  "NG_AUTHORITATIVE",
] as const;

async function postJson(
  path: string,
  body: Record<string, string | null>
): Promise<void> {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(String(response.status));
}

function FinancialReadinessPage() {
  const t = useTranslations("financialReadiness");
  const searchParams = useSearchParams();
  const format = useFormatter();
  const { user } = useUser();
  const permissions = user?.effective_permissions ?? [];
  const canManage = hasPermission(permissions, Permission.MANAGE_TON_SOURCES);
  const canConfigure = hasPermission(
    permissions,
    Permission.FULL_ADMIN_PANEL_ACCESS
  );
  const canRecompute = hasPermission(
    permissions,
    Permission.IMPORT_TON_SOURCES
  );
  const [runSelection, setRunSelection] = useState(
    searchParams.get("normalization") ?? ""
  );
  const [structureSelection, setStructureSelection] = useState("");
  const [unitSelection, setUnitSelection] = useState(
    searchParams.get("unit") ?? ""
  );
  const [categoryIndex, setCategoryIndex] = useState(
    Math.max(
      0,
      CATEGORIES.findIndex(
        (item) => item.blocker === searchParams.get("blocker")
      )
    )
  );
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<BlockerRow | null>(null);
  const [targetSearch, setTargetSearch] = useState("");
  const [targetId, setTargetId] = useState("");
  const [accountCode, setAccountCode] = useState("");
  const [accountLabel, setAccountLabel] = useState("");
  const [reason, setReason] = useState("");
  const [basis, setBasis] = useState<"MOVEMENT" | "FINAL">("MOVEMENT");
  const [lineCode, setLineCode] = useState("");
  const [startMonth, setStartMonth] = useState("");
  const [endMonth, setEndMonth] = useState("");
  const [decision, setDecision] = useState("SUPPLEMENTAL");
  const [confirming, setConfirming] = useState(false);
  const [actionError, setActionError] = useState(false);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  const runs = useSWR<Normalization[]>(
    "/api/ton/financial-domain/normalizations?limit=20",
    errorHandlingFetcher
  );
  const structures = useSWR<Structure[]>(
    "/api/ton/dre/structures?limit=100",
    errorHandlingFetcher
  );
  const visibleUnits = useSWR<Target[]>(
    !canConfigure ? "/api/ton/financial-domain/units?limit=100" : null,
    errorHandlingFetcher
  );
  const unitId = canConfigure
    ? undefined
    : unitSelection || visibleUnits.data?.[0]?.id;
  const runId = runSelection || runs.data?.[0]?.id;
  const structureId = structureSelection || structures.data?.[0]?.id;
  const version = useSWR<Version>(
    structureId
      ? `/api/ton/dre/structures/${structureId}/latest-version`
      : null,
    errorHandlingFetcher
  );
  const overview = useSWR<Overview>(
    runId && version.data && (canConfigure || unitId)
      ? `/api/ton/financial-domain/normalizations/${runId}/readiness?structure_version_id=${version.data.id}${unitId ? `&unit_id=${unitId}` : ""}`
      : null,
    errorHandlingFetcher
  );
  const extraBlockers = Array.from(
    new Set(
      (overview.data?.periods ?? []).flatMap((period) =>
        Object.keys(period.blockers)
      )
    )
  ).filter((blocker) => !CATEGORIES.some((item) => item.blocker === blocker));
  const categories = [
    ...CATEGORIES.map((item) => ({ ...item, label: t(item.key) })),
    ...extraBlockers.map((blocker) => ({
      key: "other",
      blocker,
      label: blocker.replaceAll("_", " "),
    })),
  ];
  const category = categories[categoryIndex] ?? {
    key: "units",
    blocker: "UNMAPPED_UNIT",
    label: t("units"),
  };
  const blockerUrl =
    runId && version.data && (canConfigure || unitId)
      ? `/api/ton/financial-domain/normalizations/${runId}/readiness/blockers/${category.blocker}?structure_version_id=${version.data.id}&limit=25&offset=${offset}&search=${encodeURIComponent(search)}${unitId ? `&unit_id=${unitId}` : ""}`
      : null;
  const blockers = useSWR<BlockerPage>(blockerUrl, errorHandlingFetcher);
  const isMapping = [
    "units",
    "accounts",
    "budgetAccounts",
    "budgetUnits",
  ].includes(category.key);
  const targetType = ["units", "budgetUnits"].includes(category.key)
    ? "units"
    : "accounts";
  const targets = useSWR<Target[]>(
    selected && isMapping
      ? `/api/ton/financial-domain/${targetType}?limit=50&search=${encodeURIComponent(targetSearch)}`
      : null,
    errorHandlingFetcher
  );

  function openRow(row: BlockerRow) {
    setSelected(row);
    setTargetId(row.candidate?.target_id ?? "");
    setAccountCode(row.legacy_evidence?.suggested_code ?? row.source_key ?? "");
    setAccountLabel(row.legacy_evidence?.suggested_label ?? "");
    setTargetSearch("");
    setLineCode(row.line_candidate ?? "");
    setStartMonth("");
    setEndMonth("");
    setReason("");
    setConfirming(false);
    setActionError(false);
    setSaved(false);
  }

  async function approve() {
    if (!selected || !runId || !structureId || !reason.trim()) return;
    setBusy(true);
    setActionError(false);
    try {
      if (isMapping) {
        if (!selected.source_id || !selected.source_key || !targetId) return;
        const mappingKind = {
          units: "UNIT",
          accounts: "ACCOUNT",
          budgetAccounts: "BUDGET_ACCOUNT",
          budgetUnits: "BUDGET_UNIT",
        }[category.key];
        if (!mappingKind) return;
        await postJson("/api/ton/financial-domain/mappings", {
          source_id: selected.source_id,
          kind: mappingKind,
          source_key: selected.source_key,
          unit_id: targetType === "units" ? targetId : null,
          account_id: targetType === "accounts" ? targetId : null,
          reason,
        });
      } else if (category.key === "amountBasis") {
        if (!selected.account_id) return;
        await postJson(
          `/api/ton/financial-domain/accounts/${selected.account_id}/amount-basis`,
          { basis, reason }
        );
      } else if (
        category.key === "dreAssignment" ||
        category.key === "drePending"
      ) {
        if (!selected.account_id || !lineCode) return;
        await postJson(`/api/ton/dre/structures/${structureId}/assignments`, {
          account_id: selected.account_id,
          line_code: lineCode,
          status: "APPROVED",
          reason,
        });
        await version.mutate();
      } else if (category.key === "budgetPeriods") {
        if (!selected.source_id || !selected.source_key || !startMonth) return;
        await postJson("/api/ton/financial-domain/mappings", {
          source_id: selected.source_id,
          kind: "BUDGET_PERIOD",
          source_key: selected.source_key,
          calendar_period: `${startMonth}-01`,
          effective_to: endMonth ? `${endMonth}-01` : null,
          reason,
        });
      } else {
        if (!selected.item_id) return;
        await postJson(
          `/api/ton/financial-domain/normalizations/${runId}/reconciliation/items/${selected.item_id}/decision`,
          { decision, reason }
        );
      }
      setSaved(true);
      setConfirming(false);
    } catch {
      setActionError(true);
    } finally {
      setBusy(false);
    }
  }

  async function reject() {
    if (
      (!selected?.candidate && !selected?.legacy_evidence) ||
      !selected.source_id ||
      !selected.source_key ||
      !reason.trim()
    )
      return;
    setBusy(true);
    setActionError(false);
    try {
      if (category.key !== "units" && category.key !== "accounts") return;
      const exactCandidate =
        selected.candidate?.evidence === "EXACT_CODE"
          ? selected.candidate
          : null;
      await postJson("/api/ton/financial-domain/candidates/rejections", {
        source_id: selected.source_id,
        kind: category.key === "units" ? "UNIT" : "ACCOUNT",
        source_key: selected.source_key,
        target_id: exactCandidate?.target_id ?? null,
        evidence: exactCandidate ? "EXACT_CODE" : "LEGACY_REFERENCE",
        reference_digest: exactCandidate
          ? null
          : (selected.legacy_evidence?.reference_digest ?? null),
        reason,
      });
      setSelected(null);
      await blockers.mutate();
    } catch {
      setActionError(true);
    } finally {
      setBusy(false);
    }
  }

  async function createAccount() {
    if (!accountCode.trim() || !accountLabel.trim()) return;
    setBusy(true);
    setActionError(false);
    try {
      const response = await fetch("/api/ton/financial-domain/accounts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: accountCode.trim(),
          label: accountLabel.trim(),
        }),
      });
      if (!response.ok) throw new Error(String(response.status));
      const account: Target = await response.json();
      setTargetId(account.id);
      await targets.mutate();
    } catch {
      setActionError(true);
    } finally {
      setBusy(false);
    }
  }

  async function recompute() {
    if (!runId) return;
    setBusy(true);
    setActionError(false);
    try {
      await postJson(
        `/api/ton/financial-domain/normalizations/${runId}/recompute`,
        {}
      );
      setRunSelection("");
      await runs.mutate();
      await overview.mutate();
      await blockers.mutate();
      setSaved(false);
    } catch {
      setActionError(true);
    } finally {
      setBusy(false);
    }
  }

  const loading =
    runs.isLoading ||
    structures.isLoading ||
    visibleUnits.isLoading ||
    version.isLoading ||
    overview.isLoading ||
    blockers.isLoading;
  const failed =
    runs.error ||
    structures.error ||
    visibleUnits.error ||
    version.error ||
    overview.error ||
    blockers.error;
  const selectedCanEdit =
    category.key === "other"
      ? false
      : isMapping ||
          category.key === "budgetPeriods" ||
          category.key.startsWith("reconciliation")
        ? canManage
        : canConfigure;
  const hasDecisionTarget = isMapping
    ? Boolean(targetId)
    : category.key === "dreAssignment" || category.key === "drePending"
      ? Boolean(lineCode)
      : category.key === "amountBasis"
        ? Boolean(selected?.account_id)
        : category.key === "budgetPeriods"
          ? Boolean(startMonth)
          : true;

  return (
    <SettingsLayouts.Root width="lg">
      <SettingsLayouts.Header
        icon={SvgBarChart}
        title={t("title")}
        description={t("description")}
        divider
        rightChildren={
          canRecompute && runId ? (
            <Button onClick={recompute} disabled={busy}>
              {t("recompute")}
            </Button>
          ) : undefined
        }
      />
      <SettingsLayouts.Body>
        {loading && (
          <div role="status">
            <SvgSimpleLoader />
            <Text font="main-ui-body" color="text-03">
              {t("loading")}
            </Text>
          </div>
        )}
        {failed && (
          <Text font="main-ui-body" color="status-error-05">
            {t("loadError")}
          </Text>
        )}
        {!loading &&
          !failed &&
          (!runId || !version.data || (!canConfigure && !unitId)) && (
            <Text font="main-ui-body" color="text-03">
              {t("noRuns")}
            </Text>
          )}
        {!loading &&
          !failed &&
          runId &&
          version.data &&
          (canConfigure || unitId) && (
            <div className="flex flex-col gap-6">
              <div className="flex flex-wrap gap-2">
                {(runs.data ?? []).map((run) => (
                  <Button
                    key={run.id}
                    prominence={run.id === runId ? "primary" : "secondary"}
                    onClick={() => {
                      setRunSelection(run.id);
                      setOffset(0);
                    }}
                    size="sm"
                  >
                    {format.dateTime(new Date(run.started_at), {
                      dateStyle: "medium",
                    })}
                  </Button>
                ))}
              </div>
              <div className="flex flex-wrap gap-2">
                {(structures.data ?? []).map((structure) => (
                  <Button
                    key={structure.id}
                    prominence={
                      structure.id === structureId ? "primary" : "secondary"
                    }
                    onClick={() => setStructureSelection(structure.id)}
                    size="sm"
                  >
                    {structure.label}
                  </Button>
                ))}
              </div>
              {!canConfigure && (
                <div className="flex flex-wrap gap-2">
                  {(visibleUnits.data ?? []).map((unit) => (
                    <Button
                      key={unit.id}
                      size="sm"
                      prominence={unit.id === unitId ? "primary" : "secondary"}
                      onClick={() => {
                        setUnitSelection(unit.id);
                        setOffset(0);
                        setSelected(null);
                      }}
                    >
                      {unit.code}
                    </Button>
                  ))}
                </div>
              )}
              <section className="rounded-xl border border-01 background-neutral-00 p-4">
                <Text as="h2" font="heading-h3" color="text-05">
                  {t("overview")}
                </Text>
                {(overview.data?.periods ?? []).map((period) => (
                  <div
                    key={period.scope.period}
                    className={
                      period.scope.period === searchParams.get("period")
                        ? "flex flex-wrap items-center justify-between gap-3 border-b-2 border-02 py-3"
                        : "flex flex-wrap items-center justify-between gap-3 border-b border-01 py-3"
                    }
                  >
                    <Text font="main-ui-body" color="text-05">
                      {format.dateTime(new Date(period.scope.period), {
                        year: "numeric",
                        month: "long",
                      })}
                    </Text>
                    <Text
                      font="main-ui-action"
                      color={
                        period.status === "READY"
                          ? "status-success-05"
                          : "status-error-05"
                      }
                    >
                      {period.status === "READY" ? t("ready") : t("notReady")}
                    </Text>
                    <Text font="main-ui-muted" color="text-03">
                      {t("blockerCount", {
                        count: Object.values(period.blockers).reduce(
                          (sum, value) => sum + value,
                          0
                        ),
                      })}
                    </Text>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(period.blockers).map(
                        ([blocker, count]) => (
                          <Button
                            key={blocker}
                            size="sm"
                            prominence="tertiary"
                            onClick={() => {
                              setCategoryIndex(
                                categories.findIndex(
                                  (item) => item.blocker === blocker
                                )
                              );
                              setOffset(0);
                              setSelected(null);
                            }}
                          >
                            {`${blocker.replaceAll("_", " ")} (${count})`}
                          </Button>
                        )
                      )}
                    </div>
                  </div>
                ))}
                {overview.data?.periods.length === 0 && (
                  <Text font="main-ui-body" color="text-03">
                    {t("empty")}
                  </Text>
                )}
              </section>
              <section className="flex flex-col gap-4">
                <Text as="h2" font="heading-h3" color="text-05">
                  {t("decisions")}
                </Text>
                <div className="flex flex-wrap gap-2">
                  {categories.map((item, index) => (
                    <Button
                      key={item.key}
                      prominence={
                        index === categoryIndex ? "primary" : "secondary"
                      }
                      size="sm"
                      onClick={() => {
                        setCategoryIndex(index);
                        setOffset(0);
                        setSelected(null);
                      }}
                    >
                      {item.label}
                    </Button>
                  ))}
                </div>
                <InputTypeIn
                  searchIcon
                  value={search}
                  onChange={(event) => {
                    setSearch(event.target.value);
                    setOffset(0);
                  }}
                  placeholder={t("search")}
                  aria-label={t("search")}
                />
                <div className="rounded-xl border border-01 background-neutral-00">
                  {(blockers.data?.rows ?? []).map((row, index) => (
                    <div
                      key={`${row.source_key ?? row.item_id ?? row.account_id}-${index}`}
                      className="flex flex-wrap items-center justify-between gap-3 border-b border-01 p-3"
                    >
                      <div className="flex flex-col gap-1">
                        <Text font="main-ui-action" color="text-05">
                          {row.source_key ?? row.item_id ?? t("unknownSource")}
                        </Text>
                        <Text font="main-ui-muted" color="text-03">
                          {t("affected", { count: row.record_count })}
                        </Text>
                        <Text font="secondary-body" color="text-03">
                          {row.status === "APPROVED" && row.candidate
                            ? `${t("approve")}: ${row.candidate.code}`
                            : row.candidate
                              ? t("candidate", { code: row.candidate.code })
                              : row.legacy_evidence
                                ? t("candidate", {
                                    code: row.legacy_evidence.suggested_code,
                                  })
                                : row.line_candidate
                                  ? t("candidate", { code: row.line_candidate })
                                  : (row.evidence ?? t("noCandidate"))}
                        </Text>
                      </div>
                      <Button
                        size="sm"
                        prominence="secondary"
                        onClick={() => openRow(row)}
                      >
                        {t("inspect")}
                      </Button>
                    </div>
                  ))}
                  {blockers.data?.rows.length === 0 && (
                    <div className="p-4">
                      <Text font="main-ui-body" color="text-03">
                        {t("empty")}
                      </Text>
                    </div>
                  )}
                </div>
                <div className="flex items-center justify-between">
                  <Button
                    size="sm"
                    prominence="secondary"
                    disabled={offset === 0}
                    onClick={() => setOffset(Math.max(0, offset - 25))}
                  >
                    {t("previous")}
                  </Button>
                  <Text font="main-ui-muted" color="text-03">
                    {t("pageRange", {
                      start: offset + 1,
                      end: Math.min(offset + 25, blockers.data?.total ?? 0),
                      total: blockers.data?.total ?? 0,
                    })}
                  </Text>
                  <Button
                    size="sm"
                    prominence="secondary"
                    disabled={offset + 25 >= (blockers.data?.total ?? 0)}
                    onClick={() => setOffset(offset + 25)}
                  >
                    {t("next")}
                  </Button>
                </div>
              </section>
              {selected && (
                <section className="rounded-xl border border-01 background-neutral-00 p-4 flex flex-col gap-4">
                  <Text as="h2" font="heading-h3" color="text-05">
                    {t("reviewDecision")}
                  </Text>
                  <Text font="main-ui-body" color="text-03">
                    {selected.evidence ?? t("sourceEvidence")}
                  </Text>
                  {selected.legacy_evidence && (
                    <Text font="secondary-body" color="text-03">
                      {`${selected.legacy_evidence.reference_label}: ${selected.legacy_evidence.suggested_code}${selected.legacy_evidence.suggested_label ? ` — ${selected.legacy_evidence.suggested_label}` : ""}`}
                    </Text>
                  )}
                  {isMapping && selectedCanEdit && (
                    <div className="flex flex-col gap-2">
                      <InputTypeIn
                        value={targetSearch}
                        onChange={(event) =>
                          setTargetSearch(event.target.value)
                        }
                        placeholder={t("searchTarget")}
                        aria-label={t("searchTarget")}
                      />
                      <div className="flex flex-wrap gap-2">
                        {(targets.data ?? []).map((target) => (
                          <Button
                            key={target.id}
                            size="sm"
                            prominence={
                              target.id === targetId ? "primary" : "secondary"
                            }
                            onClick={() => setTargetId(target.id)}
                          >
                            {target.code}
                          </Button>
                        ))}
                      </div>
                      {targets.isLoading && (
                        <Text font="main-ui-muted" color="text-03">
                          {t("loading")}
                        </Text>
                      )}
                      {(category.key === "accounts" ||
                        category.key === "budgetAccounts") &&
                        canConfigure && (
                          <div className="flex flex-col gap-2 border-t border-01 pt-3">
                            <InputTypeIn
                              value={accountCode}
                              onChange={(event) =>
                                setAccountCode(event.target.value)
                              }
                              aria-label={t("accountCode")}
                              placeholder={t("accountCode")}
                            />
                            <InputTypeIn
                              value={accountLabel}
                              onChange={(event) =>
                                setAccountLabel(event.target.value)
                              }
                              aria-label={t("accountLabel")}
                              placeholder={t("accountLabel")}
                            />
                            <Button
                              size="sm"
                              prominence="secondary"
                              disabled={
                                !accountCode.trim() ||
                                !accountLabel.trim() ||
                                busy
                              }
                              onClick={createAccount}
                            >
                              {t("createAccount")}
                            </Button>
                          </div>
                        )}
                    </div>
                  )}
                  {category.key === "amountBasis" && selectedCanEdit && (
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        prominence={
                          basis === "MOVEMENT" ? "primary" : "secondary"
                        }
                        onClick={() => setBasis("MOVEMENT")}
                      >
                        {t("movement")}
                      </Button>
                      <Button
                        size="sm"
                        prominence={basis === "FINAL" ? "primary" : "secondary"}
                        onClick={() => setBasis("FINAL")}
                      >
                        {t("finalAmount")}
                      </Button>
                    </div>
                  )}
                  {(category.key === "dreAssignment" ||
                    category.key === "drePending") &&
                    selectedCanEdit && (
                      <div className="flex flex-wrap gap-2">
                        {version.data.lines
                          .filter((line) => line.line_type === "SOURCE_SUM")
                          .map((line) => (
                            <Button
                              key={line.code}
                              size="sm"
                              prominence={
                                line.code === lineCode ? "primary" : "secondary"
                              }
                              onClick={() => setLineCode(line.code)}
                            >
                              {line.label}
                            </Button>
                          ))}
                      </div>
                    )}
                  {category.key === "budgetPeriods" && selectedCanEdit && (
                    <div className="flex gap-2">
                      <InputTypeIn
                        type="month"
                        value={startMonth}
                        onChange={(event) => setStartMonth(event.target.value)}
                        aria-label={t("startMonth")}
                      />
                      <InputTypeIn
                        type="month"
                        value={endMonth}
                        onChange={(event) => setEndMonth(event.target.value)}
                        aria-label={t("endMonth")}
                      />
                    </div>
                  )}
                  {category.key.startsWith("reconciliation") &&
                    selectedCanEdit && (
                      <div className="flex flex-wrap gap-2">
                        {RECONCILIATION_DECISIONS.filter(
                          (value) =>
                            value !== "NG_AUTHORITATIVE" || selected.paired
                        ).map((value) => (
                          <Button
                            key={value}
                            size="sm"
                            prominence={
                              decision === value ? "primary" : "secondary"
                            }
                            onClick={() => setDecision(value)}
                          >
                            {t(value)}
                          </Button>
                        ))}
                      </div>
                    )}
                  {selectedCanEdit && (
                    <InputTypeIn
                      value={reason}
                      onChange={(event) => setReason(event.target.value)}
                      placeholder={t("reason")}
                      aria-label={t("reason")}
                    />
                  )}
                  {confirming && (
                    <Text font="main-ui-body" color="text-05">
                      {t("approvalConsequence", {
                        count: selected.record_count,
                      })}
                    </Text>
                  )}
                  {saved && (
                    <Text font="main-ui-body" color="status-success-05">
                      {t("savedRecompute")}
                    </Text>
                  )}
                  {actionError && (
                    <Text font="main-ui-body" color="status-error-05">
                      {t("saveError")}
                    </Text>
                  )}
                  <div className="flex flex-wrap gap-2">
                    {selectedCanEdit && !confirming && (
                      <Button
                        disabled={!reason.trim() || !hasDecisionTarget || busy}
                        onClick={() => setConfirming(true)}
                      >
                        {t("reviewApproval")}
                      </Button>
                    )}
                    {selectedCanEdit && confirming && (
                      <Button disabled={busy} onClick={approve}>
                        {t("approve")}
                      </Button>
                    )}
                    {selectedCanEdit &&
                      (category.key === "units" ||
                        category.key === "accounts") &&
                      (selected.candidate?.evidence === "EXACT_CODE" ||
                        selected.legacy_evidence) && (
                        <Button
                          prominence="secondary"
                          disabled={!reason.trim() || busy}
                          onClick={reject}
                        >
                          {t("rejectCandidate")}
                        </Button>
                      )}
                    <Button
                      prominence="tertiary"
                      onClick={() => setSelected(null)}
                    >
                      {t("close")}
                    </Button>
                  </div>
                </section>
              )}
            </div>
          )}
      </SettingsLayouts.Body>
    </SettingsLayouts.Root>
  );
}

export default FinancialReadinessPage;
