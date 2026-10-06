"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import {
  Button,
  InputSingleSelect,
  InputTextArea,
  InputTypeIn,
  Modal,
  Text,
} from "@opal/components";
import { SvgBubbleText, SvgLock, SvgMail, SvgPlus } from "@opal/icons";
import { formatDateTime } from "@/lib/ton/copy";
import {
  EMAIL_FLOWS_API,
  EMAIL_FLOWS_COPY as COPY,
  assetUrl,
  sendJson,
  uploadAsset,
  useFlowCatalog,
  useFlowTable,
  type ApprovalView,
  type FlowStatus,
  type FlowSummary,
  type LayoutView,
  type RunView,
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

const STATUS_TONE = {
  SUGGESTED: "brand",
  ACTIVE: "success",
  PAUSED: "neutral",
  DISCARDED: "neutral",
} satisfies Record<FlowStatus, TonTone>;

function runTone(run: RunView): TonTone {
  if (run.status === "SENT") return "success";
  if (run.status === "FAILED" || run.status === "PARTIAL") return "danger";
  if (run.status === "NOT_CONFIGURED" || run.status === "WAITING") return "warning";
  return "neutral";
}

function href(id: string): Route {
  return `/ton/fluxos/${id}` as Route;
}

function chatHref(): Route {
  // Pre-filled, not sent: the person completes the request in the chat.
  return `/ton/chat?${new URLSearchParams({ firstMessage: COPY.askTonPrompt }).toString()}` as Route;
}

function LastRun({ run }: { run: RunView | null }) {
  if (!run)
    return (
      <Text font="secondary-body" color="text-03">
        {COPY.never}
      </Text>
    );
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

function StepsCell({ flow }: { flow: FlowSummary }) {
  const lines = flow.steps_text.slice(0, 3);
  return (
    <span className="flex flex-col gap-0.5">
      {lines.map((line, index) => (
        <span key={index} style={{ paddingInlineStart: `${line.depth * 12}px` }}>
          <Text font="secondary-body" color="text-04">
            {line.text}
          </Text>
        </span>
      ))}
      {flow.steps_text.length > 3 && (
        <Text font="secondary-body" color="text-03">
          {`+ ${flow.steps_text.length - 3}`}
        </Text>
      )}
    </span>
  );
}

function Approvals({ approvals, onDecided }: { approvals: ApprovalView[]; onDecided: () => Promise<void> }) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  async function decide(approval: ApprovalView, approve: boolean) {
    setBusy(approval.id);
    setError(null);
    try {
      await sendJson(`${EMAIL_FLOWS_API}/approvals/${approval.id}/decide`, { approve });
      await onDecided();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : String(failure));
    } finally {
      setBusy(null);
    }
  }
  return (
    <section className="ton-card flex flex-col gap-2 p-4">
      <Text font="main-ui-action" color="text-05">
        {COPY.approvals.title}
      </Text>
      {approvals.map((approval) => (
        <div key={approval.id} className="flex flex-wrap items-center justify-between gap-3">
          <span className="flex flex-col">
            <Text font="secondary-action" color="text-05">
              {`${approval.flow_name} · ${COPY.approvals.items(approval.item_count)}`}
            </Text>
            <Text font="secondary-body" color="text-03">
              {[approval.message, formatDateTime(approval.created_at)].filter(Boolean).join(" · ")}
            </Text>
          </span>
          {approval.can_decide && (
            <span className="flex gap-1.5">
              <Button size="sm" disabled={busy !== null} onClick={() => decide(approval, true)}>
                {COPY.approvals.approve}
              </Button>
              <Button size="sm" prominence="secondary" disabled={busy !== null} onClick={() => decide(approval, false)}>
                {COPY.approvals.reject}
              </Button>
            </span>
          )}
        </div>
      ))}
      {error && (
        <Text font="secondary-body" color="text-05">
          {error}
        </Text>
      )}
    </section>
  );
}

function LayoutModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const catalog = useFlowCatalog();
  const L = COPY.layout;
  const [draft, setDraft] = useState<LayoutView | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const layout = draft ?? catalog.data?.layout ?? null;

  async function save() {
    if (!layout) return;
    try {
      await sendJson(`${EMAIL_FLOWS_API}/layout`, layout, "PUT");
      setMessage(L.saved);
      await catalog.mutate();
    } catch (failure) {
      setMessage(failure instanceof Error ? failure.message : String(failure));
    }
  }

  return (
    <Modal open={open} onOpenChange={(value) => !value && onClose()}>
      <Modal.Content width="md">
        <Modal.Header icon={SvgMail} title={L.title} description={L.description} onClose={onClose} />
        <Modal.Body>
          {!layout || !catalog.data ? (
            <LoadingBlock label={COPY.loading} lines={3} />
          ) : (
            <div className="flex flex-col gap-4">
              <label className="flex flex-col gap-1.5">
                <Text font="secondary-action" color="text-04">
                  {L.color}
                </Text>
                <span className="flex items-center gap-2">
                  <span className="ton-composer-swatch" style={{ background: layout.brand_color }} />
                  <InputTypeIn
                    aria-label={L.color}
                    value={layout.brand_color}
                    maxLength={7}
                    onChange={(event) => setDraft({ ...layout, brand_color: event.target.value })}
                  />
                </span>
              </label>
              <label className="flex flex-col gap-1.5">
                <Text font="secondary-action" color="text-04">
                  {L.logo}
                </Text>
                <InputSingleSelect
                  value={layout.logo_asset_id ?? "__none"}
                  onValueChange={(value) => {
                    if (value === "__upload") fileRef.current?.click();
                    else setDraft({ ...layout, logo_asset_id: value === "__none" ? null : value });
                  }}
                >
                  <InputSingleSelect.Trigger aria-label={L.logo} placeholder={L.logo} />
                  <InputSingleSelect.Content>
                    <InputSingleSelect.Item value="__none">{L.noLogo}</InputSingleSelect.Item>
                    {catalog.data.assets.map((asset) => (
                      <InputSingleSelect.Item key={asset.id} value={asset.id}>
                        {asset.name}
                      </InputSingleSelect.Item>
                    ))}
                    <InputSingleSelect.Item value="__upload">{L.upload}</InputSingleSelect.Item>
                  </InputSingleSelect.Content>
                </InputSingleSelect>
                {layout.logo_asset_id && (
                  <img src={assetUrl(layout.logo_asset_id)} alt={L.logo} className="ton-layout-logo" />
                )}
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/png,image/jpeg,image/gif"
                  hidden
                  onChange={async (event) => {
                    const file = event.target.files?.[0];
                    event.target.value = "";
                    if (!file) return;
                    const asset = await uploadAsset(file);
                    await catalog.mutate();
                    setDraft({ ...layout, logo_asset_id: asset.id });
                  }}
                />
              </label>
              <label className="flex flex-col gap-1.5">
                <Text font="secondary-action" color="text-04">
                  {L.footer}
                </Text>
                <InputTextArea rows={3} value={layout.footer} onChange={(event) => setDraft({ ...layout, footer: event.target.value })} />
              </label>
              {message && (
                <Text font="secondary-body" color="text-03">
                  {message}
                </Text>
              )}
            </div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button onClick={save} disabled={!layout}>
            {L.save}
          </Button>
        </Modal.Footer>
      </Modal.Content>
    </Modal>
  );
}

export default function EmailFlowsPage() {
  const router = useRouter();
  const { data, error, isLoading, mutate } = useFlowTable();
  const [busy, setBusy] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [layoutOpen, setLayoutOpen] = useState(false);

  async function act(flow: FlowSummary, action: "activate" | "discard") {
    if (action === "activate" && flow.problems.length) {
      router.push(href(flow.id));
      return;
    }
    setBusy(flow.id);
    setFeedback(null);
    try {
      await sendJson(`${EMAIL_FLOWS_API}/${flow.id}/${action}`, {});
      await mutate();
    } catch (failure) {
      setFeedback(failure instanceof Error ? failure.message : String(failure));
    } finally {
      setBusy(null);
    }
  }

  const forbidden = error && typeof error === "object" && "status" in error && error.status === 403;

  return (
    <PageContainer>
      <PageHeader
        eyebrow={COPY.eyebrow}
        title={COPY.title}
        description={COPY.description}
        actions={
          data?.can_manage ? (
            <>
              <Button prominence="tertiary" icon={SvgMail} onClick={() => setLayoutOpen(true)}>
                {COPY.layoutButton}
              </Button>
              <Button prominence="secondary" icon={SvgBubbleText} href={chatHref()}>
                {COPY.askTon}
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
      {data && data.approvals.length > 0 && <Approvals
          approvals={data.approvals}
          onDecided={async () => {
            await mutate();
          }}
        />}
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
          <table className="ton-statement ton-classification-grid w-full min-w-[900px] border-collapse">
            <thead>
              <tr>
                <th scope="col">{COPY.columns.flow}</th>
                <th scope="col">{COPY.columns.when}</th>
                <th scope="col">{COPY.columns.steps}</th>
                <th scope="col">{COPY.columns.lastRun}</th>
                <th scope="col">{COPY.columns.status}</th>
              </tr>
            </thead>
            <tbody>
              {data.flows.map((flow) => (
                <tr key={flow.id} className="cursor-pointer" onClick={() => router.push(href(flow.id))}>
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
                    <StepsCell flow={flow} />
                  </td>
                  <td>
                    <LastRun run={flow.last_run} />
                  </td>
                  <td onClick={(event) => event.stopPropagation()}>
                    <span className="flex flex-col items-start gap-1.5">
                      <StatusPill tone={STATUS_TONE[flow.status]}>{COPY.status[flow.status]}</StatusPill>
                      {flow.status === "SUGGESTED" && data.can_manage && (
                        <span className="flex gap-1.5">
                          <Button size="sm" disabled={busy !== null} onClick={() => act(flow, "activate")}>
                            {COPY.register}
                          </Button>
                          <Button size="sm" prominence="tertiary" disabled={busy !== null} onClick={() => act(flow, "discard")}>
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
      <LayoutModal open={layoutOpen} onClose={() => setLayoutOpen(false)} />
    </PageContainer>
  );
}
