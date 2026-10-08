"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { Route } from "next";
import { Button, Popover, Text } from "@opal/components";
import { SvgChevronDown, SvgPlus, SvgSparkle, SvgUserCheck, SvgWorkflow, SvgBlocks } from "@opal/icons";
import {
  COPY,
  KIND_LABELS,
  RUN_STATUS_LABELS,
  STATUS_LABELS,
  useAutomationTable,
  type ApprovalView,
  type AutomationKind,
  type AutomationSummary,
} from "@/lib/ton/automations";
import { formatDateTime, formatRelativeDateTime } from "@/lib/ton/copy";
import { EmptyState, ErrorState, LoadingBlock, PageContainer, PageHeader, StatusPill, TonCard } from "@/views/ton/components/ui";
import ApprovalModal from "@/views/ton/AutomationsPage/ApprovalModal";
import { RUN_TONE, STATUS_TONE } from "@/views/ton/AutomationsPage/DetailPage";
import NewAutomationModal, { type NewMode } from "@/views/ton/AutomationsPage/NewAutomationModal";
import RoutinesSection from "@/views/ton/AutomationsPage/RoutinesSection";

type Filter = AutomationKind | "ALL" | "ROUTINES";

function Approvals({ approvals, onOpen }: { approvals: ApprovalView[]; onOpen: (approval: ApprovalView) => void }) {
  if (!approvals.length) return null;
  return (
    <TonCard className="flex flex-col gap-2 p-4" labelledBy="ton-auto-approvals">
      <Text as="h2" id="ton-auto-approvals" font="main-ui-action" color="text-05">
        {`${COPY.approvalsTitle} (${approvals.length})`}
      </Text>
      <ul className="flex flex-col divide-y divide-border-01">
        {approvals.map((approval) => (
          <li key={approval.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <span className="flex min-w-0 flex-col">
              <Text font="secondary-action" color="text-05">
                {approval.title}
              </Text>
              <Text font="secondary-body" color="text-03">
                {`${approval.automation_name} · ${formatRelativeDateTime(approval.created_at)}`}
              </Text>
            </span>
            {approval.can_decide && (
              <Button size="sm" prominence="secondary" icon={SvgUserCheck} onClick={() => onOpen(approval)}>
                {COPY.approve}
              </Button>
            )}
          </li>
        ))}
      </ul>
    </TonCard>
  );
}

function Runs28({ automation }: { automation: AutomationSummary }) {
  const ok = automation.runs_28d.SUCCEEDED ?? 0;
  const failed = (automation.runs_28d.FAILED ?? 0) + (automation.runs_28d.TIMED_OUT ?? 0);
  if (!ok && !failed) return <span className="ton-auto-muted">{"—"}</span>;
  return (
    <span className="ton-auto-runs28">
      {ok > 0 && <span data-tone="success">{`✓ ${ok}`}</span>}
      {failed > 0 && <span data-tone="error">{`✕ ${failed}`}</span>}
    </span>
  );
}

function Row({ automation }: { automation: AutomationSummary }) {
  const router = useRouter();
  const href = `/ton/automacoes/${automation.id}` as Route;
  return (
    <tr className="ton-auto-table-row" onClick={() => router.push(href)}>
      <td>
        <span className="flex min-w-0 flex-col gap-0.5">
          <a href={href} className="ton-focusable" onClick={(event) => event.preventDefault()}>
            <Text font="main-ui-action" color="text-05">
              {automation.name}
            </Text>
          </a>
          <Text font="secondary-body" color="text-03" maxLines={1}>
            {automation.description ?? COPY.steps(automation.steps_count)}
          </Text>
          {automation.problems.length > 0 && automation.status !== "ACTIVE" && <span className="ton-auto-problems">{COPY.problems(automation.problems.length)}</span>}
        </span>
      </td>
      <td>
        <span className="ton-auto-kind-pill" data-kind={automation.kind}>
          {KIND_LABELS[automation.kind]}
        </span>
      </td>
      <td>
        <span className="flex flex-col gap-0.5">
          <Text font="secondary-body" color="text-04">
            {automation.when}
          </Text>
          {automation.next_run_at && (
            <Text font="secondary-body" color="text-03">
              {COPY.next(formatDateTime(automation.next_run_at))}
            </Text>
          )}
        </span>
      </td>
      <td>
        <StatusPill tone={STATUS_TONE[automation.status]}>{STATUS_LABELS[automation.status]}</StatusPill>
      </td>
      <td>
        {automation.last_run ? (
          <span className="flex flex-col gap-0.5">
            <StatusPill tone={RUN_TONE[automation.last_run.status]}>{RUN_STATUS_LABELS[automation.last_run.status]}</StatusPill>
            <Text font="secondary-body" color="text-03">
              {formatRelativeDateTime(automation.last_run.created_at)}
            </Text>
          </span>
        ) : (
          <span className="ton-auto-muted">{COPY.never}</span>
        )}
      </td>
      <td data-numeric>
        <Runs28 automation={automation} />
      </td>
    </tr>
  );
}

export default function AutomationsPage() {
  const table = useAutomationTable();
  const search = useSearchParams();
  const [filter, setFilter] = useState<Filter>("ALL");
  const [newMode, setNewMode] = useState<NewMode | null>(null);
  const [approval, setApproval] = useState<ApprovalView | null>(null);
  const automations = table.data?.automations ?? [];
  const counts = useMemo(() => {
    const map = new Map<AutomationKind, number>();
    for (const item of automations) map.set(item.kind, (map.get(item.kind) ?? 0) + 1);
    return map;
  }, [automations]);
  const shown = filter === "ALL" || filter === "ROUTINES" ? automations : automations.filter((item) => item.kind === filter);

  useEffect(() => {
    const wanted = search.get("aprovacao");
    if (!wanted || !table.data) return;
    const found = table.data.approvals.find((item) => item.id === wanted);
    if (found) setApproval(found);
  }, [search, table.data]);

  return (
    <PageContainer>
      <PageHeader
        title={COPY.title}
        description={COPY.description}
        actions={
          table.data?.can_manage ? (
            <Popover>
              <Popover.Trigger asChild>
                <Button icon={SvgPlus} rightIcon={SvgChevronDown}>
                  {COPY.newAutomation}
                </Button>
              </Popover.Trigger>
              <Popover.Content align="end" width="md">
                <Popover.Menu>
                  {[
                    <Button key="blank" prominence="tertiary" icon={SvgWorkflow} width="full" onClick={() => setNewMode("blank")}>
                      {COPY.blank}
                    </Button>,
                    <Button key="template" prominence="tertiary" icon={SvgBlocks} width="full" onClick={() => setNewMode("template")}>
                      {COPY.fromTemplate}
                    </Button>,
                    <Button key="ask" prominence="tertiary" icon={SvgSparkle} width="full" onClick={() => setNewMode("ask")}>
                      {COPY.askTon}
                    </Button>,
                  ]}
                </Popover.Menu>
              </Popover.Content>
            </Popover>
          ) : undefined
        }
      />
      <Approvals approvals={table.data?.approvals ?? []} onOpen={setApproval} />
      <div className="ton-auto-filters" role="tablist">
        {(["ALL", "EMAIL", "ALERT", "ROUTINE", "APPROVAL", "DATA_AI", "GENERAL"] as const).map((key) => {
          const count = key === "ALL" ? automations.length : counts.get(key) ?? 0;
          if (key !== "ALL" && !count) return null;
          return (
            <button key={key} type="button" role="tab" aria-selected={filter === key} className="ton-auto-filter ton-focusable" onClick={() => setFilter(key)}>
              {key === "ALL" ? COPY.all : KIND_LABELS[key]}
              <span>{count}</span>
            </button>
          );
        })}
        <span className="flex-1" />
        <button type="button" role="tab" aria-selected={filter === "ROUTINES"} className="ton-auto-filter ton-focusable" onClick={() => setFilter("ROUTINES")}>
          {COPY.routines}
        </button>
      </div>
      {filter === "ROUTINES" ? (
        <RoutinesSection />
      ) : table.error ? (
        <ErrorState onRetry={() => table.mutate()} />
      ) : !table.data ? (
        <TonCard className="p-5">
          <LoadingBlock label="…" />
        </TonCard>
      ) : shown.length === 0 ? (
        <EmptyState icon={SvgWorkflow} title={COPY.empty} description={COPY.emptyHint} />
      ) : (
        <TonCard as="div" className="overflow-x-auto">
          <table className="ton-auto-table">
            <thead>
              <tr>
                <th scope="col">{COPY.columns.name}</th>
                <th scope="col">{COPY.columns.kind}</th>
                <th scope="col">{COPY.columns.trigger}</th>
                <th scope="col">{COPY.columns.status}</th>
                <th scope="col">{COPY.columns.lastRun}</th>
                <th scope="col" data-numeric>
                  {COPY.columns.runs}
                </th>
              </tr>
            </thead>
            <tbody>
              {shown.map((automation) => (
                <Row key={automation.id} automation={automation} />
              ))}
            </tbody>
          </table>
        </TonCard>
      )}
      <NewAutomationModal mode={newMode} onClose={() => setNewMode(null)} />
      <ApprovalModal approval={approval} onClose={() => setApproval(null)} onDecided={() => void table.mutate()} />
    </PageContainer>
  );
}
