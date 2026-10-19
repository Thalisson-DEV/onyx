"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Button, InputTypeIn, Text } from "@opal/components";
import {
  SvgArrowUp,
  SvgPlus,
  SvgTrash,
  SvgX,
} from "@opal/icons";
import { cn } from "@opal/utils";
import { COPY } from "@/lib/ton/copy";
import { TonApiError, postTonJson } from "@/lib/ton/decisions";
import { getBusinessLabel } from "@/lib/ton/labels";
import { StatusPill } from "@/views/ton/components/ui";
import StructureHistory from "@/views/ton/DrePage/StructureHistory";

const T = COPY.dre.editor;

/** A DRE line as the structure API stores it, formula included. */
export interface EditableLine {
  code: string;
  label: string;
  position: number;
  parent_code: string | null;
  line_type: "SOURCE_SUM" | "CALCULATED" | "SUBTOTAL" | "RESULT" | "PERCENTAGE";
  operation?: "SUM_LINES" | "SUM_CHILDREN" | "SUBTRACT" | "RATIO" | null;
  operands?: string[];
  hidden?: boolean;
  excluded?: boolean;
}

export interface EditableVersion {
  id: string;
  number: number;
  lines: EditableLine[];
  assignments: Array<{
    account_id: string;
    line_code: string;
    status: string;
  }>;
}

type Kind = "group" | "nature" | "total";

function kindOf(line: EditableLine): Kind {
  if (line.line_type === "SOURCE_SUM") return "nature";
  if (line.line_type === "SUBTOTAL" && line.operation === "SUM_CHILDREN")
    return "group";
  return "total";
}

interface Draft {
  lines: Record<string, EditableLine>;
  top: string[];
  children: Record<string, string[]>;
}

function toDraft(version: EditableVersion): Draft {
  const sorted = [...version.lines].sort((a, b) => a.position - b.position);
  const children: Record<string, string[]> = {};
  const top: string[] = [];
  for (const line of sorted) {
    if (line.parent_code) {
      (children[line.parent_code] ??= []).push(line.code);
    } else {
      top.push(line.code);
    }
  }
  return {
    lines: Object.fromEntries(
      sorted.map((line) => [
        line.code,
        {
          ...line,
          operands: line.operands ?? [],
          hidden: line.hidden ?? false,
          excluded: line.excluded ?? false,
        },
      ])
    ),
    top,
    children,
  };
}

/** Lines in display order with fresh, unique positions. */
function flatten(draft: Draft): EditableLine[] {
  const result: EditableLine[] = [];
  function walk(code: string) {
    const line = draft.lines[code];
    if (!line) return;
    result.push({ ...line, position: result.length + 1 });
    for (const child of draft.children[code] ?? []) walk(child);
  }
  for (const code of draft.top) walk(code);
  return result;
}

function move<T>(items: T[], index: number, delta: number): T[] {
  const target = index + delta;
  if (target < 0 || target >= items.length) return items;
  const next = [...items];
  const [item] = next.splice(index, 1);
  if (item === undefined) return items;
  next.splice(target, 0, item);
  return next;
}

/** Totals that read a line directly in their formula. */
function totalsUsing(draft: Draft, code: string): string[] {
  return Object.values(draft.lines)
    .filter(
      (line) => kindOf(line) === "total" && (line.operands ?? []).includes(code)
    )
    .map((line) => line.code);
}

function problemsOf(draft: Draft): string[] {
  const problems: string[] = [];
  for (const code of draft.top) {
    const line = draft.lines[code];
    if (!line) continue;
    if (!line.label.trim()) problems.push(T.problems.emptyName);
    if (kindOf(line) === "group" && !(draft.children[code] ?? []).length)
      problems.push(T.problems.emptyGroup(line.label || T.newGroup));
    if (kindOf(line) === "total" && line.operation === "SUM_LINES") {
      if (!(line.operands ?? []).length)
        problems.push(T.problems.emptyTotal(line.label));
    }
  }
  return [...new Set(problems)];
}

export default function StructureEditor({
  structureId,
  version,
  onClose,
  onSaved,
}: {
  structureId: string;
  version: EditableVersion;
  onClose: () => void;
  onSaved: (number: number) => Promise<void>;
}) {
  const [draft, setDraft] = useState<Draft>(() => toDraft(version));
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [tab, setTab] = useState<"structure" | "history">("structure");
  const closeRef = useRef<HTMLButtonElement>(null);
  const original = useMemo(
    () => JSON.stringify(flatten(toDraft(version))),
    [version]
  );
  const changed = JSON.stringify(flatten(draft)) !== original;
  const problems = problemsOf(draft);
  const groups = draft.top.filter((code) => {
    const line = draft.lines[code];
    return line && kindOf(line) === "group";
  });

  useEffect(() => {
    closeRef.current?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape" && !saving) onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, saving]);

  function update(code: string, patch: Partial<EditableLine>) {
    setDraft((old) => {
      const line = old.lines[code];
      if (!line) return old;
      return { ...old, lines: { ...old.lines, [code]: { ...line, ...patch } } };
    });
  }

  function moveTop(code: string, delta: number) {
    setDraft((old) => ({
      ...old,
      top: move(old.top, old.top.indexOf(code), delta),
    }));
  }

  function moveChild(parent: string, code: string, delta: number) {
    setDraft((old) => {
      const siblings = old.children[parent] ?? [];
      return {
        ...old,
        children: {
          ...old.children,
          [parent]: move(siblings, siblings.indexOf(code), delta),
        },
      };
    });
  }

  function regroup(code: string, from: string, to: string) {
    if (from === to) return;
    setDraft((old) => {
      const line = old.lines[code];
      if (!line) return old;
      return {
        ...old,
        lines: { ...old.lines, [code]: { ...line, parent_code: to } },
        children: {
          ...old.children,
          [from]: (old.children[from] ?? []).filter((item) => item !== code),
          [to]: [...(old.children[to] ?? []), code],
        },
      };
    });
  }

  /** In the result: the first total below the group sums it. */
  function setInResult(code: string, inResult: boolean) {
    setDraft((old) => {
      const lines = { ...old.lines };
      if (!inResult) {
        for (const total of totalsUsing(old, code)) {
          const line = lines[total];
          if (line)
            lines[total] = {
              ...line,
              operands: (line.operands ?? []).filter((item) => item !== code),
            };
        }
        return { ...old, lines };
      }
      const index = old.top.indexOf(code);
      const below = old.top
        .slice(index + 1)
        .find((item) => {
          const line = old.lines[item];
          return line && kindOf(line) === "total" && line.operation === "SUM_LINES";
        });
      const target =
        below ??
        [...old.top].reverse().find((item) => {
          const line = old.lines[item];
          return line && kindOf(line) === "total" && line.operation === "SUM_LINES";
        });
      const line = target ? lines[target] : undefined;
      if (!target || !line) return old;
      lines[target] = { ...line, operands: [...(line.operands ?? []), code] };
      return { ...old, lines };
    });
  }

  function addGroup() {
    setDraft((old) => {
      const numbers = Object.keys(old.lines)
        .map((code) => /^g(\d+)$/.exec(code)?.[1])
        .filter((value): value is string => Boolean(value))
        .map(Number);
      const code = `g${Math.max(0, ...numbers) + 1}`;
      return {
        ...old,
        lines: {
          ...old.lines,
          [code]: {
            code,
            label: T.newGroup,
            position: 0,
            parent_code: null,
            line_type: "SUBTOTAL",
            operation: "SUM_CHILDREN",
            operands: [],
          },
        },
        top: [...old.top, code],
        children: { ...old.children, [code]: [] },
      };
    });
  }

  function removeGroup(code: string) {
    setDraft((old) => {
      const lines = { ...old.lines };
      delete lines[code];
      for (const total of totalsUsing(old, code)) {
        const line = lines[total];
        if (line)
          lines[total] = {
            ...line,
            operands: (line.operands ?? []).filter((item) => item !== code),
          };
      }
      return {
        ...old,
        lines,
        top: old.top.filter((item) => item !== code),
      };
    });
  }

  async function save() {
    setSaving(true);
    setFailure(null);
    try {
      const saved = await postTonJson<{ number: number }>(
        `/api/ton/dre/structures/${structureId}/versions`,
        {
          lines: flatten(draft),
          assignments: version.assignments,
          reason: reason.trim() || T.defaultReason,
        }
      );
      await onSaved(saved.number);
    } catch (error) {
      setFailure(
        error instanceof TonApiError && error.detail
          ? T.failedWithDetail(getBusinessLabel(error.detail))
          : T.failed
      );
    } finally {
      setSaving(false);
    }
  }

  function OrderButtons({
    onUp,
    onDown,
    first,
    last,
    label,
  }: {
    onUp: () => void;
    onDown: () => void;
    first: boolean;
    last: boolean;
    label: string;
  }) {
    return (
      <span className="flex gap-0.5">
        <button
          type="button"
          className="ton-focusable ton-icon-button"
          aria-label={T.moveUp(label)}
          disabled={first}
          onClick={onUp}
        >
          <SvgArrowUp size={14} />
        </button>
        <button
          type="button"
          className="ton-focusable ton-icon-button"
          aria-label={T.moveDown(label)}
          disabled={last}
          onClick={onDown}
        >
          <SvgArrowUp size={14} className="rotate-180" />
        </button>
      </span>
    );
  }

  return (
    <>
      <div
        aria-hidden
        className="ton-scrim fixed inset-0 z-40"
        onClick={() => !saving && onClose()}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="ton-structure-title"
        className="ton-drawer fixed inset-y-0 end-0 z-50 flex flex-col w-full lg:w-[min(980px,calc(100vw-6rem))]"
      >
        <header className="flex items-start justify-between gap-4 px-6 pt-5 pb-4 border-b border-01">
          <div className="flex flex-col gap-1 min-w-0">
            <span className="ton-eyebrow">{T.eyebrow(version.number)}</span>
            <Text
              as="h2"
              id="ton-structure-title"
              font="heading-h2"
              color="text-05"
            >
              {T.title}
            </Text>
            <Text font="secondary-body" color="text-03">
              {T.description}
            </Text>
          </div>
          <Button
            ref={closeRef}
            icon={SvgX}
            prominence="tertiary"
            aria-label={T.close}
            disabled={saving}
            onClick={onClose}
          />
        </header>
        <div
          role="tablist"
          aria-label={T.title}
          className="flex gap-1 px-6 pt-2 border-b border-01"
        >
          {(["structure", "history"] as const).map((item) => (
            <button
              key={item}
              type="button"
              role="tab"
              aria-selected={tab === item}
              className={cn(
                "ton-focusable px-3 py-2 -mb-px border-b-2",
                tab === item ? "border-text-05" : "border-transparent"
              )}
              onClick={() => setTab(item)}
            >
              <Text
                font="secondary-action"
                color={tab === item ? "text-05" : "text-03"}
              >
                {T.tabs[item]}
              </Text>
            </button>
          ))}
        </div>
        {tab === "history" ? (
          <div className="flex-1 overflow-auto px-6 py-4">
            <StructureHistory
              structureId={structureId}
              currentNumber={version.number}
              onRestored={onSaved}
            />
          </div>
        ) : (
          <>
        <div className="flex-1 overflow-auto px-6 py-4">
          <table className="ton-structure w-full border-collapse">
            <thead>
              <tr>
                <th scope="col" className="w-16">
                  {T.columns.order}
                </th>
                <th scope="col">{T.columns.line}</th>
                <th scope="col" className="w-48">
                  {T.columns.group}
                </th>
                <th scope="col" className="w-40">
                  {T.columns.result}
                </th>
                <th scope="col" className="w-32">
                  {T.columns.shown}
                </th>
                <th scope="col" className="w-10">
                  <span className="sr-only">{T.columns.remove}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {draft.top.map((code, topIndex) => {
                const line = draft.lines[code];
                if (!line) return null;
                const kind = kindOf(line);
                const kids = draft.children[code] ?? [];
                const inResult = totalsUsing(draft, code).length > 0;
                return [
                  <tr key={code} data-kind={kind}>
                    <td>
                      <OrderButtons
                        label={line.label}
                        first={topIndex === 0}
                        last={topIndex === draft.top.length - 1}
                        onUp={() => moveTop(code, -1)}
                        onDown={() => moveTop(code, 1)}
                      />
                    </td>
                    <td>
                      <span className="flex items-center gap-2">
                        <span className="flex-1 min-w-0">
                          <InputTypeIn
                            value={line.label}
                            aria-label={T.rename(line.label)}
                            onChange={(event) =>
                              update(code, { label: event.target.value })
                            }
                          />
                        </span>
                        <StatusPill tone={kind === "total" ? "brand" : "neutral"}>
                          {T.kinds[kind]}
                        </StatusPill>
                      </span>
                    </td>
                    <td aria-hidden="true" />
                    <td>
                      {kind === "group" && (
                        <label className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            className="ton-checkbox"
                            checked={inResult}
                            onChange={(event) =>
                              setInResult(code, event.target.checked)
                            }
                          />
                          <Text font="secondary-body" color="text-04">
                            {inResult ? T.inResult : T.outOfResult}
                          </Text>
                        </label>
                      )}
                      {kind === "group" && inResult && line.hidden && (
                        <span className="block text-status-warning-05">
                          <Text font="secondary-body" color="inherit">
                            {T.hiddenButSummed}
                          </Text>
                        </span>
                      )}
                      {kind === "total" && (
                        <Text font="secondary-body" color="text-03">
                          {(line.operands ?? [])
                            .map((item) =>
                              getBusinessLabel(draft.lines[item]?.label ?? item)
                            )
                            .join(" + ")}
                        </Text>
                      )}
                    </td>
                    <td>
                      {kind === "group" && (
                        <label className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            className="ton-checkbox"
                            checked={!line.hidden}
                            onChange={(event) =>
                              update(code, { hidden: !event.target.checked })
                            }
                          />
                          <Text font="secondary-body" color="text-04">
                            {line.hidden ? T.hidden : T.shown}
                          </Text>
                        </label>
                      )}
                    </td>
                    <td>
                      {kind === "group" && kids.length === 0 && (
                        <button
                          type="button"
                          className="ton-focusable ton-icon-button"
                          aria-label={T.remove(line.label)}
                          onClick={() => removeGroup(code)}
                        >
                          <SvgTrash size={14} />
                        </button>
                      )}
                    </td>
                  </tr>,
                  ...kids.map((child, childIndex) => {
                    const nature = draft.lines[child];
                    if (!nature) return null;
                    return (
                      <tr key={child} data-kind="nature">
                        <td>
                          <OrderButtons
                            label={nature.label}
                            first={childIndex === 0}
                            last={childIndex === kids.length - 1}
                            onUp={() => moveChild(code, child, -1)}
                            onDown={() => moveChild(code, child, 1)}
                          />
                        </td>
                        <td>
                          <span className="ton-structure-child">
                            <InputTypeIn
                              value={nature.label}
                              aria-label={T.rename(nature.label)}
                              onChange={(event) =>
                                update(child, { label: event.target.value })
                              }
                            />
                          </span>
                        </td>
                        <td>
                          <select
                            className={cn("ton-select ton-focusable")}
                            aria-label={T.moveTo(nature.label)}
                            value={code}
                            onChange={(event) =>
                              regroup(child, code, event.target.value)
                            }
                          >
                            {groups.map((group) => (
                              <option key={group} value={group}>
                                {getBusinessLabel(
                                  draft.lines[group]?.label ?? group
                                )}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td>
                          <label
                            className="flex items-center gap-2"
                            title={T.natureOutHint}
                          >
                            <input
                              type="checkbox"
                              className="ton-checkbox"
                              checked={!nature.excluded}
                              onChange={(event) =>
                                update(child, { excluded: !event.target.checked })
                              }
                            />
                            <Text
                              font="secondary-body"
                              color={nature.excluded ? "status-error-05" : "text-04"}
                            >
                              {nature.excluded
                                ? T.natureOutOfGroup
                                : T.natureInGroup}
                            </Text>
                          </label>
                        </td>
                        <td>
                          <label className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              className="ton-checkbox"
                              checked={!nature.hidden}
                              onChange={(event) =>
                                update(child, { hidden: !event.target.checked })
                              }
                            />
                            <Text font="secondary-body" color="text-04">
                              {nature.hidden ? T.hidden : T.shown}
                            </Text>
                          </label>
                        </td>
                        <td aria-hidden="true" />
                      </tr>
                    );
                  }),
                ];
              })}
            </tbody>
          </table>
          <div className="pt-3">
            <Button prominence="secondary" icon={SvgPlus} onClick={addGroup}>
              {T.addGroup}
            </Button>
          </div>
        </div>
        <footer className="flex flex-col gap-3 px-6 py-4 border-t border-01">
          {problems.length > 0 && (
            <ul className="flex flex-col gap-0.5" role="status">
              {problems.map((problem) => (
                <li key={problem}>
                  <Text font="secondary-body" color="text-05">
                    {problem}
                  </Text>
                </li>
              ))}
            </ul>
          )}
          {failure && (
            <Text font="secondary-body" color="status-error-05">
              {failure}
            </Text>
          )}
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1 flex-1 min-w-[16rem]">
              <Text font="secondary-action" color="text-04">
                {T.reason}
              </Text>
              <InputTypeIn
                value={reason}
                placeholder={T.reasonPlaceholder}
                aria-label={T.reason}
                onChange={(event) => setReason(event.target.value)}
              />
            </label>
            <Button prominence="tertiary" disabled={saving} onClick={onClose}>
              {T.cancel}
            </Button>
            <Button
              disabled={saving || !changed || problems.length > 0}
              onClick={() => void save()}
            >
              {saving ? T.saving : T.save}
            </Button>
          </div>
          <Text font="secondary-body" color="text-03">
            {T.afterSave}
          </Text>
        </footer>
          </>
        )}
      </aside>
    </>
  );
}
