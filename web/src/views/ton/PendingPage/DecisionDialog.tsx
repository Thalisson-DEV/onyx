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
  formatPeriod,
  formatRelativeDateTime,
  plural,
} from "@/lib/ton/copy";
import {
  type DecisionEntry,
  type DecisionLog,
  TON_DECISIONS_KEY,
  postTonJson,
  sumBlockers,
} from "@/lib/ton/decisions";
import { getBusinessLabel } from "@/lib/ton/labels";
import EvidenceRecords from "@/views/ton/components/EvidenceRecords";
import ReadinessDelta from "@/views/ton/components/ReadinessDelta";
import { LoadingBlock, StatusPill } from "@/views/ton/components/ui";
import {
  type BlockerRow,
  MAPPING_KEYS,
  type Overview,
  type PeriodReadiness,
  type QueueCategory,
  RECONCILIATION_DECISIONS,
  type ReconciliationDecision,
  type Target,
  type Version,
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

type Phase = "edit" | "confirm" | "recording" | "recomputing" | "result";
type DecisionStep = "review" | "decide" | "confirm" | "done";

function DecisionSteps({ current }: { current: DecisionStep }) {
  const steps: DecisionStep[] = ["review", "decide", "confirm", "done"];
  const index = steps.indexOf(current);
  return (
    <ol
      aria-label={COPY.pending.steps.label}
      className="flex flex-wrap items-center gap-x-2 gap-y-1"
    >
      {steps.map((step, position) => (
        <li key={step} className="flex items-center gap-2">
          <span
            aria-current={position === index ? "step" : undefined}
            className="ton-step"
            data-state={
              position < index
                ? "done"
                : position === index
                  ? "current"
                  : "next"
            }
          >
            {position + 1}
          </span>
          <Text
            font={position === index ? "secondary-action" : "secondary-body"}
            color={position <= index ? "text-05" : "text-03"}
          >
            {COPY.pending.steps[step]}
          </Text>
          {position < steps.length - 1 && (
            <span aria-hidden className="w-4 border-t border-02" />
          )}
        </li>
      ))}
    </ol>
  );
}

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

/** Plain-language question and effect on the numbers; facts, not advice. */
function Explanation({ category }: { category: QueueCategory }) {
  const explain = LOOP.explain.categories[category.key];
  if (!explain) return null;
  return (
    <section className="flex flex-col gap-1.5 rounded-12 bg-background-neutral-01 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="ton-eyebrow">{LOOP.explain.title}</span>
        <StatusPill tone={explain.changes ? "warning" : "neutral"}>
          {explain.changes
            ? LOOP.explain.changesNumbers
            : LOOP.explain.keepsNumbers}
        </StatusPill>
      </div>
      <Text font="main-ui-body" color="text-05">
        {explain.question}
      </Text>
      <Text font="secondary-body" color="text-04">
        {explain.effect}
      </Text>
    </section>
  );
}

function evidenceBasis(row: BlockerRow): string | null {
  if (row.candidate) return LOOP.evidenceReady[row.candidate.evidence];
  if (row.legacy_evidence) return LOOP.evidenceReady.LEGACY;
  return null;
}

function monthLabel(value: string): string {
  return formatPeriod(`${value}-01`).toLowerCase();
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
  const [reason, setReason] = useState("");
  const [basis, setBasis] = useState<"MOVEMENT" | "FINAL">("MOVEMENT");
  const [lineCode, setLineCode] = useState(row.line_candidate ?? "");
  const [startMonth, setStartMonth] = useState("");
  const [endMonth, setEndMonth] = useState("");
  // No default: a reconciliation outcome must be an explicit human choice.
  const [decision, setDecision] = useState<ReconciliationDecision | null>(null);
  const [phase, setPhase] = useState<Phase>("edit");
  const [failed, setFailed] = useState(false);
  const [rejected, setRejected] = useState(false);
  const [result, setResult] = useState<DecisionResult | null>(null);
  const [createdTargets, setCreatedTargets] = useState<Target[]>([]);

  const isMapping = MAPPING_KEYS.includes(category.key);
  const isDre =
    category.key === "dreAssignment" || category.key === "drePending";
  const isReconciliation = category.key.startsWith("reconciliation");
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
      : isMapping || category.key === "budgetPeriods" || isReconciliation
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
            : false;
  const busy = phase === "recording" || phase === "recomputing";

  const allTargets = [...createdTargets, ...(targets.data ?? [])];
  const chosenTarget = allTargets.find((item) => item.id === targetId);
  const targetText = chosenTarget
    ? getBusinessLabel(
        [chosenTarget.code, chosenTarget.name ?? chosenTarget.label]
          .filter(Boolean)
          .join(" — ")
      )
    : row.candidate && row.candidate.target_id === targetId
      ? `${row.candidate.code} — ${row.candidate.label}`
      : "";
  const lineLabel =
    scope.version.lines.find((line) => line.code === lineCode)?.label ??
    lineCode;

  function previewChange(): string | null {
    if (!hasTarget) return null;
    const source = getBusinessLabel(row.source_key ?? "");
    if (isMapping)
      return targetType === "units"
        ? LOOP.preview.unit(source, targetText)
        : LOOP.preview.account(source, targetText);
    if (category.key === "amountBasis")
      return LOOP.preview.amountBasis(
        basis === "MOVEMENT" ? DIALOG.movement : DIALOG.finalAmount
      );
    if (isDre) return LOOP.preview.dre(getBusinessLabel(lineLabel));
    if (category.key === "budgetPeriods")
      return LOOP.preview.budgetPeriod(
        monthLabel(startMonth),
        endMonth ? monthLabel(endMonth) : null
      );
    if (isReconciliation && decision)
      return LOOP.preview.reconciliation(COPY.pending.decisions[decision]);
    return null;
  }

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
    } else if (decision && row.item_id) {
      await postTonJson(
        `/api/ton/financial-domain/normalizations/${scope.runId}/reconciliation/items/${row.item_id}/decision`,
        { decision, reason }
      );
    }
  }

  async function confirm() {
    if (!reason.trim() || !hasTarget) return;
    setFailed(false);
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
    } catch {
      setFailed(true);
      setPhase("confirm");
    }
  }

  async function reject() {
    if (!row.source_id || !row.source_key || !reason.trim()) return;
    if (category.key !== "units" && category.key !== "accounts") return;
    setFailed(false);
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
    } catch {
      setFailed(true);
      setPhase("edit");
    }
  }

  async function createAccount() {
    if (!accountCode.trim() || !accountLabel.trim()) return;
    setFailed(false);
    try {
      const account = await postTonJson<Target>(
        "/api/ton/financial-domain/accounts",
        { code: accountCode.trim(), label: accountLabel.trim() }
      );
      setCreatedTargets((items) => [account, ...items]);
      setTargetId(account.id);
    } catch {
      setFailed(true);
    }
  }

  const step: DecisionStep =
    phase === "result"
      ? "done"
      : phase === "edit"
        ? reason.trim() && hasTarget
          ? "decide"
          : "review"
        : "confirm";
  const periodLabel = formatPeriod(scope.period.scope.period).toLowerCase();
  const preview = previewChange();

  return (
    <Modal
      open
      onOpenChange={(open) => {
        if (!open && !busy) onClose();
      }}
    >
      <Modal.Content width="lg">
        <Modal.Header
          title={phase === "result" ? LOOP.result.title : DIALOG.title}
        />
        <Modal.Body>
          <div className="flex flex-col gap-5">
            {canEdit && <DecisionSteps current={step} />}

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
                result={result}
                periodLabel={periodLabel}
                onNext={onNext}
                onClose={onClose}
              />
            )}

            {phase !== "result" && (
              <>
                <Section title={DIALOG.found}>
                  <div className="flex flex-wrap items-center gap-2">
                    <Text font="main-ui-action" color="text-05">
                      {rowTitle(row, category)}
                    </Text>
                    <StatusPill tone="warning">
                      {getBusinessLabel(row.status)}
                    </StatusPill>
                  </div>
                  {row.evidence && rowDetail(row, category) && (
                    <Text font="main-ui-body" color="text-04">
                      {rowDetail(row, category)}
                    </Text>
                  )}
                  <Text font="secondary-body" color="text-03">
                    {[COPY.pending.affected(row.record_count), rowPeriods(row)]
                      .filter(Boolean)
                      .join(" · ")}
                  </Text>
                </Section>

                <Explanation category={category} />

                <Section title={LOOP.evidenceTitle}>
                  <EvidenceRecords
                    records={row.records}
                    total={row.record_count}
                    reconciliation={isReconciliation}
                  />
                  {row.legacy_evidence && (
                    <Text font="secondary-body" color="text-03">
                      {`${row.legacy_evidence.reference_label}: ${row.legacy_evidence.suggested_code}${row.legacy_evidence.suggested_label ? ` — ${row.legacy_evidence.suggested_label}` : ""}`}
                    </Text>
                  )}
                </Section>

                {evidenceBasis(row) ? (
                  <section className="flex flex-col gap-1 rounded-12 border border-01 p-3">
                    <div className="flex items-center gap-2">
                      <SvgCheckCircle size={16} className="ton-brand-text" />
                      <Text font="main-ui-action" color="text-05">
                        {LOOP.evidenceReady.title}
                      </Text>
                    </div>
                    <Text font="main-ui-body" color="text-04">
                      {rowSuggestion(row)}
                    </Text>
                    <Text font="secondary-body" color="text-03">
                      {LOOP.evidenceReady.body(evidenceBasis(row) ?? "")}
                    </Text>
                  </section>
                ) : (
                  !isReconciliation &&
                  !category.noActual && (
                    <Section title={DIALOG.suggestion}>
                      <Text font="main-ui-body" color="text-04">
                        {rowSuggestion(row)}
                      </Text>
                    </Section>
                  )
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

                {!category.noActual && !canEdit && (
                  <Text font="main-ui-body" color="text-03">
                    {category.key === "other"
                      ? category.action
                      : DIALOG.noPermission}
                  </Text>
                )}

                {canEdit && phase === "edit" && (
                  <Section title={DIALOG.decision}>
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
                          placeholder={DIALOG.searchTarget}
                          aria-label={DIALOG.searchTarget}
                        />
                        <div className="flex flex-wrap gap-2">
                          {allTargets.map((target) => (
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
                          access.canConfigure && (
                            <div className="flex flex-col gap-2 border-t border-01 pt-3">
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
                          )}
                      </div>
                    )}
                    {category.key === "amountBasis" && (
                      <div className="flex gap-2">
                        {(["MOVEMENT", "FINAL"] as const).map((value) => (
                          <Button
                            key={value}
                            size="sm"
                            prominence={
                              basis === value ? "primary" : "secondary"
                            }
                            onClick={() => setBasis(value)}
                          >
                            {value === "MOVEMENT"
                              ? DIALOG.movement
                              : DIALOG.finalAmount}
                          </Button>
                        ))}
                      </div>
                    )}
                    {isDre && (
                      <div className="flex flex-wrap gap-2">
                        {scope.version.lines
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
                              {getBusinessLabel(line.label)}
                            </Button>
                          ))}
                      </div>
                    )}
                    {category.key === "budgetPeriods" && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        <label className="flex flex-col gap-1">
                          <Text font="secondary-action" color="text-04">
                            {DIALOG.startMonth}
                          </Text>
                          <InputTypeIn
                            type="month"
                            value={startMonth}
                            onChange={(event) =>
                              setStartMonth(event.target.value)
                            }
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
                            onChange={(event) =>
                              setEndMonth(event.target.value)
                            }
                            aria-label={DIALOG.endMonth}
                          />
                        </label>
                      </div>
                    )}
                    {isReconciliation && (
                      <div
                        role="radiogroup"
                        aria-label={DIALOG.decision}
                        className="flex flex-col gap-2"
                      >
                        {RECONCILIATION_DECISIONS.filter(
                          (value) => value !== "NG_AUTHORITATIVE" || row.paired
                        ).map((value) => (
                          // Selectable option card: title plus what it means.
                          <button
                            key={value}
                            type="button"
                            role="radio"
                            aria-checked={decision === value}
                            onClick={() => setDecision(value)}
                            className={cn(
                              "ton-focusable flex flex-col gap-0.5 rounded-12 border px-3 py-2 text-start",
                              decision === value
                                ? "border-action-selection-05 bg-background-tint-01"
                                : "border-02 hover:bg-background-neutral-01"
                            )}
                          >
                            <Text font="main-ui-action" color="text-05">
                              {COPY.pending.decisions[value]}
                            </Text>
                            <Text font="secondary-body" color="text-03">
                              {LOOP.explain.options[value]}
                            </Text>
                          </button>
                        ))}
                      </div>
                    )}
                    <label className="flex flex-col gap-1">
                      <Text font="secondary-action" color="text-04">
                        {DIALOG.reason}
                      </Text>
                      <InputTypeIn
                        value={reason}
                        onChange={(event) => setReason(event.target.value)}
                        placeholder={DIALOG.reasonPlaceholder}
                        aria-label={DIALOG.reason}
                      />
                    </label>
                  </Section>
                )}

                {canEdit && (
                  <div
                    className={cn(
                      "rounded-12 p-3 flex flex-col gap-1.5",
                      phase === "edit"
                        ? "bg-background-neutral-01"
                        : "bg-status-warning-01"
                    )}
                  >
                    <Text font="main-ui-action" color="text-05">
                      {phase === "edit"
                        ? LOOP.preview.title
                        : DIALOG.confirmTitle}
                    </Text>
                    {preview && (
                      <Text font="main-ui-body" color="text-05">
                        {preview}
                      </Text>
                    )}
                    <Text font="secondary-body" color="text-04">
                      {LOOP.preview.scope(
                        plural(row.record_count, "registro", "registros"),
                        rowPeriods(row)
                      )}
                    </Text>
                    {phase !== "edit" && reason.trim() && (
                      <Text font="secondary-body" color="text-04">
                        {`${DIALOG.reason}: “${reason.trim()}”`}
                      </Text>
                    )}
                    <Text font="secondary-body" color="text-03">
                      {`${willApply ? LOOP.preview.recompute : LOOP.preview.recordOnly} ${LOOP.preview.nothingAutomatic}`}
                    </Text>
                  </div>
                )}

                {busy && (
                  <LoadingBlock
                    label={
                      phase === "recording"
                        ? LOOP.working.recording
                        : LOOP.working.recomputing
                    }
                    lines={1}
                  />
                )}
                {failed && (
                  <Text font="main-ui-body" color="status-error-05">
                    {DIALOG.error}
                  </Text>
                )}

                <div className="flex flex-wrap gap-2 justify-end">
                  {canEdit &&
                    phase === "edit" &&
                    (category.key === "units" || category.key === "accounts") &&
                    (row.candidate?.evidence === "EXACT_CODE" ||
                      row.legacy_evidence) && (
                      <Button
                        prominence="secondary"
                        disabled={!reason.trim()}
                        onClick={reject}
                      >
                        {DIALOG.reject}
                      </Button>
                    )}
                  {phase === "edit" && category.key !== "other" && (
                    <Button
                      prominence="tertiary"
                      icon={SvgBubbleText}
                      href={askTonHref(category, row)}
                    >
                      {LOOP.explain.askTon}
                    </Button>
                  )}
                  <Button
                    prominence="tertiary"
                    disabled={busy}
                    onClick={() =>
                      phase === "confirm" ? setPhase("edit") : onClose()
                    }
                  >
                    {phase === "confirm" ? DIALOG.back : DIALOG.close}
                  </Button>
                  {canEdit && phase === "edit" && (
                    <Button
                      disabled={!reason.trim() || !hasTarget}
                      onClick={() => setPhase("confirm")}
                    >
                      {DIALOG.review}
                    </Button>
                  )}
                  {canEdit && phase !== "edit" && (
                    <Button disabled={busy} onClick={confirm}>
                      {DIALOG.confirm}
                    </Button>
                  )}
                </div>
              </>
            )}
          </div>
        </Modal.Body>
      </Modal.Content>
    </Modal>
  );
}

function ResultView({
  result,
  periodLabel,
  onNext,
  onClose,
}: {
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
                {`${LOOP.log.kinds[entry.kind]}: ${getBusinessLabel(entry.subject)} → ${LOOP.log.outcomes[entry.outcome] ?? getBusinessLabel(entry.outcome)}`}
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
