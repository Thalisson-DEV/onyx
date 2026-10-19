"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Button, Text } from "@opal/components";
import { SvgPlus, SvgTrash, SvgX } from "@opal/icons";
import { cn } from "@opal/utils";
import { COPY, formatNumber } from "@/lib/ton/copy";
import { TonApiError, postTonJson } from "@/lib/ton/decisions";
import { IMPORT_DIAGNOSTIC_KEYS } from "@/lib/ton/import-diagnostics";
import type { ClientImport, ClientSource } from "@/lib/ton/types";

const T = COPY.sources.paste;

/** Sources whose table the Controladoria keeps and can paste into the TON. */
export const PASTE_COLUMNS: Record<string, string[]> = {
  installments: [
    "Mês",
    "Data de pagamento",
    "Unidade",
    "Conta NG",
    "Credor",
    "Nº do parcelamento",
    "Parcela",
    "Valor pago",
  ],
};
const START_ROWS = 12;

interface Problem {
  code: string;
  level: string;
  row_number: number | null;
  column: string | null;
}

interface Validation {
  records: number;
  problems: Problem[];
  result: ClientImport | null;
}

function letter(index: number): string {
  let value = index + 1;
  let out = "";
  while (value > 0) {
    const rest = (value - 1) % 26;
    out = String.fromCharCode(65 + rest) + out;
    value = Math.floor((value - 1) / 26);
  }
  return out;
}

function columnIndex(column: string): number {
  return [...column].reduce((total, char) => total * 26 + char.charCodeAt(0) - 64, 0) - 1;
}

function normal(value: string): string {
  return value
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .trim();
}

/** Wider columns for long text, narrow ones for codes and numbers. */
function widthOf(title: string): string {
  const name = normal(title);
  if (name.includes("unidade")) return "17rem";
  if (["credor", "descri", "hist"].some((word) => name.includes(word)))
    return "14rem";
  if (name.includes("conta")) return "11rem";
  if (name.includes("parcelamento")) return "10rem";
  if (name.includes("data") || name.includes("valor")) return "9rem";
  if (name === "parcela") return "6rem";
  if (name.includes("mes")) return "7rem";
  return "9rem";
}

function emptyRow(width: number): string[] {
  return Array.from({ length: width }, () => "");
}

/** Excel copies cells as tab-separated lines. */
function parseClipboard(text: string): string[][] {
  const lines = text.replace(/\r\n?/g, "\n").split("\n");
  while (lines.length && lines[lines.length - 1] === "") lines.pop();
  return lines.map((line) => line.split("\t"));
}

/** A spreadsheet-like grid: paste from Excel, edit, check, then import. */
export default function PasteTable({
  source,
  onClose,
  onComplete,
}: {
  source: ClientSource;
  onClose: () => void;
  onComplete: (result: ClientImport) => void;
}) {
  const t = useTranslations("dataSources");
  const [header, setHeader] = useState<string[]>(
    () => PASTE_COLUMNS[source.key] ?? []
  );
  const [rows, setRows] = useState<string[][]>(() =>
    Array.from({ length: START_ROWS }, () => emptyRow(header.length))
  );
  const [validation, setValidation] = useState<Validation | null>(null);
  const [checkedFor, setCheckedFor] = useState("");
  const [busy, setBusy] = useState<"check" | "import" | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  const filled = rows.filter((row) => row.some((cell) => cell.trim()));
  const payload = JSON.stringify([header, ...filled]);
  const current = validation !== null && checkedFor === payload;

  useEffect(() => {
    closeRef.current?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape" && !busy) onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, busy]);

  // Problems by grid cell: sheet row 1 is the titles, so data row = row - 2.
  const flagged = new Map<string, string>();
  const rowFlags = new Map<number, string>();
  for (const problem of current ? validation.problems : []) {
    if (problem.row_number === null) continue;
    const label = describe(problem);
    if (problem.column) {
      flagged.set(`${problem.row_number - 2}:${columnIndex(problem.column)}`, label);
    }
    rowFlags.set(problem.row_number - 2, label);
  }

  function describe(problem: Problem): string {
    if (problem.code === "TABLE_NOT_RECOGNIZED") return T.notRecognized;
    const key = Object.entries(IMPORT_DIAGNOSTIC_KEYS).find(
      ([code]) => code === problem.code
    )?.[1];
    return key ? t(`diagnostics.${key}`) : t("diagnostics.other");
  }

  function setCell(row: number, column: number, value: string) {
    setRows((old) =>
      old.map((cells, index) =>
        index === row
          ? cells.map((cell, position) => (position === column ? value : cell))
          : cells
      )
    );
  }

  function paste(row: number, column: number, text: string) {
    let block = parseClipboard(text);
    if (!block.length) return;
    // A pasted title row replaces the titles instead of becoming data.
    const first = block[0] ?? [];
    const known = new Set(header.map(normal));
    if (first.filter((cell) => known.has(normal(cell))).length >= 2) {
      setHeader(first.map((cell) => cell.trim()));
      block = block.slice(1);
      row = 0;
      column = 0;
    }
    setRows((old) => {
      const width = Math.max(header.length, column + Math.max(...block.map((line) => line.length)));
      const next = old.map((cells) => [...cells, ...emptyRow(width - cells.length)]);
      while (next.length < row + block.length + 1) next.push(emptyRow(width));
      block.forEach((line, offset) => {
        line.forEach((value, step) => {
          const target = next[row + offset];
          if (target) target[column + step] = value.trim();
        });
      });
      return next;
    });
    setHeader((old) => {
      const width = Math.max(old.length, column + Math.max(...block.map((line) => line.length)));
      return [...old, ...Array.from({ length: width - old.length }, (_, index) => letter(old.length + index))];
    });
  }

  async function send(dryRun: boolean) {
    setBusy(dryRun ? "check" : "import");
    setFailure(null);
    try {
      const answer = await postTonJson<Validation>(
        `/api/ton/data-sources/${source.key}/paste`,
        { rows: [header, ...filled], dry_run: dryRun }
      );
      setValidation(answer);
      setCheckedFor(payload);
      if (!dryRun && answer.result) onComplete(answer.result);
    } catch (error) {
      setFailure(
        error instanceof TonApiError && error.detail
          ? `${T.failed} ${error.detail}`
          : T.failed
      );
    } finally {
      setBusy(null);
    }
  }

  const errors = current
    ? validation.problems.filter((item) => item.level === "ERROR").length
    : 0;

  return (
    <>
      <div
        aria-hidden
        className="ton-scrim fixed inset-0 z-40"
        onClick={() => !busy && onClose()}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="ton-paste-title"
        className="ton-drawer fixed inset-y-0 end-0 z-50 flex flex-col w-full lg:w-[min(1180px,calc(100vw-4rem))]"
      >
        <header className="flex items-start justify-between gap-4 px-6 pt-5 pb-4 border-b border-01">
          <div className="flex flex-col gap-1 min-w-0">
            <span className="ton-eyebrow">{source.name}</span>
            <Text as="h2" id="ton-paste-title" font="heading-h2" color="text-05">
              {T.title}
            </Text>
            <Text font="secondary-body" color="text-03">
              {T.description}
            </Text>
          </div>
          <Button
            ref={closeRef}
            icon={SvgX}
            prominence="tertiary"
            aria-label={T.close}
            disabled={busy !== null}
            onClick={onClose}
          />
        </header>
        <div className="flex-1 min-h-0 flex flex-col gap-3 px-6 py-4">
          <div className="ton-paste-frame flex-1 min-h-0 overflow-auto">
          <table className="ton-paste-grid">
            <colgroup>
              <col className="ton-paste-index-col" />
              {header.map((title, column) => (
                <col key={column} style={{ width: widthOf(title) }} />
              ))}
              <col className="ton-paste-action-col" />
            </colgroup>
            <thead>
              <tr className="ton-paste-letters" aria-hidden>
                <th />
                {header.map((_, column) => (
                  <th key={column}>{letter(column)}</th>
                ))}
                <th />
              </tr>
              <tr className="ton-paste-titles">
                <th scope="col" className="ton-paste-index">
                  <span className="sr-only">{T.row}</span>
                </th>
                {header.map((title, column) => (
                  <th key={column} scope="col">
                    <input
                      className="ton-paste-cell is-title ton-focusable"
                      value={title}
                      aria-label={T.titleOf(letter(column))}
                      onChange={(event) =>
                        setHeader((old) =>
                          old.map((item, index) =>
                            index === column ? event.target.value : item
                          )
                        )
                      }
                    />
                  </th>
                ))}
                <th aria-hidden />
              </tr>
            </thead>
            <tbody>
              {rows.map((cells, row) => (
                <tr key={row} className={cn(rowFlags.has(row) && "is-flagged")}>
                  <th scope="row" className="ton-paste-index" title={rowFlags.get(row)}>
                    {row + 2}
                  </th>
                  {header.map((_, column) => {
                    const problem = flagged.get(`${row}:${column}`);
                    return (
                      <td key={column} className={cn(problem && "is-flagged")}>
                        <input
                          className="ton-paste-cell ton-focusable"
                          value={cells[column] ?? ""}
                          title={problem}
                          aria-label={T.cell(letter(column), row + 2)}
                          aria-invalid={problem ? true : undefined}
                          onChange={(event) => setCell(row, column, event.target.value)}
                          onPaste={(event) => {
                            const text = event.clipboardData.getData("text/plain");
                            if (!text.includes("\t") && !text.includes("\n")) return;
                            event.preventDefault();
                            paste(row, column, text);
                          }}
                        />
                      </td>
                    );
                  })}
                  <td className="ton-paste-action">
                    {cells.some((cell) => cell.trim()) && (
                      <button
                        type="button"
                        className="ton-focusable ton-icon-button"
                        aria-label={T.removeRow(row + 2)}
                        onClick={() =>
                          setRows((old) =>
                            old.length > 1
                              ? old.filter((_, index) => index !== row)
                              : old
                          )
                        }
                      >
                        <SvgTrash size={14} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
          <div className="flex items-center justify-between gap-3">
            <Button
              prominence="tertiary"
              icon={SvgPlus}
              onClick={() =>
                setRows((old) => [
                  ...old,
                  ...Array.from({ length: 10 }, () => emptyRow(header.length)),
                ])
              }
            >
              {T.addRows}
            </Button>
            <Text font="secondary-body" color="text-03">
              {T.filled(formatNumber(filled.length))}
            </Text>
          </div>
        </div>
        <footer className="flex flex-col gap-3 px-6 py-4 border-t border-01">
          {current && (
            <div
              role="status"
              className={cn(
                "ton-paste-result flex flex-col gap-1",
                errors ? "is-error" : "is-ok"
              )}
            >
              <Text font="secondary-action" color="inherit">
                {T.summary(formatNumber(validation.records), errors)}
              </Text>
              {validation.problems.length > 0 && (
                <ul className="flex flex-col gap-0.5 max-h-24 overflow-auto">
                  {validation.problems.map((problem, index) => (
                    <li key={index}>
                      <Text font="secondary-body" color="text-04">
                        {T.problemAt(problem.row_number, problem.column, describe(problem))}
                      </Text>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {failure && (
            <Text font="secondary-body" color="status-error-05">
              {failure}
            </Text>
          )}
          <div className="flex flex-wrap items-center gap-3">
            <span className="flex-1 min-w-[14rem]">
              <Text font="secondary-body" color="text-03">
                {T.evidence}
              </Text>
            </span>
            <Button prominence="tertiary" disabled={busy !== null} onClick={onClose}>
              {T.cancel}
            </Button>
            <Button
              prominence="secondary"
              disabled={busy !== null || filled.length === 0}
              onClick={() => void send(true)}
            >
              {busy === "check" ? T.checking : T.check}
            </Button>
            <Button
              disabled={busy !== null || !current || validation.records === 0}
              onClick={() => void send(false)}
            >
              {busy === "import"
                ? T.importing
                : T.import(formatNumber(current ? validation.records : 0))}
            </Button>
          </div>
        </footer>
      </aside>
    </>
  );
}
