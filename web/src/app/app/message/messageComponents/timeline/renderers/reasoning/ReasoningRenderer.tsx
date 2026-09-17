import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import {
  PacketType,
  ReasoningPacket,
} from "@/app/app/services/streamingModels";
import {
  FullChatState,
  MessageRenderer,
  RendererResult,
} from "@/app/app/message/messageComponents/interfaces";
import {
  ActivityStatus,
  activityStateIcon,
  type ActivityState,
} from "@/app/app/message/messageComponents/timeline/ActivityStatus";

/**
 * Observable execution step for a model deliberation phase.
 *
 * TON does not surface private chain-of-thought. The reasoning packets tell us
 * exactly three observable things — a deliberation phase started, it is still
 * running, and it ended — so that is all this step reports. The text carried by
 * `REASONING_DELTA` is never read, never accumulated and never rendered, so it
 * cannot reach the DOM, accessibility tree, or user actions.
 *
 * The packets themselves stay untouched in the stream: `packetProcessor` still
 * groups them and still uses `REASONING_START` to open a step, so sequencing and
 * ordering are unchanged.
 */

/** Matches the old dwell time so short phases don't flash and vanish. */
const MIN_VISIBLE_DURATION_MS = 500;

interface ReasoningActivity {
  hasStart: boolean;
  hasEnd: boolean;
  failed: boolean;
}

/**
 * Reads only packet *types*. `REASONING_DELTA` is counted as neither start nor
 * end and its `reasoning` field is never touched.
 */
function readReasoningActivity(packets: ReasoningPacket[]): ReasoningActivity {
  let hasStart = false;
  let hasEnd = false;
  let failed = false;

  for (const packet of packets) {
    switch (packet.obj.type) {
      case PacketType.REASONING_START:
        hasStart = true;
        break;
      case PacketType.ERROR:
        failed = true;
        hasEnd = true;
        break;
      case PacketType.REASONING_DONE:
      case PacketType.SECTION_END:
        hasEnd = true;
        break;
      default:
        break;
    }
  }

  return { hasStart, hasEnd, failed };
}

export const ReasoningRenderer: MessageRenderer<
  ReasoningPacket,
  FullChatState
> = ({ packets, onComplete, animate, children }) => {
  const t = useTranslations("chat.messages.timeline");

  const { hasStart, hasEnd, failed } = useMemo(
    () => readReasoningActivity(packets),
    [packets]
  );

  const [startedAt, setStartedAt] = useState<number | null>(null);
  const completionHandledRef = useRef(false);

  useEffect(() => {
    if ((hasStart || hasEnd) && startedAt === null) {
      setStartedAt(Date.now());
    }
  }, [hasStart, hasEnd, startedAt]);

  // Completion signalling is load-bearing for the timeline: the step chain
  // waits on it. Preserved exactly, including the minimum dwell.
  useEffect(() => {
    if (!hasEnd || startedAt === null || completionHandledRef.current) {
      return;
    }

    const complete = () => {
      if (!completionHandledRef.current) {
        completionHandledRef.current = true;
        onComplete();
      }
    };

    const elapsed = Date.now() - startedAt;
    const minimum = animate ? MIN_VISIBLE_DURATION_MS : 0;

    if (elapsed >= minimum) {
      complete();
      return;
    }

    const timeout = setTimeout(complete, minimum - elapsed);
    return () => clearTimeout(timeout);
  }, [hasEnd, startedAt, animate, onComplete]);

  const state: ActivityState = failed
    ? "failed"
    : hasEnd
      ? "completed"
      : "running";
  const label = hasEnd
    ? failed
      ? t("activity.failed.label")
      : t("activity.processed.label")
    : t("activity.processing.label");

  const result: RendererResult = {
    icon: activityStateIcon(state),
    status: <ActivityStatus state={state} label={label} />,
    // No body: the runtime exposes no public detail for this phase, and an
    // honest empty step beats a fabricated one.
    content: <></>,
    noPaddingRight: true,
  };
  if (failed) {
    result.surfaceBackground = "error";
  }

  return children([result]);
};

export default ReasoningRenderer;
