"use client";

import { useMemo, useState } from "react";
import {
  Button,
  InputSingleSelect,
  InputTextArea,
  InputTypeIn,
  Modal,
  Text,
} from "@opal/components";
import {
  SvgAlertTriangle,
  SvgCheckCircle,
  SvgDownload,
  SvgLock,
  SvgSparkle,
} from "@opal/icons";
import { useUser } from "@/providers/UserProvider";
import {
  formatCurrency,
  formatDate,
  formatNumber,
  formatShortMonth,
} from "@/lib/ton/copy";
import {
  CLASSIFICATION_API,
  CLASSIFICATION_COPY as COPY,
  suggestionDiverges,
  useClassificationTable,
  type ClassificationRow,
  type ClassificationStatus,
  type ClassificationTable,
  type SuggestionRunResult,
} from "@/lib/ton/classification";
import {
  BackLink,
  EmptyState,
  ErrorState,
  LoadingBlock,
  Metric,
  PageContainer,
  PageHeader,
  StatusPill,
  TonCard,
  type TonTone,
} from "@/views/ton/components/ui";

type Filter =
  | "attention"
  | "all"
  | "awaiting"
  | "pending"
  | "divergent"
  | "confirmed";

const STATUS_TONE: Record<ClassificationStatus, TonTone> = {
  PENDING: "danger",
  AWAITING_CONFIRMATION: "warning",
  CONFIRMED: "success",
};

function matchesFilter(row: ClassificationRow, filter: Filter): boolean {
  switch (filter) {
    case "all":
      return true;
    case "attention":
      return row.status !== "CONFIRMED" || suggestionDiverges(row);
    case "awaiting":
      return row.status === "AWAITING_CONFIRMATION";
    case "pending":
      return row.status === "PENDING";
    case "divergent":
      return suggestionDiverges(row);
    case "confirmed":
      return row.status === "CONFIRMED";
  }
}

function matchesQuery(row: ClassificationRow, query: string): boolean {
  const needle = query.trim().toLocaleLowerCase("pt-BR");
  if (!needle) return true;
  return [row.account_code, row.description, row.natureza ?? ""].some((value) =>
    value.toLocaleLowerCase("pt-BR").includes(needle)
  );
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return (await response.json()) as T;
}

async function downloadWorkbook(): Promise<boolean> {
  const response = await fetch(`${CLASSIFICATION_API}/export.xlsx`);
  if (!response.ok) return false;
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `ton-classificacao-contas.xlsx`;
  anchor.click();
  URL.revokeObjectURL(url);
  return true;
}

function SuggestionCell({ row }: { row: ClassificationRow }) {
  const suggestion = row.suggestion;
  if (!suggestion) {
    return (
      <Text font="secondary-body" color="text-03">
        {COPY.noSuggestion}
      </Text>
    );
  }
  return (
    <span className="flex flex-col items-start gap-0.5">
      <span className="flex items-center gap-1.5">
        {suggestion.agrees_with_current ? (
          <SvgCheckCircle size={14} className="ton-brand-text shrink-0" />
        ) : (
          <SvgAlertTriangle
            size={14}
            className="text-status-warning-05 shrink-0"
          />
        )}
        <Text font="secondary-action" color="text-05">
          {suggestion.agrees_with_current ? COPY.agrees : suggestion.natureza}
        </Text>
      </span>
      <Text font="secondary-body" color="text-03">
        {COPY.confidence[suggestion.confidence]}
      </Text>
    </span>
  );
}

function ClassificationList({
  rows,
  onReview,
}: {
  rows: ClassificationRow[];
  onReview: (row: ClassificationRow) => void;
}) {
  if (!rows.length) {
    return (
      <TonCard className="p-5">
        <Text font="secondary-body" color="text-03">
          {COPY.empty}
        </Text>
      </TonCard>
    );
  }
  return (
    <div className="ton-card overflow-x-auto">
      <table className="ton-statement w-full min-w-[1080px] border-collapse">
        <thead>
          <tr>
            <th scope="col" className="text-start">
              {COPY.table.code}
            </th>
            <th scope="col" className="text-start">
              {COPY.table.description}
            </th>
            <th scope="col" className="text-start">
              {COPY.table.nature}
            </th>
            <th scope="col" className="text-start">
              {COPY.table.status}
            </th>
            <th scope="col" className="text-start">
              {COPY.table.suggestion}
            </th>
            <th scope="col">{COPY.table.total}</th>
            <th scope="col">
              <span className="sr-only">{COPY.table.actions}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.account_code}>
              <th scope="row" className="!min-w-0">
                <Text font="secondary-action" color="text-05">
                  {row.account_code}
                </Text>
              </th>
              <td className="text-start !whitespace-normal min-w-[14rem]">
                <Text font="secondary-body" color="text-05">
                  {row.description || "—"}
                </Text>
              </td>
              <td className="text-start !whitespace-normal">
                <span className="flex flex-col items-start">
                  <Text font="secondary-body" color="text-05">
                    {row.natureza ?? "—"}
                  </Text>
                  {row.dre_group && (
                    <Text font="secondary-body" color="text-03">
                      {row.dre_group}
                    </Text>
                  )}
                </span>
              </td>
              <td className="text-start">
                <StatusPill tone={STATUS_TONE[row.status]}>
                  {COPY.status[row.status]}
                </StatusPill>
              </td>
              <td className="text-start !whitespace-normal">
                <SuggestionCell row={row} />
              </td>
              <td>
                <Text font="secondary-body" color="text-05">
                  {formatCurrency(row.total_amount)}
                </Text>
              </td>
              <td>
                <Button
                  size="sm"
                  prominence="secondary"
                  onClick={() => onReview(row)}
                >
                  {COPY.table.review}
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DetailItem({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="ton-eyebrow">{label}</span>
      {children}
    </div>
  );
}

function ReviewDialog({
  row,
  table,
  onClose,
  onSaved,
}: {
  row: ClassificationRow;
  table: ClassificationTable;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [note, setNote] = useState("");
  const [nature, setNature] = useState<string>(
    row.suggestion && !row.suggestion.agrees_with_current
      ? row.suggestion.account_id
      : ""
  );
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const base = `${CLASSIFICATION_API}/${table.source_id}`;
  const months = table.periods.filter((period) =>
    Number(row.monthly[period] ?? 0)
  );

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setFailed(false);
    try {
      await action();
      onSaved();
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  function useSuggestion() {
    if (!row.suggestion) return;
    setNature(row.suggestion.account_id);
    setReason(
      `Sugestão do assistente aceita após conferência: ${row.suggestion.rationale}`.slice(
        0,
        500
      )
    );
  }

  const canChange =
    nature !== "" && nature !== row.account_id && reason.trim().length >= 3;

  return (
    <Modal
      open
      onOpenChange={(open) => {
        if (!open && !busy) onClose();
      }}
    >
      <Modal.Content width="lg">
        <Modal.Header title={COPY.dialog.title(row.account_code)} />
        <Modal.Body>
          <div className="flex flex-col gap-5">
            <Text as="p" font="main-ui-body" color="text-04">
              {row.description}
            </Text>

            <TonCard as="div" className="flex flex-col gap-3 p-4">
              <span className="flex flex-wrap items-center justify-between gap-2">
                <Text font="main-ui-action" color="text-05">
                  {COPY.dialog.current}
                </Text>
                <StatusPill tone={STATUS_TONE[row.status]}>
                  {COPY.status[row.status]}
                </StatusPill>
              </span>
              {row.natureza ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <DetailItem label={COPY.table.nature}>
                    <Text font="secondary-action" color="text-05">
                      {`${row.natureza} · ${row.dre_group ?? ""}`}
                    </Text>
                  </DetailItem>
                  <DetailItem label={COPY.dialog.origin}>
                    <Text font="secondary-body" color="text-04">
                      {row.origin ? COPY.origin[row.origin] : "—"}
                    </Text>
                  </DetailItem>
                  {row.reason && (
                    <div className="sm:col-span-2">
                      <DetailItem label={COPY.dialog.reason}>
                        <Text font="secondary-body" color="text-04">
                          {row.reason}
                        </Text>
                        {row.decided_at && (
                          <Text font="secondary-body" color="text-03">
                            {COPY.dialog.decided(
                              row.decided_by,
                              formatDate(row.decided_at)
                            )}
                          </Text>
                        )}
                      </DetailItem>
                    </div>
                  )}
                </div>
              ) : (
                <Text font="secondary-body" color="text-04">
                  {COPY.dialog.noCurrent}
                </Text>
              )}
            </TonCard>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <DetailItem label={COPY.dialog.pattern}>
                <Text font="secondary-body" color="text-04">
                  {row.pattern
                    ? COPY.dialog.patternText(row.pattern)
                    : COPY.dialog.noPattern}
                </Text>
              </DetailItem>
              <DetailItem label={COPY.dialog.usage}>
                <Text font="secondary-body" color="text-04">
                  {`${COPY.dialog.usageText(row.entries, row.units.length)} · ${formatCurrency(row.total_amount)}`}
                </Text>
                {months.length > 0 && (
                  <Text font="secondary-body" color="text-03">
                    {months
                      .map(
                        (period) =>
                          `${formatShortMonth(`${period}-01`)} ${formatCurrency(row.monthly[period])}`
                      )
                      .join(" · ")}
                  </Text>
                )}
                {row.units.length > 0 && (
                  <Text font="secondary-body" color="text-03">
                    {row.units.join(", ")}
                  </Text>
                )}
              </DetailItem>
            </div>

            <TonCard as="div" className="flex flex-col gap-2 p-4">
              <span className="flex items-center gap-2">
                <SvgSparkle size={16} className="ton-brand-text" />
                <Text font="main-ui-action" color="text-05">
                  {COPY.dialog.suggestion}
                </Text>
              </span>
              {row.suggestion ? (
                <>
                  <Text font="secondary-action" color="text-05">
                    {`${row.suggestion.natureza} · ${COPY.confidence[row.suggestion.confidence]}`}
                  </Text>
                  <Text font="secondary-body" color="text-04">
                    {row.suggestion.rationale}
                  </Text>
                  <Text font="secondary-body" color="text-03">
                    {COPY.dialog.suggestionNote}
                  </Text>
                  {!row.suggestion.agrees_with_current && (
                    <span>
                      <Button
                        size="sm"
                        prominence="secondary"
                        disabled={busy}
                        onClick={useSuggestion}
                      >
                        {COPY.dialog.useSuggestion}
                      </Button>
                    </span>
                  )}
                </>
              ) : (
                <Text font="secondary-body" color="text-03">
                  {COPY.dialog.noSuggestionYet}
                </Text>
              )}
            </TonCard>

            {row.natureza && row.status !== "CONFIRMED" && (
              <div className="flex flex-col gap-2">
                <Text font="main-ui-action" color="text-05">
                  {COPY.dialog.confirmTitle}
                </Text>
                <InputTextArea
                  aria-label={COPY.dialog.confirmNote}
                  placeholder={COPY.dialog.confirmNote}
                  value={note}
                  rows={2}
                  maxLength={1000}
                  onChange={(event) => setNote(event.target.value)}
                />
                <span>
                  <Button
                    icon={SvgCheckCircle}
                    disabled={busy}
                    onClick={() =>
                      void run(() =>
                        postJson(`${base}/confirm`, {
                          account_code: row.account_code,
                          note: note.trim() || null,
                        })
                      )
                    }
                  >
                    {busy ? COPY.dialog.saving : COPY.dialog.confirm}
                  </Button>
                </span>
              </div>
            )}

            <div className="flex flex-col gap-2">
              <Text font="main-ui-action" color="text-05">
                {COPY.dialog.changeTitle}
              </Text>
              <InputSingleSelect value={nature} onValueChange={setNature}>
                <InputSingleSelect.Trigger
                  placeholder={COPY.dialog.changeNature}
                  aria-label={COPY.dialog.changeNature}
                />
                <InputSingleSelect.Content>
                  {table.natures.map((item) => (
                    <InputSingleSelect.Item
                      key={item.account_id}
                      value={item.account_id}
                    >
                      {`${item.natureza} · ${item.dre_group}`}
                    </InputSingleSelect.Item>
                  ))}
                </InputSingleSelect.Content>
              </InputSingleSelect>
              <InputTextArea
                aria-label={COPY.dialog.changeReason}
                placeholder={COPY.dialog.changeReasonPlaceholder}
                value={reason}
                rows={2}
                maxLength={500}
                onChange={(event) => setReason(event.target.value)}
              />
              <Text font="secondary-body" color="text-03">
                {COPY.dialog.changeImpact}
              </Text>
              <span>
                <Button
                  prominence="secondary"
                  disabled={busy || !canChange}
                  onClick={() =>
                    void run(() =>
                      postJson(`${base}/change`, {
                        account_code: row.account_code,
                        account_id: nature,
                        reason: reason.trim(),
                      })
                    )
                  }
                >
                  {busy ? COPY.dialog.saving : COPY.dialog.change}
                </Button>
              </span>
            </div>

            {failed && (
              <span role="alert" className="text-status-error-05">
                <Text font="secondary-body" color="inherit">
                  {COPY.dialog.failed}
                </Text>
              </span>
            )}
          </div>
        </Modal.Body>
      </Modal.Content>
    </Modal>
  );
}

export default function ClassificationPage() {
  const { hasAdminAccess } = useUser();
  const table = useClassificationTable(hasAdminAccess);
  const [filter, setFilter] = useState<Filter>("attention");
  const [query, setQuery] = useState("");
  const [reviewing, setReviewing] = useState<string | null>(null);
  const [suggesting, setSuggesting] = useState(false);
  const [feedback, setFeedback] = useState<{
    tone: "success" | "error";
    text: string;
  } | null>(null);

  const rows = table.data?.rows ?? [];
  const counts = useMemo(
    () => ({
      awaiting: rows.filter((row) => row.status === "AWAITING_CONFIRMATION")
        .length,
      pending: rows.filter((row) => row.status === "PENDING").length,
      divergent: rows.filter(suggestionDiverges).length,
    }),
    [rows]
  );
  const visible = rows.filter(
    (row) => matchesFilter(row, filter) && matchesQuery(row, query)
  );
  const current = rows.find((row) => row.account_code === reviewing) ?? null;

  if (!hasAdminAccess) {
    return (
      <PageContainer>
        <EmptyState
          icon={SvgLock}
          title={COPY.noAccessTitle}
          description={COPY.noAccessDescription}
        />
      </PageContainer>
    );
  }

  async function runSuggestions() {
    if (!table.data) return;
    setSuggesting(true);
    setFeedback(null);
    try {
      const result = await postJson<SuggestionRunResult>(
        `${CLASSIFICATION_API}/${table.data.source_id}/suggestions`,
        { account_codes: [] }
      );
      setFeedback({ tone: "success", text: COPY.suggestDone(result) });
      await table.mutate();
    } catch {
      setFeedback({ tone: "error", text: COPY.suggestFailed });
    } finally {
      setSuggesting(false);
    }
  }

  async function exportExcel() {
    setFeedback(null);
    if (!(await downloadWorkbook())) {
      setFeedback({ tone: "error", text: COPY.exportFailed });
    }
  }

  const filters: { value: Filter; label: string }[] = [
    { value: "attention", label: COPY.filters.attention },
    { value: "awaiting", label: COPY.filters.awaiting },
    { value: "pending", label: COPY.filters.pending },
    { value: "divergent", label: COPY.filters.divergent },
    { value: "confirmed", label: COPY.filters.confirmed },
    { value: "all", label: COPY.filters.all },
  ];

  return (
    <PageContainer>
      <BackLink href="/ton/administracao" label={COPY.back} />
      <PageHeader
        eyebrow={COPY.eyebrow}
        title={COPY.title}
        description={COPY.description}
      />
      {table.isLoading && (
        <TonCard className="p-5">
          <LoadingBlock label="Carregando contas…" />
        </TonCard>
      )}
      {table.error && <ErrorState onRetry={() => table.mutate()} />}
      {table.data && (
        <>
          <TonCard
            as="div"
            className="grid grid-cols-2 lg:grid-cols-4 gap-4 p-5"
          >
            <Metric
              label={COPY.metrics.total}
              value={formatNumber(rows.length)}
              detail={COPY.source(table.data.source_name)}
            />
            <Metric
              label={COPY.metrics.awaiting}
              value={formatNumber(counts.awaiting)}
              detail={COPY.metrics.awaitingDetail}
              tone={counts.awaiting ? "warning" : "success"}
            />
            <Metric
              label={COPY.metrics.pending}
              value={formatNumber(counts.pending)}
              detail={COPY.metrics.pendingDetail}
              tone={counts.pending ? "danger" : "success"}
            />
            <Metric
              label={COPY.metrics.divergent}
              value={formatNumber(counts.divergent)}
              detail={COPY.metrics.divergentDetail}
              tone={counts.divergent ? "warning" : "neutral"}
            />
          </TonCard>

          <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <div className="sm:w-64">
                <InputSingleSelect
                  value={filter}
                  onValueChange={(value) => setFilter(value as Filter)}
                >
                  <InputSingleSelect.Trigger
                    placeholder={COPY.filters.label}
                    aria-label={COPY.filters.label}
                  />
                  <InputSingleSelect.Content>
                    {filters.map((item) => (
                      <InputSingleSelect.Item
                        key={item.value}
                        value={item.value}
                      >
                        {item.label}
                      </InputSingleSelect.Item>
                    ))}
                  </InputSingleSelect.Content>
                </InputSingleSelect>
              </div>
              <div className="sm:w-80">
                <InputTypeIn
                  searchIcon
                  aria-label={COPY.search}
                  placeholder={COPY.search}
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                icon={SvgSparkle}
                disabled={suggesting}
                onClick={() => void runSuggestions()}
                tooltip={COPY.suggestHint}
              >
                {suggesting ? COPY.suggesting : COPY.suggest}
              </Button>
              <Button
                prominence="secondary"
                icon={SvgDownload}
                onClick={() => void exportExcel()}
              >
                {COPY.exportExcel}
              </Button>
            </div>
          </div>

          {feedback && (
            <div role="status" className="flex items-center gap-2">
              {feedback.tone === "success" ? (
                <SvgCheckCircle size={16} className="ton-brand-text" />
              ) : (
                <SvgAlertTriangle size={16} className="text-status-error-05" />
              )}
              <Text font="secondary-body" color="text-04">
                {feedback.text}
              </Text>
            </div>
          )}

          <ClassificationList
            rows={visible}
            onReview={(row) => setReviewing(row.account_code)}
          />

          {current && (
            <ReviewDialog
              key={current.account_code}
              row={current}
              table={table.data}
              onClose={() => setReviewing(null)}
              onSaved={() => {
                setReviewing(null);
                void table.mutate();
              }}
            />
          )}
        </>
      )}
    </PageContainer>
  );
}
