"use client";

import { useRef, useState } from "react";
import { Button, InputSwitch, InputTextArea, InputTypeIn, Text } from "@opal/components";
import { SvgEdit, SvgPaperclip, SvgUploadCloud } from "@opal/icons";
import {
  DESIGNER_COPY as D,
  uploadFile,
  type CatalogView,
  type Definition,
  type FlowNode,
  type Issue,
  type JsonValue,
  type NodeTypeView,
  type ParamView,
  type Params,
} from "@/lib/ton/automations";
import { asList, asText } from "@/lib/ton/automationTree";
import ConditionBuilder from "@/views/ton/AutomationsPage/designer/ConditionBuilder";
import EmailBodyEditor from "@/views/ton/AutomationsPage/designer/EmailBodyEditor";
import {
  ChipsInput,
  ExpressionInput,
  Field,
  MultiToggle,
  RowsEditor,
  Select,
  WeekdaysInput,
  type DynamicContext,
} from "@/views/ton/AutomationsPage/designer/fields";

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const ITEM_PARAMS = new Set(["data.filter:condition", "data.select:mapping", "data.table:columns"]);

function visible(param: ParamView, params: Params, spec: NodeTypeView): boolean {
  if (!param.show_if) return true;
  const [other, values] = param.show_if;
  const fallback = spec.params.find((item) => item.key === other)?.default;
  const current = params[other] ?? fallback;
  return values.includes(asText(current));
}

function stripHtml(html: string): string {
  return html
    .replace(/<div data-block="([^"]+)"[^>]*><\/div>/g, " [$1] ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function FileInput({ value, onChange }: { value: JsonValue | undefined; onChange: (value: JsonValue) => void }) {
  const ref = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const current = value && typeof value === "object" && !Array.isArray(value) ? value : null;
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <Button size="sm" prominence="secondary" icon={SvgUploadCloud} disabled={busy} onClick={() => ref.current?.click()}>
          {busy ? D.uploading : D.upload}
        </Button>
        {current && (
          <span className="ton-auto-chip">
            <SvgPaperclip size={12} />
            {asText(current.name)}
          </span>
        )}
      </div>
      {error && (
        <Text font="secondary-body" color="text-05">
          {error}
        </Text>
      )}
      <input
        ref={ref}
        type="file"
        hidden
        accept=".xlsx,.xlsm,.csv,.txt,.json,.md,.pdf,.docx"
        onChange={async (event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (!file) return;
          setBusy(true);
          setError(null);
          try {
            const stored = await uploadFile(file);
            onChange({ id: stored.id, name: stored.name });
          } catch (failure) {
            setError(failure instanceof Error ? failure.message : String(failure));
          } finally {
            setBusy(false);
          }
        }}
      />
    </div>
  );
}

interface ParamInputProps {
  param: ParamView;
  value: JsonValue | undefined;
  nodeType: string;
  params: Params;
  context: DynamicContext;
  catalog: CatalogView;
  definition: Definition;
  invalid: boolean;
  onChange: (value: JsonValue) => void;
  onOpenEmail: () => void;
}

function ParamInput({ param, value, nodeType, params, context, catalog, definition, invalid, onChange, onOpenEmail }: ParamInputProps) {
  const itemSource = ITEM_PARAMS.has(`${nodeType}:${param.key}`) ? asText(params.items) : undefined;
  const scoped: DynamicContext = itemSource !== undefined ? { ...context, itemSource } : context;
  switch (param.kind) {
    case "boolean":
      return <InputSwitch checked={value === true} onCheckedChange={(checked) => onChange(checked)} aria-label={param.label} />;
    case "select": {
      const options =
        param.key === "name" && nodeType.startsWith("variable.")
          ? definition.variables.map((variable): [string, string] => [variable.name, variable.name])
          : param.options;
      return <Select value={asText(value)} label={param.label} options={options} onChange={onChange} />;
    }
    case "multiselect":
      return <MultiToggle value={asList(value)} options={param.options} onChange={onChange} />;
    case "weekdays":
      return <WeekdaysInput value={asList(value).map(Number)} options={param.options} onChange={onChange} />;
    case "automations":
      return <MultiToggle value={asList(value)} options={catalog.automations.map((item): [string, string] => [item.id, item.name])} onChange={onChange} />;
    case "time":
      return <InputTypeIn type="time" aria-label={param.label} value={asText(value)} onChange={(event) => onChange(event.target.value)} />;
    case "number":
      if (!param.dynamic) {
        return (
          <InputTypeIn
            type="number"
            aria-label={param.label}
            min={param.min ?? undefined}
            max={param.max ?? undefined}
            value={asText(value)}
            onChange={(event) => onChange(event.target.value === "" ? null : Number(event.target.value))}
          />
        );
      }
      return <ExpressionInput value={asText(value)} onChange={(text) => onChange(/^-?\d+([.,]\d+)?$/.test(text) ? Number(text.replace(",", ".")) : text)} context={scoped} label={param.label} placeholder={param.placeholder} invalid={invalid} />;
    case "emails":
      return <ChipsInput values={asList(value)} onChange={onChange} label={param.label} placeholder="nome@valenorte.com.br" context={scoped} validate={(text) => EMAIL.test(text.toLowerCase())} />;
    case "list":
      return <ChipsInput values={asList(value)} onChange={onChange} label={param.label} placeholder={param.placeholder} context={scoped} />;
    case "condition":
      return <ConditionBuilder value={value} operators={catalog.operators} context={scoped} onChange={onChange} />;
    case "fields":
    case "mapping":
    case "columns":
    case "keyvalue":
      return (
        <RowsEditor
          rows={Array.isArray(value) ? value.filter((row): row is Record<string, JsonValue> => !!row && typeof row === "object" && !Array.isArray(row)) : []}
          fields={param.item_fields}
          onChange={onChange}
          context={context}
          itemSource={itemSource}
        />
      );
    case "file":
      return <FileInput value={value} onChange={onChange} />;
    case "json":
      return <InputTextArea aria-label={param.label} rows={5} autoResize maxRows={16} value={asText(value)} onChange={(event) => onChange(event.target.value)} />;
    case "html": {
      const text = stripHtml(asText(value));
      return (
        <div className="ton-auto-html-preview">
          <Text font="secondary-body" color={text ? "text-04" : "text-03"}>
            {text ? (text.length > 220 ? `${text.slice(0, 218)}…` : text) : "—"}
          </Text>
          <Button size="sm" prominence="secondary" icon={SvgEdit} onClick={onOpenEmail}>
            {D.edit}
          </Button>
        </div>
      );
    }
    case "textarea":
      return <ExpressionInput multiline value={asText(value)} onChange={onChange} context={scoped} label={param.label} placeholder={param.placeholder} dynamic={param.dynamic} invalid={invalid} />;
    default:
      return <ExpressionInput value={asText(value)} onChange={onChange} context={scoped} label={param.label} placeholder={param.placeholder} dynamic={param.dynamic} invalid={invalid} />;
  }
}

interface ParamFormProps {
  spec: NodeTypeView;
  nodeId: string;
  node: FlowNode | null;
  params: Params;
  issues: Issue[];
  definition: Definition;
  catalog: CatalogView;
  automationId: string | null;
  automationName: string;
  onChange: (params: Params) => void;
}

export default function ParamForm({ spec, nodeId, node, params, issues, definition, catalog, automationId, automationName, onChange }: ParamFormProps) {
  const [emailOpen, setEmailOpen] = useState(false);
  const [advanced, setAdvanced] = useState(false);
  const context: DynamicContext = { definition, catalog, nodeId };
  const shown = spec.params.filter((param) => visible(param, params, spec));
  const basic = shown.filter((param) => !param.advanced);
  const extra = shown.filter((param) => param.advanced);

  function render(param: ParamView) {
    const issue = issues.find((item) => item.param === param.key);
    return (
      <Field key={param.key} label={param.label} required={param.required} hint={param.help} error={issue?.severity === "error" ? issue.message : null}>
        <ParamInput
          param={param}
          value={params[param.key] ?? param.default}
          nodeType={spec.type}
          params={params}
          context={context}
          catalog={catalog}
          definition={definition}
          invalid={issue?.severity === "error"}
          onChange={(value) => onChange({ ...params, [param.key]: value })}
          onOpenEmail={() => setEmailOpen(true)}
        />
      </Field>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {basic.map(render)}
      {extra.length > 0 && (
        <div className="flex flex-col gap-3">
          <Button size="sm" prominence="tertiary" onClick={() => setAdvanced((value) => !value)}>
            {D.advanced}
          </Button>
          {advanced && extra.map(render)}
        </div>
      )}
      {node && spec.type === "email.send" && (
        <EmailBodyEditor
          open={emailOpen}
          node={node}
          definition={definition}
          catalog={catalog}
          automationId={automationId}
          automationName={automationName}
          onChange={(patch) => onChange({ ...params, ...patch })}
          onClose={() => setEmailOpen(false)}
        />
      )}
      {spec.type === "email.send" && !catalog.provider_ready && (
        <Text font="secondary-body" color="text-03">
          {D.providerMissing}
        </Text>
      )}
      {spec.ai && !catalog.llm_ready && (
        <Text font="secondary-body" color="text-03">
          {D.llmMissing}
        </Text>
      )}
    </div>
  );
}
