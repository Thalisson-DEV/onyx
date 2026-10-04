"use client";

import { useEffect, useMemo, useState } from "react";
import { Button, InputTypeIn, Tabs, Text } from "@opal/components";
import {
  SvgAlertTriangle,
  SvgArrowRight,
  SvgCheckCircle,
  SvgDownload,
  SvgLock,
  SvgRefreshCw,
  SvgSparkle,
} from "@opal/icons";
import { useUser } from "@/providers/UserProvider";
import { formatRelativeDateTime } from "@/lib/ton/copy";
import {
  CLASSIFICATION_API,
  CLASSIFICATION_COPY as COPY,
  postJson,
  sectionOf,
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
import AccountPanel from "./AccountPanel";
import NaturesTab from "./NaturesTab";
import NewNatureDialog from "./NewNatureDialog";

type Feedback = { tone: "success" | "error"; text: string } | null;

/** Accounts per analysis request, and requests in flight at once. */
const CHUNK = 5;
const PARALLEL = 3;

function matchesQuery(row: ClassificationRow, query: string): boolean {
  const needle = query.trim().toLocaleLowerCase("pt-BR");
  if (!needle) return true;
  return [row.account_code, row.description, row.natureza ?? ""].some((value) =>
    value.toLocaleLowerCase("pt-BR").includes(needle)
  );
}

function FeedbackLine({ feedback }: { feedback: Feedback }) {
  if (!feedback) return null;
  return (
    <div role="status" className="flex items-center gap-2">
      {feedback.tone === "success" ? (
        <SvgCheckCircle size={16} className="ton-brand-text shrink-0" />
      ) : (
        <SvgAlertTriangle size={16} className="text-status-error-05 shrink-0" />
      )}
      <Text font="secondary-body" color="text-04">
        {feedback.text}
      </Text>
    </div>
  );
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

function AssistantCard({
  table,
  onChanged,
}: {
  table: ClassificationTable;
  onChanged: () => Promise<unknown>;
}) {
  const [running, setRunning] = useState(false);
  const [analyzed, setAnalyzed] = useState(0);
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(null);
  const open = table.rows.filter((row) => row.status !== "CONFIRMED");
  const agreeing = open.filter((row) => sectionOf(row) === "agrees");
  const decided = table.rows.filter((row) => row.decided_by_person).length;
  const total = decided + open.length;

  /** Small chunks keep every request far from the proxy timeout and let the
   * screen show progress; the briefing is written once at the end. */
  async function analyze() {
    const codes = open.map((row) => row.account_code);
    const chunks: string[][] = [];
    for (let index = 0; index < codes.length; index += CHUNK) {
      chunks.push(codes.slice(index, index + CHUNK));
    }
    setRunning(true);
    setFeedback(null);
    setAnalyzed(0);
    const results: SuggestionRunResult[] = [];
    let failures = 0;
    const queue = [...chunks];
    async function worker() {
      for (let chunk = queue.shift(); chunk; chunk = queue.shift()) {
        try {
          const result = await postJson<SuggestionRunResult>(
            `${CLASSIFICATION_API}/${table.source_id}/suggestions`,
            { account_codes: chunk, briefing: false }
          );
          results.push(result);
        } catch {
          failures += 1;
        }
        setAnalyzed((value) => value + chunk.length);
      }
    }
    try {
      await Promise.all(
        Array.from({ length: Math.min(PARALLEL, chunks.length) }, worker)
      );
      if (results.length) {
        await postJson(`${CLASSIFICATION_API}/${table.source_id}/briefing`, {});
      }
      const total: SuggestionRunResult = {
        requested: codes.length,
        suggested: results.reduce((sum, item) => sum + item.suggested, 0),
        skipped: results.flatMap((item) => item.skipped),
        model_name: results[0]?.model_name ?? null,
        briefing: true,
      };
      setFeedback(
        failures === chunks.length
          ? { tone: "error", text: COPY.assistant.failed }
          : { tone: "success", text: COPY.assistant.done(total) }
      );
      await onChanged();
    } catch {
      setFeedback({ tone: "error", text: COPY.assistant.failed });
    } finally {
      setRunning(false);
    }
  }

  async function confirmAgreeing() {
    setBusy(true);
    setFeedback(null);
    try {
      const result = await postJson<{ confirmed: number }>(
        `${CLASSIFICATION_API}/${table.source_id}/confirm-batch`,
        { account_codes: agreeing.map((row) => row.account_code) }
      );
      setFeedback({
        tone: "success",
        text: COPY.assistant.batchDone(result.confirmed),
      });
      setAsking(false);
      await onChanged();
    } catch {
      setFeedback({ tone: "error", text: CLASSIFICATION_COPY_FAILED });
    } finally {
      setBusy(false);
    }
  }

  return (
    <TonCard as="div" className="flex flex-col gap-4 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <span className="flex items-center gap-2">
          <SvgSparkle size={18} className="ton-brand-text" />
          <Text as="h2" font="heading-h3" color="text-05">
            {COPY.assistant.title}
          </Text>
        </span>
        {total > 0 && (
          <span className="flex min-w-[12rem] flex-col gap-1">
            <Text font="secondary-action" color="text-04">
              {COPY.assistant.progress(decided, total)}
            </Text>
            <span className="h-1.5 w-full overflow-hidden rounded-full bg-background-neutral-02">
              <span
                className="block h-full rounded-full"
                style={{
                  width: `${Math.round((decided / total) * 100)}%`,
                  background: "var(--ton-brand)",
                }}
              />
            </span>
          </span>
        )}
      </div>

      <Text as="p" font="main-ui-body" color="text-04">
        {open.length === 0
          ? COPY.assistant.allDone
          : (table.briefing?.summary ?? COPY.assistant.empty)}
      </Text>
      {table.briefing && (
        <Text font="secondary-body" color="text-03">
          {COPY.assistant.analyzed(
            formatRelativeDateTime(table.briefing.created_at)
          )}
        </Text>
      )}

      {asking ? (
        <div className="flex flex-col gap-2 rounded-12 border border-border-02 p-3">
          <Text font="secondary-body" color="text-04">
            {COPY.assistant.batchAsk(agreeing.length)}
          </Text>
          <span className="flex flex-wrap gap-2">
            <Button
              icon={SvgCheckCircle}
              disabled={busy}
              onClick={() => void confirmAgreeing()}
            >
              {busy ? COPY.panel.saving : COPY.assistant.batchYes}
            </Button>
            <Button
              prominence="tertiary"
              disabled={busy}
              onClick={() => setAsking(false)}
            >
              {COPY.assistant.batchNo}
            </Button>
          </span>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {agreeing.length > 0 && (
            <Button icon={SvgCheckCircle} onClick={() => setAsking(true)}>
              {COPY.assistant.batch(agreeing.length)}
            </Button>
          )}
          {open.length > 0 && (
            <Button
              prominence={agreeing.length ? "secondary" : "primary"}
              icon={table.briefing ? SvgRefreshCw : SvgSparkle}
              disabled={running}
              onClick={() => void analyze()}
            >
              {running
                ? COPY.assistant.analyzing(analyzed, open.length)
                : table.briefing
                  ? COPY.assistant.reanalyze
                  : COPY.assistant.analyze}
            </Button>
          )}
        </div>
      )}
      <FeedbackLine feedback={feedback} />
    </TonCard>
  );
}

const CLASSIFICATION_COPY_FAILED = COPY.panel.failed;

function RecomputeBanner({
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
    <div
      role="status"
      className="flex flex-wrap items-center justify-between gap-3 rounded-12 border border-border-02 bg-background-tint-01 px-4 py-3"
    >
      <Text font="secondary-body" color="text-04">
        {state === "done"
          ? COPY.recompute.done
          : state === "failed"
            ? COPY.recompute.failed
            : COPY.recompute.text(table.changes_since_calculation)}
      </Text>
      {state === "done" ? (
        <Button size="sm" rightIcon={SvgArrowRight} href="/ton/dre">
          {COPY.recompute.openDre}
        </Button>
      ) : (
        <Button
          size="sm"
          prominence="secondary"
          icon={SvgRefreshCw}
          disabled={state === "running"}
          onClick={() => void recompute()}
        >
          {state === "running" ? COPY.recompute.running : COPY.recompute.action}
        </Button>
      )}
    </div>
  );
}

export default function ClassificationPage() {
  const { hasAdminAccess } = useUser();
  const table = useClassificationTable(hasAdminAccess);
  const [tab, setTab] = useState("accounts");
  const [query, setQuery] = useState("");
  const [showConfirmed, setShowConfirmed] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [draft, setDraft] = useState<string | null>(null);
  const [creatingFor, setCreatingFor] = useState<string | null | undefined>(
    undefined
  );
  const [feedback, setFeedback] = useState<Feedback>(null);

  const rows = table.data?.rows ?? [];
  const visible = useMemo(
    () =>
      rows
        .filter((row) => matchesQuery(row, query))
        .filter((row) => showConfirmed || sectionOf(row) !== "confirmed"),
    [rows, query, showConfirmed]
  );
  // Grid order: sections first, then code order inside each.
  const ordered = useMemo(
    () =>
      (["needs_you", "agrees", "confirmed"] as const).flatMap((section) =>
        visible.filter((row) => sectionOf(row) === section)
      ),
    [visible]
  );
  const current =
    rows.find((row) => row.account_code === selected) ?? ordered[0] ?? null;
  const confirmedCount = rows.filter(
    (row) => sectionOf(row) === "confirmed"
  ).length;

  useEffect(() => {
    if (tab !== "accounts") return;
    function onKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (
        target &&
        (target.closest("input, textarea, [role='listbox'], [role='combobox']") ||
          target.isContentEditable)
      ) {
        return;
      }
      if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
      if (!ordered.length) return;
      event.preventDefault();
      const index = ordered.findIndex(
        (row) => row.account_code === current?.account_code
      );
      const next =
        event.key === "ArrowDown"
          ? Math.min(ordered.length - 1, index + 1)
          : Math.max(0, index - 1);
      const code = ordered[next]!.account_code;
      setSelected(code);
      setDraft(null);
      document
        .querySelector(`tr[data-code="${CSS.escape(code)}"]`)
        ?.scrollIntoView({ block: "nearest" });
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [tab, ordered, current]);

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

  /** After a decision, move to the next open account in grid order. */
  async function afterSave(code: string) {
    const index = ordered.findIndex((row) => row.account_code === code);
    const next = ordered
      .slice(index + 1)
      .find((row) => sectionOf(row) !== "confirmed");
    setFeedback({ tone: "success", text: COPY.panel.saved });
    await table.mutate();
    if (next) setSelected(next.account_code);
  }

  function natureCreated(nature: NatureView) {
    const forCode = creatingFor;
    setCreatingFor(undefined);
    setFeedback({ tone: "success", text: COPY.natures.created(nature.natureza) });
    void table.mutate().then(() => {
      if (forCode) {
        setSelected(forCode);
        setDraft(nature.account_id);
        setTab("accounts");
      }
    });
  }

  return (
    <PageContainer className="max-w-[1440px]">
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
                if (!ok) setFeedback({ tone: "error", text: COPY.exportFailed });
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
            <div className="flex flex-col gap-4 pt-4">
              <AssistantCard table={table.data} onChanged={table.mutate} />
              <RecomputeBanner table={table.data} onDone={table.mutate} />
              <FeedbackLine feedback={feedback} />
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 lg:items-start">
                <div className="flex flex-col gap-3 lg:col-span-7">
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="min-w-[14rem] flex-1">
                      <InputTypeIn
                        searchIcon
                        aria-label={COPY.list.search}
                        placeholder={COPY.list.search}
                        value={query}
                        onChange={(event) => setQuery(event.target.value)}
                      />
                    </div>
                    {confirmedCount > 0 && (
                      <Button
                        size="sm"
                        prominence="tertiary"
                        onClick={() => setShowConfirmed((value) => !value)}
                      >
                        {showConfirmed
                          ? COPY.list.hideConfirmed
                          : COPY.list.showConfirmed(confirmedCount)}
                      </Button>
                    )}
                    <Text font="secondary-body" color="text-03">
                      {COPY.list.keyboardHint}
                    </Text>
                  </div>
                  <AccountGrid
                    rows={ordered}
                    natures={table.data.natures}
                    selected={current?.account_code ?? null}
                    showConfirmed={showConfirmed}
                    onSelect={(code) => {
                      if (code !== current?.account_code) setDraft(null);
                      setSelected(code);
                    }}
                    onPick={(code, accountId) => {
                      setSelected(code);
                      setDraft(accountId);
                    }}
                    onNewNature={(code) => setCreatingFor(code)}
                  />
                </div>
                <div className="lg:col-span-5 lg:sticky lg:top-4">
                  <AccountPanel
                    key={current?.account_code ?? "none"}
                    row={current}
                    table={table.data}
                    draft={draft}
                    onDraft={setDraft}
                    onNewNature={() =>
                      setCreatingFor(current?.account_code ?? null)
                    }
                    onSaved={(code) => void afterSave(code)}
                  />
                </div>
              </div>
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
