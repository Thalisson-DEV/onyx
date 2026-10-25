"use client";

import { Button, Text } from "@opal/components";
import {
  COPY,
  formatCurrency,
  formatDay,
  formatMonthName,
  formatNumber,
  formatPeriod,
} from "@/lib/ton/copy";
import { getBusinessLabel } from "@/lib/ton/labels";
import type { DreDefinition, DreLine } from "@/views/admin/DrePage/types";
import {
  ErrorState,
  LoadingBlock,
  StatusPill,
} from "@/views/ton/components/ui";
import {
  Diamond,
  Drawer,
  DrawerSection,
  Tag,
} from "@/views/ton/components/kit";
import { useAskTon } from "@/views/ton/ask/AskTon";
import {
  CONSOLIDATED,
  CONTRIBUTOR_PAGE,
  type DreWorkspace,
} from "@/views/ton/DrePage/useDreWorkspace";

const D = COPY.dre.drawer;

export function scopeLabel(dre: DreWorkspace): string {
  if (!dre.unitId || dre.unitId === CONSOLIDATED) return COPY.dre.consolidated;
  const unit = dre.units.find((item) => item.id === dre.unitId);
  if (!unit) return "";
  return getBusinessLabel(unit.name ?? unit.code);
}

function valueText(
  definition: DreDefinition,
  value: string | null | undefined
) {
  if (value == null) return "—";
  return definition.line_type === "PERCENTAGE"
    ? `${Number(value).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`
    : formatCurrency(value);
}

function changeText(value: number | null): string {
  if (value == null) return "";
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${Math.abs(value).toLocaleString("pt-BR", { maximumFractionDigits: 1, minimumFractionDigits: 1 })}%`;
}

interface Part {
  definition: DreDefinition;
  sign: "+" | "−" | "÷" | "";
}

/** The lines a total is made of, with the operation between them. */
function partsOf(
  definition: DreDefinition,
  definitions: DreDefinition[]
): Part[] {
  const byCode = new Map(definitions.map((item) => [item.code, item]));
  const operands = (definition.operands ?? [])
    .map((code) => byCode.get(code))
    .filter((item): item is DreDefinition => !!item);
  if (definition.operation === "SUBTRACT")
    return operands.map((item, index) => ({
      definition: item,
      sign: index === 0 ? "" : "−",
    }));
  if (definition.operation === "RATIO")
    return operands.map((item, index) => ({
      definition: item,
      sign: index === 0 ? "" : "÷",
    }));
  if (operands.length)
    return operands.map((item) => ({ definition: item, sign: "+" }));
  return definitions
    .filter((item) => item.parent_code === definition.code)
    .map((item) => ({ definition: item, sign: item.excluded ? "" : "+" }));
}

/** Every line and figure of the DRE opens here: what makes the number. */
export default function LineDrawer({ dre }: { dre: DreWorkspace }) {
  const { ask } = useAskTon();
  const line = dre.selectedLine;
  const definition = dre.selectedDefinition;
  const period = dre.drillRun?.scope.period ?? null;
  if (!line || !definition || !period) return null;

  const label = getBusinessLabel(definition.label);
  const account = dre.selectedAccount;
  const months = dre.yearMonths.filter((month) => month.runId);
  const valueIn = (code: string, at: string): string | undefined =>
    dre.yearMonths
      .find((month) => month.period === at)
      ?.lines.find((item: DreLine) => item.code === code)?.realizado;
  const index = months.findIndex((month) => month.period === period);
  const previous = index > 0 ? months[index - 1]?.period : undefined;
  const current = Number(line.realizado);
  const before = previous ? valueIn(definition.code, previous) : undefined;
  const change =
    before != null && Number(before) !== 0
      ? ((Math.abs(current) - Math.abs(Number(before))) /
          Math.abs(Number(before))) *
        100
      : null;
  const isSource = definition.line_type === "SOURCE_SUM";
  const parts = isSource ? [] : partsOf(definition, dre.definitions);
  const series = months.map((month) => ({
    period: month.period,
    value: Number(valueIn(definition.code, month.period) ?? 0),
  }));
  const peak = Math.max(1, ...series.map((item) => Math.abs(item.value)));
  const page = dre.contributors.data;
  const scope = scopeLabel(dre);
  const columns = D.columns;

  function open(code: string, at: string) {
    dre.select.line(code, at);
  }

  function askAbout() {
    ask({
      screen: `${label} · ${formatMonthName(period ?? "")}`,
      chips: [
        "DRE",
        `${scope} · ${formatPeriod(period ?? "")}`,
        `${label} · ${valueText(definition!, line!.realizado)}`,
      ],
      details: [
        `Linha da DRE ${definition!.code} "${label}" (${definition!.line_type}${definition!.excluded ? ", fora do resultado" : ""})`,
        `Escopo: ${scope}. Mês: ${period}. Valor realizado: ${line!.realizado}. Acumulado no ano: ${line!.realizado_ytd}.`,
        previous
          ? `Mês anterior (${previous}): ${before ?? "sem valor"}; variação ${changeText(change)}`
          : "",
        account
          ? `Filtrado na conta NG ${account.code} ${account.label ?? ""}: ${account.amount}`
          : "",
        `Evolução no ano: ${series.map((item) => `${item.period.slice(0, 7)}=${item.value.toFixed(2)}`).join("; ")}`,
        ...parts.map(
          (part) =>
            `Compõe com ${part.sign || "="}: ${part.definition.code} ${getBusinessLabel(part.definition.label)} = ${valueIn(part.definition.code, period ?? "") ?? "—"}`
        ),
        ...(page?.rows ?? [])
          .slice(0, 15)
          .map(
            (fact) =>
              `Lançamento ${fact.record_date ?? ""} · ${fact.source_account_code ?? fact.account_code} · ${fact.description ?? ""} · ${fact.amount}`
          ),
      ].filter(Boolean),
      opener:
        change != null
          ? `${label} em ${formatMonthName(period ?? "")} ficou em ${valueText(definition!, line!.realizado)}, ${changeText(change)} contra ${formatMonthName(previous ?? "")}. ${Math.abs(change) >= 10 ? "É uma mudança grande: quer que eu descubra o que puxou?" : "Pergunte o que quiser sobre esse número."}`
          : `${label} em ${formatMonthName(period ?? "")}: ${valueText(definition!, line!.realizado)}. Pergunte o que quiser sobre esse número.`,
      suggestions: [
        "O que explica esse valor?",
        ...(change != null ? ["O que mudou contra o mês anterior?"] : []),
        isSource
          ? "Tem lançamento estranho aqui?"
          : "Qual linha mais pesa neste total?",
      ],
    });
  }

  return (
    <Drawer
      open
      onClose={() => dre.select.line(null)}
      storageKey="dre-line"
      defaultWidth={760}
      eyebrow={`${D.title} · ${scope}`}
      title={label}
      description={
        isSource
          ? COPY.dre.lineDrawer.sourceHint
          : COPY.dre.lineDrawer.totalHint
      }
      summary={
        <>
          <div className="tn-stat">
            <span className="tn-stat-label">
              {account
                ? D.onlyAccount(account.code, account.label ?? "")
                : formatMonthName(period, true)}
            </span>
            <span className="tn-big-figure">
              {valueText(definition, account ? account.amount : line.realizado)}
            </span>
          </div>
          {!account && change != null && (
            <div className="tn-stat">
              <span className="tn-stat-label">
                {COPY.dre.lineDrawer.versus(formatMonthName(previous ?? ""))}
              </span>
              <span className="tn-figure-sm">{changeText(change)}</span>
            </div>
          )}
          {!account && (
            <div className="tn-stat">
              <span className="tn-stat-label">{COPY.dre.kpi.ytd}</span>
              <span className="tn-figure-sm">
                {valueText(definition, line.realizado_ytd)}
              </span>
            </div>
          )}
          {definition.excluded && <Tag>{COPY.dre.table.excluded}</Tag>}
          {account && (
            <button
              type="button"
              className="tn-link ton-focusable"
              onClick={dre.select.allAccounts}
            >
              {D.allAccounts}
            </button>
          )}
        </>
      }
      subheader={
        <div
          className="tn-views px-2"
          role="group"
          aria-label={COPY.dre.year.monthsLabel}
        >
          {months.map((month) => (
            <button
              key={month.period}
              type="button"
              className="tn-view ton-focusable"
              aria-pressed={month.period === period}
              onClick={() =>
                dre.select.line(
                  definition.code,
                  month.period,
                  account ?? undefined
                )
              }
            >
              {formatMonthName(month.period)}
            </button>
          ))}
        </div>
      }
      footer={
        <>
          <button
            type="button"
            className="tn-btn ton-focusable"
            data-variant="gold"
            onClick={askAbout}
          >
            <Diamond />
            {COPY.dre.lineDrawer.ask}
          </button>
          <span className="tn-spacer" />
          {isSource && page && page.total > CONTRIBUTOR_PAGE && (
            <>
              <Text font="secondary-body" color="text-03">
                {D.page(
                  page.total === 0 ? 0 : dre.offset + 1,
                  Math.min(dre.offset + CONTRIBUTOR_PAGE, page.total),
                  page.total
                )}
              </Text>
              <Button
                size="sm"
                prominence="secondary"
                disabled={dre.offset === 0}
                onClick={() =>
                  dre.select.offset(Math.max(0, dre.offset - CONTRIBUTOR_PAGE))
                }
              >
                {D.previous}
              </Button>
              <Button
                size="sm"
                prominence="secondary"
                disabled={dre.offset + CONTRIBUTOR_PAGE >= page.total}
                onClick={() => dre.select.offset(dre.offset + CONTRIBUTOR_PAGE)}
              >
                {D.next}
              </Button>
            </>
          )}
        </>
      }
    >
      {!isSource && parts.length > 0 && (
        <DrawerSection title={COPY.dre.lineDrawer.composition}>
          <div className="flex flex-col">
            {parts.map((part) => {
              const value = valueIn(part.definition.code, period);
              return (
                <button
                  key={part.definition.code}
                  type="button"
                  className="tn-kv ton-focusable"
                  onClick={() => open(part.definition.code, period)}
                >
                  <span className="tn-kv-sign">{part.sign}</span>
                  <span className="flex-1 min-w-0 text-start truncate">
                    {getBusinessLabel(part.definition.label)}
                    {part.definition.excluded && (
                      <span className="ms-2">
                        <Tag>{COPY.dre.table.excluded}</Tag>
                      </span>
                    )}
                  </span>
                  <span className="tn-num font-semibold">
                    {valueText(part.definition, value)}
                  </span>
                </button>
              );
            })}
          </div>
        </DrawerSection>
      )}

      {isSource && (
        <DrawerSection title={D.entries}>
          {page?.rows[0] && (
            <Text font="secondary-body" color="text-03">
              {D.sourceOnce(
                page.rows[0].source_name,
                page.rows[0].original_filename
              )}
            </Text>
          )}
          {dre.budgetPresent && !account && (
            <div className="ton-segmented self-start" role="group">
              {(["ACTUAL", "BUDGET"] as const).map((type) => (
                <button
                  key={type}
                  type="button"
                  aria-pressed={dre.factType === type}
                  className="ton-focusable ton-segment"
                  onClick={() => dre.select.factType(type)}
                >
                  {type === "ACTUAL" ? D.actual : D.budget}
                </button>
              ))}
            </div>
          )}
          {dre.contributors.isLoading && (
            <LoadingBlock label={COPY.common.loading} lines={6} />
          )}
          {dre.contributors.error && (
            <ErrorState compact onRetry={() => dre.contributors.mutate()} />
          )}
          {page && page.rows.length === 0 && (
            <Text as="p" font="secondary-body" color="text-03">
              {D.empty}
            </Text>
          )}
          {page && page.rows.length > 0 && (
            <div className="tn-ledger-wrap">
              <table className="tn-ledger">
                <thead>
                  <tr>
                    <th scope="col">{columns.date}</th>
                    <th scope="col">{columns.unit}</th>
                    <th scope="col">{columns.account}</th>
                    <th scope="col">{columns.accountName}</th>
                    <th scope="col">{columns.document}</th>
                    <th scope="col" className="w-full">
                      {columns.history}
                    </th>
                    <th scope="col" className="tn-end">
                      {columns.amount}
                    </th>
                    <th scope="col">{columns.origin}</th>
                  </tr>
                </thead>
                <tbody>
                  {page.rows.map((fact) => {
                    const flagged =
                      !!fact.review_status && fact.review_status !== "ACCEPTED";
                    return (
                      <tr key={fact.id}>
                        <td data-cell="date">
                          {fact.record_date ? formatDay(fact.record_date) : "—"}
                        </td>
                        <td data-cell="unit">
                          {getBusinessLabel(fact.unit_name ?? fact.unit_code)}
                        </td>
                        <td data-cell="code">
                          {fact.source_account_code ?? fact.account_code}
                        </td>
                        <td data-cell="account">
                          {fact.source_account_label ?? fact.account_label}
                        </td>
                        <td data-cell="doc">{fact.reference ?? "—"}</td>
                        <td data-cell="history">
                          <span className="tn-ledger-history">
                            {fact.description || "—"}
                          </span>
                          {fact.treatment_title && (
                            <span className="ton-ledger-muted block pt-1">
                              {D.treatedDetail(
                                formatCurrency(
                                  fact.original_amount ?? fact.amount
                                ),
                                fact.treatment_title,
                                fact.treatment_version,
                                fact.original_account_label
                              )}
                            </span>
                          )}
                          {flagged && (
                            <span className="block pt-1">
                              <StatusPill tone="warning">
                                {`${D.review}: ${getBusinessLabel(fact.review_status ?? "")}`}
                              </StatusPill>
                            </span>
                          )}
                        </td>
                        <td
                          data-cell="amount"
                          data-negative={Number(fact.amount) < 0 || undefined}
                        >
                          {formatCurrency(fact.amount)}
                          {fact.treatment_title && (
                            <span className="block pt-1">
                              <StatusPill tone="brand">{D.treated}</StatusPill>
                            </span>
                          )}
                        </td>
                        <td data-cell="origin">
                          {D.row(fact.sheet_name, fact.source_row_number)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <Text font="secondary-body" color="text-03">
                {`${D.sorted} · ${formatNumber(page.total)} ${page.total === 1 ? "lançamento" : "lançamentos"}`}
              </Text>
            </div>
          )}
        </DrawerSection>
      )}

      {series.length > 1 && (
        <DrawerSection title={COPY.dre.lineDrawer.evolution}>
          <div className="flex flex-col">
            {series.map((item) => (
              <button
                key={item.period}
                type="button"
                className="tn-kv ton-focusable"
                aria-pressed={item.period === period}
                onClick={() => open(definition.code, item.period)}
              >
                <span className="w-24 shrink-0 text-start">
                  {formatMonthName(item.period)}
                </span>
                <span className="tn-bar">
                  <i
                    data-negative={item.value < 0 || undefined}
                    style={{
                      width: `${Math.max(2, (Math.abs(item.value) / peak) * 100)}%`,
                    }}
                  />
                </span>
                <span className="tn-num w-36 text-end">
                  {valueText(definition, String(item.value))}
                </span>
              </button>
            ))}
          </div>
        </DrawerSection>
      )}
    </Drawer>
  );
}
