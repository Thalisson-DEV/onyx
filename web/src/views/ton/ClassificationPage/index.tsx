"use client";

import { useMemo, useState } from "react";
import {
  Button,
  InputSingleSelect,
  InputTypeIn,
  Tabs,
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
  CLASSIFICATION_API,
  CLASSIFICATION_COPY as COPY,
  agrees,
  isOpen,
  postJson,
  useClassificationTable,
  type ClassificationRow,
  type ClassificationTable,
  type NatureView,
  type SuggestionRunResult,
} from "@/lib/ton/classification";
import {
  BackLink,
  EmptyState,
  ErrorState,
  LoadingBlock,
  PageContainer,
  PageHeader,
  TonCard,
} from "@/views/ton/components/ui";
import AccountGrid from "./AccountGrid";
import NaturesTab from "./NaturesTab";
import NewNatureDialog from "./NewNatureDialog";

type Filter = "open" | "confirmed" | "all";
type Feedback = { tone: "success" | "error"; text: string } | null;

/** Accounts per assistant request, and requests in flight at once: keeps each
 * request far from the proxy timeout and lets the button show progress. */
const CHUNK = 5;
const PARALLEL = 3;

function matchesQuery(row: ClassificationRow, query: string): boolean {
  const needle = query.trim().toLocaleLowerCase("pt-BR");
  if (!needle) return true;
  return [row.account_code, row.description, row.natureza ?? ""].some((value) =>
    value.toLocaleLowerCase("pt-BR").includes(needle)
  );
}

/** Open accounts the assistant disagrees with come first. */
function rank(row: ClassificationRow): number {
  if (!isOpen(row)) return 2;
  return agrees(row) ? 1 : 0;
}

async function downloadWorkbook(): Promise<boolean> {
  const response = await fetch(`${CLASSIFICATION_API}/export.xlsx`);
  if (!response.ok) return false;
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "ton-classificacao-contas.xlsx";
  anchor.click();
  URL.revokeObjectURL(url);
  return true;
}

function FeedbackLine({ feedback }: { feedback: Feedback }) {
  if (!feedback) return <span />;
  return (
    <span role="status" className="flex items-center gap-1.5">
      {feedback.tone === "success" ? (
        <SvgCheckCircle size={14} className="ton-brand-text shrink-0" />
      ) : (
        <SvgAlertTriangle size={14} className="text-status-error-05 shrink-0" />
      )}
      <Text font="secondary-body" color="text-04">
        {feedback.text}
      </Text>
    </span>
  );
}

function Actions({
  table,
  onChanged,
  onFeedback,
}: {
  table: ClassificationTable;
  onChanged: () => Promise<unknown>;
  onFeedback: (feedback: Feedback) => void;
}) {
  const [progress, setProgress] = useState<number | null>(null);
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const open = table.rows.filter(isOpen);
  const agreeing = open.filter(agrees);

  async function suggest() {
    const codes = open.map((row) => row.account_code);
    const queue: string[][] = [];
    for (let index = 0; index < codes.length; index += CHUNK) {
      queue.push(codes.slice(index, index + CHUNK));
    }
    const total = queue.length;
    let suggested = 0;
    let failures = 0;
    setProgress(0);
    onFeedback(null);
    async function worker() {
      for (let chunk = queue.shift(); chunk; chunk = queue.shift()) {
        try {
          const result = await postJson<SuggestionRunResult>(
            `${CLASSIFICATION_API}/${table.source_id}/suggestions`,
            { account_codes: chunk, briefing: false }
          );
          suggested += result.suggested;
        } catch {
          failures += 1;
        }
        const size = chunk.length;
        setProgress((value) => (value ?? 0) + size);
      }
    }
    await Promise.all(
      Array.from({ length: Math.min(PARALLEL, total) }, worker)
    );
    setProgress(null);
    onFeedback(
      failures === total
        ? { tone: "error", text: COPY.suggestFailed }
        : {
            tone: "success",
            text: COPY.suggestDone({ suggested, requested: codes.length }),
          }
    );
    await onChanged();
  }

  async function confirmAgreeing() {
    setBusy(true);
    try {
      const result = await postJson<{ confirmed: number }>(
        `${CLASSIFICATION_API}/${table.source_id}/confirm-batch`,
        { account_codes: agreeing.map((row) => row.account_code) }
      );
      onFeedback({ tone: "success", text: COPY.batchDone(result.confirmed) });
      setAsking(false);
      await onChanged();
    } catch {
      onFeedback({ tone: "error", text: COPY.failed });
    } finally {
      setBusy(false);
    }
  }

  if (asking) {
    return (
      <span className="flex items-center gap-2">
        <Text font="secondary-body" color="text-04">
          {COPY.batchAsk(agreeing.length)}
        </Text>
        <Button
          size="sm"
          icon={SvgCheckCircle}
          disabled={busy}
          onClick={() => void confirmAgreeing()}
        >
          {busy ? COPY.saving : COPY.batchYes}
        </Button>
        <Button
          size="sm"
          prominence="tertiary"
          disabled={busy}
          onClick={() => setAsking(false)}
        >
          {COPY.batchNo}
        </Button>
      </span>
    );
  }
  return (
    <span className="flex flex-wrap items-center gap-2">
      {agreeing.length > 0 && (
        <Button size="sm" icon={SvgCheckCircle} onClick={() => setAsking(true)}>
          {COPY.batch(agreeing.length)}
        </Button>
      )}
      {open.length > 0 && (
        <Button
          size="sm"
          prominence="secondary"
          icon={SvgSparkle}
          disabled={progress !== null}
          onClick={() => void suggest()}
        >
          {progress !== null
            ? COPY.suggesting(progress, open.length)
            : COPY.suggest}
        </Button>
      )}
    </span>
  );
}

function RecomputeLink({
  table,
  onDone,
}: {
  table: ClassificationTable;
  onDone: () => Promise<unknown>;
}) {
  const [state, setState] = useState<"idle" | "running" | "done" | "failed">(
    "idle"
  );
  if (!table.normalization_run_id) return null;
  if (table.changes_since_calculation === 0 && state !== "done") return null;
  if (state === "done") {
    return (
      <Text font="secondary-body" color="text-03">
        {COPY.recompute.done}
      </Text>
    );
  }

  async function recompute() {
    setState("running");
    try {
      await postJson(
        `/api/ton/financial-domain/normalizations/${table.normalization_run_id}/recompute`,
        {}
      );
      setState("done");
      await onDone();
    } catch {
      setState("failed");
    }
  }

  return (
    <span className="flex items-center gap-2">
      <Text font="secondary-body" color="text-03">
        {state === "failed"
          ? COPY.recompute.failed
          : COPY.recompute.text(table.changes_since_calculation)}
      </Text>
      <Button
        size="sm"
        prominence="tertiary"
        disabled={state === "running"}
        onClick={() => void recompute()}
      >
        {state === "running" ? COPY.recompute.running : COPY.recompute.action}
      </Button>
    </span>
  );
}

export default function ClassificationPage() {
  const { hasAdminAccess } = useUser();
  const table = useClassificationTable(hasAdminAccess);
  const [tab, setTab] = useState("accounts");
  const [filter, setFilter] = useState<Filter>("open");
  const [query, setQuery] = useState("");
  const [creatingFor, setCreatingFor] = useState<string | null | undefined>(
    undefined
  );
  const [pending, setPending] = useState<{
    code: string;
    accountId: string;
  } | null>(null);
  const [feedback, setFeedback] = useState<Feedback>(null);

  const rows = useMemo(() => table.data?.rows ?? [], [table.data]);
  const counts = {
    open: rows.filter(isOpen).length,
    confirmed: rows.filter((row) => !isOpen(row)).length,
    all: rows.length,
  };
  const visible = useMemo(
    () =>
      rows
        .filter((row) =>
          filter === "all"
            ? true
            : filter === "open"
              ? isOpen(row)
              : !isOpen(row)
        )
        .filter((row) => matchesQuery(row, query))
        .map((row, index) => ({ row, index }))
        .sort((a, b) => rank(a.row) - rank(b.row) || a.index - b.index)
        .map((item) => item.row),
    [rows, filter, query]
  );

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

  function natureCreated(nature: NatureView) {
    const forCode = creatingFor;
    setCreatingFor(undefined);
    setFeedback({
      tone: "success",
      text: COPY.natures.created(nature.natureza),
    });
    void table.mutate().then(() => {
      if (forCode) {
        setTab("accounts");
        setPending({ code: forCode, accountId: nature.account_id });
      }
    });
  }

  return (
    <PageContainer className="max-w-[1280px]">
      <BackLink href="/ton/administracao" label={COPY.back} />
      <PageHeader
        eyebrow={COPY.eyebrow}
        title={COPY.title}
        description={COPY.description}
        actions={
          <Button
            prominence="secondary"
            icon={SvgDownload}
            onClick={() =>
              void downloadWorkbook().then((ok) => {
                if (!ok)
                  setFeedback({ tone: "error", text: COPY.exportFailed });
              })
            }
          >
            {COPY.exportExcel}
          </Button>
        }
      />
      {table.isLoading && (
        <TonCard className="p-5">
          <LoadingBlock label={COPY.loading} />
        </TonCard>
      )}
      {table.error && <ErrorState onRetry={() => table.mutate()} />}
      {table.data && (
        <Tabs value={tab} onValueChange={setTab} variant="underline">
          <Tabs.List>
            <Tabs.Trigger value="accounts">{COPY.tabs.accounts}</Tabs.Trigger>
            <Tabs.Trigger value="natures">{COPY.tabs.natures}</Tabs.Trigger>
          </Tabs.List>
          <Tabs.Content value="accounts">
            <div className="flex flex-col gap-3 pt-4">
              <div className="flex flex-wrap items-center gap-2">
                <div className="w-full sm:w-72">
                  <InputTypeIn
                    searchIcon
                    aria-label={COPY.search}
                    placeholder={COPY.search}
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                  />
                </div>
                <div className="w-full sm:w-56">
                  <InputSingleSelect
                    value={filter}
                    onValueChange={(value) => setFilter(value as Filter)}
                  >
                    <InputSingleSelect.Trigger
                      placeholder={COPY.filters.label}
                      aria-label={COPY.filters.label}
                    />
                    <InputSingleSelect.Content>
                      <InputSingleSelect.Item value="open">
                        {COPY.filters.open(counts.open)}
                      </InputSingleSelect.Item>
                      <InputSingleSelect.Item value="confirmed">
                        {COPY.filters.confirmed(counts.confirmed)}
                      </InputSingleSelect.Item>
                      <InputSingleSelect.Item value="all">
                        {COPY.filters.all(counts.all)}
                      </InputSingleSelect.Item>
                    </InputSingleSelect.Content>
                  </InputSingleSelect>
                </div>
                <span className="ms-auto">
                  <Actions
                    table={table.data}
                    onChanged={table.mutate}
                    onFeedback={setFeedback}
                  />
                </span>
              </div>
              {(feedback || table.data.changes_since_calculation > 0) && (
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <FeedbackLine feedback={feedback} />
                  <RecomputeLink table={table.data} onDone={table.mutate} />
                </div>
              )}
              <AccountGrid
                table={table.data}
                rows={visible}
                onNewNature={(code) => setCreatingFor(code)}
                onSaved={table.mutate}
                pending={pending}
                onPendingUsed={() => setPending(null)}
              />
            </div>
          </Tabs.Content>
          <Tabs.Content value="natures">
            <div className="pt-4">
              <NaturesTab
                table={table.data}
                onCreate={() => setCreatingFor(null)}
              />
            </div>
          </Tabs.Content>
        </Tabs>
      )}
      {table.data && creatingFor !== undefined && (
        <NewNatureDialog
          groups={table.data.groups}
          defaultGroup={
            creatingFor
              ? (table.data.natures.find(
                  (item) =>
                    item.account_id ===
                    rows.find((row) => row.account_code === creatingFor)
                      ?.account_id
                )?.dre_group_code ?? null)
              : null
          }
          onClose={() => setCreatingFor(undefined)}
          onCreated={natureCreated}
        />
      )}
    </PageContainer>
  );
}
