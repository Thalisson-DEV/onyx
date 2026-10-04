"use client";

import { cn } from "@opal/utils";

export interface TonMarkProps {
  size?: number;
  /** TON is working on the answer: a gold ring orbits the mark. */
  working?: boolean;
  className?: string;
}

/**
 * The TON identity in the conversation: the brand-green chrome as a rounded
 * square, a "T" glyph and the gold spark from the Vale Norte palette.
 * Decorative; the surrounding text names the state.
 */
export default function TonMark({
  size = 28,
  working = false,
  className,
}: TonMarkProps) {
  return (
    <span
      aria-hidden
      className={cn("ton-mark", className)}
      data-working={working || undefined}
      style={{ width: size, height: size }}
    >
      <svg viewBox="0 0 16 16" fill="none">
        <path
          d="M3.75 5.25H10.25M7 5.25V12.25"
          stroke="currentColor"
          strokeWidth={1.75}
          strokeLinecap="round"
        />
        <path
          className="ton-mark-spark"
          d="M12 1.75L12.7 3.3L14.25 4L12.7 4.7L12 6.25L11.3 4.7L9.75 4L11.3 3.3L12 1.75Z"
        />
      </svg>
    </span>
  );
}
