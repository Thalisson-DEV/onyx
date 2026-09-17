"use client";

import { MinimalAgent } from "@/lib/agents/types";
import { Text } from "@opal/components";

export interface AgentDescriptionProps {
  agent?: MinimalAgent;
}

export default function AgentDescription({ agent }: AgentDescriptionProps) {
  if (!agent?.description) return null;

  return (
    <div className="w-full min-w-0 text-center">
      <Text
        as="p"
        font="secondary-body"
        color="text-03"
        wordWrap="wrap-break-word"
        textPosition="text-center"
      >
        {agent.description}
      </Text>
    </div>
  );
}
