"use client";

import { useState } from "react";
import { Button, InputTypeIn, Popover, Text } from "@opal/components";
import { SvgArrowExchange, SvgCopy, SvgMoreHorizontal, SvgPlus, SvgTrash, SvgX } from "@opal/icons";
import {
  DESIGNER_COPY as D,
  RUN_AFTER_LABELS,
  type CatalogView,
  type Definition,
  type FlowNode,
  type Issue,
  type NodeTypeView,
  type RetryPolicy,
  type RunAfter,
} from "@/lib/ton/automations";
import { uniqueId, allIds } from "@/lib/ton/automationTree";
import { nodeIcon } from "@/views/ton/AutomationsPage/designer/icons";
import ParamForm from "@/views/ton/AutomationsPage/designer/ParamForm";
import { Field, Select } from "@/views/ton/AutomationsPage/designer/fields";

type Tab = "params" | "settings" | "outputs";

function IssueList({ issues }: { issues: Issue[] }) {
  if (!issues.length) return null;
  return (
    <ul className="ton-auto-issues">
      {issues.map((issue, index) => (
        <li key={index} data-severity={issue.severity}>
          <Text font="secondary-body" color="text-05">
            {issue.message}
          </Text>
        </li>
      ))}
    </ul>
  );
}

function Settings({ node, spec, onChange }: { node: FlowNode; spec: NodeTypeView; onChange: (node: FlowNode) => void }) {
  const runAfter = node.run_after ?? ["succeeded"];
  const retry: RetryPolicy = node.retry ?? spec.default_retry;
  return (
    <div className="flex flex-col gap-4">
      <Field label={D.notes}>
        <InputTypeIn aria-label={D.notes} value={node.description ?? ""} onChange={(event) => onChange({ ...node, description: event.target.value })} />
      </Field>
      <Field label={D.runAfter} hint={D.runAfterHint}>
        <div className="ton-auto-weekdays" role="group">
          {(Object.keys(RUN_AFTER_LABELS) as RunAfter[]).map((status) => {
            const active = runAfter.includes(status);
            return (
              <button
                key={status}
                type="button"
                className="ton-auto-weekday ton-auto-toggle ton-focusable"
                aria-pressed={active}
                data-active={active || undefined}
                onClick={() => {
                  const next = active ? runAfter.filter((item) => item !== status) : [...runAfter, status];
                  if (next.length) onChange({ ...node, run_after: next });
                }}
              >
                {RUN_AFTER_LABELS[status]}
              </button>
            );
          })}
        </div>
      </Field>
      {!spec.container && node.type !== "control.wait" && node.type !== "approval.request" && node.type !== "control.terminate" && (
        <>
          <Field label={D.retry}>
            <Select
              value={retry.policy}
              label={D.retry}
              options={Object.entries(D.retryPolicy)}
              onChange={(policy) =>
                onChange({
                  ...node,
                  retry: { ...retry, policy: policy as RetryPolicy["policy"], count: policy === "none" ? 0 : Math.max(1, retry.count || 3) },
                })
              }
            />
          </Field>
          {retry.policy !== "none" && (
            <div className="grid grid-cols-2 gap-3">
              <Field label={D.retryCount}>
                <InputTypeIn type="number" min={1} max={10} aria-label={D.retryCount} value={String(retry.count)} onChange={(event) => onChange({ ...node, retry: { ...retry, count: Number(event.target.value) || 1 } })} />
              </Field>
              <Field label={D.retryInterval}>
                <InputTypeIn type="number" min={1} max={3600} aria-label={D.retryInterval} value={String(retry.interval_seconds)} onChange={(event) => onChange({ ...node, retry: { ...retry, interval_seconds: Number(event.target.value) || 30 } })} />
              </Field>
            </div>
          )}
          <Field label={D.timeout} hint={D.timeoutHint}>
            <InputTypeIn
              type="number"
              min={1}
              aria-label={D.timeout}
              value={node.timeout_seconds ? String(node.timeout_seconds) : ""}
              onChange={(event) => onChange({ ...node, timeout_seconds: event.target.value ? Number(event.target.value) : null })}
            />
          </Field>
        </>
      )}
    </div>
  );
}

function Outputs({ nodeId, spec }: { nodeId: string; spec: NodeTypeView }) {
  const prefix = nodeId === "trigger" ? "trigger.outputs" : `steps.${nodeId}.outputs`;
  if (!spec.outputs.length) {
    return (
      <Text font="secondary-body" color="text-03">
        {"—"}
      </Text>
    );
  }
  return (
    <ul className="ton-auto-outputs">
      {spec.outputs.map((output) => (
        <li key={output.key}>
          <span className="flex flex-col">
            <Text font="secondary-action" color="text-05">
              {output.label}
            </Text>
            <code>{`{{ ${prefix}.${output.key} }}`}</code>
            {output.item_fields.length > 0 && (
              <Text font="secondary-body" color="text-03">
                {output.item_fields.map((field) => field.key).join(", ")}
              </Text>
            )}
          </span>
          <span className="ton-auto-dyn-type">{output.type}</span>
        </li>
      ))}
    </ul>
  );
}

function CasesEditor({ node, definition, onChange }: { node: FlowNode; definition: Definition; onChange: (node: FlowNode) => void }) {
  if (node.type === "control.switch") {
    return (
      <Field label={D.addCase}>
        <div className="flex flex-col gap-2">
          {(node.cases ?? []).map((item) => (
            <div key={item.id} className="flex items-center gap-2">
              <div className="flex-1">
                <InputTypeIn aria-label={D.caseValue} placeholder={D.caseValue} value={item.value} onChange={(event) => onChange({ ...node, cases: (node.cases ?? []).map((c) => (c.id === item.id ? { ...c, value: event.target.value } : c)) })} />
              </div>
              <Button size="sm" prominence="tertiary" icon={SvgTrash} aria-label={D.remove} onClick={() => onChange({ ...node, cases: (node.cases ?? []).filter((c) => c.id !== item.id) })} />
            </div>
          ))}
          <div>
            <Button size="sm" prominence="secondary" icon={SvgPlus} onClick={() => onChange({ ...node, cases: [...(node.cases ?? []), { id: uniqueId("caso", allIds(definition)), value: "", steps: [] }] })}>
              {D.addCase}
            </Button>
          </div>
        </div>
      </Field>
    );
  }
  if (node.type === "control.parallel") {
    return (
      <Field label={D.addBranch}>
        <div className="flex flex-col gap-2">
          {(node.branches ?? []).map((branch) => (
            <div key={branch.id} className="flex items-center gap-2">
              <div className="flex-1">
                <InputTypeIn aria-label={D.branchLabel} value={branch.label} onChange={(event) => onChange({ ...node, branches: (node.branches ?? []).map((b) => (b.id === branch.id ? { ...b, label: event.target.value } : b)) })} />
              </div>
              <Button size="sm" prominence="tertiary" icon={SvgTrash} aria-label={D.remove} onClick={() => onChange({ ...node, branches: (node.branches ?? []).filter((b) => b.id !== branch.id) })} />
            </div>
          ))}
          <div>
            <Button
              size="sm"
              prominence="secondary"
              icon={SvgPlus}
              onClick={() => onChange({ ...node, branches: [...(node.branches ?? []), { id: uniqueId("ramo", allIds(definition)), label: `Ramo ${(node.branches ?? []).length + 1}`, steps: [] }] })}
            >
              {D.addBranch}
            </Button>
          </div>
        </div>
      </Field>
    );
  }
  return null;
}

export interface ConfigPanelProps {
  selectedId: string;
  definition: Definition;
  catalog: CatalogView;
  specs: Map<string, NodeTypeView>;
  issues: Issue[];
  automationId: string | null;
  automationName: string;
  readOnly?: boolean;
  onChangeNode: (id: string, node: FlowNode) => void;
  onChangeTrigger: (params: FlowNode["params"]) => void;
  onChangeTriggerType: () => void;
  onDelete: (id: string) => void;
  onDuplicate: (id: string) => void;
  onClose: () => void;
}

export default function ConfigPanel({
  selectedId,
  definition,
  catalog,
  specs,
  issues,
  automationId,
  automationName,
  onChangeNode,
  onChangeTrigger,
  onChangeTriggerType,
  onDelete,
  onDuplicate,
  onClose,
}: ConfigPanelProps) {
  const [tab, setTab] = useState<Tab>("params");
  const isTrigger = selectedId === "trigger";
  const node = isTrigger ? null : findIn(definition.steps, selectedId);
  const type = isTrigger ? definition.trigger.type : node?.type ?? "";
  const spec = specs.get(type);
  if (!spec || (!isTrigger && !node)) return null;
  const Icon = nodeIcon(spec.icon);
  const own = issues.filter((issue) => (issue.node_id ?? "") === selectedId);
  const tabs: [Tab, string][] = isTrigger
    ? [["params", D.parameters], ["outputs", D.outputs]]
    : [["params", D.parameters], ["settings", D.configuration], ["outputs", D.outputs]];

  return (
    <aside className="ton-auto-panel" aria-label={spec.label} data-group={isTrigger ? "trigger" : spec.group}>
      <header className="ton-auto-panel-head">
        <span className="ton-auto-node-icon">
          <Icon size={18} />
        </span>
        <div className="flex min-w-0 flex-1 flex-col">
          {isTrigger ? (
            <Text font="main-ui-action" color="text-05">
              {spec.label}
            </Text>
          ) : (
            <input
              className="ton-auto-title-input ton-focusable"
              aria-label={D.label}
              value={node?.label ?? ""}
              placeholder={spec.label}
              onChange={(event) => node && onChangeNode(node.id, { ...node, label: event.target.value })}
            />
          )}
          <Text font="secondary-body" color="text-03">
            {isTrigger ? D.trigger : `${spec.label} · ${selectedId}`}
          </Text>
        </div>
        {isTrigger ? (
          <Button size="sm" prominence="tertiary" icon={SvgArrowExchange} tooltip={D.addTrigger} aria-label={D.addTrigger} onClick={onChangeTriggerType} />
        ) : (
          <Popover>
            <Popover.Trigger asChild>
              <Button size="sm" prominence="tertiary" icon={SvgMoreHorizontal} aria-label={D.more} />
            </Popover.Trigger>
            <Popover.Content align="end">
              <Popover.Menu>
                {[
                  <Button key="dup" prominence="tertiary" icon={SvgCopy} width="full" onClick={() => onDuplicate(selectedId)}>
                    {D.duplicate}
                  </Button>,
                  <Button key="del" prominence="tertiary" variant="danger" icon={SvgTrash} width="full" onClick={() => onDelete(selectedId)}>
                    {D.remove}
                  </Button>,
                ]}
              </Popover.Menu>
            </Popover.Content>
          </Popover>
        )}
        <Button size="sm" prominence="tertiary" icon={SvgX} aria-label={D.closePanel} onClick={onClose} />
      </header>
      <Text font="secondary-body" color="text-03">
        {spec.description}
      </Text>
      <div className="ton-auto-panel-tabs" role="tablist">
        {tabs.map(([key, label]) => (
          <button key={key} type="button" role="tab" aria-selected={tab === key} className="ton-focusable" onClick={() => setTab(key)}>
            {label}
          </button>
        ))}
      </div>
      <div className="ton-auto-panel-body">
        <IssueList issues={own} />
        {tab === "params" && (
          <>
            <ParamForm
              spec={spec}
              nodeId={selectedId}
              node={node}
              params={isTrigger ? definition.trigger.params : node?.params ?? {}}
              issues={own}
              definition={definition}
              catalog={catalog}
              automationId={automationId}
              automationName={automationName}
              onChange={(params) => (isTrigger ? onChangeTrigger(params) : node && onChangeNode(node.id, { ...node, params }))}
            />
            {node && <CasesEditor node={node} definition={definition} onChange={(next) => onChangeNode(node.id, next)} />}
          </>
        )}
        {tab === "settings" && node && <Settings node={node} spec={spec} onChange={(next) => onChangeNode(node.id, next)} />}
        {tab === "outputs" && <Outputs nodeId={selectedId} spec={spec} />}
      </div>
    </aside>
  );
}

function findIn(nodes: FlowNode[], id: string): FlowNode | null {
  for (const node of nodes) {
    if (node.id === id) return node;
    for (const list of [node.then, node.else, node.default, node.steps, ...(node.cases ?? []).map((c) => c.steps), ...(node.branches ?? []).map((b) => b.steps)]) {
      if (!list) continue;
      const found = findIn(list, id);
      if (found) return found;
    }
  }
  return null;
}
