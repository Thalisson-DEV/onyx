"use client";

import { Fragment, useEffect, useState } from "react";
import {
  Button,
  InputSingleSelect,
  InputTypeIn,
  Text,
} from "@opal/components";
import {
  SvgAlertTriangle,
  SvgCheckCircle,
  SvgChevronDown,
  SvgChevronRight,
} from "@opal/icons";
import { formatCurrency, formatDate, formatDay } from "@/lib/ton/copy";
import {
  CLASSIFICATION_API,
  CLASSIFICATION_COPY as COPY,
  postJson,
  sentenceCase,
  useAccountEntries,
  type ClassificationRow,
  type ClassificationTable,
} from "@/lib/ton/classification";
import { askHref } from "@/views/ton/shell/TonCommandMenu";
import { NEW_NATURE } from "./shared";

const COLUMNS = 6;

interface Draft {
  code: string;
  accountId: string;
  reason: string;
}

interface AccountGridProps {
  table: ClassificationTable;
  rows: ClassificationRow[];
  onNewNature: (code: string) => void;
  onSaved: () => Promise<unknown>;
  /** Set by the parent after a natureza is created for a row. */
  pending: { code: string; accountId: string } | null;
  onPendingUsed: () => void;
}

function AssistantCell({
  row,
  onUse,
}: {
  row: ClassificationRow;
  onUse: () => void;
}) {
  const suggestion = row.suggestion;
  if (!suggestion) {
    return (
      <Text font="secondary-body" color="text-03">
        {COPY.notAnalyzed}
      </Text>
    );
  }
  if (suggestion.agrees_with_current) {
    return (
      <span className="flex items-center gap-1.5">
        <SvgCheckCircle size={14} className="ton-brand-text shrink-0" />
        <Text font="secondary-body" color="text-04">
          {COPY.agrees}
        </Text>
      </span>
    );
  }
  return (
    <span className="flex items-center gap-2">
      <SvgAlertTriangle size={14} className="text-status-warning-05 shrink-0" />
      <Text font="secondary-body" color="text-05">
        {COPY.suggests(sentenceCase(suggestion.natureza))}
      </Text>
      <span onClick={(event) => event.stopPropagation()}>
        <Button size="sm" prominence="secondary" onClick={onUse}>
          {COPY.use}
        </Button>
      </span>
    </span>
  );
}

function Detail({
  row,
  table,
  busy,
  onConfirm,
}: {
  row: ClassificationRow;
  table: ClassificationTable;
  busy: boolean;
  onConfirm: () => void;
}) {
  const entries = useAccountEntries(table.source_id, row.account_code);
  const suggestion = row.suggestion;
  return (
    <div className="flex flex-col gap-2 py-1">
      {suggestion ? (
        <>
          {suggestion.question && (
            <Text font="secondary-action" color="text-05">
              {suggestion.question}
            </Text>
          )}
          <Text font="secondary-body" color="text-04">
            {suggestion.rationale}
          </Text>
        </>
      ) : (
        <Text font="secondary-body" color="text-03">
          {COPY.detail.noAnalysis}
        </Text>
      )}
      {(entries.data ?? []).map((entry, index) => (
        <Text key={index} font="secondary-body" color="text-03">
          {[
            formatDay(entry.date),
            entry.unit,
            entry.history,
            formatCurrency(entry.amount),
          ]
            .filter(Boolean)
            .join(" · ")}
        </Text>
      ))}
      {row.status === "CONFIRMED" && row.decided_at && (
        <Text font="secondary-body" color="text-03">
          {COPY.detail.decided(row.decided_by ?? "—", formatDate(row.decided_at))}
        </Text>
      )}
      <span className="flex flex-wrap gap-2 pt-1">
        {row.natureza && row.status !== "CONFIRMED" && (
          <Button size="sm" icon={SvgCheckCircle} disabled={busy} onClick={onConfirm}>
            {busy ? COPY.saving : COPY.detail.confirm(sentenceCase(row.natureza))}
          </Button>
        )}
        <Button
          size="sm"
          prominence="tertiary"
          href={askHref(COPY.detail.askPrompt(row))}
        >
          {COPY.detail.ask}
        </Button>
      </span>
    </div>
  );
}

function ChangeRow({
  row,
  table,
  draft,
  busy,
  onReason,
  onSave,
  onCancel,
}: {
  row: ClassificationRow;
  table: ClassificationTable;
  draft: Draft;
  busy: boolean;
  onReason: (reason: string) => void;
  onSave: () => void;
  onCancel: () => void;
}) {
  const target = table.natures.find((item) => item.account_id === draft.accountId);
  return (
    <div className="flex flex-col gap-2 py-1">
      <Text font="secondary-action" color="text-05">
        {COPY.change.title(
          row.natureza ? sentenceCase(row.natureza) : null,
          sentenceCase(target?.natureza ?? "")
        )}
      </Text>
      <div className="flex flex-wrap items-center gap-2">
        <div className="min-w-[18rem] flex-1">
          <InputTypeIn
            aria-label={COPY.change.reason}
            placeholder={COPY.change.reason}
            value={draft.reason}
            maxLength={500}
            autoFocus
            onChange={(event) => onReason(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && draft.reason.trim().length >= 3) onSave();
              if (event.key === "Escape") onCancel();
            }}
          />
        </div>
        <Button
          size="sm"
          disabled={busy || draft.reason.trim().length < 3}
          onClick={onSave}
        >
          {busy ? COPY.saving : COPY.change.save}
        </Button>
        <Button size="sm" prominence="tertiary" disabled={busy} onClick={onCancel}>
          {COPY.change.cancel}
        </Button>
      </div>
    </div>
  );
}

export default function AccountGrid({
  table,
  rows,
  onNewNature,
  onSaved,
  pending,
  onPendingUsed,
}: AccountGridProps) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const base = `${CLASSIFICATION_API}/${table.source_id}`;

  useEffect(() => {
    if (!pending) return;
    setDraft({ code: pending.code, accountId: pending.accountId, reason: "" });
    setExpanded(null);
    onPendingUsed();
  }, [pending, onPendingUsed]);

  async function run(code: string, action: () => Promise<unknown>) {
    setBusy(true);
    setFailed(null);
    try {
      await action();
      setDraft(null);
      setExpanded(null);
      await onSaved();
    } catch {
      setFailed(code);
    } finally {
      setBusy(false);
    }
  }

  if (!rows.length) {
    return (
      <div className="ton-card p-5">
        <Text font="secondary-body" color="text-03">
          {COPY.empty}
        </Text>
      </div>
    );
  }

  return (
    <div className="ton-card overflow-x-auto">
      <table className="ton-statement ton-classification-grid w-full min-w-[880px] border-collapse">
        <thead>
          <tr>
            <th scope="col" className="w-8">
              <span className="sr-only">Detalhes</span>
            </th>
            <th scope="col">{COPY.columns.code}</th>
            <th scope="col">{COPY.columns.description}</th>
            <th scope="col">{COPY.columns.nature}</th>
            <th scope="col">{COPY.columns.assistant}</th>
            <th scope="col" data-numeric>
              {COPY.columns.total}
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const open = expanded === row.account_code;
            const changing = draft?.code === row.account_code ? draft : null;
            return (
              <Fragment key={row.account_code}>
                <tr
                  aria-expanded={open}
                  aria-selected={open || changing != null}
                  onClick={() => {
                    setDraft(null);
                    setExpanded(open ? null : row.account_code);
                  }}
                  className="cursor-pointer"
                >
                  <td>
                    {open ? (
                      <SvgChevronDown size={14} className="text-text-03" />
                    ) : (
                      <SvgChevronRight size={14} className="text-text-03" />
                    )}
                  </td>
                  <td>
                    <Text font="secondary-action" color="text-05">
                      {row.account_code}
                    </Text>
                  </td>
                  <td>
                    <Text font="secondary-body" color="text-05">
                      {row.description || "—"}
                    </Text>
                  </td>
                  <td onClick={(event) => event.stopPropagation()}>
                    <InputSingleSelect
                      value={changing?.accountId ?? row.account_id ?? ""}
                      onValueChange={(value) => {
                        if (value === NEW_NATURE) {
                          onNewNature(row.account_code);
                        } else if (value !== row.account_id) {
                          setExpanded(null);
                          setDraft({
                            code: row.account_code,
                            accountId: value,
                            reason: "",
                          });
                        }
                      }}
                    >
                      <InputSingleSelect.Trigger
                        placeholder={COPY.noNature}
                        aria-label={`${COPY.columns.nature} ${row.account_code}`}
                      />
                      <InputSingleSelect.Content>
                        {table.natures.map((item) => (
                          <InputSingleSelect.Item
                            key={item.account_id}
                            value={item.account_id}
                          >
                            {item.natureza}
                          </InputSingleSelect.Item>
                        ))}
                        <InputSingleSelect.Item value={NEW_NATURE}>
                          {COPY.newNatureOption}
                        </InputSingleSelect.Item>
                      </InputSingleSelect.Content>
                    </InputSingleSelect>
                  </td>
                  <td>
                    <AssistantCell
                      row={row}
                      onUse={() => {
                        if (!row.suggestion) return;
                        setExpanded(null);
                        setDraft({
                          code: row.account_code,
                          accountId: row.suggestion.account_id,
                          reason: COPY.change
                            .reasonFromSuggestion(row.suggestion.rationale)
                            .slice(0, 500),
                        });
                      }}
                    />
                  </td>
                  <td data-numeric>
                    <Text font="secondary-body" color="text-05">
                      {formatCurrency(row.total_amount)}
                    </Text>
                  </td>
                </tr>
                {(open || changing) && (
                  <tr data-type="DETAIL">
                    <td />
                    <td colSpan={COLUMNS - 1}>
                      {changing ? (
                        <ChangeRow
                          row={row}
                          table={table}
                          draft={changing}
                          busy={busy}
                          onReason={(reason) => setDraft({ ...changing, reason })}
                          onCancel={() => setDraft(null)}
                          onSave={() =>
                            void run(row.account_code, () =>
                              postJson(`${base}/change`, {
                                account_code: row.account_code,
                                account_id: changing.accountId,
                                reason: changing.reason.trim(),
                              })
                            )
                          }
                        />
                      ) : (
                        <Detail
                          row={row}
                          table={table}
                          busy={busy}
                          onConfirm={() =>
                            void run(row.account_code, () =>
                              postJson(`${base}/confirm`, {
                                account_code: row.account_code,
                                note: null,
                              })
                            )
                          }
                        />
                      )}
                      {failed === row.account_code && (
                        <span role="alert" className="text-status-error-05">
                          <Text font="secondary-body" color="inherit">
                            {COPY.failed}
                          </Text>
                        </span>
                      )}
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
