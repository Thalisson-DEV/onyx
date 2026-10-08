"use client";

import { useCallback, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
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
        <span className="ton-auto-field-error">{error}</span>
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

export function typeLabel(type: string): string {
  return D.typeLabels[type] ?? D.typeLabels.any ?? type;
}

function GroupList({ group, query, onPick }: { group: DynamicGroup; query: string; onPick: (expression: string) => void }) {
  const [open, setOpen] = useState(true);
  const Icon = nodeIcon(group.icon);
  const items = group.items.filter((item) => !query || `${item.label} ${group.title}`.toLowerCase().includes(query.toLowerCase()));
  if (!items.length) return null;
  return (
    <div className="ton-auto-dyn-group" data-group={group.group}>
      <button type="button" className="ton-auto-dyn-head ton-focusable" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        <span className="ton-auto-dyn-icon">
          <Icon size={13} />
        </span>
        <span className="ton-auto-dyn-title">{group.title}</span>
        {open ? <SvgChevronDown size={14} /> : <SvgChevronRight size={14} />}
      </button>
      {open && (
        <ul>
          {items.map((item) => (
            <li key={item.expression}>
              <button type="button" className="ton-auto-dyn-item ton-focusable" onClick={() => onPick(item.expression)} title={item.description || undefined}>
                <span className="ton-auto-dyn-label">{item.label}</span>
                <span className="ton-auto-dyn-type">{typeLabel(item.type)}</span>
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
      <div className="ton-auto-dyn-top">
        <Text font="main-ui-action" color="text-05">
          {tab === "content" ? D.pickerTitle : D.expression}
        </Text>
        <button type="button" className="ton-auto-link ton-focusable" onClick={() => setTab(tab === "content" ? "expression" : "content")}>
          {tab === "content" ? D.expression : D.dynamicShort}
        </button>
      </div>
      {tab === "content" ? (
        <>
          <InputTypeIn searchIcon placeholder={D.searchData} value={query} onChange={(event) => setQuery(event.target.value)} />
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
          <Text font="secondary-body" color="text-03">
            {D.expressionHint}
          </Text>
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

// ---------------------------------------------------------------------------
// Token field: text where each {{ expression }} shows as a friendly chip
// ---------------------------------------------------------------------------

function escapeHtml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function tokenHtml(expression: string, label: string): string {
  return `<span class="ton-auto-token" contenteditable="false" data-expr="${escapeHtml(expression)}" title="${escapeHtml(label)}">${escapeHtml(label)}</span>`;
}

function renderTokens(value: string, describe: (expression: string) => string): string {
  return segments(value)
    .map((part) => (part.expression !== undefined ? tokenHtml(part.expression, describe(part.expression)) : escapeHtml(part.text).replace(/\n/g, "<br>")))
    .join("")
    .concat(value.endsWith("\n") ? "<br>" : "");
}

function serializeTokens(root: Node): string {
  let out = "";
  root.childNodes.forEach((child, index) => {
    if (child.nodeType === Node.TEXT_NODE) {
      out += (child.textContent ?? "").replace(/ /g, " ");
      return;
    }
    if (!(child instanceof HTMLElement)) return;
    if (child.dataset.expr !== undefined) {
      out += `{{ ${child.dataset.expr} }}`;
    } else if (child.tagName === "BR") {
      // A trailing <br> only keeps the empty last line visible.
      if (index < root.childNodes.length - 1) out += "\n";
    } else {
      const block = child.tagName === "DIV" || child.tagName === "P";
      if (block && out && !out.endsWith("\n")) out += "\n";
      out += serializeTokens(child);
    }
  });
  return out;
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

/** Text with dynamic data: the ⚡ button inserts a chip at the cursor. */
export function ExpressionInput({ value, onChange, context, label, placeholder, multiline, dynamic = true, invalid }: ExpressionInputProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const range = useRef<Range | null>(null);
  const describe = useCallback((expression: string) => describeExpression(expression, context.definition, context.catalog), [context.definition, context.catalog]);
  const html = useMemo(() => renderTokens(value, describe), [value, describe]);

  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return;
    const focused = document.activeElement === element;
    if (serializeTokens(element) !== value || (!focused && element.innerHTML !== html)) element.innerHTML = html;
  }, [value, html]);

  function remember() {
    const selection = window.getSelection();
    if (selection && selection.rangeCount && ref.current?.contains(selection.anchorNode)) range.current = selection.getRangeAt(0).cloneRange();
  }

  function emit() {
    if (ref.current) onChange(serializeTokens(ref.current));
  }

  function insert(expression: string) {
    const element = ref.current;
    setOpen(false);
    if (!element) return;
    const holder = document.createElement("span");
    holder.innerHTML = tokenHtml(expression, describe(expression));
    const token = holder.firstChild as HTMLElement;
    const space = document.createTextNode(" ");
    const at = range.current && element.contains(range.current.startContainer) ? range.current : null;
    if (at) {
      at.deleteContents();
      at.insertNode(space);
      at.insertNode(token);
    } else {
      element.append(token, space);
    }
    const selection = window.getSelection();
    const after = document.createRange();
    after.setStartAfter(space);
    after.collapse(true);
    selection?.removeAllRanges();
    selection?.addRange(after);
    range.current = after.cloneRange();
    emit();
  }

  const picker = dynamic && context.nodeId !== "trigger" && (
    <Popover open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <Button size="sm" prominence="tertiary" icon={SvgZap} tooltip={D.dynamic} aria-label={D.dynamic} onMouseDown={remember} />
      </Popover.Trigger>
      <Popover.Content width="xl" align="end">
        <DynamicPicker context={context} onPick={insert} />
      </Popover.Content>
    </Popover>
  );

  return (
    <div className="ton-auto-tokenfield" data-invalid={invalid || undefined} data-multiline={multiline || undefined}>
      <div
        ref={ref}
        className="ton-auto-tokenfield-input"
        contentEditable
        suppressContentEditableWarning
        role="textbox"
        aria-label={label}
        aria-multiline={multiline || undefined}
        aria-invalid={invalid || undefined}
        data-placeholder={placeholder ?? ""}
        tabIndex={0}
        onInput={emit}
        onKeyUp={remember}
        onMouseUp={remember}
        onBlur={remember}
        onKeyDown={(event) => {
          if (event.key !== "Enter") return;
          event.preventDefault();
          if (multiline) {
            document.execCommand("insertLineBreak");
            emit();
          }
        }}
        onPaste={(event) => {
          event.preventDefault();
          const text = event.clipboardData.getData("text/plain");
          document.execCommand("insertText", false, multiline ? text : text.replace(/\s*\n\s*/g, " "));
        }}
      />
      {picker && <span className="ton-auto-tokenfield-action">{picker}</span>}
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
          <Popover.Content width="xl" align="end">
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
