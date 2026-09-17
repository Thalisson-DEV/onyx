"use client";

import { useMemo, useState, useRef } from "react";
import { useTranslations } from "next-intl";
import AgentCard from "@/sections/agents/AgentCard";
import { AgentViewer } from "@/lib/agents/components";
import { useUser } from "@/providers/UserProvider";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";
import { checkUserOwnsAgent } from "@/lib/agents/utils";
import { useAgents } from "@/lib/agents/hooks";
import { MinimalAgent } from "@/lib/agents/types";
import Text from "@/refresh-components/texts/Text";
import { IllustrationContent, SettingsLayouts } from "@opal/layouts";
import TextSeparator from "@/refresh-components/TextSeparator";
import { Button, InputTypeIn } from "@opal/components";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { SvgPlus } from "@opal/icons";
import useOnMount from "@/hooks/useOnMount";
import { useAgentsFilters } from "@/sections/agents/AgentsFilters";

interface AgentsSectionProps {
  title: string;
  description?: string;
  agents: MinimalAgent[];
  viewedAgentId: number | null;
  onView: (agentId: number) => void;
}

function AgentsSection({
  title,
  description,
  agents,
  viewedAgentId,
  onView,
}: AgentsSectionProps) {
  if (agents.length === 0) return null;

  return (
    <div className="flex flex-col gap-2.5">
      <div>
        <Text as="p" headingH3>
          {title}
        </Text>
        {description && (
          <Text as="p" secondaryBody text03>
            {description}
          </Text>
        )}
      </div>
      <div className="w-full flex flex-col divide-y divide-border-default/60 border border-border-default rounded-lg overflow-hidden bg-background-tint-00">
        {agents
          .sort((a, b) => b.id - a.id)
          .map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              isSelected={agent.id === viewedAgentId}
              onView={() => onView(agent.id)}
            />
          ))}
      </div>
    </div>
  );
}

export default function AgentsNavigationPage() {
  const t = useTranslations("agents");
  const { agents } = useAgents();
  const { user, permissions } = useUser();
  const canCreateAgent = hasPermission(permissions, Permission.ADD_AGENTS);
  const [searchQuery, setSearchQuery] = useState("");
  // One viewer for the listing, so the id lives here rather than in whichever
  // card happened to be clicked.
  const [viewedAgentId, setViewedAgentId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<"all" | "your">("all");
  const searchInputRef = useRef<HTMLInputElement>(null);

  useOnMount(() => {
    searchInputRef.current?.focus();
  });

  const nonBuiltinAgents = useMemo(
    () => agents.filter((a) => !a.builtin_persona),
    [agents]
  );

  const { filtered: agentsFilteredByFilters, filterBar } =
    useAgentsFilters(nonBuiltinAgents);

  const memoizedCurrentlyVisibleAgents = useMemo(() => {
    return agentsFilteredByFilters.filter((agent) => {
      const nameMatches = agent.name
        .toLowerCase()
        .includes(searchQuery.toLowerCase());
      const labelMatches = agent.labels?.some((label) =>
        label.name.toLowerCase().includes(searchQuery.toLowerCase())
      );

      const mineFilter =
        activeTab === "your" ? checkUserOwnsAgent(user, agent) : true;

      return (nameMatches || labelMatches) && mineFilter;
    });
  }, [agentsFilteredByFilters, searchQuery, activeTab, user]);

  const featuredAgents = memoizedCurrentlyVisibleAgents.filter(
    (agent) => agent.is_featured
  );
  const allAgents = memoizedCurrentlyVisibleAgents.filter(
    (agent) => !agent.is_featured
  );

  const agentCount = featuredAgents.length + allAgents.length;

  return (
    <SettingsLayouts.Root
      data-testid="AgentsPage/container"
      aria-label={t("navigation.page.ariaLabel")}
      width="lg"
    >
      <AgentViewer
        agentId={viewedAgentId}
        onClose={() => setViewedAgentId(null)}
      />

      {/* Operational, quiet page header — no oversized brand icons */}
      <div className="w-full pt-8 pb-4 px-4 flex flex-col gap-5 border-b border-border-default/40">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div className="flex flex-col gap-1">
            <h1 className="text-2xl font-semibold tracking-tight text-text-04">
              {t("navigation.header.title")}
            </h1>
            <p className="text-sm text-text-03 max-w-xl leading-relaxed">
              {t("navigation.header.description")}
            </p>
          </div>
          <div className="shrink-0">
            <Button
              href={canCreateAgent ? "/app/agents/create" : undefined}
              icon={SvgPlus}
              data-testid="AgentsPage/new-agent-button"
              aria-label={t("navigation.newAgent.ariaLabel")}
              disabled={!canCreateAgent}
              tooltip={
                !canCreateAgent
                  ? t("navigation.newAgent.noPermission.tooltip")
                  : undefined
              }
            >
              {t("navigation.newAgent.label")}
            </Button>
          </div>
        </div>

        {/* Primary Search Input */}
        <div className="w-full">
          <InputTypeIn
            ref={searchInputRef}
            placeholder={t("navigation.search.placeholder")}
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            searchIcon
          />
        </div>

        {/* Quiet Secondary Filter Row: Tabs (Todos / Seus) + Subordinate Filters */}
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between pt-1">
          <div className="w-full sm:w-auto">
            <TabsPrimitive.Root
              value={activeTab}
              // SAFETY: value matches one of the declared trigger values
              onValueChange={(value) => {
                if (value === "all" || value === "your") {
                  setActiveTab(value);
                }
              }}
            >
              <TabsPrimitive.List
                aria-label={t("navigation.tabs.all.label")}
                className="flex items-center gap-6 bg-transparent border-none p-0"
              >
                <TabsPrimitive.Trigger
                  value="all"
                  className="group relative pb-2 text-sm transition-colors cursor-pointer bg-transparent border-none p-0 select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-border-focused rounded-sm data-[state=active]:font-semibold data-[state=active]:text-text-04 data-[state=inactive]:font-normal data-[state=inactive]:text-text-03 hover:data-[state=inactive]:text-text-04"
                >
                  <span>{t("navigation.tabs.all.label")}</span>
                  <span
                    aria-hidden="true"
                    className="absolute inset-x-0 bottom-0 h-[2px] bg-text-04 transition-all opacity-0 group-data-[state=active]:opacity-100"
                  />
                </TabsPrimitive.Trigger>

                <TabsPrimitive.Trigger
                  value="your"
                  className="group relative pb-2 text-sm transition-colors cursor-pointer bg-transparent border-none p-0 select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-border-focused rounded-sm data-[state=active]:font-semibold data-[state=active]:text-text-04 data-[state=inactive]:font-normal data-[state=inactive]:text-text-03 hover:data-[state=inactive]:text-text-04"
                >
                  <span>{t("navigation.tabs.your.label")}</span>
                  <span
                    aria-hidden="true"
                    className="absolute inset-x-0 bottom-0 h-[2px] bg-text-04 transition-all opacity-0 group-data-[state=active]:opacity-100"
                  />
                </TabsPrimitive.Trigger>
              </TabsPrimitive.List>
            </TabsPrimitive.Root>
          </div>

          <div className="flex flex-wrap items-center gap-2 sm:justify-end pb-0.5">
            {filterBar}
          </div>
        </div>
      </div>

      {/* Specialists List Body */}
      <SettingsLayouts.Body>
        {agentCount === 0 ? (
          <div className="w-full flex items-center justify-center py-12">
            <IllustrationContent
              title={t("navigation.empty.title")}
              description={t("navigation.empty.description")}
            />
          </div>
        ) : (
          <>
            <AgentsSection
              title={t("navigation.sections.featured.title")}
              description={t("navigation.sections.featured.description")}
              agents={featuredAgents}
              viewedAgentId={viewedAgentId}
              onView={setViewedAgentId}
            />
            <AgentsSection
              title={t("navigation.sections.all.title")}
              agents={allAgents}
              viewedAgentId={viewedAgentId}
              onView={setViewedAgentId}
            />
            <TextSeparator
              count={agentCount}
              text={t("navigation.countSeparator.label", {
                count: agentCount,
              })}
            />
          </>
        )}
      </SettingsLayouts.Body>
    </SettingsLayouts.Root>
  );
}
