import { cn } from "@opal/utils";

/**
 * Streaming caret.
 *
 * This is functional feedback, not decoration: it marks where the answer is
 * still being written, both as the empty-content placeholder and as the inline
 * caret at the end of streamed markdown. So it stays.
 *
 * `motion-safe:` matches the pattern VIS-001 set on `SvgSimpleLoader` — under
 * `prefers-reduced-motion: reduce` the bar stays put and stops blinking, which
 * still reads as "the answer continues here". `aria-hidden` because the caret is
 * a visual cue for sighted readers; assistive technology follows the text.
 *
 * Retuning the blink onto the VIS-001 motion tokens needs a keyframe in
 * `globals.css`, which VIS-009 owns. Recorded as deferred in
 * `plans/ton/frontend/006-messages-streaming-tools.md` §14.
 */
export function BlinkingBar({ addMargin = false }: { addMargin?: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "motion-safe:animate-pulse flex-none bg-theme-primary-05 relative top-[0.15rem] inline-block w-2 h-4",
        addMargin && "ms-1"
      )}
    ></span>
  );
}
