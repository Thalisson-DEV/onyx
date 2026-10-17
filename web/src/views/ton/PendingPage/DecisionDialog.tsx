"use client";

import { useState } from "react";
import useSWR, { useSWRConfig } from "swr";
import { Button, InputTypeIn, Modal, Text } from "@opal/components";
import { SvgArrowRight, SvgBubbleText, SvgCheckCircle } from "@opal/icons";
import type { Route } from "next";
import { SEARCH_PARAM_NAMES } from "@/app/app/services/searchParams";
import { cn } from "@opal/utils";
import { errorHandlingFetcher } from "@/lib/fetcher";
import {
  COPY,
  formatCurrency,
  formatPeriod,
  formatRelativeDateTime,
  plural,
} from "@/lib/ton/copy";
import {
  type DecisionEntry,
  type DecisionLog,
  TON_DECISIONS_KEY,
  TonApiError,
  postTonJson,
  sumBlockers,
} from "@/lib/ton/decisions";
import { getBusinessLabel } from "@/lib/ton/labels";
import EvidenceRecords from "@/views/ton/components/EvidenceRecords";
import DuplicateCompare from "@/views/ton/PendingPage/DuplicateCompare";
import ReconciliationCompare from "@/views/ton/PendingPage/ReconciliationCompare";
import ReadinessDelta from "@/views/ton/components/ReadinessDelta";
import { LoadingBlock, StatusPill } from "@/views/ton/components/ui";
import {
  type BlockerRow,
  JUSTIFICATIONS,
  type Justification,
  MAPPING_KEYS,
  type Overview,
  type PeriodReadiness,
  type QueueCategory,
  RECONCILIATION_DECISIONS,
  REVIEW_DECISIONS,
  type ReconciliationDecision,
  type ReviewDecision,
  type Target,
  type Version,
  duplicatePair,
  isReviewCategory,
  readinessUrl,
  rowDetail,
  rowPeriods,
  rowSuggestion,
  rowTitle,
} from "@/views/ton/PendingPage/model";

const DIALOG = COPY.pending.dialog;
const LOOP = COPY.decisionLoop;

const MAPPING_KIND: Partial<Record<string, string>> = {
  units: "UNIT",
  accounts: "ACCOUNT",
  budgetAccounts: "BUDGET_ACCOUNT",
  budgetUnits: "BUDGET_UNIT",
};

type Phase = "edit" | "recording" | "recomputing" | "result";

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-1.5">
      <span className="ton-eyebrow">{title}</span>
      {children}
    </section>
  );
}

function askTonHref(category: QueueCategory, row: BlockerRow): Route {
  // Only business labels travel in the link: no amounts, payers or ids.
  const query = new URLSearchParams({
    firstMessage: LOOP.explain.askPrompt(
      category.label,
      rowTitle(row, category),
      rowPeriods(row)
    ),
    [SEARCH_PARAM_NAMES.SUBMIT_ON_LOAD]: "true",
  });
  // SAFETY: /ton/chat is a static route; only its query varies.
  return `/ton/chat?${query.toString()}` as Route;
}

/** The case at a glance: what it is and the facts a person checks first. */
function FactCard({
  row,
  category,
  batch,
  titleOnly,
}: {
  row: BlockerRow;
  category: QueueCategory;
  batch?: BlockerRow[];
  /** The comparison below already shows the facts. */
  titleOnly?: boolean;
}) {
  if (batch && batch.length > 1) {
    return (
      <section className="ton-fact-card flex flex-col gap-1">
        <span className="ton-eyebrow">{category.label}</span>
        <Text as="h3" font="heading-h3" color="text-05">
          {DIALOG.batchTitle(batch.length)}
        </Text>
        <Text font="secondary-body" color="text-03">
          {DIALOG.batchBody}
        </Text>
      </section>
    );
  }
  const first = row.records[0];
  const amount = first
    ? (first.movement_amount ?? first.final_amount ?? first.service_amount)
    : null;
  const facts = first
    ? [
        [DIALOG.facts.document, first.document],
        [DIALOG.facts.unit, first.unit ?? first.counterparty],
        [
          DIALOG.facts.date,
          first.emission_date
            ? first.emission_date.slice(0, 10).split("-").reverse().join("/")
            : null,
        ],
        [DIALOG.facts.amount, amount ? formatCurrency(amount) : null],
        [
          DIALOG.facts.where,
          first.sheet && first.row
            ? LOOP.location(first.sheet, first.row)
            : null,
        ],
        [DIALOG.facts.account, first.account],
        [DIALOG.facts.history, first.description],
      ].filter((item): item is [string, string] => Boolean(item[1]))
    : row.locations?.length
      ? [[DIALOG.facts.where, row.locations.join(" ; ")] as [string, string]]
      : [];
  const detail = row.evidence ? rowDetail(row, category) : "";
  return (
    <section className="ton-fact-card flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <span className="ton-eyebrow">{category.label}</span>
        <Text as="h3" font="heading-h3" color="text-05">
          {rowTitle(row, category)}
        </Text>
        {detail && (
          <Text font="main-ui-body" color="text-04">
            {detail}
          </Text>
        )}
        <Text font="secondary-body" color="text-03">
          {[COPY.pending.affected(row.record_count), rowPeriods(row)]
            .filter(Boolean)
            .join(" · ")}
        </Text>
      </div>
      {!titleOnly && facts.length > 0 && (
        <dl className="ton-fact-grid">
          {facts.map(([label, value]) => (
            <div key={label} className="flex flex-col gap-0.5 min-w-0">
              <dt>
                <Text font="secondary-body" color="text-03">
                  {label}
                </Text>
              </dt>
              <dd className="ton-fact-value">
                <Text font="main-ui-action" color="text-05">
                  {value}
                </Text>
              </dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}

function OptionCard({
  selected,
  title,
  help,
  onSelect,
  compact,
}: {
  selected: boolean;
  title: string;
  help?: string;
  onSelect: () => void;
  compact?: boolean;
}) {
  return (
    // Selectable option card: title plus what it means.
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={onSelect}
      className={cn(
        "ton-option-card ton-focusable",
        selected && "is-selected",
        compact && "is-compact"
      )}
    >
      <span className="ton-option-dot" aria-hidden />
      <span className="flex flex-col gap-0.5 min-w-0 text-start">
        <Text font="main-ui-action" color="text-05">
          {title}
        </Text>
        {help && (
          <Text font="secondary-body" color="text-03">
            {help}
          </Text>
        )}
      </span>
    </button>
  );
}

/** The API's own reason when it gives one, so the person knows what to fix. */
function failureMessage(error: unknown): string {
  return error instanceof TonApiError && error.detail
    ? DIALOG.errorWithDetail(getBusinessLabel(error.detail))
    : DIALOG.error;
}

/** Selected cases at a glance: one line each, the amount on the right. */
function BatchTable({ rows }: { rows: BlockerRow[] }) {
  return (
    <div className="ton-batch-table">
      <table className="w-full border-collapse">
        <tbody>
          {rows.map((item, index) => {
            const first = item.records[0];
            const amount =
              first?.movement_amount ??
              first?.final_amount ??
              first?.service_amount ??
              null;
            return (
              <tr key={`${item.occurrence_id ?? item.item_id ?? index}`}>
                <td>{first?.document ?? "—"}</td>
                <td className="w-full">
                  {first?.account ?? first?.counterparty ?? item.rule_title ?? ""}
                  {first?.description && (
                    <span className="ton-batch-history">{first.description}</span>
                  )}
                </td>
                <td className="whitespace-nowrap">
                  {first?.sheet && first.row
                    ? LOOP.location(first.sheet, first.row)
                    : ""}
                </td>
                <td className="text-end whitespace-nowrap font-semibold">
                  {amount ? formatCurrency(amount) : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function evidenceBasis(row: BlockerRow): string | null {
  if (row.candidate) return LOOP.evidenceReady[row.candidate.evidence];
  if (row.legacy_evidence) return LOOP.evidenceReady.LEGACY;
  return null;
}

interface DecisionResult {
  recomputed: boolean;
  before: PeriodReadiness;
  after: PeriodReadiness | null;
  entry: DecisionEntry | null;
}

export interface DecisionScope {
  runId: string;
  structureId: string;
  version: Version;
  unitId?: string;
  period: PeriodReadiness;
}

export interface DecisionAccess {
  canManage: boolean;
  canConfigure: boolean;
  canRecompute: boolean;
}

interface DecisionDialogProps {
  row: BlockerRow;
  /** Rows the person selected in the queue: one decision settles all. */
  batch?: BlockerRow[];
  category: QueueCategory;
  scope: DecisionScope;
  access: DecisionAccess;
  /** Refreshes the queue after the base or the DRE structure changed. */
  onApplied: () => Promise<void>;
  onNext: () => void;
  onClose: () => void;
}

export default function DecisionDialog({
  row,
  batch,
  category,
  scope,
  access,
  onApplied,
  onNext,
  onClose,
}: DecisionDialogProps) {
  const { mutate } = useSWRConfig();
  const [targetSearch, setTargetSearch] = useState("");
  const [targetId, setTargetId] = useState(row.candidate?.target_id ?? "");
  const [accountCode, setAccountCode] = useState(
    row.legacy_evidence?.suggested_code ?? row.source_key ?? ""
  );
  const [accountLabel, setAccountLabel] = useState(
    row.legacy_evidence?.suggested_label ?? ""
  );
  const [reasonInput, setReason] = useState("");
  const [basis, setBasis] = useState<"MOVEMENT" | "FINAL">("MOVEMENT");
  const [lineCode, setLineCode] = useState(row.line_candidate ?? "");
  const [startMonth, setStartMonth] = useState("");
  const [endMonth, setEndMonth] = useState("");
  // No default: a reconciliation outcome must be an explicit human choice.
  const [decision, setDecision] = useState<ReconciliationDecision | null>(null);
  // Unit-missing cases: the unit the entry belongs to, instead of a review
  // decision (the case is decided as part of the assignment).
  const [assigning, setAssigning] = useState(false);
  const [assignUnit, setAssignUnit] = useState("");
  const [reviewDecision, setReviewDecision] = useState<ReviewDecision | null>(
    null
  );
  const [justification, setJustification] =
    useState<Justification>("BUSINESS_EXCEPTION");
  const [authorization, setAuthorization] = useState<string>(
    DIALOG.authorizationDefault
  );
  const [applyToAll, setApplyToAll] = useState(false);
  const [batchProgress, setBatchProgress] = useState<{
    done: number;
    total: number;
  } | null>(null);
  const [phase, setPhase] = useState<Phase>("edit");
  const [failure, setFailure] = useState<string | null>(null);
  const [rejected, setRejected] = useState(false);
  const [result, setResult] = useState<DecisionResult | null>(null);
  const [createdTargets, setCreatedTargets] = useState<Target[]>([]);

  const isMapping = MAPPING_KEYS.includes(category.key);
  const isDre =
    category.key === "dreAssignment" || category.key === "drePending";
  const isReconciliation = category.key.startsWith("reconciliation");
  const isReview = isReviewCategory(category);
  // The Controladoria may skip the reason on review, reconciliation and
  // mapping decisions; the history then records the decision itself.
  const defaultReason = isReview
    ? assigning
      ? DIALOG.assignUnit
      : reviewDecision
      ? DIALOG.defaultReason(
          COPY.pending.reviewDecisions[reviewDecision] ?? reviewDecision
        )
      : ""
    : isReconciliation
      ? decision
        ? DIALOG.defaultReason(COPY.pending.decisions[decision])
        : ""
      : isMapping
        ? DIALOG.defaultMappingReason
        : "";
  const reasonOptional = isReview || isReconciliation || isMapping;
  const reason = reasonInput.trim() || defaultReason;
  // Cases of the same rule: one decision can settle all of them.
  // Reconciliation items of the same closing month: one reason can settle a
  // whole list (for example every August note with a different number).
  const siblings = useSWR<{ rows: BlockerRow[] }>(
    !batch &&
      ((isReview && row.rule_key) || (isReconciliation && row.item_id))
      ? `/api/ton/financial-domain/normalizations/${scope.runId}/readiness/blockers/${category.blocker}?structure_version_id=${scope.version.id}&limit=100${isReconciliation ? `&period=${scope.period.scope.period}` : ""}${scope.unitId ? `&unit_id=${scope.unitId}` : ""}`
      : null,
    errorHandlingFetcher
  );
  const sameRule = (siblings.data?.rows ?? []).filter((item) =>
    isReview
      ? item.rule_key === row.rule_key && item.occurrence_id
      : Boolean(item.item_id)
  );
  // The NG and billing sides of one invoice are separate items with the same
  // matching key: they are read and decided together.
  const pairRows = row.group_key
    ? (siblings.data?.rows ?? []).filter(
        (item) => item.group_key === row.group_key && item.item_id
      )
    : [];
  const pair = pairRows.length > 1 ? pairRows : [];
  const batchLabel = isReview
    ? DIALOG.applyToAll(
        sameRule.length,
        row.rule_title ?? rowTitle(row, category)
      )
    : DIALOG.applyToList(sameRule.length);
  const targetType = ["units", "budgetUnits"].includes(category.key)
    ? "units"
    : "accounts";
  const targets = useSWR<Target[]>(
    isMapping
      ? `/api/ton/financial-domain/${targetType}?limit=50&search=${encodeURIComponent(targetSearch)}`
      : null,
    errorHandlingFetcher
  );

  const canEdit =
    category.key === "other"
      ? false
      : isMapping ||
          category.key === "budgetPeriods" ||
          isReconciliation ||
          isReview
        ? access.canManage
        : access.canConfigure;
  // DRE classification changes the structure version, which readiness reads
  // directly; every other decision reaches readiness through a new base.
  const willApply = isDre || access.canRecompute;
  const hasTarget = isMapping
    ? Boolean(targetId)
    : isDre
      ? Boolean(lineCode)
      : category.key === "amountBasis"
        ? Boolean(row.account_id)
        : category.key === "budgetPeriods"
          ? Boolean(startMonth)
          : isReconciliation
            ? Boolean(decision)
            : isReview
              ? assigning
                ? Boolean(assignUnit)
                : Boolean(reviewDecision)
              : false;
  const busy = phase === "recording" || phase === "recomputing";
  const batchRecords = (batch ?? []).flatMap((item) => item.records);
  const duplicate = batch ? null : duplicatePair(row);
  // A single NG row is already shown in the case card above.
  const showEvidence =
    Boolean(batch) ||
    isReconciliation ||
    row.records.length > 1 ||
    Boolean(row.legacy_evidence);
  const ruleCopy = COPY.pending.ruleDecisions[row.rule_key ?? ""];
  const unitMissing = row.rule_key === "NGF-UNIT-MISSING";
  const activeUnits = useSWR<Target[]>(
    unitMissing && canEdit
      ? "/api/ton/financial-domain/units?limit=100&active_only=true"
      : null,
    errorHandlingFetcher
  );
  // For a duplicate the likely answer is "same entry": offer it first.
  const reviewOrder: readonly ReviewDecision[] = row.rule_key?.startsWith(
    "NGF-DUP"
  )
    ? ["REQUEST_SOURCE_CORRECTION", "JUSTIFY_EXCEPTION", "MARK_FALSE_POSITIVE"]
    : REVIEW_DECISIONS;
  const allTargets = [...createdTargets, ...(targets.data ?? [])];

  async function recordDecision(): Promise<void> {
    if (isMapping) {
      const kind = MAPPING_KIND[category.key] ?? null;
      await postTonJson("/api/ton/financial-domain/mappings", {
        source_id: row.source_id,
        kind,
        source_key: row.source_key,
        unit_id: targetType === "units" ? targetId : null,
        account_id: targetType === "accounts" ? targetId : null,
        reason,
      });
    } else if (category.key === "amountBasis") {
      await postTonJson(
        `/api/ton/financial-domain/accounts/${row.account_id}/amount-basis`,
        { basis, reason }
      );
    } else if (isDre) {
      await postTonJson(
        `/api/ton/dre/structures/${scope.structureId}/assignments`,
        {
          account_id: row.account_id,
          line_code: lineCode,
          status: "APPROVED",
          reason,
        }
      );
    } else if (category.key === "budgetPeriods") {
      await postTonJson("/api/ton/financial-domain/mappings", {
        source_id: row.source_id,
        kind: "BUDGET_PERIOD",
        source_key: row.source_key,
        calendar_period: `${startMonth}-01`,
        effective_to: endMonth ? `${endMonth}-01` : null,
        reason,
      });
    } else if (isReview && assigning && assignUnit && row.occurrence_id) {
      const pool = batch ?? (applyToAll && sameRule.length > 1 ? sameRule : [row]);
      const ids = pool.flatMap((item) =>
        item.occurrence_id ? [item.occurrence_id] : []
      );
      for (const [index, occurrenceId] of ids.entries()) {
        if (ids.length > 1) setBatchProgress({ done: index, total: ids.length });
        await postTonJson(
          `/api/ton/financial-review/occurrences/${occurrenceId}/unit-assignment`,
          { unit_id: assignUnit, reason: reasonInput.trim() }
        );
      }
      setBatchProgress(null);
    } else if (isReview && reviewDecision && row.occurrence_id) {
      const pool = batch ?? (applyToAll && sameRule.length > 1 ? sameRule : [row]);
      const ids = pool.flatMap((item) =>
        item.occurrence_id ? [item.occurrence_id] : []
      );
      for (const [index, occurrenceId] of ids.entries()) {
        if (ids.length > 1) setBatchProgress({ done: index, total: ids.length });
        await postTonJson(
          `/api/ton/financial-review/occurrences/${occurrenceId}/decisions`,
          {
            kind: reviewDecision,
            reason,
            authorization_reference:
              authorization.trim() || DIALOG.authorizationDefault,
            justification_category:
              reviewDecision === "JUSTIFY_EXCEPTION" ? justification : null,
          }
        );
      }
      setBatchProgress(null);
    } else if (decision && row.item_id) {
      const pool =
        batch ??
        (applyToAll && sameRule.length > 1
          ? sameRule
          : pair.length
            ? pair
            : [row]);
      const ids = pool
        .filter((item) => decision !== "NG_AUTHORITATIVE" || item.paired)
        .flatMap((item) => (item.item_id ? [item.item_id] : []));
      for (const [index, itemId] of ids.entries()) {
        if (ids.length > 1) setBatchProgress({ done: index, total: ids.length });
        await postTonJson(
          `/api/ton/financial-domain/normalizations/${scope.runId}/reconciliation/items/${itemId}/decision`,
          { decision, reason }
        );
      }
      setBatchProgress(null);
    }
  }

  async function confirm() {
    if (!reason.trim() || !hasTarget) return;
    setFailure(null);
    setPhase("recording");
    try {
      await recordDecision();
      let runId = scope.runId;
      let versionId = scope.version.id;
      if (isDre) {
        const latest = await errorHandlingFetcher<Version>(
          `/api/ton/dre/structures/${scope.structureId}/latest-version`
        );
        versionId = latest.id;
      } else if (access.canRecompute) {
        setPhase("recomputing");
        const run = await postTonJson<{ id: string }>(
          `/api/ton/financial-domain/normalizations/${scope.runId}/recompute`,
          {}
        );
        runId = run.id;
      }
      const [overview, log] = await Promise.all([
        willApply
          ? errorHandlingFetcher<Overview>(
              readinessUrl(runId, versionId, scope.unitId)
            )
          : Promise.resolve(null),
        errorHandlingFetcher<DecisionLog>(TON_DECISIONS_KEY),
      ]);
      const after =
        overview?.periods.find(
          (item) => item.scope.period === scope.period.scope.period
        ) ?? null;
      setResult({
        recomputed: willApply,
        before: scope.period,
        after,
        entry: log.entries[0] ?? null,
      });
      setPhase("result");
      await Promise.all([onApplied(), mutate(TON_DECISIONS_KEY, log, false)]);
    } catch (error) {
      setBatchProgress(null);
      setFailure(failureMessage(error));
      setPhase("edit");
    }
  }

  async function reject() {
    if (!row.source_id || !row.source_key || !reason.trim()) return;
    if (category.key !== "units" && category.key !== "accounts") return;
    setFailure(null);
    setPhase("recording");
    try {
      const exact =
        row.candidate?.evidence === "EXACT_CODE" ? row.candidate : null;
      await postTonJson("/api/ton/financial-domain/candidates/rejections", {
        source_id: row.source_id,
        kind: category.key === "units" ? "UNIT" : "ACCOUNT",
        source_key: row.source_key,
        target_id: exact?.target_id ?? null,
        evidence: exact ? "EXACT_CODE" : "LEGACY_REFERENCE",
        reference_digest: exact
          ? null
          : (row.legacy_evidence?.reference_digest ?? null),
        reason,
      });
      setRejected(true);
      setPhase("result");
      await Promise.all([onApplied(), mutate(TON_DECISIONS_KEY)]);
    } catch (error) {
      setFailure(failureMessage(error));
      setPhase("edit");
    }
  }

  async function createAccount() {
    if (!accountCode.trim() || !accountLabel.trim()) return;
    setFailure(null);
    try {
      const account = await postTonJson<Target>(
        "/api/ton/financial-domain/accounts",
        { code: accountCode.trim(), label: accountLabel.trim() }
      );
      setCreatedTargets((items) => [account, ...items]);
      setTargetId(account.id);
    } catch (error) {
      setFailure(failureMessage(error));
    }
  }

  const periodLabel = formatPeriod(scope.period.scope.period).toLowerCase();
  const explain = LOOP.explain.categories[category.key];
  const decisionCount = batch
    ? batch.length
    : applyToAll && sameRule.length > 1
      ? sameRule.length
      : pair.length || 1;
  const impactText = [
    pair.length > 1 && !batch && !applyToAll
      ? DIALOG.impactPair
      : decisionCount > 1
        ? DIALOG.impactMany(decisionCount)
      : LOOP.preview.scope(
          plural(row.record_count, "registro", "registros"),
          rowPeriods(row)
        ),
    willApply ? DIALOG.impactRecompute : DIALOG.impactRecordOnly,
  ].join(" · ");

  return (
    <Modal
      open
      onOpenChange={(open) => {
        if (!open && !busy) onClose();
      }}
    >
      <Modal.Content width="full">
        <Modal.Header
          title={phase === "result" ? LOOP.result.title : category.label}
          onClose={() => !busy && onClose()}
        />
        <Modal.Body>
          <div className="w-full flex flex-col gap-5">
            {phase === "result" && rejected && (
              <div className="flex items-center gap-2">
                <SvgCheckCircle size={18} className="ton-brand-text" />
                <Text font="main-ui-body" color="text-04">
                  {LOOP.result.rejected}
                </Text>
              </div>
            )}

            {phase === "result" && result && (
              <ResultView
                count={decisionCount}
                result={result}
                periodLabel={periodLabel}
                onNext={onNext}
                onClose={onClose}
              />
            )}

            {phase !== "result" && (
              <div className="ton-decision-layout">
                <div className="flex flex-col gap-4 min-w-0">
                  <FactCard
                    row={row}
                    category={category}
                    batch={batch}
                    titleOnly={Boolean(duplicate) || (isReconciliation && !batch)}
                  />
                  {duplicate ? (
                    <DuplicateCompare
                      kept={duplicate.kept}
                      repeated={duplicate.repeated}
                    />
                  ) : isReconciliation && !batch ? (
                    <ReconciliationCompare
                      records={
                        pair.length
                          ? pair.flatMap((item) => item.records)
                          : row.records
                      }
                    />
                  ) : (
                    showEvidence && (
                      <Section title={LOOP.evidenceTitle}>
                        {batch ? (
                          <BatchTable rows={batch} />
                        ) : (
                          <EvidenceRecords
                            records={row.records}
                            total={row.record_count}
                            reconciliation={isReconciliation}
                          />
                        )}
                        {row.legacy_evidence && (
                          <Text font="secondary-body" color="text-03">
                            {`${row.legacy_evidence.reference_label}: ${row.legacy_evidence.suggested_code}${row.legacy_evidence.suggested_label ? ` — ${row.legacy_evidence.suggested_label}` : ""}`}
                          </Text>
                        )}
                      </Section>
                    )
                  )}
                  {evidenceBasis(row) && !batch && (
                    <section className="flex flex-col gap-1 rounded-12 border border-01 p-3">
                      <div className="flex items-center gap-2">
                        <SvgCheckCircle size={16} className="ton-brand-text" />
                        <Text font="main-ui-action" color="text-05">
                          {rowSuggestion(row)}
                        </Text>
                      </div>
                      <Text font="secondary-body" color="text-03">
                        {LOOP.evidenceReady.body(evidenceBasis(row) ?? "")}
                      </Text>
                    </section>
                  )}
                  {category.noActual && (
                    <div className="flex flex-col gap-2">
                      <Text font="main-ui-body" color="text-04">
                        {COPY.pending.noActual.action}
                      </Text>
                      <div>
                        <Button href="/ton/fontes" rightIcon={SvgArrowRight}>
                          {COPY.pending.noActual.cta}
                        </Button>
                      </div>
                    </div>
                  )}
                </div>

                <aside className="ton-decision-panel">
                  <div className="flex flex-col gap-1.5">
                    <Text as="h3" font="heading-h3" color="text-05">
                      {DIALOG.decision}
                    </Text>
                    {explain && (
                      <span>
                        <StatusPill tone={explain.changes ? "warning" : "neutral"}>
                          {explain.changes
                            ? LOOP.explain.changesNumbers
                            : LOOP.explain.keepsNumbers}
                        </StatusPill>
                      </span>
                    )}
                  </div>

                  {!category.noActual && !canEdit && (
                    <Text font="main-ui-body" color="text-03">
                      {category.key === "other"
                        ? category.action
                        : DIALOG.noPermission}
                    </Text>
                  )}

                  {canEdit && isMapping && (
                    <div className="flex flex-col gap-2">
                      <InputTypeIn
                        searchIcon
                        value={targetSearch}
                        onChange={(event) =>
                          setTargetSearch(event.target.value)
                        }
                        placeholder={DIALOG.searchTarget}
                        aria-label={DIALOG.searchTarget}
                      />
                      <div
                        role="radiogroup"
                        aria-label={DIALOG.decision}
                        className="ton-choice-list"
                      >
                        {allTargets.map((target) => (
                          <OptionCard
                            key={target.id}
                            compact
                            selected={target.id === targetId}
                            title={getBusinessLabel(
                              target.name ?? target.label ?? target.code
                            )}
                            help={target.code}
                            onSelect={() => setTargetId(target.id)}
                          />
                        ))}
                      </div>
                      {targets.isLoading && (
                        <LoadingBlock label={COPY.common.loading} lines={1} />
                      )}
                      {(category.key === "accounts" ||
                        category.key === "budgetAccounts") &&
                        access.canConfigure && (
                          <details className="ton-more">
                            <summary>{DIALOG.createAccount}</summary>
                            <div className="flex flex-col gap-2 pt-2">
                              <InputTypeIn
                                value={accountCode}
                                onChange={(event) =>
                                  setAccountCode(event.target.value)
                                }
                                aria-label={DIALOG.accountCode}
                                placeholder={DIALOG.accountCode}
                              />
                              <InputTypeIn
                                value={accountLabel}
                                onChange={(event) =>
                                  setAccountLabel(event.target.value)
                                }
                                aria-label={DIALOG.accountLabel}
                                placeholder={DIALOG.accountLabel}
                              />
                              <div>
                                <Button
                                  size="sm"
                                  prominence="secondary"
                                  disabled={
                                    !accountCode.trim() || !accountLabel.trim()
                                  }
                                  onClick={createAccount}
                                >
                                  {DIALOG.createAccount}
                                </Button>
                              </div>
                            </div>
                          </details>
                        )}
                    </div>
                  )}

                  {canEdit && category.key === "amountBasis" && (
                    <div
                      role="radiogroup"
                      aria-label={DIALOG.decision}
                      className="ton-choice-list"
                    >
                      {(["MOVEMENT", "FINAL"] as const).map((value) => (
                        <OptionCard
                          key={value}
                          compact
                          selected={basis === value}
                          title={
                            value === "MOVEMENT"
                              ? DIALOG.movement
                              : DIALOG.finalAmount
                          }
                          onSelect={() => setBasis(value)}
                        />
                      ))}
                    </div>
                  )}

                  {canEdit && isDre && (
                    <div
                      role="radiogroup"
                      aria-label={DIALOG.decision}
                      className="ton-choice-list"
                    >
                      {scope.version.lines
                        .filter((line) => line.line_type === "SOURCE_SUM")
                        .map((line) => (
                          <OptionCard
                            key={line.code}
                            compact
                            selected={line.code === lineCode}
                            title={getBusinessLabel(line.label)}
                            onSelect={() => setLineCode(line.code)}
                          />
                        ))}
                    </div>
                  )}

                  {canEdit && category.key === "budgetPeriods" && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <label className="flex flex-col gap-1">
                        <Text font="secondary-action" color="text-04">
                          {DIALOG.startMonth}
                        </Text>
                        <InputTypeIn
                          type="month"
                          value={startMonth}
                          onChange={(event) => setStartMonth(event.target.value)}
                          aria-label={DIALOG.startMonth}
                        />
                      </label>
                      <label className="flex flex-col gap-1">
                        <Text font="secondary-action" color="text-04">
                          {DIALOG.endMonth}
                        </Text>
                        <InputTypeIn
                          type="month"
                          value={endMonth}
                          onChange={(event) => setEndMonth(event.target.value)}
                          aria-label={DIALOG.endMonth}
                        />
                      </label>
                    </div>
                  )}

                  {canEdit && isReconciliation && (
                    <div
                      role="radiogroup"
                      aria-label={DIALOG.decision}
                      className="flex flex-col gap-2"
                    >
                      {RECONCILIATION_DECISIONS.filter(
                        (value) => value !== "NG_AUTHORITATIVE" || row.paired
                      ).map((value) => (
                        <OptionCard
                          key={value}
                          selected={decision === value}
                          title={COPY.pending.decisions[value]}
                          help={LOOP.explain.options[value]}
                          onSelect={() => setDecision(value)}
                        />
                      ))}
                    </div>
                  )}

                  {canEdit && isReview && (
                    <div
                      role="radiogroup"
                      aria-label={DIALOG.decision}
                      className="flex flex-col gap-2"
                    >
                      {unitMissing && (
                        <OptionCard
                          selected={assigning}
                          title={DIALOG.assignUnit}
                          help={DIALOG.assignUnitHelp}
                          onSelect={() => {
                            setAssigning(true);
                            setReviewDecision(null);
                          }}
                        />
                      )}
                      {unitMissing && assigning && (
                        <select
                          className="ton-select ton-focusable"
                          aria-label={DIALOG.assignUnitPick}
                          value={assignUnit}
                          onChange={(event) => setAssignUnit(event.target.value)}
                        >
                          <option value="">{DIALOG.assignUnitPick}</option>
                          {(activeUnits.data ?? []).map((unit) => (
                            <option key={unit.id} value={unit.id}>
                              {getBusinessLabel(unit.name ?? unit.code)}
                            </option>
                          ))}
                        </select>
                      )}
                      {reviewOrder.map((value) => (
                        <OptionCard
                          key={value}
                          selected={!assigning && reviewDecision === value}
                          title={
                            ruleCopy?.[value]?.title ??
                            COPY.pending.reviewDecisions[value] ??
                            value
                          }
                          help={
                            ruleCopy?.[value]?.help ??
                            COPY.pending.reviewDecisionHelp[value] ??
                            ""
                          }
                          onSelect={() => {
                            setAssigning(false);
                            setReviewDecision(value);
                          }}
                        />
                      ))}
                    </div>
                  )}

                  {canEdit &&
                    isReview &&
                    reviewDecision === "JUSTIFY_EXCEPTION" && (
                      <div className="flex flex-col gap-1.5">
                        <Text font="secondary-action" color="text-04">
                          {COPY.pending.justification.label}
                        </Text>
                        <div className="flex flex-wrap gap-1.5">
                          {JUSTIFICATIONS.map((value) => (
                            <button
                              key={value}
                              type="button"
                              aria-pressed={justification === value}
                              className="ton-chip ton-focusable"
                              onClick={() => setJustification(value)}
                            >
                              {COPY.pending.justification[value] ?? value}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                  {canEdit &&
                    !batch &&
                    (isReview || isReconciliation) &&
                    sameRule.length > Math.max(1, pair.length) && (
                      <label
                        aria-label={batchLabel}
                        className="ton-apply-all flex items-start gap-2.5"
                      >
                        <input
                          type="checkbox"
                          checked={applyToAll}
                          onChange={(event) =>
                            setApplyToAll(event.target.checked)
                          }
                        />
                        <span className="flex flex-col gap-0.5">
                          <Text font="main-ui-action" color="text-05">
                            {batchLabel}
                          </Text>
                          <Text font="secondary-body" color="text-03">
                            {DIALOG.applyToAllHint}
                          </Text>
                        </span>
                      </label>
                    )}

                  {canEdit && !category.noActual && (
                    <div className="flex flex-col gap-1.5">
                      <label className="flex flex-col gap-1">
                        <Text font="secondary-action" color="text-04">
                          {isReview
                            ? DIALOG.noteOptional
                            : reasonOptional
                              ? DIALOG.reasonOptional
                              : DIALOG.reason}
                        </Text>
                        <InputTypeIn
                          value={reasonInput}
                          onChange={(event) => setReason(event.target.value)}
                          placeholder={DIALOG.reasonPlaceholder}
                          aria-label={DIALOG.reason}
                        />
                      </label>
                      {category.key !== "review" &&
                        (COPY.pending.quickReasons[category.key] ?? []).length >
                          0 && (
                        <div className="flex flex-wrap gap-1.5">
                          {(COPY.pending.quickReasons[category.key] ?? []).map(
                            (text) => (
                              <button
                                key={text}
                                type="button"
                                aria-pressed={reasonInput === text}
                                className="ton-chip ton-focusable"
                                onClick={() => setReason(text)}
                              >
                                {text}
                              </button>
                            )
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {canEdit && isReview && (
                    <details className="ton-more">
                      <summary>{DIALOG.moreOptions}</summary>
                      <label className="flex flex-col gap-1 pt-2">
                        <Text font="secondary-action" color="text-04">
                          {DIALOG.authorization}
                        </Text>
                        <InputTypeIn
                          value={authorization}
                          onChange={(event) =>
                            setAuthorization(event.target.value)
                          }
                          placeholder={DIALOG.authorizationPlaceholder}
                          aria-label={DIALOG.authorization}
                        />
                      </label>
                    </details>
                  )}

                  {busy && (
                    <LoadingBlock
                      label={
                        phase === "recording"
                          ? batchProgress
                            ? DIALOG.recordingMany(
                                batchProgress.done + 1,
                                batchProgress.total
                              )
                            : LOOP.working.recording
                          : LOOP.working.recomputing
                      }
                      lines={1}
                    />
                  )}
                  {failure && (
                    <Text font="main-ui-body" color="status-error-05">
                      {failure}
                    </Text>
                  )}

                  <div className="ton-decision-footer">
                    {canEdit && (
                      <Text font="secondary-body" color="text-03">
                        {impactText}
                      </Text>
                    )}
                    <div className="flex flex-wrap gap-2 justify-end">
                      {canEdit &&
                        (category.key === "units" ||
                          category.key === "accounts") &&
                        (row.candidate?.evidence === "EXACT_CODE" ||
                          row.legacy_evidence) && (
                          <Button
                            prominence="secondary"
                            disabled={busy || !reason.trim()}
                            onClick={reject}
                          >
                            {DIALOG.reject}
                          </Button>
                        )}
                      {category.key !== "other" && !batch && (
                        <Button
                          prominence="tertiary"
                          icon={SvgBubbleText}
                          href={askTonHref(category, row)}
                        >
                          {LOOP.explain.askTonShort}
                        </Button>
                      )}
                      {canEdit ? (
                        <Button
                          disabled={busy || !reason.trim() || !hasTarget}
                          onClick={() => void confirm()}
                        >
                          {decisionCount > 1
                            ? DIALOG.confirmMany(decisionCount)
                            : DIALOG.confirm}
                        </Button>
                      ) : (
                        <Button prominence="secondary" onClick={onClose}>
                          {DIALOG.close}
                        </Button>
                      )}
                    </div>
                  </div>
                </aside>
              </div>
            )}
          </div>
        </Modal.Body>
      </Modal.Content>
    </Modal>
  );
}

function ResultView({
  count,
  result,
  periodLabel,
  onNext,
  onClose,
}: {
  count: number;
  result: DecisionResult;
  periodLabel: string;
  onNext: () => void;
  onClose: () => void;
}) {
  const labels = LOOP.result;
  const { entry, before, after } = result;
  const remaining = after ? sumBlockers(after.blockers) : null;
  const unchanged =
    after !== null && sumBlockers(before.blockers) === remaining;
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start gap-2">
        <SvgCheckCircle size={18} className="ton-brand-text shrink-0 mt-0.5" />
        <div className="flex flex-col gap-0.5">
          {entry && (
            <>
              <Text font="main-ui-action" color="text-05">
                {count > 1
                  ? DIALOG.recordedMany(
                      count,
                      LOOP.log.outcomes[entry.outcome] ??
                        getBusinessLabel(entry.outcome)
                    )
                  : `${LOOP.log.kinds[entry.kind]}: ${getBusinessLabel(entry.subject)} → ${LOOP.log.outcomes[entry.outcome] ?? getBusinessLabel(entry.outcome)}`}
              </Text>
              <Text font="secondary-body" color="text-03">
                {labels.meta(
                  entry.version,
                  entry.decided_by,
                  formatRelativeDateTime(entry.decided_at)
                )}
              </Text>
            </>
          )}
        </div>
      </div>

      {result.recomputed && after ? (
        <section className="flex flex-col gap-3 rounded-12 border border-01 p-4">
          <span className="ton-eyebrow">{labels.recomputed}</span>
          <ReadinessDelta
            before={before.blockers}
            after={after.blockers}
            statusBefore={before.status}
            statusAfter={after.status}
            changedOnly
          />
          <Text font="main-ui-body" color="text-04">
            {after.status === "READY"
              ? labels.nowReady(periodLabel)
              : unchanged
                ? labels.unchanged
                : labels.stillBlocked(periodLabel, remaining ?? 0)}
          </Text>
        </section>
      ) : (
        <Text font="main-ui-body" color="text-04">
          {labels.notRecomputed}
        </Text>
      )}

      <div className="flex flex-wrap gap-2 justify-end">
        <Button prominence="tertiary" onClick={onClose}>
          {labels.done}
        </Button>
        {after?.status === "READY" ? (
          <Button href="/ton/dre" rightIcon={SvgArrowRight}>
            {labels.openDre}
          </Button>
        ) : (
          (remaining ?? 1) > 0 && (
            <Button onClick={onNext} rightIcon={SvgArrowRight}>
              {labels.next}
            </Button>
          )
        )}
      </div>
    </div>
  );
}
