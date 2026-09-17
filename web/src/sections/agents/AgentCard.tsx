"use client";

import { useMemo, useCallback } from "react";
import { useTranslations } from "next-intl";
import { MinimalAgent } from "@/lib/agents/types";
import AgentAvatar from "@/refresh-components/avatars/AgentAvatar";
import { Button } from "@opal/components";
import { usePinnedAgents } from "@/lib/agents/hooks";
import { noProp } from "@/lib/utils";
import { useRouter } from "next/navigation";
import { can } from "@/lib/permissions/resource-actions";
import { useTierAtLeast } from "@/hooks/useTierAtLeast";
import { Tier } from "@/lib/settings/types";
import {
  SvgActions,
  SvgBarChart,
  SvgBubbleText,
  SvgEdit,
  SvgPin,
  SvgPinned,
  SvgShare,
  SvgUser,
} from "@opal/icons";
import { useCreateModal } from "@opal/components";
import { useAppPosition } from "@/lib/position/hooks";
import { ShareAgentModal } from "@/lib/agents/components";
import { cn } from "@opal/utils";

export interface AgentCardProps {
  agent: MinimalAgent;
  isSelected?: boolean;
  /** Opens this agent's viewer, which the listing renders. */
  onView: () => void;
}

/**
 * AgentCard — operational specialist row for TON.
 *
 * Designed as a restrained, quiet, single-zone flat row:
 * - Content-driven height (no arbitrary fixed box).
 * - Identity + Name + Description as primary hierarchy.
 * - Actions and Start Conversation aligned to the right.
 * - Selected state indicated via semantic background and border tokens.
 * - No multi-zone card split, no decorative gradients, no elevated tile shadows.
 */
export default function AgentCard({ agent, isSelected = false, onView }: AgentCardProps) {
  const t = useTranslations("agents");
  const appPosition = useAppPosition();
  const router = useRouter();
  const { pinnedAgents, togglePinnedAgent } = usePinnedAgents();
  const pinned = useMemo(
    () => pinnedAgents.some((pinnedAgent) => pinnedAgent.id === agent.id),
    [agent.id, pinnedAgents]
  );
  const businessTier = useTierAtLeast(Tier.BUSINESS);
  const shareAgentModal = useCreateModal();

  // Start chat and auto-pin unpinned agents to the sidebar
  const handleStartChat = useCallback(() => {
    if (!pinned) {
      togglePinnedAgent(agent, true);
    }
    appPosition.openAgent(agent.id);
  }, [pinned, togglePinnedAgent, agent, appPosition]);

  return (
    <>
      <shareAgentModal.Provider>
        {/* Saved agents persist sharing inside the dialog itself */}
        <ShareAgentModal agentId={agent.id} />
      </shareAgentModal.Provider>

      <div
        role="button"
        tabIndex={0}
        onClick={onView}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onView();
          }
        }}
        data-testid={`SpecialistRow/${agent.id}`}
        data-selected={isSelected ? "true" : undefined}
        className={cn(
          "group/agent-row flex self-stretch flex-col sm:flex-row sm:items-center justify-between gap-3 px-4 py-3 cursor-pointer transition-colors text-left select-none",
          isSelected
            ? "bg-background-tint-02 border-l-2 border-l-border-selected"
            : "hover:bg-background-tint-01/80 border-l-2 border-l-transparent"
        )}
      >
        {/* Left: Identity + Primary Info */}
        <div className="flex items-start sm:items-center gap-3 min-w-0 flex-1">
          <div className="shrink-0 pt-0.5 sm:pt-0">
            <AgentAvatar agent={agent} size={32} />
          </div>

          <div className="flex flex-col min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold text-text-04 truncate">
                {agent.name}
              </span>
              {agent.owner?.email && (
                <span className="text-xs text-text-02 truncate flex items-center gap-1">
                  <SvgUser className="w-3 h-3 text-text-02 shrink-0" />
                  {agent.owner.email}
                </span>
              )}
            </div>

            {agent.description && (
              <p className="text-xs text-text-03 line-clamp-1 leading-relaxed mt-0.5">
                {agent.description}
              </p>
            )}
          </div>
        </div>

        {/* Right: Actions aligned to the right */}
        <div className="flex items-center justify-between sm:justify-end gap-1.5 shrink-0 pt-1 sm:pt-0">
          <div className="flex items-center gap-0.5">
            {can(agent, "view_stats") && businessTier && (
              <Button
                icon={SvgBarChart}
                prominence="tertiary"
                size="sm"
                onClick={noProp(() =>
                  router.push(`/ee/agents/stats/${agent.id}`)
                )}
                tooltip={t("card.viewStats.tooltip")}
              />
            )}
            {can(agent, "edit") && (
              <Button
                icon={SvgEdit}
                prominence="tertiary"
                size="sm"
                onClick={noProp(() =>
                  router.push(`/app/agents/edit/${agent.id}`)
                )}
                tooltip={t("card.edit.tooltip")}
              />
            )}
            {can(agent, "share") && (
              <Button
                icon={SvgShare}
                prominence="tertiary"
                size="sm"
                onClick={noProp(() => shareAgentModal.toggle(true))}
                tooltip={t("card.share.tooltip")}
              />
            )}
            <span
              className={cn(
                !pinned &&
                  "opacity-0 group-hover/agent-row:opacity-100 focus-within:opacity-100 transition-opacity"
              )}
            >
              <Button
                icon={pinned ? SvgPinned : SvgPin}
                prominence="tertiary"
                size="sm"
                onClick={noProp(() => togglePinnedAgent(agent, !pinned))}
                tooltip={pinned ? t("card.unpin.tooltip") : t("card.pin.tooltip")}
              />
            </span>
          </div>

          {/* Start Conversation button */}
          <Button
            prominence="tertiary"
            size="sm"
            rightIcon={SvgBubbleText}
            onClick={noProp(handleStartChat)}
          >
            {t("card.startChat.label")}
          </Button>
        </div>
      </div>
    </>
  );
}
