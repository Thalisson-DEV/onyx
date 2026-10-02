import { PacketType } from "@/app/app/services/streamingModels";
import type { TransformedStep } from "@/app/app/message/messageComponents/timeline/transformers";
import type { ToolSnapshot } from "@/lib/tools/types";
import { TON_TOOL_NAMES } from "@/lib/ton/labels";

export function getTonToolKey(
  step: TransformedStep,
  tools: ToolSnapshot[]
): string | null {
  for (const packet of step.packets) {
    const object = packet.obj;
    if (
      object.type !== PacketType.CUSTOM_TOOL_START &&
      object.type !== PacketType.CUSTOM_TOOL_DELTA
    )
      continue;
    const tool = tools.find((item) => item.id === object.tool_id);
    if (tool) return tool.name.startsWith("ton_") ? tool.name : null;
    if (object.tool_name.startsWith("ton_")) return object.tool_name;
    return (
      Object.entries(TON_TOOL_NAMES).find(
        ([, label]) => label === object.tool_name
      )?.[0] ?? null
    );
  }
  return null;
}

const QUIET_PACKETS = new Set<string>([
  PacketType.REASONING_START,
  PacketType.REASONING_DELTA,
  PacketType.REASONING_DONE,
  PacketType.SECTION_END,
]);

/**
 * True when the steps that TON does not summarize are only model reasoning.
 * The TON progress card already covers that turn, so the generic timeline
 * header would just repeat it. Steps from other tools (files, Code
 * Interpreter, search) keep the timeline visible.
 */
export function onlyReasoningBesidesTon(
  steps: TransformedStep[],
  tools: ToolSnapshot[]
): boolean {
  const ton = steps.some((step) => getTonToolKey(step, tools));
  if (!ton) return false;
  return steps
    .filter((step) => !getTonToolKey(step, tools))
    .every((step) =>
      step.packets.every((packet) => QUIET_PACKETS.has(packet.obj.type))
    );
}
