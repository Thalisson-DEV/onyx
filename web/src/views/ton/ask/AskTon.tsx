"use client";

/*
 * "Perguntar ao TON": a side panel that opens from any screen with the
 * screen's context (and the row or figure clicked), asks the TON agent and
 * shows, live, what it is doing — reasoning, each tool it consults, then
 * the answer. The context goes as additional context of the message, so
 * the conversation stays clean and can continue in the Assistente.
 */

import Link from "next/link";
import type { Route } from "next";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { CompactMarkdown, Text } from "@opal/components";
import "@/views/ton/chat/chat.css";
import TonMark from "@/views/ton/chat/TonMark";
import { SvgArrowUp, SvgCheck, SvgChevronDown, SvgX } from "@opal/icons";
import { createChatSession, sendMessage } from "@/app/app/services/lib";
import { SEARCH_PARAM_NAMES } from "@/app/app/services/searchParams";
import { useTonAccess, useTonPersona } from "@/lib/ton/api";
import {
  contextText,
  formatSeconds,
  nextParentId,
  reduceTurn,
  type AskStep,
  type AskTonContext,
  type AskTurn,
  finishTurn,
} from "@/lib/ton/ask";
import { COPY } from "@/lib/ton/copy";
import { Diamond, Drawer } from "@/views/ton/components/kit";

interface AskTonApi {
  /** Opens the panel; without a context it uses the current screen's. */
  ask: (context?: AskTonContext) => void;
  /** Screens declare what they show so the header button has context. */
  setPageContext: (context: AskTonContext | null) => void;
}

/** Outside the TON shell (report viewer, tests) asking is simply unavailable. */
const NO_ASK: AskTonApi = {
  ask: () => undefined,
  setPageContext: () => undefined,
};

const AskTonContextValue = createContext<AskTonApi>(NO_ASK);

export function useAskTon(): AskTonApi {
  return useContext(AskTonContextValue);
}

/** Declares the context of the current screen while it is mounted. */
export function useAskTonPage(context: AskTonContext | null) {
  const { setPageContext } = useAskTon();
  const serialized = JSON.stringify(context);
  useEffect(() => {
    setPageContext(context);
    return () => setPageContext(null);
    // The serialized value keeps the effect from re-running every render.
  }, [serialized, setPageContext]);
}

function StepIcon({ state }: { state: AskStep["state"] }) {
  return (
    <span className="tn-st" data-state={state} aria-hidden>
      {state === "done" && <SvgCheck size={10} />}
      {state === "error" && <SvgX size={10} />}
    </span>
  );
}

interface StepDetailProps {
  text: string;
  reasoning: boolean;
}

/**
 * The model reasons in its own words (often English) and fast: showing that
 * stream live made the panel jump. The step title says what the TON is
 * doing; the raw reasoning stays one click away.
 */
function StepDetail({ text, reasoning }: StepDetailProps) {
  const [open, setOpen] = useState(false);
  if (!reasoning) return <span className="tn-step-detail">{text}</span>;
  return (
    <span className="tn-step-detail">
      <button
        type="button"
        className="tn-link ton-focusable"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        {open ? COPY.ask.lessReasoning : COPY.ask.moreReasoning}
      </button>
      {open && (
        <span className="tn-step-raw" data-kind="why">
          {text}
        </span>
      )}
    </span>
  );
}

function elapsed(step: AskStep, now: number): string {
  const ms = (step.endedAt ?? now) - step.startedAt;
  // A tool answered with its own announcement has no time worth showing.
  return step.state !== "run" && ms < 100 ? "" : formatSeconds(ms);
}

interface ThinkingProps {
  turn: AskTurn;
  now: number;
}

/** What the TON did before answering: live while it works, then folded. */
function Thinking({ turn, now }: ThinkingProps) {
  const running = turn.endedAt === null;
  const [open, setOpen] = useState(true);
  const done = !running;
  useEffect(() => {
    if (done && turn.answer) setOpen(false);
  }, [done, turn.answer]);
  const current = [...turn.steps]
    .reverse()
    .find((step) => step.state === "run");
  const work = turn.steps.filter((step) => step.kind !== "answer");
  if (turn.steps.length === 0 && !running) return null;
  return (
    <div className="tn-think">
      <button
        type="button"
        className="tn-think-head ton-focusable"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        {running ? (
          <>
            <StepIcon state="run" />
            <b>{current?.title ?? COPY.ask.thinking}</b>
            <span className="tn-typing" aria-hidden>
              <i />
              <i />
              <i />
            </span>
          </>
        ) : (
          <>
            <StepIcon state={turn.error ? "error" : "done"} />
            <b>
              {COPY.ask.thoughtFor(
                formatSeconds((turn.endedAt ?? now) - turn.startedAt),
                work.length
              )}
            </b>
          </>
        )}
        <SvgChevronDown size={12} className="tn-chev ms-auto" />
      </button>
      {open && turn.steps.length > 0 && (
        <ol className="tn-think-steps" aria-live="polite">
          {turn.steps.map((step) => (
            <li key={step.id} className="tn-step">
              <StepIcon state={step.state} />
              <span className="tn-step-title">{step.title}</span>
              <span className="tn-step-time">{elapsed(step, now)}</span>
              {step.detail && step.state !== "run" && (
                <StepDetail
                  text={step.detail.trim()}
                  reasoning={step.kind === "reasoning"}
                />
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

interface AskPanelProps {
  context: AskTonContext;
  onClose: () => void;
}

function AskPanel({ context, onClose }: AskPanelProps) {
  const persona = useTonPersona();
  const [turns, setTurns] = useState<AskTurn[]>([]);
  const [draft, setDraft] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const parentRef = useRef<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const busy = turns.some((turn) => turn.endedAt === null);

  useEffect(() => {
    if (!busy) return;
    const timer = window.setInterval(() => setNow(Date.now()), 500);
    return () => window.clearInterval(timer);
  }, [busy]);

  useEffect(() => () => abortRef.current?.abort(), []);

  // Follow the conversation only while the reader is at its end, and glide:
  // jumping on every streamed word made the panel flicker.
  const follow = useRef(true);
  const lastScroll = useRef(0);
  useEffect(() => {
    const body = endRef.current?.closest(".tn-drawer-body");
    if (!body) return;
    function onScroll() {
      if (!body) return;
      follow.current =
        body.scrollHeight - body.scrollTop - body.clientHeight < 80;
    }
    body.addEventListener("scroll", onScroll, { passive: true });
    return () => body.removeEventListener("scroll", onScroll);
  }, []);
  const turnCount = turns.length;
  useEffect(() => {
    follow.current = true;
  }, [turnCount]);
  useEffect(() => {
    const body = endRef.current?.closest(".tn-drawer-body");
    if (!body || !follow.current) return;
    const at = Date.now();
    const wait = Math.max(0, 350 - (at - lastScroll.current));
    const timer = window.setTimeout(() => {
      lastScroll.current = Date.now();
      body.scrollTo({ top: body.scrollHeight, behavior: "smooth" });
    }, wait);
    return () => window.clearTimeout(timer);
  }, [turns]);

  function update(id: string, change: (turn: AskTurn) => AskTurn) {
    setTurns((list) =>
      list.map((turn) => (turn.id === id ? change(turn) : turn))
    );
  }

  async function send(question: string) {
    const text = question.trim();
    if (!text || busy) return;
    const personaId = persona.data?.persona_id;
    const id = `${Date.now()}`;
    const startedAt = Date.now();
    setDraft("");
    setTurns((list) => [
      ...list,
      {
        id,
        question: text,
        answer: "",
        steps: [],
        startedAt,
        endedAt: null,
        error: null,
      },
    ]);
    if (!personaId) {
      update(id, (turn) => ({
        ...turn,
        error: COPY.ask.noPersona,
        endedAt: Date.now(),
      }));
      return;
    }
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const chatId =
        sessionId ??
        (await createChatSession(
          personaId,
          `${context.screen} · ${text}`.slice(0, 120),
          null
        ));
      setSessionId(chatId);
      const stream = sendMessage({
        message: text,
        chatSessionId: chatId,
        parentMessageId: parentRef.current,
        filters: null,
        signal: controller.signal,
        origin: "webapp",
        additionalContext: contextText(context),
      });
      for await (const packet of stream) {
        const parent = nextParentId(packet);
        if (parent !== null) parentRef.current = parent;
        const at = Date.now();
        update(id, (turn) => reduceTurn(turn, packet, at));
      }
      const at = Date.now();
      update(id, (turn) => finishTurn(turn, at));
    } catch {
      if (controller.signal.aborted) return;
      update(id, (turn) => ({
        ...turn,
        error: COPY.ask.failed,
        endedAt: Date.now(),
      }));
    }
  }

  const asked = new Set(turns.map((turn) => turn.question));
  const suggestions = (context.suggestions ?? []).filter(
    (item) => !asked.has(item)
  );
  const focus = context.chips[context.chips.length - 1];

  return (
    <Drawer
      open
      onClose={onClose}
      storageKey="ask"
      defaultWidth={460}
      eyebrow={COPY.ask.eyebrow}
      title={context.screen}
      leading={<TonMark size={36} working={busy} />}
      summary={
        <div className="flex flex-col gap-1.5 w-full">
          <span className="tn-stat-label flex items-center gap-1.5">
            <Diamond />
            {COPY.ask.seeing}
          </span>
          <div className="flex flex-wrap gap-1.5">
            {context.chips.map((chip, index) => (
              <span
                key={`${chip}-${index}`}
                className="tn-chip"
                data-focus={index === context.chips.length - 1}
              >
                {chip}
              </span>
            ))}
          </div>
        </div>
      }
      footer={
        <div className="flex flex-col gap-2 w-full">
          <div className="tn-composer">
            <textarea
              aria-label={COPY.ask.placeholder}
              placeholder={COPY.ask.placeholder}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void send(draft);
                }
              }}
            />
            <div className="flex items-center gap-2 px-2 pb-2">
              {focus && <span className="tn-ctx-chip">{focus}</span>}
              <button
                type="button"
                className="tn-send ton-focusable"
                aria-label={COPY.ask.send}
                disabled={busy || !draft.trim()}
                onClick={() => void send(draft)}
              >
                <SvgArrowUp size={16} />
              </button>
            </div>
          </div>
          <div className="flex items-center justify-between gap-2">
            <Text font="secondary-body" color="text-03">
              {COPY.ask.promise}
            </Text>
            {sessionId && (
              <Link
                className="tn-link ton-focusable shrink-0"
                href={
                  `/ton/chat?${SEARCH_PARAM_NAMES.CHAT_ID}=${sessionId}` as Route
                }
              >
                {COPY.ask.continueInAssistant}
              </Link>
            )}
          </div>
        </div>
      }
    >
      <div className="tn-msg-ton">
        <TonMark size={24} />
        <div className="tn-msg-ton-body">
          <span>{context.opener ?? COPY.ask.greeting(context.screen)}</span>
        </div>
      </div>
      {turns.map((turn) => (
        <div key={turn.id} className="flex flex-col gap-3">
          <div className="tn-msg-me">{turn.question}</div>
          <div className="tn-msg-ton">
            <span className="w-[22px] shrink-0" />
            <div className="tn-msg-ton-body">
              <Thinking turn={turn} now={now} />
              {turn.answer && (
                <CompactMarkdown className="tn-answer">
                  {turn.answer}
                </CompactMarkdown>
              )}
              {turn.error && (
                <Text as="p" font="secondary-body" color="text-03">
                  {turn.error}
                </Text>
              )}
            </div>
          </div>
        </div>
      ))}
      {!busy && suggestions.length > 0 && (
        <div className="flex flex-col items-start gap-1.5 ps-8">
          {suggestions.map((item) => (
            <button
              key={item}
              type="button"
              className="tn-reply ton-focusable"
              onClick={() => void send(item)}
            >
              {item}
            </button>
          ))}
        </div>
      )}
      <div ref={endRef} />
    </Drawer>
  );
}

interface AskTonProviderProps {
  children: ReactNode;
}

export function AskTonProvider({ children }: AskTonProviderProps) {
  const [open, setOpen] = useState<{
    key: number;
    context: AskTonContext;
  } | null>(null);
  const pageRef = useRef<AskTonContext | null>(null);

  const setPageContext = useCallback((context: AskTonContext | null) => {
    pageRef.current = context;
  }, []);

  const ask = useCallback((context?: AskTonContext) => {
    const chosen = context ?? pageRef.current;
    setOpen({
      key: Date.now(),
      context: chosen ?? { screen: COPY.ask.button, chips: [] },
    });
  }, []);

  const api = useMemo(() => ({ ask, setPageContext }), [ask, setPageContext]);

  return (
    <AskTonContextValue.Provider value={api}>
      {children}
      {open && (
        <AskPanel
          key={open.key}
          context={open.context}
          onClose={() => setOpen(null)}
        />
      )}
    </AskTonContextValue.Provider>
  );
}

/** The header entry point: asks about the screen as it is now. */
export function AskTonHeaderButton() {
  const { canRead } = useTonAccess();
  const { ask } = useAskTon();
  if (!canRead) return null;
  return (
    <button
      type="button"
      className="tn-ask-top ton-focusable"
      onClick={() => ask()}
    >
      <Diamond />
      <span className="hidden md:inline">{COPY.ask.button}</span>
    </button>
  );
}

interface AskTonRowButtonProps {
  label: string;
  context: AskTonContext;
}

/** Small "?" beside a row or figure: asks with that item in focus. */
export function AskTonRowButton({ label, context }: AskTonRowButtonProps) {
  const { ask } = useAskTon();
  return (
    <button
      type="button"
      className="tn-icon-btn tn-row-ask ton-focusable"
      aria-label={COPY.ask.rowButton(label)}
      onClick={(event) => {
        event.stopPropagation();
        ask(context);
      }}
    >
      <Diamond />
    </button>
  );
}
