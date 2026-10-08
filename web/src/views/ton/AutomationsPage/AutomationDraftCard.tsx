"use client";

import { useState } from "react";
import type { Route } from "next";
import { Button, Text } from "@opal/components";
import { SvgAlertTriangle, SvgCheckCircle, SvgEdit, SvgPlayCircle, SvgWorkflow } from "@opal/icons";
import { AUTOMATIONS_API, COPY, KIND_LABELS, send, type DraftResult } from "@/lib/ton/automations";

const CARD = {
  created: "Rascunho criado pelo TON — revise antes de ativar",
  updated: "Rascunho ajustado pelo TON",
  active: "Automação ativa",
  open: "Abrir no editor",
  activated: "Ativada",
};

export function isAutomationDraft(value: unknown): value is DraftResult {
  if (typeof value !== "object" || value === null) return false;
  const record: Record<string, unknown> = { ...value };
  return typeof record.automation_id === "string" && typeof record.name === "string" && Array.isArray(record.steps_text) && typeof record.editor_url === "string";
}

/** What TON shows in the chat after drafting an automation. */
export default function AutomationDraftCard({ draft }: { draft: DraftResult }) {
  const [status, setStatus] = useState(draft.status);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const active = status === "ACTIVE";
  const pending = [...draft.missing, ...draft.problems.filter((problem) => !draft.missing.includes(problem))];

  async function activate() {
    setBusy(true);
    setError(null);
    try {
      await send(`${AUTOMATIONS_API}/${draft.automation_id}/status`, { status: "ACTIVE" });
      setStatus("ACTIVE");
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : String(failure));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="ton-result-card flex flex-col gap-3 p-3">
      <div className="flex items-center gap-3">
        <span className="ton-icon-tile flex items-center justify-center w-8 h-8 shrink-0">
          <SvgWorkflow size={16} />
        </span>
        <span className="flex flex-1 min-w-0 flex-col">
          <Text font="main-ui-action" color="text-05">
            {draft.name}
          </Text>
          <Text font="secondary-body" color="text-03">
            {active ? CARD.active : draft.created ? CARD.created : CARD.updated}
          </Text>
        </span>
        <span className="ton-auto-kind-pill">{KIND_LABELS[draft.kind]}</span>
      </div>
      {draft.summary && (
        <Text font="secondary-body" color="text-04">
          {draft.summary}
        </Text>
      )}
      <div className="ton-auto-draft-steps">
        {draft.steps_text.map((line, index) => (
          <Text key={index} font="secondary-body" color="text-04">
            {line}
          </Text>
        ))}
      </div>
      {pending.length > 0 && !active && (
        <div className="flex flex-col gap-1">
          {pending.slice(0, 8).map((problem) => (
            <span key={problem} className="flex items-start gap-1.5">
              <SvgAlertTriangle size={14} className="shrink-0 mt-0.5" />
              <Text font="secondary-body" color="text-04">
                {problem}
              </Text>
            </span>
          ))}
        </div>
      )}
      {error && (
        <Text font="secondary-body" color="text-05">
          {error}
        </Text>
      )}
      <div className="flex flex-wrap gap-2">
        <Button prominence="secondary" icon={SvgEdit} href={draft.editor_url as Route}>
          {CARD.open}
        </Button>
        {active ? (
          <span className="flex items-center gap-1.5">
            <SvgCheckCircle size={14} className="ton-brand-text" />
            <Text font="secondary-action" color="text-04">
              {CARD.activated}
            </Text>
          </span>
        ) : (
          <Button icon={SvgPlayCircle} disabled={busy || draft.problems.length > 0} onClick={activate}>
            {COPY.activate}
          </Button>
        )}
      </div>
    </div>
  );
}
