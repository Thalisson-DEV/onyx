/** Changes the TON chat proposes; only a person's click applies them. */

export const AGENT_ACTIONS_API = "/api/ton/agent/actions";

/** Window event a chat card fires to continue the conversation. */
export const TON_SEND_MESSAGE_EVENT = "ton:send-message";

export type AgentActionStatus =
  | "PROPOSED"
  | "APPLIED"
  | "CANCELLED"
  | "EXPIRED"
  | "UNDONE"
  | "FAILED";

export interface PreviewLine {
  label: string;
  antes: string | null;
  depois: string | null;
  total: boolean;
}

export interface ActionPreview {
  resumo: string[];
  escopo: string | null;
  linhas: PreviewLine[];
  avisos: string[];
  pode_desfazer: boolean;
}

export interface AgentAction {
  id: string;
  kind: string;
  title: string;
  status: AgentActionStatus;
  preview: ActionPreview;
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  decided_at: string | null;
  expires_at: string;
}

function isPreview(value: unknown): value is ActionPreview {
  if (typeof value !== "object" || value === null) return false;
  const preview: Record<string, unknown> = { ...value };
  return Array.isArray(preview.resumo) && Array.isArray(preview.linhas);
}

export function isAgentAction(value: unknown): value is AgentAction {
  if (typeof value !== "object" || value === null) return false;
  const action: Record<string, unknown> = { ...value };
  return (
    action.kind === "agent_action" &&
    typeof action.id === "string" &&
    typeof action.title === "string" &&
    typeof action.status === "string" &&
    isPreview(action.preview)
  );
}

async function readError(response: Response): Promise<string> {
  try {
    const body: { detail?: unknown } = await response.json();
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // fall through
  }
  return `HTTP ${response.status}`;
}

export async function decideAction(
  id: string,
  decision: "apply" | "cancel" | "undo"
): Promise<AgentAction> {
  const response = await fetch(`${AGENT_ACTIONS_API}/${id}/${decision}`, {
    method: "POST",
  });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

/** Continue the TON conversation with ``message`` as if the person typed it. */
export function sendTonMessage(message: string): void {
  window.dispatchEvent(
    new CustomEvent(TON_SEND_MESSAGE_EVENT, { detail: { message } })
  );
}
