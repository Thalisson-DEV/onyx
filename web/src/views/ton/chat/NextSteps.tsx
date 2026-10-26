"use client";

import { SvgArrowRight } from "@opal/icons";
import { COPY } from "@/lib/ton/copy";
import { sendTonMessage } from "@/lib/ton/agent-actions";

/** The requests the TON suggests next; a click sends one as the person. */
export default function NextSteps({ steps }: { steps: string[] }) {
  if (!steps.length) return null;
  return (
    <nav className="tn-next" aria-label={COPY.chat.nextSteps}>
      <span className="tn-next-label">{COPY.chat.nextSteps}</span>
      <span className="tn-next-row">
        {steps.map((step) => (
          // Suggestion chips are pill-shaped text buttons, not Opal actions.
          <button
            key={step}
            type="button"
            className="tn-next-chip ton-focusable"
            onClick={() => sendTonMessage(step)}
          >
            {step}
            <SvgArrowRight size={12} aria-hidden />
          </button>
        ))}
      </span>
    </nav>
  );
}
