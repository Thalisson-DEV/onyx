"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import {
  Button,
  InputSingleSelect,
  InputTypeIn,
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

const TRIGGER_ICONS: Record<TriggerKind, IconFunctionComponent> = {
  SCHEDULE: SvgCalendar,
  NG_IMPORT_COMPLETED: SvgZap,
  NG_OCCURRENCE_CHANGED: SvgBranch,
  ACCOUNT_UNCLASSIFIED: SvgFilter,
  DRE_RECALCULATED: SvgSparkle,
};

const STATUS_TONE: Record<FlowStatus, TonTone> = {
  SUGGESTED: "brand",
  ACTIVE: "success",
  PAUSED: "neutral",
  DISCARDED: "neutral",
};

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
      : "Escolha as mudanças";
  }
  return catalog.triggers.find((item) => item.kind === trigger.kind)?.label ?? "";
}

function describeClause(clause: ConditionClause, spec: TriggerView | undefined, catalog: CatalogView): string {
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
  return `${field.label.toLocaleLowerCase("pt-BR")} ${catalog.operators[clause.operator]} ${text}`;
}

function describeAction(action: EmailAction, catalog: CatalogView): string {
  if (action.kind === "NONE") return COPY.editor.nothing;
  const people = action.to.length + action.cc.length + action.bcc.length;
  const template = action.template ? catalog.templates[action.template].split(" (")[0] : "";
  const who = people
    ? `${people} ${people === 1 ? "pessoa" : "pessoas"}`
    : "sem destinatários";
  return `E-mail para ${who} · ${template}`;
}

// ---------------------------------------------------------------------------
// Canvas
// ---------------------------------------------------------------------------

function FlowNode({
  icon,
  kind,
  summary,
  selected,
  muted,
  onSelect,
}: {
  icon: IconFunctionComponent;
  kind: string;
  summary: string;
  selected: boolean;
  muted?: boolean;
  onSelect: () => void;
}) {
  const Icon = icon;
  return (
    <button
      type="button"
      className="ton-flow-node ton-focusable"
      data-selected={selected || undefined}
      data-muted={muted || undefined}
      onClick={onSelect}
    >
      <span className="ton-flow-node-icon" aria-hidden>
        <Icon size={16} />
      </span>
      <span className="flex min-w-0 flex-col items-start gap-1 text-start">
        <span className="ton-flow-node-kind">{kind}</span>
        <Text font="secondary-body" color="text-05">
          {summary}
        </Text>
      </span>
    </button>
  );
}

function Connector({ label }: { label?: string }) {
  return (
    <span className="ton-flow-connector" aria-hidden>
      {label && <span className="ton-flow-connector-label">{label}</span>}
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
  selected: NodeId;
  onSelect: (node: NodeId) => void;
}) {
  const spec = catalog.triggers.find((item) => item.kind === definition.trigger.kind);
  const condition = definition.conditions.length
    ? definition.conditions.map((c) => describeClause(c, spec, catalog)).join(" e ")
    : COPY.editor.always;
  return (
    <div className="ton-flow-canvas">
      <div className="ton-flow-column">
        <FlowNode
          icon={TRIGGER_ICONS[definition.trigger.kind]}
          kind={COPY.editor.trigger}
          summary={describeTrigger(definition, catalog)}
          selected={selected === "trigger"}
          onSelect={() => onSelect("trigger")}
        />
        <Connector />
        <FlowNode
          icon={SvgFilter}
          kind={COPY.editor.condition}
          summary={condition}
          selected={selected === "condition"}
          onSelect={() => onSelect("condition")}
        />
        <div className="ton-flow-split" aria-hidden />
        <div className="ton-flow-branches">
          {(["yes", "no"] as const).map((branch) => {
            const action = branch === "yes" ? definition.on_yes : definition.on_no;
            return (
              <div key={branch} className="ton-flow-column">
                <Connector label={branch === "yes" ? COPY.editor.yes : COPY.editor.no} />
                <FlowNode
                  icon={action.kind === "EMAIL" ? SvgMail : SvgX}
                  kind={COPY.editor.action}
                  summary={describeAction(action, catalog)}
                  selected={selected === branch}
                  muted={action.kind === "NONE"}
                  onSelect={() => onSelect(branch)}
                />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Builder
// ---------------------------------------------------------------------------

function BlockTile({
  icon,
  label,
  active,
  onClick,
}: {
  icon: IconFunctionComponent;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  const Icon = icon;
  return (
    <button
      type="button"
      className="ton-flow-tile ton-focusable"
      data-active={active || undefined}
      onClick={onClick}
    >
      <Icon size={16} />
      <span>{label}</span>
    </button>
  );
}

function Section({
  title,
  open,
  onOpen,
  children,
}: {
  title: string;
  open: boolean;
  onOpen: () => void;
  children: React.ReactNode;
}) {
  return (
    <section className="ton-flow-section" data-open={open || undefined}>
      <button type="button" className="ton-flow-section-head ton-focusable" onClick={onOpen}>
        <span>{title}</span>
        <span aria-hidden>{open ? "–" : "+"}</span>
      </button>
      {open && <div className="flex flex-col gap-3 px-4 pb-4">{children}</div>}
    </section>
  );
}

function Labeled({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <label className="flex flex-col gap-1">
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

function TriggerFields({
  definition,
  catalog,
  onChange,
}: {
  definition: FlowDefinition;
  catalog: CatalogView;
  onChange: (definition: FlowDefinition) => void;
}) {
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
      <div className="ton-flow-tiles">
        {catalog.triggers.map((item) => (
          <BlockTile
            key={item.kind}
            icon={TRIGGER_ICONS[item.kind]}
            label={item.label}
            active={item.kind === trigger.kind}
            onClick={() => choose(item.kind)}
          />
        ))}
      </div>
      <Text font="secondary-body" color="text-03">
        {catalog.triggers.find((item) => item.kind === trigger.kind)?.description}
      </Text>
      {trigger.kind === "SCHEDULE" && (
        <>
          <Labeled label={COPY.editor.frequency}>
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
          </Labeled>
          {trigger.frequency === "WEEKLY" && (
            <Labeled label={COPY.editor.weekday}>
              <Select
                label={COPY.editor.weekday}
                value={String(trigger.weekday ?? 0)}
                options={WEEKDAYS.map((day, index) => [String(index), day])}
                onChange={(value) => setTrigger({ weekday: Number(value) })}
              />
            </Labeled>
          )}
          <Labeled label={COPY.editor.time}>
            <InputTypeIn
              aria-label={COPY.editor.time}
              placeholder="08:00"
              value={trigger.time ?? ""}
              maxLength={5}
              onChange={(event) => setTrigger({ time: event.target.value })}
            />
          </Labeled>
        </>
      )}
      {trigger.kind === "NG_OCCURRENCE_CHANGED" && (
        <Labeled label={COPY.editor.changes}>
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
        </Labeled>
      )}
    </>
  );
}

function ConditionFields({
  definition,
  catalog,
  onChange,
}: {
  definition: FlowDefinition;
  catalog: CatalogView;
  onChange: (definition: FlowDefinition) => void;
}) {
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
          {COPY.editor.always}
        </Text>
      )}
      {definition.conditions.map((clause, index) => {
        const field = fields.find((item) => item.key === clause.field) ?? fields[0];
        return (
          <div key={index} className="ton-flow-clause">
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
                value={Array.isArray(clause.value) ? clause.value.join(", ") : String(clause.value)}
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
}: {
  branch: Branch;
  definition: FlowDefinition;
  catalog: CatalogView;
  addressText: Record<AddressField, string>;
  onAddressText: (field: AddressField, value: string) => void;
  onChange: (definition: FlowDefinition) => void;
}) {
  const key = branch === "yes" ? "on_yes" : "on_no";
  const action = definition[key];
  const spec = catalog.triggers.find((item) => item.kind === definition.trigger.kind);
  function setAction(next: EmailAction) {
    onChange({ ...definition, [key]: next });
  }
  return (
    <>
      <div className="ton-flow-tiles">
        <BlockTile
          icon={SvgMail}
          label={COPY.editor.sendEmail}
          active={action.kind === "EMAIL"}
          onClick={() =>
            action.kind !== "EMAIL" &&
            setAction(emailAction((spec?.templates[0] ?? "SIMPLE_NOTICE") as TemplateKey))
          }
        />
        <BlockTile
          icon={SvgX}
          label={COPY.editor.nothing}
          active={action.kind === "NONE"}
          onClick={() => setAction(emptyAction())}
        />
      </div>
      {action.kind === "EMAIL" && (
        <>
          {(["to", "cc", "bcc"] as const).map((field) => (
            <Labeled
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
            </Labeled>
          ))}
          <Labeled
            label={COPY.editor.subject}
            hint={COPY.editor.markers(
              Object.entries(catalog.subject_markers)
                .map(([marker, meaning]) => `{${marker}} ${meaning}`)
                .join(" · ")
            )}
          >
            <InputTypeIn
              aria-label={COPY.editor.subject}
              value={action.subject}
              maxLength={200}
              onChange={(event) => setAction({ ...action, subject: event.target.value })}
            />
          </Labeled>
          <Labeled label={COPY.editor.template}>
            <Select
              label={COPY.editor.template}
              value={action.template ?? ""}
              options={(spec?.templates ?? []).map((template) => [
                template,
                catalog.templates[template],
              ])}
              onChange={(value) => setAction({ ...action, template: value as TemplateKey })}
            />
          </Labeled>
        </>
      )}
    </>
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
      <table className="ton-statement ton-classification-grid w-full min-w-[760px] border-collapse">
        <thead>
          <tr>
            <th scope="col">{columns.date}</th>
            <th scope="col">{columns.branch}</th>
            <th scope="col" data-numeric>
              {columns.items}
            </th>
            <th scope="col">{columns.recipients}</th>
            <th scope="col">{columns.batch}</th>
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
                    {run.branch === "YES" ? COPY.editor.yes : run.branch === "NO" ? COPY.editor.no : "—"}
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
                      ? `${delivery.to.length} / ${delivery.cc.length} / ${delivery.bcc.length}`
                      : "—"}
                  </Text>
                </td>
                <td>
                  <Text font="secondary-body" color="text-04">
                    {delivery ? `${delivery.batch_no}/${delivery.batch_count}` : "—"}
                  </Text>
                </td>
                <td>
                  <span className="flex flex-col gap-0.5">
                    <Text font="secondary-body" color="text-05">
                      {delivery ? COPY.deliveryStatus[delivery.status] : COPY.runStatus[run.status]}
                    </Text>
                    <Text font="secondary-body" color="text-03">
                      {delivery?.error ?? run.reason ?? ""}
                    </Text>
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

function Preview({ preview, onClose }: { preview: PreviewView; onClose: () => void }) {
  return (
    <div className="ton-card flex flex-col gap-3 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <Text font="main-ui-action" color="text-05">
            {preview.subject ?? COPY.editor.previewTitle}
          </Text>
          <Text font="secondary-body" color="text-03">
            {COPY.editor.previewBranch(
              preview.branch === "YES" ? COPY.editor.yes : COPY.editor.no,
              preview.reason,
              preview.item_count
            )}
          </Text>
          {preview.html && (
            <Text font="secondary-body" color="text-03">
              {COPY.editor.previewRecipients(
                preview.to.length,
                preview.cc.length,
                preview.bcc.length,
                preview.batches
              )}
            </Text>
          )}
        </div>
        <Button size="sm" prominence="tertiary" icon={SvgX} aria-label={COPY.editor.closePreview} onClick={onClose} />
      </div>
      {preview.html ? (
        <iframe
          title={COPY.editor.previewTitle}
          srcDoc={preview.html}
          sandbox=""
          className="ton-flow-preview"
        />
      ) : (
        <Text font="secondary-body" color="text-04">
          {COPY.editor.previewNothing}
        </Text>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Editor
// ---------------------------------------------------------------------------

function addressTexts(definition: FlowDefinition): Record<Branch, Record<AddressField, string>> {
  const join = (action: EmailAction) => ({
    to: action.to.join(", "),
    cc: action.cc.join(", "),
    bcc: action.bcc.join(", "),
  });
  return { yes: join(definition.on_yes), no: join(definition.on_no) };
}

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
  const [selected, setSelected] = useState<NodeId>("trigger");
  const [busy, setBusy] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "error" | "ok"; text: string } | null>(null);
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
    const result = await run("test", () => sendJson<RunView>(`${EMAIL_FLOWS_API}/${id}/test`, {}));
    if (result) {
      const status = result.deliveries[0]
        ? COPY.deliveryStatus[result.deliveries[0].status]
        : COPY.runStatus[result.status];
      setFeedback({ tone: "ok", text: COPY.editor.testSent(status) });
      onSaved({ ...flow, runs: [result, ...flow.runs] });
    }
  }

  const status = flow?.status;
  const section: "trigger" | "condition" | "action" =
    selected === "yes" || selected === "no" ? "action" : selected;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-[16rem] flex-1 items-center gap-3">
          <div className="min-w-[14rem] flex-1">
            <InputTypeIn
              aria-label={COPY.editor.namePlaceholder}
              placeholder={COPY.editor.namePlaceholder}
              value={name}
              maxLength={120}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          {status && <StatusPill tone={STATUS_TONE[status]}>{COPY.status[status]}</StatusPill>}
          {flow && (
            <Text font="secondary-body" color="text-03">
              {COPY.editor.version(flow.version)}
            </Text>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button prominence="secondary" icon={SvgEye} disabled={busy !== null} onClick={showPreview}>
            {COPY.editor.preview}
          </Button>
          {flow && (
            <Button
              prominence="secondary"
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
          {(status === undefined || status === "PAUSED" || status === "SUGGESTED") && (
            <Button
              icon={SvgPlayCircle}
              disabled={busy !== null || name.trim().length < 3}
              onClick={() => changeStatus("activate")}
            >
              {status === "SUGGESTED" ? COPY.editor.register : COPY.editor.activate}
            </Button>
          )}
          {status === "ACTIVE" && (
            <Button icon={SvgPauseCircle} prominence="secondary" disabled={busy !== null} onClick={() => changeStatus("pause")}>
              {COPY.editor.pause}
            </Button>
          )}
          {(status === "SUGGESTED" || status === "PAUSED") && (
            <Button prominence="tertiary" disabled={busy !== null} onClick={() => changeStatus("discard")}>
              {COPY.editor.discard}
            </Button>
          )}
        </div>
      </div>

      {(feedback || (flow && dirty)) && (
        <Text font="secondary-body" color={feedback?.tone === "error" ? "text-05" : "text-03"}>
          {feedback?.text ?? COPY.editor.unsaved}
        </Text>
      )}
      {flow?.status === "SUGGESTED" && flow.suggestion_reason && (
        <Text font="secondary-body" color="text-04">
          {`${COPY.editor.suggestedBy}: ${flow.suggestion_reason}`}
        </Text>
      )}
      {flow?.approved_by && flow.approved_at && (
        <Text font="secondary-body" color="text-03">
          {[
            COPY.editor.approvedBy(flow.approved_by, formatDateTime(flow.approved_at)),
            flow.next_run_at ? COPY.editor.nextRun(formatDateTime(flow.next_run_at)) : null,
          ]
            .filter(Boolean)
            .join(" · ")}
        </Text>
      )}

      <div className="ton-flow-workspace">
        <Canvas definition={definition} catalog={catalog} selected={selected} onSelect={setSelected} />
        <aside className="ton-flow-builder" aria-label={COPY.editor.builder}>
          <div className="flex flex-col gap-1 px-4 pt-4 pb-2">
            <Text font="main-ui-action" color="text-05">
              {COPY.editor.builder}
            </Text>
            <Text font="secondary-body" color="text-03">
              {COPY.editor.builderHint}
            </Text>
          </div>
          <Section title={COPY.editor.trigger} open={section === "trigger"} onOpen={() => setSelected("trigger")}>
            <TriggerFields definition={definition} catalog={catalog} onChange={setDefinition} />
          </Section>
          <Section title={COPY.editor.condition} open={section === "condition"} onOpen={() => setSelected("condition")}>
            <ConditionFields definition={definition} catalog={catalog} onChange={setDefinition} />
          </Section>
          <Section
            title={`${COPY.editor.action} · ${selected === "no" ? COPY.editor.no : COPY.editor.yes}`}
            open={section === "action"}
            onOpen={() => setSelected(selected === "no" ? "no" : "yes")}
          >
            <span className="flex gap-1.5">
              {(["yes", "no"] as const).map((branch) => (
                <Button
                  key={branch}
                  size="sm"
                  prominence={selected === branch ? "primary" : "secondary"}
                  onClick={() => setSelected(branch)}
                >
                  {branch === "yes" ? COPY.editor.yes : COPY.editor.no}
                </Button>
              ))}
            </span>
            <ActionFields
              key={selected}
              branch={selected === "no" ? "no" : "yes"}
              definition={definition}
              catalog={catalog}
              addressText={addresses[selected === "no" ? "no" : "yes"]}
              onAddressText={(field, value) => {
                const branch = selected === "no" ? "no" : "yes";
                setAddresses((current) => ({
                  ...current,
                  [branch]: { ...current[branch], [field]: value },
                }));
              }}
              onChange={setDefinition}
            />
          </Section>
        </aside>
      </div>

      {preview && <Preview preview={preview} onClose={() => setPreview(null)} />}

      {flow && (
        <div className="flex flex-col gap-2">
          <Text font="main-ui-action" color="text-05">
            {COPY.editor.history}
          </Text>
          <History runs={flow.runs} />
        </div>
      )}
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
        <ErrorState message={COPY.error} onRetry={() => { catalog.mutate(); detail.mutate(); }} />
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

