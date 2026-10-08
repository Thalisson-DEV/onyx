"use client";

import { useState } from "react";
import { Button, InputSwitch, InputTextArea, InputTypeIn, Modal, Text } from "@opal/components";
import { SvgPlayCircle, SvgPlus, SvgSettings, SvgSparkle, SvgTrash, SvgX } from "@opal/icons";
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
  type JsonValue,
  type VariableDecl,
} from "@/lib/ton/automations";
import { asText } from "@/lib/ton/automationTree";
import { ChipsInput, Field, Select } from "@/views/ton/AutomationsPage/designer/fields";

// ---------------------------------------------------------------------------
// Variables and settings
// ---------------------------------------------------------------------------

interface SettingsModalProps {
  open: boolean;
  definition: Definition;
  catalog: CatalogView;
  kind: AutomationKind;
  description: string;
  onChange: (patch: { definition?: Definition; kind?: AutomationKind; description?: string }) => void;
  onClose: () => void;
}

export function SettingsModal({ open, definition, catalog, kind, description, onChange, onClose }: SettingsModalProps) {
  const variables = definition.variables;
  function setVariables(next: VariableDecl[]) {
    onChange({ definition: { ...definition, variables: next } });
  }
  const context = { definition, catalog, nodeId: "trigger" };
  return (
    <Modal open={open} onOpenChange={(value) => !value && onClose()}>
      <Modal.Content width="lg" height="lg">
        <Modal.Header icon={SvgSettings} title={D.settings} onClose={onClose} />
        <Modal.Body>
          <div className="flex flex-col gap-5">
            <Field label={D.kind}>
              <Select value={kind} label={D.kind} options={catalog.kinds.map((item): [string, string] => [item.key, `${item.label} — ${item.description}`])} onChange={(value) => onChange({ kind: value as AutomationKind })} />
            </Field>
            <Field label={D.description}>
              <InputTextArea rows={2} autoResize maxRows={5} aria-label={D.description} value={description} onChange={(event) => onChange({ description: event.target.value })} />
            </Field>
            <div className="flex flex-col gap-2">
              <Text font="main-ui-action" color="text-05">
                {D.variables}
              </Text>
              {variables.map((variable, index) => (
                <div key={index} className="ton-auto-row">
                  <div className="ton-auto-row-fields">
                    <div className="ton-auto-row-cell">
                      <InputTypeIn
                        aria-label={D.variableName}
                        placeholder={D.variableName}
                        value={variable.name}
                        onChange={(event) => setVariables(variables.map((item, i) => (i === index ? { ...item, name: event.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "_") } : item)))}
                      />
                    </div>
                    <div className="ton-auto-row-cell">
                      <Select
                        value={variable.type}
                        label={D.variableType}
                        options={Object.entries(D.variableTypes)}
                        onChange={(type) => setVariables(variables.map((item, i) => (i === index ? { ...item, type: type as VariableDecl["type"] } : item)))}
                      />
                    </div>
                    <div className="ton-auto-row-cell ton-auto-row-wide">
                      <InputTypeIn
                        aria-label={D.variableValue}
                        placeholder={D.variableValue}
                        value={asText(variable.value)}
                        onChange={(event) => setVariables(variables.map((item, i) => (i === index ? { ...item, value: event.target.value } : item)))}
                      />
                    </div>
                  </div>
                  <Button size="sm" prominence="tertiary" icon={SvgTrash} aria-label={D.remove} onClick={() => setVariables(variables.filter((_, i) => i !== index))} />
                </div>
              ))}
              <div>
                <Button size="sm" prominence="secondary" icon={SvgPlus} onClick={() => setVariables([...variables, { name: `variavel_${variables.length + 1}`, type: "string", value: "" }])}>
                  {D.addVariable}
                </Button>
              </div>
            </div>
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
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button onClick={onClose}>{D.done}</Button>
        </Modal.Footer>
      </Modal.Content>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Ask TON
// ---------------------------------------------------------------------------

interface AskPanelProps {
  automationId: string;
  definition: Definition;
  onApplied: (result: DraftResult) => void;
  onClose: () => void;
}

export function AskPanel({ automationId, definition, onApplied, onClose }: AskPanelProps) {
  const [request, setRequest] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<DraftResult | null>(null);
  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const result = await send<DraftResult>(`${AUTOMATIONS_API}/drafts`, { request, automation_id: automationId, definition });
      setDone(result);
      setRequest("");
      onApplied(result);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : String(failure));
    } finally {
      setBusy(false);
    }
  }
  return (
    <aside className="ton-auto-panel" aria-label={D.ask} data-group="ai">
      <header className="ton-auto-panel-head">
        <span className="ton-auto-node-icon">
          <SvgSparkle size={18} />
        </span>
        <div className="flex min-w-0 flex-1 flex-col">
          <Text font="main-ui-action" color="text-05">
            {D.ask}
          </Text>
          <Text font="secondary-body" color="text-03">
            {COPY.askTonHint}
          </Text>
        </div>
        <Button size="sm" prominence="tertiary" icon={SvgX} aria-label={D.closePanel} onClick={onClose} />
      </header>
      <div className="ton-auto-panel-body">
        <InputTextArea rows={6} autoResize maxRows={14} aria-label={D.ask} placeholder={D.askPlaceholder} value={request} onChange={(event) => setRequest(event.target.value)} />
        <div className="flex justify-end">
          <Button icon={SvgSparkle} disabled={busy || request.trim().length < 5} onClick={submit}>
            {busy ? D.asking : D.askSubmit}
          </Button>
        </div>
        {error && (
          <Text font="secondary-body" color="text-05">
            {error}
          </Text>
        )}
        {done && (
          <div className="ton-auto-ask-result">
            <Text font="secondary-action" color="text-05">
              {D.askApplied}
            </Text>
            {done.summary && (
              <Text font="secondary-body" color="text-04">
                {done.summary}
              </Text>
            )}
            {[...done.missing, ...done.problems].slice(0, 6).map((item) => (
              <Text key={item} font="secondary-body" color="text-03">
                {`• ${item}`}
              </Text>
            ))}
          </div>
        )}
      </div>
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

export function kindLabel(kind: AutomationKind): string {
  return KIND_LABELS[kind];
}
