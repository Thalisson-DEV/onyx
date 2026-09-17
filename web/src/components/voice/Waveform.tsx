"use client";

import { useEffect, useState, useMemo, useRef } from "react";
import { useTranslations } from "next-intl";
import { formatElapsedTime } from "@/lib/dateUtils";
import { Button } from "@opal/components";
import { SvgMicrophone, SvgMicrophoneOff } from "@opal/icons";

// Recording waveform constants
export const RECORDING_BAR_COUNT = 120;
const MIN_BAR_HEIGHT = 2;
const MAX_BAR_HEIGHT = 16;

interface WaveformProps {
  /** Visual style and behavior variant. Speaking variant removed in TON-VIS-008. */
  variant?: "recording" | "speaking";
  /** Whether the waveform is actively animating */
  isActive: boolean;
  /** Whether audio is muted */
  isMuted?: boolean;
  /** Current microphone audio level (0-1), used when audio level stream is present */
  audioLevel?: number;
  /** Callback when mute button is clicked */
  onMuteToggle?: () => void;
}

function Waveform({
  variant = "recording",
  isActive,
  isMuted = false,
  audioLevel = 0,
  onMuteToggle,
}: WaveformProps) {
  const t = useTranslations("chat.input.waveform");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [barHeights, setBarHeights] = useState<number[]>(() =>
    Array.from({ length: RECORDING_BAR_COUNT }, () => MIN_BAR_HEIGHT)
  );
  const animationRef = useRef<number | null>(null);
  const lastPushTimeRef = useRef(0);
  const audioLevelRef = useRef(audioLevel);

  useEffect(() => {
    audioLevelRef.current = audioLevel;
  }, [audioLevel]);

  // Speaking waveform removed in TON-VIS-008 (conversational voice disabled)
  const isSpeakingVariant = variant === "speaking";

  // ─── Recording: Timer effect ───────────────────────────────────────────────
  useEffect(() => {
    if (isSpeakingVariant) return;

    if (!isActive) {
      setElapsedSeconds(0);
      return;
    }

    const interval = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [isSpeakingVariant, isActive]);

  // ─── Recording: Audio level visualization effect (when real audio level > 0) ──
  useEffect(() => {
    if (isSpeakingVariant) return;

    if (!isActive || audioLevelRef.current <= 0) {
      setBarHeights(
        Array.from({ length: RECORDING_BAR_COUNT }, () => MIN_BAR_HEIGHT)
      );
      lastPushTimeRef.current = 0;
      return;
    }

    const updateBars = (timestamp: number) => {
      // Push a new bar roughly every 50ms (~20fps scrolling)
      if (timestamp - lastPushTimeRef.current >= 50) {
        lastPushTimeRef.current = timestamp;
        const level = isMuted ? 0 : audioLevelRef.current;
        const height =
          MIN_BAR_HEIGHT + level * (MAX_BAR_HEIGHT - MIN_BAR_HEIGHT);

        setBarHeights((prev) => {
          const next = prev.slice(1);
          next.push(height);
          return next;
        });
      }

      animationRef.current = requestAnimationFrame(updateBars);
    };

    animationRef.current = requestAnimationFrame(updateBars);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
    };
  }, [isSpeakingVariant, isActive, isMuted, audioLevel]);

  const formattedTime = useMemo(
    () => formatElapsedTime(elapsedSeconds),
    [elapsedSeconds]
  );

  if (!isActive || isSpeakingVariant) {
    return null;
  }

  // ─── Honest recording indicator render ──────────────────────────────────────
  return (
    <div className="flex items-center gap-3 px-3 py-2 bg-background-tint-00 rounded-12 min-h-[32px]">
      {audioLevel > 0 ? (
        <div className="flex-1 flex items-center justify-between h-4 overflow-hidden">
          {barHeights.map((height, i) => (
            <div
              key={i}
              className="w-[1.5px] bg-text-03 rounded-full shrink-0 transition-[height] duration-75"
              style={{ height: `${height}px` }}
            />
          ))}
        </div>
      ) : (
        <div className="flex items-center gap-2 flex-1">
          <span
            className={
              isMuted
                ? "w-2 h-2 rounded-full bg-text-03 shrink-0"
                : "w-2 h-2 rounded-full bg-status-destructive animate-pulse shrink-0"
            }
            aria-hidden="true"
          />
          <span className="text-xs text-text-02 font-medium select-none">
            {t("dictating")}
          </span>
        </div>
      )}

      {/* Timer */}
      <span className="font-mono text-xs text-text-03 tabular-nums shrink-0">
        {formattedTime}
      </span>

      {/* Mute button */}
      {onMuteToggle && (
        <Button
          icon={isMuted ? SvgMicrophoneOff : SvgMicrophone}
          onClick={onMuteToggle}
          prominence="tertiary"
          size="sm"
          aria-label={
            isMuted
              ? t("muteButton.unmuteAriaLabel")
              : t("muteButton.muteAriaLabel")
          }
          tooltip={
            isMuted
              ? t("muteButton.unmuteTooltip")
              : t("muteButton.muteTooltip")
          }
        />
      )}
    </div>
  );
}

export default Waveform;
