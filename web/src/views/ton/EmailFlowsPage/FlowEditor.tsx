"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import {
  Button,
  InputSingleSelect,
  InputTypeIn,
  Modal,
  Text,
} from "@opal/components";
import {
  SvgBranch,
  SvgCalendar,
  SvgEye,
  SvgFilter,
  SvgMail,
  SvgPauseCircle,
  SvgPlayCircle,
  SvgSparkle,
  SvgTrash,
  SvgX,
  SvgZap,
} from "@opal/icons";
import type { IconFunctionComponent } from "@opal/types";
import { formatDateTime } from "@/lib/ton/copy";
import {
  EMAIL_FLOWS_API,
  EMAIL_FLOWS_COPY as COPY,
  WEEKDAYS,
  emailAction,
  emptyAction,
  newDefinition,
  parseAddresses,
  sendJson,
  useFlowCatalog,
  useFlowDetail,
  type CatalogView,
  type ConditionClause,
  type EmailAction,
  type FlowDefinition,
  type FlowDetail,
  type FlowStatus,
  type ItemState,
  type PreviewView,
  type RunView,
  type TemplateKey,
  type TriggerKind,
  type TriggerView,
} from "@/lib/ton/emailFlows";
import {
  BackLink,
  ErrorState,
  LoadingBlock,
  PageContainer,
  StatusPill,
  type TonTone,
} from "@/views/ton/components/ui";

type NodeId = "trigger" | "condition" | "yes" | "no";
type Branch = "yes" | "no";
type AddressField = "to" | "cc" | "bcc";
type NodeTone = "trigger" | "condition" | "email" | "none";

const TRIGGER_ICONS = {
  SCHEDULE: SvgCalendar,
  NG_IMPORT_COMPLETED: SvgZap,
  NG_OCCURRENCE_CHANGED: SvgBranch,
  ACCOUNT_UNCLASSIFIED: SvgFilter,
  DRE_RECALCULATED: SvgSparkle,
} satisfies Record<TriggerKind, IconFunctionComponent>;

const STATUS_TONE = {
  SUGGESTED: "brand",
  ACTIVE: "success",
  PAUSED: "neutral",
  DISCARDED: "neutral",
} satisfies Record<FlowStatus, TonTone>;

// ---------------------------------------------------------------------------
// Sentences (mirror the backend's, so the canvas updates while editing)
// ---------------------------------------------------------------------------

function describeTrigger(definition: FlowDefinition, catalog: CatalogView): string {
  const trigger = definition.trigger;
  if (trigger.kind === "SCHEDULE") {
    if (trigger.frequency === "WEEKLY")
      return `Toda ${WEEKDAYS[trigger.weekday ?? 0]} às ${trigger.time ?? "--:--"}`;
    return `Todo dia às ${trigger.time ?? "--:--"}`;
  }
  if (trigger.kind === "NG_OCCURRENCE_CHANGED") {
    const labels = Object.fromEntries(catalog.changes);
    return trigger.changes.length
      ? `Inconsistência ${trigger.changes.map((c) => labels[c]).join(", ")}`
      : COPY.editor.chooseChanges;
  }
  return catalog.triggers.find((item) => item.kind === trigger.kind)?.label ?? "";
}

function describeClause(
  clause: ConditionClause,
  spec: TriggerView | undefined,
  catalog: CatalogView
): string {
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

function recipientsLine(action: EmailAction): string {
  if (!action.to.length) return COPY.editor.noRecipients;
  const to = action.to.length === 1 ? action.to[0] : `${action.to.length} destinatários`;
  const copies = action.cc.length + action.bcc.length;
  return copies ? `${COPY.editor.to}: ${to} · ${COPY.editor.cc}: ${copies}` : `${COPY.editor.to}: ${to}`;
}

// ---------------------------------------------------------------------------
// Canvas
// ---------------------------------------------------------------------------

function FlowNode({
  tone,
  icon,
  label,
  title,
  detail,
  selected,
  onSelect,
}: {
  tone: NodeTone;
  icon: IconFunctionComponent;
  label: string;
  title: string;
  detail?: string;
  selected: boolean;
  onSelect: () => void;
}) {
  const Icon = icon;
  return (
    <button
      type="button"
      className="ton-flow-node ton-focusable"
      data-tone={tone}
      data-selected={selected || undefined}
      onClick={onSelect}
    >
      <span className="ton-flow-node-icon" aria-hidden>
        <Icon size={18} />
      </span>
      <span className="flex min-w-0 flex-col items-start gap-0.5 text-start">
        <span className="ton-flow-node-label">{label}</span>
        <span className="ton-flow-node-title">{title}</span>
        {detail && <span className="ton-flow-node-detail">{detail}</span>}
      </span>
    </button>
  );
}

function Connector({ label, tone }: { label?: string; tone?: "yes" | "no" }) {
  return (
    <span className="ton-flow-connector" aria-hidden>
      {label && (
        <span className="ton-flow-pill" data-tone={tone}>
          {label}
        </span>
      )}
    </span>
  );
}

function Canvas({
  definition,
  catalog,
  selected,
  onSelect,
}: {
  definition: FlowDefinition;
  catalog: CatalogView;
  selected: NodeId | null;
  onSelect: (node: NodeId) => void;
}) {
  const spec = catalog.triggers.find((item) => item.kind === definition.trigger.kind);
  const clauses = definition.conditions.map((c) => describeClause(c, spec, catalog));
  return (
    <div className="ton-flow-stage">
      <FlowNode
        tone="trigger"
        icon={TRIGGER_ICONS[definition.trigger.kind]}
        label={COPY.editor.when}
        title={describeTrigger(definition, catalog)}
        detail={definition.trigger.kind === "SCHEDULE" ? COPY.editor.brasilia : spec?.label}
        selected={selected === "trigger"}
        onSelect={() => onSelect("trigger")}
      />
      <Connector />
      <FlowNode
        tone="condition"
        icon={SvgFilter}
        label={COPY.editor.if}
        title={clauses[0] ?? COPY.editor.always}
        detail={clauses.length > 1 ? clauses.slice(1).map((c) => `e ${c}`).join(" · ") : undefined}
        selected={selected === "condition"}
        onSelect={() => onSelect("condition")}
      />
      <div className="ton-flow-fork" aria-hidden />
      <div className="ton-flow-branches">
        {(["yes", "no"] as const).map((branch) => {
          const action = branch === "yes" ? definition.on_yes : definition.on_no;
          const email = action.kind === "EMAIL";
          return (
            <div key={branch} className="ton-flow-branch">
              <Connector
                label={branch === "yes" ? COPY.editor.yes : COPY.editor.no}
                tone={branch}
              />
              <FlowNode
                tone={email ? "email" : "none"}
                icon={email ? SvgMail : SvgX}
                label={email ? COPY.editor.sendEmail : COPY.editor.nothing}
                title={
                  email
                    ? action.template
                      ? catalog.templates[action.template].split(" (")[0] ?? ""
                      : ""
                    : COPY.editor.nothingDetail
                }
                detail={email ? recipientsLine(action) : undefined}
                selected={selected === branch}
                onSelect={() => onSelect(branch)}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Node panel
// ---------------------------------------------------------------------------

function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
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
    <button
      type="button"
      className="ton-flow-choice ton-focusable"
      data-active={active || undefined}
      aria-pressed={active}
      onClick={onClick}
    >
      <Icon size={16} />
      <span className="flex min-w-0 flex-col items-start text-start">
        <span className="ton-flow-choice-label">{label}</span>
        {description && active && (
          <span className="ton-flow-choice-description">{description}</span>
        )}
      </span>
    </button>
  );
}

interface EditorProps {
  definition: FlowDefinition;
  catalog: CatalogView;
  onChange: (definition: FlowDefinition) => void;
}

function TriggerFields({ definition, catalog, onChange }: EditorProps) {
  const trigger = definition.trigger;
  function setTrigger(patch: Partial<FlowDefinition["trigger"]>) {
    onChange({ ...definition, trigger: { ...trigger, ...patch } });
  }
  function choose(kind: TriggerKind) {
    if (kind === trigger.kind) return;
    const spec = catalog.triggers.find((item) => item.kind === kind);
    const keys = new Set(spec?.fields.map((field) => field.key));
    const fit = (action: EmailAction): EmailAction =>
      action.kind === "EMAIL" && action.template && !spec?.templates.includes(action.template)
        ? { ...action, template: spec?.templates[0] ?? null }
        : action;
    onChange({
      trigger: {
        kind,
        frequency: kind === "SCHEDULE" ? "WEEKLY" : null,
        weekday: kind === "SCHEDULE" ? 0 : null,
        time: kind === "SCHEDULE" ? "08:00" : null,
        changes: kind === "NG_OCCURRENCE_CHANGED" ? ["NEW", "REAPPEARED"] : [],
      },
      conditions: definition.conditions.filter((clause) => keys.has(clause.field)),
      on_yes: fit(definition.on_yes),
      on_no: fit(definition.on_no),
    });
  }
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
            onClick={() => choose(item.kind)}
          />
        ))}
      </div>
      {trigger.kind === "SCHEDULE" && (
        <div className="grid grid-cols-2 gap-3">
          <Field label={COPY.editor.frequency}>
            <Select
              label={COPY.editor.frequency}
              value={trigger.frequency ?? "WEEKLY"}
              options={[
                ["WEEKLY", COPY.editor.weekly],
                ["DAILY", COPY.editor.daily],
              ]}
              onChange={(value) =>
                setTrigger({
                  frequency: value === "DAILY" ? "DAILY" : "WEEKLY",
                  weekday: value === "DAILY" ? null : trigger.weekday ?? 0,
                })
              }
            />
          </Field>
          <Field label={COPY.editor.time}>
            <InputTypeIn
              aria-label={COPY.editor.time}
              placeholder="08:00"
              value={trigger.time ?? ""}
              maxLength={5}
              onChange={(event) => setTrigger({ time: event.target.value })}
            />
          </Field>
          {trigger.frequency === "WEEKLY" && (
            <Field label={COPY.editor.weekday}>
              <Select
                label={COPY.editor.weekday}
                value={String(trigger.weekday ?? 0)}
                options={WEEKDAYS.map((day, index) => [String(index), day])}
                onChange={(value) => setTrigger({ weekday: Number(value) })}
              />
            </Field>
          )}
        </div>
      )}
      {trigger.kind === "NG_OCCURRENCE_CHANGED" && (
        <Field label={COPY.editor.changes}>
          <span className="flex flex-wrap gap-1.5">
            {catalog.changes.map(([state, label]) => {
              const on = trigger.changes.includes(state);
              return (
                <Button
                  key={state}
                  size="sm"
                  prominence={on ? "primary" : "secondary"}
                  onClick={() =>
                    setTrigger({
                      changes: on
                        ? trigger.changes.filter((item) => item !== state)
                        : [...trigger.changes, state as ItemState],
                    })
                  }
                >
                  {label}
                </Button>
              );
            })}
          </span>
        </Field>
      )}
    </>
  );
}

function ConditionFields({ definition, catalog, onChange }: EditorProps) {
  const spec = catalog.triggers.find((item) => item.kind === definition.trigger.kind);
  const fields = spec?.fields ?? [];
  function setClause(index: number, clause: ConditionClause) {
    const conditions = [...definition.conditions];
    conditions[index] = clause;
    onChange({ ...definition, conditions });
  }
  return (
    <>
      {definition.conditions.length === 0 && (
        <Text font="secondary-body" color="text-03">
          {COPY.editor.alwaysHint}
        </Text>
      )}
      {definition.conditions.map((clause, index) => {
        const field = fields.find((item) => item.key === clause.field) ?? fields[0];
        return (
          <div key={index} className="ton-flow-clause">
            <div className="flex items-center justify-between">
              <Text font="secondary-action" color="text-04">
                {index === 0 ? COPY.editor.if : COPY.editor.and}
              </Text>
              <Button
                size="sm"
                prominence="tertiary"
                icon={SvgTrash}
                aria-label={COPY.editor.remove}
                onClick={() =>
                  onChange({
                    ...definition,
                    conditions: definition.conditions.filter((_, i) => i !== index),
                  })
                }
              />
            </div>
            <Select
              label={COPY.editor.field}
              value={clause.field}
              options={fields.map((item) => [item.key, item.label])}
              onChange={(key) => {
                const next = fields.find((item) => item.key === key);
                if (!next) return;
                setClause(index, {
                  field: key,
                  operator: next.operators[0] ?? "EQ",
                  value: next.choices[0]?.[0] ?? (next.type === "TEXT" ? "" : 0),
                });
              }}
            />
            <div className="grid grid-cols-2 gap-2">
              {field && (
                <Select
                  label={COPY.editor.operator}
                  value={clause.operator}
                  options={field.operators.map((op) => [op, catalog.operators[op]])}
                  onChange={(op) =>
                    setClause(index, { ...clause, operator: op as ConditionClause["operator"] })
                  }
                />
              )}
              {field && field.choices.length > 0 && clause.operator === "EQ" ? (
                <Select
                  label={COPY.editor.value}
                  value={String(clause.value)}
                  options={field.choices}
                  onChange={(value) => setClause(index, { ...clause, value })}
                />
              ) : (
                <InputTypeIn
                  aria-label={COPY.editor.value}
                  placeholder={COPY.editor.value}
                  value={
                    Array.isArray(clause.value) ? clause.value.join(", ") : String(clause.value)
                  }
                  onChange={(event) => {
                    const raw = event.target.value;
                    setClause(index, {
                      ...clause,
                      value:
                        clause.operator === "IN"
                          ? raw.split(",").map((item) => item.trim())
                          : raw,
                    });
                  }}
                />
              )}
            </div>
          </div>
        );
      })}
      {definition.conditions.length < 5 && fields.length > 0 && (
        <span>
          <Button
            size="sm"
            prominence="secondary"
            onClick={() =>
              onChange({
                ...definition,
                conditions: [
                  ...definition.conditions,
                  {
                    field: fields[0]!.key,
                    operator: fields[0]!.operators[0] ?? "EQ",
                    value: fields[0]!.type === "TEXT" ? "" : 0,
                  },
                ],
              })
            }
          >
            {COPY.editor.addCondition}
          </Button>
        </span>
      )}
    </>
  );
}

function ActionFields({
  branch,
  definition,
  catalog,
  addressText,
  onAddressText,
  onChange,
}: EditorProps & {
  branch: Branch;
  addressText: Record<AddressField, string>;
  onAddressText: (field: AddressField, value: string) => void;
}) {
  const key = branch === "yes" ? "on_yes" : "on_no";
  const action = definition[key];
  const spec = catalog.triggers.find((item) => item.kind === definition.trigger.kind);
  function setAction(next: EmailAction) {
    onChange({ ...definition, [key]: next });
  }
  return (
    <>
      <div className="grid grid-cols-2 gap-1.5">
        <Choice
          icon={SvgMail}
          label={COPY.editor.sendEmail}
          active={action.kind === "EMAIL"}
          onClick={() =>
            action.kind !== "EMAIL" &&
            setAction(emailAction((spec?.templates[0] ?? "SIMPLE_NOTICE") as TemplateKey))
          }
        />
        <Choice
          icon={SvgX}
          label={COPY.editor.nothing}
          active={action.kind === "NONE"}
          onClick={() => setAction(emptyAction())}
        />
      </div>
      {action.kind === "EMAIL" && (
        <>
          {(["to", "cc", "bcc"] as const).map((field) => (
            <Field
              key={field}
              label={COPY.editor[field]}
              hint={field === "to" ? COPY.editor.addressesHint : undefined}
            >
              <InputTypeIn
                aria-label={COPY.editor[field]}
                placeholder="nome@valenorte.com.br"
                value={addressText[field]}
                onChange={(event) => {
                  onAddressText(field, event.target.value);
                  setAction({ ...action, [field]: parseAddresses(event.target.value) });
                }}
              />
            </Field>
          ))}
          <Field label={COPY.editor.subject} hint={COPY.editor.markersShort}>
            <InputTypeIn
              aria-label={COPY.editor.subject}
              value={action.subject}
              maxLength={200}
              onChange={(event) => setAction({ ...action, subject: event.target.value })}
            />
          </Field>
          <Field label={COPY.editor.template}>
            <Select
              label={COPY.editor.template}
              value={action.template ?? ""}
              options={(spec?.templates ?? []).map((template) => [
                template,
                catalog.templates[template],
              ])}
              onChange={(value) => setAction({ ...action, template: value as TemplateKey })}
            />
          </Field>
        </>
      )}
    </>
  );
}

function NodePanel({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <aside className="ton-flow-panel" aria-label={title}>
      <div className="flex items-center justify-between gap-2 px-5 pt-4 pb-3">
        <Text font="main-ui-action" color="text-05">
          {title}
        </Text>
        <Button
          size="sm"
          prominence="tertiary"
          icon={SvgX}
          aria-label={COPY.editor.closePanel}
          onClick={onClose}
        />
      </div>
      <div className="flex flex-col gap-4 overflow-y-auto px-5 pb-5">{children}</div>
    </aside>
  );
}

// ---------------------------------------------------------------------------
// History and preview
// ---------------------------------------------------------------------------

function History({ runs }: { runs: RunView[] }) {
  if (!runs.length) {
    return (
      <Text font="secondary-body" color="text-03">
        {COPY.editor.noRuns}
      </Text>
    );
  }
  const columns = COPY.editor.historyColumns;
  return (
    <div className="ton-card overflow-x-auto">
      <table className="ton-statement ton-classification-grid w-full min-w-[720px] border-collapse">
        <thead>
          <tr>
            <th scope="col">{columns.date}</th>
            <th scope="col">{columns.branch}</th>
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
                    {`${formatDateTime(run.started_at)}${run.is_test ? ` · ${COPY.test}` : ""}`}
                  </Text>
                </td>
                <td>
                  <Text font="secondary-body" color="text-04">
                    {run.branch === "YES"
                      ? COPY.editor.yes
                      : run.branch === "NO"
                        ? COPY.editor.no
                        : "—"}
                  </Text>
                </td>
                <td data-numeric>
                  <Text font="secondary-body" color="text-04">
                    {String(run.item_count)}
                  </Text>
                </td>
                <td>
                  <Text font="secondary-body" color="text-04">
                    {delivery
                      ? `${[...delivery.to, ...delivery.cc].join(", ")}${
                          delivery.batch_count > 1
                            ? ` · lote ${delivery.batch_no}/${delivery.batch_count}`
                            : ""
                        }`
                      : "—"}
                  </Text>
                </td>
                <td>
                  <span className="flex flex-col gap-0.5">
                    <Text font="secondary-body" color="text-05">
                      {delivery
                        ? COPY.deliveryStatus[delivery.status]
                        : COPY.runStatus[run.status]}
                    </Text>
                    {(delivery?.error ?? (!delivery ? run.reason : null)) && (
                      <Text font="secondary-body" color="text-03">
                        {delivery?.error ?? run.reason ?? ""}
                      </Text>
                    )}
                    {delivery && (
                      <a
                        className="ton-brand-text text-sm"
                        href={`${EMAIL_FLOWS_API}/deliveries/${delivery.id}/html`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {COPY.editor.openEmail}
                      </a>
                    )}
                  </span>
                </td>
              </tr>
            ));
          })}
        </tbody>
      </table>
    </div>
  );
}

function PreviewModal({
  preview,
  onClose,
}: {
  preview: PreviewView | null;
  onClose: () => void;
}) {
  return (
    <Modal open={preview !== null} onOpenChange={(open) => !open && onClose()}>
      <Modal.Content width="lg" height="lg">
        <Modal.Header
          icon={SvgMail}
          title={preview?.subject ?? COPY.editor.previewTitle}
          description={
            preview
              ? [
                  COPY.editor.previewBranch(
                    preview.branch === "YES" ? COPY.editor.yes : COPY.editor.no,
                    preview.reason,
                    preview.item_count
                  ),
                  preview.html
                    ? COPY.editor.previewRecipients(
                        preview.to.length,
                        preview.cc.length,
                        preview.bcc.length,
                        preview.batches
                      )
                    : null,
                ]
                  .filter(Boolean)
                  .join(" · ")
              : undefined
          }
          onClose={onClose}
        />
        <Modal.Body>
          {preview?.html ? (
            <iframe
              title={COPY.editor.previewTitle}
              srcDoc={preview.html}
              sandbox=""
              className="ton-flow-preview"
            />
          ) : (
            <Text font="main-ui-body" color="text-04">
              {COPY.editor.previewNothing}
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

function addressTexts(definition: FlowDefinition) {
  const join = (action: EmailAction) => ({
    to: action.to.join(", "),
    cc: action.cc.join(", "),
    bcc: action.bcc.join(", "),
  });
  return { yes: join(definition.on_yes), no: join(definition.on_no) };
}

const PANEL_TITLES = {
  trigger: COPY.editor.when,
  condition: COPY.editor.if,
  yes: `${COPY.editor.action} · ${COPY.editor.yes}`,
  no: `${COPY.editor.action} · ${COPY.editor.no}`,
} satisfies Record<NodeId, string>;

function Editor({
  flow,
  catalog,
  onSaved,
}: {
  flow: FlowDetail | null;
  catalog: CatalogView;
  onSaved: (flow: FlowDetail) => void;
}) {
  const router = useRouter();
  const [name, setName] = useState(flow?.name ?? "");
  const [definition, setDefinition] = useState<FlowDefinition>(
    flow?.definition ?? newDefinition()
  );
  const [addresses, setAddresses] = useState(addressTexts(flow?.definition ?? newDefinition()));
  const [selected, setSelected] = useState<NodeId | null>(flow ? null : "trigger");
  const [busy, setBusy] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "error" | "ok"; text: string } | null>(
    null
  );
  const [preview, setPreview] = useState<PreviewView | null>(null);

  useEffect(() => {
    if (!flow) return;
    setName(flow.name);
    setDefinition(flow.definition);
    setAddresses(addressTexts(flow.definition));
  }, [flow?.id, flow?.version]); // eslint-disable-line react-hooks/exhaustive-deps

  const dirty = useMemo(
    () =>
      !flow ||
      name !== flow.name ||
      JSON.stringify(definition) !== JSON.stringify(flow.definition),
    [flow, name, definition]
  );

  async function run<T>(label: string, task: () => Promise<T>): Promise<T | null> {
    setBusy(label);
    setFeedback(null);
    try {
      return await task();
    } catch (failure) {
      setFeedback({
        tone: "error",
        text: failure instanceof Error ? failure.message : String(failure),
      });
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
      setFeedback({ tone: "ok", text: COPY.editor.saved });
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
    const updated = await run(action, () =>
      sendJson<FlowDetail>(`${EMAIL_FLOWS_API}/${id}/${action}`, {})
    );
    if (updated) onSaved(updated);
    if (updated && action === "discard") router.push("/ton/fluxos" as Route);
  }

  async function showPreview() {
    const result = await run("preview", () =>
      sendJson<PreviewView>(`${EMAIL_FLOWS_API}/preview`, { definition })
    );
    if (result) setPreview(result);
  }

  async function sendToMe() {
    if (!flow) return;
    const id = flow.id;
    const result = await run("test", () =>
      sendJson<RunView>(`${EMAIL_FLOWS_API}/${id}/test`, {})
    );
    if (result) {
      const status = result.deliveries[0]
        ? COPY.deliveryStatus[result.deliveries[0].status]
        : COPY.runStatus[result.status];
      setFeedback({ tone: "ok", text: COPY.editor.testSent(status) });
      onSaved({ ...flow, runs: [result, ...flow.runs] });
    }
  }

  const status = flow?.status;
  const branch: Branch = selected === "no" ? "no" : "yes";
  const subtitle =
    flow?.status === "SUGGESTED" && flow.suggestion_reason
      ? flow.suggestion_reason
      : flow?.approved_by && flow.approved_at
        ? [
            COPY.editor.approvedBy(flow.approved_by, formatDateTime(flow.approved_at)),
            flow.next_run_at ? COPY.editor.nextRun(formatDateTime(flow.next_run_at)) : null,
          ]
            .filter(Boolean)
            .join(" · ")
        : null;

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-[18rem] flex-1 items-center gap-3">
            <div className="ton-flow-name min-w-0 flex-1">
              <InputTypeIn
                aria-label={COPY.editor.namePlaceholder}
                placeholder={COPY.editor.namePlaceholder}
                value={name}
                maxLength={120}
                onChange={(event) => setName(event.target.value)}
              />
            </div>
            {status && <StatusPill tone={STATUS_TONE[status]}>{COPY.status[status]}</StatusPill>}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              prominence="tertiary"
              icon={SvgEye}
              disabled={busy !== null}
              onClick={showPreview}
            >
              {COPY.editor.preview}
            </Button>
            {flow && (
              <Button
                prominence="tertiary"
                icon={SvgMail}
                disabled={busy !== null || dirty}
                onClick={sendToMe}
              >
                {busy === "test" ? COPY.editor.sending : COPY.editor.sendToMe}
              </Button>
            )}
            <Button
              prominence="secondary"
              disabled={busy !== null || !dirty || name.trim().length < 3}
              onClick={save}
            >
              {busy === "save" ? COPY.editor.saving : COPY.editor.save}
            </Button>
            {status === "ACTIVE" ? (
              <Button
                icon={SvgPauseCircle}
                prominence="secondary"
                disabled={busy !== null}
                onClick={() => changeStatus("pause")}
              >
                {COPY.editor.pause}
              </Button>
            ) : (
              <Button
                icon={SvgPlayCircle}
                disabled={busy !== null || name.trim().length < 3}
                onClick={() => changeStatus("activate")}
              >
                {status === "SUGGESTED" ? COPY.editor.register : COPY.editor.activate}
              </Button>
            )}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          {subtitle && (
            <Text font="secondary-body" color="text-03">
              {subtitle}
            </Text>
          )}
          {(feedback || (flow && dirty)) && (
            <Text
              font="secondary-action"
              color={feedback?.tone === "error" ? "text-05" : "text-04"}
            >
              {feedback?.text ?? COPY.editor.unsaved}
            </Text>
          )}
          {(status === "SUGGESTED" || status === "PAUSED") && (
            <Button
              size="sm"
              prominence="tertiary"
              disabled={busy !== null}
              onClick={() => changeStatus("discard")}
            >
              {COPY.editor.discard}
            </Button>
          )}
        </div>
      </header>

      <div className="ton-flow-canvas" data-panel={selected ? true : undefined}>
        <Canvas
          definition={definition}
          catalog={catalog}
          selected={selected}
          onSelect={setSelected}
        />
        {!selected && (
          <span className="ton-flow-hint">
            <Text font="secondary-body" color="text-03">
              {COPY.editor.clickHint}
            </Text>
          </span>
        )}
        {selected && (
          <NodePanel title={PANEL_TITLES[selected]} onClose={() => setSelected(null)}>
            {selected === "trigger" && (
              <TriggerFields definition={definition} catalog={catalog} onChange={setDefinition} />
            )}
            {selected === "condition" && (
              <ConditionFields
                definition={definition}
                catalog={catalog}
                onChange={setDefinition}
              />
            )}
            {(selected === "yes" || selected === "no") && (
              <ActionFields
                key={selected}
                branch={branch}
                definition={definition}
                catalog={catalog}
                addressText={addresses[branch]}
                onAddressText={(field, value) =>
                  setAddresses((current) => ({
                    ...current,
                    [branch]: { ...current[branch], [field]: value },
                  }))
                }
                onChange={setDefinition}
              />
            )}
          </NodePanel>
        )}
      </div>

      {flow && (
        <section className="flex flex-col gap-2">
          <Text font="main-ui-action" color="text-05">
            {COPY.editor.history}
          </Text>
          <History runs={flow.runs} />
        </section>
      )}

      <PreviewModal preview={preview} onClose={() => setPreview(null)} />
    </div>
  );
}

export default function FlowEditorPage({ flowId }: { flowId: string }) {
  const isNew = flowId === "novo";
  const catalog = useFlowCatalog();
  const detail = useFlowDetail(isNew ? null : flowId);
  const [local, setLocal] = useState<FlowDetail | null>(null);
  const flow = local && local.id === flowId ? local : detail.data ?? null;

  const error = catalog.error ?? detail.error;
  return (
    <PageContainer>
      <BackLink href={"/ton/fluxos" as Route} label={COPY.back} />
      {error ? (
        <ErrorState
          message={COPY.error}
          onRetry={() => {
            catalog.mutate();
            detail.mutate();
          }}
        />
      ) : !catalog.data || (!isNew && !flow) ? (
        <div className="ton-card p-5">
          <LoadingBlock label={COPY.loading} lines={5} />
        </div>
      ) : (
        <Editor
          key={flow?.id ?? "novo"}
          flow={flow}
          catalog={catalog.data}
          onSaved={(saved) => {
            setLocal(saved);
            detail.mutate(saved, { revalidate: true });
          }}
        />
      )}
    </PageContainer>
  );
}
