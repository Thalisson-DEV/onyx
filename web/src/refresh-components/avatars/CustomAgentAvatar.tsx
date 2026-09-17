"use client";

import { cn } from "@opal/utils";
import type { IconProps } from "@opal/types";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { DEFAULT_AVATAR_SIZE_PX } from "@/lib/constants";
import { SpecialistAvatar } from "@/refresh-components/avatars/SpecialistAvatar";
import type { SpecialistState } from "@/refresh-components/avatars/SpecialistAvatar";
import {
  SvgActivitySmall,
  SvgAudioEqSmall,
  SvgBarChartSmall,
  SvgBooksLineSmall,
  SvgBooksStackSmall,
  SvgCheckSmall,
  SvgClockHandsSmall,
  SvgFileSmall,
  SvgHashSmall,
  SvgImageSmall,
  SvgInfoSmall,
  SvgMusicSmall,
  SvgPenSmall,
  SvgQuestionMarkSmall,
  SvgSearchSmall,
  SvgSlidersSmall,
  SvgTerminalSmall,
  SvgTextLinesSmall,
  SvgTwoLineSmall,
} from "@opal/icons";

// ─── Icon Map ────────────────────────────────────────────────────────────────

interface IconConfig {
  Icon: React.FunctionComponent<IconProps>;
  className?: string;
}

/**
 * Mapping of icon names to icon components + stroke class.
 *
 * Colors are TON semantic tokens — NOT raw palette colors.
 * The 4 "green" entries use stroke-theme-primary-05 (identity/selection)
 * and NOT stroke-theme-green-05 (which is Onyx green, #008933, not Vale Norte).
 */
export const agentAvatarIconMap: Record<string, IconConfig> = {
  Info: { Icon: SvgInfoSmall, className: "stroke-theme-primary-05" },
  QuestionMark: {
    Icon: SvgQuestionMarkSmall,
    className: "stroke-theme-primary-05",
  },

  // blue
  TextLines: { Icon: SvgTextLinesSmall, className: "stroke-theme-blue-05" },
  Pen: { Icon: SvgPenSmall, className: "stroke-theme-blue-05" },
  ClockHands: { Icon: SvgClockHandsSmall, className: "stroke-theme-blue-05" },
  Hash: { Icon: SvgHashSmall, className: "stroke-theme-blue-05" },

  // primary (was erroneously using stroke-theme-green-05 / Onyx green)
  Search: { Icon: SvgSearchSmall, className: "stroke-theme-primary-05" },
  Check: { Icon: SvgCheckSmall, className: "stroke-theme-primary-05" },
  BarChart: { Icon: SvgBarChartSmall, className: "stroke-theme-primary-05" },
  Activity: { Icon: SvgActivitySmall, className: "stroke-theme-primary-05" },

  // purple
  File: { Icon: SvgFileSmall, className: "stroke-theme-purple-05" },
  Image: { Icon: SvgImageSmall, className: "stroke-theme-purple-05" },
  BooksStack: { Icon: SvgBooksStackSmall, className: "stroke-theme-purple-05" },
  BooksLine: { Icon: SvgBooksLineSmall, className: "stroke-theme-purple-05" },

  // orange
  Terminal: { Icon: SvgTerminalSmall, className: "stroke-theme-orange-04" },
  Sliders: { Icon: SvgSlidersSmall, className: "stroke-theme-orange-04" },

  // amber
  AudioEq: { Icon: SvgAudioEqSmall, className: "stroke-theme-amber-04" },
  Music: { Icon: SvgMusicSmall, className: "stroke-theme-amber-04" },
};

// ─── Fallback Helpers ─────────────────────────────────────────────────────────

/**
 * Returns the first user-perceived character (grapheme cluster) of the string.
 * Accepts Latin letters, digits, emoji, CJK characters — not just /^[a-zA-Z]$/.
 *
 * VIS-007: the old restriction `/^[a-zA-Z]$/` excluded digits, emoji and CJK.
 */
function firstGrapheme(s: string): string | undefined {
  const trimmed = s.trim();
  if (trimmed.length === 0) return undefined;
  const seg = new Intl.Segmenter(undefined, { granularity: "grapheme" });
  const [first] = seg.segment(trimmed);
  return first?.segment ?? undefined;
}

// ─── Component ───────────────────────────────────────────────────────────────

export interface CustomAgentAvatarProps {
  name?: string;
  src?: string;
  iconName?: string;
  size?: number;
  /** Runtime state. Only set when backed by real application data. */
  state?: SpecialistState;
}

/**
 * CustomAgentAvatar — renders a specialist identity for a user-configured agent.
 *
 * Fallback chain (deterministic, no randomized color):
 *   1. uploaded image  → circular crop (preserves photographic intent)
 *   2. configured icon → SpecialistAvatar with named icon
 *   3. first grapheme  → SpecialistAvatar with initial (letter/digit/emoji/CJK)
 *   4. empty/missing   → SpecialistAvatar with TwoLine glyph
 *
 * The image case retains circular geometry because a photograph is semantically
 * an avatar; the surrounding specialist identity contract still applies at
 * callsites that show state or selection.
 */
export default function CustomAgentAvatar({
  name,
  src,
  iconName,
  size = DEFAULT_AVATAR_SIZE_PX,
  state = "idle",
}: CustomAgentAvatarProps) {
  const t = useTranslations("common.agentAvatar");

  if (src) {
    return (
      <div
        className={cn(
          "aspect-square rounded-full overflow-hidden relative shrink-0",
          // Forward selected/attention border to the image container so the
          // visual contract is coherent regardless of content type.
          state === "selected" && "ring-1 ring-border-selected",
          state === "attention" && "ring-1 ring-border-attention"
        )}
        style={{ height: size, width: size }}
        aria-selected={state === "selected" || undefined}
        data-attention={state === "attention" || undefined}
        data-running={state === "running" || undefined}
      >
        <Image
          alt={name || t("image.altFallback")}
          src={src}
          fill
          className="object-cover object-center"
          sizes={`${size}px`}
        />
      </div>
    );
  }

  const iconConfig = iconName && agentAvatarIconMap[iconName];
  if (iconConfig) {
    const { Icon, className: iconClassName } = iconConfig;
    return (
      <SpecialistAvatar
        size={size}
        Icon={Icon}
        iconClassName={iconClassName}
        state={state}
      />
    );
  }

  const initial = name ? firstGrapheme(name) : undefined;
  if (initial) {
    return (
      <SpecialistAvatar
        size={size}
        initial={initial.toUpperCase()}
        state={state}
      />
    );
  }

  return (
    <SpecialistAvatar
      size={size}
      Icon={SvgTwoLineSmall}
      iconClassName="stroke-text-03"
      state={state}
    />
  );
}
