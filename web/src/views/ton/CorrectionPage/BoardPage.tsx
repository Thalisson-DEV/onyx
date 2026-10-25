"use client";

import { useRouter } from "next/navigation";
import type { Route } from "next";
import { Button, Text } from "@opal/components";
import { SvgCheckCircle, SvgDownload } from "@opal/icons";
import { brl } from "@/lib/ton/payables";
import {
  CORRECTION_API,
  CRITICALITY_TONE,
  caseNumber,
  useBoard,
} from "@/lib/ton/correction";
import {
  BackLink,
  EmptyState,
  ErrorState,
  LoadingBlock,
  PageContainer,
  StatusPill,
} from "@/views/ton/components/ui";
import { PatternHead } from "@/views/ton/components/pattern";

const LABELS: Record<string, string> = {
  CRITICAL: "Crítica",
  HIGH: "Alta",
  MEDIUM: "Média",
  MONITORING: "Monitoramento",
};

function compact(value: string): string {
  const amount = Number(value);
  if (amount >= 1_000_000)
    return `R$ ${(amount / 1_000_000).toFixed(2).replace(".", ",")} mi`;
  if (amount >= 1_000)
    return `R$ ${(amount / 1_000).toFixed(1).replace(".", ",")} mil`;
  return brl(amount);
}

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div className="tp-figure">
      <Text font="secondary-body" color="text-03">
        {label}
      </Text>
      <span className="tp-figure-value">{value}</span>
    </div>
  );
}

/** Prompt Mestre §14.2: result, problem, impact, cause, action. */
export default function BoardPage() {
  const router = useRouter();
  const board = useBoard();
  const summary = board.data;
  return (
    <PageContainer>
      <BackLink href={"/ton/ocorrencias" as Route} label="Plano de correção" />
      <PatternHead
        eyebrow="Plano de correção · Resumo para a diretoria"
        title="O que precisa ser corrigido"
        description="Resultado, problema, impacto, causa e ação, em poucas linhas por caso. Entram os casos marcados para a diretoria ou, sem marcação, os críticos e altos em aberto."
        actions={
          <Button
            icon={SvgDownload}
            onClick={() =>
              window.location.assign(`${CORRECTION_API}/board.xlsx`)
            }
          >
            Baixar Excel
          </Button>
        }
      />
      {board.isLoading && <LoadingBlock label="Carregando…" lines={6} />}
      {board.error && (
        <ErrorState
          message="Não foi possível montar o resumo."
          onRetry={() => board.mutate()}
        />
      )}
      {summary && (
        <>
          <div className="ton-card tp-figures">
            <Figure label="Em aberto" value={compact(summary.open_amount)} />
            <Figure
              label="Corrigido e verificado no mês"
              value={compact(summary.verified_amount)}
            />
            <Figure label="Reincidentes" value={String(summary.recurring)} />
            <Figure
              label="Sem responsável"
              value={String(summary.unassigned)}
            />
            <Figure label="Prazo vencido" value={String(summary.overdue)} />
          </div>
          {summary.items.length === 0 ? (
            <div className="ton-card">
              <EmptyState
                icon={SvgCheckCircle}
                tone="brand"
                title="Nada crítico em aberto"
              />
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {summary.items.map((item) => (
                <article key={item.case_id} className="ton-card">
                  <header className="flex flex-wrap items-center justify-between gap-2 px-6 pt-4">
                    <button
                      type="button"
                      className="ton-focusable ton-link-button"
                      onClick={() =>
                        router.push(`/ton/ocorrencias/${item.case_id}` as Route)
                      }
                    >
                      {caseNumber(item.number)}
                    </button>
                    {item.verified ? (
                      <StatusPill tone="success">
                        Corrigida e verificada
                      </StatusPill>
                    ) : (
                      <StatusPill tone={CRITICALITY_TONE[item.criticality]}>
                        {LABELS[item.criticality] ?? item.criticality}
                      </StatusPill>
                    )}
                  </header>
                  <dl className="tp-board-item">
                    <dt>Resultado</dt>
                    <dd>{item.result}</dd>
                    <dt>Problema</dt>
                    <dd>{item.problem}</dd>
                    <dt>Impacto</dt>
                    <dd>{item.impact}</dd>
                    <dt>Causa</dt>
                    <dd>{item.cause}</dd>
                    <dt>Ação</dt>
                    <dd>{item.action}</dd>
                  </dl>
                </article>
              ))}
            </div>
          )}
        </>
      )}
    </PageContainer>
  );
}
