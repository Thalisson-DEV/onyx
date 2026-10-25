"use client";

import { useState } from "react";
import useSWR from "swr";
import type { Route } from "next";
import { useSearchParams } from "next/navigation";
import { Button, Text } from "@opal/components";
import {
  SvgArrowRight,
  SvgCheckCircle,
  SvgClock,
  SvgRefreshCw,
} from "@opal/icons";
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
  TonCard,
} from "@/views/ton/components/ui";
import { BatchBar, BatchButton } from "@/views/ton/components/pattern";
import {
  Drawer,
  FilterBar,
  FilterField,
  Segmented,
  Tag,
  TonMark,
  ViewTabs,
  type FilterToken,
} from "@/views/ton/components/kit";
import { AskTonRowButton, useAskTonPage } from "@/views/ton/ask/AskTon";
import { Select } from "@/views/ton/PayablesPage/fields";
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

function rowKey(row: BlockerRow): string {
  return `${row.source_id}:${row.source_key}:${row.item_id}:${row.account_id}:${row.occurrence_id ?? ""}`;
}

const ANY = "__any";

function amountOf(row: BlockerRow): number {
  const record = row.records[0];
  if (!record) return 0;
  return Number(record.movement_amount ?? record.service_amount ?? 0);
}

/** What the TON suggests for the case, without the "Sugestão do TON" prefix. */
function suggestionText(row: BlockerRow): string | null {
  if (row.candidate) return row.candidate.code;
  if (row.legacy_evidence) return row.legacy_evidence.suggested_code;
  if (row.line_candidate) return row.line_candidate;
  return null;
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
  const [historyOpen, setHistoryOpen] = useState(false);
  const [sortBy, setSortBy] = useState<"amount" | "order">("amount");
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

  function openRow(row: BlockerRow, target = category, batch?: BlockerRow[]) {
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
  const sorted =
    sortBy === "amount"
      ? [...pageRows].sort(
          (a, b) => Math.abs(amountOf(b)) - Math.abs(amountOf(a))
        )
      : pageRows;
  const tokens: FilterToken[] = ruleFilter
    ? [
        {
          key: "rule",
          label: COPY.pending.ruleLabel,
          value: getBusinessLabel(ruleFilter),
          onRemove: () => {
            setRuleFilter(null);
            setSelection([]);
          },
        },
      ]
    : [];

  useAskTonPage(
    ready && period
      ? {
          screen: COPY.pending.title,
          chips: [
            COPY.closing.eyebrow,
            periodLabel ?? "",
            ...(category
              ? [`${COPY.pending.categoriesLabel}: ${category.label}`]
              : []),
            COPY.pending.thisScreen,
          ],
          details: [
            `Período ${period.scope.period} · ${period.status === "READY" ? "pronto para publicar" : "não pronto"} · ${totalPending} itens pendentes`,
            ...categories.map((item) => `${item.label}: ${item.count}`),
            ...sorted
              .slice(0, 30)
              .map(
                (row) =>
                  `${rowTitle(row, category ?? categories[0]!)} · ${row.periods.join(", ")} · ${rowAmount(row) ?? ""} · ${suggestionText(row) ?? "sem sugestão"}`
              ),
          ],
          opener: COPY.pending.askOpener(
            periodLabel ?? "",
            totalPending,
            category?.label ?? ""
          ),
          suggestions: COPY.pending.askSuggestions,
        }
      : null
  );

  return (
    <ClosingFrame
      active="pending"
      title={COPY.pending.title}
      description={COPY.pending.description}
      status={
        ready && period ? (
          <Tag tone={period.status === "READY" ? "ok" : "danger"}>
            {period.status === "READY"
              ? COPY.pending.readyTag(periodLabel ?? "")
              : COPY.pending.notReadyTag(periodLabel ?? "")}
          </Tag>
        ) : undefined
      }
      actions={
        ready ? (
          <Button
            prominence="tertiary"
            icon={SvgClock}
            onClick={() => setHistoryOpen(true)}
          >
            {COPY.pending.history}
          </Button>
        ) : undefined
      }
    >
      {loading && <LoadingBlock label={COPY.common.loading} />}
      {failed && (
        <div className="tn-card flex flex-wrap items-center justify-between gap-3 p-4">
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
        </div>
      )}
      {!loading && !failed && !scopeReady && (
        <div className="tn-card p-4">
          <Text font="main-ui-body" color="text-03">
            {COPY.pending.noBase}
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
        <>
          <ViewTabs
            label={COPY.pending.categoriesLabel}
            value={category.blocker}
            onChange={chooseCategory}
            views={categories.map((item) => ({
              key: item.blocker,
              label: item.label,
              count: item.count,
              tone: item.count > 0 ? ("warn" as const) : undefined,
            }))}
          />

          <section className="tn-card" aria-label={category.label}>
            <div className="flex flex-wrap items-start gap-3 px-4 pt-3.5 pb-1">
              <div className="flex flex-col gap-0.5 min-w-0 flex-1">
                <Text as="h2" font="main-ui-action" color="text-05">
                  {category.label}
                </Text>
                <Text font="secondary-body" color="text-03">
                  {blockers.data && blockers.data.total !== category.count
                    ? `${category.description} ${COPY.pending.casesAndEntries(blockers.data.total, category.count)}.`
                    : `${category.description} ${category.action}`}
                </Text>
              </div>
            </div>
            {category.noActual && blockers.data && period && (
              <div className="px-4 pb-3">
                <MissingActualsGuide
                  page={blockers.data}
                  closingPeriod={period.scope.period}
                />
              </div>
            )}
            {CLASSIFICATION_KEYS.includes(category.key) && (
              <div className="px-4 pb-3">
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
              </div>
            )}
            {category.key.startsWith("reconciliation") && unmappedCount > 0 && (
              <div className="px-4 pb-3">
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
              </div>
            )}

            {!category.noActual && (
              <FilterBar
                search={{
                  value: search,
                  onChange: (value) => {
                    setSearch(value);
                    setOffset(0);
                  },
                  placeholder: COPY.pending.search,
                }}
                tokens={tokens}
                onClear={() => {
                  setRuleFilter(null);
                  setSelection([]);
                }}
                end={
                  <Segmented
                    label={COPY.pending.sortLabel}
                    lead={COPY.pending.sortLabel}
                    value={sortBy}
                    onChange={setSortBy}
                    options={[
                      { key: "amount", label: COPY.pending.sortAmount },
                      { key: "order", label: COPY.pending.sortOrder },
                    ]}
                  />
                }
                panel={
                  <>
                    {rules.length > 1 && (
                      <FilterField label={COPY.pending.ruleLabel} span={2}>
                        <Select
                          label={COPY.pending.ruleLabel}
                          placeholder={COPY.pending.allRules}
                          value={ruleFilter ?? ANY}
                          options={[
                            {
                              value: ANY,
                              label: `${COPY.pending.allRules} · ${allRows.length}`,
                            },
                            ...rules.map(([title, count]) => ({
                              value: title,
                              label: `${getBusinessLabel(title)} · ${count}`,
                            })),
                          ]}
                          onChange={(value) => {
                            setRuleFilter(value === ANY ? null : value);
                            setSelection([]);
                          }}
                        />
                      </FilterField>
                    )}
                    <FilterField label={COPY.pending.advancedBase} span={2}>
                      <Select
                        label={COPY.pending.advancedBase}
                        placeholder={COPY.pending.advancedBase}
                        value={runId ?? ""}
                        options={(runs.data ?? []).map((run) => ({
                          value: run.id,
                          label: formatDateTime(run.started_at),
                        }))}
                        onChange={(value) => {
                          setRunSelection(value);
                          setOffset(0);
                        }}
                      />
                    </FilterField>
                    <FilterField
                      label={COPY.pending.advancedStructure}
                      span={2}
                    >
                      <Select
                        label={COPY.pending.advancedStructure}
                        placeholder={COPY.pending.advancedStructure}
                        value={structureId ?? ""}
                        options={(structures.data ?? []).map((structure) => ({
                          value: structure.id,
                          label: getBusinessLabel(structure.label),
                        }))}
                        onChange={setStructureSelection}
                      />
                    </FilterField>
                    {!access.canConfigure && (
                      <FilterField label={COPY.pending.advancedUnit} span={2}>
                        <Select
                          label={COPY.pending.advancedUnit}
                          placeholder={COPY.pending.advancedUnit}
                          value={unitId ?? ""}
                          options={(visibleUnits.data ?? []).map((unit) => ({
                            value: unit.id,
                            label: getBusinessLabel(unit.name ?? unit.code),
                          }))}
                          onChange={(value) => {
                            setUnitSelection(value);
                            setOffset(0);
                            setDialog(null);
                          }}
                        />
                      </FilterField>
                    )}
                  </>
                }
              />
            )}

            {blockers.isLoading && (
              <div className="px-4 pb-4">
                <LoadingBlock label={COPY.common.loading} />
              </div>
            )}
            {!category.noActual && (
              <div className="overflow-x-auto border-t border-01">
                <table className="tp-table">
                  <thead>
                    <tr>
                      {selectable && (
                        <th scope="col" className="tp-check">
                          <input
                            type="checkbox"
                            className="tp-checkbox"
                            aria-label={COPY.pending.selectAll}
                            checked={
                              pageRows.length > 0 &&
                              pageRows.every((row) =>
                                selection.includes(rowKey(row))
                              )
                            }
                            onChange={(event) =>
                              setSelection(
                                event.target.checked ? pageRows.map(rowKey) : []
                              )
                            }
                          />
                        </th>
                      )}
                      <th scope="col">{COPY.pending.columns.item}</th>
                      <th scope="col">{COPY.pending.columns.period}</th>
                      <th scope="col" className="tp-end">
                        {COPY.pending.columns.amount}
                      </th>
                      <th scope="col">{COPY.pending.columns.suggestion}</th>
                      <th scope="col">
                        <span className="sr-only">{COPY.pending.decide}</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {sorted.map((row) => {
                      const key = rowKey(row);
                      const accountish = CLASSIFICATION_KEYS.includes(
                        category.key
                      );
                      const hint = accountish ? null : rowRecordHint(row);
                      const amount =
                        rowAmount(row) ??
                        (row.record_count > 1
                          ? COPY.pending.entries(row.record_count)
                          : null);
                      // An account reads by code and name, as in the NG.
                      const title =
                        hint ??
                        (accountish ? row.records[0]?.account : null) ??
                        rowTitle(row, category);
                      const kind =
                        accountish || ruleFilter || groupOf(row) === title
                          ? ""
                          : (groupOf(row) ?? "");
                      const suggestion = suggestionText(row);
                      const checked = selection.includes(key);
                      return (
                        <tr
                          key={key}
                          className="tp-row"
                          data-selected={checked ? "true" : undefined}
                          onClick={() => openRow(row)}
                        >
                          {selectable && (
                            <td
                              className="tp-check"
                              onClick={(event) => event.stopPropagation()}
                            >
                              <input
                                type="checkbox"
                                className="tp-checkbox"
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
                          <td className="tp-wrap">
                            <span className="flex flex-col">
                              <span className="flex flex-wrap items-center gap-2">
                                <span className="tp-strong">{title}</span>
                                {triageOf(row, category) === "evidence" && (
                                  <Tag tone="info">
                                    {COPY.decisionLoop.triage.evidence}
                                  </Tag>
                                )}
                              </span>
                              {kind && <span className="tp-muted">{kind}</span>}
                            </span>
                          </td>
                          <td className="tp-muted">
                            {row.periods
                              .map((item) => formatMonthName(item))
                              .join(", ") || "—"}
                          </td>
                          <td className="tp-end tp-strong tn-num">
                            {amount ?? "—"}
                          </td>
                          <td>
                            {suggestion && <TonMark>{suggestion}</TonMark>}
                          </td>
                          <td
                            className="tp-end"
                            onClick={(event) => event.stopPropagation()}
                          >
                            <span className="inline-flex items-center gap-1">
                              <AskTonRowButton
                                label={title}
                                context={{
                                  screen: title,
                                  chips: [
                                    COPY.pending.title,
                                    category.label,
                                    amount ? `${title} · ${amount}` : title,
                                  ],
                                  details: [
                                    `Pendência do fechamento (${category.label}, código ${category.blocker})`,
                                    `Item: ${title}${kind ? ` · ${kind}` : ""}`,
                                    `Meses: ${row.periods.join(", ") || "—"} · valor ${amount ?? "—"} · ${row.record_count} registros`,
                                    row.evidence
                                      ? `Evidência: ${getBusinessLabel(row.evidence)}`
                                      : "",
                                    suggestion
                                      ? `Sugestão do TON: ${suggestion}`
                                      : "Sem sugestão do TON",
                                    ...row.records
                                      .slice(0, 5)
                                      .map(
                                        (record) =>
                                          `Registro: ${[record.document, record.counterparty, record.account, record.movement_amount ?? record.service_amount].filter(Boolean).join(" · ")}`
                                      ),
                                  ].filter(Boolean),
                                  opener: COPY.pending.askRowOpener(
                                    title,
                                    suggestion
                                  ),
                                  suggestions: COPY.pending.askRowSuggestions,
                                }}
                              />
                              <Button
                                size="sm"
                                prominence="secondary"
                                rightIcon={SvgArrowRight}
                                onClick={() => openRow(row)}
                              >
                                {COPY.pending.decide}
                              </Button>
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                    {blockers.data?.rows.length === 0 && (
                      <tr>
                        <td colSpan={selectable ? 6 : 5}>
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
              <div className="flex items-center justify-between gap-2 px-4 py-3 border-t border-01">
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
          </section>

          {!category.noActual && selectable && selectedRows.length > 0 && (
            <BatchBar summary={COPY.pending.selected(selectedRows.length)}>
              <BatchButton
                label={COPY.pending.clearSelection}
                onClick={() => setSelection([])}
              />
              <BatchButton
                label={COPY.pending.decideSelected}
                primary
                onClick={() => {
                  const [first] = selectedRows;
                  if (first) openRow(first, category, selectedRows);
                }}
              />
            </BatchBar>
          )}
        </>
      )}

      {ready && !category && (
        <div className="tn-notice">
          <SvgCheckCircle size={16} />
          {COPY.home.attention.empty}
        </div>
      )}

      <Drawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        storageKey="pending-history"
        eyebrow={COPY.pending.title}
        title={COPY.pending.history}
      >
        {runId && version.data && period && (
          <LastUpdate
            runId={runId}
            versionId={version.data.id}
            unitId={unitId}
            period={period.scope.period}
          />
        )}
        <DecisionLogList entries={decisions.data?.entries ?? []} limit={30} />
      </Drawer>

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
