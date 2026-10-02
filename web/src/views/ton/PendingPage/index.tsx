"use client";

import { useState } from "react";
import useSWR from "swr";
import { useSearchParams } from "next/navigation";
import { Button, InputTypeIn, Text } from "@opal/components";
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
import {
  COPY,
  formatCurrency,
  formatDateTime,
  formatPeriod,
} from "@/lib/ton/copy";
import {
  PENDING_CATEGORIES,
  postTonJson,
  useDecisionLog,
  useReadinessChanges,
} from "@/lib/ton/decisions";
import ClosingFrame from "@/views/ton/components/ClosingFrame";
import DecisionLogList from "@/views/ton/components/DecisionLogList";
import ReadinessDelta from "@/views/ton/components/ReadinessDelta";
import {
  CardHeader,
  IconTile,
  LoadingBlock,
  StatusPill,
  TonCard,
} from "@/views/ton/components/ui";
import MissingActualsGuide from "@/views/ton/PendingPage/MissingActualsGuide";
import DecisionDialog, {
  type DecisionScope,
} from "@/views/ton/PendingPage/DecisionDialog";
import {
  type BlockerPage,
  type BlockerRow,
  CATEGORY_PARAM,
  type Normalization,
  type Overview,
  type QueueCategory,
  type Structure,
  type Target,
  type Version,
  describeCategory,
  readinessUrl,
  rowDetail,
  rowPeriods,
  rowRecordHint,
  rowSuggestion,
  rowTitle,
  triageOf,
} from "@/views/ton/PendingPage/model";

const PAGE = 25;

const TRIAGE_TONE = {
  evidence: "brand",
  decision: "warning",
  data: "neutral",
} as const;

function rowKey(row: BlockerRow): string {
  return `${row.source_id}:${row.source_key}:${row.item_id}:${row.account_id}`;
}

function rowAmount(row: BlockerRow): string | null {
  const record = row.records[0];
  if (!record || row.record_count !== 1) return null;
  const value = record.movement_amount ?? record.service_amount;
  return value ? formatCurrency(value) : null;
}

/** Recompute applies decisions recorded after the base was built. */
function PendingDecisionsBanner({
  count,
  canRecompute,
  busy,
  onApply,
}: {
  count: number;
  canRecompute: boolean;
  busy: boolean;
  onApply: () => void;
}) {
  return (
    <TonCard className="flex flex-wrap items-center gap-3 p-4">
      <IconTile icon={SvgRefreshCw} tone="warning" size="sm" />
      <div className="flex flex-col gap-0.5 flex-1 min-w-0">
        <Text font="main-ui-action" color="text-05">
          {COPY.decisionLoop.pendingBanner(count)}
        </Text>
        {!canRecompute && (
          <Text font="secondary-body" color="text-03">
            {COPY.decisionLoop.applyNeedsPermission}
          </Text>
        )}
      </div>
      {canRecompute && (
        <Button onClick={onApply} disabled={busy} icon={SvgRefreshCw}>
          {busy ? COPY.decisionLoop.applying : COPY.decisionLoop.applyNow}
        </Button>
      )}
    </TonCard>
  );
}

function LastUpdate({
  runId,
  versionId,
  unitId,
  period,
}: {
  runId: string;
  versionId: string;
  unitId?: string;
  period: string;
}) {
  const changes = useReadinessChanges(runId, versionId, unitId);
  const change = changes.data?.periods.find((item) => item.period === period);
  if (!changes.data?.previous_started_at || !change) return null;
  return (
    <TonCard className="flex flex-col gap-3 p-4" labelledBy="ton-last-update">
      <CardHeader
        id="ton-last-update"
        title={COPY.decisionLoop.changes.title}
        description={COPY.decisionLoop.changes.since(
          formatDateTime(changes.data.previous_started_at)
        )}
      />
      <ReadinessDelta
        before={change.blockers_before}
        after={change.blockers_after}
        statusBefore={change.status_before}
        statusAfter={change.status_after}
        changedOnly
      />
    </TonCard>
  );
}

export default function PendingPage() {
  const searchParams = useSearchParams();
  const { user } = useUser();
  const permissions = user?.effective_permissions ?? [];
  const access = {
    canManage: hasPermission(permissions, Permission.MANAGE_TON_SOURCES),
    canConfigure: hasPermission(
      permissions,
      Permission.FULL_ADMIN_PANEL_ACCESS
    ),
    canRecompute: hasPermission(permissions, Permission.IMPORT_TON_SOURCES),
  };
  const closing = useTonClosing();
  const decisions = useDecisionLog();
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
  // The dialog keeps the scope it opened with: a decision replaces the base,
  // and the live queue reloads underneath it while the result is shown.
  const [dialog, setDialog] = useState<{
    key: number;
    row: BlockerRow;
    category: QueueCategory;
    scope: DecisionScope;
  } | null>(null);
  const selected = dialog?.row ?? null;
  const [applying, setApplying] = useState(false);
  const [applyFailed, setApplyFailed] = useState(false);

  const runs = useSWR<Normalization[]>(
    "/api/ton/financial-domain/normalizations?limit=20",
    errorHandlingFetcher
  );
  const structures = useSWR<Structure[]>(
    "/api/ton/dre/structures?limit=100",
    errorHandlingFetcher
  );
  const visibleUnits = useSWR<Target[]>(
    !access.canConfigure ? "/api/ton/financial-domain/units?limit=100" : null,
    errorHandlingFetcher
  );
  const unitId = access.canConfigure
    ? undefined
    : unitSelection || visibleUnits.data?.[0]?.id;
  // An explicit base comes from a deep link; after a recompute the newest wins.
  const runId = runSelection || runs.data?.[0]?.id;
  const structureId = structureSelection || structures.data?.[0]?.id;
  const version = useSWR<Version>(
    structureId
      ? `/api/ton/dre/structures/${structureId}/latest-version`
      : null,
    errorHandlingFetcher
  );
  const scopeReady =
    !!runId && !!version.data && (access.canConfigure || !!unitId);
  const overview = useSWR<Overview>(
    scopeReady && runId && version.data
      ? readinessUrl(runId, version.data.id, unitId)
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

  const categories: QueueCategory[] = (() => {
    const known = PENDING_CATEGORIES.map((item) =>
      describeCategory(
        item.key,
        item.blocker,
        periodBlockers[item.blocker] ?? 0
      )
    );
    const extra = Object.keys(periodBlockers)
      .filter(
        (blocker) =>
          !PENDING_CATEGORIES.some((item) => item.blocker === blocker)
      )
      .map((blocker) =>
        describeCategory("other", blocker, periodBlockers[blocker] ?? 0)
      );
    return [...known, ...extra].filter(
      (item) => item.count > 0 || item.blocker === blockerSelection
    );
  })();

  const category: QueueCategory | undefined =
    categories.find((item) => item.blocker === blockerSelection) ??
    // Default to the largest category that needs a human decision.
    [...categories].sort(
      (a, b) => Number(a.noActual) - Number(b.noActual) || b.count - a.count
    )[0];

  const blockerUrl =
    scopeReady && category && runId && version.data
      ? `/api/ton/financial-domain/normalizations/${runId}/readiness/blockers/${category.blocker}?structure_version_id=${version.data.id}&limit=${PAGE}&offset=${offset}&search=${encodeURIComponent(search)}${unitId ? `&unit_id=${unitId}` : ""}`
      : null;
  const blockers = useSWR<BlockerPage>(blockerUrl, errorHandlingFetcher);

  function chooseCategory(blocker: string) {
    setBlockerSelection(blocker);
    setOffset(0);
    setDialog(null);
  }

  function openRow(row: BlockerRow, target = category) {
    const currentVersion = version.data;
    if (!target || !runId || !structureId || !currentVersion || !period) return;
    // Pin the category so the queue stays on it after it empties.
    setBlockerSelection(target.blocker);
    setDialog((current) => ({
      key: (current?.key ?? 0) + 1,
      row,
      category: target,
      scope: {
        runId,
        structureId,
        version: currentVersion,
        unitId,
        period,
      },
    }));
  }

  async function refreshAfterDecision() {
    // Follow the newest base: the decision may have produced it.
    setRunSelection("");
    await Promise.all([
      runs.mutate(),
      version.mutate(),
      closing.mutate(),
      decisions.mutate(),
    ]);
    await Promise.all([overview.mutate(), blockers.mutate()]);
  }

  async function openNext() {
    const current = selected ? rowKey(selected) : null;
    const page = await blockers.mutate();
    const next = page?.rows.find((row) => rowKey(row) !== current);
    if (next) {
      openRow(next);
      return;
    }
    setDialog(null);
    const other = categories.find(
      (item) => item.blocker !== category?.blocker && item.count > 0
    );
    if (other) chooseCategory(other.blocker);
  }

  async function applyPendingDecisions() {
    if (!runId) return;
    setApplying(true);
    setApplyFailed(false);
    try {
      await postTonJson(
        `/api/ton/financial-domain/normalizations/${runId}/recompute`,
        {}
      );
      await refreshAfterDecision();
    } catch {
      setApplyFailed(true);
    } finally {
      setApplying(false);
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
  const periodLabel = period ? formatPeriod(period.scope.period) : null;
  const pendingDecisions = decisions.data?.pending_decisions ?? 0;
  const ready = !loading && !failed && scopeReady;

  return (
    <ClosingFrame
      active="pending"
      title={COPY.pending.title}
      description={COPY.pending.description}
      wide
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

      {ready && period && (
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

      {ready && pendingDecisions > 0 && (
        <PendingDecisionsBanner
          count={pendingDecisions}
          canRecompute={access.canRecompute}
          busy={applying}
          onApply={applyPendingDecisions}
        />
      )}
      {applyFailed && (
        <Text font="main-ui-body" color="status-error-05">
          {COPY.pending.dialog.error}
        </Text>
      )}

      {ready && category && (
        <div className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-5 items-start">
          <div className="flex flex-col gap-5 lg:sticky lg:top-4">
            <nav
              aria-label={COPY.pending.categoriesLabel}
              className="ton-card flex flex-col p-2"
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
            {runId && version.data && period && (
              <LastUpdate
                runId={runId}
                versionId={version.data.id}
                unitId={unitId}
                period={period.scope.period}
              />
            )}
            <TonCard
              className="hidden lg:flex flex-col gap-3 p-4"
              labelledBy="ton-recent-decisions"
            >
              <CardHeader
                id="ton-recent-decisions"
                title={COPY.decisionLoop.log.title}
              />
              <DecisionLogList
                entries={decisions.data?.entries ?? []}
                limit={4}
              />
            </TonCard>
          </div>

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
            {category.noActual && blockers.data && period && (
              <MissingActualsGuide
                page={blockers.data}
                closingPeriod={period.scope.period}
              />
            )}
            {!category.noActual && (blockers.data?.total ?? 0) > 5 && (
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
            {!category.noActual && (
              <ul className="flex flex-col divide-y divide-border-01 border border-01 rounded-12">
                {(blockers.data?.rows ?? []).map((row) => {
                  const hint = rowRecordHint(row);
                  const amount = rowAmount(row);
                  return (
                    <li
                      key={rowKey(row)}
                      className="flex flex-wrap items-center gap-3 p-3.5"
                    >
                      <IconTile
                        icon={SvgAlertTriangle}
                        tone="warning"
                        size="sm"
                      />
                      <div className="flex flex-col gap-1 min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <Text font="main-ui-action" color="text-05">
                            {rowTitle(row, category)}
                          </Text>
                          <StatusPill
                            tone={TRIAGE_TONE[triageOf(row, category)]}
                          >
                            {COPY.decisionLoop.triage[triageOf(row, category)]}
                          </StatusPill>
                        </div>
                        <Text font="secondary-body" color="text-03">
                          {[
                            hint,
                            amount,
                            COPY.pending.affected(row.record_count),
                            rowPeriods(row),
                          ]
                            .filter(Boolean)
                            .join(" · ")}
                        </Text>
                        <Text font="secondary-body" color="text-03">
                          {row.evidence &&
                          !row.candidate &&
                          !row.legacy_evidence
                            ? rowDetail(row, category)
                            : rowSuggestion(row)}
                        </Text>
                      </div>
                      <Button
                        size="md"
                        prominence="secondary"
                        rightIcon={SvgArrowRight}
                        onClick={() => openRow(row)}
                      >
                        {category.noActual
                          ? COPY.pending.analyze
                          : COPY.pending.decide}
                      </Button>
                    </li>
                  );
                })}
                {blockers.data?.rows.length === 0 && (
                  <li className="p-4">
                    <Text font="main-ui-body" color="text-03">
                      {COPY.pending.empty}
                    </Text>
                  </li>
                )}
              </ul>
            )}
            {(blockers.data?.total ?? 0) > PAGE && (
              <div className="flex items-center justify-between">
                <Button
                  size="md"
                  prominence="secondary"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - PAGE))}
                >
                  {COPY.pending.previous}
                </Button>
                <Text font="main-ui-muted" color="text-03">
                  {COPY.pending.pageRange(
                    offset + 1,
                    Math.min(offset + PAGE, blockers.data?.total ?? 0),
                    blockers.data?.total ?? 0
                  )}
                </Text>
                <Button
                  size="md"
                  prominence="secondary"
                  disabled={offset + PAGE >= (blockers.data?.total ?? 0)}
                  onClick={() => setOffset(offset + PAGE)}
                >
                  {COPY.pending.next}
                </Button>
              </div>
            )}
          </TonCard>
        </div>
      )}

      {ready && !category && (
        <TonCard className="flex items-center gap-3 p-5">
          <SvgCheckCircle size={18} className="ton-brand-text" />
          <Text font="main-ui-body" color="text-04">
            {COPY.home.attention.empty}
          </Text>
        </TonCard>
      )}

      {ready && (
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
                  {formatDateTime(run.started_at)}
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
            {!access.canConfigure && (
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
                      setDialog(null);
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

      {dialog && (
        <DecisionDialog
          key={dialog.key}
          row={dialog.row}
          category={dialog.category}
          scope={dialog.scope}
          access={access}
          onApplied={refreshAfterDecision}
          onNext={() => void openNext()}
          onClose={() => setDialog(null)}
        />
      )}
    </ClosingFrame>
  );
}
