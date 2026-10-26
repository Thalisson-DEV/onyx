"use client";

import { cn } from "@opal/utils";

export interface TonMarkProps {
  size?: number;
  /** TON is working on the answer: the Vale Norte arrows turn. */
  working?: boolean;
  className?: string;
}

/**
 * The TON identity in the conversation: the Vale Norte arrows on a round
 * coin. The arrows already suggest motion, so while TON thinks they turn.
 * Decorative; the surrounding text names the state.
 */
export default function TonMark({
  size = 32,
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
      <img
        src="/ton/vale-norte-mark.png"
        alt=""
        width={Math.round(size * 0.7)}
        height={Math.round(size * 0.7)}
        draggable={false}
      />
    </span>
  );
}
