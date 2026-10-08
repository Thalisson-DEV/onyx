"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import type { Route } from "next";
import { Button, Popover, Text } from "@opal/components";
import { SvgBell, SvgBlocks, SvgChevronDown, SvgChevronRight, SvgMail, SvgPlus, SvgRefreshCw, SvgSparkle, SvgUserCheck, SvgWorkflow } from "@opal/icons";
import type { IconFunctionComponent } from "@opal/types";
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

const KIND_ICONS: Record<AutomationKind, IconFunctionComponent> = {
  EMAIL: SvgMail,
  ALERT: SvgBell,
  ROUTINE: SvgRefreshCw,
  APPROVAL: SvgUserCheck,
  DATA_AI: SvgSparkle,
  GENERAL: SvgWorkflow,
};

function Runs28({ automation }: { automation: AutomationSummary }) {
  const ok = automation.runs_28d.SUCCEEDED ?? 0;
  const failed = (automation.runs_28d.FAILED ?? 0) + (automation.runs_28d.TIMED_OUT ?? 0);
  if (!ok && !failed) return null;
  return (
    <span className="ton-auto-runs28" title={COPY.columns.runs}>
      {ok > 0 && <span data-tone="success">{COPY.runsOk(ok)}</span>}
      {failed > 0 && <span data-tone="error">{COPY.runsFailed(failed)}</span>}
    </span>
  );
}

function Row({ automation }: { automation: AutomationSummary }) {
  const href = `/ton/automacoes/${automation.id}` as Route;
  const Icon = KIND_ICONS[automation.kind] ?? SvgWorkflow;
  const pending = automation.problems.length > 0 && automation.status !== "ACTIVE";
  return (
    <li className="ton-auto-list-row">
      <span className="ton-auto-list-icon" data-kind={automation.kind} aria-hidden>
        <Icon size={18} />
      </span>
      <span className="ton-auto-list-main">
        <Link href={href} className="ton-auto-list-name ton-focusable">
          {automation.name}
        </Link>
        <span className="ton-auto-list-desc">
          <span className="ton-auto-list-kind">{KIND_LABELS[automation.kind]}</span>
          <span aria-hidden>·</span>
          <span className="truncate">{automation.description ?? COPY.steps(automation.steps_count)}</span>
        </span>
      </span>
      <span className="ton-auto-list-when">
        <span className="ton-auto-list-label">{COPY.columns.trigger}</span>
        <span>{automation.when}</span>
        {automation.next_run_at && automation.status === "ACTIVE" && <span className="ton-auto-muted">{COPY.next(formatDateTime(automation.next_run_at))}</span>}
      </span>
      <span className="ton-auto-list-last">
        <span className="ton-auto-list-label">{COPY.columns.lastRun}</span>
        {automation.last_run ? (
          <span className="ton-auto-list-run" data-status={automation.last_run.status}>
            <span className="ton-auto-dot" aria-hidden />
            {`${RUN_STATUS_LABELS[automation.last_run.status]} · ${formatRelativeDateTime(automation.last_run.created_at)}`}
          </span>
        ) : (
          <span className="ton-auto-muted">{COPY.never}</span>
        )}
        <Runs28 automation={automation} />
      </span>
      <span className="ton-auto-list-status">
        {pending ? <span className="ton-auto-problems">{COPY.problems(automation.problems.length)}</span> : null}
        <StatusPill tone={STATUS_TONE[automation.status]}>{STATUS_LABELS[automation.status]}</StatusPill>
        <SvgChevronRight size={16} className="ton-auto-list-chevron" />
      </span>
    </li>
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
      <div className="ton-auto-filters" role="tablist" aria-label={COPY.columns.kind}>
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
        <TonCard as="div" className="ton-auto-list-card">
          <ul className="ton-auto-list">
            {shown.map((automation) => (
              <Row key={automation.id} automation={automation} />
            ))}
          </ul>
        </TonCard>
      )}
      <NewAutomationModal mode={newMode} onClose={() => setNewMode(null)} />
      <ApprovalModal approval={approval} onClose={() => setApproval(null)} onDecided={() => void table.mutate()} />
    </PageContainer>
  );
}
