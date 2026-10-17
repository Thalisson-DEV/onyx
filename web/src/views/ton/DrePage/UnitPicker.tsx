"use client";

import { useEffect, useRef, useState } from "react";
import { Button, Text } from "@opal/components";
import { SvgChevronDown, SvgX } from "@opal/icons";
import { cn } from "@opal/utils";
import { COPY } from "@/lib/ton/copy";
import { getBusinessLabel } from "@/lib/ton/labels";
import {
  CONSOLIDATED,
  type DreWorkspace,
} from "@/views/ton/DrePage/useDreWorkspace";

const T = COPY.dre.units;

/**
 * Consolidated, one unit, or a set of units added together (for example the
 * operating units without the central administration).
 */
export default function UnitPicker({ dre }: { dre: DreWorkspace }) {
  const [open, setOpen] = useState(false);
  const current =
    dre.multi
      ? dre.unitSet
      : dre.unitId && dre.unitId !== CONSOLIDATED
        ? [dre.unitId]
        : [];
  const [draft, setDraft] = useState<string[]>(current);
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    function onClick(event: MouseEvent) {
      if (!panel.current?.contains(event.target as Node)) setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onClick);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onClick);
    };
  }, [open]);

  const nameOf = (id: string) => {
    const unit = dre.units.find((item) => item.id === id);
    return getBusinessLabel(unit?.name ?? unit?.code ?? id);
  };
  const label = dre.multi
    ? T.many(dre.unitSet.length)
    : current[0]
      ? nameOf(current[0])
      : COPY.dre.consolidated;
  const operational = dre.units
    .filter((unit) => unit.kind === "OPERATIONAL")
    .map((unit) => unit.id);

  function apply(ids: string[]) {
    setOpen(false);
    if (ids.length === 0) dre.select.unit(CONSOLIDATED);
    else dre.select.units(ids);
  }

  return (
    <div className="relative flex flex-col gap-1 min-w-56" ref={panel}>
      <span className="ton-eyebrow">{COPY.dre.scope}</span>
      <span className="flex items-center gap-1">
        <button
          type="button"
          aria-haspopup="dialog"
          aria-expanded={open}
          className="ton-focusable ton-picker-trigger flex-1"
          onClick={() => {
            setDraft(current);
            setOpen((value) => !value);
          }}
        >
          <span className="truncate">{label}</span>
          <SvgChevronDown size={14} className="shrink-0 text-text-03" />
        </button>
        {current.length > 0 && (dre.access.isAdmin || dre.multi) && (
          <button
            type="button"
            className="ton-focusable ton-icon-button"
            aria-label={T.reset}
            title={T.reset}
            onClick={() =>
              dre.access.isAdmin
                ? dre.select.unit(CONSOLIDATED)
                : dre.select.units(current.slice(0, 1))
            }
          >
            <SvgX size={14} />
          </button>
        )}
      </span>
      {open && (
        <div role="dialog" aria-label={T.title} className="ton-picker-panel">
          {dre.access.isAdmin && (
            <button
              type="button"
              className={cn(
                "ton-focusable ton-picker-row",
                current.length === 0 && "is-current"
              )}
              onClick={() => apply([])}
            >
              <Text font="main-ui-action" color="text-05">
                {T.consolidated}
              </Text>
            </button>
          )}
          <div className="flex items-center justify-between gap-2 px-2 pt-2">
            <span className="ton-eyebrow">{T.pick}</span>
            <span className="flex gap-1">
              {operational.length > 1 && (
                <button
                  type="button"
                  className="ton-focusable ton-link-button"
                  title={T.operationalHint}
                  onClick={() => setDraft(operational)}
                >
                  {T.operational(operational.length)}
                </button>
              )}
              {draft.length > 0 && (
                <button
                  type="button"
                  className="ton-focusable ton-link-button"
                  onClick={() => setDraft([])}
                >
                  {T.clear}
                </button>
              )}
            </span>
          </div>
          <ul className="ton-picker-list">
            {dre.units.map((unit) => {
              const checked = draft.includes(unit.id);
              return (
                <li key={unit.id}>
                  <label className="ton-picker-row">
                    <input
                      type="checkbox"
                      className="ton-checkbox"
                      checked={checked}
                      onChange={() =>
                        setDraft((old) =>
                          checked
                            ? old.filter((id) => id !== unit.id)
                            : [...old, unit.id]
                        )
                      }
                    />
                    <Text font="main-ui-body" color="text-05">
                      {getBusinessLabel(unit.name ?? unit.code)}
                    </Text>
                  </label>
                </li>
              );
            })}
          </ul>
          <div className="flex items-center justify-between gap-2 border-t border-01 p-2">
            <Text font="secondary-body" color="text-03">
              {draft.length > 1 ? T.sumHint(draft.length) : T.oneHint}
            </Text>
            <Button size="sm" disabled={draft.length === 0} onClick={() => apply(draft)}>
              {T.apply}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
