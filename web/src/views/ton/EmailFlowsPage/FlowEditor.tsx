"use client";

import "@xyflow/react/dist/style.css";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import {
  Background,
  BackgroundVariant,
  BaseEdge,
  Controls,
  EdgeLabelRenderer,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
  getSmoothStepPath,
  useReactFlow,
  type EdgeProps,
  type NodeProps,
} from "@xyflow/react";
import {
  Button,
  InputSingleSelect,
  InputTextArea,
  InputTypeIn,
  Modal,
  Text,
} from "@opal/components";
import {
  SvgArrowLeft,
  SvgBranch,
  SvgCalendar,
  SvgCheckCircle,
  SvgChevronDown,
  SvgChevronUp,
  SvgClock,
  SvgEye,
  SvgFilter,
  SvgMail,
  SvgPauseCircle,
  SvgPlayCircle,
  SvgPlus,
  SvgSparkle,
  SvgTrash,
  SvgUsers,
  SvgX,
  SvgZap,
} from "@opal/icons";
import type { IconFunctionComponent } from "@opal/types";
import { formatDateTime } from "@/lib/ton/copy";
import {
  EMAIL_FLOWS_API,
  EMAIL_FLOWS_COPY as COPY,
  WEEKDAYS,
  blankStep,
  insertStep,
  insideForEach,
  moveStep,
  newDefinition,
  parseAddresses,
  removeStep,
  replaceStep,
  sendJson,
  useFlowCatalog,
  useFlowDetail,
  type ApprovalStep,
  type AssetView,
  type CatalogView,
  type ConditionClause,
  type ConditionStep,
  type FlowDefinition,
  type FlowDetail,
  type FlowStatus,
  type ForEachUnitStep,
  type ItemState,
  type PreviewView,
  type RunView,
  type SendEmailStep,
  type Step,
  type StepType,
  type TriggerKind,
  type WaitStep,
} from "@/lib/ton/emailFlows";
import { ErrorState, LoadingBlock, StatusPill, type TonTone } from "@/views/ton/components/ui";
import EmailComposer from "@/views/ton/EmailFlowsPage/EmailComposer";
import {
  NODE_WIDTH,
  buildGraph,
  type FlowNode,
  type InsertEdgeData,
  type InsertTarget,
  type StepAddress,
} from "@/views/ton/EmailFlowsPage/graph";

const E = COPY.editor;

const TRIGGER_ICONS = {
  SCHEDULE: SvgCalendar,
  NG_IMPORT_COMPLETED: SvgZap,
  NG_OCCURRENCE_CHANGED: SvgBranch,
  ACCOUNT_UNCLASSIFIED: SvgFilter,
  DRE_RECALCULATED: SvgSparkle,
} satisfies Record<TriggerKind, IconFunctionComponent>;

const STEP_ICONS = {
  send_email: SvgMail,
  condition: SvgFilter,
  for_each_unit: SvgUsers,
  wait: SvgClock,
  approval: SvgCheckCircle,
} satisfies Record<StepType, IconFunctionComponent>;

const STEP_TONES = {
  send_email: "email",
  condition: "condition",
  for_each_unit: "loop",
  wait: "wait",
  approval: "approval",
} satisfies Record<StepType, string>;

const STATUS_TONE = {
  SUGGESTED: "brand",
  ACTIVE: "success",
  PAUSED: "neutral",
  DISCARDED: "neutral",
} satisfies Record<FlowStatus, TonTone>;

const STEP_ORDER: StepType[] = ["send_email", "condition", "for_each_unit", "wait", "approval"];

// ---------------------------------------------------------------------------
// Sentences
// ---------------------------------------------------------------------------

function triggerText(definition: FlowDefinition, catalog: CatalogView): string {
  const trigger = definition.trigger;
  if (trigger.kind === "SCHEDULE") {
    return trigger.frequency === "WEEKLY"
      ? `Toda ${WEEKDAYS[trigger.weekday ?? 0]} às ${trigger.time ?? "--:--"}`
      : `Todo dia às ${trigger.time ?? "--:--"}`;
  }
  if (trigger.kind === "NG_OCCURRENCE_CHANGED") {
    const labels = Object.fromEntries(catalog.changes);
    return `Inconsistência ${trigger.changes.map((change) => labels[change]).join(", ") || "…"}`;
  }
  return catalog.triggers.find((item) => item.kind === trigger.kind)?.label ?? "";
}

function clauseText(clause: ConditionClause, definition: FlowDefinition, catalog: CatalogView): string {
  const spec = catalog.triggers.find((item) => item.kind === definition.trigger.kind);
  const field = spec?.fields.find((item) => item.key === clause.field);
  if (!field) return clause.field;
  const choices = Object.fromEntries(field.choices);
  const values = Array.isArray(clause.value) ? clause.value : [clause.value];
  const text = values
    .map((value) =>
      field.type === "MONEY"
        ? Number(value).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
        : choices[String(value)] ?? String(value)
    )
    .join(", ");
  return `${field.label} ${catalog.operators[clause.operator]} ${text}`;
}

function recipients(addresses: string[]): string {
  if (!addresses.length) return E.noRecipients;
  const shown = addresses.map((address) => (address === "{email_unidade}" ? "e-mail da unidade" : address));
  return shown.length === 1 ? `${E.to}: ${shown[0]}` : `${E.to}: ${shown.length} destinatários`;
}

function stepSummary(step: Step, definition: FlowDefinition, catalog: CatalogView): { title: string; detail?: string } {
  switch (step.type) {
    case "send_email":
      return { title: step.subject || "Sem assunto", detail: recipients(step.to) };
    case "condition": {
      const texts = step.conditions.map((clause) => clauseText(clause, definition, catalog));
      return { title: texts[0] ?? E.always, detail: texts.length > 1 ? texts.slice(1).map((t) => `e ${t}`).join(" · ") : undefined };
    }
    case "for_each_unit":
      return {
        title: "Um caminho por unidade",
        detail: step.recipients.length ? `${step.recipients.length} unidades com e-mail cadastrado` : "E-mails por unidade a cadastrar",
      };
    case "wait":
      return {
        title:
          step.mode === "duration"
            ? `${step.days ? `${step.days} dia(s) ` : ""}${step.hours ? `${step.hours} h` : ""}`.trim()
            : `Até ${WEEKDAYS[step.weekday ?? 0]} às ${step.time ?? "--:--"}`,
        detail: "Depois segue só com o que continua aberto",
      };
    case "approval":
      return { title: step.approvers.join(", ") || "Quem aprova?", detail: "O fluxo para até alguém decidir" };
  }
}

// ---------------------------------------------------------------------------
// Canvas pieces
// ---------------------------------------------------------------------------

interface CanvasActions {
  definition: FlowDefinition;
  catalog: CatalogView;
  selected: StepAddress | "trigger" | null;
  menu: InsertTarget | null;
  select: (target: StepAddress | "trigger") => void;
  openMenu: (target: InsertTarget | null) => void;
  insert: (target: InsertTarget, type: StepType) => void;
}

const CanvasContext = createContext<CanvasActions | null>(null);

function useCanvas(): CanvasActions {
  const value = useContext(CanvasContext);
  if (!value) throw new Error("CanvasContext missing");
  return value;
}

function sameAddress(a: StepAddress | "trigger" | null, b: StepAddress): boolean {
  return a !== null && a !== "trigger" && a.index === b.index && a.path.join(".") === b.path.join(".");
}

function NodeCard({
  tone,
  icon,
  label,
  title,
  detail,
  selected,
  onClick,
}: {
  tone: string;
  icon: IconFunctionComponent;
  label: string;
  title: string;
  detail?: string;
  selected: boolean;
  onClick: () => void;
}) {
  const Icon = icon;
  return (
    <div
      role="button"
      tabIndex={0}
      className="ton-flow-node ton-focusable"
      data-tone={tone}
      data-selected={selected || undefined}
      style={{ width: NODE_WIDTH }}
      onClick={onClick}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") onClick();
      }}
    >
      <Handle type="target" position={Position.Top} className="ton-flow-handle" isConnectable={false} />
      <span className="ton-flow-node-icon" aria-hidden>
        <Icon size={18} />
      </span>
      <span className="flex min-w-0 flex-col items-start gap-0.5 text-start">
        <span className="ton-flow-node-label">{label}</span>
        <span className="ton-flow-node-title">{title}</span>
        {detail && <span className="ton-flow-node-detail">{detail}</span>}
      </span>
      <Handle type="source" position={Position.Bottom} className="ton-flow-handle" isConnectable={false} />
    </div>
  );
}

function TriggerNode() {
  const { definition, catalog, selected, select } = useCanvas();
  return (
    <NodeCard
      tone="trigger"
      icon={TRIGGER_ICONS[definition.trigger.kind]}
      label={E.when}
      title={triggerText(definition, catalog)}
      detail={definition.variables.length ? `${definition.variables.length} variável(is) do fluxo` : undefined}
      selected={selected === "trigger"}
      onClick={() => select("trigger")}
    />
  );
}

function StepNode({ data }: NodeProps<FlowNode>) {
  const { definition, catalog, selected, select } = useCanvas();
  if (data.kind !== "step") return null;
  const step = data.step;
  const summary = stepSummary(step, definition, catalog);
  return (
    <NodeCard
      tone={STEP_TONES[step.type]}
      icon={STEP_ICONS[step.type]}
      label={COPY.steps[step.type]}
      title={summary.title}
      detail={summary.detail}
      selected={sameAddress(selected, data.address)}
      onClick={() => select(data.address)}
    />
  );
}

function MergeNode() {
  return (
    <div className="ton-flow-merge">
      <Handle type="target" position={Position.Top} className="ton-flow-handle" isConnectable={false} />
      <Handle type="source" position={Position.Bottom} className="ton-flow-handle" isConnectable={false} />
    </div>
  );
}

function EndNode() {
  return (
    <div className="ton-flow-end">
      <Handle type="target" position={Position.Top} className="ton-flow-handle" isConnectable={false} />
      <Text font="secondary-action" color="text-03">
        {E.end}
      </Text>
    </div>
  );
}

function InsertEdge({ id, sourceX, sourceY, targetX, targetY, data }: EdgeProps & { data?: InsertEdgeData }) {
  const { menu, openMenu, insert, definition } = useCanvas();
  const [path, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition: Position.Bottom,
    targetPosition: Position.Top,
    borderRadius: 12,
  });
  if (!data) return <BaseEdge id={id} path={path} />;
  const target = data.target;
  const open = menu !== null && menu.index === target.index && menu.path.join(".") === target.path.join(".");
  const loop = insideForEach(definition, target.path);
  const types = STEP_ORDER.filter((type) => !(loop && (type === "for_each_unit" || type === "wait" || type === "approval")));
  return (
    <>
      <BaseEdge id={id} path={path} className="ton-flow-edge" />
      <EdgeLabelRenderer>
        {data.label && (
          <span
            className="ton-flow-pill nodrag nopan"
            data-tone={data.tone}
            style={{ transform: `translate(-50%, 0) translate(${targetX}px, ${sourceY + 14}px)` }}
          >
            {data.label}
          </span>
        )}
        <div
          className="ton-flow-insert nodrag nopan"
          style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY + (data.label ? 10 : 0)}px)` }}
        >
          <button
            type="button"
            className="ton-flow-plus ton-focusable"
            aria-label={E.addStep}
            onClick={() => openMenu(open ? null : target)}
          >
            <SvgPlus size={12} />
          </button>
          {open && (
            <div className="ton-flow-menu">
              {types.map((type) => {
                const Icon = STEP_ICONS[type];
                return (
                  <button key={type} type="button" className="ton-flow-menu-item" onClick={() => insert(target, type)}>
                    <Icon size={14} />
                    <span className="flex flex-col items-start text-start">
                      <span className="ton-flow-choice-label">{COPY.steps[type]}</span>
                      <span className="ton-flow-choice-description">{COPY.stepHints[type]}</span>
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

const NODE_TYPES = { trigger: TriggerNode, step: StepNode, merge: MergeNode, end: EndNode };
const EDGE_TYPES = { insert: InsertEdge };

function Canvas({ definition }: { definition: FlowDefinition }) {
  const { openMenu } = useCanvas();
  const graph = useMemo(() => buildGraph(definition), [definition]);
  const flow = useReactFlow();
  const [fitted, setFitted] = useState(false);
  useEffect(() => {
    if (!fitted && graph.nodes.length) {
      requestAnimationFrame(() => flow.fitView({ padding: 0.2, maxZoom: 1 }));
      setFitted(true);
    }
  }, [fitted, graph.nodes.length, flow]);
  return (
    <ReactFlow
      nodes={graph.nodes}
      edges={graph.edges}
      nodeTypes={NODE_TYPES}
      edgeTypes={EDGE_TYPES}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable={false}
      minZoom={0.25}
      maxZoom={1.5}
      panOnScroll
      zoomOnPinch
      onPaneClick={() => openMenu(null)}
      proOptions={{ hideAttribution: true }}
    >
      <Background variant={BackgroundVariant.Dots} gap={20} size={1.2} />
      <Controls showInteractive={false} position="bottom-left" />
      <MiniMap pannable zoomable position="bottom-right" className="ton-flow-minimap" />
    </ReactFlow>
  );
}

// ---------------------------------------------------------------------------
// Panels
// ---------------------------------------------------------------------------

function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <Text font="secondary-action" color="text-04">
        {label}
      </Text>
      {children}
      {hint && (
        <Text font="secondary-body" color="text-03">
          {hint}
        </Text>
      )}
    </label>
  );
}

function Select({
  value,
  label,
  options,
  onChange,
}: {
  value: string;
  label: string;
  options: [string, string][];
  onChange: (value: string) => void;
}) {
  return (
    <InputSingleSelect value={value} onValueChange={onChange}>
      <InputSingleSelect.Trigger aria-label={label} placeholder={label} />
      <InputSingleSelect.Content>
        {options.map(([key, text]) => (
          <InputSingleSelect.Item key={key} value={key}>
            {text}
          </InputSingleSelect.Item>
        ))}
      </InputSingleSelect.Content>
    </InputSingleSelect>
  );
}

function Choice({
  icon,
  label,
  description,
  active,
  onClick,
}: {
  icon: IconFunctionComponent;
  label: string;
  description?: string;
  active: boolean;
  onClick: () => void;
}) {
  const Icon = icon;
  return (
    <button type="button" className="ton-flow-choice ton-focusable" data-active={active || undefined} aria-pressed={active} onClick={onClick}>
      <Icon size={16} />
      <span className="flex min-w-0 flex-col items-start text-start">
        <span className="ton-flow-choice-label">{label}</span>
        {description && active && <span className="ton-flow-choice-description">{description}</span>}
      </span>
    </button>
  );
}

function AddressInput({
  label,
  hint,
  value,
  onChange,
}: {
  label: string;
  hint?: string;
  value: string[];
  onChange: (value: string[]) => void;
}) {
  const [text, setText] = useState(value.join(", "));
  return (
    <Field label={label} hint={hint}>
      <InputTypeIn
        aria-label={label}
        placeholder="nome@valenorte.com.br"
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          onChange(parseAddresses(event.target.value));
        }}
      />
    </Field>
  );
}

function TriggerPanel({
  definition,
  catalog,
  onChange,
}: {
  definition: FlowDefinition;
  catalog: CatalogView;
  onChange: (definition: FlowDefinition) => void;
}) {
  const trigger = definition.trigger;
  const setTrigger = (patch: Partial<FlowDefinition["trigger"]>) =>
    onChange({ ...definition, trigger: { ...trigger, ...patch } });
  return (
    <>
      <div className="flex flex-col gap-1.5">
        {catalog.triggers.map((item) => (
          <Choice
            key={item.kind}
            icon={TRIGGER_ICONS[item.kind]}
            label={item.label}
            description={item.description}
            active={item.kind === trigger.kind}
            onClick={() =>
              item.kind !== trigger.kind &&
              setTrigger({
                kind: item.kind,
                frequency: item.kind === "SCHEDULE" ? "WEEKLY" : null,
                weekday: item.kind === "SCHEDULE" ? 0 : null,
                time: item.kind === "SCHEDULE" ? "08:00" : null,
                changes: item.kind === "NG_OCCURRENCE_CHANGED" ? ["NEW", "REAPPEARED"] : [],
              })
            }
          />
        ))}
      </div>
      {trigger.kind === "SCHEDULE" && (
        <div className="grid grid-cols-2 gap-3">
          <Field label={E.frequency}>
            <Select
              label={E.frequency}
              value={trigger.frequency ?? "WEEKLY"}
              options={[
                ["WEEKLY", E.weekly],
                ["DAILY", E.daily],
              ]}
              onChange={(value) =>
                setTrigger({ frequency: value === "DAILY" ? "DAILY" : "WEEKLY", weekday: value === "DAILY" ? null : trigger.weekday ?? 0 })
              }
            />
          </Field>
          <Field label={E.time}>
            <InputTypeIn aria-label={E.time} value={trigger.time ?? ""} maxLength={5} onChange={(event) => setTrigger({ time: event.target.value })} />
          </Field>
          {trigger.frequency === "WEEKLY" && (
            <Field label={E.weekday}>
              <Select
                label={E.weekday}
                value={String(trigger.weekday ?? 0)}
                options={WEEKDAYS.map((day, index) => [String(index), day])}
                onChange={(value) => setTrigger({ weekday: Number(value) })}
              />
            </Field>
          )}
        </div>
      )}
      {trigger.kind === "NG_OCCURRENCE_CHANGED" && (
        <Field label={E.changes}>
          <span className="flex flex-wrap gap-1.5">
            {catalog.changes.map(([state, label]) => {
              const on = trigger.changes.includes(state);
              return (
                <Button
                  key={state}
                  size="sm"
                  prominence={on ? "primary" : "secondary"}
                  onClick={() =>
                    setTrigger({ changes: on ? trigger.changes.filter((item) => item !== state) : [...trigger.changes, state as ItemState] })
                  }
                >
                  {label}
                </Button>
              );
            })}
          </span>
        </Field>
      )}
      <Field label={E.variables} hint={E.variablesHint}>
        <div className="flex flex-col gap-2">
          {definition.variables.map((variable, index) => (
            <div key={index} className="grid grid-cols-[1fr_1.4fr_auto] gap-2">
              <InputTypeIn
                aria-label={E.variableName}
                placeholder={E.variableName}
                value={variable.name}
                onChange={(event) =>
                  onChange({
                    ...definition,
                    variables: definition.variables.map((item, i) => (i === index ? { ...item, name: event.target.value } : item)),
                  })
                }
              />
              <InputTypeIn
                aria-label={E.variableValue}
                placeholder={E.variableValue}
                value={variable.value}
                onChange={(event) =>
                  onChange({
                    ...definition,
                    variables: definition.variables.map((item, i) => (i === index ? { ...item, value: event.target.value } : item)),
                  })
                }
              />
              <Button
                size="sm"
                prominence="tertiary"
                icon={SvgTrash}
                aria-label={E.remove}
                onClick={() => onChange({ ...definition, variables: definition.variables.filter((_, i) => i !== index) })}
              />
            </div>
          ))}
          <span>
            <Button
              size="sm"
              prominence="secondary"
              onClick={() => onChange({ ...definition, variables: [...definition.variables, { name: "", value: "" }] })}
            >
              {E.addVariable}
            </Button>
          </span>
        </div>
      </Field>
    </>
  );
}

function ConditionPanel({
  step,
  definition,
  catalog,
  onChange,
}: {
  step: ConditionStep;
  definition: FlowDefinition;
  catalog: CatalogView;
  onChange: (step: Step) => void;
}) {
  const fields = catalog.triggers.find((item) => item.kind === definition.trigger.kind)?.fields ?? [];
  const setClause = (index: number, clause: ConditionClause) =>
    onChange({ ...step, conditions: step.conditions.map((item, i) => (i === index ? clause : item)) });
  return (
    <>
      <Text font="secondary-body" color="text-03">
        {COPY.stepHints.condition}
      </Text>
      {step.conditions.length === 0 && (
        <Text font="secondary-body" color="text-03">
          {E.alwaysHint}
        </Text>
      )}
      {step.conditions.map((clause, index) => {
        const field = fields.find((item) => item.key === clause.field) ?? fields[0];
        return (
          <div key={index} className="ton-flow-clause">
            <div className="flex items-center justify-between">
              <Text font="secondary-action" color="text-04">
                {index === 0 ? E.if : E.and}
              </Text>
              <Button
                size="sm"
                prominence="tertiary"
                icon={SvgTrash}
                aria-label={E.remove}
                onClick={() => onChange({ ...step, conditions: step.conditions.filter((_, i) => i !== index) })}
              />
            </div>
            <Select
              label={E.field}
              value={clause.field}
              options={fields.map((item) => [item.key, item.label])}
              onChange={(key) => {
                const next = fields.find((item) => item.key === key);
                if (next)
                  setClause(index, {
                    field: key,
                    operator: next.operators[0] ?? "EQ",
                    value: next.choices[0]?.[0] ?? (next.type === "TEXT" ? "" : 0),
                  });
              }}
            />
            {field && (
              <div className="grid grid-cols-2 gap-2">
                <Select
                  label={E.operator}
                  value={clause.operator}
                  options={field.operators.map((op) => [op, catalog.operators[op]])}
                  onChange={(op) => setClause(index, { ...clause, operator: op as ConditionClause["operator"] })}
                />
                {field.choices.length > 0 && clause.operator === "EQ" ? (
                  <Select label={E.value} value={String(clause.value)} options={field.choices} onChange={(value) => setClause(index, { ...clause, value })} />
                ) : (
                  <InputTypeIn
                    aria-label={E.value}
                    placeholder={E.value}
                    value={Array.isArray(clause.value) ? clause.value.join(", ") : String(clause.value)}
                    onChange={(event) =>
                      setClause(index, {
                        ...clause,
                        value: clause.operator === "IN" ? event.target.value.split(",").map((item) => item.trim()) : event.target.value,
                      })
                    }
                  />
                )}
              </div>
            )}
          </div>
        );
      })}
      {step.conditions.length < 5 && fields[0] && (
        <span>
          <Button
            size="sm"
            prominence="secondary"
            onClick={() =>
              onChange({
                ...step,
                conditions: [
                  ...step.conditions,
                  { field: fields[0]!.key, operator: fields[0]!.operators[0] ?? "EQ", value: fields[0]!.type === "TEXT" ? "" : 0 },
                ],
              })
            }
          >
            {E.addCondition}
          </Button>
        </span>
      )}
    </>
  );
}

function EmailPanel({
  step,
  insideLoop,
  onChange,
  onCompose,
}: {
  step: SendEmailStep;
  insideLoop: boolean;
  onChange: (step: Step) => void;
  onCompose: () => void;
}) {
  return (
    <>
      <AddressInput label={E.to} hint={insideLoop ? E.unitToken : E.addressesHint} value={step.to} onChange={(to) => onChange({ ...step, to })} />
      <AddressInput label={E.cc} value={step.cc} onChange={(cc) => onChange({ ...step, cc })} />
      <AddressInput label={E.bcc} value={step.bcc} onChange={(bcc) => onChange({ ...step, bcc })} />
      <Field label={E.subject} hint={E.subjectHint}>
        <InputTypeIn aria-label={E.subject} value={step.subject} maxLength={200} onChange={(event) => onChange({ ...step, subject: event.target.value })} />
      </Field>
      <Choice
        icon={SvgCheckCircle}
        label={E.useLayout}
        active={step.use_layout}
        onClick={() => onChange({ ...step, use_layout: !step.use_layout })}
      />
      <Button icon={SvgMail} onClick={onCompose}>
        {E.editEmail}
      </Button>
    </>
  );
}

function ForEachPanel({ step, onChange }: { step: ForEachUnitStep; onChange: (step: Step) => void }) {
  const [text, setText] = useState(step.recipients.map((entry) => `${entry.unit} = ${entry.emails.join(", ")}`).join("\n"));
  return (
    <>
      <Text font="secondary-body" color="text-03">
        {COPY.stepHints.for_each_unit}
      </Text>
      <Field label={E.unitRecipients} hint={E.unitRecipientsHint}>
        <InputTextArea
          rows={6}
          value={text}
          onChange={(event) => {
            setText(event.target.value);
            const recipients = event.target.value
              .split("\n")
              .map((line) => line.split("="))
              .filter((parts) => parts.length === 2 && parts[0]!.trim())
              .map(([unit, emails]) => ({ unit: unit!.trim(), emails: parseAddresses(emails ?? "") }));
            onChange({ ...step, recipients });
          }}
        />
      </Field>
      <AddressInput label={E.defaultEmails} value={step.default_emails} onChange={(default_emails) => onChange({ ...step, default_emails })} />
    </>
  );
}

function WaitPanel({ step, onChange }: { step: WaitStep; onChange: (step: Step) => void }) {
  return (
    <>
      <Text font="secondary-body" color="text-03">
        {COPY.stepHints.wait}
      </Text>
      <div className="grid grid-cols-2 gap-1.5">
        <Choice icon={SvgClock} label={E.waitDuration} active={step.mode === "duration"} onClick={() => onChange({ ...step, mode: "duration", days: step.days || 2 })} />
        <Choice icon={SvgCalendar} label={E.waitUntil} active={step.mode === "until"} onClick={() => onChange({ ...step, mode: "until", weekday: step.weekday ?? 4, time: step.time ?? "17:00" })} />
      </div>
      {step.mode === "duration" ? (
        <div className="grid grid-cols-2 gap-3">
          <Field label={E.days}>
            <InputTypeIn aria-label={E.days} value={String(step.days)} onChange={(event) => onChange({ ...step, days: Math.max(0, Math.min(60, Number(event.target.value) || 0)) })} />
          </Field>
          <Field label={E.hours}>
            <InputTypeIn aria-label={E.hours} value={String(step.hours)} onChange={(event) => onChange({ ...step, hours: Math.max(0, Math.min(23, Number(event.target.value) || 0)) })} />
          </Field>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          <Field label={E.weekday}>
            <Select label={E.weekday} value={String(step.weekday ?? 4)} options={WEEKDAYS.map((day, index) => [String(index), day])} onChange={(value) => onChange({ ...step, weekday: Number(value) })} />
          </Field>
          <Field label={E.time}>
            <InputTypeIn aria-label={E.time} value={step.time ?? ""} maxLength={5} onChange={(event) => onChange({ ...step, time: event.target.value })} />
          </Field>
        </div>
      )}
    </>
  );
}

function ApprovalPanel({ step, onChange }: { step: ApprovalStep; onChange: (step: Step) => void }) {
  return (
    <>
      <Text font="secondary-body" color="text-03">
        {COPY.stepHints.approval}
      </Text>
      <AddressInput label={E.approvers} value={step.approvers} onChange={(approvers) => onChange({ ...step, approvers })} />
      <Field label={E.approvalMessage}>
        <InputTextArea rows={3} value={step.message} onChange={(event) => onChange({ ...step, message: event.target.value })} />
      </Field>
    </>
  );
}

function Panel({ title, onClose, footer, children }: { title: string; onClose: () => void; footer?: ReactNode; children: ReactNode }) {
  return (
    <aside className="ton-flow-panel" aria-label={title}>
      <div className="flex items-center justify-between gap-2 px-5 pt-4 pb-3">
        <Text font="main-ui-action" color="text-05">
          {title}
        </Text>
        <Button size="sm" prominence="tertiary" icon={SvgX} aria-label={E.closePanel} onClick={onClose} />
      </div>
      <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-5 pb-5">{children}</div>
      {footer && <div className="flex items-center gap-1 border-t border-border-01 px-5 py-3">{footer}</div>}
    </aside>
  );
}

// ---------------------------------------------------------------------------
// History and preview
// ---------------------------------------------------------------------------

function HistoryModal({ open, runs, onClose }: { open: boolean; runs: RunView[]; onClose: () => void }) {
  const columns = E.historyColumns;
  return (
    <Modal open={open} onOpenChange={(value) => !value && onClose()}>
      <Modal.Content width="xl" height="lg">
        <Modal.Header icon={SvgClock} title={E.history} onClose={onClose} />
        <Modal.Body>
          {runs.length === 0 ? (
            <Text font="secondary-body" color="text-03">
              {E.noRuns}
            </Text>
          ) : (
            <table className="ton-statement ton-classification-grid w-full border-collapse">
              <thead>
                <tr>
                  <th scope="col">{columns.date}</th>
                  <th scope="col" data-numeric>
                    {columns.items}
                  </th>
                  <th scope="col">{columns.recipients}</th>
                  <th scope="col">{columns.status}</th>
                </tr>
              </thead>
              <tbody>
                {runs.flatMap((run) => {
                  const rows = run.deliveries.length ? run.deliveries : [null];
                  return rows.map((delivery, index) => (
                    <tr key={`${run.id}-${index}`}>
                      <td>
                        <Text font="secondary-body" color="text-04">
                          {`${formatDateTime(run.started_at)}${run.is_test ? ` · ${COPY.test}` : ""}${delivery?.unit ? ` · ${delivery.unit}` : ""}`}
                        </Text>
                      </td>
                      <td data-numeric>
                        <Text font="secondary-body" color="text-04">
                          {String(run.item_count)}
                        </Text>
                      </td>
                      <td>
                        <Text font="secondary-body" color="text-04">
                          {delivery ? [...delivery.to, ...delivery.cc].join(", ") : "—"}
                        </Text>
                      </td>
                      <td>
                        <span className="flex flex-col gap-0.5">
                          <Text font="secondary-body" color="text-05">
                            {delivery ? COPY.deliveryStatus[delivery.status] : COPY.runStatus[run.status]}
                          </Text>
                          {(delivery?.error ?? (!delivery ? run.reason : null)) && (
                            <Text font="secondary-body" color="text-03">
                              {delivery?.error ?? run.reason ?? ""}
                            </Text>
                          )}
                          {delivery && (
                            <a className="ton-brand-text text-sm" href={`${EMAIL_FLOWS_API}/deliveries/${delivery.id}/html`} target="_blank" rel="noreferrer">
                              {E.openEmail}
                            </a>
                          )}
                        </span>
                      </td>
                    </tr>
                  ));
                })}
              </tbody>
            </table>
          )}
        </Modal.Body>
      </Modal.Content>
    </Modal>
  );
}

function PreviewModal({ preview, onClose }: { preview: PreviewView | null; onClose: () => void }) {
  return (
    <Modal open={preview !== null} onOpenChange={(value) => !value && onClose()}>
      <Modal.Content width="lg" height="lg">
        <Modal.Header icon={SvgMail} title={preview?.subject ?? E.previewTitle} description={preview?.reason} onClose={onClose} />
        <Modal.Body>
          {preview?.html ? (
            <iframe title={E.previewTitle} srcDoc={preview.html} sandbox="allow-same-origin" className="ton-flow-preview" />
          ) : (
            <Text font="main-ui-body" color="text-04">
              {preview?.reason ?? E.previewNothing}
            </Text>
          )}
        </Modal.Body>
      </Modal.Content>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Editor
// ---------------------------------------------------------------------------

function stepAt(definition: FlowDefinition, address: StepAddress): Step | undefined {
  let steps = definition.steps;
  for (let index = 0; index < address.path.length; index += 2) {
    const step = steps[Number(address.path[index])];
    const branch = address.path[index + 1];
    if (!step) return undefined;
    if (step.type === "condition") steps = branch === "else" ? step.else : step.then;
    else if (step.type === "for_each_unit") steps = step.steps;
    else return undefined;
  }
  return steps[address.index];
}

function Editor({
  flow,
  catalog,
  onSaved,
  onAssetAdded,
}: {
  flow: FlowDetail | null;
  catalog: CatalogView;
  onSaved: (flow: FlowDetail) => void;
  onAssetAdded: (asset: AssetView) => void;
}) {
  const router = useRouter();
  const [name, setName] = useState(flow?.name ?? E.newTitle);
  const [definition, setDefinition] = useState<FlowDefinition>(flow?.definition ?? newDefinition());
  const [selected, setSelected] = useState<StepAddress | "trigger" | null>(null);
  const [menu, setMenu] = useState<InsertTarget | null>(null);
  const [composing, setComposing] = useState<StepAddress | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "error" | "ok"; text: string } | null>(null);
  const [preview, setPreview] = useState<PreviewView | null>(null);
  const [history, setHistory] = useState(false);

  useEffect(() => {
    if (!flow) return;
    setName(flow.name);
    setDefinition(flow.definition);
  }, [flow?.id, flow?.version]); // eslint-disable-line react-hooks/exhaustive-deps

  const dirty = !flow || name !== flow.name || JSON.stringify(definition) !== JSON.stringify(flow.definition);
  const selectedStep = selected && selected !== "trigger" ? stepAt(definition, selected) : undefined;
  const composingStep = composing ? stepAt(definition, composing) : undefined;

  async function run<T>(label: string, task: () => Promise<T>): Promise<T | null> {
    setBusy(label);
    setFeedback(null);
    try {
      return await task();
    } catch (failure) {
      setFeedback({ tone: "error", text: failure instanceof Error ? failure.message : String(failure) });
      return null;
    } finally {
      setBusy(null);
    }
  }

  async function save(): Promise<FlowDetail | null> {
    return run("save", async () => {
      const body = { name: name.trim(), definition };
      const saved = flow
        ? await sendJson<FlowDetail>(`${EMAIL_FLOWS_API}/${flow.id}`, body, "PUT")
        : await sendJson<FlowDetail>(EMAIL_FLOWS_API, { ...body, activate: false });
      setFeedback({ tone: "ok", text: E.saved });
      if (!flow) router.replace(`/ton/fluxos/${saved.id}` as Route);
      onSaved(saved);
      return saved;
    });
  }

  async function changeStatus(action: "activate" | "pause" | "discard") {
    let target = flow;
    if (dirty) target = await save();
    if (!target) return;
    const id = target.id;
    const updated = await run(action, () => sendJson<FlowDetail>(`${EMAIL_FLOWS_API}/${id}/${action}`, {}));
    if (updated) onSaved(updated);
    if (updated && action === "discard") router.push("/ton/fluxos" as Route);
  }

  async function showPreview(stepId: string | null) {
    const result = await run("preview", () =>
      sendJson<PreviewView>(`${EMAIL_FLOWS_API}/preview`, { definition, step_id: stepId, flow_name: name })
    );
    if (result) setPreview(result);
  }

  async function sendToMe(stepId: string | null) {
    if (!flow) return;
    const id = flow.id;
    const result = await run("test", () => sendJson<RunView>(`${EMAIL_FLOWS_API}/${id}/test`, { step_id: stepId }));
    if (result) {
      const status = result.deliveries[0] ? COPY.deliveryStatus[result.deliveries[0].status] : COPY.runStatus[result.status];
      setFeedback({ tone: "ok", text: E.testSent(status) });
      onSaved({ ...flow, runs: [result, ...flow.runs] });
    }
  }

  const actions: CanvasActions = {
    definition,
    catalog,
    selected,
    menu,
    select: (target) => {
      setMenu(null);
      setSelected(target);
    },
    openMenu: setMenu,
    insert: (target, type) => {
      const created = blankStep(type, insideForEach(definition, target.path));
      setDefinition(insertStep(definition, target.path, target.index, created));
      setMenu(null);
      setSelected({ path: target.path, index: target.index });
    },
  };

  const status = flow?.status;
  const panelFooter =
    selected && selected !== "trigger" ? (
      <>
        <Button size="sm" prominence="tertiary" icon={SvgChevronUp} aria-label={E.moveUp} tooltip={E.moveUp} onClick={() => {
          if (selected.index === 0) return;
          setDefinition(moveStep(definition, selected.path, selected.index, -1));
          setSelected({ ...selected, index: selected.index - 1 });
        }} />
        <Button size="sm" prominence="tertiary" icon={SvgChevronDown} aria-label={E.moveDown} tooltip={E.moveDown} onClick={() => {
          setDefinition(moveStep(definition, selected.path, selected.index, 1));
          setSelected({ ...selected, index: selected.index + 1 });
        }} />
        <span className="flex-1" />
        <Button size="sm" prominence="tertiary" icon={SvgTrash} onClick={() => {
          setDefinition(removeStep(definition, selected.path, selected.index));
          setSelected(null);
        }}>
          {E.removeStep}
        </Button>
      </>
    ) : undefined;

  const updateSelected = (step: Step) => {
    if (selected && selected !== "trigger") setDefinition(replaceStep(definition, selected.path, selected.index, step));
  };

  return (
    <CanvasContext.Provider value={actions}>
      <div className="ton-flow-page">
        <header className="ton-flow-topbar">
          <Button size="sm" prominence="tertiary" icon={SvgArrowLeft} href={"/ton/fluxos" as Route}>
            {COPY.back}
          </Button>
          <div className="ton-flow-name min-w-[12rem] max-w-[28rem] flex-1">
            <InputTypeIn aria-label={E.namePlaceholder} placeholder={E.namePlaceholder} value={name} maxLength={120} onChange={(event) => setName(event.target.value)} />
          </div>
          {status && <StatusPill tone={STATUS_TONE[status]}>{COPY.status[status]}</StatusPill>}
          {(feedback || (flow && dirty)) && (
            <Text font="secondary-action" color={feedback?.tone === "error" ? "text-05" : "text-03"}>
              {feedback?.text ?? E.unsaved}
            </Text>
          )}
          <span className="flex-1" />
          <Button size="sm" prominence="tertiary" icon={SvgEye} disabled={busy !== null} onClick={() => showPreview(null)}>
            {E.preview}
          </Button>
          {flow && (
            <Button size="sm" prominence="tertiary" icon={SvgClock} onClick={() => setHistory(true)}>
              {E.history}
            </Button>
          )}
          {flow && (
            <Button size="sm" prominence="tertiary" icon={SvgMail} disabled={busy !== null || dirty} onClick={() => sendToMe(null)}>
              {busy === "test" ? E.sending : E.sendToMe}
            </Button>
          )}
          <Button size="sm" prominence="secondary" disabled={busy !== null || !dirty || name.trim().length < 3} onClick={save}>
            {busy === "save" ? E.saving : E.save}
          </Button>
          {status === "ACTIVE" ? (
            <Button size="sm" prominence="secondary" icon={SvgPauseCircle} disabled={busy !== null} onClick={() => changeStatus("pause")}>
              {E.pause}
            </Button>
          ) : (
            <Button size="sm" icon={SvgPlayCircle} disabled={busy !== null || name.trim().length < 3} onClick={() => changeStatus("activate")}>
              {E.activate}
            </Button>
          )}
          {(status === "SUGGESTED" || status === "PAUSED") && (
            <Button size="sm" prominence="tertiary" disabled={busy !== null} onClick={() => changeStatus("discard")}>
              {E.discard}
            </Button>
          )}
        </header>
        {flow?.status === "SUGGESTED" && flow.suggestion_reason && (
          <div className="ton-flow-notice">
            <Text font="secondary-body" color="text-04">
              {`${COPY.status.SUGGESTED}: ${flow.suggestion_reason}`}
            </Text>
          </div>
        )}
        <div className="ton-flow-canvas-full">
          <Canvas definition={definition} />
          {selected === "trigger" && (
            <Panel title={E.trigger} onClose={() => setSelected(null)}>
              <TriggerPanel definition={definition} catalog={catalog} onChange={setDefinition} />
            </Panel>
          )}
          {selectedStep && selected && selected !== "trigger" && (
            <Panel key={selectedStep.id} title={COPY.steps[selectedStep.type]} onClose={() => setSelected(null)} footer={panelFooter}>
              {selectedStep.type === "condition" && (
                <ConditionPanel step={selectedStep} definition={definition} catalog={catalog} onChange={updateSelected} />
              )}
              {selectedStep.type === "send_email" && (
                <EmailPanel
                  step={selectedStep}
                  insideLoop={insideForEach(definition, selected.path)}
                  onChange={updateSelected}
                  onCompose={() => setComposing(selected)}
                />
              )}
              {selectedStep.type === "for_each_unit" && <ForEachPanel step={selectedStep} onChange={updateSelected} />}
              {selectedStep.type === "wait" && <WaitPanel step={selectedStep} onChange={updateSelected} />}
              {selectedStep.type === "approval" && <ApprovalPanel step={selectedStep} onChange={updateSelected} />}
            </Panel>
          )}
        </div>
      </div>
      {composingStep?.type === "send_email" && composing && (
        <EmailComposer
          open
          step={composingStep}
          definition={definition}
          flowName={name}
          insideLoop={insideForEach(definition, composing.path)}
          catalog={catalog}
          onAssetAdded={onAssetAdded}
          onChange={(step) => setDefinition((current) => replaceStep(current, composing.path, composing.index, step))}
          onClose={() => setComposing(null)}
        />
      )}
      <PreviewModal preview={preview} onClose={() => setPreview(null)} />
      <HistoryModal open={history} runs={flow?.runs ?? []} onClose={() => setHistory(false)} />
    </CanvasContext.Provider>
  );
}

export default function FlowEditorPage({ flowId }: { flowId: string }) {
  const isNew = flowId === "novo";
  const catalog = useFlowCatalog();
  const detail = useFlowDetail(isNew ? null : flowId);
  const [local, setLocal] = useState<FlowDetail | null>(null);
  const flow = local && local.id === flowId ? local : detail.data ?? null;
  const error = catalog.error ?? detail.error;

  if (error)
    return (
      <div className="p-6">
        <ErrorState message={COPY.error} onRetry={() => { catalog.mutate(); detail.mutate(); }} />
      </div>
    );
  if (!catalog.data || (!isNew && !flow))
    return (
      <div className="p-6">
        <LoadingBlock label={COPY.loading} lines={5} />
      </div>
    );
  const catalogData = catalog.data;
  return (
    <ReactFlowProvider>
      <Editor
        key={flow?.id ?? "novo"}
        flow={flow}
        catalog={catalogData}
        onSaved={(saved) => {
          setLocal(saved);
          void detail.mutate(saved, { revalidate: true });
        }}
        onAssetAdded={(asset) => void catalog.mutate({ ...catalogData, assets: [...catalogData.assets, asset] }, { revalidate: false })}
      />
    </ReactFlowProvider>
  );
}
