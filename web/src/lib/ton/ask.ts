import type { PacketType } from "@/app/app/services/lib";
import { COPY } from "@/lib/ton/copy";
import { TON_TOOL_NAMES } from "@/lib/ton/labels";

/** What the screen tells the TON when the user asks from it. */
export interface AskTonContext {
  /** Screen name, e.g. "Agenda de pagamentos". */
  screen: string;
  /** Context crumbs shown to the user; the last one is what was clicked. */
  chips: string[];
  /** Facts for the model, one per line (filters, the row, the figures). */
  details?: string[];
  /** The TON's first line, with an opinion when the screen has one. */
  opener?: string;
  /** Ready questions offered under the opener. */
  suggestions?: readonly string[];
}

export type AskStepState = "run" | "done" | "error";

export interface AskStep {
  id: string;
  title: string;
  detail: string;
  kind: "reasoning" | "tool" | "answer";
  state: AskStepState;
  startedAt: number;
  endedAt: number | null;
}

export interface AskTurn {
  id: string;
  question: string;
  answer: string;
  steps: AskStep[];
  startedAt: number;
  endedAt: number | null;
  error: string | null;
}

/** The context block injected beside the question, not stored in chat. */
export function contextText(context: AskTonContext): string {
  return [
    COPY.ask.contextIntro,
    `Tela: ${context.screen}`,
    `Onde clicou: ${context.chips.join(" › ")}`,
    ...(context.details ?? []),
  ].join("\n");
}

const GENERIC_TOOLS: Record<string, string> = {
  search_tool_start: "documentos",
  python_tool_start: "uma planilha de cálculo",
  open_url_start: "um endereço",
  file_reader_start: "um arquivo",
  memory_tool_start: "a memória do TON",
};

function toolLabel(name: string): string {
  return TON_TOOL_NAMES[name] ?? name.replace(/^ton_/, "").replace(/_/g, " ");
}

const RUNNING_PREFIX = COPY.ask.stepTool("");
const DONE_PREFIX = COPY.ask.stepToolDone("");

function closeRunning(steps: AskStep[], now: number): AskStep[] {
  return steps.map((step) =>
    step.state === "run"
      ? {
          ...step,
          // A tool closed by the next step finished too: say it in the past.
          title:
            step.kind === "tool" && step.title.startsWith(RUNNING_PREFIX)
              ? DONE_PREFIX + step.title.slice(RUNNING_PREFIX.length)
              : step.title,
          state: "done",
          endedAt: now,
        }
      : step
  );
}

/** Folds one stream packet into the turn; returns the turn unchanged if irrelevant. */
export function reduceTurn(
  turn: AskTurn,
  packet: PacketType,
  now: number
): AskTurn {
  if ("error" in packet && typeof packet.error === "string") {
    return {
      ...turn,
      steps: closeRunning(turn.steps, now),
      error: packet.error || COPY.ask.failed,
      endedAt: now,
    };
  }
  if (!("obj" in packet)) return turn;
  const obj = packet.obj;
  const key = `${packet.placement.turn_index}-${packet.placement.tab_index ?? 0}`;
  switch (obj.type) {
    case "reasoning_start":
      return {
        ...turn,
        steps: [
          ...closeRunning(turn.steps, now),
          {
            id: `r-${key}-${turn.steps.length}`,
            title: COPY.ask.stepReasoning,
            detail: "",
            kind: "reasoning",
            state: "run",
            startedAt: now,
            endedAt: null,
          },
        ],
      };
    case "reasoning_delta": {
      const last = turn.steps[turn.steps.length - 1];
      if (!last || last.kind !== "reasoning") return turn;
      return {
        ...turn,
        steps: [
          ...turn.steps.slice(0, -1),
          { ...last, detail: last.detail + obj.reasoning },
        ],
      };
    }
    case "reasoning_done":
      return { ...turn, steps: closeRunning(turn.steps, now) };
    case "custom_tool_start": {
      // The backend can announce the same call twice; keep one line.
      const title = COPY.ask.stepTool(toolLabel(obj.tool_name));
      const last = turn.steps[turn.steps.length - 1];
      if (
        last &&
        last.kind === "tool" &&
        last.title === title &&
        now - last.startedAt < 1500
      )
        return turn;
      return {
        ...turn,
        steps: [
          ...closeRunning(turn.steps, now),
          {
            id: `t-${key}-${turn.steps.length}`,
            title,
            detail: "",
            kind: "tool",
            state: "run",
            startedAt: now,
            endedAt: null,
          },
        ],
      };
    }
    case "custom_tool_delta": {
      const index = turn.steps.findLastIndex(
        (step) => step.kind === "tool" && step.state === "run"
      );
      if (index < 0) return turn;
      const step = turn.steps[index];
      if (!step) return turn;
      const failed = !!obj.error;
      const steps = [...turn.steps];
      steps[index] = {
        ...step,
        title: COPY.ask.stepToolDone(toolLabel(obj.tool_name)),
        detail: failed ? (obj.error?.message ?? "") : step.detail,
        state: failed ? "error" : "done",
        endedAt: now,
      };
      return { ...turn, steps };
    }
    case "search_tool_start":
    case "python_tool_start":
    case "open_url_start":
    case "file_reader_start":
    case "memory_tool_start":
      return {
        ...turn,
        steps: [
          ...closeRunning(turn.steps, now),
          {
            id: `g-${key}-${turn.steps.length}`,
            title: COPY.ask.stepTool(GENERIC_TOOLS[obj.type] ?? obj.type),
            detail: "",
            kind: "tool",
            state: "run",
            startedAt: now,
            endedAt: null,
          },
        ],
      };
    case "message_start":
      return {
        ...turn,
        steps: [
          ...closeRunning(turn.steps, now),
          {
            id: `a-${key}`,
            title: COPY.ask.stepAnswer,
            detail: "",
            kind: "answer",
            state: "run",
            startedAt: now,
            endedAt: null,
          },
        ],
      };
    case "message_delta":
      return { ...turn, answer: turn.answer + obj.content };
    case "error":
      return {
        ...turn,
        steps: closeRunning(turn.steps, now),
        error: obj.message || COPY.ask.failed,
        endedAt: now,
      };
    case "stop":
      return { ...turn, steps: closeRunning(turn.steps, now), endedAt: now };
    default:
      return turn;
  }
}

/** The assistant message id the next question must hang from. */
export function nextParentId(packet: PacketType): number | null {
  if ("reserved_assistant_message_id" in packet) {
    return packet.reserved_assistant_message_id;
  }
  return null;
}

export function formatSeconds(ms: number): string {
  return `${(ms / 1000).toLocaleString("pt-BR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })} s`;
}

/** Closes a turn whose stream ended without an explicit stop. */
export function finishTurn(turn: AskTurn, now: number): AskTurn {
  if (turn.endedAt !== null) return turn;
  return { ...turn, steps: closeRunning(turn.steps, now), endedAt: now };
}
