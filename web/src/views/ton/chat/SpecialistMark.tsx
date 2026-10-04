"use client";

import { Tooltip } from "@opal/components";
import { SpecialistAvatar } from "@/refresh-components/avatars/SpecialistAvatar";
import { specialistIdentity } from "@/lib/ton/specialists";

export interface SpecialistMarkProps {
  specialistKey: string;
  fallbackName?: string | null;
  size?: number;
  /** Shows the name and role on hover. */
  withTooltip?: boolean;
  /** Dims a specialist that is waiting for a source. */
  muted?: boolean;
}

/** A TON specialist in the Onyx agent-avatar style. */
export default function SpecialistMark({
  specialistKey,
  fallbackName,
  size = 28,
  withTooltip = false,
  muted = false,
}: SpecialistMarkProps) {
  const identity = specialistIdentity(specialistKey, fallbackName);
  const avatar = (
    <span className={muted ? "opacity-50" : undefined}>
      <SpecialistAvatar
        size={size}
        Icon={identity.Icon}
        iconClassName={muted ? "stroke-text-03" : identity.iconClassName}
        iconScale={0.95}
      />
    </span>
  );
  if (!withTooltip) return avatar;
  return (
    <Tooltip
      side="top"
      tooltip={
        identity.role ? `${identity.name} · ${identity.role}` : identity.name
      }
    >
      {avatar}
    </Tooltip>
  );
}
