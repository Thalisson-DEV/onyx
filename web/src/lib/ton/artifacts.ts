import { create } from "zustand";

/**
 * Artifacts the assistant builds in a conversation (dashboards, decks,
 * reports). The tool result is the whole spec, so a reloaded conversation
 * draws them again; every call with the same id is the next version.
 */

export type ArtifactKind = "painel" | "apresentacao" | "relatorio";
export type ArtifactFormat = "brl" | "percent" | "number";
export type ArtifactTone = "neutral" | "good" | "bad";

export interface ArtifactItem {
  label: string;
  value: number | null;
  display: string | null;
  note: string | null;
  tone: ArtifactTone;
}

export interface ArtifactSeries {
  name: string;
  points: { label: string; value: number }[];
}

export type ArtifactBlock =
  | { type: "kpis"; title: string | null; items: ArtifactItem[] }
  | {
      type: "barras";
      title: string | null;
      items: ArtifactItem[];
      format: ArtifactFormat;
    }
  | {
      type: "linha";
      title: string | null;
      series: ArtifactSeries[];
      format: ArtifactFormat;
    }
  | {
      type: "tabela";
      title: string | null;
      columns: string[];
      rows: (string | number)[][];
    }
  | { type: "texto"; title: string | null; body: string };

export interface ArtifactSlide {
  kicker: string | null;
  title: string;
  body: string | null;
  metric: { value: string; label: string } | null;
  block: ArtifactBlock | null;
}

export interface TonArtifact {
  kind: "ton_artifact";
  artifact_id: string;
  artifact_kind: ArtifactKind;
  title: string;
  subtitle: string | null;
  blocks: ArtifactBlock[];
  slides: ArtifactSlide[];
  sources: string[];
  created_at: string;
}

const KINDS: ArtifactKind[] = ["painel", "apresentacao", "relatorio"];

export function isArtifactKind(value: unknown): value is ArtifactKind {
  // SAFETY: includes() only compares; a non-kind value returns false.
  return KINDS.includes(value as ArtifactKind);
}

export function isTonArtifact(value: unknown): value is TonArtifact {
  if (typeof value !== "object" || value === null) return false;
  // SAFETY: an object; every field read below is checked before use.
  const item = value as Partial<TonArtifact>;
  return (
    item.kind === "ton_artifact" &&
    typeof item.artifact_id === "string" &&
    typeof item.title === "string" &&
    // SAFETY: includes() only compares; a non-kind value returns false.
    KINDS.includes(item.artifact_kind as ArtifactKind) &&
    Array.isArray(item.blocks) &&
    Array.isArray(item.slides)
  );
}

interface ArtifactState {
  /** Versions per artifact id, oldest first. */
  versions: Record<string, TonArtifact[]>;
  open: { id: string; createdAt: string } | null;
  /** Ids already opened once, so a reload does not reopen them. */
  seen: Record<string, true>;
  expanded: boolean;
  /** An artifact asked for by link: its latest version opens once it loads. */
  wanted: string | null;
  register: (artifact: TonArtifact) => void;
  show: (artifact: TonArtifact) => void;
  close: () => void;
  setExpanded: (expanded: boolean) => void;
  reset: (wanted?: string | null) => void;
}

export const useArtifactStore = create<ArtifactState>((set) => ({
  versions: {},
  open: null,
  seen: {},
  expanded: false,
  wanted: null,
  register: (artifact) =>
    set((state) => {
      const list = state.versions[artifact.artifact_id] ?? [];
      if (list.some((item) => item.created_at === artifact.created_at))
        return state;
      const next = [...list, artifact].sort((a, b) =>
        a.created_at.localeCompare(b.created_at)
      );
      const latest = next[next.length - 1]!;
      return {
        versions: { ...state.versions, [artifact.artifact_id]: next },
        ...(state.wanted === artifact.artifact_id && {
          open: { id: latest.artifact_id, createdAt: latest.created_at },
        }),
      };
    }),
  show: (artifact) =>
    set((state) => ({
      open: { id: artifact.artifact_id, createdAt: artifact.created_at },
      seen: { ...state.seen, [artifact.created_at]: true },
      wanted: null,
    })),
  close: () => set({ open: null, expanded: false, wanted: null }),
  setExpanded: (expanded) => set({ expanded }),
  reset: (wanted = null) =>
    set({ versions: {}, open: null, seen: {}, expanded: false, wanted }),
}));

/** The 1-based version of ``artifact`` among the ones seen in the session. */
export function artifactVersion(
  versions: Record<string, TonArtifact[]>,
  artifact: TonArtifact
): number {
  const list = versions[artifact.artifact_id] ?? [];
  const index = list.findIndex(
    (item) => item.created_at === artifact.created_at
  );
  return index < 0 ? 1 : index + 1;
}

const BRL = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const COMPACT = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const NUMBER = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

/** Short money for axes and bars: R$ 10,76 mi, R$ 412 mil. */
export function formatArtifactValue(
  value: number,
  format: ArtifactFormat
): string {
  if (format === "percent") return `${NUMBER.format(value)}%`;
  if (format === "number") return NUMBER.format(value);
  const abs = Math.abs(value);
  // The sign leads, as in "−R$ 25 mi".
  const sign = value < 0 ? "−" : "";
  if (abs >= 1_000_000)
    return `${sign}R$ ${COMPACT.format(abs / 1_000_000)} mi`;
  if (abs >= 10_000) return `${sign}R$ ${NUMBER.format(abs / 1_000)} mil`;
  return `${sign}R$ ${BRL.format(abs)}`;
}

/** The exact figure for the data tab and CSV: R$ 10.758.398,69. */
export function formatExactValue(
  value: number,
  format: ArtifactFormat
): string {
  if (format === "percent") return `${NUMBER.format(value)}%`;
  if (format === "number") return value.toLocaleString("pt-BR");
  return `${value < 0 ? "−" : ""}R$ ${BRL.format(Math.abs(value))}`;
}

/** KPIs carry no format; the short text the TON wrote tells it. */
function formatOf(item: ArtifactItem): ArtifactFormat {
  const display = item.display ?? "";
  if (display.includes("%")) return "percent";
  if (display.includes("R$")) return "brl";
  return "number";
}

/** A cell that reads as a number aligns right. */
export function isNumericCell(cell: string | number): boolean {
  if (typeof cell === "number") return true;
  return /^[(−\-+]?\s*(R\$\s*)?[(−\-+]?\s*[\d.]+(,\d+)?\)?\s*(%|mi|mil)?$/.test(
    cell.trim()
  );
}

/** "−R$ 1.234,56" → "-1234,56": a number Excel sums, not text. */
const EXACT_MONEY = /^([−-])?\s*R\$\s*([\d.]+,\d{2})$/;

function csvCell(cell: string | number): string {
  const money = typeof cell === "string" ? EXACT_MONEY.exec(cell.trim()) : null;
  const text =
    typeof cell === "number"
      ? BRL.format(cell).replace(/\./g, "")
      : money
        ? `${money[1] ? "-" : ""}${money[2]!.replace(/\./g, "")}`
        : cell;
  return /[;"\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

/** Semicolon CSV with a BOM: Excel in pt-BR opens it with the right columns. */
export function toCsv(columns: string[], rows: (string | number)[][]): string {
  return (
    "﻿" +
    [columns, ...rows].map((row) => row.map(csvCell).join(";")).join("\r\n")
  );
}

export function downloadText(
  filename: string,
  text: string,
  type = "text/csv"
): void {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function slugify(text: string): string {
  return (
    text
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 60) || "artefato"
  );
}

/** Every table the artifact shows, for "Dados e fontes" and the CSV. */
export function artifactTables(
  artifact: TonArtifact
): { title: string; columns: string[]; rows: (string | number)[][] }[] {
  const blocks = [
    ...artifact.blocks,
    ...artifact.slides.flatMap((slide) => (slide.block ? [slide.block] : [])),
  ];
  return blocks.flatMap((block, index) => {
    const title = block.title ?? `${artifact.title} · ${index + 1}`;
    if (block.type === "tabela")
      return [{ title, columns: block.columns, rows: block.rows }];
    if (block.type === "barras" || block.type === "kpis")
      return [
        {
          title,
          columns: ["Item", "Valor", "Observação"],
          rows: block.items.map((item) => [
            item.label,
            item.value === null
              ? (item.display ?? "")
              : formatExactValue(
                  item.value,
                  block.type === "barras" ? block.format : formatOf(item)
                ),
            item.note ?? "",
          ]),
        },
      ];
    if (block.type === "linha") {
      const labels = block.series[0]?.points.map((point) => point.label) ?? [];
      return [
        {
          title,
          columns: ["", ...block.series.map((serie) => serie.name)],
          rows: labels.map((label, row) => [
            label,
            ...block.series.map((serie) => {
              const value = serie.points[row]?.value;
              return value === undefined
                ? ""
                : formatExactValue(value, block.format);
            }),
          ]),
        },
      ];
    }
    return [];
  });
}

/**
 * "Criar" marks only what the answer must become; the person writes the ask.
 * The mark travels at the head of the message, where the TON reads it as the
 * final result and the conversation draws it as a chip.
 */
const CREATE_MARK = /^\[\[ton:(painel|apresentacao|relatorio)\]\]\s*/;

export function markCreate(kind: ArtifactKind, text: string): string {
  return `[[ton:${kind}]] ${text}`;
}

export function splitCreateMark(message: string): {
  kind: ArtifactKind | null;
  text: string;
} {
  const match = CREATE_MARK.exec(message);
  if (!match) return { kind: null, text: message };
  // SAFETY: the pattern only captures the three kinds.
  return {
    kind: match[1] as ArtifactKind,
    text: message.slice(match[0].length),
  };
}

interface CreateModeState {
  kind: ArtifactKind | null;
  setKind: (kind: ArtifactKind | null) => void;
}

/** The result the next message asks for, chosen in "Criar". */
export const useCreateMode = create<CreateModeState>((set) => ({
  kind: null,
  setKind: (kind) => set({ kind }),
}));

/** Ask the composer to hold ``text`` for the person to finish and send. */
export const TON_COMPOSE_EVENT = "ton:compose";

export function composeTonMessage(text: string): void {
  window.dispatchEvent(
    new CustomEvent(TON_COMPOSE_EVENT, { detail: { text } })
  );
}

/** Put the cursor in the composer and keep whatever draft is there. */
export function focusTonComposer(): void {
  window.dispatchEvent(
    new CustomEvent(TON_COMPOSE_EVENT, { detail: { focus: true } })
  );
}
