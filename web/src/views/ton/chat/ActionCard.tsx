"use client";

import { useState } from "react";
import useSWR from "swr";
import { Button, Text } from "@opal/components";
import {
  SvgAlertTriangle,
  SvgCheck,
  SvgCheckCircle,
  SvgEdit,
  SvgRevert,
  SvgX,
} from "@opal/icons";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { formatAmount } from "@/lib/ton/copy";
import {
  AGENT_ACTIONS_API,
  type AgentAction,
  type AgentActionStatus,
  decideAction,
  sendTonMessage,
} from "@/lib/ton/agent-actions";

const CARD = {
  proposed: "Proposta do TON — nada muda até você aplicar",
  applied: "Aplicada",
  cancelled: "Cancelada",
  expired: "Expirou; peça ao TON para propor de novo",
  undone: "Desfeita",
  failed: "Não foi possível aplicar",
  apply: "Aplicar",
  applying: "Aplicando…",
  cancel: "Cancelar",
  undo: "Desfazer",
  undoing: "Desfazendo…",
  line: "Linha",
  before: "Antes",
  after: "Depois",
  appliedMessage: (title: string) =>
    `Ação aplicada: ${title}. Mostre como ficou.`,
  undoneMessage: (title: string) => `Ação desfeita: ${title}.`,
};

const STATUS_TEXT: Record<AgentActionStatus, string> = {
  PROPOSED: CARD.proposed,
  APPLIED: CARD.applied,
  CANCELLED: CARD.cancelled,
  EXPIRED: CARD.expired,
  UNDONE: CARD.undone,
  FAILED: CARD.failed,
};

interface ActionCardProps {
  action: AgentAction;
}

/** A change TON proposed, with the DRE before and after and the decision buttons. */
export default function ActionCard({ action: proposed }: ActionCardProps) {
  // The card lives in the chat history: read the current state, not the
  // state at the moment the proposal was made.
  const { data, mutate } = useSWR<AgentAction>(
    `${AGENT_ACTIONS_API}/${proposed.id}`,
    errorHandlingFetcher,
    { fallbackData: proposed, revalidateOnFocus: false }
  );
  const action = data ?? proposed;
  const [busy, setBusy] = useState<"apply" | "cancel" | "undo" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { preview } = action;

  async function decide(decision: "apply" | "cancel" | "undo") {
    setBusy(decision);
    setError(null);
    try {
      const updated = await decideAction(action.id, decision);
      await mutate(updated, { revalidate: false });
      if (decision === "apply" && updated.status === "APPLIED")
        sendTonMessage(CARD.appliedMessage(updated.title));
      if (decision === "undo" && updated.status === "UNDONE")
        sendTonMessage(CARD.undoneMessage(updated.title));
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : String(failure));
    } finally {
      setBusy(null);
    }
  }

  const proposedNow = action.status === "PROPOSED";
  const failure = error ?? action.error;
  const changed = (line: AgentAction["preview"]["linhas"][number]) =>
    line.antes !== line.depois;

  return (
    <div
      className="ton-result-card ton-action-card flex flex-col gap-3 p-3"
      data-status={action.status}
    >
      <div className="flex items-center gap-3">
        <span
          className="ton-icon-tile flex items-center justify-center w-8 h-8 shrink-0"
          data-tone={proposedNow ? "gold" : undefined}
        >
          {action.status === "APPLIED" ? (
            <SvgCheckCircle size={16} />
          ) : (
            <SvgEdit size={16} />
          )}
        </span>
        <span className="flex flex-1 min-w-0 flex-col">
          <Text font="main-ui-action" color="text-05">
            {action.title}
          </Text>
          <Text font="secondary-body" color="text-03">
            {[STATUS_TEXT[action.status], preview.escopo]
              .filter(Boolean)
              .join(" · ")}
          </Text>
        </span>
      </div>

      {preview.resumo.length > 0 && (
        <ul className="ton-action-summary flex flex-col gap-1">
          {preview.resumo.map((item, index) => (
            <li key={index}>
              <Text font="secondary-body" color="text-04">
                {item}
              </Text>
            </li>
          ))}
        </ul>
      )}

      {preview.linhas.length > 0 && (
        <table className="ton-action-table">
          <thead>
            <tr>
              <th>
                <Text font="secondary-action" color="text-03">
                  {CARD.line}
                </Text>
              </th>
              <th>
                <Text font="secondary-action" color="text-03">
                  {CARD.before}
                </Text>
              </th>
              <th>
                <Text font="secondary-action" color="text-03">
                  {CARD.after}
                </Text>
              </th>
            </tr>
          </thead>
          <tbody>
            {preview.linhas.map((line, index) => (
              <tr
                key={`${line.label}-${index}`}
                data-total={line.total || undefined}
                data-changed={changed(line) || undefined}
              >
                <td>
                  <Text
                    font={line.total ? "secondary-action" : "secondary-body"}
                    color="text-04"
                  >
                    {line.label}
                  </Text>
                </td>
                <td>
                  <Text font="secondary-mono" color="text-03">
                    {formatAmount(line.antes)}
                  </Text>
                </td>
                <td>
                  <Text
                    font="secondary-mono"
                    color={changed(line) ? "text-05" : "text-03"}
                  >
                    {formatAmount(line.depois)}
                  </Text>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {(proposedNow ? preview.avisos : []).map((item) => (
        <span key={item} className="flex items-start gap-1.5">
          <SvgAlertTriangle size={14} className="shrink-0 mt-0.5" />
          <Text font="secondary-body" color="text-03">
            {item}
          </Text>
        </span>
      ))}

      {failure && (
        <Text font="secondary-body" color="text-05">
          {failure}
        </Text>
      )}

      {proposedNow && (
        <div className="flex flex-wrap gap-2">
          <Button
            icon={SvgCheck}
            disabled={busy !== null}
            onClick={() => decide("apply")}
          >
            {busy === "apply" ? CARD.applying : CARD.apply}
          </Button>
          <Button
            prominence="secondary"
            icon={SvgX}
            disabled={busy !== null}
            onClick={() => decide("cancel")}
          >
            {CARD.cancel}
          </Button>
        </div>
      )}
      {action.status === "APPLIED" && preview.pode_desfazer && (
        <div className="flex flex-wrap gap-2">
          <Button
            prominence="secondary"
            icon={SvgRevert}
            disabled={busy !== null}
            onClick={() => decide("undo")}
          >
            {busy === "undo" ? CARD.undoing : CARD.undo}
          </Button>
        </div>
      )}
    </div>
  );
}
