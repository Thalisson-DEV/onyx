"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import { Button, Popover, Text } from "@opal/components";
import {
  SvgFolderIn,
  SvgCopy,
  SvgEdit,
  SvgMoreHorizontal,
  SvgPauseCircle,
  SvgPlayCircle,
  SvgRevert,
  SvgZap,
} from "@opal/icons";
import {
  AUTOMATIONS_API,
  COPY,
  KIND_LABELS,
  MODE_LABELS,
  RUN_STATUS_LABELS,
  STATUS_LABELS,
  send,
  useAutomation,
  type AutomationDetail,
  type AutomationStatus,
  type JsonValue,
  type RunStatus,
  type RunSummary,
} from "@/lib/ton/automations";
import { formatDateTime } from "@/lib/ton/copy";
import { ErrorState, LoadingBlock, PageContainer, StatusPill, TonCard, type TonTone } from "@/views/ton/components/ui";
import { formatDuration } from "@/views/ton/AutomationsPage/designer/CanvasNodes";
import { RunModal } from "@/views/ton/AutomationsPage/designer/dialogs";

export const RUN_TONE: Record<RunStatus, TonTone> = {
  QUEUED: "neutral",
  RUNNING: "brand",
  WAITING: "warning",
  SUCCEEDED: "success",
  FAILED: "danger",
  CANCELLED: "neutral",
  TIMED_OUT: "danger",
};
export const STATUS_TONE: Record<AutomationStatus, TonTone> = { ACTIVE: "success", DRAFT: "neutral", PAUSED: "warning", ARCHIVED: "neutral" };

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <Text font="secondary-action" color="text-04">
        {label}
      </Text>
      <Text font="main-ui-body" color="text-05">
        {value}
      </Text>
    </div>
  );
}

function History({ detail }: { detail: AutomationDetail }) {
  return (
    <TonCard className="flex flex-col gap-3 p-5" labelledBy="ton-auto-history">
      <div className="flex items-center justify-between gap-2">
        <Text as="h2" id="ton-auto-history" font="main-ui-action" color="text-05">
          {COPY.history}
        </Text>
      </div>
      {detail.runs.length === 0 ? (
        <Text font="secondary-body" color="text-03">
          {COPY.noRuns}
        </Text>
      ) : (
        <table className="ton-statement ton-classification-grid w-full border-collapse">
          <thead>
            <tr>
              <th scope="col">{COPY.start}</th>
              <th scope="col">{COPY.mode}</th>
              <th scope="col" data-numeric>
                {COPY.duration}
              </th>
              <th scope="col">{COPY.status}</th>
            </tr>
          </thead>
          <tbody>
            {detail.runs.map((run: RunSummary) => (
              <tr key={run.id} className="ton-auto-run-row">
                <td>
                  <Link href={`/ton/automacoes/${detail.id}/execucoes/${run.id}` as Route} className="ton-row-link ton-focusable" aria-label={formatDateTime(run.created_at)}>
                    <Text font="secondary-body" color="text-05">
                      {formatDateTime(run.created_at)}
                    </Text>
                  </Link>
                </td>
                <td>
                  <Text font="secondary-body" color="text-04">
                    {`${MODE_LABELS[run.mode]}${run.triggered_by ? ` · ${run.triggered_by}` : ""}`}
                  </Text>
                </td>
                <td data-numeric>
                  <Text font="secondary-body" color="text-04">
                    {run.duration_ms !== null ? formatDuration(run.duration_ms) : "—"}
                  </Text>
                </td>
                <td>
                  <span className="flex flex-col gap-0.5">
                    <StatusPill tone={RUN_TONE[run.status]}>{RUN_STATUS_LABELS[run.status]}</StatusPill>
                    {run.error && (
                      <Text font="secondary-body" color="text-03" maxLines={2}>
                        {run.error}
                      </Text>
                    )}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </TonCard>
  );
}

export default function DetailPage({ automationId }: { automationId: string }) {
  const router = useRouter();
  const detail = useAutomation(automationId);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runModal, setRunModal] = useState<"run" | "test" | null>(null);

  if (detail.error) return <ErrorState onRetry={() => detail.mutate()} />;
  if (!detail.data) return <LoadingBlock label="…" />;
  const data = detail.data;
  const runs = data.runs.filter((run) => run.mode !== "TEST");
  const succeeded = runs.filter((run) => run.status === "SUCCEEDED").length;

  async function act(path: string, body: Parameters<typeof send>[1] = {}) {
    setBusy(true);
    setError(null);
    try {
      const result = await send<AutomationDetail>(`${AUTOMATIONS_API}/${automationId}${path}`, body);
      if (path === "/duplicate") router.push(`/ton/automacoes/${result.id}/editar` as Route);
      else await detail.mutate(result, { revalidate: false });
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : String(failure));
    } finally {
      setBusy(false);
    }
  }

  async function run(inputs: Record<string, JsonValue>) {
    const test = runModal === "test";
    setBusy(true);
    setError(null);
    try {
      const result = await send<RunSummary>(`${AUTOMATIONS_API}/${automationId}/${test ? "test" : "run"}`, { inputs });
      setRunModal(null);
      router.push(`/ton/automacoes/${automationId}/execucoes/${result.id}` as Route);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : String(failure));
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageContainer>
      <nav className="flex items-center gap-2" aria-label={COPY.title}>
        <Link href="/ton/automacoes" className="ton-brand-text ton-focusable">
          <Text font="main-ui-body" color="text-03">
            {COPY.title}
          </Text>
        </Link>
        <Text font="main-ui-body" color="text-03">
          {"›"}
        </Text>
        <Text as="h1" font="heading-h3" color="text-05">
          {data.name}
        </Text>
        <StatusPill tone={STATUS_TONE[data.status]}>{STATUS_LABELS[data.status]}</StatusPill>
      </nav>
      {data.can_manage && (
        <div className="flex flex-wrap items-center gap-2">
          <Button icon={SvgEdit} href={`/ton/automacoes/${automationId}/editar`}>
            {COPY.edit}
          </Button>
          <Button prominence="secondary" icon={SvgZap} disabled={busy} onClick={() => setRunModal("test")}>
            {COPY.test}
          </Button>
          <Button prominence="secondary" icon={SvgPlayCircle} disabled={busy || data.problems.length > 0} onClick={() => setRunModal("run")}>
            {COPY.run}
          </Button>
          {data.status === "ACTIVE" ? (
            <Button prominence="tertiary" icon={SvgPauseCircle} disabled={busy} onClick={() => void act("/status", { status: "PAUSED" })}>
              {COPY.pause}
            </Button>
          ) : data.status !== "ARCHIVED" ? (
            <Button prominence="tertiary" icon={SvgPlayCircle} disabled={busy || data.problems.length > 0} onClick={() => void act("/status", { status: "ACTIVE" })}>
              {COPY.activate}
            </Button>
          ) : (
            <Button prominence="tertiary" icon={SvgRevert} disabled={busy} onClick={() => void act("/status", { status: "PAUSED" })}>
              {COPY.restore}
            </Button>
          )}
          <Popover>
            <Popover.Trigger asChild>
              <Button prominence="tertiary" icon={SvgMoreHorizontal} aria-label={COPY.details} />
            </Popover.Trigger>
            <Popover.Content align="start">
              <Popover.Menu>
                {[
                  <Button key="dup" prominence="tertiary" icon={SvgCopy} width="full" onClick={() => void act("/duplicate")}>
                    {COPY.duplicate}
                  </Button>,
                  data.status !== "ARCHIVED" && data.status !== "ACTIVE" ? (
                    <Button key="arch" prominence="tertiary" variant="danger" icon={SvgFolderIn} width="full" onClick={() => void act("/status", { status: "ARCHIVED" })}>
                      {COPY.archive}
                    </Button>
                  ) : undefined,
                ]}
              </Popover.Menu>
            </Popover.Content>
          </Popover>
        </div>
      )}
      {error && (
        <div className="ton-auto-banner" data-tone="error">
          <Text font="secondary-body" color="text-05">
            {error}
          </Text>
        </div>
      )}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] items-start">
        <div className="flex flex-col gap-5">
          <TonCard className="flex flex-col gap-4 p-5" labelledBy="ton-auto-details">
            <Text as="h2" id="ton-auto-details" font="main-ui-action" color="text-05">
              {COPY.details}
            </Text>
            {data.description && (
              <Text font="main-ui-body" color="text-04">
                {data.description}
              </Text>
            )}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Info label={COPY.type} value={KIND_LABELS[data.kind]} />
              <Info label={COPY.trigger} value={data.when} />
              <Info label={COPY.owner} value={data.owner ?? "—"} />
              <Info label={COPY.version} value={`v${data.version} · ${COPY.steps(data.steps_count)}`} />
              <Info label={COPY.createdAt} value={`${formatDateTime(data.created_at)}${data.created_by ? ` · ${data.created_by}` : ""}`} />
              <Info label={COPY.updatedAt} value={`${formatDateTime(data.updated_at)}${data.updated_by ? ` · ${data.updated_by}` : ""}`} />
              {data.next_run_at && <Info label={COPY.nextRun} value={formatDateTime(data.next_run_at)} />}
            </div>
            {data.problems.length > 0 && (
              <div className="ton-auto-banner" data-tone="warning">
                <div className="flex flex-col gap-1">
                  <Text font="secondary-action" color="text-05">
                    {COPY.pending}
                  </Text>
                  {data.problems.slice(0, 8).map((problem) => (
                    <Text key={problem} font="secondary-body" color="text-04">
                      {`• ${problem}`}
                    </Text>
                  ))}
                </div>
              </div>
            )}
          </TonCard>
          <History detail={data} />
        </div>
        <div className="flex flex-col gap-5">
          <TonCard className="flex flex-col gap-4 p-5">
            <Info label={COPY.averageDuration} value={data.average_duration_ms !== null ? formatDuration(data.average_duration_ms) : "—"} />
            <Info label={COPY.successRate} value={runs.length ? `${succeeded} de ${runs.length}` : "—"} />
          </TonCard>
          <TonCard className="flex flex-col gap-2 p-5" labelledBy="ton-auto-versions">
            <Text as="h2" id="ton-auto-versions" font="main-ui-action" color="text-05">
              {COPY.versions}
            </Text>
            <ul className="flex flex-col divide-y divide-border-01">
              {data.versions.slice(0, 12).map((version) => (
                <li key={version.version} className="flex items-center justify-between gap-2 py-2">
                  <span className="flex min-w-0 flex-col">
                    <Text font="secondary-action" color="text-05">
                      {`v${version.version}${version.note ? ` · ${version.note}` : ""}`}
                    </Text>
                    <Text font="secondary-body" color="text-03">
                      {`${formatDateTime(version.created_at)}${version.created_by ? ` · ${version.created_by}` : ""}`}
                    </Text>
                  </span>
                  {data.can_manage && version.version !== data.version && (
                    <Button size="sm" prominence="tertiary" icon={SvgRevert} tooltip={COPY.restore} aria-label={COPY.restore} disabled={busy} onClick={() => void act(`/versions/${version.version}/restore`)} />
                  )}
                </li>
              ))}
            </ul>
          </TonCard>
        </div>
      </div>
      <RunModal open={runModal !== null} test={runModal === "test"} definition={data.definition} busy={busy} error={error} onRun={(inputs) => void run(inputs)} onClose={() => setRunModal(null)} />
    </PageContainer>
  );
}
