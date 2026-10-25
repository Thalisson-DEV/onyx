"use client";

import { Fragment, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import { Button, Text } from "@opal/components";
import {
  SvgCheckCircle,
  SvgLock,
  SvgPlus,
  SvgUsers,
  SvgWallet,
} from "@opal/icons";
import { toast } from "@opal/layouts";
import {
  CLOSED_STATUSES,
  STATUS,
  brl,
  daysUntil,
  documentText,
  downloadForTitles,
  errorText,
  formatPlate,
  payablesJson,
  rememberQueue,
  shortMonth,
  titleNumber,
  todayIso,
  usePayablesContext,
  useSuppliers,
  useTitles,
  type BatchResult,
  type PayablesContext,
  type TitleRow,
  type TitleStatus,
} from "@/lib/ton/payables";
import type { AskTonContext } from "@/lib/ton/ask";
import {
  EmptyState,
  ErrorState,
  LoadingBlock,
  PageContainer,
  StatusPill,
  type TonTone,
} from "@/views/ton/components/ui";
import { BatchBar, BatchButton } from "@/views/ton/components/pattern";
import {
  FilterBar,
  FilterField,
  PageFrame,
  PageHead,
  Segmented,
  Switch,
  Tag,
  TonMark,
  ViewTabs,
  type DotTone,
  type FilterToken,
  type TagTone,
} from "@/views/ton/components/kit";
import { AskTonRowButton, useAskTonPage } from "@/views/ton/ask/AskTon";
import { Select } from "@/views/ton/PayablesPage/fields";

const ANY = "__any";
const OPEN: TitleStatus[] = [
  "WAITING_ATTACHMENT",
  "WAITING_SUPPLIER",
  "RECEIVED",
  "RETURNED",
  "CONFERRED",
  "RELEASED",
];

interface View {
  key: string;
  label: string;
  tone?: DotTone;
  financeOnly?: boolean;
  /** Show the total next to the count. */
  money?: boolean;
  test: (row: TitleRow) => boolean;
}

const isOpenReal = (row: TitleRow) =>
  row.kind === "REAL" && OPEN.includes(row.status);

const VIEWS: View[] = [
  {
    key: "abertos",
    label: "Todos em aberto",
    money: true,
    test: (row) => OPEN.includes(row.status) || row.status === "ESTIMATE_OPEN",
  },
  {
    key: "vencidos",
    label: "Vencidos",
    tone: "danger",
    money: true,
    test: (row) => isOpenReal(row) && daysUntil(row.due_date) < 0,
  },
  {
    key: "semana",
    label: "Vencem em 7 dias",
    tone: "warn",
    money: true,
    test: (row) =>
      isOpenReal(row) &&
      daysUntil(row.due_date) >= 0 &&
      daysUntil(row.due_date) <= 7,
  },
  {
    key: "conferir",
    label: "Para conferir",
    tone: "info",
    financeOnly: true,
    money: true,
    test: (row) => row.status === "RECEIVED",
  },
  {
    key: "impedimento",
    label: "Com impedimento",
    tone: "danger",
    money: true,
    test: (row) => isOpenReal(row) && row.blocking > 0,
  },
  {
    key: "unidade",
    label: "Esperando a unidade",
    tone: "gold",
    test: (row) =>
      ["WAITING_ATTACHMENT", "WAITING_SUPPLIER", "RETURNED"].includes(
        row.status
      ),
  },
  {
    key: "prontos",
    label: "Prontos para pagar",
    tone: "ok",
    money: true,
    test: (row) => row.status === "RELEASED",
  },
  {
    key: "estimativas",
    label: "Estimativas",
    test: (row) => row.status === "ESTIMATE_OPEN",
  },
  {
    key: "encerrados",
    label: "Encerrados",
    test: (row) => CLOSED_STATUSES.includes(row.status),
  },
];

const DUE_OPTIONS = [
  { value: ANY, label: "Qualquer vencimento" },
  { value: "late", label: "Vencidos" },
  { value: "today", label: "Vencem hoje" },
  { value: "7", label: "Próximos 7 dias" },
  { value: "15", label: "Próximos 15 dias" },
  { value: "month", label: "Este mês" },
  { value: "next", label: "Mês que vem" },
];

const PAY_OPTIONS = [
  { value: ANY, label: "Qualquer pagamento" },
  { value: "PIX", label: "PIX" },
  { value: "Boleto", label: "Boleto" },
  { value: "Transferência", label: "Transferência" },
];

function normalize(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

function dueMatches(row: TitleRow, filter: string): boolean {
  if (filter === ANY) return true;
  const days = daysUntil(row.due_date);
  const today = todayIso();
  if (filter === "late") return days < 0;
  if (filter === "today") return days === 0;
  if (filter === "7" || filter === "15")
    return days >= 0 && days <= Number(filter);
  const month = today.slice(0, 7);
  if (filter === "month") return row.due_date.startsWith(month);
  const [year = 0, monthNumber = 1] = month.split("-").map(Number);
  const next = new Date(year, monthNumber, 1);
  const nextKey = `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, "0")}`;
  return row.due_date.startsWith(nextKey);
}

const WEEKDAYS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

function dayLabel(iso: string): string {
  const [year = 0, month = 1, day = 1] = iso.split("-").map(Number);
  const weekday = WEEKDAYS[new Date(year, month - 1, day).getDay()];
  return `${weekday}, ${String(day).padStart(2, "0")}/${String(month).padStart(2, "0")}`;
}

function total(rows: TitleRow[]): number {
  return rows.reduce((sum, row) => sum + Number(row.amount), 0);
}

function docLine(row: TitleRow): string {
  const parts = [
    row.kind === "ESTIMATE"
      ? `Estimativa · ${shortMonth(row.competence)}`
      : `${documentText(row)}${row.installment_count > 1 ? ` · ${row.installment_number}/${row.installment_count}` : ""}`,
  ];
  if (row.vehicle_plates.length > 2)
    parts.push(`${row.vehicle_plates.length} veículos`);
  else if (row.vehicle_plates.length)
    parts.push(row.vehicle_plates.map(formatPlate).join(", "));
  return `${titleNumber(row.number)} · ${parts.join(" · ")}`;
}

type GroupBy = "due" | "supplier" | "unit";

interface DueTag {
  label: string;
  tone: TagTone;
}

/** The deadline of a day, in the same tag shape as every other state. */
function dueTag(iso: string): DueTag {
  const days = daysUntil(iso);
  if (days < -1) return { label: `Venceu há ${-days} dias`, tone: "danger" };
  if (days === -1) return { label: "Venceu ontem", tone: "danger" };
  if (days === 0) return { label: "Vence hoje", tone: "danger" };
  if (days === 1) return { label: "Amanhã", tone: "warn" };
  if (days <= 3) return { label: `Em ${days} dias`, tone: "warn" };
  return { label: `Em ${days} dias`, tone: "neutral" };
}

interface RowGroup {
  key: string;
  label: string;
  items: TitleRow[];
  due: DueTag | null;
}

function groupRows(rows: TitleRow[], by: GroupBy): RowGroup[] {
  const keyOf = (row: TitleRow) =>
    by === "due"
      ? row.due_date
      : by === "unit"
        ? row.unit_name
        : row.supplier_name;
  const map = new Map<string, TitleRow[]>();
  for (const row of rows)
    map.set(keyOf(row), [...(map.get(keyOf(row)) ?? []), row]);
  const entries = Array.from(map.entries());
  // By supplier or unit, the biggest amount first: that is where to look.
  if (by !== "due") entries.sort((a, b) => total(b[1]) - total(a[1]));
  return entries.map(([key, items]) => ({
    key,
    label: by === "due" ? dayLabel(key) : key,
    items,
    due: by === "due" && items.some(isOpenReal) ? dueTag(key) : null,
  }));
}

function plural(count: number, one: string, many: string): string {
  return count === 1 ? `1 ${one}` : `${count} ${many}`;
}

/** The TON's first line about the view: what deserves attention first. */
function openerFor(rows: TitleRow[], view: string): string {
  const open = rows.filter(isOpenReal);
  const late = open.filter((row) => daysUntil(row.due_date) < 0);
  const blocked = open.filter((row) => row.blocking > 0);
  const parts = [
    `Na visão “${view}” há ${plural(rows.length, "título", "títulos")}, ${brl(total(rows))}.`,
  ];
  if (late.length)
    parts.push(
      `${late.length === 1 ? "Um já venceu" : `${late.length} já venceram`} (${brl(total(late))}).`
    );
  const first = blocked[0];
  if (first)
    parts.push(
      `O que mais me preocupa: ${plural(blocked.length, "título travado", "títulos travados")}${first.top_issue ? `, como ${titleNumber(first.number)} (${first.top_issue.toLowerCase()})` : ""}.`
    );
  parts.push(
    "Pergunte o que quiser sobre esta tela, ou me peça para resolver algo."
  );
  return parts.join(" ");
}

function rowContext(row: TitleRow, screen: string): AskTonContext {
  const code = titleNumber(row.number);
  const status = STATUS[row.status].label;
  const more = row.blocking + row.attention - 1;
  return {
    screen: `${code} · ${row.supplier_name}`,
    chips: [
      "Contas a pagar",
      dayLabel(row.due_date),
      `${code} · ${brl(row.amount)}`,
    ],
    details: [
      `Tela de origem: ${screen}`,
      `Título ${code} (id ${row.id}) do fornecedor ${row.supplier_name}, CNPJ ${row.supplier_tax_id}`,
      `Documento: ${docLine(row)}`,
      `Unidade: ${row.unit_name} · natureza ${row.account_code} ${row.account_label}`,
      `Valor ${brl(row.amount)} · vence ${row.due_date} · pagar por ${row.payment_method}`,
      `Situação: ${status}`,
      row.top_issue
        ? `O TON apontou: ${row.top_issue} (${row.blocking} impedimentos, ${row.attention} pontos de atenção)`
        : "O TON não apontou nada neste título.",
    ],
    opener: row.top_issue
      ? `${code} está “${status.toLowerCase()}” e eu apontei: ${row.top_issue.toLowerCase()}${more > 0 ? ` (e mais ${more})` : ""}. Quer que eu explique o porquê, ou que diga o que falta para liberar?`
      : `${code} está “${status.toLowerCase()}” e não vi nada de errado nele. Pergunte o que quiser.`,
    suggestions: row.top_issue
      ? [
          "Por que você apontou isso?",
          "O que falta para liberar este título?",
          "Compara com os outros títulos deste fornecedor",
        ]
      : [
          "Posso pagar este título?",
          "Compara com os outros títulos deste fornecedor",
        ],
  };
}

function Agenda({ context }: { context: PayablesContext }) {
  const router = useRouter();
  const titles = useTitles();
  const suppliers = useSuppliers();
  const finance = context.is_finance;
  const [view, setView] = useState("abertos");
  const [query, setQuery] = useState("");
  const [unit, setUnit] = useState(ANY);
  const [due, setDue] = useState(ANY);
  const [nature, setNature] = useState(ANY);
  const [pay, setPay] = useState(ANY);
  const [tonOnly, setTonOnly] = useState(false);
  const [groupBy, setGroupBy] = useState<GroupBy>("due");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);

  const showUnit = context.units.length > 1;
  const all = titles.data ?? [];
  const pendingSuppliers = (suppliers.data ?? []).filter(
    (item) => item.status === "PENDING"
  ).length;

  // Filters narrow the rows; the views then count within them.
  const filtered = useMemo(() => {
    const needle = normalize(query.trim());
    const plate = query.toUpperCase().replace(/[^A-Z0-9]/g, "");
    const digits = query.replace(/\D/g, "");
    return all.filter((row) => {
      if (unit !== ANY && row.unit_id !== unit) return false;
      if (nature !== ANY && row.account_code !== nature) return false;
      if (pay !== ANY && !row.payment_method.startsWith(pay)) return false;
      if (!dueMatches(row, due)) return false;
      if (tonOnly && !row.top_issue) return false;
      if (!needle) return true;
      return (
        normalize(
          `${row.supplier_name} ${row.document_number ?? ""} ${row.description} ${titleNumber(row.number)}`
        ).includes(needle) ||
        (digits.length >= 4 &&
          row.supplier_tax_id.replace(/\D/g, "").includes(digits)) ||
        (plate.length >= 3 &&
          row.vehicle_plates.some((value) => value.includes(plate)))
      );
    });
  }, [all, query, unit, nature, pay, due, tonOnly]);

  const views = VIEWS.filter((item) => finance || !item.financeOnly);
  const current = views.find((item) => item.key === view) ?? views[0];
  const rows = current ? filtered.filter(current.test) : filtered;
  const groups = useMemo(() => groupRows(rows, groupBy), [rows, groupBy]);
  const natures = Array.from(
    new Map(all.map((row) => [row.account_code, row.account_label])).entries()
  ).sort(([a], [b]) => a.localeCompare(b));
  const picked = rows.filter((row) => selected.has(row.id));

  const unitName = (id: string) =>
    context.units.find((item) => item.id === id)?.name ?? id;
  const tokens: FilterToken[] = [];
  if (unit !== ANY)
    tokens.push({
      key: "unit",
      label: "Unidade",
      value: unitName(unit),
      onRemove: () => setUnit(ANY),
    });
  if (due !== ANY)
    tokens.push({
      key: "due",
      label: "Vencimento",
      value: DUE_OPTIONS.find((item) => item.value === due)?.label ?? due,
      onRemove: () => setDue(ANY),
    });
  if (nature !== ANY)
    tokens.push({
      key: "nature",
      label: "Natureza",
      value: nature,
      onRemove: () => setNature(ANY),
    });
  if (pay !== ANY)
    tokens.push({
      key: "pay",
      label: "Pagamento",
      value: pay,
      onRemove: () => setPay(ANY),
    });
  if (tonOnly)
    tokens.push({
      key: "ton",
      label: "TON",
      value: "só o que apontou",
      onRemove: () => setTonOnly(false),
    });

  const screen = finance ? "Agenda de pagamentos" : "Contas da unidade";
  const viewLabel = current?.label ?? "";

  useAskTonPage({
    screen,
    chips: [
      "Contas a pagar",
      `Visão: ${viewLabel}`,
      ...(tokens.length
        ? [`Filtros: ${tokens.map((item) => item.value).join(", ")}`]
        : []),
      "Esta tela",
    ],
    details: [
      `Visão ativa: ${viewLabel} · ${rows.length} títulos · ${brl(total(rows))}`,
      ...tokens.map((item) => `Filtro ${item.label}: ${item.value}`),
      ...rows
        .slice(0, 40)
        .map(
          (row) =>
            `${titleNumber(row.number)} · ${row.supplier_name} · vence ${row.due_date} · ${brl(row.amount)} · ${STATUS[row.status].label}${row.top_issue ? ` · TON: ${row.top_issue}` : ""}`
        ),
    ],
    opener: titles.data ? openerFor(rows, viewLabel) : undefined,
    suggestions: [
      "O que dá para pagar hoje?",
      "O que está travando pagamento e quem precisa agir?",
      "Tem algum título repetido ou suspeito?",
    ],
  });

  function open(id: string) {
    rememberQueue(rows.map((row) => row.id));
    router.push(`/ton/contas-a-pagar/${id}` as Route);
  }

  function toggle(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function runBatch(action: "CONFER" | "RELEASE") {
    const ids = picked
      .filter((row) =>
        action === "CONFER"
          ? row.status === "RECEIVED"
          : row.status === "CONFERRED"
      )
      .map((row) => row.id);
    setBusy(true);
    try {
      const result = await payablesJson<BatchResult>(
        "POST",
        "/titles/batch-actions",
        {
          ids,
          action,
        }
      );
      const verb = action === "CONFER" ? "conferido" : "liberado";
      if (result.done.length)
        toast.success(
          result.done.length === 1
            ? `1 título ${verb}.`
            : `${result.done.length} títulos ${verb}s.`
        );
      if (result.failed.length)
        toast.error(
          `${result.failed.length} não ${result.failed.length === 1 ? "pôde" : "puderam"} seguir: ${result.failed
            .slice(0, 3)
            .map((item) => `${titleNumber(item.number)} (${item.message})`)
            .join("; ")}`
        );
      setSelected(new Set());
      await titles.mutate();
    } catch (error) {
      toast.error(errorText(error, "Não foi possível concluir."));
    } finally {
      setBusy(false);
    }
  }

  async function download(kind: "lote" | "zip") {
    setBusy(true);
    try {
      await downloadForTitles(
        kind === "lote" ? "/titles/payment-batch" : "/titles/attachments-zip",
        picked.map((row) => row.id),
        kind === "lote" ? "lote-de-pagamento.xlsx" : "notas-e-boletos.zip"
      );
    } catch (error) {
      toast.error(errorText(error, "Não foi possível gerar o arquivo."));
    } finally {
      setBusy(false);
    }
  }

  const canConfer = picked.some((row) => row.status === "RECEIVED");
  const canRelease = picked.some((row) => row.status === "CONFERRED");
  const allChecked =
    rows.length > 0 && rows.every((row) => selected.has(row.id));
  const leadColumns = (finance ? 1 : 0) + (showUnit ? 4 : 3);

  return (
    <PageFrame>
      <PageHead
        title={screen}
        description={
          finance
            ? "O que as unidades enviaram, na ordem em que vence. Confira, resolva o que o TON apontou e gere o lote para pagar."
            : "Envie cada conta assim que a nota chegar. Aqui você acompanha o que o financeiro conferiu, devolveu ou liberou."
        }
        actions={
          <>
            <Button
              prominence="tertiary"
              icon={SvgUsers}
              onClick={() =>
                router.push("/ton/contas-a-pagar/fornecedores" as Route)
              }
            >
              {finance && pendingSuppliers
                ? `Fornecedores (${pendingSuppliers} em aprovação)`
                : "Fornecedores"}
            </Button>
            <Button
              icon={SvgPlus}
              onClick={() => router.push("/ton/contas-a-pagar/nova" as Route)}
            >
              Nova conta
            </Button>
          </>
        }
      />

      {titles.isLoading && <LoadingBlock label="Carregando…" lines={6} />}
      {titles.error && (
        <ErrorState
          message="Não foi possível carregar as contas."
          onRetry={() => titles.mutate()}
        />
      )}
      {titles.data && all.length === 0 && (
        <div className="tn-card">
          <EmptyState
            icon={SvgWallet}
            tone="brand"
            title="Nenhuma conta enviada ainda"
            description={
              finance
                ? "Quando as unidades enviarem as contas, elas aparecem aqui na ordem de vencimento."
                : "Envie a primeira conta com a nota e o boleto. O TON lê os documentos e preenche quase tudo."
            }
            action={
              <Button
                icon={SvgPlus}
                onClick={() => router.push("/ton/contas-a-pagar/nova" as Route)}
              >
                Nova conta
              </Button>
            }
          />
        </div>
      )}

      {all.length > 0 && (
        <>
          <ViewTabs
            label="Visões"
            value={current?.key ?? "abertos"}
            onChange={(key) => {
              setView(key);
              setSelected(new Set());
            }}
            views={views
              .map((item) => ({ item, matching: filtered.filter(item.test) }))
              // An empty view is noise, unless it is the one in use.
              .filter(
                ({ item, matching }) =>
                  matching.length > 0 ||
                  item.key === "abertos" ||
                  current?.key === item.key
              )
              .map(({ item, matching }) => ({
                key: item.key,
                label: item.label,
                tone: item.tone,
                count: matching.length,
                total:
                  item.money && matching.length
                    ? brl(total(matching))
                    : undefined,
              }))}
          />

          <section className="tn-card" aria-label="Títulos">
            <FilterBar
              search={{
                value: query,
                onChange: setQuery,
                placeholder: "Fornecedor, CNPJ, nº da nota, placa ou CP-",
              }}
              tokens={tokens}
              onClear={() => {
                setUnit(ANY);
                setDue(ANY);
                setNature(ANY);
                setPay(ANY);
                setTonOnly(false);
              }}
              end={
                <Segmented
                  label="Agrupar"
                  lead="Agrupar"
                  value={groupBy}
                  onChange={setGroupBy}
                  options={[
                    { key: "due", label: "Vencimento" },
                    { key: "supplier", label: "Fornecedor" },
                    ...(showUnit
                      ? [{ key: "unit" as const, label: "Unidade" }]
                      : []),
                  ]}
                />
              }
              panel={
                <>
                  {showUnit && (
                    <FilterField label="Unidade">
                      <Select
                        value={unit}
                        label="Unidade"
                        placeholder="Todas as unidades"
                        options={[
                          { value: ANY, label: "Todas as unidades" },
                          ...context.units.map((item) => ({
                            value: item.id,
                            label: item.name,
                          })),
                        ]}
                        onChange={setUnit}
                      />
                    </FilterField>
                  )}
                  <FilterField label="Vencimento">
                    <Select
                      value={due}
                      label="Vencimento"
                      placeholder="Qualquer vencimento"
                      searchAbove={99}
                      options={DUE_OPTIONS}
                      onChange={setDue}
                    />
                  </FilterField>
                  <FilterField label="Natureza" span={2}>
                    <Select
                      value={nature}
                      label="Natureza"
                      placeholder="Todas as naturezas"
                      options={[
                        { value: ANY, label: "Todas as naturezas" },
                        ...natures.map(([code, label]) => ({
                          value: code,
                          label: `${code} ${label}`,
                        })),
                      ]}
                      onChange={setNature}
                    />
                  </FilterField>
                  <FilterField label="Forma de pagamento">
                    <Select
                      value={pay}
                      label="Forma de pagamento"
                      placeholder="Qualquer pagamento"
                      searchAbove={99}
                      options={PAY_OPTIONS}
                      onChange={setPay}
                    />
                  </FilterField>
                  <FilterField label="Apontamentos">
                    <Switch checked={tonOnly} onChange={setTonOnly} tone="gold">
                      <TonMark>Só o que o TON apontou</TonMark>
                    </Switch>
                  </FilterField>
                </>
              }
            />

            {rows.length === 0 ? (
              <div className="border-t border-01">
                <EmptyState
                  icon={SvgCheckCircle}
                  tone="brand"
                  title="Nada nesta visão"
                  description="Troque a visão ou limpe os filtros para ver outros títulos."
                />
              </div>
            ) : (
              <div className="overflow-x-auto border-t border-01">
                <table className="tp-table">
                  <thead>
                    <tr>
                      {finance && (
                        <th scope="col" className="tp-check">
                          <input
                            type="checkbox"
                            className="tp-checkbox"
                            aria-label="Selecionar todos"
                            checked={allChecked}
                            onChange={() =>
                              setSelected(
                                allChecked
                                  ? new Set()
                                  : new Set(rows.map((row) => row.id))
                              )
                            }
                          />
                        </th>
                      )}
                      <th scope="col">Fornecedor e documento</th>
                      {showUnit && <th scope="col">Unidade</th>}
                      <th scope="col">Natureza</th>
                      <th scope="col">Pagar por</th>
                      <th scope="col" className="tp-end">
                        Valor
                      </th>
                      <th scope="col">Situação</th>
                      <th scope="col">O TON apontou</th>
                      <th scope="col" className="w-10">
                        <span className="sr-only">Perguntar ao TON</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {groups.map((group) => (
                      <Fragment key={group.key}>
                        <tr className="tp-group">
                          {finance && <td aria-hidden="true" />}
                          <td colSpan={showUnit ? 4 : 3}>
                            <span className="flex flex-wrap items-center gap-2.5">
                              {group.label}
                              {group.due && (
                                <Tag tone={group.due.tone}>
                                  {group.due.label}
                                </Tag>
                              )}
                              <span className="tp-muted font-normal">
                                {plural(
                                  group.items.length,
                                  "título",
                                  "títulos"
                                )}
                              </span>
                            </span>
                          </td>
                          <td className="tp-end tn-num">
                            {brl(total(group.items))}
                          </td>
                          <td colSpan={3} aria-hidden="true" />
                        </tr>
                        {group.items.map((row) => (
                          <tr
                            key={row.id}
                            className="tp-row"
                            tabIndex={0}
                            data-selected={
                              selected.has(row.id) ? "true" : undefined
                            }
                            aria-label={`Abrir ${titleNumber(row.number)}`}
                            onClick={() => open(row.id)}
                            onKeyDown={(event) => {
                              if (event.key === "Enter") open(row.id);
                            }}
                          >
                            {finance && (
                              <td
                                className="tp-check"
                                onClick={(event) => event.stopPropagation()}
                              >
                                <input
                                  type="checkbox"
                                  className="tp-checkbox"
                                  aria-label={`Selecionar ${titleNumber(row.number)}`}
                                  checked={selected.has(row.id)}
                                  onChange={() => toggle(row.id)}
                                />
                              </td>
                            )}
                            <td className="tp-wrap">
                              <span className="flex flex-col">
                                {groupBy === "supplier" ? (
                                  // The group already names the supplier: the
                                  // row says when it falls due.
                                  <span className="flex items-center gap-2">
                                    <span className="tp-strong">
                                      {dayLabel(row.due_date)}
                                    </span>
                                    {isOpenReal(row) && (
                                      <Tag tone={dueTag(row.due_date).tone}>
                                        {dueTag(row.due_date).label}
                                      </Tag>
                                    )}
                                  </span>
                                ) : (
                                  <span className="tp-strong">
                                    {row.supplier_name}
                                  </span>
                                )}
                                <span className="tp-muted">{docLine(row)}</span>
                              </span>
                            </td>
                            {showUnit && (
                              <td className="tp-muted">{row.unit_name}</td>
                            )}
                            <td className="tp-muted">
                              <span className="text-text-02 me-1.5">
                                {row.account_code}
                              </span>
                              {row.account_label}
                            </td>
                            <td className="tp-muted">{row.payment_method}</td>
                            <td className="tp-end tp-strong tn-num">
                              <span
                                className={
                                  row.kind === "ESTIMATE"
                                    ? "tp-muted"
                                    : undefined
                                }
                              >
                                {brl(row.amount)}
                              </span>
                            </td>
                            <td>
                              <StatusPill tone={STATUS[row.status].tone}>
                                {STATUS[row.status].label}
                              </StatusPill>
                            </td>
                            <td>
                              {row.top_issue && (
                                <TonMark>
                                  {row.blocking + row.attention > 1
                                    ? `${row.top_issue} +${row.blocking + row.attention - 1}`
                                    : row.top_issue}
                                </TonMark>
                              )}
                            </td>
                            <td onClick={(event) => event.stopPropagation()}>
                              <AskTonRowButton
                                label={titleNumber(row.number)}
                                context={rowContext(row, screen)}
                              />
                            </td>
                          </tr>
                        ))}
                      </Fragment>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <td colSpan={leadColumns} className="tp-muted">
                        {plural(rows.length, "título", "títulos")}
                      </td>
                      <td className="tp-end tn-num">{brl(total(rows))}</td>
                      <td colSpan={3} aria-hidden="true" />
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </section>

          {finance && picked.length > 0 && (
            <BatchBar
              summary={`${picked.length} ${picked.length === 1 ? "selecionado" : "selecionados"} · ${brl(total(picked))}`}
            >
              {canConfer && (
                <BatchButton
                  label="Conferir"
                  disabled={busy}
                  onClick={() => void runBatch("CONFER")}
                />
              )}
              {canRelease && (
                <BatchButton
                  label="Liberar para pagar"
                  disabled={busy}
                  onClick={() => void runBatch("RELEASE")}
                />
              )}
              <BatchButton
                label="Baixar notas e boletos (.zip)"
                disabled={busy}
                onClick={() => void download("zip")}
              />
              <BatchButton
                label="Gerar lote de pagamento"
                primary
                disabled={busy}
                onClick={() => void download("lote")}
              />
            </BatchBar>
          )}
          {finance && (
            <Text as="p" font="secondary-body" color="text-03">
              O lote de pagamento é uma planilha com favorecido, CPF/CNPJ, chave
              PIX ou banco, valor, vencimento e o histórico pronto para o NG. O
              .zip traz as notas e os boletos com nome padronizado. Juntos,
              substituem imprimir nota e boleto para quem paga.
            </Text>
          )}
        </>
      )}
    </PageFrame>
  );
}

export default function PayablesPage() {
  const context = usePayablesContext();
  if (context.error) {
    return (
      <PageContainer>
        <EmptyState
          icon={SvgLock}
          title="Sem acesso às contas a pagar"
          description="Peça ao administrador do TON para liberar sua unidade."
        />
      </PageContainer>
    );
  }
  if (!context.data) {
    return (
      <PageContainer>
        <LoadingBlock label="Carregando…" lines={6} />
      </PageContainer>
    );
  }
  return <Agenda context={context.data} />;
}
