"use client";

import { useState } from "react";
import useSWR from "swr";
import { useSearchParams } from "next/navigation";
import { Button, InputTypeIn, Modal, Text } from "@opal/components";
import {
  SvgAlertTriangle,
  SvgArrowRight,
  SvgCheckCircle,
  SvgChevronDown,
  SvgRefreshCw,
  SvgServer,
  SvgShield,
} from "@opal/icons";
import { cn } from "@opal/utils";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";
import { useUser } from "@/providers/UserProvider";
import { getBusinessLabel } from "@/lib/ton/labels";
import { useTonClosing } from "@/lib/ton/api";
import { COPY, formatPeriod } from "@/lib/ton/copy";
import ClosingFrame from "@/views/ton/components/ClosingFrame";
import {
  IconTile,
  LoadingBlock,
  StatusPill,
  TonCard,
} from "@/views/ton/components/ui";

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

type CategoryKey = keyof typeof COPY.pending.categories;

const CATEGORIES: { key: CategoryKey; blocker: string }[] = [
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
];

/** Overview links use business categories; the queue works on blocker codes. */
const CATEGORY_PARAM: Record<string, string> = {
  units: "UNMAPPED_UNIT",
  budget: "BUDGET_PERIOD_UNRESOLVED",
  reconciliation: "SOURCE_RECONCILIATION_UNRESOLVED",
  actuals: "NO_ACTUAL",
};

const RECONCILIATION_DECISIONS = [
  "SUPPLEMENTAL",
  "EXPECTED_DIFFERENCE",
  "NOT_SAME_EVENT",
  "NG_AUTHORITATIVE",
] as const;

const MAPPING_KEYS: CategoryKey[] = [
  "units",
  "accounts",
  "budgetAccounts",
  "budgetUnits",
];

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

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

interface QueueCategory {
  key: CategoryKey;
  blocker: string;
  label: string;
  description: string;
  action: string;
  rowTitle: string;
  count: number;
  noActual: boolean;
}

function describeCategory(
  key: CategoryKey,
  blocker: string,
  count: number
): QueueCategory {
  if (blocker === "NO_ACTUAL") {
    return {
      key: "other",
      blocker,
      label: COPY.pending.noActual.label,
      description: COPY.pending.noActual.description,
      action: COPY.pending.noActual.action,
      rowTitle: COPY.pending.noActual.label,
      count,
      noActual: true,
    };
  }
  const copy = COPY.pending.categories[key];
  return {
    key,
    blocker,
    label: key === "other" ? getBusinessLabel(blocker) : copy.label,
    description: copy.description,
    action: copy.action,
    rowTitle: copy.rowTitle,
    count,
    noActual: false,
  };
}

function rowTitle(row: BlockerRow, category: QueueCategory): string {
  if (category.noActual) return category.rowTitle;
  if (row.source_key && !UUID.test(row.source_key))
    return getBusinessLabel(row.source_key);
  return category.rowTitle;
}

function rowPeriods(row: BlockerRow): string | null {
  if (!row.periods.length) return null;
  return row.periods
    .map((period) => formatPeriod(period).toLowerCase())
    .join(", ");
}

function rowSuggestion(row: BlockerRow): string {
  if (row.status === "APPROVED" && row.candidate)
    return COPY.pending.approvedCandidate(row.candidate.code);
  if (row.candidate) return COPY.pending.candidate(row.candidate.code);
  if (row.legacy_evidence)
    return COPY.pending.candidate(row.legacy_evidence.suggested_code);
  if (row.line_candidate) return COPY.pending.candidate(row.line_candidate);
  return COPY.pending.noCandidate;
}

export default function PendingPage() {
  const searchParams = useSearchParams();
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
  const closing = useTonClosing();
  const requestedBlocker =
    searchParams.get("blocker") ??
    CATEGORY_PARAM[searchParams.get("categoria") ?? ""] ??
    null;

  const [runSelection, setRunSelection] = useState(
    searchParams.get("normalization") ?? ""
  );
  const [structureSelection, setStructureSelection] = useState("");
  const [unitSelection, setUnitSelection] = useState(
    searchParams.get("unit") ?? ""
  );
  const [blockerSelection, setBlockerSelection] = useState<string | null>(
    requestedBlocker
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
  // No default: a reconciliation outcome must be an explicit human choice.
  const [decision, setDecision] = useState<
    (typeof RECONCILIATION_DECISIONS)[number] | null
  >(null);
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
  const scopeReady = !!runId && !!version.data && (canConfigure || !!unitId);
  const overview = useSWR<Overview>(
    scopeReady
      ? `/api/ton/financial-domain/normalizations/${runId}/readiness?structure_version_id=${version.data?.id}${unitId ? `&unit_id=${unitId}` : ""}`
      : null,
    errorHandlingFetcher
  );

  const requestedPeriod = searchParams.get("period");
  const period =
    overview.data?.periods.find(
      (item) => item.scope.period === requestedPeriod
    ) ?? overview.data?.periods.at(-1);
  const periodBlockers = period?.blockers ?? {};
  const totalPending = Object.values(periodBlockers).reduce(
    (sum, count) => sum + count,
    0
  );

  const categories = (() => {
    const known = CATEGORIES.map((item) =>
      describeCategory(
        item.key,
        item.blocker,
        periodBlockers[item.blocker] ?? 0
      )
    );
    const extra = Object.keys(periodBlockers)
      .filter((blocker) => !CATEGORIES.some((item) => item.blocker === blocker))
      .map((blocker) =>
        describeCategory("other", blocker, periodBlockers[blocker] ?? 0)
      );
    return [...known, ...extra].filter(
      (item) => item.count > 0 || item.blocker === blockerSelection
    );
  })();

  const category: QueueCategory | undefined =
    categories.find((item) => item.blocker === blockerSelection) ??
    [...categories].sort((a, b) => b.count - a.count)[0];

  const blockerUrl =
    scopeReady && category
      ? `/api/ton/financial-domain/normalizations/${runId}/readiness/blockers/${category.blocker}?structure_version_id=${version.data?.id}&limit=25&offset=${offset}&search=${encodeURIComponent(search)}${unitId ? `&unit_id=${unitId}` : ""}`
      : null;
  const blockers = useSWR<BlockerPage>(blockerUrl, errorHandlingFetcher);
  const isMapping = !!category && MAPPING_KEYS.includes(category.key);
  const targetType =
    category && ["units", "budgetUnits"].includes(category.key)
      ? "units"
      : "accounts";
  const targets = useSWR<Target[]>(
    selected && isMapping
      ? `/api/ton/financial-domain/${targetType}?limit=50&search=${encodeURIComponent(targetSearch)}`
      : null,
    errorHandlingFetcher
  );

  function chooseCategory(blocker: string) {
    setBlockerSelection(blocker);
    setOffset(0);
    setSelected(null);
  }

  function openRow(row: BlockerRow) {
    setSelected(row);
    setTargetId(row.candidate?.target_id ?? "");
    setAccountCode(row.legacy_evidence?.suggested_code ?? row.source_key ?? "");
    setAccountLabel(row.legacy_evidence?.suggested_label ?? "");
    setTargetSearch("");
    setLineCode(row.line_candidate ?? "");
    setStartMonth("");
    setEndMonth("");
    setDecision(null);
    setReason("");
    setConfirming(false);
    setActionError(false);
    setSaved(false);
  }

  async function approve() {
    if (!selected || !category || !runId || !structureId || !reason.trim())
      return;
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
        }[
          category.key as
            | "units"
            | "accounts"
            | "budgetAccounts"
            | "budgetUnits"
        ];
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
        if (!selected.item_id || !decision) return;
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
      !category ||
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
      await closing.mutate();
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
    overview.isLoading;
  const failed =
    runs.error ||
    structures.error ||
    visibleUnits.error ||
    version.error ||
    overview.error ||
    blockers.error;
  const selectedCanEdit =
    !category || category.key === "other"
      ? false
      : isMapping ||
          category.key === "budgetPeriods" ||
          category.key.startsWith("reconciliation")
        ? canManage
        : canConfigure;
  const hasDecisionTarget = isMapping
    ? Boolean(targetId)
    : category?.key === "dreAssignment" || category?.key === "drePending"
      ? Boolean(lineCode)
      : category?.key === "amountBasis"
        ? Boolean(selected?.account_id)
        : category?.key === "budgetPeriods"
          ? Boolean(startMonth)
          : category?.key.startsWith("reconciliation")
            ? Boolean(decision)
            : true;
  const periodLabel = period ? formatPeriod(period.scope.period) : null;

  return (
    <ClosingFrame
      active="pending"
      title={COPY.pending.title}
      description={COPY.pending.description}
      wide
      actions={
        canRecompute && runId ? (
          <Button
            onClick={recompute}
            disabled={busy}
            prominence="secondary"
            icon={SvgRefreshCw}
          >
            {COPY.pending.recompute}
          </Button>
        ) : undefined
      }
    >
      {loading && (
        <TonCard className="p-5">
          <LoadingBlock label={COPY.common.loading} />
        </TonCard>
      )}
      {failed && (
        <TonCard className="p-5">
          <Text font="main-ui-body" color="status-error-05">
            {COPY.pending.loadError}
          </Text>
        </TonCard>
      )}
      {!loading && !failed && !scopeReady && (
        <TonCard className="p-5">
          <Text font="main-ui-body" color="text-03">
            {COPY.pending.noBase}
          </Text>
        </TonCard>
      )}

      {!loading && !failed && scopeReady && period && (
        <div className="flex flex-wrap items-center gap-3">
          <StatusPill tone={period.status === "READY" ? "success" : "warning"}>
            {period.status === "READY"
              ? COPY.pending.ready
              : COPY.pending.notReady}
          </StatusPill>
          <Text font="main-ui-action" color="text-05">
            {COPY.pending.periodStatus(periodLabel ?? "", totalPending)}
          </Text>
        </div>
      )}

      {!loading && !failed && scopeReady && category && (
        <div className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-5 items-start">
          <nav
            aria-label={COPY.pending.categoriesLabel}
            className="ton-card flex flex-col p-2 lg:sticky lg:top-4"
          >
            {categories.map((item) => {
              const active = item.blocker === category.blocker;
              return (
                // Category switcher rows; Opal has no list-selection button.
                <button
                  key={item.blocker}
                  type="button"
                  aria-current={active ? "true" : undefined}
                  onClick={() => chooseCategory(item.blocker)}
                  className={cn(
                    "ton-focusable ton-row-link flex items-center gap-3 px-3 py-2.5 text-start",
                    active && "bg-background-neutral-02"
                  )}
                >
                  <span className="flex-1 min-w-0">
                    <Text
                      font={active ? "main-ui-action" : "main-ui-body"}
                      color="text-05"
                    >
                      {item.label}
                    </Text>
                  </span>
                  <StatusPill tone={item.count > 0 ? "warning" : "neutral"}>
                    {String(item.count)}
                  </StatusPill>
                </button>
              );
            })}
          </nav>

          <TonCard className="flex flex-col gap-4 p-5" as="div">
            <div className="flex items-start gap-3">
              <IconTile
                icon={category.noActual ? SvgServer : SvgShield}
                tone="warning"
              />
              <div className="flex flex-col gap-1 min-w-0">
                <Text as="h2" font="heading-h3" color="text-05">
                  {category.label}
                </Text>
                <Text font="main-ui-body" color="text-03">
                  {category.description}
                </Text>
                <Text font="secondary-action" color="text-04">
                  {category.action}
                </Text>
              </div>
            </div>
            {category.noActual && (
              <div>
                <Button href="/ton/fontes" rightIcon={SvgArrowRight}>
                  {COPY.pending.noActual.cta}
                </Button>
              </div>
            )}
            {!category.noActual && (
              <InputTypeIn
                searchIcon
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setOffset(0);
                }}
                placeholder={COPY.pending.search}
                aria-label={COPY.pending.search}
              />
            )}
            {blockers.isLoading && <LoadingBlock label={COPY.common.loading} />}
            <ul className="flex flex-col divide-y divide-border-01 border border-01 rounded-12">
              {(blockers.data?.rows ?? []).map((row, index) => (
                <li
                  key={`${row.source_key ?? row.item_id ?? row.account_id}-${index}`}
                  className="flex flex-wrap items-center gap-3 p-3.5"
                >
                  <IconTile icon={SvgAlertTriangle} tone="warning" size="sm" />
                  <div className="flex flex-col gap-1 min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Text font="main-ui-action" color="text-05">
                        {rowTitle(row, category)}
                      </Text>
                      <StatusPill tone="warning">
                        {getBusinessLabel(row.status)}
                      </StatusPill>
                    </div>
                    <Text font="secondary-body" color="text-03">
                      {[
                        COPY.pending.affected(row.record_count),
                        rowPeriods(row),
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </Text>
                    <Text font="secondary-body" color="text-03">
                      {row.evidence && !row.candidate && !row.legacy_evidence
                        ? getBusinessLabel(row.evidence)
                        : rowSuggestion(row)}
                    </Text>
                  </div>
                  <Button
                    size="md"
                    prominence="secondary"
                    onClick={() => openRow(row)}
                  >
                    {COPY.pending.analyze}
                  </Button>
                </li>
              ))}
              {blockers.data?.rows.length === 0 && (
                <li className="p-4">
                  <Text font="main-ui-body" color="text-03">
                    {COPY.pending.empty}
                  </Text>
                </li>
              )}
            </ul>
            {(blockers.data?.total ?? 0) > 25 && (
              <div className="flex items-center justify-between">
                <Button
                  size="md"
                  prominence="secondary"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - 25))}
                >
                  {COPY.pending.previous}
                </Button>
                <Text font="main-ui-muted" color="text-03">
                  {COPY.pending.pageRange(
                    offset + 1,
                    Math.min(offset + 25, blockers.data?.total ?? 0),
                    blockers.data?.total ?? 0
                  )}
                </Text>
                <Button
                  size="md"
                  prominence="secondary"
                  disabled={offset + 25 >= (blockers.data?.total ?? 0)}
                  onClick={() => setOffset(offset + 25)}
                >
                  {COPY.pending.next}
                </Button>
              </div>
            )}
          </TonCard>
        </div>
      )}

      {!loading && !failed && scopeReady && !category && (
        <TonCard className="flex items-center gap-3 p-5">
          <SvgCheckCircle size={18} className="ton-brand-text" />
          <Text font="main-ui-body" color="text-04">
            {COPY.home.attention.empty}
          </Text>
        </TonCard>
      )}

      {!loading && !failed && scopeReady && (
        <details className="group">
          <summary className="flex items-center gap-1 cursor-pointer list-none w-fit">
            <Text font="secondary-action" color="text-03">
              {COPY.pending.advanced}
            </Text>
            <SvgChevronDown
              size={14}
              className="transition-transform group-open:rotate-180"
            />
          </summary>
          <div className="flex flex-col gap-3 pt-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="ton-eyebrow w-36">
                {COPY.pending.advancedBase}
              </span>
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
                  {`${formatPeriod(run.started_at.slice(0, 10))} · rev. ${run.mapping_revision_number}`}
                </Button>
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="ton-eyebrow w-36">
                {COPY.pending.advancedStructure}
              </span>
              {(structures.data ?? []).map((structure) => (
                <Button
                  key={structure.id}
                  prominence={
                    structure.id === structureId ? "primary" : "secondary"
                  }
                  onClick={() => setStructureSelection(structure.id)}
                  size="sm"
                >
                  {getBusinessLabel(structure.label)}
                </Button>
              ))}
            </div>
            {!canConfigure && (
              <div className="flex flex-wrap items-center gap-2">
                <span className="ton-eyebrow w-36">
                  {COPY.pending.advancedUnit}
                </span>
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
                    {getBusinessLabel(unit.name ?? unit.code)}
                  </Button>
                ))}
              </div>
            )}
          </div>
        </details>
      )}

      {selected && category && (
        <Modal
          open
          onOpenChange={(open) => {
            if (!open && !busy) setSelected(null);
          }}
        >
          <Modal.Content width="lg">
            <Modal.Header title={COPY.pending.dialog.title} />
            <Modal.Body>
              <div className="flex flex-col gap-5">
                <section className="flex flex-col gap-1.5">
                  <span className="ton-eyebrow">
                    {COPY.pending.dialog.found}
                  </span>
                  <div className="flex flex-wrap items-center gap-2">
                    <Text font="main-ui-action" color="text-05">
                      {rowTitle(selected, category)}
                    </Text>
                    <StatusPill tone="warning">
                      {getBusinessLabel(selected.status)}
                    </StatusPill>
                  </div>
                  {selected.evidence && (
                    <Text font="main-ui-body" color="text-04">
                      {getBusinessLabel(selected.evidence)}
                    </Text>
                  )}
                  <Text font="secondary-body" color="text-03">
                    {rowSuggestion(selected)}
                  </Text>
                  {selected.legacy_evidence && (
                    <Text font="secondary-body" color="text-03">
                      {`${selected.legacy_evidence.reference_label}: ${selected.legacy_evidence.suggested_code}${selected.legacy_evidence.suggested_label ? ` — ${selected.legacy_evidence.suggested_label}` : ""}`}
                    </Text>
                  )}
                </section>

                <section className="flex flex-col gap-1.5">
                  <span className="ton-eyebrow">
                    {COPY.pending.dialog.scope}
                  </span>
                  <Text font="main-ui-body" color="text-04">
                    {[
                      COPY.pending.affected(selected.record_count),
                      rowPeriods(selected),
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </Text>
                </section>

                {category.noActual && (
                  <section className="flex flex-col gap-2">
                    <Text font="main-ui-body" color="text-04">
                      {COPY.pending.noActual.action}
                    </Text>
                    <div>
                      <Button href="/ton/fontes" rightIcon={SvgArrowRight}>
                        {COPY.pending.noActual.cta}
                      </Button>
                    </div>
                  </section>
                )}

                {!category.noActual && !selectedCanEdit && (
                  <Text font="main-ui-body" color="text-03">
                    {category.key === "other"
                      ? category.action
                      : COPY.pending.dialog.noPermission}
                  </Text>
                )}

                {selectedCanEdit && (
                  <section className="flex flex-col gap-3">
                    <span className="ton-eyebrow">
                      {COPY.pending.dialog.decision}
                    </span>
                    <Text font="main-ui-body" color="text-04">
                      {category.action}
                    </Text>
                    {isMapping && (
                      <div className="flex flex-col gap-2">
                        <InputTypeIn
                          searchIcon
                          value={targetSearch}
                          onChange={(event) =>
                            setTargetSearch(event.target.value)
                          }
                          placeholder={COPY.pending.dialog.searchTarget}
                          aria-label={COPY.pending.dialog.searchTarget}
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
                              {getBusinessLabel(
                                target.name ?? target.label ?? target.code
                              )}
                            </Button>
                          ))}
                        </div>
                        {targets.isLoading && (
                          <LoadingBlock label={COPY.common.loading} lines={1} />
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
                                aria-label={COPY.pending.dialog.accountCode}
                                placeholder={COPY.pending.dialog.accountCode}
                              />
                              <InputTypeIn
                                value={accountLabel}
                                onChange={(event) =>
                                  setAccountLabel(event.target.value)
                                }
                                aria-label={COPY.pending.dialog.accountLabel}
                                placeholder={COPY.pending.dialog.accountLabel}
                              />
                              <div>
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
                                  {COPY.pending.dialog.createAccount}
                                </Button>
                              </div>
                            </div>
                          )}
                      </div>
                    )}
                    {category.key === "amountBasis" && (
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          prominence={
                            basis === "MOVEMENT" ? "primary" : "secondary"
                          }
                          onClick={() => setBasis("MOVEMENT")}
                        >
                          {COPY.pending.dialog.movement}
                        </Button>
                        <Button
                          size="sm"
                          prominence={
                            basis === "FINAL" ? "primary" : "secondary"
                          }
                          onClick={() => setBasis("FINAL")}
                        >
                          {COPY.pending.dialog.finalAmount}
                        </Button>
                      </div>
                    )}
                    {(category.key === "dreAssignment" ||
                      category.key === "drePending") &&
                      version.data && (
                        <div className="flex flex-wrap gap-2">
                          {version.data.lines
                            .filter((line) => line.line_type === "SOURCE_SUM")
                            .map((line) => (
                              <Button
                                key={line.code}
                                size="sm"
                                prominence={
                                  line.code === lineCode
                                    ? "primary"
                                    : "secondary"
                                }
                                onClick={() => setLineCode(line.code)}
                              >
                                {getBusinessLabel(line.label)}
                              </Button>
                            ))}
                        </div>
                      )}
                    {category.key === "budgetPeriods" && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        <label className="flex flex-col gap-1">
                          <Text font="secondary-action" color="text-04">
                            {COPY.pending.dialog.startMonth}
                          </Text>
                          <InputTypeIn
                            type="month"
                            value={startMonth}
                            onChange={(event) =>
                              setStartMonth(event.target.value)
                            }
                            aria-label={COPY.pending.dialog.startMonth}
                          />
                        </label>
                        <label className="flex flex-col gap-1">
                          <Text font="secondary-action" color="text-04">
                            {COPY.pending.dialog.endMonth}
                          </Text>
                          <InputTypeIn
                            type="month"
                            value={endMonth}
                            onChange={(event) =>
                              setEndMonth(event.target.value)
                            }
                            aria-label={COPY.pending.dialog.endMonth}
                          />
                        </label>
                      </div>
                    )}
                    {category.key.startsWith("reconciliation") && (
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
                            {COPY.pending.decisions[value]}
                          </Button>
                        ))}
                      </div>
                    )}
                    <label className="flex flex-col gap-1">
                      <Text font="secondary-action" color="text-04">
                        {COPY.pending.dialog.reason}
                      </Text>
                      <InputTypeIn
                        value={reason}
                        onChange={(event) => setReason(event.target.value)}
                        placeholder={COPY.pending.dialog.reasonPlaceholder}
                        aria-label={COPY.pending.dialog.reason}
                      />
                    </label>
                  </section>
                )}

                {selectedCanEdit && (
                  <div
                    className={cn(
                      "rounded-12 p-3 flex flex-col gap-1",
                      confirming
                        ? "bg-status-warning-01"
                        : "bg-background-neutral-01"
                    )}
                  >
                    {confirming && (
                      <Text font="main-ui-action" color="text-05">
                        {COPY.pending.dialog.confirmTitle}
                      </Text>
                    )}
                    <Text font="secondary-body" color="text-04">
                      {COPY.pending.dialog.consequence(selected.record_count)}
                    </Text>
                  </div>
                )}
                {saved && (
                  <Text font="main-ui-body" color="status-success-05">
                    {COPY.pending.dialog.saved}
                  </Text>
                )}
                {actionError && (
                  <Text font="main-ui-body" color="status-error-05">
                    {COPY.pending.dialog.error}
                  </Text>
                )}

                <div className="flex flex-wrap gap-2 justify-end">
                  {selectedCanEdit &&
                    (category.key === "units" || category.key === "accounts") &&
                    (selected.candidate?.evidence === "EXACT_CODE" ||
                      selected.legacy_evidence) &&
                    !confirming && (
                      <Button
                        prominence="secondary"
                        disabled={!reason.trim() || busy}
                        onClick={reject}
                      >
                        {COPY.pending.dialog.reject}
                      </Button>
                    )}
                  <Button
                    prominence="tertiary"
                    onClick={() =>
                      confirming ? setConfirming(false) : setSelected(null)
                    }
                  >
                    {confirming
                      ? COPY.pending.dialog.back
                      : COPY.pending.dialog.close}
                  </Button>
                  {selectedCanEdit && !confirming && !saved && (
                    <Button
                      disabled={!reason.trim() || !hasDecisionTarget || busy}
                      onClick={() => setConfirming(true)}
                    >
                      {COPY.pending.dialog.review}
                    </Button>
                  )}
                  {selectedCanEdit && confirming && (
                    <Button disabled={busy} onClick={approve}>
                      {COPY.pending.dialog.confirm}
                    </Button>
                  )}
                </div>
              </div>
            </Modal.Body>
          </Modal.Content>
        </Modal>
      )}
    </ClosingFrame>
  );
}
