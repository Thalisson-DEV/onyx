"use client";

import { useMemo, useRef, useState, type ReactNode } from "react";
import {
  Button,
  InputSingleSelect,
  InputSwitch,
  InputTextArea,
  InputTypeIn,
  Popover,
  Text,
} from "@opal/components";
import { SvgChevronDown, SvgChevronRight, SvgPlus, SvgTrash, SvgX, SvgZap } from "@opal/icons";
import { cn } from "@opal/utils";
import {
  DESIGNER_COPY as D,
  type CatalogView,
  type Definition,
  type FieldView,
  type JsonValue,
} from "@/lib/ton/automations";
import { asText } from "@/lib/ton/automationTree";
import {
  describeExpression,
  dynamicGroups,
  segments,
  type DynamicGroup,
} from "@/views/ton/AutomationsPage/designer/dynamic";
import { nodeIcon } from "@/views/ton/AutomationsPage/designer/icons";

// ---------------------------------------------------------------------------
// Layout helpers
// ---------------------------------------------------------------------------

interface FieldProps {
  label: string;
  required?: boolean;
  hint?: string | null;
  error?: string | null;
  children: ReactNode;
}

export function Field({ label, required, hint, error, children }: FieldProps) {
  return (
    <div className="ton-auto-field">
      <span className="ton-auto-field-label">
        <Text font="secondary-action" color="text-04">
          {label}
        </Text>
        {required && <span className="ton-auto-required" aria-label={D.required}>*</span>}
      </span>
      {children}
      {error ? (
        <Text font="secondary-body" color="text-05">
          {error}
        </Text>
      ) : (
        hint && (
          <Text font="secondary-body" color="text-03">
            {hint}
          </Text>
        )
      )}
    </div>
  );
}

interface SelectProps {
  value: string;
  label: string;
  options: [string, string][];
  onChange: (value: string) => void;
}

export function Select({ value, label, options, onChange }: SelectProps) {
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

// ---------------------------------------------------------------------------
// Dynamic content
// ---------------------------------------------------------------------------

export interface DynamicContext {
  definition: Definition;
  catalog: CatalogView;
  nodeId: string;
  itemSource?: string;
}

interface DynamicPickerProps {
  context: DynamicContext;
  onPick: (expression: string) => void;
}

function GroupList({ group, query, onPick }: { group: DynamicGroup; query: string; onPick: (expression: string) => void }) {
  const [open, setOpen] = useState(true);
  const Icon = nodeIcon(group.icon);
  const items = group.items.filter(
    (item) => !query || `${item.label} ${item.expression} ${group.title}`.toLowerCase().includes(query.toLowerCase())
  );
  if (!items.length) return null;
  return (
    <div className="ton-auto-dyn-group" data-group={group.group}>
      <button type="button" className="ton-auto-dyn-head ton-focusable" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        {open ? <SvgChevronDown size={14} /> : <SvgChevronRight size={14} />}
        <span className="ton-auto-dyn-icon">
          <Icon size={13} />
        </span>
        <span className="ton-auto-dyn-title">{group.title}</span>
      </button>
      {open && (
        <ul>
          {items.map((item) => (
            <li key={item.expression}>
              <button type="button" className="ton-auto-dyn-item ton-focusable" onClick={() => onPick(item.expression)} title={item.description || item.expression}>
                <span className="ton-auto-dyn-label">{item.label}</span>
                <span className="ton-auto-dyn-type">{item.type}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function DynamicPicker({ context, onPick }: DynamicPickerProps) {
  const [query, setQuery] = useState("");
  const [tab, setTab] = useState<"content" | "expression">("content");
  const [expression, setExpression] = useState("");
  const groups = useMemo(
    () => dynamicGroups(context.definition, context.nodeId, context.catalog, { itemSource: context.itemSource }),
    [context.definition, context.nodeId, context.catalog, context.itemSource]
  );
  return (
    <div className="ton-auto-dyn">
      <div className="ton-auto-dyn-tabs" role="tablist">
        <button type="button" role="tab" aria-selected={tab === "content"} className="ton-focusable" onClick={() => setTab("content")}>
          {D.dynamic}
        </button>
        <button type="button" role="tab" aria-selected={tab === "expression"} className="ton-focusable" onClick={() => setTab("expression")}>
          {D.expression}
        </button>
      </div>
      {tab === "content" ? (
        <>
          <InputTypeIn searchIcon placeholder={D.search} value={query} onChange={(event) => setQuery(event.target.value)} />
          <div className="ton-auto-dyn-list">
            {groups.length === 0 && (
              <Text font="secondary-body" color="text-03">
                {D.noOutputs}
              </Text>
            )}
            {groups.map((group) => (
              <GroupList key={group.key} group={group} query={query} onPick={onPick} />
            ))}
          </div>
        </>
      ) : (
        <div className="flex flex-col gap-2">
          <InputTextArea
            rows={3}
            autoResize
            maxRows={6}
            placeholder="format_money(sum(steps.buscar.outputs.items, 'valor'))"
            value={expression}
            onChange={(event) => setExpression(event.target.value)}
          />
          <div className="flex justify-end">
            <Button size="sm" disabled={!expression.trim()} onClick={() => onPick(expression.trim())}>
              {D.insert}
            </Button>
          </div>
          <Text font="secondary-action" color="text-04">
            {D.functions}
          </Text>
          <ul className="ton-auto-dyn-functions">
            {Object.entries(context.catalog.functions).map(([name, help]) => (
              <li key={name}>
                <button type="button" className="ton-focusable" onClick={() => setExpression((value) => `${value}${name}(`)}>
                  <code>{name}</code>
                  <span>{help.split("—")[1]?.trim() ?? help}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function TokenChips({ value, context }: { value: string; context: DynamicContext }) {
  const tokens = segments(value).filter((part) => part.expression !== undefined);
  if (!tokens.length) return null;
  return (
    <span className="ton-auto-tokens">
      {tokens.map((part, index) => (
        <span key={`${part.expression}-${index}`} className="ton-auto-token" title={`{{ ${part.expression} }}`}>
          <SvgZap size={11} />
          {describeExpression(part.expression ?? "", context.definition, context.catalog)}
        </span>
      ))}
    </span>
  );
}

interface ExpressionInputProps {
  value: string;
  onChange: (value: string) => void;
  context: DynamicContext;
  label: string;
  placeholder?: string | null;
  multiline?: boolean;
  dynamic?: boolean;
  invalid?: boolean;
}

/** Text with {{ expressions }}: the ⚡ button inserts dynamic content at the cursor. */
export function ExpressionInput({ value, onChange, context, label, placeholder, multiline, dynamic = true, invalid }: ExpressionInputProps) {
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const areaRef = useRef<HTMLTextAreaElement>(null);
  const cursor = useRef<number | null>(null);

  function remember() {
    const element = multiline ? areaRef.current : inputRef.current;
    cursor.current = element?.selectionStart ?? null;
  }

  function insert(expression: string) {
    const token = `{{ ${expression} }}`;
    const at = cursor.current ?? value.length;
    onChange(`${value.slice(0, at)}${token}${value.slice(at)}`);
    cursor.current = at + token.length;
    setOpen(false);
  }

  const picker = dynamic && context.nodeId !== "trigger" && (
    <Popover open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <Button size="sm" prominence="tertiary" icon={SvgZap} tooltip={D.dynamic} aria-label={D.dynamic} onMouseDown={remember} />
      </Popover.Trigger>
      <Popover.Content width="lg" align="end">
        <DynamicPicker context={context} onPick={insert} />
      </Popover.Content>
    </Popover>
  );

  return (
    <div className="flex flex-col gap-1">
      {multiline ? (
        <InputTextArea
          ref={areaRef}
          aria-label={label}
          variant={invalid ? "error" : "primary"}
          rows={3}
          autoResize
          maxRows={14}
          placeholder={placeholder ?? undefined}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onSelect={remember}
          onBlur={remember}
          rightSection={picker || undefined}
        />
      ) : (
        <InputTypeIn
          ref={inputRef}
          aria-label={label}
          variant={invalid ? "error" : "primary"}
          placeholder={placeholder ?? undefined}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onSelect={remember}
          onBlur={remember}
          rightChildren={picker || undefined}
        />
      )}
      <TokenChips value={value} context={context} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Lists
// ---------------------------------------------------------------------------

interface ChipsInputProps {
  values: string[];
  onChange: (values: string[]) => void;
  label: string;
  placeholder?: string | null;
  context: DynamicContext;
  validate?: (value: string) => boolean;
}

/** Chips (e-mails, categories); each chip may be an expression. */
export function ChipsInput({ values, onChange, label, placeholder, context, validate }: ChipsInputProps) {
  const [draft, setDraft] = useState("");
  const [open, setOpen] = useState(false);

  function commit(raw: string) {
    const parts = raw
      .split(/[,;\n]+/)
      .map((part) => part.trim())
      .filter(Boolean);
    if (!parts.length) return;
    onChange([...values, ...parts.filter((part) => !values.includes(part))]);
    setDraft("");
  }

  return (
    <div className="ton-auto-chips">
      {values.map((value, index) => {
        const expression = segments(value).find((part) => part.expression !== undefined)?.expression;
        const bad = !expression && validate ? !validate(value) : false;
        return (
          <span key={`${value}-${index}`} className={cn("ton-auto-chip", expression && "ton-auto-chip-dynamic")} data-invalid={bad || undefined}>
            {expression ? describeExpression(expression, context.definition, context.catalog) : value}
            <button type="button" className="ton-focusable" aria-label={`${D.removeRule} ${value}`} onClick={() => onChange(values.filter((_, i) => i !== index))}>
              <SvgX size={11} />
            </button>
          </span>
        );
      })}
      <input
        className="ton-auto-chips-input"
        aria-label={label}
        placeholder={values.length ? "" : placeholder ?? ""}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === "," || event.key === ";" || event.key === "Tab") {
            if (draft.trim()) {
              event.preventDefault();
              commit(draft);
            }
          } else if (event.key === "Backspace" && !draft && values.length) {
            onChange(values.slice(0, -1));
          }
        }}
        onBlur={() => draft.trim() && commit(draft)}
        onPaste={(event) => {
          const text = event.clipboardData.getData("text");
          if (/[,;\n]/.test(text)) {
            event.preventDefault();
            commit(text);
          }
        }}
      />
      {context.nodeId !== "trigger" && (
        <Popover open={open} onOpenChange={setOpen}>
          <Popover.Trigger asChild>
            <Button size="sm" prominence="tertiary" icon={SvgZap} tooltip={D.dynamic} aria-label={D.dynamic} />
          </Popover.Trigger>
          <Popover.Content width="lg" align="end">
            <DynamicPicker
              context={context}
              onPick={(expression) => {
                onChange([...values, `{{ ${expression} }}`]);
                setOpen(false);
              }}
            />
          </Popover.Content>
        </Popover>
      )}
    </div>
  );
}

type Row = Record<string, JsonValue>;

interface RowsEditorProps {
  rows: Row[];
  fields: FieldView[];
  onChange: (rows: Row[]) => void;
  context: DynamicContext;
  itemSource?: string;
}

/** Table-like editor for list parameters (fields, mapping, columns, headers). */
export function RowsEditor({ rows, fields, onChange, context, itemSource }: RowsEditorProps) {
  function update(index: number, key: string, value: JsonValue) {
    onChange(rows.map((row, i) => (i === index ? { ...row, [key]: value } : row)));
  }
  return (
    <div className="ton-auto-rows">
      {rows.map((row, index) => (
        <div key={index} className="ton-auto-row">
          <div className="ton-auto-row-fields">
            {fields.map((field) => {
              const label = field.label;
              if (field.kind === "select") {
                return (
                  <div key={field.key} className="ton-auto-row-cell">
                    <Select value={asText(row[field.key]) || field.options[0]?.[0] || ""} label={label} options={field.options} onChange={(value) => update(index, field.key, value)} />
                  </div>
                );
              }
              if (field.kind === "boolean") {
                return (
                  <label key={field.key} className="ton-auto-row-cell ton-auto-row-switch">
                    <InputSwitch checked={row[field.key] === true} onCheckedChange={(checked) => update(index, field.key, checked)} aria-label={label} />
                    <Text font="secondary-body" color="text-04">
                      {label}
                    </Text>
                  </label>
                );
              }
              if (field.kind === "expression") {
                return (
                  <div key={field.key} className="ton-auto-row-cell ton-auto-row-wide">
                    <ExpressionInput
                      value={asText(row[field.key])}
                      onChange={(value) => update(index, field.key, value)}
                      context={{ ...context, itemSource: itemSource ?? context.itemSource }}
                      label={label}
                      placeholder={field.placeholder ?? label}
                    />
                  </div>
                );
              }
              return (
                <div key={field.key} className="ton-auto-row-cell">
                  <InputTypeIn aria-label={label} placeholder={field.placeholder ?? label} value={asText(row[field.key])} onChange={(event) => update(index, field.key, event.target.value)} />
                </div>
              );
            })}
          </div>
          <Button size="sm" prominence="tertiary" icon={SvgTrash} aria-label={D.remove} tooltip={D.remove} onClick={() => onChange(rows.filter((_, i) => i !== index))} />
        </div>
      ))}
      <div>
        <Button
          size="sm"
          prominence="secondary"
          icon={SvgPlus}
          onClick={() => onChange([...rows, Object.fromEntries(fields.map((field) => [field.key, field.kind === "boolean" ? false : field.kind === "select" ? field.options[0]?.[0] ?? "" : ""]))])}
        >
          {D.addRow}
        </Button>
      </div>
    </div>
  );
}

export function WeekdaysInput({ value, options, onChange }: { value: number[]; options: [string, string][]; onChange: (value: number[]) => void }) {
  return (
    <div className="ton-auto-weekdays" role="group">
      {options.map(([key, text]) => {
        const day = Number(key);
        const active = value.includes(day);
        return (
          <button
            key={key}
            type="button"
            className="ton-auto-weekday ton-focusable"
            aria-pressed={active}
            data-active={active || undefined}
            onClick={() => onChange(active ? value.filter((item) => item !== day) : [...value, day].sort())}
          >
            {text.slice(0, 3)}
          </button>
        );
      })}
    </div>
  );
}

export function MultiToggle({ value, options, onChange }: { value: string[]; options: [string, string][]; onChange: (value: string[]) => void }) {
  return (
    <div className="ton-auto-weekdays" role="group">
      {options.map(([key, text]) => {
        const active = value.includes(key);
        return (
          <button
            key={key}
            type="button"
            className="ton-auto-weekday ton-auto-toggle ton-focusable"
            aria-pressed={active}
            data-active={active || undefined}
            onClick={() => onChange(active ? value.filter((item) => item !== key) : [...value, key])}
          >
            {text}
          </button>
        );
      })}
    </div>
  );
}
