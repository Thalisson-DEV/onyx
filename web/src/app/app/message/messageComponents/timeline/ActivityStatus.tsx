import { useTranslations } from "next-intl";
import { SvgCheckCircle, SvgSimpleLoader, SvgXCircle } from "@opal/icons";
import type { IconProps } from "@opal/types";
import type { FunctionComponent } from "react";

/**
 * The TON operational activity vocabulary.
 *
 * A timeline step reports what the runtime is observably doing, in three states
 * derived from real packets:
 *
 * - `running`   — a start packet arrived and no end packet has
 * - `completed` — `SECTION_END` (or the tool's own terminal packet) arrived
 * - `failed`    — an `ERROR` packet arrived
 *
 * A renderer may only claim a state the packets actually support. Where the
 * stream cannot distinguish success from failure, the renderer reports
 * `completed` rather than inventing a distinction. The mapping table lives in
 * `plans/ton/frontend/006-messages-streaming-tools.md` §3.
 */
export type ActivityState = "running" | "completed" | "failed";

/**
 * The glyph for a state. `SvgSimpleLoader` is the one contained activity
 * indicator in the transcript — it carries `motion-safe:animate-spin`, so it
 * stops under `prefers-reduced-motion` while the glyph stays.
 */
export function activityStateIcon(
  state: ActivityState
): FunctionComponent<IconProps> {
  switch (state) {
    case "running":
      return SvgSimpleLoader;
    case "completed":
      return SvgCheckCircle;
    case "failed":
      return SvgXCircle;
  }
}

export interface ActivityStatusProps {
  state: ActivityState;
  /** The operation label. Must come from a catalog key, never hard-coded. */
  label: string;
}

/**
 * Inline status for a timeline step header.
 *
 * Renders a `<span>` because `TimelineStepContent` already wraps the header slot
 * in a `<p>`. Carries the state as a visually hidden word as well as a glyph and
 * surface, so state is never communicated by colour alone, and exposes
 * `data-activity-state` so tests can assert the derivation.
 */
export function ActivityStatus({ state, label }: ActivityStatusProps) {
  const t = useTranslations("chat.messages.timeline");

  return (
    <span data-activity-state={state}>
      {label}
      <span className="sr-only">{` ${t(`activity.state.${state}`)}`}</span>
    </span>
  );
}

export default ActivityStatus;
