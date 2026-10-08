"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import { Button, Popover, Text } from "@opal/components";
import {
  SvgAlertCircle,
  SvgArrowLeft,
  SvgCheckCircle,
  SvgPauseCircle,
  SvgPlayCircle,
  SvgRefreshCw,
  SvgRevert,
  SvgSettings,
  SvgSparkle,
  SvgZap,
} from "@opal/icons";
import {
  AUTOMATIONS_API,
  COPY,
  DESIGNER_COPY as D,
  KIND_LABELS,
  STATUS_LABELS,
  send,
  useAutomation,
  useAutomationCatalog,
  type AutomationDetail,
  type AutomationKind,
  type Definition,
  type DraftResult,
  type FlowNode,
  type Issue,
  type JsonValue,
  type NodeTypeView,
  type RunSummary,
  type ValidateResult,
} from "@/lib/ton/automations";
import {
  allIds,
  duplicateNode,
  findNode,
  insertNode,
  moveNode,
  newNode,
  normalizeDefinition,
  removeNode,
  updateNode,
  type InsertTarget,
} from "@/lib/ton/automationTree";
import { ErrorState, LoadingBlock, StatusPill, type TonTone } from "@/views/ton/components/ui";
import AddPanel from "@/views/ton/AutomationsPage/designer/AddPanel";
import Canvas from "@/views/ton/AutomationsPage/designer/Canvas";
import ConfigPanel from "@/views/ton/AutomationsPage/designer/ConfigPanel";
import { AskPanel, RunModal, SettingsModal } from "@/views/ton/AutomationsPage/designer/dialogs";
import { specMap } from "@/views/ton/AutomationsPage/designer/dynamic";
import { nodeSummary } from "@/views/ton/AutomationsPage/designer/summary";

const STATUS_TONE: Record<string, TonTone> = { ACTIVE: "success", DRAFT: "neutral", PAUSED: "warning", ARCHIVED: "neutral" };
const HISTORY_LIMIT = 80;

interface Snapshot {
  definition: Definition;
  name: string;
  description: string;
  kind: AutomationKind;
}

interface History {
  past: Snapshot[];
  present: Snapshot;
  future: Snapshot[];
}

type Side = { kind: "config"; id: string } | { kind: "add"; mode: "action" | "trigger"; target: InsertTarget | null } | { kind: "ask" } | null;

function useDebounced<T>(value: T, delay: number): T {
  const [current, setCurrent] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setCurrent(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);
  return current;
}

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}

function Editor({ detail, onSaved, onRefresh }: { detail: AutomationDetail; onSaved: (detail: AutomationDetail) => void; onRefresh: () => void }) {
  const router = useRouter();
  const catalog = useAutomationCatalog();
  const specs = useMemo(() => (catalog.data ? specMap(catalog.data) : new Map<string, NodeTypeView>()), [catalog.data]);
  const initial: Snapshot = useMemo(
    () => ({ definition: normalizeDefinition(detail.definition), name: detail.name, description: detail.description ?? "", kind: detail.kind }),
    // Reset only when another automation or version loads.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [detail.id, detail.version]
  );
  const [history, setHistory] = useState<History>({ past: [], present: initial, future: [] });
  const state = history.present;
  const past = history.past;
  const future = history.future;
  const [saved, setSaved] = useState<Snapshot>(initial);
  const [side, setSide] = useState<Side>(initial.definition.steps.length ? null : { kind: "config", id: "trigger" });
  const [paletteDragging, setPaletteDragging] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [runModal, setRunModal] = useState<"test" | "run" | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [check, setCheck] = useState<ValidateResult | null>(null);
  const [focus, setFocus] = useState<{ id: string; nonce: number } | null>(null);

  useEffect(() => {
    setHistory({ past: [], present: initial, future: [] });
    setSaved(initial);
  }, [initial]);

  const dirty = JSON.stringify(state) !== JSON.stringify(saved);
  const commit = useCallback((next: Snapshot | ((current: Snapshot) => Snapshot)) => {
    setHistory((current) => {
      const value = typeof next === "function" ? next(current.present) : next;
      if (JSON.stringify(value) === JSON.stringify(current.present)) return current;
      return { past: [...current.past.slice(-HISTORY_LIMIT), current.present], present: value, future: [] };
    });
  }, []);
  const setDefinition = useCallback((fn: (definition: Definition) => Definition) => commit((current) => ({ ...current, definition: fn(current.definition) })), [commit]);

  function undo() {
    setHistory((current) => {
      const previous = current.past[current.past.length - 1];
      if (!previous) return current;
      return { past: current.past.slice(0, -1), present: previous, future: [current.present, ...current.future] };
    });
  }
  function redo() {
    setHistory((current) => {
      const next = current.future[0];
      if (!next) return current;
      return { past: [...current.past, current.present], present: next, future: current.future.slice(1) };
    });
  }

  // Live checker: the server rules, a moment after each change.
  const debounced = useDebounced(state, 450);
  useEffect(() => {
    let cancelled = false;
    send<ValidateResult>(`${AUTOMATIONS_API}/validate`, { definition: debounced.definition, kind: debounced.kind })
      .then((result) => !cancelled && setCheck(result))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [debounced]);

  const issues: Issue[] = useMemo(() => check?.issues ?? [], [check]);
  const issuesByNode = useMemo(() => {
    const map = new Map<string, { errors: number; warnings: number }>();
    for (const issue of issues) {
      const key = issue.node_id ?? "";
      if (!key) continue;
      const entry = map.get(key) ?? { errors: 0, warnings: 0 };
      if (issue.severity === "error") entry.errors += 1;
      else entry.warnings += 1;
      map.set(key, entry);
    }
    return map;
  }, [issues]);
  const errors = issues.filter((issue) => issue.severity === "error").length + (check?.structure_error ? 1 : 0);
  const warnings = issues.filter((issue) => issue.severity === "warning").length;
  const kindProblems = (check?.problems ?? []).filter((problem) => !issues.some((issue) => problem.endsWith(issue.message)));

  async function save(): Promise<AutomationDetail | null> {
    setBusy("save");
    setError(null);
    try {
      const result = await send<AutomationDetail>(
        `${AUTOMATIONS_API}/${detail.id}`,
        { name: state.name.trim() || detail.name, description: state.description || null, kind: state.kind, definition: state.definition },
        "PUT"
      );
      setSaved(state);
      onSaved(result);
      return result;
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : String(failure));
      return null;
    } finally {
      setBusy(null);
    }
  }

  async function setStatus(status: "ACTIVE" | "PAUSED") {
    if (dirty && !(await save())) return;
    setBusy("status");
    setError(null);
    try {
      onSaved(await send<AutomationDetail>(`${AUTOMATIONS_API}/${detail.id}/status`, { status }));
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : String(failure));
    } finally {
      setBusy(null);
    }
  }

  async function run(inputs: Record<string, JsonValue>) {
    const test = runModal === "test";
    if (dirty && !(await save())) return;
    setBusy("run");
    setError(null);
    try {
      const result = await send<RunSummary>(`${AUTOMATIONS_API}/${detail.id}/${test ? "test" : "run"}`, { inputs });
      setRunModal(null);
      router.push(`/ton/automacoes/${detail.id}/execucoes/${result.id}` as Route);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : String(failure));
    } finally {
      setBusy(null);
    }
  }

  function insertAt(target: InsertTarget, spec: NodeTypeView) {
    const node = newNode(spec, allIds(state.definition));
    setDefinition((definition) => insertNode(definition, target, node));
    setSide({ kind: "config", id: node.id });
    setFocus({ id: node.id, nonce: Date.now() });
  }

  function remove(id: string) {
    setDefinition((definition) => removeNode(definition, id));
    setSide(null);
  }

  // Keyboard: undo/redo, delete, save, escape.
  const keyHandler = useRef<(event: KeyboardEvent) => void>(() => undefined);
  const onKey = (event: KeyboardEvent) => {
    const mod = event.ctrlKey || event.metaKey;
    if (mod && event.key.toLowerCase() === "s") {
      event.preventDefault();
      void save();
      return;
    }
    if (isTyping(event.target)) return;
    if (mod && event.key.toLowerCase() === "z" && !event.shiftKey) {
      event.preventDefault();
      undo();
    } else if (mod && (event.key.toLowerCase() === "y" || (event.key.toLowerCase() === "z" && event.shiftKey))) {
      event.preventDefault();
      redo();
    } else if ((event.key === "Delete" || event.key === "Backspace") && side?.kind === "config" && side.id !== "trigger") {
      event.preventDefault();
      remove(side.id);
    } else if (event.key === "Escape") {
      setSide(null);
    }
  };
  useEffect(() => {
    keyHandler.current = onKey;
  });
  useEffect(() => {
    const listener = (event: KeyboardEvent) => keyHandler.current(event);
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, []);
  useEffect(() => {
    if (!dirty) return;
    const listener = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener("beforeunload", listener);
    return () => window.removeEventListener("beforeunload", listener);
  }, [dirty]);

  if (catalog.error) return <ErrorState onRetry={() => catalog.mutate()} />;
  if (!catalog.data) return <LoadingBlock label="…" />;
  const data = catalog.data;

  const summary = (id: string) =>
    id === "trigger"
      ? nodeSummary(null, specs.get(state.definition.trigger.type), state.definition, data)
      : nodeSummary(findNode(state.definition, id) ?? null, specs.get(findNode(state.definition, id)?.type ?? ""), state.definition, data);

  const selectedId = side?.kind === "config" ? side.id : null;
  const canActivate = detail.status !== "ACTIVE" && detail.status !== "ARCHIVED";

  return (
    <div className="ton-auto-designer">
      <header className="ton-auto-topbar">
        <Button size="sm" prominence="tertiary" icon={SvgArrowLeft} href={`/ton/automacoes/${detail.id}`} aria-label={D.back}>
          {D.back}
        </Button>
        <input
          className="ton-auto-name ton-focusable"
          aria-label={COPY.name}
          value={state.name}
          maxLength={120}
          onChange={(event) => commit((current) => ({ ...current, name: event.target.value }))}
        />
        <span className="ton-auto-kind-pill" title={D.kind}>
          {KIND_LABELS[state.kind]}
        </span>
        <StatusPill tone={STATUS_TONE[detail.status] ?? "neutral"}>{STATUS_LABELS[detail.status]}</StatusPill>
        <span className="flex-1" />
        <Text font="secondary-body" color="text-03">
          {busy === "save" ? D.saving : dirty ? D.unsaved : D.saved}
        </Text>
        <Button size="sm" prominence="tertiary" icon={SvgRevert} tooltip={D.undo} aria-label={D.undo} disabled={!past.length} onClick={undo} />
        <Button size="sm" prominence="tertiary" icon={SvgRefreshCw} tooltip={D.redo} aria-label={D.redo} disabled={!future.length} onClick={redo} />
        <Popover>
          <Popover.Trigger asChild>
            <Button size="sm" prominence="tertiary" icon={errors ? SvgAlertCircle : SvgCheckCircle} variant={errors ? "danger" : "default"}>
              {errors || warnings ? `${errors ? D.errors(errors) : ""}${errors && warnings ? " · " : ""}${warnings ? D.warnings(warnings) : ""}` : D.checker}
            </Button>
          </Popover.Trigger>
          <Popover.Content width="xl" align="end">
            <div className="ton-auto-checker">
              <Text font="main-ui-action" color="text-05">
                {D.checker}
              </Text>
              {check?.structure_error && (
                <div className="ton-auto-checker-item" data-severity="error">
                  <Text font="secondary-body" color="text-05">
                    {check.structure_error}
                  </Text>
                </div>
              )}
              {!issues.length && !kindProblems.length && !check?.structure_error && (
                <Text font="secondary-body" color="text-03">
                  {D.checkerOk}
                </Text>
              )}
              {issues.map((issue, index) => (
                <button
                  key={index}
                  type="button"
                  className="ton-auto-checker-item ton-focusable"
                  data-severity={issue.severity}
                  onClick={() => {
                    if (issue.node_id) {
                      setSide({ kind: "config", id: issue.node_id });
                      setFocus({ id: issue.node_id, nonce: Date.now() });
                    }
                  }}
                >
                  <span className="ton-auto-checker-node">{issue.node_id && issue.node_id !== "trigger" ? findNode(state.definition, issue.node_id)?.label || issue.node_id : D.trigger}</span>
                  <span>{issue.message}</span>
                </button>
              ))}
              {kindProblems.map((problem) => (
                <div key={problem} className="ton-auto-checker-item" data-severity="error">
                  <span>{problem}</span>
                </div>
              ))}
            </div>
          </Popover.Content>
        </Popover>
        <Button size="sm" prominence="tertiary" icon={SvgSettings} onClick={() => setSettingsOpen(true)}>
          {D.settings}
        </Button>
        <Button size="sm" prominence="tertiary" icon={SvgSparkle} onClick={() => setSide({ kind: "ask" })}>
          {D.ask}
        </Button>
        <Button size="sm" prominence="secondary" icon={SvgZap} disabled={busy !== null || errors > 0} onClick={() => setRunModal("test")} tooltip={errors ? D.errors(errors) : COPY.testHint}>
          {D.test}
        </Button>
        <Button size="sm" disabled={busy !== null || !dirty} onClick={() => void save()}>
          {busy === "save" ? D.saving : D.save}
        </Button>
        {canActivate ? (
          <Button size="sm" prominence="secondary" icon={SvgPlayCircle} disabled={busy !== null || errors > 0 || kindProblems.length > 0} onClick={() => void setStatus("ACTIVE")}>
            {COPY.activate}
          </Button>
        ) : detail.status === "ACTIVE" ? (
          <Button size="sm" prominence="secondary" icon={SvgPauseCircle} disabled={busy !== null} onClick={() => void setStatus("PAUSED")}>
            {COPY.pause}
          </Button>
        ) : null}
      </header>
      {error && (
        <div className="ton-auto-banner" data-tone="error">
          <Text font="secondary-body" color="text-05">
            {error}
          </Text>
        </div>
      )}
      <div className="ton-auto-workspace">
        {side?.kind === "add" && (
          <AddPanel
            catalog={data}
            mode={side.mode}
            onClose={() => setSide(null)}
            onDragState={setPaletteDragging}
            onPick={(spec) => {
              if (side.mode === "trigger") {
                const defaults: Record<string, JsonValue> = {};
                for (const param of spec.params) if (param.default !== null) defaults[param.key] = param.default;
                setDefinition((definition) => ({ ...definition, trigger: { type: spec.type, params: defaults } }));
                setSide({ kind: "config", id: "trigger" });
              } else {
                insertAt(side.target ?? { parentId: null, slot: "steps", index: state.definition.steps.length }, spec);
              }
            }}
          />
        )}
        <Canvas
          definition={state.definition}
          specs={specs}
          selectedId={selectedId}
          issues={issuesByNode}
          paletteDragging={paletteDragging}
          summary={summary}
          focus={focus}
          onSelect={(id) => setSide({ kind: "config", id })}
          onInsertAt={(target) => setSide({ kind: "add", mode: "action", target })}
          onDropNew={(target, type) => {
            setPaletteDragging(false);
            const spec = specs.get(type);
            if (spec) insertAt(target, spec);
          }}
          onMove={(id, target) => setDefinition((definition) => moveNode(definition, id, target))}
        />
        {side?.kind === "config" && (
          <ConfigPanel
            key={side.id}
            selectedId={side.id}
            definition={state.definition}
            catalog={data}
            specs={specs}
            issues={issues}
            automationId={detail.id}
            automationName={state.name}
            onChangeNode={(id, node: FlowNode) => setDefinition((definition) => updateNode(definition, id, () => node))}
            onChangeTrigger={(params) => setDefinition((definition) => ({ ...definition, trigger: { ...definition.trigger, params } }))}
            onChangeTriggerType={() => setSide({ kind: "add", mode: "trigger", target: null })}
            onDelete={remove}
            onDuplicate={(id) => {
              const result = duplicateNode(state.definition, id);
              commit((current) => ({ ...current, definition: result.definition }));
              if (result.id) setSide({ kind: "config", id: result.id });
            }}
            onClose={() => setSide(null)}
          />
        )}
        {side?.kind === "ask" && (
          <AskPanel
            automationId={detail.id}
            definition={state.definition}
            onClose={() => setSide(null)}
            onApplied={(result: DraftResult) => {
              if (!result.definition) return;
              // The draft is saved as a new version; reload it.
              onRefresh();
            }}
          />
        )}
      </div>
      <SettingsModal
        open={settingsOpen}
        definition={state.definition}
        catalog={data}
        kind={state.kind}
        description={state.description}
        onClose={() => setSettingsOpen(false)}
        onChange={(patch) =>
          commit((current) => ({
            ...current,
            definition: patch.definition ?? current.definition,
            kind: patch.kind ?? current.kind,
            description: patch.description ?? current.description,
          }))
        }
      />
      <RunModal
        open={runModal !== null}
        test={runModal === "test"}
        definition={state.definition}
        busy={busy !== null}
        error={error}
        onRun={(inputs) => void run(inputs)}
        onClose={() => setRunModal(null)}
      />
    </div>
  );
}

export default function DesignerPage({ automationId }: { automationId: string }) {
  const detail = useAutomation(automationId);
  if (detail.error) return <ErrorState onRetry={() => detail.mutate()} />;
  if (!detail.data) return <LoadingBlock label="…" />;
  return <Editor detail={detail.data} onSaved={(next) => void detail.mutate(next, { revalidate: false })} onRefresh={() => void detail.mutate()} />;
}
