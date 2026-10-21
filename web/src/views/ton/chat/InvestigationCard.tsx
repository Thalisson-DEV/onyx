"use client";

import { useState } from "react";
import { Button, Text } from "@opal/components";
import { SvgChevronDown, SvgSearch } from "@opal/icons";

const CARD = {
  more: (count: number) => `Ver mais ${count}`,
  less: "Ver menos",
  parameters: "Parâmetros do teste",
};

const VISIBLE_ROWS = 6;

type Cell = string | number | boolean | null;
type Row = Record<string, Cell>;

/** Keys that become columns: plain values only, evidence and lists stay out. */
function columns(rows: Row[]): string[] {
  const keys: string[] = [];
  for (const row of rows.slice(0, 5))
    for (const key of Object.keys(row))
      if (!keys.includes(key) && key !== "evidencia" && key !== "chave")
        keys.push(key);
  return keys.slice(0, 6);
}

function label(key: string): string {
  const text = key.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function plainRows(value: unknown): Row[] {
  if (!Array.isArray(value)) return [];
  return value
    .filter(
      (item): item is Record<string, unknown> =>
        typeof item === "object" && item !== null && !Array.isArray(item)
    )
    .map((item) =>
      Object.fromEntries(
        Object.entries(item).filter(
          (entry): entry is [string, Cell] =>
            entry[1] === null || typeof entry[1] !== "object"
        )
      )
    );
}

export interface InvestigationData {
  title: string;
  summary: string | null;
  parameters: Record<string, unknown> | null;
  rows: Row[];
}

/** Reads the result of an investigation tool into a title, summary and rows. */
export function investigationData(value: unknown): InvestigationData | null {
  if (typeof value !== "object" || value === null) return null;
  const body: Record<string, unknown> = { ...value };
  const parameters =
    typeof body.parametros_do_teste === "object" &&
    body.parametros_do_teste !== null
      ? { ...body.parametros_do_teste }
      : null;
  if (body.kind === "investigation")
    return {
      title: String(body.teste ?? ""),
      summary: typeof body.resumo === "string" ? body.resumo : null,
      parameters,
      rows: plainRows(body.itens),
    };
  if (body.kind === "dre_comparison")
    return {
      title: String(body.estrutura ?? ""),
      summary: Array.isArray(body.colunas) ? body.colunas.join(" · ") : null,
      parameters: null,
      rows: plainRows(body.linhas),
    };
  if (body.kind === "line_entries")
    return {
      title: String(body.linha ?? ""),
      summary: typeof body.escopo === "string" ? body.escopo : null,
      parameters: null,
      rows: plainRows(body.maiores),
    };
  return null;
}

interface InvestigationCardProps {
  data: InvestigationData;
}

/** A test, search or comparison the TON ran, as a short table. */
export default function InvestigationCard({ data }: InvestigationCardProps) {
  const [open, setOpen] = useState(false);
  const keys = columns(data.rows);
  const shown = open ? data.rows : data.rows.slice(0, VISIBLE_ROWS);
  const parameters = Object.entries(data.parameters ?? {}).filter(
    ([, value]) => value !== null && value !== ""
  );
  return (
    <div className="ton-result-card flex flex-col gap-3 p-3">
      <div className="flex items-center gap-3">
        <span className="ton-icon-tile flex items-center justify-center w-8 h-8 shrink-0">
          <SvgSearch size={16} />
        </span>
        <span className="flex flex-1 min-w-0 flex-col">
          <Text font="main-ui-action" color="text-05">
            {data.title}
          </Text>
          {data.summary && (
            <Text font="secondary-body" color="text-03">
              {data.summary}
            </Text>
          )}
        </span>
      </div>
      {parameters.length > 0 && (
        <Text font="secondary-body" color="text-03">
          {`${CARD.parameters}: ${parameters
            .map(([key, value]) => `${label(key)} ${String(value)}`)
            .join(" · ")}`}
        </Text>
      )}
      {shown.length > 0 && (
        <div className="ton-action-table-wrap">
          <table className="ton-action-table">
            <thead>
              <tr>
                {keys.map((key) => (
                  <th key={key}>
                    <Text font="secondary-action" color="text-03">
                      {label(key)}
                    </Text>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {shown.map((row, index) => (
                <tr key={index}>
                  {keys.map((key) => (
                    <td key={key}>
                      <Text font="secondary-body" color="text-04">
                        {row[key] == null ? "—" : String(row[key])}
                      </Text>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data.rows.length > VISIBLE_ROWS && (
        <div>
          <Button
            prominence="tertiary"
            size="sm"
            icon={SvgChevronDown}
            onClick={() => setOpen(!open)}
          >
            {open ? CARD.less : CARD.more(data.rows.length - VISIBLE_ROWS)}
          </Button>
        </div>
      )}
    </div>
  );
}
