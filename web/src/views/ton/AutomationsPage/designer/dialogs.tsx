"use client";

import { useState } from "react";
import { Button, InputSwitch, InputTextArea, InputTypeIn, Modal, Text } from "@opal/components";
import { SvgArrowUp, SvgPlayCircle, SvgPlus, SvgSettings, SvgSparkle, SvgTrash, SvgX } from "@opal/icons";
import {
  AUTOMATIONS_API,
  COPY,
  DESIGNER_COPY as D,
  KIND_LABELS,
  send,
  type AutomationKind,
  type CatalogView,
  type Definition,
  type DraftResult,
  type FlowNode,
  type JsonValue,
  type Params,
  type VariableDecl,
} from "@/lib/ton/automations";
import { asText } from "@/lib/ton/automationTree";
import { prettyName } from "@/views/ton/AutomationsPage/designer/dynamic";
import { ChipsInput, Field, Select } from "@/views/ton/AutomationsPage/designer/fields";

// ---------------------------------------------------------------------------
// Settings (side panel)
// ---------------------------------------------------------------------------

function slug(text: string): string {
  const base = text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 40);
  return /^[a-z]/.test(base) ? base : `valor_${base}`.slice(0, 40);
}

function renameIn(value: JsonValue, from: RegExp, to: string): JsonValue {
  if (typeof value === "string") return value.replace(from, to);
  if (Array.isArray(value)) return value.map((item) => renameIn(item, from, to));
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, renameIn(item, from, to)]));
  return value;
}

/** Rename a variable everywhere it is read or written. */
function renameVariable(definition: Definition, from: string, to: string): Definition {
  if (from === to) return definition;
  const pattern = new RegExp(`\\bvars\\.${from}\\b`, "g");
  const walk = (nodes: FlowNode[]): FlowNode[] =>
    nodes.map((node) => {
      let params = renameIn(node.params, pattern, `vars.${to}`) as Params;
      if (node.type.startsWith("variable.") && params.name === from) params = { ...params, name: to };
      return {
        ...node,
        params,
        then: node.then && walk(node.then),
        else: node.else && walk(node.else),
        default: node.default && walk(node.default),
        steps: node.steps && walk(node.steps),
        cases: node.cases?.map((item) => ({ ...item, steps: walk(item.steps) })),
        branches: node.branches?.map((branch) => ({ ...branch, steps: walk(branch.steps) })),
      };
    });
  return { ...definition, steps: walk(definition.steps) };
}

interface SettingsPanelProps {
  definition: Definition;
  catalog: CatalogView;
  kind: AutomationKind;
  description: string;
  onChange: (patch: { definition?: Definition; kind?: AutomationKind; description?: string }) => void;
  onClose: () => void;
}

export function SettingsPanel({ definition, catalog, kind, description, onChange, onClose }: SettingsPanelProps) {
  const variables = definition.variables;
  const kindInfo = catalog.kinds.find((item) => item.key === kind);
  function setVariable(index: number, patch: Partial<VariableDecl>) {
    const current = variables[index]!;
    let next: Definition = { ...definition, variables: variables.map((item, i) => (i === index ? { ...item, ...patch } : item)) };
    if (patch.name && patch.name !== current.name) next = renameVariable(next, current.name, patch.name);
    onChange({ definition: next });
  }
  function addVariable() {
    const taken = new Set(variables.map((item) => item.name));
    let index = variables.length + 1;
    while (taken.has(`valor_${index}`)) index += 1;
    onChange({ definition: { ...definition, variables: [...variables, { name: `valor_${index}`, description: `Valor ${index}`, type: "string", value: "" }] } });
  }
  const context = { definition, catalog, nodeId: "trigger" };
  return (
    <aside className="ton-auto-panel" aria-label={D.settings} data-group="trigger">
      <header className="ton-auto-panel-head">
        <span className="ton-auto-node-icon">
          <SvgSettings size={18} />
        </span>
        <Text font="main-ui-action" color="text-05">
          {D.settings}
        </Text>
        <span className="flex-1" />
        <Button size="sm" prominence="tertiary" icon={SvgX} aria-label={D.closePanel} onClick={onClose} />
      </header>
      <div className="ton-auto-panel-body ton-auto-sections">
        <section className="ton-auto-section">
          <Text as="h3" font="secondary-action" color="text-04">
            {D.settingsAbout}
          </Text>
          <Field label={D.kind} hint={kindInfo?.description}>
            <Select value={kind} label={D.kind} options={catalog.kinds.map((item): [string, string] => [item.key, item.label])} onChange={(value) => onChange({ kind: value as AutomationKind })} />
          </Field>
          <Field label={D.description}>
            <InputTextArea rows={2} autoResize maxRows={5} aria-label={D.description} placeholder={D.descriptionPlaceholder} value={description} onChange={(event) => onChange({ description: event.target.value })} />
          </Field>
        </section>
        <section className="ton-auto-section">
          <Text as="h3" font="secondary-action" color="text-04">
            {D.variables}
          </Text>
          <Text font="secondary-body" color="text-03">
            {D.variablesHint}
          </Text>
          {variables.map((variable, index) => (
            <div key={index} className="ton-auto-variable">
              <div className="ton-auto-variable-grid">
                <InputTypeIn
                  aria-label={D.variableName}
                  placeholder={D.variableName}
                  value={variable.description ?? prettyName(variable.name)}
                  onChange={(event) => {
                    const text = event.target.value;
                    const name = slug(text || variable.name);
                    const clash = variables.some((item, i) => i !== index && item.name === name);
                    setVariable(index, { description: text, name: clash ? variable.name : name });
                  }}
                />
                <Select value={variable.type} label={D.variableType} options={Object.entries(D.variableTypes)} onChange={(type) => setVariable(index, { type: type as VariableDecl["type"] })} />
              </div>
              <div className="ton-auto-variable-grid">
                <InputTypeIn aria-label={D.variableValue} placeholder={D.variableValue} value={asText(variable.value)} onChange={(event) => setVariable(index, { value: event.target.value })} />
                <Button size="sm" prominence="tertiary" icon={SvgTrash} aria-label={D.remove} tooltip={D.remove} onClick={() => onChange({ definition: { ...definition, variables: variables.filter((_, i) => i !== index) } })} />
              </div>
            </div>
          ))}
          <div>
            <Button size="sm" prominence="secondary" icon={SvgPlus} onClick={addVariable}>
              {D.addVariable}
            </Button>
          </div>
        </section>
        <section className="ton-auto-section">
          <Text as="h3" font="secondary-action" color="text-04">
            {D.settingsFailure}
          </Text>
          <Field label={D.notifyOnFailure}>
            <ChipsInput
              values={definition.settings.notify_on_failure}
              onChange={(values) => onChange({ definition: { ...definition, settings: { ...definition.settings, notify_on_failure: values } } })}
              label={D.notifyOnFailure}
              placeholder="nome@valenorte.com.br"
              context={context}
            />
          </Field>
          <Field label={D.timeoutHours}>
            <InputTypeIn
              type="number"
              min={1}
              max={720}
              aria-label={D.timeoutHours}
              value={String(definition.settings.timeout_hours)}
              onChange={(event) => onChange({ definition: { ...definition, settings: { ...definition.settings, timeout_hours: Number(event.target.value) || 168 } } })}
            />
          </Field>
        </section>
      </div>
    </aside>
  );
}

// ---------------------------------------------------------------------------
// Ask TON (side panel, chat-like)
// ---------------------------------------------------------------------------

interface AskEntry {
  request: string;
  result: DraftResult | null;
  error: string | null;
}

interface AskPanelProps {
  automationId: string;
  definition: Definition;
  onApplied: (result: DraftResult) => void;
  onClose: () => void;
}

export function AskPanel({ automationId, definition, onApplied, onClose }: AskPanelProps) {
  const [request, setRequest] = useState("");
  const [busy, setBusy] = useState(false);
  const [entries, setEntries] = useState<AskEntry[]>([]);
  async function submit(text: string) {
    const asked = text.trim();
    if (asked.length < 5 || busy) return;
    setBusy(true);
    setRequest("");
    setEntries((current) => [...current, { request: asked, result: null, error: null }]);
    let entry: AskEntry;
    try {
      const result = await send<DraftResult>(`${AUTOMATIONS_API}/drafts`, { request: asked, automation_id: automationId, definition });
      entry = { request: asked, result, error: null };
      onApplied(result);
    } catch (failure) {
      entry = { request: asked, result: null, error: failure instanceof Error ? failure.message : String(failure) };
    } finally {
      setBusy(false);
    }
    setEntries((current) => [...current.slice(0, -1), entry]);
  }
  return (
    <aside className="ton-auto-panel ton-auto-ask" aria-label={D.askTitle} data-group="ai">
      <header className="ton-auto-panel-head">
        <span className="ton-auto-node-icon">
          <SvgSparkle size={18} />
        </span>
        <Text font="main-ui-action" color="text-05">
          {D.askTitle}
        </Text>
        <span className="flex-1" />
        <Button size="sm" prominence="tertiary" icon={SvgX} aria-label={D.closePanel} onClick={onClose} />
      </header>
      <div className="ton-auto-panel-body">
        {entries.length === 0 ? (
          <div className="ton-auto-ask-empty">
            <Text font="secondary-body" color="text-03">
              {D.askIntro}
            </Text>
            <div className="ton-auto-ask-examples">
              {D.askExamples.map((example) => (
                <button key={example} type="button" className="ton-auto-ask-example ton-focusable" onClick={() => setRequest(example)}>
                  {example}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <ol className="ton-auto-ask-thread">
            {entries.map((entry, index) => (
              <li key={index} className="flex flex-col gap-2">
                <div className="ton-auto-ask-bubble" data-from="user">
                  {entry.request}
                </div>
                {entry.result ? (
                  <div className="ton-auto-ask-bubble" data-from="ton">
                    <strong>{D.askApplied}</strong>
                    {entry.result.summary && <span>{entry.result.summary}</span>}
                    {[...entry.result.missing, ...entry.result.problems].length > 0 && (
                      <span className="flex flex-col gap-0.5">
                        <span className="ton-auto-ask-missing">{D.askMissing}</span>
                        {[...entry.result.missing, ...entry.result.problems].slice(0, 6).map((item) => (
                          <span key={item}>{`• ${item}`}</span>
                        ))}
                      </span>
                    )}
                  </div>
                ) : entry.error ? (
                  <div className="ton-auto-ask-bubble" data-from="error">
                    {entry.error}
                  </div>
                ) : (
                  <div className="ton-auto-ask-bubble" data-from="ton" data-busy>
                    {D.asking}
                  </div>
                )}
              </li>
            ))}
          </ol>
        )}
      </div>
      <form
        className="ton-auto-ask-composer"
        onSubmit={(event) => {
          event.preventDefault();
          void submit(request);
        }}
      >
        <InputTextArea
          rows={2}
          autoResize
          maxRows={8}
          aria-label={D.askTitle}
          placeholder={D.askPlaceholder}
          value={request}
          onChange={(event) => setRequest(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void submit(request);
            }
          }}
        />
        <Button type="submit" icon={SvgArrowUp} disabled={busy || request.trim().length < 5} aria-label={D.askSubmit} tooltip={D.askSubmit} />
      </form>
    </aside>
  );
}

// ---------------------------------------------------------------------------
// Run / test
// ---------------------------------------------------------------------------

interface RunModalProps {
  open: boolean;
  test: boolean;
  definition: Definition;
  busy: boolean;
  error: string | null;
  onRun: (inputs: Record<string, JsonValue>) => void;
  onClose: () => void;
}

export function RunModal({ open, test, definition, busy, error, onRun, onClose }: RunModalProps) {
  const [values, setValues] = useState<Record<string, JsonValue>>({});
  const fields =
    definition.trigger.type === "trigger.manual" && Array.isArray(definition.trigger.params.inputs)
      ? definition.trigger.params.inputs.filter((field): field is Record<string, JsonValue> => !!field && typeof field === "object" && !Array.isArray(field))
      : [];
  return (
    <Modal open={open} onOpenChange={(value) => !value && onClose()}>
      <Modal.Content width="md">
        <Modal.Header icon={SvgPlayCircle} title={test ? COPY.testTitle : COPY.inputsTitle} description={test ? COPY.testHint : COPY.runHint} onClose={onClose} />
        <Modal.Body>
          <div className="flex flex-col gap-4">
            {fields.map((field) => {
              const name = asText(field.name);
              const label = asText(field.label) || name;
              const kind = asText(field.type) || "text";
              if (kind === "boolean") {
                return (
                  <Field key={name} label={label} required={field.required === true}>
                    <InputSwitch checked={values[name] === true} onCheckedChange={(checked) => setValues({ ...values, [name]: checked })} aria-label={label} />
                  </Field>
                );
              }
              if (kind === "longtext") {
                return (
                  <Field key={name} label={label} required={field.required === true}>
                    <InputTextArea rows={5} autoResize maxRows={16} aria-label={label} value={asText(values[name])} onChange={(event) => setValues({ ...values, [name]: event.target.value })} />
                  </Field>
                );
              }
              return (
                <Field key={name} label={label} required={field.required === true}>
                  <InputTypeIn
                    type={kind === "number" ? "number" : kind === "date" ? "date" : kind === "email" ? "email" : "text"}
                    aria-label={label}
                    value={asText(values[name])}
                    onChange={(event) => setValues({ ...values, [name]: event.target.value })}
                  />
                </Field>
              );
            })}
            {error && (
              <Text font="secondary-body" color="text-05">
                {error}
              </Text>
            )}
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button prominence="secondary" onClick={onClose}>
            {COPY.cancel}
          </Button>
          <Button icon={SvgPlayCircle} disabled={busy} onClick={() => onRun(values)}>
            {test ? COPY.test : COPY.run}
          </Button>
        </Modal.Footer>
      </Modal.Content>
    </Modal>
  );
}

