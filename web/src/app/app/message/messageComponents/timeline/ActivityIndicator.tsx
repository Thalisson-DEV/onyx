import { SvgSimpleLoader } from "@opal/icons";
import { Text } from "@opal/components";
import type { RichStr } from "@opal/types";

export interface ActivityIndicatorProps {
  /** The operation label. Must come from a catalog key, never hard-coded. */
  children: string | RichStr;
}

/**
 * The one running-activity indicator in the transcript header.
 *
 * Replaces the continuous shimmer sweep that used to run across the status text.
 * A sweeping highlight reads as decorative "AI thinking"; a contained spinner
 * next to steady text reads as "a process is running", which is what the packets
 * actually report.
 *
 * `SvgSimpleLoader` carries `motion-safe:animate-spin`, so under
 * `prefers-reduced-motion: reduce` the glyph stays and the rotation stops — the
 * label alone still communicates the state.
 */
export default function ActivityIndicator({
  children,
}: ActivityIndicatorProps) {
  return (
    <div className="flex items-center gap-2 min-w-0">
      <SvgSimpleLoader className="h-3.5 w-3.5 shrink-0 stroke-text-03" />
      <Text as="p" font="main-ui-action" color="text-03" maxLines={1}>
        {children}
      </Text>
    </div>
  );
}
