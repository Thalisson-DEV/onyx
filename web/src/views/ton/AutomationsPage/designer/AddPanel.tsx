"use client";

import { useMemo, useState } from "react";
import { Button, InputTypeIn, Text } from "@opal/components";
import { SvgX } from "@opal/icons";
import { DESIGNER_COPY as D, type CatalogView, type NodeTypeView } from "@/lib/ton/automations";
import { GROUP_ORDER, nodeIcon } from "@/views/ton/AutomationsPage/designer/icons";

interface AddPanelProps {
  catalog: CatalogView;
  mode: "action" | "trigger";
  onPick: (spec: NodeTypeView) => void;
  onClose: () => void;
  onDragState: (dragging: boolean) => void;
}

function normalize(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

function Item({ spec, draggable, onPick, onDragState }: { spec: NodeTypeView; draggable: boolean; onPick: () => void; onDragState: (dragging: boolean) => void }) {
  const Icon = nodeIcon(spec.icon);
  return (
    <button
      type="button"
      className="ton-auto-add-item ton-focusable"
      data-group={spec.group}
      draggable={draggable}
      onDragStart={(event) => {
        event.dataTransfer.setData("application/ton-node", `new:${spec.type}`);
        event.dataTransfer.effectAllowed = "copy";
        onDragState(true);
      }}
      onDragEnd={() => onDragState(false)}
      onClick={onPick}
      title={spec.description}
    >
      <span className="ton-auto-node-icon">
        <Icon size={16} />
      </span>
      <span className="flex min-w-0 flex-col items-start text-start">
        <span className="ton-auto-add-label">{spec.label}</span>
        <span className="ton-auto-add-desc">{spec.description}</span>
      </span>
    </button>
  );
}

export default function AddPanel({ catalog, mode, onPick, onClose, onDragState }: AddPanelProps) {
  const [query, setQuery] = useState("");
  const groups = useMemo(() => {
    const term = normalize(query.trim());
    const matches = catalog.nodes.filter((spec) => {
      if (mode === "trigger" ? !spec.is_trigger : spec.is_trigger) return false;
      if (!term) return true;
      return normalize(`${spec.label} ${spec.description} ${spec.keywords.join(" ")} ${catalog.groups[spec.group] ?? ""}`).includes(term);
    });
    if (mode === "trigger") return [{ key: "trigger", title: catalog.groups.trigger ?? D.trigger, items: matches }];
    return GROUP_ORDER.map((group) => ({ key: group, title: catalog.groups[group] ?? group, items: matches.filter((spec) => spec.group === group) })).filter(
      (group) => group.items.length
    );
  }, [catalog, mode, query]);

  return (
    <aside className="ton-auto-add" aria-label={mode === "trigger" ? D.addTrigger : D.addAction}>
      <header className="flex items-center justify-between gap-2">
        <Text font="main-ui-action" color="text-05">
          {mode === "trigger" ? D.addTrigger : D.addAction}
        </Text>
        <Button size="sm" prominence="tertiary" icon={SvgX} aria-label={D.closePanel} onClick={onClose} />
      </header>
      <InputTypeIn searchIcon placeholder={D.search} value={query} onChange={(event) => setQuery(event.target.value)} />
      <div className="ton-auto-add-list">
        {groups.length === 0 && (
          <Text font="secondary-body" color="text-03">
            {D.noResults}
          </Text>
        )}
        {groups.map((group) => (
          <section key={group.key} className="ton-auto-add-group">
            <Text font="secondary-action" color="text-04">
              {group.title}
            </Text>
            <div className="ton-auto-add-grid">
              {group.items.map((spec) => (
                <Item key={spec.type} spec={spec} draggable={mode === "action"} onPick={() => onPick(spec)} onDragState={onDragState} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </aside>
  );
}
