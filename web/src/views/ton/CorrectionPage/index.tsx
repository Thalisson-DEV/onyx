"use client";

import { Fragment, useMemo, useState } from "react";
import { FilterBar, FilterField } from "@/views/ton/components/kit";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import { Button } from "@opal/components";
import { SvgCheckCircle, SvgFileText, SvgLock } from "@opal/icons";
import { toast } from "@opal/layouts";
import { useUser } from "@/providers/UserProvider";
import { brDate, brl } from "@/lib/ton/payables";
import {
  CRITICALITY_TONE,
  SITUATION_TONE,
  caseNumber,
  correctionJson,
  isOpen,
  rememberCases,
  useCases,
  type CaseRow,
} from "@/lib/ton/correction";
import { errorText } from "@/lib/ton/payables";
import {
  EmptyState,
  ErrorState,
  LoadingBlock,
  PageContainer,
  StatusPill,
} from "@/views/ton/components/ui";
import {
  BatchBar,
  BatchButton,
  PatternHead,
  QuickView,
} from "@/views/ton/components/pattern";
import { Select } from "@/views/ton/PayablesPage/fields";
import OwnerDialog from "@/views/ton/CorrectionPage/OwnerDialog";
import ReminderDialog from "@/views/ton/CorrectionPage/ReminderDialog";

const LEVEL_LABEL: Record<string, string> = {
  CRITICAL: "Crítica",
  HIGH: "Alta",
  MEDIUM: "Média",
  MONITORING: "Monitoramento",
};

const ANY = "__any";
const NO_OWNER = "__none";

interface View {
  key: string;
  label: string;
  tone?: "danger" | "warning" | "success" | "brand";
  test: (row: CaseRow) => boolean;
  money?: boolean;
}

const VIEWS: View[] = [
  { key: "abertos", label: "Em aberto", money: true, test: isOpen },
  {
    key: "criticas",
    label: "Críticas",
    tone: "danger",
    money: true,
    test: (row) => isOpen(row) && row.criticality === "CRITICAL",
  },
  {
    key: "vencidos",
    label: "Prazo vencido",
    tone: "danger",
    test: (row) => row.situation === "OVERDUE",
  },
  {
    key: "sem-dono",
    label: "Sem responsável",
    tone: "warning",
    test: (row) => row.situation === "UNASSIGNED",
  },
  {
    key: "reincidentes",
    label: "Reincidentes",
    tone: "warning",
    test: (row) => isOpen(row) && row.recurring,
  },
  {
    key: "verificadas",
    label: "Corrigidas e verificadas",
    tone: "success",
    money: true,
    test: (row) => row.situation === "VERIFIED",
  },
  {
    key: "aceitas",
    label: "Risco aceito",
    test: (row) => row.situation === "ACCEPTED",
  },
];

function amountOf(row: CaseRow): number {
  return Number(
    row.situation === "VERIFIED" ? row.impact_total : row.impact_open
  );
}

function total(rows: CaseRow[]): number {
  return rows.reduce((sum, row) => sum + amountOf(row), 0);
}

function short(value: number): string {
  if (value >= 1_000_000)
    return `R$ ${(value / 1_000_000).toFixed(2).replace(".", ",")} mi`;
  if (value >= 1_000)
    return `R$ ${(value / 1_000).toFixed(1).replace(".", ",")} mil`;
  return brl(value);
}

function groupOf(row: CaseRow): string {
  if (row.situation === "VERIFIED") return "Corrigidas e verificadas pelo TON";
  if (row.situation === "ACCEPTED") return "Risco aceito";
  return row.owner_area ?? "Sem responsável";
}

function normalize(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

function Plan() {
  const router = useRouter();
  const cases = useCases();
  const [view, setView] = useState("abertos");
  const [query, setQuery] = useState("");
  const [owner, setOwner] = useState(ANY);
  const [month, setMonth] = useState(ANY);
  const [level, setLevel] = useState(ANY);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [assigning, setAssigning] = useState(false);
  const [reminding, setReminding] = useState(false);
  const [busy, setBusy] = useState(false);

  const all = cases.data ?? [];
  const filtered = useMemo(() => {
    const needle = normalize(query.trim());
    return all.filter((row) => {
      if (owner === NO_OWNER && row.owner_area) return false;
      if (owner !== ANY && owner !== NO_OWNER && row.owner_area !== owner)
        return false;
      if (month !== ANY && !row.months.includes(month)) return false;
      if (level !== ANY && row.criticality !== level) return false;
      if (!needle) return true;
      return normalize(
        `${caseNumber(row.number)} ${row.title} ${row.summary} ${row.origin.file_name ?? ""} ${row.rule_code}`
      ).includes(needle);
    });
  }, [all, query, owner, month, level]);
  const current = VIEWS.find((item) => item.key === view) ?? VIEWS[0];
  const rows = current ? filtered.filter(current.test) : filtered;
  const groups = useMemo(() => {
    const map = new Map<string, CaseRow[]>();
    for (const row of rows)
      map.set(groupOf(row), [...(map.get(groupOf(row)) ?? []), row]);
    return Array.from(map.entries());
  }, [rows]);
  const months = Array.from(new Set(all.flatMap((row) => row.months)));
  const owners = Array.from(
    new Set(
      all
        .map((row) => row.owner_area)
        .filter((value): value is string => Boolean(value))
    )
  );
  const picked = rows.filter((row) => selected.has(row.id));
  const allChecked =
    rows.length > 0 && rows.every((row) => selected.has(row.id));

  function open(id: string) {
    rememberCases(rows.map((row) => row.id));
    router.push(`/ton/ocorrencias/${id}` as Route);
  }

  function toggle(id: string) {
    setSelected((currentSet) => {
      const next = new Set(currentSet);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function includeInBoard() {
    setBusy(true);
    try {
      await correctionJson("POST", "/cases/board", {
        ids: picked.map((row) => row.id),
        include: true,
      });
      toast.success(
        picked.length === 1
          ? "Caso incluído no resumo da diretoria."
          : `${picked.length} casos incluídos no resumo da diretoria.`
      );
      setSelected(new Set());
      await cases.mutate();
    } catch (error) {
      toast.error(errorText(error, "Não foi possível concluir."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageContainer>
      <PatternHead
        eyebrow="Financeiro"
        title="Plano de correção"
        description="O que está errado na origem (NG, unidades, processos), quanto pesa, quem corrige e até quando. O TON confere a cada importação: fecha o que foi corrigido e reabre o que voltou."
        actions={
          <Button
            prominence="secondary"
            icon={SvgFileText}
            onClick={() => router.push("/ton/ocorrencias/diretoria" as Route)}
          >
            Resumo para a diretoria
          </Button>
        }
      />
      {cases.isLoading && <LoadingBlock label="Carregando…" lines={6} />}
      {cases.error && (
        <ErrorState
          message="Não foi possível carregar o plano de correção."
          onRetry={() => cases.mutate()}
        />
      )}
      {cases.data && all.length === 0 && (
        <div className="ton-card">
          <EmptyState
            icon={SvgCheckCircle}
            tone="brand"
            title="Nada para corrigir na origem"
            description="Quando a revisão de uma importação encontrar um problema, ele aparece aqui como um caso, com a origem, o impacto e o que fazer."
          />
        </div>
      )}
      {all.length > 0 && (
        <>
          <div className="tp-chips" role="group" aria-label="Visões rápidas">
            {VIEWS.map((item) => {
              const matching = filtered.filter(item.test);
              if (
                !matching.length &&
                item.key !== "abertos" &&
                current?.key !== item.key
              )
                return null;
              return (
                <QuickView
                  key={item.key}
                  label={item.label}
                  tone={item.tone}
                  count={
                    item.money && matching.length
                      ? `${matching.length} · ${short(total(matching))}`
                      : String(matching.length)
                  }
                  active={current?.key === item.key}
                  onSelect={() => {
                    setView(item.key);
                    setSelected(new Set());
                  }}
                />
              );
            })}
          </div>

          <section className="tn-card" aria-label="Casos">
            <FilterBar
              search={{
                value: query,
                onChange: setQuery,
                placeholder: "Caso, histórico, arquivo ou PC-",
              }}
              tokens={[
                ...(owner !== ANY
                  ? [
                      {
                        key: "owner",
                        label: "Responsável",
                        value: owner === NO_OWNER ? "Sem responsável" : owner,
                        onRemove: () => setOwner(ANY),
                      },
                    ]
                  : []),
                ...(month !== ANY
                  ? [
                      {
                        key: "month",
                        label: "Mês",
                        value: month,
                        onRemove: () => setMonth(ANY),
                      },
                    ]
                  : []),
                ...(level !== ANY
                  ? [
                      {
                        key: "level",
                        label: "Criticidade",
                        value: LEVEL_LABEL[level] ?? level,
                        onRemove: () => setLevel(ANY),
                      },
                    ]
                  : []),
              ]}
              onClear={() => {
                setOwner(ANY);
                setMonth(ANY);
                setLevel(ANY);
              }}
              panel={
                <>
                  <FilterField label="Responsável" span={2}>
                    <Select
                      value={owner}
                      label="Responsável"
                      placeholder="Todos os responsáveis"
                      searchAbove={99}
                      options={[
                        { value: ANY, label: "Todos os responsáveis" },
                        { value: NO_OWNER, label: "Sem responsável" },
                        ...owners.map((item) => ({ value: item, label: item })),
                      ]}
                      onChange={setOwner}
                    />
                  </FilterField>
                  <FilterField label="Mês" span={2}>
                    <Select
                      value={month}
                      label="Mês"
                      placeholder="Todos os meses"
                      searchAbove={99}
                      options={[
                        { value: ANY, label: "Todos os meses" },
                        ...months.map((item) => ({ value: item, label: item })),
                      ]}
                      onChange={setMonth}
                    />
                  </FilterField>
                  <FilterField label="Criticidade" span={2}>
                    <Select
                      value={level}
                      label="Criticidade"
                      placeholder="Toda criticidade"
                      searchAbove={99}
                      options={[
                        { value: ANY, label: "Toda criticidade" },
                        ...Object.entries(LEVEL_LABEL).map(
                          ([value, label]) => ({
                            value,
                            label,
                          })
                        ),
                      ]}
                      onChange={setLevel}
                    />
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
                  description="Troque a visão ou limpe os filtros."
                />
              </div>
            ) : (
              <div className="overflow-x-auto border-t border-01">
                <table className="tp-table">
                  <thead>
                    <tr>
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
                      <th scope="col">Caso</th>
                      <th scope="col">De onde veio</th>
                      <th scope="col" className="tp-end">
                        Impacto
                      </th>
                      <th scope="col">Criticidade</th>
                      <th scope="col">Responsável e prazo</th>
                      <th scope="col">Situação</th>
                    </tr>
                  </thead>
                  <tbody>
                    {groups.map(([group, items]) => (
                      <Fragment key={group}>
                        <tr className="tp-group">
                          <td />
                          <td
                            colSpan={2}
                          >{`${group} · ${items.length} ${items.length === 1 ? "caso" : "casos"}`}</td>
                          <td className="tp-end">
                            {items.some((row) => row.has_amount)
                              ? short(total(items))
                              : ""}
                          </td>
                          <td colSpan={3} />
                        </tr>
                        {items.map((row) => (
                          <tr
                            key={row.id}
                            className="tp-row"
                            tabIndex={0}
                            data-selected={
                              selected.has(row.id) ? "true" : undefined
                            }
                            aria-label={`Abrir ${caseNumber(row.number)}`}
                            onClick={() => open(row.id)}
                            onKeyDown={(event) => {
                              if (event.key === "Enter") open(row.id);
                            }}
                          >
                            <td
                              className="tp-check"
                              onClick={(event) => event.stopPropagation()}
                            >
                              <input
                                type="checkbox"
                                className="tp-checkbox"
                                aria-label={`Selecionar ${caseNumber(row.number)}`}
                                checked={selected.has(row.id)}
                                onChange={() => toggle(row.id)}
                              />
                            </td>
                            <td className="tp-wrap">
                              <span className="flex flex-col">
                                <span className="tp-strong">{row.title}</span>
                                <span className="tp-muted">{`${caseNumber(row.number)} · ${row.summary}`}</span>
                              </span>
                            </td>
                            <td
                              className="tp-wrap"
                              style={{ minWidth: "12rem" }}
                            >
                              <span className="flex flex-col">
                                <span>{`${row.origin.system.split(" · ")[0]} · ${row.origin.sheets.length > 2 ? `${row.origin.sheets.length} abas` : row.origin.sheets.join(", ") || "—"}`}</span>
                                <span className="tp-muted">
                                  {row.origin.imported_at
                                    ? `importado em ${brDate(row.origin.imported_at.slice(0, 10))}`
                                    : ""}
                                </span>
                              </span>
                            </td>
                            <td className="tp-end tp-strong">
                              {row.has_amount ? (
                                short(amountOf(row))
                              ) : (
                                <span className="tp-muted">sem valor lido</span>
                              )}
                            </td>
                            <td>
                              <span className="flex flex-col items-start gap-1">
                                <StatusPill
                                  tone={CRITICALITY_TONE[row.criticality]}
                                >
                                  {row.criticality_label}
                                </StatusPill>
                                <span
                                  className="tp-muted"
                                  style={{
                                    whiteSpace: "normal",
                                    fontSize: "0.75rem",
                                  }}
                                >
                                  {row.criticality_reason}
                                </span>
                              </span>
                            </td>
                            <td>
                              {row.owner_area ? (
                                <span className="flex flex-col">
                                  <span>
                                    {[row.owner_area, row.owner_name]
                                      .filter(Boolean)
                                      .join(" · ")}
                                  </span>
                                  <span className="tp-muted">
                                    {row.due_date
                                      ? `até ${brDate(row.due_date)}`
                                      : "sem prazo"}
                                  </span>
                                </span>
                              ) : (
                                <span className="tp-muted">{`sugerido: ${row.suggested_area}`}</span>
                              )}
                            </td>
                            <td>
                              <StatusPill tone={SITUATION_TONE[row.situation]}>
                                {row.situation_label}
                              </StatusPill>
                            </td>
                          </tr>
                        ))}
                      </Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {picked.length > 0 && (
            <BatchBar
              summary={`${picked.length} ${picked.length === 1 ? "selecionado" : "selecionados"}${picked.some((row) => row.has_amount) ? ` · ${short(total(picked))}` : ""}`}
            >
              <BatchButton
                label="Definir responsável e prazo"
                disabled={busy}
                onClick={() => setAssigning(true)}
              />
              <BatchButton
                label="Cobrar por e-mail"
                disabled={busy}
                onClick={() => setReminding(true)}
              />
              <BatchButton
                label="Incluir no resumo da diretoria"
                primary
                disabled={busy}
                onClick={() => void includeInBoard()}
              />
            </BatchBar>
          )}
        </>
      )}
      {assigning && (
        <OwnerDialog
          cases={picked}
          onClose={() => setAssigning(false)}
          onSaved={async () => {
            setAssigning(false);
            setSelected(new Set());
            await cases.mutate();
          }}
        />
      )}
      {reminding && (
        <ReminderDialog
          ids={picked.map((row) => row.id)}
          onClose={() => setReminding(false)}
        />
      )}
    </PageContainer>
  );
}

export default function CorrectionPage() {
  const { isAdmin } = useUser();
  if (!isAdmin) {
    return (
      <PageContainer>
        <EmptyState
          icon={SvgLock}
          title="Área da Controladoria"
          description="O plano de correção é usado pela Controladoria."
        />
      </PageContainer>
    );
  }
  return <Plan />;
}
