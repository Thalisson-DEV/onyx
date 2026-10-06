"use client";

import { useState } from "react";
import type { Route } from "next";
import { Button, Text } from "@opal/components";
import { SvgAlertTriangle, SvgCheckCircle, SvgMail, SvgPlayCircle } from "@opal/icons";
import {
  EMAIL_FLOWS_API,
  EMAIL_FLOWS_COPY as COPY,
  sendJson,
  type DraftResult,
} from "@/lib/ton/emailFlows";

interface FlowDraftCardProps {
  draft: DraftResult;
}

/** What TON returns in the chat after drafting a flow: the steps in plain
 * language, what is still missing, and the two ways forward. */
export default function FlowDraftCard({ draft }: FlowDraftCardProps) {
  const [status, setStatus] = useState(draft.status);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const active = status === "ACTIVE";

  async function activate() {
    setBusy(true);
    setError(null);
    try {
      await sendJson(`${EMAIL_FLOWS_API}/${draft.flow_id}/activate`, {});
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
          <SvgMail size={16} />
        </span>
        <span className="flex flex-1 min-w-0 flex-col">
          <Text font="main-ui-action" color="text-05">
            {draft.name}
          </Text>
          <Text font="secondary-body" color="text-03">
            {active ? COPY.draftCard.active : COPY.draftCard.subtitle(draft.created)}
          </Text>
        </span>
      </div>
      <div className="ton-flow-draft-steps">
        <Text font="secondary-action" color="text-04">
          {`${COPY.editor.when}: ${draft.when}`}
        </Text>
        {draft.steps_text.map((line, index) => (
          <span key={index} style={{ paddingInlineStart: `${line.depth * 16}px` }}>
            <Text font="secondary-body" color="text-04">
              {line.text}
            </Text>
          </span>
        ))}
      </div>
      {draft.problems.length > 0 && !active && (
        <div className="flex flex-col gap-1">
          {draft.problems.map((problem) => (
            <span key={problem} className="flex items-start gap-1.5">
              <SvgAlertTriangle size={14} className="text-status-warning-05 shrink-0 mt-0.5" />
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
        <Button prominence="secondary" href={draft.editor_url as Route}>
          {COPY.draftCard.open}
        </Button>
        {active ? (
          <span className="flex items-center gap-1.5">
            <SvgCheckCircle size={14} className="ton-brand-text" />
            <Text font="secondary-action" color="text-04">
              {COPY.draftCard.activated}
            </Text>
          </span>
        ) : (
          <Button
            icon={SvgPlayCircle}
            disabled={busy || !draft.can_activate}
            onClick={activate}
          >
            {busy ? COPY.editor.saving : COPY.draftCard.activate}
          </Button>
        )}
      </div>
    </div>
  );
}
