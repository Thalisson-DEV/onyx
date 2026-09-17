"use client";

import { MinimalAgent } from "@/lib/agents/types";
import { buildAgentAvatarUrl } from "@/lib/agents/utils";
import { useSettings } from "@/lib/settings/hooks";
import { DEFAULT_AVATAR_SIZE_PX, DEFAULT_AGENT_ID } from "@/lib/constants";
import CustomAgentAvatar from "@/refresh-components/avatars/CustomAgentAvatar";
import {
  SpecialistAvatar,
  type SpecialistState,
} from "@/refresh-components/avatars/SpecialistAvatar";
import { SvgManageAgent } from "@opal/icons";
import Image from "next/image";
import { useTranslations } from "next-intl";

export interface AgentAvatarProps {
  agent: MinimalAgent;
  size?: number;
  /** Runtime state of the specialist. */
  state?: SpecialistState;
  className?: string;
}

export default function AgentAvatar({
  agent,
  size = DEFAULT_AVATAR_SIZE_PX,
  state = "idle",
  className,
  ...props
}: AgentAvatarProps) {
  const t = useTranslations("common.agentAvatar");
  const { enterprise: enterpriseSettings } = useSettings();

  if (agent.id === DEFAULT_AGENT_ID) {
    return enterpriseSettings?.use_custom_logo ? (
      <div
        className="aspect-square rounded-full overflow-hidden relative shrink-0"
        style={{ height: size, width: size }}
      >
        <Image
          alt={t("logo.alt")}
          src="/api/enterprise-settings/logo"
          fill
          className="object-cover object-center"
          sizes={`${size}px`}
        />
      </div>
    ) : (
      <SpecialistAvatar
        size={size}
        Icon={SvgManageAgent}
        iconClassName="stroke-theme-primary-05"
        state={state}
        className={className}
      />
    );
  }

  return (
    <CustomAgentAvatar
      name={agent.name}
      src={agent.uploaded_image_id ? buildAgentAvatarUrl(agent.id) : undefined}
      iconName={agent.icon_name}
      size={size}
      state={state}
      {...props}
    />
  );
}
