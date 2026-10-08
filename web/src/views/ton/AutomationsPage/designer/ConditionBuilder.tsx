"use client";

import { Button, Text } from "@opal/components";
import { SvgPlus, SvgTrash } from "@opal/icons";
import { DESIGNER_COPY as D, type JsonValue } from "@/lib/ton/automations";
import { asText } from "@/lib/ton/automationTree";
import { ExpressionInput, Select, type DynamicContext } from "@/views/ton/AutomationsPage/designer/fields";

export interface Rule {
  left: string;
  operator: string;
  right: string;
}

export interface Group {
  op: "and" | "or";
  rules: (Rule | Group)[];
}

const UNARY = new Set(["empty", "not_empty", "is_true", "is_false"]);

function isGroup(value: Rule | Group): value is Group {
  return "rules" in value;
}

export function toGroup(raw: JsonValue | undefined): Group {
  if (raw && typeof raw === "object" && !Array.isArray(raw)) {
    const rules = Array.isArray(raw.rules) ? raw.rules : [];
    return {
      op: raw.op === "or" ? "or" : "and",
      rules: rules.map((rule) =>
        rule && typeof rule === "object" && !Array.isArray(rule) && "rules" in rule
          ? toGroup(rule)
          : {
              left: asText(rule && typeof rule === "object" && !Array.isArray(rule) ? rule.left : ""),
              operator: asText(rule && typeof rule === "object" && !Array.isArray(rule) ? rule.operator : "eq") || "eq",
              right: asText(rule && typeof rule === "object" && !Array.isArray(rule) ? rule.right : ""),
            }
      ),
    };
  }
  return { op: "and", rules: [] };
}

export function fromGroup(group: Group): JsonValue {
  return {
    op: group.op,
    rules: group.rules.map((rule) => (isGroup(rule) ? fromGroup(rule) : { left: rule.left, operator: rule.operator, right: rule.right })),
  };
}

interface GroupEditorProps {
  group: Group;
  operators: [string, string][];
  context: DynamicContext;
  depth: number;
  onChange: (group: Group) => void;
  onRemove?: () => void;
}

function GroupEditor({ group, operators, context, depth, onChange, onRemove }: GroupEditorProps) {
  function setRule(index: number, rule: Rule | Group) {
    onChange({ ...group, rules: group.rules.map((item, i) => (i === index ? rule : item)) });
  }
  function remove(index: number) {
    onChange({ ...group, rules: group.rules.filter((_, i) => i !== index) });
  }
  return (
    <div className="ton-auto-cond-group" data-depth={depth}>
      {group.rules.length > 1 && (
        <div className="ton-auto-cond-op" role="group">
          {(["and", "or"] as const).map((op) => (
            <button key={op} type="button" className="ton-focusable" aria-pressed={group.op === op} data-active={group.op === op || undefined} onClick={() => onChange({ ...group, op })}>
              {op === "and" ? D.and : D.or}
            </button>
          ))}
        </div>
      )}
      {group.rules.map((rule, index) =>
        isGroup(rule) ? (
          <GroupEditor
            key={index}
            group={rule}
            operators={operators}
            context={context}
            depth={depth + 1}
            onChange={(next) => setRule(index, next)}
            onRemove={() => remove(index)}
          />
        ) : (
          <div key={index} className="ton-auto-cond-rule">
            {index > 0 && (
              <Text font="secondary-action" color="text-03">
                {group.op === "and" ? D.and : D.or}
              </Text>
            )}
            <div className="ton-auto-cond-fields">
              <ExpressionInput value={rule.left} onChange={(left) => setRule(index, { ...rule, left })} context={context} label={D.dynamic} placeholder="{{ steps.x.outputs.count }}" />
              <Select value={rule.operator} label={D.expression} options={operators} onChange={(operator) => setRule(index, { ...rule, operator })} />
              {!UNARY.has(rule.operator) && (
                <ExpressionInput value={rule.right} onChange={(right) => setRule(index, { ...rule, right })} context={context} label={D.caseValue} placeholder="0" />
              )}
            </div>
            <Button size="sm" prominence="tertiary" icon={SvgTrash} aria-label={D.removeRule} tooltip={D.removeRule} onClick={() => remove(index)} />
          </div>
        )
      )}
      <div className="flex flex-wrap gap-1">
        <Button size="sm" prominence="secondary" icon={SvgPlus} onClick={() => onChange({ ...group, rules: [...group.rules, { left: "", operator: "eq", right: "" }] })}>
          {D.addRule}
        </Button>
        {depth < 3 && (
          <Button size="sm" prominence="tertiary" icon={SvgPlus} onClick={() => onChange({ ...group, rules: [...group.rules, { op: "and", rules: [{ left: "", operator: "eq", right: "" }] }] })}>
            {D.addGroup}
          </Button>
        )}
        {onRemove && <Button size="sm" prominence="tertiary" icon={SvgTrash} aria-label={D.remove} onClick={onRemove} />}
      </div>
    </div>
  );
}

interface ConditionBuilderProps {
  value: JsonValue | undefined;
  operators: Record<string, string>;
  context: DynamicContext;
  onChange: (value: JsonValue) => void;
}

export default function ConditionBuilder({ value, operators, context, onChange }: ConditionBuilderProps) {
  const group = toGroup(value);
  return (
    <GroupEditor
      group={group}
      operators={Object.entries(operators)}
      context={context}
      depth={0}
      onChange={(next) => onChange(fromGroup(next))}
    />
  );
}
