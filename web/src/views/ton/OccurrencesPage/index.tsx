"use client";

import { Fragment, useState } from "react";
import useSWR from "swr";
import type { Route } from "next";
import { Button, InputTypeIn, Text } from "@opal/components";
import {
  SvgBubbleText,
  SvgChevronDown,
  SvgChevronRight,
} from "@opal/icons";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { formatCurrency, formatDateTime, formatDay } from "@/lib/ton/copy";
import {
  ErrorState,
  LoadingBlock,
  PageContainer,
  PageHeader,
  StatusPill,
  type TonTone,
} from "@/views/ton/components/ui";

const LEDGER_API = "/api/ton/agent/ledger";

const COPY = {
  title: "Ocorrências",
  description:
    "O ledger da Controladoria: cada caso com evidência, criticidade, responsável e prazo. Os testes do TON e a revisão do NG registram aqui; as decisões continuam com as pessoas.",
  filters: { open: "Abertas", overdue: "Vencidas", all: "Todas" },
  search: "Buscar por código, caso, unidade ou responsável",
  columns: {
    reference: "Código",
    title: "Caso",
    unit: "Unidade",
    criticality: "Criticidade",
    status: "Situação",
    owner: "Responsável",
    deadline: "Prazo",
    impact: "Impacto",
  },
  noOwner: "Sem responsável",
  empty: "Nenhuma ocorrência neste filtro.",
  loading: "Carregando o ledger…",
  verification: "Como verificar",
  evidence: "Evidência",
  history: "Histórico",
  rule: "Regra",
  detections: (count: number) =>
    count === 1 ? "Detectada 1 vez" : `Detectada ${count} vezes`,
  ask: "Perguntar ao TON",
  askPrompt: (reference: string, title: string) =>
    `Sobre a ocorrência ${reference} (${title}): mostre a evidência, o que verificar e proponha responsável e próximo passo.`,
  more: (count: number) => `Mostrar mais ${count}`,
};

type Filter = keyof typeof COPY.filters;

interface LedgerRow {
  id: string;
  reference: string;
  title: string;
  rule: string | null;
  unit: string | null;
  criticality: string;
  criticality_code: string;
  status: string;
  open: boolean;
  owner: string | null;
  deadline: string | null;
  overdue: boolean;
  detections: number;
  impact: string | null;
  last_detected_at: string;
}

interface LedgerPage {
  rows: LedgerRow[];
  total: number;
  open_total: number;
  overdue_total: number;
}

interface LedgerDetail {
  row: LedgerRow;
  verification: string | null;
  evidence: Record<string, unknown> | null;
  history: { at: string; text: string }[];
}

const CRITICALITY_TONE: Record<string, TonTone> = {
  CRITICAL: "danger",
  HIGH: "warning",
  MEDIUM: "brand",
  MONITORING: "neutral",
};

const PAGE = 50;

/** Plain lines of a finding's evidence: the hit and how it was measured. */
function evidenceLines(evidence: Record<string, unknown> | null): string[] {
  if (!evidence) return [];
  const lines: string[] = [];
  const hit = evidence.achado;
  if (typeof hit === "object" && hit !== null && !Array.isArray(hit)) {
    for (const [key, value] of Object.entries(hit)) {
      if (key === "chave" || value === null || typeof value === "object")
        continue;
      lines.push(`${key.replace(/_/g, " ")}: ${String(value)}`);
    }
  }
  if (typeof evidence.base_da_receita === "string")
    lines.push(`Base da criticidade: ${evidence.base_da_receita}`);
  if (typeof evidence.impacto_percentual === "string")
    lines.push(
      `Impacto: ${Number(evidence.impacto_percentual).toFixed(2).replace(".", ",")}% da receita`
    );
  return lines;
}

function Detail({ id }: { id: string }) {
  const detail = useSWR<LedgerDetail>(
    `${LEDGER_API}/${id}`,
    errorHandlingFetcher
  );
  if (detail.isLoading) return <LoadingBlock label={COPY.loading} lines={2} />;
  if (detail.error || !detail.data) return <ErrorState compact />;
  const { row, verification, evidence, history } = detail.data;
  const lines = evidenceLines(evidence);
  const ask = new URLSearchParams({
    firstMessage: COPY.askPrompt(row.reference, row.title),
    submitOnLoad: "true",
  });
  return (
    <div className="flex flex-col gap-3 p-3">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <span className="ton-eyebrow">{COPY.evidence}</span>
          {lines.map((line) => (
            <Text key={line} font="secondary-body" color="text-04">
              {line}
            </Text>
          ))}
          {row.rule && (
            <Text font="secondary-body" color="text-03">
              {`${COPY.rule}: ${row.rule} · ${COPY.detections(row.detections)}`}
            </Text>
          )}
        </div>
        <div className="flex flex-col gap-1">
          {verification && (
            <>
              <span className="ton-eyebrow">{COPY.verification}</span>
              <Text font="secondary-body" color="text-04">
                {verification}
              </Text>
            </>
          )}
          <span className="ton-eyebrow pt-2">{COPY.history}</span>
          {history.map((item, index) => (
            <Text key={index} font="secondary-body" color="text-03">
              {`${formatDateTime(item.at)} · ${item.text}`}
            </Text>
          ))}
        </div>
      </div>
      <div>
        <Button
          size="sm"
          prominence="secondary"
          icon={SvgBubbleText}
          href={`/ton/chat?${ask.toString()}` as Route}
        >
          {COPY.ask}
        </Button>
      </div>
    </div>
  );
}

export default function OccurrencesPage() {
  const [filter, setFilter] = useState<Filter>("open");
  const [text, setText] = useState("");
  const [limit, setLimit] = useState(PAGE);
  const [expanded, setExpanded] = useState<string | null>(null);
  const query = new URLSearchParams({
    status: filter,
    limit: String(limit),
    ...(text.trim() ? { text: text.trim() } : {}),
  });
  const page = useSWR<LedgerPage>(
    `${LEDGER_API}?${query.toString()}`,
    errorHandlingFetcher,
    { keepPreviousData: true }
  );
  const data = page.data;
  const counts: Record<Filter, number | undefined> = {
    open: data?.open_total,
    overdue: data?.overdue_total,
    all: undefined,
  };
  return (
    <PageContainer className="max-w-[1760px]">
      <PageHeader title={COPY.title} description={COPY.description} />
      <div className="flex flex-wrap items-center gap-2">
        {(Object.keys(COPY.filters) as Filter[]).map((key) => (
          <Button
            key={key}
            size="sm"
            prominence={filter === key ? "primary" : "secondary"}
            onClick={() => {
              setFilter(key);
              setLimit(PAGE);
            }}
          >
            {counts[key] === undefined
              ? COPY.filters[key]
              : `${COPY.filters[key]} · ${counts[key]}`}
          </Button>
        ))}
        <div className="flex-1 min-w-[220px] max-w-md">
          <InputTypeIn
            searchIcon
            placeholder={COPY.search}
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
        </div>
      </div>
      {page.isLoading && !data && <LoadingBlock label={COPY.loading} />}
      {page.error && <ErrorState onRetry={() => page.mutate()} />}
      {data && (
        <div className="ton-card overflow-x-auto">
          <table className="ton-statement ton-classification-grid w-full min-w-[1100px] border-collapse">
            <thead>
              <tr>
                <th scope="col" className="w-8">
                  <span className="sr-only">Detalhes</span>
                </th>
                <th scope="col" className="whitespace-nowrap">{COPY.columns.reference}</th>
                <th scope="col" className="whitespace-nowrap">{COPY.columns.title}</th>
                <th scope="col" className="whitespace-nowrap">{COPY.columns.unit}</th>
                <th scope="col" className="whitespace-nowrap">{COPY.columns.criticality}</th>
                <th scope="col" className="whitespace-nowrap">{COPY.columns.status}</th>
                <th scope="col" className="whitespace-nowrap">{COPY.columns.owner}</th>
                <th scope="col" className="whitespace-nowrap">{COPY.columns.deadline}</th>
                <th scope="col" data-numeric className="whitespace-nowrap">
                  {COPY.columns.impact}
                </th>
              </tr>
            </thead>
            <tbody>
              {data.rows.length === 0 && (
                <tr>
                  <td colSpan={9}>
                    <Text font="secondary-body" color="text-03">
                      {COPY.empty}
                    </Text>
                  </td>
                </tr>
              )}
              {data.rows.map((row) => {
                const open = expanded === row.id;
                return (
                  <Fragment key={row.id}>
                    <tr
                      aria-expanded={open}
                      onClick={() => setExpanded(open ? null : row.id)}
                      className="cursor-pointer"
                    >
                      <td>
                        {open ? (
                          <SvgChevronDown size={14} className="text-text-03" />
                        ) : (
                          <SvgChevronRight size={14} className="text-text-03" />
                        )}
                      </td>
                      <td className="whitespace-nowrap">
                        <Text font="secondary-mono" color="text-04" wordWrap="whitespace-nowrap">
                          {row.reference}
                        </Text>
                      </td>
                      <td>
                        <Text font="secondary-action" color="text-05">
                          {row.title}
                        </Text>
                      </td>
                      <td className="whitespace-nowrap">
                        <Text font="secondary-body" color="text-04" wordWrap="whitespace-nowrap">
                          {row.unit ?? "—"}
                        </Text>
                      </td>
                      <td className="whitespace-nowrap">
                        <StatusPill
                          tone={CRITICALITY_TONE[row.criticality_code] ?? "neutral"}
                        >
                          {row.criticality}
                        </StatusPill>
                      </td>
                      <td className="whitespace-nowrap">
                        <Text font="secondary-body" color="text-04" wordWrap="whitespace-nowrap">
                          {row.status}
                        </Text>
                      </td>
                      <td className="whitespace-nowrap">
                        <Text
                          font="secondary-body"
                          color={row.owner ? "text-04" : "text-03"}
                          wordWrap="whitespace-nowrap"
                        >
                          {row.owner ?? COPY.noOwner}
                        </Text>
                      </td>
                      <td className="whitespace-nowrap">
                        {row.deadline ? (
                          <StatusPill tone={row.overdue ? "danger" : "neutral"}>
                            {formatDay(row.deadline)}
                          </StatusPill>
                        ) : (
                          <Text font="secondary-body" color="text-03">
                            —
                          </Text>
                        )}
                      </td>
                      <td data-numeric className="whitespace-nowrap">
                        <Text font="secondary-body" color="text-05" wordWrap="whitespace-nowrap">
                          {row.impact ? formatCurrency(row.impact) : "—"}
                        </Text>
                      </td>
                    </tr>
                    {open && (
                      <tr>
                        <td colSpan={9}>
                          <Detail id={row.id} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {data && data.total > data.rows.length && (
        <div>
          <Button
            size="sm"
            prominence="secondary"
            onClick={() => setLimit(limit + PAGE)}
          >
            {COPY.more(Math.min(PAGE, data.total - data.rows.length))}
          </Button>
        </div>
      )}
    </PageContainer>
  );
}
