"use client";

import { useState } from "react";
import useSWR from "swr";
import type { Route } from "next";
import { useSearchParams } from "next/navigation";
import { Button, InputTypeIn, Text } from "@opal/components";
import {
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
  formatMonthName,
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
  CLASSIFICATION_KEYS,
  type Normalization,
  type Overview,
  type QueueCategory,
  type Structure,
  type Target,
  type Version,
  describeCategory,
  isReviewCategory,
  readinessUrl,
  rowRecordHint,
  rowSuggestion,
  rowTitle,
  triageOf,
} from "@/views/ton/PendingPage/model";

const PAGE = 100;

/** Classification first; it clears items in the other lists. */
const WORK_ORDER = [
  "units",
  "accounts",
  "amountBasis",
  "dreAssignment",
  "drePending",
  "review",
  "excludedRows",
  "reconciliation",
  "reconciliationAmbiguous",
  "budgetAccounts",
  "budgetUnits",
  "budgetPeriods",
];

/** Kind of case inside a category: the review rule, or what happened. */
function groupOf(row: BlockerRow): string | null {
  if (row.rule_title) return row.rule_title;
  const headline = getBusinessLabel(row.evidence ?? "")
    .split(/[.(]/)[0]
    ?.trim();
  return headline ? headline : null;
}

const TRIAGE_TONE = {
  evidence: "brand",
  decision: "warning",
  data: "neutral",
} as const;

function rowKey(row: BlockerRow): string {
  return `${row.source_id}:${row.source_key}:${row.item_id}:${row.account_id}:${row.occurrence_id ?? ""}`;
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
    batch?: BlockerRow[];
    category: QueueCategory;
    scope: DecisionScope;
  } | null>(null);
  const [selection, setSelection] = useState<string[]>([]);
  const [ruleFilter, setRuleFilter] = useState<string | null>(null);
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
    // Work order: what classification settles first, then the review of the
    // NG rows, then the comparison with billing, which depends on both.
    const order = WORK_ORDER;
    return [...known, ...extra]
      .filter((item) => item.count > 0 || item.blocker === blockerSelection)
      .sort(
        (a, b) =>
          (order.indexOf(a.key) + 1 || order.length + 1) -
          (order.indexOf(b.key) + 1 || order.length + 1)
      );
  })();

  const category: QueueCategory | undefined =
    categories.find((item) => item.blocker === blockerSelection) ??
    // Start where the work starts: the first category in work order.
    categories.find((item) => !item.noActual) ??
    categories[0];

  const blockerUrl =
    scopeReady && category && runId && version.data
      ? `/api/ton/financial-domain/normalizations/${runId}/readiness/blockers/${category.blocker}?structure_version_id=${version.data.id}&limit=${PAGE}&offset=${offset}&search=${encodeURIComponent(search)}${unitId ? `&unit_id=${unitId}` : ""}${period ? `&period=${period.scope.period}` : ""}`
      : null;
  const blockers = useSWR<BlockerPage>(blockerUrl, errorHandlingFetcher);
  const allRows = blockers.data?.rows ?? [];
  // Review cases come from several rules; each is decided its own way.
  const rules = Array.from(
    allRows.reduce((counts, row) => {
      const group = groupOf(row);
      if (group) counts.set(group, (counts.get(group) ?? 0) + 1);
      return counts;
    }, new Map<string, number>())
  );
  const unmappedCount = allRows.filter((row) =>
    (groupOf(row) ?? "").startsWith("Registro sem unidade ou natureza")
  ).length;
  const pageRows = allRows.filter(
    (row) => !ruleFilter || groupOf(row) === ruleFilter
  );
  // Review and reconciliation cases take the same decision in bulk.
  const selectable =
    !!category &&
    (isReviewCategory(category) || category.key.startsWith("reconciliation"));
  const selectedRows = pageRows.filter((row) =>
    selection.includes(rowKey(row))
  );

  function chooseCategory(blocker: string) {
    setBlockerSelection(blocker);
    setOffset(0);
    setDialog(null);
    setSelection([]);
    setRuleFilter(null);
  }

  function openRow(
    row: BlockerRow,
    target = category,
    batch?: BlockerRow[]
  ) {
    const currentVersion = version.data;
    if (!target || !runId || !structureId || !currentVersion || !period) return;
    // Pin the category so the queue stays on it after it empties.
    setBlockerSelection(target.blocker);
    setDialog((current) => ({
      key: (current?.key ?? 0) + 1,
      row,
      batch,
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
    setSelection([]);
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
    const other = categories.find(
      (item) => item.blocker !== category?.blocker && item.count > 0
    );
    if (!other || !runId || !version.data) {
      setDialog(null);
      if (other) chooseCategory(other.blocker);
      return;
    }
    // Open the first case of the next category instead of a bare list.
    chooseCategory(other.blocker);
    try {
      const first = await errorHandlingFetcher<BlockerPage>(
        `/api/ton/financial-domain/normalizations/${runId}/readiness/blockers/${other.blocker}?structure_version_id=${version.data.id}&limit=1&offset=0${unitId ? `&unit_id=${unitId}` : ""}${period ? `&period=${period.scope.period}` : ""}`
      );
      const row = first.rows[0];
      if (row) openRow(row, other);
    } catch {
      // The list of the new category is already on screen.
    }
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
        <TonCard className="flex flex-wrap items-center justify-between gap-3 p-5">
          <Text font="main-ui-body" color="status-error-05">
            {COPY.pending.loadError}
          </Text>
          <Button
            prominence="secondary"
            icon={SvgRefreshCw}
            onClick={() => {
              void runs.mutate();
              void structures.mutate();
              void version.mutate();
              void overview.mutate();
              void blockers.mutate();
            }}
          >
            {COPY.pending.retry}
          </Button>
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
                  {blockers.data && blockers.data.total !== category.count
                    ? COPY.pending.casesAndEntries(
                        blockers.data.total,
                        category.count
                      )
                    : category.action}
                </Text>
              </div>
            </div>
            {category.noActual && blockers.data && period && (
              <MissingActualsGuide
                page={blockers.data}
                closingPeriod={period.scope.period}
              />
            )}
            {CLASSIFICATION_KEYS.includes(category.key) && (
              <div className="ton-guide">
                <Text font="main-ui-body" color="text-04">
                  {COPY.pending.classificationGuide[category.key] ?? ""}
                </Text>
                <span className="shrink-0">
                  <Button
                    href={"/ton/classificacao?voltar=pendencias" as Route}
                    rightIcon={SvgArrowRight}
                  >
                    {COPY.pending.classificationCta}
                  </Button>
                </span>
              </div>
            )}
            {category.key.startsWith("reconciliation") && unmappedCount > 0 && (
              <div className="ton-guide">
                <Text font="main-ui-body" color="text-04">
                  {COPY.pending.unmappedGuide(unmappedCount)}
                </Text>
                <span className="shrink-0">
                  <Button
                    prominence="secondary"
                    href={"/ton/classificacao?voltar=pendencias" as Route}
                    rightIcon={SvgArrowRight}
                  >
                    {COPY.pending.classificationCta}
                  </Button>
                </span>
              </div>
            )}
            {rules.length > 1 && (
              <div
                className="flex flex-wrap gap-1.5"
                role="group"
                aria-label={COPY.pending.categoriesLabel}
              >
                <button
                  type="button"
                  aria-pressed={ruleFilter === null}
                  className="ton-chip ton-focusable"
                  onClick={() => {
                    setRuleFilter(null);
                    setSelection([]);
                  }}
                >
                  {`${COPY.pending.allRules} · ${allRows.length}`}
                </button>
                {rules.map(([title, count]) => (
                  <button
                    key={title}
                    type="button"
                    aria-pressed={ruleFilter === title}
                    className="ton-chip ton-focusable"
                    onClick={() => {
                      setRuleFilter(title);
                      setSelection([]);
                    }}
                  >
                    {`${getBusinessLabel(title)} · ${count}`}
                  </button>
                ))}
              </div>
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
            {!category.noActual && selectable && selectedRows.length > 0 && (
              <div className="ton-bulk-bar" role="region" aria-live="polite">
                <Text font="main-ui-action" color="text-05">
                  {COPY.pending.selected(selectedRows.length)}
                </Text>
                <span className="flex-1" />
                <Button
                  size="md"
                  prominence="tertiary"
                  onClick={() => setSelection([])}
                >
                  {COPY.pending.clearSelection}
                </Button>
                <Button
                  size="md"
                  rightIcon={SvgArrowRight}
                  onClick={() => {
                    const [first] = selectedRows;
                    if (first) openRow(first, category, selectedRows);
                  }}
                >
                  {COPY.pending.decideSelected}
                </Button>
              </div>
            )}
            {!category.noActual && (
              <div className="ton-queue-table-wrap">
                <table className="ton-queue-table w-full border-collapse">
                  <thead>
                    <tr>
                      {selectable && (
                        <th scope="col" className="w-10">
                          <input
                            type="checkbox"
                            aria-label={COPY.pending.selectAll}
                            checked={
                              pageRows.length > 0 &&
                              pageRows.every((row) =>
                                selection.includes(rowKey(row))
                              )
                            }
                            onChange={(event) =>
                              setSelection(
                                event.target.checked
                                  ? pageRows.map(rowKey)
                                  : []
                              )
                            }
                          />
                        </th>
                      )}
                      <th scope="col" className="text-start">
                        {COPY.pending.columns.item}
                      </th>
                      <th scope="col" className="text-start">
                        {COPY.pending.columns.period}
                      </th>
                      <th scope="col" className="text-end">
                        {COPY.pending.columns.amount}
                      </th>
                      <th scope="col">
                        <span className="sr-only">{COPY.pending.decide}</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {pageRows.map((row) => {
                      const key = rowKey(row);
                      const hint = CLASSIFICATION_KEYS.includes(category.key)
                        ? null
                        : rowRecordHint(row);
                      const amount =
                        rowAmount(row) ??
                        (row.record_count > 1
                          ? COPY.pending.entries(row.record_count)
                          : null);
                      const accountish = CLASSIFICATION_KEYS.includes(
                        category.key
                      );
                      // An account reads by code and name, as in the NG.
                      const title =
                        hint ??
                        (accountish ? row.records[0]?.account : null) ??
                        rowTitle(row, category);
                      // The kind of case, once; nothing when a chip filters it.
                      const detail = accountish
                        ? ""
                        : row.candidate || row.legacy_evidence
                          ? rowSuggestion(row)
                          : ruleFilter
                            ? ""
                            : groupOf(row) === title
                              ? ""
                              : (groupOf(row) ?? "");
                      const checked = selection.includes(key);
                      return (
                        <tr
                          key={key}
                          aria-selected={checked || undefined}
                          onClick={() => openRow(row)}
                        >
                          {selectable && (
                            <td onClick={(event) => event.stopPropagation()}>
                              <input
                                type="checkbox"
                                aria-label={COPY.pending.selectRow(title)}
                                checked={checked}
                                onChange={(event) =>
                                  setSelection((old) =>
                                    event.target.checked
                                      ? [...old, key]
                                      : old.filter((item) => item !== key)
                                  )
                                }
                              />
                            </td>
                          )}
                          <td className="ton-queue-item">
                            <span className="flex flex-wrap items-center gap-2">
                              <Text font="main-ui-action" color="text-05">
                                {title}
                              </Text>
                              {triageOf(row, category) === "evidence" && (
                                <StatusPill tone={TRIAGE_TONE.evidence}>
                                  {COPY.decisionLoop.triage.evidence}
                                </StatusPill>
                              )}
                            </span>
                            {detail && (
                              <span className="ton-queue-detail">{detail}</span>
                            )}
                          </td>
                          <td className="whitespace-nowrap">
                            <Text font="secondary-body" color="text-04">
                              {row.periods
                                .map((item) => formatMonthName(item))
                                .join(", ") || "—"}
                            </Text>
                          </td>
                          <td className="text-end whitespace-nowrap ton-queue-amount">
                            {amount ?? "—"}
                          </td>
                          <td className="text-end">
                            <Button
                              size="sm"
                              prominence="secondary"
                              rightIcon={SvgArrowRight}
                              onClick={(event) => {
                                event.stopPropagation();
                                openRow(row);
                              }}
                            >
                              {COPY.pending.decide}
                            </Button>
                          </td>
                        </tr>
                      );
                    })}
                    {blockers.data?.rows.length === 0 && (
                      <tr>
                        <td colSpan={selectable ? 5 : 4} className="p-4">
                          <Text font="main-ui-body" color="text-03">
                            {COPY.pending.empty}
                          </Text>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
            {(blockers.data?.total ?? 0) > PAGE && (
              <div className="flex items-center justify-between">
                <Button
                  size="md"
                  prominence="secondary"
                  disabled={offset === 0}
                  onClick={() => {
                    setOffset(Math.max(0, offset - PAGE));
                    setSelection([]);
                  }}
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
                  onClick={() => {
                    setOffset(offset + PAGE);
                    setSelection([]);
                  }}
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
          batch={dialog.batch}
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
