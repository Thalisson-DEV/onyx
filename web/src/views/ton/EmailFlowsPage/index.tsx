"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import { Button, Text } from "@opal/components";
import { SvgLock, SvgPlus, SvgSparkle } from "@opal/icons";
import { formatDateTime } from "@/lib/ton/copy";
import {
  EMAIL_FLOWS_API,
  EMAIL_FLOWS_COPY as COPY,
  sendJson,
  useFlowTable,
  type FlowSummary,
  type FlowStatus,
  type RunView,
  type SuggestionRunResult,
} from "@/lib/ton/emailFlows";
import {
  EmptyState,
  ErrorState,
  LoadingBlock,
  PageContainer,
  PageHeader,
  StatusPill,
  type TonTone,
} from "@/views/ton/components/ui";

const STATUS_TONE: Record<FlowStatus, TonTone> = {
  SUGGESTED: "brand",
  ACTIVE: "success",
  PAUSED: "neutral",
  DISCARDED: "neutral",
};

function runTone(run: RunView): TonTone {
  if (run.status === "SENT") return "success";
  if (run.status === "FAILED" || run.status === "PARTIAL") return "danger";
  if (run.status === "NOT_CONFIGURED") return "warning";
  return "neutral";
}

function LastRun({ run }: { run: RunView | null }) {
  if (!run) {
    return (
      <Text font="secondary-body" color="text-03">
        {COPY.never}
      </Text>
    );
  }
  return (
    <span className="flex flex-col gap-0.5">
      <Text font="secondary-body" color="text-04">
        {formatDateTime(run.started_at)}
      </Text>
      <span>
        <StatusPill tone={runTone(run)}>{COPY.runStatus[run.status]}</StatusPill>
      </span>
    </span>
  );
}

function href(id: string): Route {
  return `/ton/fluxos/${id}` as Route;
}

export default function EmailFlowsPage() {
  const router = useRouter();
  const { data, error, isLoading, mutate } = useFlowTable();
  const [busy, setBusy] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  async function act(flow: FlowSummary, action: "activate" | "discard") {
    setBusy(flow.id);
    setFeedback(null);
    try {
      await sendJson(`${EMAIL_FLOWS_API}/${flow.id}/${action}`, {});
      await mutate();
    } catch (failure) {
      // A suggestion without recipients cannot be registered from the row.
      if (action === "activate") router.push(href(flow.id));
      else setFeedback(failure instanceof Error ? failure.message : String(failure));
    } finally {
      setBusy(null);
    }
  }

  async function suggest() {
    setBusy("suggest");
    setFeedback(null);
    try {
      const result = await sendJson<SuggestionRunResult>(
        `${EMAIL_FLOWS_API}/suggestions`,
        {}
      );
      setFeedback(COPY.suggested(result.created));
      await mutate();
    } catch (failure) {
      setFeedback(failure instanceof Error ? failure.message : String(failure));
    } finally {
      setBusy(null);
    }
  }

  const forbidden =
    error && typeof error === "object" && "status" in error && error.status === 403;

  return (
    <PageContainer>
      <PageHeader
        eyebrow={COPY.eyebrow}
        title={COPY.title}
        description={COPY.description}
        actions={
          data?.can_manage ? (
            <>
              <Button
                prominence="secondary"
                icon={SvgSparkle}
                disabled={busy !== null}
                onClick={suggest}
              >
                {busy === "suggest" ? COPY.suggesting : COPY.suggest}
              </Button>
              <Button icon={SvgPlus} href={href("novo")}>
                {COPY.newFlow}
              </Button>
            </>
          ) : undefined
        }
      />
      {feedback && (
        <Text font="secondary-body" color="text-04">
          {feedback}
        </Text>
      )}
      {data && !data.provider_ready && (
        <Text font="secondary-body" color="text-03">
          {COPY.providerMissing}
        </Text>
      )}
      {forbidden ? (
        <EmptyState icon={SvgLock} title={COPY.noAccessTitle} description={COPY.noAccess} />
      ) : error ? (
        <ErrorState message={COPY.error} onRetry={() => mutate()} />
      ) : isLoading || !data ? (
        <div className="ton-card p-5">
          <LoadingBlock label={COPY.loading} lines={4} />
        </div>
      ) : data.flows.length === 0 ? (
        <div className="ton-card p-5">
          <Text font="main-ui-body" color="text-03">
            {COPY.empty}
          </Text>
        </div>
      ) : (
        <div className="ton-card overflow-x-auto">
          <table className="ton-statement ton-classification-grid w-full min-w-[960px] border-collapse">
            <thead>
              <tr>
                <th scope="col">{COPY.columns.flow}</th>
                <th scope="col">{COPY.columns.when}</th>
                <th scope="col">{COPY.columns.condition}</th>
                <th scope="col">{COPY.columns.yes}</th>
                <th scope="col">{COPY.columns.no}</th>
                <th scope="col">{COPY.columns.lastRun}</th>
                <th scope="col">{COPY.columns.status}</th>
              </tr>
            </thead>
            <tbody>
              {data.flows.map((flow) => (
                <tr
                  key={flow.id}
                  className="cursor-pointer"
                  onClick={() => router.push(href(flow.id))}
                >
                  <td>
                    <Text font="main-ui-action" color="text-05">
                      {flow.name}
                    </Text>
                  </td>
                  <td>
                    <Text font="secondary-body" color="text-04">
                      {flow.when}
                    </Text>
                  </td>
                  <td>
                    <Text font="secondary-body" color="text-04">
                      {flow.condition}
                    </Text>
                  </td>
                  <td>
                    <Text font="secondary-body" color="text-04">
                      {flow.on_yes}
                    </Text>
                  </td>
                  <td>
                    <Text font="secondary-body" color="text-03">
                      {flow.on_no}
                    </Text>
                  </td>
                  <td>
                    <LastRun run={flow.last_run} />
                  </td>
                  <td onClick={(event) => event.stopPropagation()}>
                    <span className="flex flex-col items-start gap-1.5">
                      <StatusPill tone={STATUS_TONE[flow.status]}>
                        {COPY.status[flow.status]}
                      </StatusPill>
                      {flow.status === "SUGGESTED" && data.can_manage && (
                        <span className="flex gap-1.5">
                          <Button
                            size="sm"
                            disabled={busy !== null}
                            onClick={() => act(flow, "activate")}
                          >
                            {COPY.register}
                          </Button>
                          <Button
                            size="sm"
                            prominence="tertiary"
                            disabled={busy !== null}
                            onClick={() => act(flow, "discard")}
                          >
                            {COPY.discard}
                          </Button>
                        </span>
                      )}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </PageContainer>
  );
}
