"use client";

import { cn } from "@opal/utils";
import type { IconProps } from "@opal/types";

// ─── Runtime States ──────────────────────────────────────────────────────────

/**
 * Runtime state of the specialist. Production code must only set a state when
 * backed by real application data. Do NOT fabricate running/attention states.
 *
 * idle      — neutral, no indicator, no animation.
 * running   — contained execution indicator (not the avatar itself animated).
 * attention — semantic amber/gold border; distinct from error.
 * selected  — border + aria-selected; not communicated by color alone.
 */
export type SpecialistState = "idle" | "running" | "attention" | "selected";

// ─── Component ───────────────────────────────────────────────────────────────

export interface SpecialistAvatarProps {
  /** Size in px for both width and height. Defaults to 32. */
  size?: number;
  /** Icon to render inside the container. Decorative — aria-hidden. */
  Icon?: React.FunctionComponent<IconProps>;
  /** className applied to the icon (e.g. stroke-* color). */
  iconClassName?: string;
  /** Inline text content (letter, digit, emoji, CJK). */
  initial?: string;
  /** font size fraction of size (default: 0.5). */
  initialScale?: number;
  /** Runtime state. Never invent this from non-existent data. Default: idle. */
  state?: SpecialistState;
  /** Additional classes applied to the outer container. */
  className?: string;
}

/** Scale factor for icons inside the container. */
const ICON_SCALE = 0.6;

/**
 * SpecialistAvatar — the unified TON specialist identity container.
 *
 * One geometry for all fallback types. The container is a rounded square
 * (radius-08 / 8px). State is communicated through border + aria attributes,
 * not color alone.
 *
 * TON-VIS-007: replaces SvgOctagonWrapper. Do NOT reintroduce brand geometry.
 */
export function SpecialistAvatar({
  size = 32,
  Icon,
  iconClassName,
  initial,
  initialScale = 0.5,
  state = "idle",
  className,
}: SpecialistAvatarProps) {
  const isSelected = state === "selected";
  const isRunning = state === "running";
  const isAttention = state === "attention";

  return (
    <div
      className={cn(
        // Base geometry — rounded square, never octagon.
        "relative flex items-center justify-center shrink-0 overflow-hidden",
        "rounded-lg", // radius-08
        "border",
        // State-driven border semantics.
        isSelected && "border-border-selected",
        isAttention && "border-border-attention",
        !isSelected && !isAttention && "border-border-default",
        // Surface.
        "bg-background-tint-00",
        className
      )}
      style={{ width: size, height: size }}
      // Non-color semantic evidence for selected state (WCAG SC 1.4.1).
      aria-selected={isSelected || undefined}
      // Non-color semantic evidence for attention state.
      data-attention={isAttention || undefined}
      // Running state data attribute (production only when real data exists).
      data-running={isRunning || undefined}
    >
      {Icon && (
        <Icon
          className={cn("shrink-0", iconClassName ?? "stroke-text-03")}
          style={{
            width: size * ICON_SCALE,
            height: size * ICON_SCALE,
          }}
          aria-hidden
        />
      )}
      {!Icon && initial && (
        <span
          aria-hidden
          className="select-none leading-none text-text-03 font-medium"
          style={{ fontSize: size * initialScale }}
        >
          {initial}
        </span>
      )}
      {/* Running state indicator — contained, does not animate the avatar. */}
      {isRunning && (
        <span
          data-testid="running-indicator"
          className="absolute bottom-px end-px w-1.5 h-1.5 rounded-full bg-theme-primary-04 motion-safe:animate-pulse"
          aria-hidden
        />
      )}
    </div>
  );
}

export default SpecialistAvatar;
