"use client";

import { Fragment, useState } from "react";
import { Button, InputTypeIn, Text } from "@opal/components";
import {
  SvgAlertTriangle,
  SvgCheckCircle,
  SvgChevronDown,
  SvgChevronRight,
  SvgLock,
  SvgPlus,
} from "@opal/icons";
import { useUser } from "@/providers/UserProvider";
import { postJson } from "@/lib/ton/classification";
import { formatDate, formatDateTime } from "@/lib/ton/copy";
import {
  TREATMENTS_API,
  TREATMENTS_COPY as COPY,
  asRequest,
  periodLabel,
  useTreatmentHistory,
  useTreatmentTable,
  type TreatmentTable,
  type TreatmentView,
} from "@/lib/ton/treatments";
import {
  BackLink,
  ErrorState,
  EmptyState,
  LoadingBlock,
  PageContainer,
  PageHeader,
  StatusPill,
  TonCard,
} from "@/views/ton/components/ui";
import TreatmentDialog from "./TreatmentDialog";

type Feedback = { tone: "success" | "error"; text: string } | null;
const COLUMNS = 7;

function StatusCell({ treatment }: { treatment: TreatmentView }) {
  if (treatment.status === "ACTIVE")
    return <StatusPill tone="success">{COPY.status.ACTIVE}</StatusPill>;
  if (treatment.status === "REVOKED")
    return <StatusPill tone="neutral">{COPY.status.REVOKED}</StatusPill>;
  return (
    <StatusPill tone="warning">
      {COPY.status.BLOCKED(treatment.required_source)}
    </StatusPill>
  );
}

function History({ treatmentKey }: { treatmentKey: string }) {
  const history = useTreatmentHistory(treatmentKey);
  if (!history.data) return null;
  return (
    <div className="flex flex-col gap-1">
      <span className="ton-eyebrow">{COPY.detail.history}</span>
      {history.data.map((item) => (
        <Text key={item.id} as="p" font="secondary-body" color="text-04">
          {`v${item.version} · ${formatDate(item.created_at)} · ${
            item.status === "BLOCKED"
              ? COPY.status.BLOCKED(item.required_source)
              : COPY.status[item.status]
          } · ${COPY.effect[item.effect]} · ${item.justification}`}
        </Text>
      ))}
    </div>
  );
}

function Detail({
  treatment,
  onNewVersion,
  onRevoked,
}: {
  treatment: TreatmentView;
  onNewVersion: () => void;
  onRevoked: () => Promise<void>;
}) {
  const [revoking, setRevoking] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const scope = [
    treatment.unit_name ?? COPY.detail.allUnits,
    periodLabel(treatment),
  ].join(", ");

  async function revoke() {
    setBusy(true);
    setFailed(false);
    try {
      await postJson(
        TREATMENTS_API,
        asRequest(treatment, {
          status: "REVOKED",
          required_source: null,
          justification: reason.trim(),
        })
      );
      await onRevoked();
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-3 py-2">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div className="flex flex-col gap-1">
          <span className="ton-eyebrow">{COPY.detail.justification}</span>
          <Text as="p" font="secondary-body" color="text-05">
            {treatment.justification}
          </Text>
        </div>
        <div className="flex flex-col gap-1">
          <span className="ton-eyebrow">{COPY.detail.evidence}</span>
          <Text as="p" font="secondary-body" color="text-05">
            {treatment.evidence}
          </Text>
        </div>
        <div className="flex flex-col gap-1">
          <span className="ton-eyebrow">{COPY.detail.scope}</span>
          <Text as="p" font="secondary-body" color="text-05">
            {treatment.effect === "RECLASSIFY" && treatment.target_account_label
              ? `${scope} → ${treatment.target_account_label}`
              : scope}
          </Text>
        </div>
        <Text as="p" font="secondary-body" color="text-03">
          {COPY.detail.author(
            treatment.created_by_email,
            formatDateTime(treatment.created_at)
          )}
        </Text>
      </div>
      <History treatmentKey={treatment.treatment_key} />
      {treatment.status !== "REVOKED" && !revoking && (
        <div className="flex gap-2">
          <Button size="sm" prominence="secondary" onClick={onNewVersion}>
            {COPY.detail.newVersion}
          </Button>
          <Button
            size="sm"
            prominence="tertiary"
            onClick={() => setRevoking(true)}
          >
            {COPY.detail.revoke}
          </Button>
        </div>
      )}
      {revoking && (
        <div className="flex flex-wrap items-center gap-2">
          <div className="min-w-[18rem] flex-1">
            <InputTypeIn
              aria-label={COPY.detail.revokeReason}
              placeholder={COPY.detail.revokeReason}
              value={reason}
              maxLength={2000}
              onChange={(event) => setReason(event.target.value)}
            />
          </div>
          <Button
            size="sm"
            disabled={busy || reason.trim().length < 3}
            onClick={() => void revoke()}
          >
            {COPY.detail.confirmRevoke}
          </Button>
          <Button
            size="sm"
            prominence="tertiary"
            disabled={busy}
            onClick={() => setRevoking(false)}
          >
            {COPY.dialog.cancel}
          </Button>
        </div>
      )}
      {failed && (
        <span role="alert" className="text-status-error-05">
          <Text font="secondary-body" color="inherit">
            {COPY.dialog.failed}
          </Text>
        </span>
      )}
    </div>
  );
}

function RecomputeLink({
  table,
  onDone,
}: {
  table: TreatmentTable;
  onDone: () => Promise<void>;
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

function TreatmentGrid({
  table,
  onNewVersion,
  onChanged,
}: {
  table: TreatmentTable;
  onNewVersion: (treatment: TreatmentView) => void;
  onChanged: () => Promise<void>;
}) {
  const [expanded, setExpanded] = useState<string | null>(null);
  if (!table.treatments.length) {
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
            <th scope="col">{COPY.columns.title}</th>
            <th scope="col">{COPY.columns.nature}</th>
            <th scope="col">{COPY.columns.effect}</th>
            <th scope="col">{COPY.columns.status}</th>
            <th scope="col" data-numeric>
              {COPY.columns.applied}
            </th>
            <th scope="col">{COPY.columns.version}</th>
          </tr>
        </thead>
        <tbody>
          {table.treatments.map((treatment) => {
            const open = expanded === treatment.treatment_key;
            return (
              <Fragment key={treatment.id}>
                <tr
                  aria-expanded={open}
                  aria-selected={open}
                  onClick={() =>
                    setExpanded(open ? null : treatment.treatment_key)
                  }
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
                      {treatment.title}
                    </Text>
                  </td>
                  <td>
                    <Text font="secondary-body" color="text-05">
                      {treatment.account_label ?? "—"}
                    </Text>
                  </td>
                  <td>
                    <Text font="secondary-body" color="text-04">
                      {COPY.effect[treatment.effect]}
                    </Text>
                  </td>
                  <td>
                    <StatusCell treatment={treatment} />
                  </td>
                  <td data-numeric>
                    <Text font="secondary-body" color="text-05">
                      {treatment.status !== "ACTIVE"
                        ? "—"
                        : treatment.applied_fact_count === null
                          ? COPY.notInBase
                          : String(treatment.applied_fact_count)}
                    </Text>
                  </td>
                  <td>
                    <Text font="secondary-body" color="text-04">
                      {`v${treatment.version} · ${formatDate(treatment.created_at)}`}
                    </Text>
                  </td>
                </tr>
                {open && (
                  <tr data-type="DETAIL">
                    <td aria-hidden="true" />
                    <td colSpan={COLUMNS - 1}>
                      <Detail
                        treatment={treatment}
                        onNewVersion={() => onNewVersion(treatment)}
                        onRevoked={async () => {
                          setExpanded(null);
                          await onChanged();
                        }}
                      />
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

export default function TreatmentsPage() {
  const { hasAdminAccess } = useUser();
  const table = useTreatmentTable(hasAdminAccess);
  // undefined: closed; null: new treatment; a view: new version of it.
  const [editing, setEditing] = useState<TreatmentView | null | undefined>(
    undefined
  );
  const [feedback, setFeedback] = useState<Feedback>(null);

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

  return (
    <PageContainer className="max-w-[1280px]">
      <BackLink href="/ton/administracao" label={COPY.back} />
      <PageHeader
        eyebrow={COPY.eyebrow}
        title={COPY.title}
        description={COPY.description}
        actions={
          <Button icon={SvgPlus} onClick={() => setEditing(null)}>
            {COPY.create}
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
        <div className="flex flex-col gap-3">
          {(feedback || table.data.changes_since_calculation > 0) && (
            <div className="flex flex-wrap items-center justify-between gap-2">
              {feedback ? (
                <span role="status" className="flex items-center gap-1.5">
                  {feedback.tone === "success" ? (
                    <SvgCheckCircle
                      size={14}
                      className="ton-brand-text shrink-0"
                    />
                  ) : (
                    <SvgAlertTriangle
                      size={14}
                      className="text-status-error-05 shrink-0"
                    />
                  )}
                  <Text font="secondary-body" color="text-04">
                    {feedback.text}
                  </Text>
                </span>
              ) : (
                <span />
              )}
              <RecomputeLink
                table={table.data}
                onDone={async () => {
                  await table.mutate();
                }}
              />
            </div>
          )}
          <TreatmentGrid
            table={table.data}
            onNewVersion={(treatment) => setEditing(treatment)}
            onChanged={async () => {
              setFeedback(null);
              await table.mutate();
            }}
          />
        </div>
      )}
      {table.data && editing !== undefined && (
        <TreatmentDialog
          table={table.data}
          base={editing}
          onClose={() => setEditing(undefined)}
          onSaved={(treatment) => {
            setEditing(undefined);
            setFeedback({ tone: "success", text: COPY.saved(treatment.title) });
            void table.mutate();
          }}
        />
      )}
    </PageContainer>
  );
}
