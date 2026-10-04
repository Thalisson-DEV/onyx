"use client";

import { useState } from "react";
import {
  Button,
  InputSingleSelect,
  InputTextArea,
  Text,
} from "@opal/components";
import {
  SvgArrowRight,
  SvgCheckCircle,
  SvgHelpCircle,
  SvgSparkle,
} from "@opal/icons";
import { formatCurrency, formatDate, formatDay } from "@/lib/ton/copy";
import {
  CLASSIFICATION_API,
  CLASSIFICATION_COPY,
  formatMagnitude,
  postJson,
  useAccountEntries,
  type ClassificationRow,
  type ClassificationTable,
} from "@/lib/ton/classification";
import { askHref } from "@/views/ton/shell/TonCommandMenu";
import { StatusPill, TonCard } from "@/views/ton/components/ui";
import { NEW_NATURE, STATUS_LABEL, STATUS_TONE } from "./shared";

const COPY = CLASSIFICATION_COPY.panel;

interface AccountPanelProps {
  row: ClassificationRow | null;
  table: ClassificationTable;
  /** Natureza picked in the grid, waiting for a justification here. */
  draft: string | null;
  onDraft: (accountId: string | null) => void;
  onNewNature: () => void;
  onSaved: (code: string) => void;
}

function Label({ children }: { children: string }) {
  return <span className="ton-eyebrow">{children}</span>;
}

function impactText(
  row: ClassificationRow,
  table: ClassificationTable
): string | null {
  const suggestion = row.suggestion;
  if (!suggestion || suggestion.agrees_with_current) return null;
  const target = table.natures.find(
    (item) => item.account_id === suggestion.account_id
  );
  if (!target) return null;
  const amount = formatMagnitude(row.total_amount);
  if (!row.dre_group) return COPY.impactFromNothing(amount, target.dre_group);
  if (row.dre_group === target.dre_group) {
    return COPY.impactSameGroup(row.dre_group);
  }
  return COPY.impactMove(amount, row.dre_group, target.dre_group);
}

function Entries({ table, row }: { table: ClassificationTable; row: ClassificationRow }) {
  const entries = useAccountEntries(table.source_id, row.account_code);
  return (
    <div className="flex flex-col gap-2">
      <Label>{COPY.examples}</Label>
      {entries.data && entries.data.length === 0 && (
        <Text font="secondary-body" color="text-03">
          {COPY.examplesEmpty}
        </Text>
      )}
      <ul className="flex flex-col divide-y divide-border-01 rounded-08 border border-border-01">
        {(entries.data ?? []).map((entry, index) => (
          <li key={index} className="flex flex-col gap-0.5 px-3 py-2">
            <span className="flex items-baseline justify-between gap-3">
              <Text font="secondary-body" color="text-03">
                {[formatDay(entry.date), entry.unit].filter(Boolean).join(" · ")}
              </Text>
              <span className="ton-metric-num shrink-0">
                <Text font="secondary-action" color="text-05">
                  {formatCurrency(entry.amount)}
                </Text>
              </span>
            </span>
            <Text font="secondary-body" color="text-04">
              {entry.history}
            </Text>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function AccountPanel({
  row,
  table,
  draft,
  onDraft,
  onNewNature,
  onSaved,
}: AccountPanelProps) {
  const [note, setNote] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  if (!row) {
    return (
      <TonCard as="div" className="p-5">
        <Text font="secondary-body" color="text-03">
          {COPY.empty}
        </Text>
      </TonCard>
    );
  }

  const base = `${CLASSIFICATION_API}/${table.source_id}`;
  const suggestion = row.suggestion;
  const agrees = suggestion?.agrees_with_current ?? false;
  const draftNature = table.natures.find((item) => item.account_id === draft);
  const impact = impactText(row, table);

  async function run(action: () => Promise<unknown>) {
    if (!row) return;
    setBusy(true);
    setFailed(false);
    try {
      await action();
      setNote("");
      setReason("");
      onDraft(null);
      onSaved(row.account_code);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  function confirm() {
    void run(() =>
      postJson(`${base}/confirm`, {
        account_code: row!.account_code,
        note: note.trim() || null,
      })
    );
  }

  function saveChange() {
    if (!draft) return;
    void run(() =>
      postJson(`${base}/change`, {
        account_code: row!.account_code,
        account_id: draft,
        reason: reason.trim(),
      })
    );
  }

  function startSuggestion() {
    if (!suggestion) return;
    onDraft(suggestion.account_id);
    setReason(COPY.reasonFromSuggestion(suggestion.rationale).slice(0, 500));
  }

  return (
    <TonCard as="div" className="flex flex-col gap-5 p-5">
      <header className="flex flex-col gap-1.5">
        <span className="flex flex-wrap items-center gap-2">
          <Text font="heading-h3" color="text-05">
            {row.account_code}
          </Text>
          <StatusPill tone={STATUS_TONE[row.status]}>
            {STATUS_LABEL[row.status]}
          </StatusPill>
        </span>
        <Text font="main-ui-body" color="text-04">
          {row.description || "—"}
        </Text>
        <Text font="secondary-body" color="text-03">
          {[
            formatCurrency(row.total_amount),
            COPY.entries(row.entries),
            COPY.units(row.units.length),
          ].join(" · ")}
        </Text>
      </header>

      <div className="flex gap-3 rounded-12 bg-background-tint-01 p-4">
        <SvgHelpCircle size={18} className="ton-brand-text shrink-0 mt-0.5" />
        <div className="flex flex-col gap-1">
          <Label>{COPY.question}</Label>
          <Text font="main-ui-action" color="text-05">
            {suggestion?.question ?? COPY.noQuestion}
          </Text>
        </div>
      </div>

      {agrees && suggestion ? (
        <div className="flex items-start gap-2">
          <SvgCheckCircle size={16} className="ton-brand-text shrink-0 mt-0.5" />
          <div className="flex flex-col gap-0.5">
            <Text font="main-ui-action" color="text-05">
              {COPY.agree(suggestion.natureza)}
            </Text>
            <Text font="secondary-body" color="text-03">
              {`${row.dre_group ?? ""} · ${COPY.confidence[suggestion.confidence]}`}
            </Text>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="flex flex-col gap-1 rounded-12 border border-border-01 p-3">
            <Label>{COPY.today}</Label>
            <Text font="main-ui-action" color="text-05">
              {row.natureza ?? CLASSIFICATION_COPY.list.noNature}
            </Text>
            <Text font="secondary-body" color="text-03">
              {[row.dre_group, row.origin ? COPY.origin[row.origin] : null]
                .filter(Boolean)
                .join(" · ")}
            </Text>
          </div>
          <div className="flex flex-col gap-1 rounded-12 border border-border-01 p-3">
            <span className="flex items-center gap-1.5">
              <SvgSparkle size={14} className="ton-brand-text" />
              <Label>{COPY.suggestion}</Label>
            </span>
            <Text font="main-ui-action" color="text-05">
              {suggestion?.natureza ?? COPY.noSuggestion}
            </Text>
            {suggestion && (
              <Text font="secondary-body" color="text-03">
                {`${
                  table.natures.find(
                    (item) => item.account_id === suggestion.account_id
                  )?.dre_group ?? ""
                } · ${COPY.confidence[suggestion.confidence]}`}
              </Text>
            )}
          </div>
        </div>
      )}

      {suggestion && (
        <div className="flex flex-col gap-1">
          <Label>{COPY.why}</Label>
          <Text font="secondary-body" color="text-04">
            {suggestion.rationale}
          </Text>
          {impact && (
            <Text font="secondary-action" color="text-05">
              {impact}
            </Text>
          )}
        </div>
      )}

      {row.pattern && (
        <Text font="secondary-body" color="text-03">
          {COPY.pattern(row.pattern)}
        </Text>
      )}

      <Entries table={table} row={row} />

      <section className="flex flex-col gap-3 border-t border-border-01 pt-4">
        <Label>{COPY.decide}</Label>
        {row.status === "CONFIRMED" && row.decided_at && (
          <Text font="secondary-body" color="text-03">
            {COPY.decided(row.decided_by ?? "—", formatDate(row.decided_at))}
          </Text>
        )}

        {draft && draftNature ? (
          <div className="flex flex-col gap-2 rounded-12 border border-border-02 p-3">
            <Text font="main-ui-action" color="text-05">
              {COPY.changeTo(row.natureza, draftNature.natureza)}
            </Text>
            <Text font="secondary-body" color="text-03">
              {draftNature.dre_group}
            </Text>
            <InputTextArea
              aria-label={COPY.reason}
              placeholder={COPY.reason}
              value={reason}
              rows={3}
              maxLength={500}
              autoFocus
              onChange={(event) => setReason(event.target.value)}
            />
            <span className="flex flex-wrap gap-2">
              <Button
                icon={SvgCheckCircle}
                disabled={busy || reason.trim().length < 3}
                onClick={saveChange}
              >
                {busy ? COPY.saving : COPY.save}
              </Button>
              <Button
                prominence="tertiary"
                disabled={busy}
                onClick={() => onDraft(null)}
              >
                {COPY.cancel}
              </Button>
            </span>
          </div>
        ) : (
          <>
            <div className="flex flex-wrap gap-2">
              {row.natureza && row.status !== "CONFIRMED" && (
                <Button icon={SvgCheckCircle} disabled={busy} onClick={confirm}>
                  {busy ? COPY.saving : COPY.keep(row.natureza)}
                </Button>
              )}
              {suggestion && !agrees && (
                <Button
                  prominence={row.natureza ? "secondary" : "primary"}
                  icon={SvgSparkle}
                  disabled={busy}
                  onClick={startSuggestion}
                >
                  {COPY.useSuggestion(suggestion.natureza)}
                </Button>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <InputSingleSelect
                value=""
                onValueChange={(value) =>
                  value === NEW_NATURE ? onNewNature() : onDraft(value)
                }
              >
                <InputSingleSelect.Trigger
                  placeholder={COPY.other}
                  aria-label={COPY.other}
                />
                <InputSingleSelect.Content>
                  {table.natures
                    .filter((item) => item.account_id !== row.account_id)
                    .map((item) => (
                      <InputSingleSelect.Item
                        key={item.account_id}
                        value={item.account_id}
                      >
                        {`${item.natureza} · ${item.dre_group}`}
                      </InputSingleSelect.Item>
                    ))}
                  <InputSingleSelect.Item value={NEW_NATURE}>
                    {CLASSIFICATION_COPY.list.newNatureOption}
                  </InputSingleSelect.Item>
                </InputSingleSelect.Content>
              </InputSingleSelect>
            </div>
            {row.natureza && row.status !== "CONFIRMED" && (
              <InputTextArea
                aria-label={COPY.note}
                placeholder={COPY.notePlaceholder}
                value={note}
                rows={2}
                maxLength={1000}
                onChange={(event) => setNote(event.target.value)}
              />
            )}
          </>
        )}

        {failed && (
          <span role="alert" className="text-status-error-05">
            <Text font="secondary-body" color="inherit">
              {COPY.failed}
            </Text>
          </span>
        )}

        <span>
          <Button
            prominence="tertiary"
            size="sm"
            rightIcon={SvgArrowRight}
            href={askHref(COPY.askPrompt(row))}
          >
            {COPY.ask}
          </Button>
        </span>
      </section>
    </TonCard>
  );
}
